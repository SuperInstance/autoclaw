"""Base agent class for all crew agents.

Every agent inherits from BaseAgent. It provides:
  - Lifecycle management (start, stop, pause, heartbeat)
  - Message bus integration (receive, publish, reply)
  - Resource checking (memory, CF credits, rate limits)
  - State persistence (data/agents/{id}/state.yaml)
  - Logging with agent context

Subclasses implement:
  - process_message(message) → handle a specific message type
  - get_capabilities() → list of what this agent can do
  - idle_work() → what to do when no messages are pending
"""

import time
import threading
import logging
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from crew.messaging.bus import MessageBus, Message, get_bus

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all swarm agents.

    Lifecycle:
        1. __init__ — load config, set up logging
        2. start() — begin main loop in thread
        3. _main_loop() — receive messages, call process_message
        4. stop() — graceful shutdown

    Subclass interface:
        process_message(msg) — implement to handle messages
        get_capabilities() — return list of capability strings
        idle_work() — called when no messages pending (optional)
    """

    # Subclasses set these
    ROLE: str = "base"           # e.g., 'researcher', 'teacher'
    DEFAULT_PRIORITY: int = 5

    def __init__(
        self,
        agent_id: str,
        bus: Optional[MessageBus] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize agent.

        Args:
            agent_id: Unique identifier (e.g., 'researcher_1')
            bus: Message bus (uses global singleton if not provided)
            config: Agent configuration dict
        """
        self.agent_id = agent_id
        self.bus = bus or get_bus()
        self.config = config or {}
        self.status = "idle"
        self.shutdown_requested = False
        self.current_message: Optional[Message] = None
        self.messages_processed = 0
        self.errors_count = 0
        self.started_at: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None

        # State directory
        self.state_dir = Path(f"data/agents/{self.agent_id}")
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Resource limits from config
        limits = self.config.get("resource_limits", {})
        self.max_memory_mb = limits.get("max_memory_mb", 512)
        self.cf_budget_pct = limits.get("cf_budget_pct", 0.25)
        self.max_llm_calls_per_hour = limits.get("max_llm_calls_per_hour", 100)
        self.max_web_searches_per_hour = limits.get("max_web_searches_per_hour", 30)

        # Rate tracking
        self._llm_calls_this_hour = 0
        self._web_searches_this_hour = 0
        self._rate_reset_at = datetime.now(timezone.utc)

        # Setup logging
        self.logger = logging.getLogger(f"crew.agents.{self.agent_id}")

    # ========================================================================
    # Abstract Interface (subclasses implement these)
    # ========================================================================

    @abstractmethod
    def process_message(self, message: Message) -> Optional[Message]:
        """Process a received message.

        Args:
            message: The message to process

        Returns:
            Optional reply message (will be published to bus)
        """
        ...

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of capability strings this agent has.

        Example: ['web_search', 'llm_query', 'qa_generation']
        """
        ...

    def idle_work(self):
        """Called when no messages are pending.

        Override to do something useful when idle.
        Default: sleep briefly.
        """
        time.sleep(5)

    # ========================================================================
    # Lifecycle
    # ========================================================================

    def start(self):
        """Start the agent in a background thread."""
        self.started_at = datetime.now(timezone.utc)
        self.status = "idle"

        thread = threading.Thread(
            target=self._main_loop,
            name=f"agent-{self.agent_id}",
            daemon=True,
        )
        thread.start()

        self.logger.info(
            f"Agent {self.agent_id} started "
            f"(role={self.ROLE}, capabilities={self.get_capabilities()})"
        )
        self._save_state()

    def stop(self):
        """Request graceful shutdown."""
        self.logger.info(f"Agent {self.agent_id} stopping...")
        self.shutdown_requested = True
        self.status = "stopped"
        self._save_state()

    def _main_loop(self):
        """Main agent loop: receive messages, process, repeat."""
        heartbeat_interval = self.config.get("heartbeat_interval_seconds", 30)
        poll_interval = self.config.get("poll_interval_seconds", 2)

        while not self.shutdown_requested:
            try:
                # Reset rate limits hourly
                self._reset_rate_limits_if_needed()

                # Receive pending messages for this agent
                messages = self.bus.receive(
                    agent_id=self.agent_id,
                    roles=[self.ROLE],
                    limit=5,
                )

                if messages:
                    for msg in messages:
                        if self.shutdown_requested:
                            break
                        self._handle_message(msg)
                else:
                    # No messages — do idle work
                    self.status = "idle"
                    self.idle_work()

                # Send heartbeat periodically
                now = datetime.now(timezone.utc)
                if (
                    self.last_heartbeat is None
                    or (now - self.last_heartbeat).total_seconds() > heartbeat_interval
                ):
                    self._send_heartbeat()
                    self.last_heartbeat = now

                time.sleep(poll_interval)

            except Exception as e:
                self.errors_count += 1
                self.logger.error(f"Agent loop error: {e}", exc_info=True)
                time.sleep(5)  # Brief pause before retrying

    def _handle_message(self, message: Message):
        """Handle a single message with error isolation."""
        self.current_message = message
        self.status = "working"
        self.bus.mark_processing(message.id)

        self.logger.debug(
            f"Processing message #{message.id} type={message.type} "
            f"from={message.from_agent}"
        )

        try:
            reply = self.process_message(message)
            self.bus.complete(message.id)
            self.messages_processed += 1

            # Publish reply if one was returned
            if reply:
                reply.parent_message_id = message.id
                if not reply.from_agent:
                    reply.from_agent = self.agent_id
                self.bus.publish(reply)

        except Exception as e:
            self.errors_count += 1
            error_msg = f"{type(e).__name__}: {e}"
            self.bus.fail(message.id, error_msg)
            self.logger.error(
                f"Error processing message #{message.id}: {error_msg}",
                exc_info=True,
            )

            # Publish error notification to daemon
            self.bus.publish(Message(
                from_agent=self.agent_id,
                to_agent="daemon",
                type="error",
                priority=3,
                payload={
                    "failed_message_id": message.id,
                    "error": error_msg,
                    "agent_id": self.agent_id,
                },
            ))

        finally:
            self.current_message = None
            self.status = "idle"
            self._save_state()

    # ========================================================================
    # Message Helpers
    # ========================================================================

    def publish(
        self,
        to_agent: str,
        msg_type: str,
        payload: Dict[str, Any],
        priority: Optional[int] = None,
        parent_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        expires_in_hours: Optional[float] = None,
    ) -> int:
        """Convenience wrapper for publishing messages.

        Returns: Published message ID
        """
        return self.bus.publish(Message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            type=msg_type,
            payload=payload,
            priority=priority or self.DEFAULT_PRIORITY,
            parent_message_id=parent_id,
            tags=tags or [],
            expires_in_hours=expires_in_hours,
        ))

    def reply(
        self,
        original: Message,
        msg_type: str,
        payload: Dict[str, Any],
        priority: Optional[int] = None,
    ) -> int:
        """Publish a reply to a message.

        Routes reply back to original sender.
        """
        return self.publish(
            to_agent=original.from_agent,
            msg_type=msg_type,
            payload=payload,
            priority=priority or original.priority,
            parent_id=original.id,
            tags=original.tags,
        )

    def request_research(
        self,
        topic: str,
        context: Optional[str] = None,
        target_format: str = "structured",
        linked_task_id: Optional[int] = None,
        priority: int = 5,
    ) -> int:
        """Request research from any available researcher agent.

        Returns: Message ID for tracking
        """
        return self.publish(
            to_agent="any_researcher",
            msg_type="task_request",
            payload={
                "description": f"Research: {topic}",
                "topic": topic,
                "context": context,
                "target_format": target_format,
                "linked_task_id": linked_task_id,
            },
            priority=priority,
            tags=[topic.replace(" ", "-")[:30]],
            expires_in_hours=24.0,
        )

    def request_training_data(
        self,
        topic: str,
        source_text: str,
        n_examples: int = 20,
        format_type: str = "qa_pair",
        priority: int = 6,
    ) -> int:
        """Request training data generation from any teacher agent.

        Returns: Message ID for tracking
        """
        return self.publish(
            to_agent="any_teacher",
            msg_type="task_request",
            payload={
                "description": f"Generate {n_examples} {format_type} examples for: {topic}",
                "topic": topic,
                "source_text": source_text,
                "n_examples": n_examples,
                "format_type": format_type,
            },
            priority=priority,
            tags=[topic.replace(" ", "-")[:30]],
            expires_in_hours=24.0,
        )

    def submit_knowledge(
        self,
        insight: str,
        category: str,
        tags: List[str],
        confidence: str = "medium",
        conditions: Optional[str] = None,
        evidence: Optional[Dict] = None,
    ) -> int:
        """Submit a new knowledge entry to the knowledge store.

        Returns: Message ID
        """
        return self.publish(
            to_agent="daemon",
            msg_type="knowledge",
            payload={
                "entry": {
                    "insight": insight,
                    "category": category,
                    "tags": tags,
                    "confidence": confidence,
                    "conditions": conditions,
                    "evidence": evidence or {},
                    "source_agent": self.agent_id,
                },
                "tier": "hot",
            },
            priority=7,  # Knowledge is important but not urgent
            tags=tags,
        )

    # ========================================================================
    # Resource Checking
    # ========================================================================

    def check_rate_limit(self, resource: str) -> bool:
        """Check if we're within rate limits for a resource.

        Args:
            resource: 'llm_call' or 'web_search'

        Returns: True if OK to proceed, False if rate limited
        """
        if resource == "llm_call":
            if self._llm_calls_this_hour >= self.max_llm_calls_per_hour:
                self.logger.warning(
                    f"LLM rate limit reached ({self._llm_calls_this_hour}/"
                    f"{self.max_llm_calls_per_hour})"
                )
                return False
        elif resource == "web_search":
            if self._web_searches_this_hour >= self.max_web_searches_per_hour:
                self.logger.warning(
                    f"Web search rate limit reached ({self._web_searches_this_hour}/"
                    f"{self.max_web_searches_per_hour})"
                )
                return False
        return True

    def consume_rate(self, resource: str, count: int = 1):
        """Record consumption of a rate-limited resource."""
        if resource == "llm_call":
            self._llm_calls_this_hour += count
        elif resource == "web_search":
            self._web_searches_this_hour += count

    def _reset_rate_limits_if_needed(self):
        """Reset hourly rate limits if an hour has passed."""
        now = datetime.now(timezone.utc)
        if (now - self._rate_reset_at).total_seconds() >= 3600:
            self._llm_calls_this_hour = 0
            self._web_searches_this_hour = 0
            self._rate_reset_at = now

    # ========================================================================
    # Heartbeat and State
    # ========================================================================

    def _send_heartbeat(self):
        """Publish heartbeat to daemon."""
        self.bus.publish(Message(
            from_agent=self.agent_id,
            to_agent="daemon",
            type="heartbeat",
            priority=9,  # Low priority
            payload={
                "status": self.status,
                "messages_processed": self.messages_processed,
                "errors_count": self.errors_count,
                "capabilities": self.get_capabilities(),
                "current_task": (
                    self.current_message.payload.get("description")
                    if self.current_message else None
                ),
            },
            expires_in_hours=1.0,  # Heartbeats expire quickly
        ))

    def _save_state(self):
        """Persist agent state to disk."""
        state = {
            "agent_id": self.agent_id,
            "role": self.ROLE,
            "status": self.status,
            "messages_processed": self.messages_processed,
            "errors_count": self.errors_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
            "capabilities": self.get_capabilities(),
        }

        state_file = self.state_dir / "state.yaml"
        try:
            state_file.write_text(yaml.dump(state, default_flow_style=False))
        except Exception as e:
            self.logger.debug(f"Could not save agent state: {e}")
