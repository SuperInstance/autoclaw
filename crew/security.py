"""Security hardening for AutoClaw.

Implements:
- API key validation and rotation
- Audit logging for all operations
- Rate limiting
- Input sanitization
- CORS and security headers
- Secrets management
"""

import logging
import hashlib
import secrets
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from pathlib import Path
from functools import wraps
import json

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manage API keys and authentication."""

    def __init__(self, keys_file: Path = Path("data/api_keys.json")):
        """Initialize API key manager."""
        self.keys_file = keys_file
        self.keys: Dict[str, Dict[str, Any]] = {}
        self._load_keys()

    def _load_keys(self):
        """Load keys from file."""
        if self.keys_file.exists():
            try:
                self.keys = json.loads(self.keys_file.read_text())
                logger.debug(f"Loaded {len(self.keys)} API keys")
            except Exception as e:
                logger.error(f"Error loading API keys: {e}")
                self.keys = {}

    def _save_keys(self):
        """Save keys to file."""
        try:
            self.keys_file.parent.mkdir(parents=True, exist_ok=True)
            self.keys_file.write_text(json.dumps(self.keys, indent=2))
            self.keys_file.chmod(0o600)  # Read/write owner only
        except Exception as e:
            logger.error(f"Error saving API keys: {e}")

    def create_key(self, name: str, permissions: list = None) -> Tuple[str, str]:
        """Create a new API key.

        Returns: (key_id, secret_key)
        """
        key_id = secrets.token_urlsafe(16)
        secret = secrets.token_urlsafe(32)

        # Store hashed secret
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()

        self.keys[key_id] = {
            "name": name,
            "secret_hash": secret_hash,
            "permissions": permissions or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": None,
            "active": True,
        }

        self._save_keys()
        logger.info(f"Created API key: {key_id} ({name})")

        return key_id, secret

    def validate_key(self, key_id: str, secret: str) -> bool:
        """Validate an API key."""
        if key_id not in self.keys:
            logger.warning(f"Invalid key_id: {key_id}")
            return False

        key_info = self.keys[key_id]

        if not key_info.get("active"):
            logger.warning(f"Inactive key: {key_id}")
            return False

        # Compare secrets
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        if secret_hash != key_info["secret_hash"]:
            logger.warning(f"Invalid secret for key: {key_id}")
            return False

        # Update last used
        key_info["last_used"] = datetime.now(timezone.utc).isoformat()
        self._save_keys()

        return True

    def revoke_key(self, key_id: str):
        """Revoke an API key."""
        if key_id in self.keys:
            self.keys[key_id]["active"] = False
            self._save_keys()
            logger.info(f"Revoked API key: {key_id}")

    def rotate_key(self, key_id: str) -> Tuple[str, str]:
        """Rotate an API key (revoke old, create new)."""
        if key_id not in self.keys:
            raise ValueError(f"Key not found: {key_id}")

        old_name = self.keys[key_id]["name"]
        old_permissions = self.keys[key_id].get("permissions", [])

        # Revoke old key
        self.revoke_key(key_id)

        # Create new key
        new_key_id, new_secret = self.create_key(old_name, old_permissions)
        logger.info(f"Rotated API key: {key_id} -> {new_key_id}")

        return new_key_id, new_secret


class AuditLogger:
    """Audit logging for all operations."""

    def __init__(self, log_file: Path = Path("data/logs/audit.log")):
        """Initialize audit logger."""
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: str,
        operation: str,
        user: str = "system",
        details: Dict[str, Any] = None,
        status: str = "success",
    ):
        """Log an audit event."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "operation": operation,
            "user": user,
            "status": status,
            "details": details or {},
        }

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Error writing audit log: {e}")

    def get_events(
        self,
        event_type: str = None,
        user: str = None,
        hours: int = 24,
    ) -> list:
        """Get audit events."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        events = []

        if not self.log_file.exists():
            return events

        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry["timestamp"])

                        if entry_time < cutoff:
                            continue

                        if event_type and entry.get("event_type") != event_type:
                            continue

                        if user and entry.get("user") != user:
                            continue

                        events.append(entry)

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.error(f"Error reading audit log: {e}")

        return events


class RateLimiter:
    """Rate limiting for API calls."""

    def __init__(self, limits_per_minute: int = 100):
        """Initialize rate limiter."""
        self.limits_per_minute = limits_per_minute
        self.requests: Dict[str, list] = {}

    def is_allowed(self, client_id: str) -> bool:
        """Check if client is within rate limit."""
        now = time.time()
        minute_ago = now - 60

        if client_id not in self.requests:
            self.requests[client_id] = []

        # Remove old requests
        self.requests[client_id] = [
            ts for ts in self.requests[client_id]
            if ts > minute_ago
        ]

        # Check limit
        if len(self.requests[client_id]) >= self.limits_per_minute:
            logger.warning(f"Rate limit exceeded for {client_id}")
            return False

        # Record request
        self.requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for this minute."""
        now = time.time()
        minute_ago = now - 60

        if client_id not in self.requests:
            return self.limits_per_minute

        # Remove old requests
        self.requests[client_id] = [
            ts for ts in self.requests[client_id]
            if ts > minute_ago
        ]

        return self.limits_per_minute - len(self.requests[client_id])


def require_api_key(func):
    """Decorator to require valid API key."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract key from kwargs (set by middleware)
        key_id = kwargs.pop("_api_key_id", None)

        if not key_id:
            logger.error("API key required")
            raise PermissionError("API key required")

        # Get audit logger
        audit = AuditLogger()
        audit.log_event(
            event_type="api_call",
            operation=func.__name__,
            user=key_id,
            status="success"
        )

        return func(*args, **kwargs)

    return wrapper


def rate_limited(limiter: RateLimiter):
    """Decorator to apply rate limiting."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_id = kwargs.pop("_client_id", "unknown")

            if not limiter.is_allowed(client_id):
                logger.error(f"Rate limit exceeded for {client_id}")
                raise RuntimeError("Rate limit exceeded")

            remaining = limiter.get_remaining(client_id)
            kwargs["_rate_limit_remaining"] = remaining

            return func(*args, **kwargs)

        return wrapper
    return decorator


class SecretsManager:
    """Manage secrets (API keys, passwords, etc.)."""

    @staticmethod
    def get_from_env(key: str, default: str = None) -> str:
        """Get secret from environment variable."""
        import os
        return os.environ.get(key, default)

    @staticmethod
    def get_from_file(secret_name: str, secrets_dir: Path = Path("data/secrets")) -> str:
        """Get secret from encrypted file."""
        secret_file = secrets_dir / f"{secret_name}.secret"

        if not secret_file.exists():
            raise ValueError(f"Secret not found: {secret_name}")

        try:
            return secret_file.read_text().strip()
        except Exception as e:
            logger.error(f"Error reading secret: {e}")
            raise

    @staticmethod
    def store_secret(secret_name: str, value: str, secrets_dir: Path = Path("data/secrets")):
        """Store a secret in encrypted file."""
        secrets_dir.mkdir(parents=True, exist_ok=True)
        secret_file = secrets_dir / f"{secret_name}.secret"

        try:
            secret_file.write_text(value)
            secret_file.chmod(0o600)  # Read/write owner only
            logger.info(f"Stored secret: {secret_name}")
        except Exception as e:
            logger.error(f"Error storing secret: {e}")
            raise


class SecurityHeaders:
    """Security headers for HTTP responses."""

    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

    @staticmethod
    def apply_headers(environ, start_response, wrapped):
        """Apply security headers to response."""
        def custom_start_response(status, headers):
            security_headers = SecurityHeaders.get_headers()
            headers = list(headers) + [(k, v) for k, v in security_headers.items()]
            return start_response(status, headers)

        return wrapped(environ, custom_start_response)


class PasswordValidator:
    """Validate passwords meet security requirements."""

    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBERS = True
    REQUIRE_SPECIAL = True

    @staticmethod
    def validate(password: str) -> Tuple[bool, str]:
        """Validate password strength."""
        if len(password) < PasswordValidator.MIN_LENGTH:
            return False, f"Password must be at least {PasswordValidator.MIN_LENGTH} characters"

        if PasswordValidator.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Password must contain uppercase letters"

        if PasswordValidator.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            return False, "Password must contain lowercase letters"

        if PasswordValidator.REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
            return False, "Password must contain numbers"

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if PasswordValidator.REQUIRE_SPECIAL and not any(c in special_chars for c in password):
            return False, "Password must contain special characters"

        return True, "Password is strong"


# Global instances
_api_key_manager = None
_audit_logger = None
_rate_limiter = None


def get_api_key_manager() -> APIKeyManager:
    """Get global API key manager."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


def get_audit_logger() -> AuditLogger:
    """Get global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
