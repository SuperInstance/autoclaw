"""Comprehensive error handling and recovery framework for AutoClaw.

Provides:
- Retry logic with exponential backoff
- Circuit breakers for external APIs
- Error classification and handling
- Graceful degradation
- Error notifications
- Audit logging of failures
"""

import logging
import functools
import time
from typing import Optional, Callable, Any, Type
from enum import Enum
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    INFO = "info"           # Recoverable, expected
    WARNING = "warning"     # Degraded function but recoverable
    ERROR = "error"         # Component failure, retry recommended
    CRITICAL = "critical"   # System failure, immediate action needed


class ErrorContext:
    """Context information for errors."""

    def __init__(
        self,
        error: Exception,
        component: str,
        operation: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[dict] = None,
    ):
        self.error = error
        self.component = component
        self.operation = operation
        self.severity = severity
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc)
        self.attempt = 1
        self.last_attempt_time = self.timestamp

    def to_dict(self):
        """Convert to dict for logging."""
        return {
            "component": self.component,
            "operation": self.operation,
            "error_type": type(self.error).__name__,
            "error_message": str(self.error),
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "attempt": self.attempt,
            "context": self.context,
        }


class CircuitBreaker:
    """Circuit breaker for external APIs."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
    ):
        """Initialize circuit breaker.

        Args:
            name: Circuit breaker name
            failure_threshold: Failures before opening circuit
            recovery_timeout_seconds: Seconds before trying recovery
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_seconds)

        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed | open | half_open

    def record_success(self):
        """Record successful operation."""
        self.failures = 0
        self.state = "closed"
        logger.debug(f"Circuit breaker '{self.name}' reset to closed")

    def record_failure(self):
        """Record failed operation."""
        self.failures += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker '{self.name}' opened after {self.failures} failures"
            )

    def is_available(self) -> bool:
        """Check if circuit can attempt operation."""
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if recovery timeout passed
            if self.last_failure_time:
                elapsed = datetime.now(timezone.utc) - self.last_failure_time
                if elapsed > self.recovery_timeout:
                    self.state = "half_open"
                    logger.info(f"Circuit breaker '{self.name}' attempting recovery")
                    return True
            return False

        if self.state == "half_open":
            return True

        return False

    def status(self) -> dict:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state,
            "failures": self.failures,
            "threshold": self.failure_threshold,
            "last_failure": self.last_failure_time.isoformat()
            if self.last_failure_time else None,
        }


def retry(
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    max_delay_seconds: float = 32.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
):
    """Decorator for retry logic with exponential backoff.

    Usage:
        @retry(max_attempts=3, retryable_exceptions=(IOError, TimeoutError))
        def fetch_data():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            delay = base_delay_seconds

            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        logger.info(
                            f"{func.__name__} succeeded on attempt {attempt}/{max_attempts}"
                        )
                    return result

                except retryable_exceptions as e:
                    last_error = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}"
                        )
                        logger.debug(f"Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        delay = min(delay * exponential_base, max_delay_seconds)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )

            raise last_error or Exception(f"Failed after {max_attempts} attempts")

        return wrapper

    return decorator


def handle_error(
    component: str,
    operation: str,
    default_return: Any = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    notify: bool = False,
):
    """Decorator for error handling with graceful degradation.

    Usage:
        @handle_error("knowledge_store", "query", default_return=[])
        def query_knowledge(tags):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)

            except Exception as e:
                error_context = ErrorContext(
                    e,
                    component=component,
                    operation=operation,
                    severity=severity,
                )

                # Log error with context
                log_error(error_context)

                # Optional notification
                if notify:
                    notify_error(error_context)

                # Return default value (graceful degradation)
                logger.debug(
                    f"Returning default value from {component}.{operation}: {default_return}"
                )
                return default_return

        return wrapper

    return decorator


def log_error(error_context: ErrorContext):
    """Log error with full context."""
    error_dict = error_context.to_dict()

    if error_context.severity == ErrorSeverity.INFO:
        logger.info(f"[{error_context.component}] {error_context.operation}: {error_dict}")
    elif error_context.severity == ErrorSeverity.WARNING:
        logger.warning(
            f"[{error_context.component}] {error_context.operation}: {error_dict}"
        )
    elif error_context.severity == ErrorSeverity.ERROR:
        logger.error(
            f"[{error_context.component}] {error_context.operation}: {error_dict}",
            exc_info=error_context.error,
        )
    elif error_context.severity == ErrorSeverity.CRITICAL:
        logger.critical(
            f"[{error_context.component}] {error_context.operation}: {error_dict}",
            exc_info=error_context.error,
        )


def notify_error(error_context: ErrorContext):
    """Notify captain of critical errors."""
    if error_context.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
        try:
            from crew.notifications import NotificationManager

            nm = NotificationManager()
            nm.create(
                title=f"Error in {error_context.component}",
                body=f"{error_context.operation}: {str(error_context.error)[:200]}",
                severity="urgent" if error_context.severity == ErrorSeverity.CRITICAL else "important",
                source="error_handler",
                tags=[error_context.component, error_context.operation],
            )
        except Exception as e:
            logger.warning(f"Could not notify error: {e}")


class ErrorAuditor:
    """Tracks and analyzes errors."""

    def __init__(self):
        self.errors: list[ErrorContext] = []
        self.error_counts: dict[str, int] = {}

    def record(self, error_context: ErrorContext):
        """Record an error."""
        self.errors.append(error_context)
        key = f"{error_context.component}.{error_context.operation}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

    def get_stats(self) -> dict:
        """Get error statistics."""
        return {
            "total_errors": len(self.errors),
            "error_counts": self.error_counts,
            "recent_errors": [e.to_dict() for e in self.errors[-10:]],
        }

    def get_hotspots(self, top_n: int = 5) -> list[tuple]:
        """Get most error-prone operations."""
        sorted_errors = sorted(
            self.error_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_errors[:top_n]


# Global error auditor
_auditor = ErrorAuditor()


def get_error_auditor() -> ErrorAuditor:
    """Get global error auditor."""
    return _auditor
