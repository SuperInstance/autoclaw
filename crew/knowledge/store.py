"""Multi-tier knowledge store.

Facade over all storage tiers: hot (memory) → warm (SQLite) → cold (files).
All reads/writes go through this interface. Tier selection is transparent.

Architecture:
  - HOT:  Python dict (in-memory LRU), < 1000 entries, backed up to SQLite
  - WARM: SQLite database (local), optionally synced to CF D1
  - COLD: Compressed JSON files on disk, optionally synced to CF R2

Usage:
    store = KnowledgeStore()
    entry_id = store.add(
        insight="LR=0.005 optimal for DEPTH=8",
        category="hyperparameter",
        tags=["learning-rate", "depth-8"],
        confidence="very_high",
    )
    results = store.query(tags=["learning-rate"], min_confidence="medium")
    entry = store.get(entry_id)
    store.update(entry_id, confidence="very_high")
"""

import json
import sqlite3
import threading
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from collections import OrderedDict
import yaml

logger = logging.getLogger(__name__)

DB_PATH = Path("data/knowledge/warm.db")
COLD_DIR = Path("data/knowledge/cold")


class KnowledgeEntry:
    """A single knowledge entry."""

    def __init__(
        self,
        insight: str,
        category: str,
        tags: List[str],
        confidence: str = "medium",
        conditions: Optional[str] = None,
        evidence: Optional[Dict] = None,
        source_agent: Optional[str] = None,
        entry_id: Optional[int] = None,
        status: str = "active",
        tier: str = "hot",
        score: float = 0.5,
        created_at: Optional[str] = None,
        last_validated: Optional[str] = None,
        queries_last_7d: int = 0,
    ):
        self.id = entry_id
        self.insight = insight
        self.category = category
        self.tags = tags
        self.confidence = confidence
        self.conditions = conditions
        self.evidence = evidence or {}
        self.source_agent = source_agent
        self.status = status
        self.tier = tier
        self.score = score
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.last_validated = last_validated
        self.queries_last_7d = queries_last_7d

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "insight": self.insight,
            "category": self.category,
            "tags": self.tags,
            "confidence": self.confidence,
            "conditions": self.conditions,
            "evidence": self.evidence,
            "source_agent": self.source_agent,
            "status": self.status,
            "tier": self.tier,
            "score": self.score,
            "created_at": self.created_at,
            "last_validated": self.last_validated,
            "queries_last_7d": self.queries_last_7d,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgeEntry":
        return cls(
            entry_id=d.get("id"),
            insight=d["insight"],
            category=d["category"],
            tags=d.get("tags", []),
            confidence=d.get("confidence", "medium"),
            conditions=d.get("conditions"),
            evidence=d.get("evidence", {}),
            source_agent=d.get("source_agent"),
            status=d.get("status", "active"),
            tier=d.get("tier", "warm"),
            score=d.get("score", 0.5),
            created_at=d.get("created_at"),
            last_validated=d.get("last_validated"),
            queries_last_7d=d.get("queries_last_7d", 0),
        )


class KnowledgeStore:
    """Multi-tier knowledge store with hot/warm/cold tiers.

    All knowledge entries flow through:
      hot (memory) → warm (SQLite) → cold (files) → archive/deleted

    The GC cycle in lifecycle.py handles promotion/demotion.
    """

    def __init__(
        self,
        db_path: Path = DB_PATH,
        cold_dir: Path = COLD_DIR,
        hot_max: int = 1000,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize knowledge store.

        Args:
            db_path: SQLite database path (warm tier)
            cold_dir: Directory for cold tier files
            hot_max: Max entries in hot cache
            config: Knowledge config section
        """
        self.db_path = db_path
        self.cold_dir = cold_dir
        self.config = config or {}
        self._lock = threading.Lock()

        # Hot tier: LRU cache (entry_id → KnowledgeEntry)
        self._hot: OrderedDict[int, KnowledgeEntry] = OrderedDict()
        self._hot_max = hot_max

        # Setup
        db_path.parent.mkdir(parents=True, exist_ok=True)
        cold_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._load_hot_from_db()

    # ========================================================================
    # Public API
    # ========================================================================

    def add(
        self,
        insight: str,
        category: str,
        tags: List[str],
        confidence: str = "medium",
        conditions: Optional[str] = None,
        evidence: Optional[Dict] = None,
        source_agent: Optional[str] = None,
    ) -> int:
        """Add a new knowledge entry.

        Starts in hot tier. GC moves it to warm over time.

        Returns: Entry ID
        """
        entry = KnowledgeEntry(
            insight=insight,
            category=category,
            tags=tags,
            confidence=confidence,
            conditions=conditions,
            evidence=evidence,
            source_agent=source_agent,
            tier="hot",
        )

        with self._lock:
            entry_id = self._write_warm(entry)
            entry.id = entry_id
            self._put_hot(entry)

        logger.debug(f"Added knowledge entry #{entry_id}: {insight[:50]}...")
        return entry_id

    def get(self, entry_id: int) -> Optional[KnowledgeEntry]:
        """Get a knowledge entry by ID.

        Checks hot first, then warm, then cold.

        Returns: KnowledgeEntry or None
        """
        # Hot tier
        with self._lock:
            if entry_id in self._hot:
                entry = self._hot[entry_id]
                # Move to end (LRU)
                self._hot.move_to_end(entry_id)
                return entry

        # Warm tier
        entry = self._read_warm(entry_id)
        if entry:
            with self._lock:
                self._put_hot(entry)
            self._increment_query_count(entry_id)
            return entry

        # Cold tier
        entry = self._read_cold(entry_id)
        if entry:
            # Promote back to warm if accessed from cold
            with self._lock:
                entry.tier = "warm"
                self._write_warm(entry)
                self._put_hot(entry)
            return entry

        return None

    def query(
        self,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        min_confidence: Optional[str] = None,
        status: str = "active",
        limit: int = 20,
        tier: Optional[str] = None,
    ) -> List[KnowledgeEntry]:
        """Query the knowledge base.

        Args:
            tags: Filter by any matching tag
            category: Filter by category
            min_confidence: Minimum confidence level
            status: Entry status filter
            limit: Max results
            tier: Filter by tier (hot/warm/cold or None for all)

        Returns: List of entries sorted by score (highest first)
        """
        confidence_order = {"low": 0, "medium": 1, "high": 2, "very_high": 3}
        min_conf_level = confidence_order.get(min_confidence or "low", 0)

        # Query warm DB (source of truth for active entries)
        with self._get_conn() as conn:
            # Build query
            conditions = ["status = ?"]
            params: list = [status]

            if category:
                conditions.append("category = ?")
                params.append(category)

            if tier:
                conditions.append("tier = ?")
                params.append(tier)

            where = " AND ".join(conditions)
            rows = conn.execute(
                f"SELECT * FROM knowledge WHERE {where} ORDER BY score DESC LIMIT ?",
                (*params, limit * 2),  # Over-fetch for tag filtering
            ).fetchall()

        entries = [self._row_to_entry(row) for row in rows]

        # Filter by tags (post-filter)
        if tags:
            tag_set = {t.lower() for t in tags}
            entries = [
                e for e in entries
                if tag_set.intersection({t.lower() for t in e.tags})
            ]

        # Filter by confidence
        entries = [
            e for e in entries
            if confidence_order.get(e.confidence, 0) >= min_conf_level
        ]

        # Record query hits on returned entries
        for e in entries[:limit]:
            self._increment_query_count(e.id)

        return entries[:limit]

    def update(self, entry_id: int, **kwargs) -> bool:
        """Update fields on a knowledge entry.

        Args:
            entry_id: Entry to update
            **kwargs: Fields to update (insight, confidence, status, etc.)

        Returns: True if updated
        """
        with self._get_conn() as conn:
            # Build SET clause
            valid_fields = {
                "insight", "category", "tags", "confidence", "status",
                "conditions", "evidence", "last_validated", "score",
            }
            updates = {k: v for k, v in kwargs.items() if k in valid_fields}
            if not updates:
                return False

            set_parts = []
            values = []
            for key, value in updates.items():
                set_parts.append(f"{key} = ?")
                if key in ("tags", "evidence"):
                    values.append(json.dumps(value))
                else:
                    values.append(value)

            values.append(entry_id)
            conn.execute(
                f"UPDATE knowledge SET {', '.join(set_parts)} WHERE id = ?",
                values,
            )

        # Invalidate hot cache
        with self._lock:
            self._hot.pop(entry_id, None)

        return True

    def challenge(self, entry_id: int, counter_evidence: str, severity: str = "moderate"):
        """Record a challenge to a knowledge entry from the critic.

        Args:
            entry_id: Entry being challenged
            counter_evidence: What the critic found
            severity: minor | moderate | major | fatal
        """
        entry = self.get(entry_id)
        if not entry:
            return

        # Downgrade confidence based on severity
        downgrade_map = {
            "minor": None,              # No change, just log
            "moderate": {"very_high": "high", "high": "medium"},
            "major": {"very_high": "medium", "high": "low", "medium": "low"},
            "fatal": {"very_high": "low", "high": "low", "medium": "low", "low": "low"},
        }

        new_conf = downgrade_map.get(severity, {}).get(entry.confidence)
        updates = {"status": "questioned"}
        if new_conf:
            updates["confidence"] = new_conf

        evidence = entry.evidence or {}
        challenges = evidence.get("challenges", [])
        challenges.append({"text": counter_evidence, "severity": severity})
        evidence["challenges"] = challenges
        updates["evidence"] = evidence

        self.update(entry_id, **updates)
        logger.info(f"Knowledge entry #{entry_id} challenged (severity={severity})")

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            by_tier = {}
            for row in conn.execute(
                "SELECT tier, COUNT(*) FROM knowledge GROUP BY tier"
            ).fetchall():
                by_tier[row[0]] = row[1]

            by_confidence = {}
            for row in conn.execute(
                "SELECT confidence, COUNT(*) FROM knowledge GROUP BY confidence"
            ).fetchall():
                by_confidence[row[0]] = row[1]

        # Cold entries (in files)
        cold_count = len(list(self.cold_dir.glob("**/*.json.gz")))
        cold_mb = sum(
            f.stat().st_size for f in self.cold_dir.rglob("*.json.gz")
        ) / (1024 * 1024)

        return {
            "hot_entries": len(self._hot),
            "warm_entries": total,
            "cold_files": cold_count,
            "cold_mb": round(cold_mb, 1),
            "by_tier": by_tier,
            "by_confidence": by_confidence,
        }

    # ========================================================================
    # Internal: Hot Tier
    # ========================================================================

    def _put_hot(self, entry: KnowledgeEntry):
        """Add to hot cache, evict if over limit."""
        if entry.id is None:
            return
        self._hot[entry.id] = entry
        self._hot.move_to_end(entry.id)

        # Evict oldest if over limit
        while len(self._hot) > self._hot_max:
            self._hot.popitem(last=False)  # Remove oldest (LRU)

    def _load_hot_from_db(self):
        """Load most recent/relevant entries into hot cache on startup."""
        try:
            with self._get_conn() as conn:
                rows = conn.execute(
                    """SELECT * FROM knowledge
                       WHERE status = 'active'
                       ORDER BY score DESC, created_at DESC
                       LIMIT ?""",
                    (self._hot_max,),
                ).fetchall()

            with self._lock:
                for row in rows:
                    entry = self._row_to_entry(row)
                    self._hot[entry.id] = entry
        except Exception as e:
            logger.debug(f"Could not load hot cache: {e}")

    # ========================================================================
    # Internal: Warm Tier (SQLite)
    # ========================================================================

    def _init_db(self):
        """Initialize SQLite schema."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    insight         TEXT    NOT NULL,
                    category        TEXT    NOT NULL,
                    tags            TEXT    DEFAULT '[]',
                    confidence      TEXT    DEFAULT 'medium',
                    status          TEXT    DEFAULT 'active',
                    conditions      TEXT,
                    evidence        TEXT    DEFAULT '{}',
                    source_agent    TEXT,
                    tier            TEXT    DEFAULT 'hot',
                    score           REAL    DEFAULT 0.5,
                    created_at      TEXT    NOT NULL,
                    last_validated  TEXT,
                    queries_last_7d INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_status   ON knowledge(status);
                CREATE INDEX IF NOT EXISTS idx_category ON knowledge(category);
                CREATE INDEX IF NOT EXISTS idx_score    ON knowledge(score DESC);
                CREATE INDEX IF NOT EXISTS idx_tier     ON knowledge(tier);

                -- Full-text search
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
                USING fts5(insight, tags, content='knowledge', content_rowid='id');
            """)

    def _write_warm(self, entry: KnowledgeEntry) -> int:
        """Write entry to warm SQLite DB. Returns ID."""
        with self._get_conn() as conn:
            if entry.id:
                conn.execute(
                    """UPDATE knowledge SET
                       insight=?, category=?, tags=?, confidence=?,
                       status=?, conditions=?, evidence=?, tier=?,
                       score=?, last_validated=?
                       WHERE id=?""",
                    (
                        entry.insight, entry.category,
                        json.dumps(entry.tags), entry.confidence,
                        entry.status, entry.conditions,
                        json.dumps(entry.evidence), entry.tier,
                        entry.score, entry.last_validated,
                        entry.id,
                    ),
                )
                return entry.id
            else:
                cursor = conn.execute(
                    """INSERT INTO knowledge
                       (insight, category, tags, confidence, status,
                        conditions, evidence, source_agent, tier, score, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        entry.insight, entry.category,
                        json.dumps(entry.tags), entry.confidence,
                        entry.status, entry.conditions,
                        json.dumps(entry.evidence or {}),
                        entry.source_agent, entry.tier,
                        entry.score, entry.created_at,
                    ),
                )
                return cursor.lastrowid

    def _read_warm(self, entry_id: int) -> Optional[KnowledgeEntry]:
        """Read entry from warm SQLite DB."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge WHERE id=?", (entry_id,)
            ).fetchone()
            return self._row_to_entry(row) if row else None

    def _increment_query_count(self, entry_id: Optional[int]):
        """Increment query counter for an entry (for scoring)."""
        if entry_id is None:
            return
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE knowledge SET queries_last_7d = queries_last_7d + 1 WHERE id=?",
                    (entry_id,),
                )
        except Exception:
            pass

    # ========================================================================
    # Internal: Cold Tier (files)
    # ========================================================================

    def _read_cold(self, entry_id: int) -> Optional[KnowledgeEntry]:
        """Try to read entry from cold storage."""
        import gzip
        # Search cold directory (not ideal — production would have an index)
        for path in self.cold_dir.rglob(f"{entry_id}.json.gz"):
            try:
                with gzip.open(path, "rt") as f:
                    d = json.load(f)
                return KnowledgeEntry.from_dict(d)
            except Exception:
                pass
        return None

    def _write_cold(self, entry: KnowledgeEntry):
        """Compress and write entry to cold storage."""
        import gzip
        from datetime import datetime
        dt = datetime.fromisoformat(entry.created_at.replace("Z", "+00:00"))
        year_month = dt.strftime("%Y/%m")
        cold_path = self.cold_dir / year_month
        cold_path.mkdir(parents=True, exist_ok=True)
        file_path = cold_path / f"{entry.id}.json.gz"

        with gzip.open(file_path, "wt") as f:
            json.dump(entry.to_dict(), f)

    def _get_conn(self) -> sqlite3.Connection:
        """Get SQLite connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _row_to_entry(self, row: sqlite3.Row) -> KnowledgeEntry:
        """Convert SQLite row to KnowledgeEntry."""
        return KnowledgeEntry(
            entry_id=row["id"],
            insight=row["insight"],
            category=row["category"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            confidence=row["confidence"],
            status=row["status"],
            conditions=row["conditions"],
            evidence=json.loads(row["evidence"]) if row["evidence"] else {},
            source_agent=row["source_agent"],
            tier=row["tier"],
            score=row["score"] or 0.5,
            created_at=row["created_at"],
            last_validated=row["last_validated"],
            queries_last_7d=row["queries_last_7d"] or 0,
        )
