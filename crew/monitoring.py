"""Advanced monitoring and metrics for AutoClaw.

Provides:
- System metrics (memory, CPU, disk)
- Component metrics (message throughput, latency)
- Custom metrics export
- Alerting triggers
- Metric storage and aggregation
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Single metric data point."""
    name: str
    value: float
    timestamp: str
    labels: Dict[str, str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Alert:
    """Alert definition."""
    name: str
    condition: str  # "greater_than", "less_than", "equals"
    threshold: float
    metric_name: str
    severity: str  # "info", "warning", "critical"
    enabled: bool = True
    triggered: bool = False


class MetricBuffer:
    """Buffer for storing metrics."""

    def __init__(self, max_size: int = 1000):
        """Initialize metric buffer."""
        self.max_size = max_size
        self.metrics: deque = deque(maxlen=max_size)

    def add(self, metric: Metric):
        """Add metric to buffer."""
        self.metrics.append(metric)

    def get_last(self, name: str, minutes: int = 5) -> List[Metric]:
        """Get metrics from last N minutes."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        result = []

        for metric in self.metrics:
            if metric.name != name:
                continue

            metric_time = datetime.fromisoformat(metric.timestamp)
            if metric_time >= cutoff:
                result.append(metric)

        return result

    def get_stats(self, name: str, minutes: int = 5) -> Dict[str, float]:
        """Get statistics for metric."""
        metrics = self.get_last(name, minutes)

        if not metrics:
            return {}

        values = [m.value for m in metrics]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1] if values else 0,
        }

    def clear(self):
        """Clear all metrics."""
        self.metrics.clear()


class MetricsCollector:
    """Collect system and application metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.buffer = MetricBuffer(max_size=5000)
        self.alerts: Dict[str, Alert] = {}

    def record(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a metric."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            labels=labels or {}
        )
        self.buffer.add(metric)

    def get_memory_usage(self) -> float:
        """Get process memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            logger.warning("psutil not available for memory monitoring")
            return 0

    def get_cpu_usage(self) -> float:
        """Get process CPU usage percentage."""
        try:
            import psutil
            return psutil.Process().cpu_percent(interval=0.1)
        except ImportError:
            logger.warning("psutil not available for CPU monitoring")
            return 0

    def get_disk_usage(self, path: str = "data") -> Dict[str, float]:
        """Get disk usage for path."""
        try:
            import shutil
            stat = shutil.disk_usage(path)
            return {
                "used_gb": stat.used / 1024 / 1024 / 1024,
                "free_gb": stat.free / 1024 / 1024 / 1024,
                "total_gb": stat.total / 1024 / 1024 / 1024,
                "percent": (stat.used / stat.total) * 100,
            }
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return {}

    def collect_system_metrics(self):
        """Collect all system metrics."""
        # Memory
        memory_mb = self.get_memory_usage()
        self.record("system.memory_mb", memory_mb)

        # CPU
        cpu_percent = self.get_cpu_usage()
        self.record("system.cpu_percent", cpu_percent)

        # Disk
        disk = self.get_disk_usage()
        if disk:
            self.record("system.disk_used_gb", disk.get("used_gb", 0))
            self.record("system.disk_free_gb", disk.get("free_gb", 0))
            self.record("system.disk_percent", disk.get("percent", 0))

    def collect_component_metrics(self):
        """Collect component-level metrics."""
        try:
            from crew.knowledge import get_knowledge_store
            from crew.messaging.bus import MessageBus
            from crew.daemon_integration import get_daemon_integration

            # Knowledge store
            store = get_knowledge_store()
            stats = store.stats()
            self.record("component.knowledge_entries", stats.get("total_entries", 0))

            # Message bus
            bus = MessageBus()
            depths = bus.get_queue_depths()
            pending = depths.get("by_status", {}).get("pending", 0)
            self.record("component.messages_pending", pending)

            # Daemon integration
            di = get_daemon_integration()
            di_stats = di.get_stats()
            self.record("component.notifications_total", di_stats.get("total_notifications", 0))

        except Exception as e:
            logger.error(f"Error collecting component metrics: {e}")

    def register_alert(self, alert: Alert):
        """Register an alert condition."""
        self.alerts[alert.name] = alert

    def check_alerts(self) -> List[str]:
        """Check all alerts and return triggered ones."""
        triggered = []

        for alert_name, alert in self.alerts.items():
            if not alert.enabled:
                continue

            stats = self.buffer.get_stats(alert.metric_name, minutes=1)
            if not stats:
                continue

            value = stats.get("latest", 0)
            should_trigger = False

            if alert.condition == "greater_than" and value > alert.threshold:
                should_trigger = True
            elif alert.condition == "less_than" and value < alert.threshold:
                should_trigger = True
            elif alert.condition == "equals" and value == alert.threshold:
                should_trigger = True

            if should_trigger and not alert.triggered:
                logger.warning(f"ALERT: {alert_name} (severity={alert.severity}): {alert.metric_name}={value}")
                triggered.append(alert_name)
                alert.triggered = True

            elif not should_trigger and alert.triggered:
                logger.info(f"ALERT CLEARED: {alert_name}")
                alert.triggered = False

        return triggered

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Get unique metric names
        metric_names = set()
        for metric in self.buffer.metrics:
            metric_names.add(metric.name)

        # Export each metric type
        for metric_name in sorted(metric_names):
            stats = self.buffer.get_stats(metric_name, minutes=60)

            if not stats:
                continue

            # Help text
            lines.append(f"# HELP autoclaw_{metric_name} {metric_name}")
            lines.append(f"# TYPE autoclaw_{metric_name} gauge")

            # Current value
            lines.append(f"autoclaw_{metric_name} {stats.get('latest', 0)}")

            # Statistics
            if len(lines) > 3:  # Only if we have stats
                lines.append(f"autoclaw_{metric_name}_min {stats.get('min', 0)}")
                lines.append(f"autoclaw_{metric_name}_max {stats.get('max', 0)}")
                lines.append(f"autoclaw_{metric_name}_avg {stats.get('avg', 0)}")

        return "\n".join(lines)

    def export_json(self) -> str:
        """Export metrics as JSON."""
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": [m.to_dict() for m in self.buffer.metrics],
        }
        return json.dumps(data, indent=2)

    def get_report(self) -> Dict[str, Any]:
        """Get metrics report."""
        metric_names = set()
        for metric in self.buffer.metrics:
            metric_names.add(metric.name)

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {},
            "alerts": {},
        }

        # Metrics
        for metric_name in sorted(metric_names):
            stats = self.buffer.get_stats(metric_name, minutes=60)
            if stats:
                report["metrics"][metric_name] = stats

        # Alerts
        for alert_name, alert in self.alerts.items():
            report["alerts"][alert_name] = {
                "enabled": alert.enabled,
                "triggered": alert.triggered,
                "severity": alert.severity,
            }

        return report


class PerformanceTracker:
    """Track performance metrics for specific operations."""

    def __init__(self):
        """Initialize tracker."""
        self.durations: Dict[str, List[float]] = {}

    def start(self, operation: str) -> float:
        """Start timing an operation."""
        return time.time()

    def end(self, operation: str, start_time: float):
        """End timing an operation."""
        duration = (time.time() - start_time) * 1000  # milliseconds

        if operation not in self.durations:
            self.durations[operation] = deque(maxlen=100)

        self.durations[operation].append(duration)

        # Log slow operations
        if duration > 1000:  # > 1 second
            logger.warning(f"Slow operation: {operation} took {duration:.1f}ms")

    def get_report(self) -> Dict[str, Dict[str, float]]:
        """Get performance report."""
        report = {}

        for operation, durations in self.durations.items():
            if not durations:
                continue

            durations_list = list(durations)
            report[operation] = {
                "count": len(durations_list),
                "min_ms": min(durations_list),
                "max_ms": max(durations_list),
                "avg_ms": sum(durations_list) / len(durations_list),
                "p95_ms": sorted(durations_list)[int(len(durations_list) * 0.95)],
            }

        return report


# Global metrics collector
_metrics_collector = None
_performance_tracker = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
        # Register default alerts
        _metrics_collector.register_alert(Alert(
            name="high_memory",
            condition="greater_than",
            threshold=1000,  # 1GB
            metric_name="system.memory_mb",
            severity="warning"
        ))
        _metrics_collector.register_alert(Alert(
            name="high_cpu",
            condition="greater_than",
            threshold=80,  # 80%
            metric_name="system.cpu_percent",
            severity="warning"
        ))
        _metrics_collector.register_alert(Alert(
            name="disk_full",
            condition="greater_than",
            threshold=90,  # 90%
            metric_name="system.disk_percent",
            severity="critical"
        ))
        _metrics_collector.register_alert(Alert(
            name="message_queue_backed_up",
            condition="greater_than",
            threshold=1000,
            metric_name="component.messages_pending",
            severity="warning"
        ))
    return _metrics_collector


def get_performance_tracker() -> PerformanceTracker:
    """Get global performance tracker."""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    return _performance_tracker
