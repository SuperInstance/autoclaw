"""Input validation and sanitization for AutoClaw.

Validates all user inputs at system boundaries:
- API method parameters
- Configuration values
- External data

Prevents common issues:
- SQL injection (via SQLite)
- Buffer overflow (via size limits)
- Invalid state transitions
- Type mismatches
"""

import re
from typing import Any, Dict, List, Optional, Type
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Validation failed."""
    pass


class StringValidator:
    """Validates string inputs."""

    MAX_LENGTH = 10000
    FORBIDDEN_PATTERNS = [
        # XSS patterns
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers (onclick, etc)
        r"<iframe",  # Iframe tags
        r"<object",  # Object tags
        # SQL injection patterns
        r"'\s*;\s*DROP\s+",  # DROP statement
        r"'\s*OR\s+'?\d*'?\s*=\s*'",  # OR 1=1 type
        r"'\s*OR\s+1\s*=\s*1",  # OR 1=1
        r"--\s*$",  # SQL comment at end of line
        r";\s*DROP",  # DROP after semicolon
        r"UNION\s+SELECT",  # UNION based injection
    ]

    @staticmethod
    def validate(value: str, field: str = "string", max_length: int = None) -> str:
        """Validate and sanitize string input."""
        if not isinstance(value, str):
            raise ValidationError(f"{field}: expected string, got {type(value).__name__}")

        max_len = max_length or StringValidator.MAX_LENGTH
        if len(value) > max_len:
            raise ValidationError(f"{field}: exceeds max length {max_len} (got {len(value)})")

        if len(value) == 0:
            raise ValidationError(f"{field}: cannot be empty")

        # Check for forbidden patterns
        for pattern in StringValidator.FORBIDDEN_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError(f"{field}: contains forbidden pattern")

        return value.strip()


class IntValidator:
    """Validates integer inputs."""

    @staticmethod
    def validate(value: Any, field: str = "int", min_val: int = None, max_val: int = None) -> int:
        """Validate integer input."""
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValidationError(f"{field}: expected int, got {type(value).__name__}")

        if min_val is not None and value < min_val:
            raise ValidationError(f"{field}: {value} < minimum {min_val}")

        if max_val is not None and value > max_val:
            raise ValidationError(f"{field}: {value} > maximum {max_val}")

        return value


class ListValidator:
    """Validates list inputs."""

    MAX_LENGTH = 1000

    @staticmethod
    def validate(value: Any, field: str = "list", element_type: Type = None, max_length: int = None) -> List:
        """Validate list input."""
        if not isinstance(value, list):
            raise ValidationError(f"{field}: expected list, got {type(value).__name__}")

        max_len = max_length or ListValidator.MAX_LENGTH
        if len(value) > max_len:
            raise ValidationError(f"{field}: exceeds max length {max_len}")

        if element_type:
            for i, elem in enumerate(value):
                if not isinstance(elem, element_type):
                    raise ValidationError(f"{field}[{i}]: expected {element_type.__name__}, got {type(elem).__name__}")

        return value


class DictValidator:
    """Validates dictionary inputs."""

    @staticmethod
    def validate(value: Any, field: str = "dict", schema: Dict[str, Type] = None) -> Dict:
        """Validate dict input."""
        if not isinstance(value, dict):
            raise ValidationError(f"{field}: expected dict, got {type(value).__name__}")

        if schema:
            for key, expected_type in schema.items():
                if key in value:
                    if not isinstance(value[key], expected_type):
                        raise ValidationError(
                            f"{field}.{key}: expected {expected_type.__name__}, got {type(value[key]).__name__}"
                        )

        return value


class EnumValidator:
    """Validates enum values."""

    @staticmethod
    def validate(value: str, field: str = "enum", enum_class: Type[Enum] = None) -> str:
        """Validate enum input."""
        if not isinstance(value, str):
            raise ValidationError(f"{field}: expected string, got {type(value).__name__}")

        if enum_class:
            valid_values = [e.value for e in enum_class]
            if value not in valid_values:
                raise ValidationError(f"{field}: '{value}' not in {valid_values}")

        return value


class KnowledgeValidator:
    """Validates knowledge store inputs."""

    @staticmethod
    def validate_create(
        insight: str,
        category: str,
        tags: List[str],
        source_task_ids: List[int],
        experiments_supporting: int,
        experiments_contradicting: int = 0,
        conditions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate knowledge.create() parameters."""
        # Validate insight
        insight = StringValidator.validate(insight, "insight", max_length=5000)

        # Validate category
        valid_categories = {"hyperparameter", "architecture", "training_dynamics", "data", "methodology"}
        category = StringValidator.validate(category, "category", max_length=50)
        if category not in valid_categories:
            raise ValidationError(f"category: '{category}' not in {valid_categories}")

        # Validate tags
        tags = ListValidator.validate(tags, "tags", str, max_length=20)
        for tag in tags:
            StringValidator.validate(tag, f"tag", max_length=50)

        # Validate source_task_ids
        source_task_ids = ListValidator.validate(source_task_ids, "source_task_ids", int)
        for task_id in source_task_ids:
            IntValidator.validate(task_id, f"source_task_id", min_val=1)

        # Validate experiment counts
        experiments_supporting = IntValidator.validate(
            experiments_supporting,
            "experiments_supporting",
            min_val=0,
            max_val=10000
        )
        experiments_contradicting = IntValidator.validate(
            experiments_contradicting,
            "experiments_contradicting",
            min_val=0,
            max_val=10000
        )

        # Validate conditions
        if conditions:
            conditions = StringValidator.validate(conditions, "conditions", max_length=1000)

        return {
            "insight": insight,
            "category": category,
            "tags": tags,
            "source_task_ids": source_task_ids,
            "experiments_supporting": experiments_supporting,
            "experiments_contradicting": experiments_contradicting,
            "conditions": conditions,
        }


class NotificationValidator:
    """Validates notification inputs."""

    @staticmethod
    def validate_create(
        title: str,
        body: str,
        severity: str = "important",
        source: str = "system",
        tags: List[str] = None,
        auto_deliver: bool = True,
    ) -> Dict[str, Any]:
        """Validate notification.create() parameters."""
        # Validate title
        title = StringValidator.validate(title, "title", max_length=200)

        # Validate body
        body = StringValidator.validate(body, "body", max_length=5000)

        # Validate severity
        valid_severities = {"info", "important", "urgent"}
        severity = StringValidator.validate(severity, "severity", max_length=20)
        if severity not in valid_severities:
            raise ValidationError(f"severity: '{severity}' not in {valid_severities}")

        # Validate source
        source = StringValidator.validate(source, "source", max_length=100)

        # Validate tags
        tags = tags or []
        tags = ListValidator.validate(tags, "tags", str, max_length=20)
        for tag in tags:
            StringValidator.validate(tag, "tag", max_length=50)

        # Validate auto_deliver
        if not isinstance(auto_deliver, bool):
            raise ValidationError(f"auto_deliver: expected bool, got {type(auto_deliver).__name__}")

        return {
            "title": title,
            "body": body,
            "severity": severity,
            "source": source,
            "tags": tags,
            "auto_deliver": auto_deliver,
        }


class MessageValidator:
    """Validates message bus inputs."""

    @staticmethod
    def validate_publish(
        from_agent: str,
        to_agent: str,
        msg_type: str,
        payload: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        tags: List[str] = None,
        expires_in_hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Validate message.publish() parameters."""
        # Validate agents
        from_agent = StringValidator.validate(from_agent, "from_agent", max_length=100)
        to_agent = StringValidator.validate(to_agent, "to_agent", max_length=100)

        # Validate message type
        msg_type = StringValidator.validate(msg_type, "type", max_length=100)

        # Validate priority
        priority = IntValidator.validate(priority, "priority", min_val=1, max_val=10)

        # Validate payload
        payload = payload or {}
        if not isinstance(payload, dict):
            raise ValidationError(f"payload: expected dict, got {type(payload).__name__}")

        # Validate tags
        tags = tags or []
        tags = ListValidator.validate(tags, "tags", str, max_length=20)

        # Validate expiry
        if expires_in_hours is not None:
            if not isinstance(expires_in_hours, (int, float)):
                raise ValidationError(f"expires_in_hours: expected number, got {type(expires_in_hours).__name__}")
            if expires_in_hours <= 0:
                raise ValidationError(f"expires_in_hours: must be positive")
            if expires_in_hours > 720:  # 30 days
                raise ValidationError(f"expires_in_hours: cannot exceed 720 hours (30 days)")

        return {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "type": msg_type,
            "payload": payload,
            "priority": priority,
            "tags": tags,
            "expires_in_hours": expires_in_hours,
        }


class TriggerValidator:
    """Validates trigger configuration."""

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate trigger configuration."""
        if not isinstance(config, dict):
            raise ValidationError(f"config: expected dict, got {type(config).__name__}")

        # Required fields
        required = ["id", "name", "type", "enabled"]
        for field in required:
            if field not in config:
                raise ValidationError(f"trigger.{field}: required")

        # Validate ID
        config["id"] = IntValidator.validate(config["id"], "trigger.id", min_val=1)

        # Validate name
        config["name"] = StringValidator.validate(config["name"], "trigger.name", max_length=100)

        # Validate type
        valid_types = {"RSS", "Schedule", "Webhook", "File", "Sensor"}
        config["type"] = StringValidator.validate(config["type"], "trigger.type", max_length=20)
        if config["type"] not in valid_types:
            raise ValidationError(f"trigger.type: '{config['type']}' not in {valid_types}")

        # Validate enabled
        if not isinstance(config["enabled"], bool):
            raise ValidationError(f"trigger.enabled: expected bool, got {type(config['enabled']).__name__}")

        # Validate source if present
        if "source" in config:
            source = DictValidator.validate(config["source"], "trigger.source")
            if config["type"] == "RSS" and "url" not in source:
                raise ValidationError("trigger.source.url: required for RSS type")
            if config["type"] == "Schedule" and "cron" not in source:
                raise ValidationError("trigger.source.cron: required for Schedule type")

        # Validate filter if present
        if "filter" in config:
            DictValidator.validate(config["filter"], "trigger.filter")

        return config


class ConfigValidator:
    """Validates configuration files."""

    REQUIRED_SECTIONS = ["crew", "llm", "knowledge", "triggers", "notifications"]

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete config."""
        if not isinstance(config, dict):
            raise ValidationError(f"config: expected dict, got {type(config).__name__}")

        # Check required sections
        for section in ConfigValidator.REQUIRED_SECTIONS:
            if section not in config:
                raise ValidationError(f"config.{section}: required section missing")

        # Validate crew section
        if "name" in config.get("crew", {}):
            StringValidator.validate(config["crew"]["name"], "crew.name")

        # Validate LLM section
        llm = config.get("llm", {})
        if "provider" in llm:
            StringValidator.validate(llm["provider"], "llm.provider")
        if "model" in llm:
            StringValidator.validate(llm["model"], "llm.model")
        if "api_key" in llm:
            StringValidator.validate(llm["api_key"], "llm.api_key")

        # Validate knowledge section
        knowledge = config.get("knowledge", {})
        if "max_entries" in knowledge:
            IntValidator.validate(knowledge["max_entries"], "knowledge.max_entries", min_val=10, max_val=10000)
        if "cleanup_days" in knowledge:
            IntValidator.validate(knowledge["cleanup_days"], "knowledge.cleanup_days", min_val=1, max_val=365)

        # Validate triggers
        triggers = config.get("triggers", {})
        if "default_poll_minutes" in triggers:
            IntValidator.validate(triggers["default_poll_minutes"], "triggers.default_poll_minutes", min_val=1)
        if "triggers" in triggers and isinstance(triggers["triggers"], list):
            for i, trigger in enumerate(triggers["triggers"]):
                TriggerValidator.validate_config(trigger)

        # Validate notifications
        notifications = config.get("notifications", {})
        if "external_channels" in notifications:
            channels = ListValidator.validate(
                notifications["external_channels"],
                "notifications.external_channels",
                max_length=20
            )
            for i, channel in enumerate(channels):
                if "type" in channel:
                    valid_types = {"webhook", "email", "command", "file"}
                    if channel["type"] not in valid_types:
                        raise ValidationError(
                            f"notifications.external_channels[{i}].type: "
                            f"'{channel['type']}' not in {valid_types}"
                        )

        return config


def validate_decorator(validator_func):
    """Decorator to apply validation to function parameters."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Call validator with kwargs
                validated = validator_func(**kwargs)
                # Merge with args
                return func(*args, **validated)
            except ValidationError as e:
                logger.error(f"Validation error in {func.__name__}: {e}")
                raise
        return wrapper
    return decorator


# Global validation singleton
_config_validated = False


def validate_config_on_startup(config_path: Path) -> bool:
    """Validate config file on startup."""
    global _config_validated

    if _config_validated:
        return True

    try:
        import yaml
        config = yaml.safe_load(config_path.read_text())
        ConfigValidator.validate_config(config)
        _config_validated = True
        logger.info("Configuration validated successfully")
        return True
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Error reading configuration: {e}")
        return False
