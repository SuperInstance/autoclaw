"""Agent pool manager.

Spawns, monitors, and scales agents based on hardware profile and workload.
The pool is managed by the daemon, which calls:

    pool = AgentPool(config, bus, hardware_profile)
    pool.start()        # Spawn initial agents
    pool.status()       # Check health
    pool.scale_up(role) # Add an agent
    pool.scale_down(role) # Remove idle agent
    pool.stop()         # Graceful shutdown

Agents are threads (not processes) to share the message bus and knowledge store
in the same process. For true parallelism across GPUs, use separate daemon
instances each with their own pool.
"""

import time
import logging
import threading
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Type

from crew.messaging.bus import MessageBus, Message, get_bus
from crew.agents.base import BaseAgent

logger = logging.getLogger(__name__)


# ============================================================================
# Registry of agent classes by role
# ============================================================================

_AGENT_CLASSES: Dict[str, Type[BaseAgent]] = {}


def register_agent_class(role: str, cls: Type[BaseAgent]):
    """Register an agent class for a role.

    Args:
        role: Role string (e.g., 'researcher')
        cls: Agent class to use for this role
    """
    _AGENT_CLASSES[role] = cls


def get_agent_class(role: str) -> Optional[Type[BaseAgent]]:
    """Get the agent class for a role."""
    return _AGENT_CLASSES.get(role)


# ============================================================================
# AgentPool
# ============================================================================


class AgentPool:
    """Manages a pool of agents.

    Responsible for:
    - Spawning agents on startup (based on hardware profile)
    - Health monitoring via heartbeats
    - Auto-scaling based on message queue depth
    - Graceful shutdown
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        bus: Optional[MessageBus] = None,
        hardware_profile: Optional[str] = None,
    ):
        """Initialize agent pool.

        Args:
            config: Pool configuration (agent_pool section from main config)
            bus: Shared message bus
            hardware_profile: Hardware profile name (e.g., 'laptop_gpu')
        """
        self.config = config or {}
        self.bus = bus or get_bus()
        self.hardware_profile = hardware_profile or "cpu_only"
        self.agents: Dict[str, BaseAgent] = {}   # agent_id → agent
        self._counters: Dict[str, int] = {}      # role → next instance number
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown = False

        # Subscribe to heartbeats to track agent health
        self.bus.subscribe("heartbeat", self._on_heartbeat)
        self._last_heartbeat: Dict[str, datetime] = {}

    # ========================================================================
    # Startup / Shutdown
    # ========================================================================

    def start(self):
        """Spawn initial agents based on hardware profile composition."""
        composition = self._get_composition()

        logger.info(
            f"Starting agent pool (profile={self.hardware_profile}, "
            f"composition={composition})"
        )

        for role, count in composition.items():
            for _ in range(count):
                self.spawn(role)

        # Start health monitor
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="agent-pool-monitor",
            daemon=True,
        )
        self._monitor_thread.start()

        logger.info(f"Agent pool started: {len(self.agents)} agents")

    def stop(self):
        """Gracefully stop all agents."""
        logger.info("Stopping agent pool...")
        self._shutdown = True

        with self._lock:
            for agent_id, agent in self.agents.items():
                try:
                    agent.stop()
                except Exception as e:
                    logger.warning(f"Error stopping agent {agent_id}: {e}")

        logger.info("Agent pool stopped")

    # ========================================================================
    # Agent Management
    # ========================================================================

    def spawn(self, role: str, config_override: Optional[Dict] = None) -> Optional[str]:
        """Spawn a new agent of the given role.

        Args:
            role: Agent role (e.g., 'researcher')
            config_override: Override default agent config

        Returns: Agent ID of spawned agent, or None if failed
        """
        cls = get_agent_class(role)
        if cls is None:
            logger.warning(f"No agent class registered for role '{role}'")
            return None

        # Generate unique ID
        with self._lock:
            num = self._counters.get(role, 0) + 1
            self._counters[role] = num
            agent_id = f"{role}_{num}"

        # Build agent config
        agent_config = self._get_agent_config(role)
        if config_override:
            agent_config.update(config_override)

        try:
            agent = cls(agent_id=agent_id, bus=self.bus, config=agent_config)
            with self._lock:
                self.agents[agent_id] = agent
            agent.start()
            logger.info(f"Spawned agent {agent_id}")
            return agent_id
        except Exception as e:
            logger.error(f"Failed to spawn {role} agent: {e}", exc_info=True)
            return None

    def terminate(self, agent_id: str):
        """Stop and remove a specific agent.

        Args:
            agent_id: Agent to terminate
        """
        with self._lock:
            agent = self.agents.pop(agent_id, None)

        if agent:
            agent.stop()
            logger.info(f"Terminated agent {agent_id}")
        else:
            logger.warning(f"Agent {agent_id} not found")

    def scale_up(self, role: str) -> Optional[str]:
        """Add one more agent for the given role.

        Returns: New agent ID or None
        """
        max_per_role = self.config.get("scaling", {}).get("max_agents_per_role", 4)
        current = self.agents_by_role(role)

        if len(current) >= max_per_role:
            logger.info(f"Cannot scale up {role}: already at max ({max_per_role})")
            return None

        logger.info(f"Scaling up: spawning additional {role} agent")
        return self.spawn(role)

    def scale_down(self, role: str) -> bool:
        """Remove the most idle agent for the given role.

        Returns: True if removed, False if none available
        """
        candidates = [
            (agent_id, agent)
            for agent_id, agent in self.agents.items()
            if agent.ROLE == role and agent.status == "idle"
        ]

        if not candidates:
            return False

        # Remove the one that has been idle longest (most recently heartbeat)
        agent_id, _ = candidates[0]
        self.terminate(agent_id)
        logger.info(f"Scaled down: removed {agent_id}")
        return True

    # ========================================================================
    # Status and Monitoring
    # ========================================================================

    def status(self) -> Dict[str, Any]:
        """Get pool status summary.

        Returns: Dict with agent count, health, queue depth
        """
        with self._lock:
            agents_info = [
                {
                    "id": agent_id,
                    "role": agent.ROLE,
                    "status": agent.status,
                    "messages_processed": agent.messages_processed,
                    "errors": agent.errors_count,
                    "healthy": self._is_healthy(agent_id),
                }
                for agent_id, agent in self.agents.items()
            ]

        queue_depths = self.bus.get_queue_depths()

        return {
            "total_agents": len(agents_info),
            "agents": agents_info,
            "queue": queue_depths,
            "hardware_profile": self.hardware_profile,
        }

    def agents_by_role(self, role: str) -> List[str]:
        """Get list of agent IDs for a role."""
        with self._lock:
            return [
                agent_id
                for agent_id, agent in self.agents.items()
                if agent.ROLE == role
            ]

    def _is_healthy(self, agent_id: str) -> bool:
        """Check if an agent is sending heartbeats."""
        last = self._last_heartbeat.get(agent_id)
        if last is None:
            return True  # Never heard from → assume healthy (just started)
        max_missed = self.config.get("health", {}).get("max_missed_heartbeats", 3)
        interval = self.config.get("health", {}).get("heartbeat_interval_seconds", 30)
        threshold = timedelta(seconds=max_missed * interval)
        return (datetime.now(timezone.utc) - last) < threshold

    def _on_heartbeat(self, message: Message):
        """Update heartbeat tracking when agent sends heartbeat."""
        self._last_heartbeat[message.from_agent] = datetime.now(timezone.utc)

    def _monitor_loop(self):
        """Background thread: check health and auto-scale."""
        check_interval = 60

        while not self._shutdown:
            try:
                self._health_check()
                if self.config.get("scaling", {}).get("auto_scale", False):
                    self._auto_scale()
            except Exception as e:
                logger.error(f"Pool monitor error: {e}", exc_info=True)

            time.sleep(check_interval)

    def _health_check(self):
        """Restart unhealthy agents."""
        with self._lock:
            unhealthy = [
                (agent_id, agent.ROLE)
                for agent_id, agent in self.agents.items()
                if not self._is_healthy(agent_id)
            ]

        for agent_id, role in unhealthy:
            backoff = self.config.get("health", {}).get("restart_backoff_seconds", 30)
            logger.warning(f"Agent {agent_id} is unhealthy, restarting...")
            self.terminate(agent_id)
            time.sleep(backoff)
            self.spawn(role)

    def _auto_scale(self):
        """Add/remove agents based on queue depth."""
        scaling = self.config.get("scaling", {})
        scale_up_threshold = scaling.get("scale_up_threshold", 10)
        scale_down_idle = scaling.get("scale_down_idle_minutes", 30)

        # Scale up if queue deep
        pending = self.bus.get_pending_count()
        if pending > scale_up_threshold:
            # Find the busiest role (by pending messages in its queue)
            # Simple heuristic: scale up researchers first if research requests pending
            for role in ["researcher", "teacher", "distiller", "critic"]:
                if self.agents_by_role(role):
                    new_id = self.scale_up(role)
                    if new_id:
                        logger.info(
                            f"Auto-scaled up {role} due to queue depth {pending}"
                        )
                        break

    # ========================================================================
    # Config Helpers
    # ========================================================================

    def _get_composition(self) -> Dict[str, int]:
        """Get agent composition from hardware profile or config override."""
        # Start with hardware profile defaults
        profile_defaults = {
            "nano":         {"researcher": 1, "teacher": 1, "critic": 0, "distiller": 0},
            "jetson_orin":  {"researcher": 1, "teacher": 2, "critic": 1, "distiller": 1},
            "laptop_gpu":   {"researcher": 1, "teacher": 2, "critic": 1, "distiller": 1},
            "workstation":  {"researcher": 2, "teacher": 3, "critic": 1, "distiller": 2},
            "multi_gpu":    {"researcher": 4, "teacher": 6, "critic": 2, "distiller": 3},
            "cloud":        {"researcher": 2, "teacher": 4, "critic": 1, "distiller": 2},
            "cpu_only":     {"researcher": 1, "teacher": 1, "critic": 0, "distiller": 0},
        }

        composition = profile_defaults.get(
            self.hardware_profile,
            {"researcher": 1, "teacher": 1, "critic": 0, "distiller": 0},
        )

        # Apply config overrides
        config_composition = self.config.get("composition", {})
        composition.update(config_composition)

        # Only spawn roles that have registered classes
        composition = {
            role: count
            for role, count in composition.items()
            if count > 0 and get_agent_class(role) is not None
        }

        return composition

    def _get_agent_config(self, role: str) -> Dict[str, Any]:
        """Build config dict for a specific role's agent."""
        base = self.config.get("agent_defaults", {})
        role_overrides = self.config.get(f"{role}_config", {})
        merged = {**base, **role_overrides}
        return merged

    def save_registry(self):
        """Write agent registry to disk."""
        registry = {
            "agents": [
                {
                    "id": agent_id,
                    "role": agent.ROLE,
                    "status": agent.status,
                    "capabilities": agent.get_capabilities(),
                }
                for agent_id, agent in self.agents.items()
            ],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        registry_path = Path("data/agents/registry.yaml")
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            registry_path.write_text(yaml.dump(registry, default_flow_style=False))
        except Exception as e:
            logger.debug(f"Could not save agent registry: {e}")
