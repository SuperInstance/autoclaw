"""Health check and monitoring endpoints for AutoClaw.

Provides:
- HTTP health check endpoint (for load balancers)
- Component status checks
- Metrics export (Prometheus-compatible)
- Liveness and readiness probes
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Health status of a single component."""

    def __init__(self, name: str, status: HealthStatus, details: str = "", latency_ms: float = 0):
        self.name = name
        self.status = status
        self.details = details
        self.latency_ms = latency_ms
        self.timestamp = datetime.now(timezone.utc)

    def __str__(self) -> str:
        """String representation includes component name."""
        return f"{self.name}:{self.status.value}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "component": self.name,
            "status": self.status.value,
            "details": self.details,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class HealthChecker:
    """Checks health of all components."""

    def __init__(self):
        """Initialize health checker."""
        self.component_checks = []
        self._register_checks()

    def _register_checks(self):
        """Register health checks for each component."""
        self.component_checks = [
            ("knowledge_store", self._check_knowledge_store),
            ("message_bus", self._check_message_bus),
            ("notifications", self._check_notifications),
            ("handoff_manager", self._check_handoff_manager),
            ("trigger_daemon", self._check_trigger_daemon),
            ("adaptive_scheduler", self._check_adaptive_scheduler),
            ("flowstate_manager", self._check_flowstate_manager),
            ("error_auditor", self._check_error_auditor),
            ("disk_space", self._check_disk_space),
        ]

    def _check_knowledge_store(self) -> Tuple[HealthStatus, str, float]:
        """Check knowledge store."""
        import time
        from crew.knowledge import get_knowledge_store

        start = time.time()
        try:
            store = get_knowledge_store()
            stats = store.stats()

            if stats.get('total_entries', 0) > 450:  # Close to max of 500
                status = HealthStatus.DEGRADED
                details = f"Knowledge store near capacity ({stats['total_entries']}/500)"
            else:
                status = HealthStatus.HEALTHY
                details = f"{stats.get('total_entries', 0)} entries"

            latency = (time.time() - start) * 1000
            return status, details, latency

        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), (time.time() - start) * 1000

    def _check_message_bus(self) -> Tuple[HealthStatus, str, float]:
        """Check message bus."""
        import time
        from crew.messaging.bus import MessageBus

        start = time.time()
        try:
            bus = MessageBus()
            depths = bus.get_queue_depths()

            pending = depths.get('by_status', {}).get('pending', 0)
            failed = depths.get('by_status', {}).get('failed', 0)

            if failed > 100:
                status = HealthStatus.DEGRADED
                details = f"{pending} pending, {failed} failed messages"
            elif pending > 1000:
                status = HealthStatus.DEGRADED
                details = f"{pending} pending messages (queue backing up)"
            else:
                status = HealthStatus.HEALTHY
                details = f"{pending} pending messages"

            latency = (time.time() - start) * 1000
            return status, details, latency

        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), (time.time() - start) * 1000

    def _check_notifications(self) -> Tuple[HealthStatus, str, float]:
        """Check notifications."""
        import time
        from crew.notifications import NotificationManager

        start = time.time()
        try:
            nm = NotificationManager()
            stats = nm.stats()

            unread = stats.get('unread', 0)
            total = stats.get('total_notifications', 0)

            status = HealthStatus.HEALTHY
            details = f"{total} total, {unread} unread"

            latency = (time.time() - start) * 1000
            return status, details, latency

        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), (time.time() - start) * 1000

    def _check_handoff_manager(self) -> Tuple[HealthStatus, str, float]:
        """Check handoff manager."""
        import time
        from crew.handoff import get_handoff_manager

        start = time.time()
        try:
            hm = get_handoff_manager()
            # Just check it's accessible
            gens = hm.list_generations(task_id=1) or []

            status = HealthStatus.HEALTHY
            details = f"Active handoffs"

            latency = (time.time() - start) * 1000
            return status, details, latency

        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), (time.time() - start) * 1000

    def _check_trigger_daemon(self) -> Tuple[HealthStatus, str, float]:
        """Check trigger daemon."""
        import time
        from crew.triggers import TriggerDaemon

        start = time.time()
        try:
            daemon = TriggerDaemon()
            stats = daemon.stats()

            status = HealthStatus.HEALTHY
            details = f"{stats.get('total_triggers', 0)} triggers, {stats.get('enabled', 0)} enabled"

            latency = (time.time() - start) * 1000
            return status, details, latency

        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), (time.time() - start) * 1000

    def _check_adaptive_scheduler(self) -> Tuple[HealthStatus, str, float]:
        """Check adaptive scheduler."""
        import time
        from crew.adaptive import get_adaptive_scheduler

        start = time.time()
        try:
            scheduler = get_adaptive_scheduler()
            stats = scheduler.stats()

            status = HealthStatus.HEALTHY
            details = f"{len(stats.get('directions', []))} tracked directions"

            latency = (time.time() - start) * 1000
            return status, details, latency

        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), (time.time() - start) * 1000

    def _check_flowstate_manager(self) -> Tuple[HealthStatus, str, float]:
        """Check flowstate manager."""
        import time
        from crew.flowstate import get_flowstate_manager

        start = time.time()
        try:
            manager = get_flowstate_manager()
            stats = manager.stats()

            active = len(stats.get('active_sandboxes', []))
            status = HealthStatus.HEALTHY
            details = f"{active} active sandboxes"

            latency = (time.time() - start) * 1000
            return status, details, latency

        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), (time.time() - start) * 1000

    def _check_error_auditor(self) -> Tuple[HealthStatus, str, float]:
        """Check error auditor."""
        import time
        from crew.error_handling import get_error_auditor

        start = time.time()
        try:
            auditor = get_error_auditor()
            stats = auditor.get_stats()

            total_errors = stats.get('total_errors', 0)

            if total_errors > 1000:
                status = HealthStatus.DEGRADED
                details = f"{total_errors} errors recorded (high)"
            else:
                status = HealthStatus.HEALTHY
                details = f"{total_errors} total errors"

            latency = (time.time() - start) * 1000
            return status, details, latency

        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), (time.time() - start) * 1000

    def _check_disk_space(self) -> Tuple[HealthStatus, str, float]:
        """Check disk space availability."""
        import time
        import shutil
        from pathlib import Path

        start = time.time()
        try:
            # Check data directory
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)

            # Get disk usage stats
            usage = shutil.disk_usage(str(data_dir))
            available_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            percent_free = (usage.free / usage.total) * 100

            if available_gb < 1:  # Less than 1GB free
                status = HealthStatus.UNHEALTHY
                details = f"Critical: {available_gb:.1f}GB free ({percent_free:.1f}%)"
            elif available_gb < 5:  # Less than 5GB free
                status = HealthStatus.DEGRADED
                details = f"Low: {available_gb:.1f}GB free ({percent_free:.1f}%)"
            else:
                status = HealthStatus.HEALTHY
                details = f"OK: {available_gb:.1f}GB free ({percent_free:.1f}%)"

            latency = (time.time() - start) * 1000
            return status, details, latency

        except Exception as e:
            return HealthStatus.UNHEALTHY, str(e), (time.time() - start) * 1000

    def check_all(self) -> Tuple[HealthStatus, List[ComponentHealth]]:
        """Run all health checks."""
        results = []
        worst_status = HealthStatus.HEALTHY

        for component_name, check_func in self.component_checks:
            try:
                status, details, latency = check_func()
                result = ComponentHealth(component_name, status, details, latency)
                results.append(result)

                # Track worst status
                if status == HealthStatus.UNHEALTHY:
                    worst_status = HealthStatus.UNHEALTHY
                elif status == HealthStatus.DEGRADED and worst_status != HealthStatus.UNHEALTHY:
                    worst_status = HealthStatus.DEGRADED

            except Exception as e:
                logger.error(f"Error checking {component_name}: {e}")
                result = ComponentHealth(component_name, HealthStatus.UNHEALTHY, str(e), 0)
                results.append(result)
                worst_status = HealthStatus.UNHEALTHY

        return worst_status, results

    def get_status_for_load_balancer(self) -> Tuple[int, str]:
        """Get HTTP status and body for load balancer health check."""
        overall_status, components = self.check_all()

        if overall_status == HealthStatus.HEALTHY:
            return 200, json.dumps({"status": "healthy"})
        elif overall_status == HealthStatus.DEGRADED:
            return 200, json.dumps({"status": "degraded"})
        else:
            return 503, json.dumps({"status": "unhealthy"})

    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status for monitoring."""
        overall_status, components = self.check_all()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall_status.value,
            "components": [c.to_dict() for c in components],
            "healthy_count": sum(1 for c in components if c.status == HealthStatus.HEALTHY),
            "degraded_count": sum(1 for c in components if c.status == HealthStatus.DEGRADED),
            "unhealthy_count": sum(1 for c in components if c.status == HealthStatus.UNHEALTHY),
        }

    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        overall_status, components = self.check_all()

        lines = []

        # Overall status
        status_value = 1 if overall_status == HealthStatus.HEALTHY else (0.5 if overall_status == HealthStatus.DEGRADED else 0)
        lines.append(f"# HELP autoclaw_health_status Overall system health (1=healthy, 0.5=degraded, 0=unhealthy)")
        lines.append(f"# TYPE autoclaw_health_status gauge")
        lines.append(f"autoclaw_health_status {status_value}")

        # Component metrics
        lines.append(f"# HELP autoclaw_component_health Component health status")
        lines.append(f"# TYPE autoclaw_component_health gauge")
        for component in components:
            status_value = 1 if component.status == HealthStatus.HEALTHY else (0.5 if component.status == HealthStatus.DEGRADED else 0)
            lines.append(f'autoclaw_component_health{{component="{component.name}"}} {status_value}')

        # Component latency
        lines.append(f"# HELP autoclaw_component_latency_ms Component check latency in milliseconds")
        lines.append(f"# TYPE autoclaw_component_latency_ms gauge")
        for component in components:
            lines.append(f'autoclaw_component_latency_ms{{component="{component.name}"}} {component.latency_ms}')

        return "\n".join(lines)


# Global health checker instance
_health_checker = None


def get_health_checker() -> HealthChecker:
    """Get or create global health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def health_check_handler(environ, start_response):
    """WSGI handler for health check endpoint."""
    path = environ.get('PATH_INFO', '')

    checker = get_health_checker()

    if path == '/health':
        status_code, body = checker.get_status_for_load_balancer()
        status = f"{status_code} OK" if status_code == 200 else f"{status_code} Service Unavailable"
        response_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
        ]
        start_response(status, response_headers)
        return [body.encode()]

    elif path == '/health/detailed':
        status_data = checker.get_detailed_status()
        body = json.dumps(status_data, indent=2)
        status = "200 OK"
        response_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
        ]
        start_response(status, response_headers)
        return [body.encode()]

    elif path == '/metrics':
        body = checker.get_prometheus_metrics()
        status = "200 OK"
        response_headers = [
            ('Content-Type', 'text/plain'),
            ('Content-Length', str(len(body))),
        ]
        start_response(status, response_headers)
        return [body.encode()]

    else:
        status = "404 Not Found"
        body = json.dumps({"error": "not found"})
        response_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
        ]
        start_response(status, response_headers)
        return [body.encode()]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    )

    checker = get_health_checker()

    print("\n=== DETAILED STATUS ===")
    status_data = checker.get_detailed_status()
    print(json.dumps(status_data, indent=2))

    print("\n=== PROMETHEUS METRICS ===")
    print(checker.get_prometheus_metrics())
