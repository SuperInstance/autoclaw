"""Durable inter-agent message bus backed by SQLite.

Agents publish and subscribe to messages. Messages are persisted so
no work is lost if an agent restarts. Each message has:
  - A routing address (agent ID, role group, or broadcast)
  - A type and priority
  - A JSON payload
  - A lifecycle: pending → delivered → processing → completed/failed

Design:
  - SQLite for durability (survives crashes)
  - Threading lock for concurrent access from multiple agent threads
  - Pub/sub via role-group routing ('any_researcher', 'broadcast', etc.)
  - TTL expiry for messages that are no longer relevant
  - Dead-letter queue for failed messages (stored separately)
"""

import json
import sqlite3
import threading
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

DB_PATH = Path("data/messages.db")


@dataclass
class Message:
    """Inter-agent message."""

    from_agent: str
    to_agent: str        # agent ID | 'any_researcher' | 'broadcast' | 'daemon'
    type: str            # task_request | result | challenge | knowledge | ...
    payload: Dict[str, Any]
    priority: int = 5    # 1-10, lower = higher priority
    tags: List[str] = field(default_factory=list)
    parent_message_id: Optional[int] = None
    expires_in_hours: Optional[float] = None

    # Auto-filled
    id: Optional[int] = None
    status: str = "pending"
    created_at: Optional[str] = None
    delivered_at: Optional[str] = None
    completed_at: Optional[str] = None
    expires_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.expires_in_hours and self.expires_at is None:
            expiry = datetime.now(timezone.utc) + timedelta(hours=self.expires_in_hours)
            self.expires_at = expiry.isoformat()


class MessageBus:
    """SQLite-backed durable message bus for inter-agent communication.

    Usage:
        bus = MessageBus()
        msg_id = bus.publish(Message(
            from_agent="daemon",
            to_agent="any_researcher",
            type="task_request",
            payload={"topic": "transformer warmup"}
        ))

        # Agent picks up its messages
        messages = bus.receive("researcher_1", roles=["researcher"])
        for msg in messages:
            process(msg)
            bus.complete(msg.id)
    """

    def __init__(self, db_path: Path = DB_PATH):
        """Initialize message bus.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[Callable]] = {}  # type → callbacks
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite schema."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_agent    TEXT    NOT NULL,
                    to_agent      TEXT    NOT NULL,
                    type          TEXT    NOT NULL,
                    priority      INTEGER DEFAULT 5,
                    payload       TEXT    NOT NULL,
                    tags          TEXT    DEFAULT '[]',
                    status        TEXT    DEFAULT 'pending',
                    created_at    TEXT    NOT NULL,
                    delivered_at  TEXT,
                    completed_at  TEXT,
                    expires_at    TEXT,
                    parent_message_id INTEGER,
                    error_message TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_status ON messages(status);
                CREATE INDEX IF NOT EXISTS idx_to_agent ON messages(to_agent);
                CREATE INDEX IF NOT EXISTS idx_priority ON messages(priority, created_at);
                CREATE INDEX IF NOT EXISTS idx_type ON messages(type);

                CREATE TABLE IF NOT EXISTS dead_letters (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_id   INTEGER NOT NULL,
                    reason        TEXT    NOT NULL,
                    failed_at     TEXT    NOT NULL,
                    payload       TEXT    NOT NULL
                );
            """)

    def _get_conn(self) -> sqlite3.Connection:
        """Get SQLite connection with row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def publish(self, message: Message) -> int:
        """Publish a message to the bus.

        Args:
            message: Message to publish

        Returns: Message ID
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """INSERT INTO messages
                       (from_agent, to_agent, type, priority, payload, tags,
                        status, created_at, expires_at, parent_message_id)
                       VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
                    (
                        message.from_agent,
                        message.to_agent,
                        message.type,
                        message.priority,
                        json.dumps(message.payload),
                        json.dumps(message.tags),
                        message.created_at,
                        message.expires_at,
                        message.parent_message_id,
                    ),
                )
                msg_id = cursor.lastrowid
                message.id = msg_id

        logger.debug(
            f"Published message #{msg_id} type={message.type} "
            f"from={message.from_agent} to={message.to_agent}"
        )

        # Notify subscribers (in-process callbacks)
        self._notify_subscribers(message)

        return msg_id

    def receive(
        self,
        agent_id: str,
        roles: Optional[List[str]] = None,
        limit: int = 10,
        min_priority: int = 10,
    ) -> List[Message]:
        """Receive pending messages for an agent.

        Checks messages addressed to:
          1. This specific agent ID
          2. Role groups matching agent's roles (e.g., 'any_researcher')
          3. 'broadcast' messages not yet seen by this agent

        Args:
            agent_id: This agent's unique ID
            roles: List of roles this agent has (e.g., ['researcher'])
            limit: Max messages to return
            min_priority: Only return messages with priority <= this

        Returns: List of messages, highest priority first
        """
        if roles is None:
            roles = []

        # Build list of addresses this agent can receive
        addresses = [agent_id, "broadcast"]
        for role in roles:
            addresses.append(f"any_{role}")

        placeholders = ",".join("?" * len(addresses))
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            with self._get_conn() as conn:
                rows = conn.execute(
                    f"""SELECT * FROM messages
                        WHERE to_agent IN ({placeholders})
                          AND status = 'pending'
                          AND priority <= ?
                          AND (expires_at IS NULL OR expires_at > ?)
                        ORDER BY priority ASC, created_at ASC
                        LIMIT ?""",
                    (*addresses, min_priority, now, limit),
                ).fetchall()

                messages = []
                for row in rows:
                    msg = self._row_to_message(row)

                    # Mark as delivered
                    conn.execute(
                        "UPDATE messages SET status='delivered', delivered_at=? WHERE id=?",
                        (datetime.now(timezone.utc).isoformat(), msg.id),
                    )
                    msg.status = "delivered"
                    messages.append(msg)

        return messages

    def mark_processing(self, message_id: int):
        """Mark a message as being processed."""
        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE messages SET status='processing' WHERE id=?",
                    (message_id,),
                )

    def complete(self, message_id: int):
        """Mark a message as successfully completed."""
        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE messages SET status='completed', completed_at=? WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), message_id),
                )

    def fail(self, message_id: int, error: str):
        """Mark a message as failed and move to dead-letter queue."""
        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE messages SET status='failed', error_message=? WHERE id=?",
                    (error, message_id),
                )

                # Copy to dead letters
                row = conn.execute(
                    "SELECT payload FROM messages WHERE id=?", (message_id,)
                ).fetchone()
                if row:
                    conn.execute(
                        """INSERT INTO dead_letters (original_id, reason, failed_at, payload)
                           VALUES (?, ?, ?, ?)""",
                        (message_id, error, datetime.now(timezone.utc).isoformat(), row["payload"]),
                    )

    def subscribe(self, message_type: str, callback: Callable[[Message], None]):
        """Register an in-process callback for a message type.

        Callbacks are called synchronously on publish. For heavy processing,
        use receive() polling instead.

        Args:
            message_type: Type to subscribe to, or '*' for all
            callback: Function called with Message on publish
        """
        if message_type not in self._subscribers:
            self._subscribers[message_type] = []
        self._subscribers[message_type].append(callback)

    def _notify_subscribers(self, message: Message):
        """Call in-process subscribers for a message."""
        for msg_type in [message.type, "*"]:
            for cb in self._subscribers.get(msg_type, []):
                try:
                    cb(message)
                except Exception as e:
                    logger.warning(f"Subscriber callback error: {e}")

    def get_pending_count(self, to_agent: Optional[str] = None) -> int:
        """Get count of pending messages.

        Args:
            to_agent: Filter by recipient, or None for all

        Returns: Count of pending messages
        """
        with self._get_conn() as conn:
            if to_agent:
                row = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE status='pending' AND to_agent=?",
                    (to_agent,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE status='pending'",
                ).fetchone()
            return row[0] if row else 0

    def get_queue_depths(self) -> Dict[str, int]:
        """Get message count by status for monitoring.

        Returns: Dict of status → count
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM messages GROUP BY status"
            ).fetchall()
            return {row["status"]: row["cnt"] for row in rows}

    def cleanup_expired(self) -> int:
        """Remove expired messages. Returns count removed."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """UPDATE messages SET status='expired'
                       WHERE status='pending' AND expires_at IS NOT NULL AND expires_at < ?""",
                    (now,),
                )
                return cursor.rowcount

    def cleanup_old_completed(self, days: int = 7) -> int:
        """Remove completed messages older than N days. Returns count removed."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """DELETE FROM messages
                       WHERE status IN ('completed', 'expired', 'failed')
                         AND created_at < ?""",
                    (cutoff,),
                )
                return cursor.rowcount

    def get_message(self, message_id: int) -> Optional[Message]:
        """Get a specific message by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM messages WHERE id=?", (message_id,)
            ).fetchone()
            return self._row_to_message(row) if row else None

    def get_thread(self, message_id: int) -> List[Message]:
        """Get a message and all its replies (by parent_message_id chain)."""
        result = []
        seen = set()

        def collect(mid: int):
            if mid in seen:
                return
            seen.add(mid)
            msg = self.get_message(mid)
            if msg:
                result.append(msg)
                # Find replies
                with self._get_conn() as conn:
                    rows = conn.execute(
                        "SELECT id FROM messages WHERE parent_message_id=?", (mid,)
                    ).fetchall()
                    for row in rows:
                        collect(row["id"])

        collect(message_id)
        result.sort(key=lambda m: m.created_at or "")
        return result

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        """Convert SQLite row to Message dataclass."""
        return Message(
            id=row["id"],
            from_agent=row["from_agent"],
            to_agent=row["to_agent"],
            type=row["type"],
            priority=row["priority"],
            payload=json.loads(row["payload"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            status=row["status"],
            created_at=row["created_at"],
            delivered_at=row["delivered_at"],
            completed_at=row["completed_at"],
            expires_at=row["expires_at"],
            parent_message_id=row["parent_message_id"],
        )


# ============================================================================
# Global singleton bus (shared across all agents in same process)
# ============================================================================

_default_bus: Optional[MessageBus] = None
_bus_lock = threading.Lock()


def get_bus(db_path: Path = DB_PATH) -> MessageBus:
    """Get or create the global message bus singleton.

    Args:
        db_path: Database path (only used on first call)

    Returns: Shared MessageBus instance
    """
    global _default_bus
    with _bus_lock:
        if _default_bus is None:
            _default_bus = MessageBus(db_path)
    return _default_bus
