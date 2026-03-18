"""Configuration loading and management for AutoClaw.

Loads and validates configuration from YAML files with:
- Schema validation
- Environment variable interpolation
- Configuration merging (defaults + user config)
- Type checking
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from crew.validation import ConfigValidator, ValidationError

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and manage configuration."""

    def __init__(self, config_file: Path = Path("data/config.yaml")):
        """Initialize config loader."""
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from file."""
        if not self.config_file.exists():
            logger.error(f"Configuration file not found: {self.config_file}")
            raise FileNotFoundError(f"Configuration not found: {self.config_file}")

        try:
            with open(self.config_file, 'r') as f:
                raw_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in configuration: {e}")
            raise

        # Interpolate environment variables
        self.config = self._interpolate_env(raw_config)

        # Validate configuration
        try:
            self.config = ConfigValidator.validate_config(self.config)
            logger.info("Configuration loaded and validated")
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise

    def _interpolate_env(self, obj: Any) -> Any:
        """Recursively interpolate environment variables."""
        if isinstance(obj, str):
            # Handle ${VAR_NAME} syntax
            if obj.startswith("${") and obj.endswith("}"):
                var_name = obj[2:-1]
                value = os.environ.get(var_name)
                if value is None:
                    logger.warning(f"Environment variable not set: {var_name}")
                    return None
                return value
            return obj

        elif isinstance(obj, dict):
            return {k: self._interpolate_env(v) for k, v in obj.items()}

        elif isinstance(obj, list):
            return [self._interpolate_env(item) for item in obj]

        return obj

    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value by path (e.g., 'llm.model')."""
        parts = path.split('.')
        current = self.config

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default

        return current

    def set(self, path: str, value: Any):
        """Set configuration value by path."""
        parts = path.split('.')
        current = self.config

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        return self.config.get(section, {})

    def reload(self):
        """Reload configuration from file."""
        logger.info("Reloading configuration...")
        self._load_config()

    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary."""
        return self.config.copy()


class ConfigDefaults:
    """Default configuration values."""

    DEFAULTS = {
        "crew": {
            "name": "AutoClaw",
            "personality": "balanced",
        },
        "llm": {
            "provider": "anthropic",
            "model": "claude-opus-4-6",
        },
        "knowledge": {
            "max_entries": 500,
            "cleanup_days": 30,
            "auto_cleanup": True,
        },
        "triggers": {
            "enabled": True,
            "default_poll_minutes": 30,
            "triggers": [],
        },
        "notifications": {
            "external_channels": [],
        },
        "experiments": {
            "time_budget_seconds": 300,
            "git_commit_each": False,
            "keep_checkpoints": "best_only",
        },
        "adaptive": {
            "enabled": True,
            "thompson_samples_per_decision": 100,
        },
        "flowstate": {
            "enabled": True,
            "default_budget_gb": 10.0,
            "default_budget_hours": 4.0,
            "max_concurrent": 5,
        },
        "hardware": {
            "profile": None,
        },
        "daemon": {
            "log_level": "info",
            "log_file": "data/logs/autoclaw.log",
            "log_format": "json",
            "shutdown_timeout": 30,
            "health_check_interval": 30,
            "idle_sleep": 5,
        },
        "message_bus": {
            "database": "data/message_bus.db",
            "default_ttl_hours": 24,
            "max_messages": 10000,
            "auto_cleanup": True,
        },
        "error_handling": {
            "enable_audit": True,
            "audit_size": 1000,
            "notify_critical": True,
            "circuit_breaker_failures": 5,
            "circuit_breaker_recovery_seconds": 60,
        },
        "performance": {
            "db_pool_size": 5,
            "db_max_overflow": 10,
            "knowledge_cache_size": 100,
            "profile_queries": False,
        },
        "security": {
            "validate_api_keys": True,
            "enable_rate_limiting": True,
            "rate_limit_per_minute": 100,
            "validate_inputs": True,
            "enable_audit_log": True,
            "audit_log_file": "data/logs/audit.log",
        },
        "features": {
            "swarm_mode": False,
            "distributed": False,
            "experimental": False,
        },
    }

    @staticmethod
    def merge_with_user_config(user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user configuration with defaults."""
        result = ConfigDefaults.DEFAULTS.copy()

        for section, values in user_config.items():
            if section not in result:
                result[section] = {}

            if isinstance(values, dict):
                result[section].update(values)
            else:
                result[section] = values

        return result


# Global config instance
_config_loader = None


def get_config() -> ConfigLoader:
    """Get or create global config loader."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def load_config(config_file: Path = Path("data/config.yaml")) -> ConfigLoader:
    """Load configuration from file."""
    global _config_loader
    _config_loader = ConfigLoader(config_file)
    return _config_loader


def reload_config():
    """Reload configuration."""
    config = get_config()
    config.reload()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    )

    # Test configuration loading
    try:
        config = load_config()
        print(f"Loaded config from {config.config_file}")
        print(f"LLM Model: {config.get('llm.model')}")
        print(f"Max knowledge entries: {config.get('knowledge.max_entries')}")
        print("\nConfiguration is valid!")
    except Exception as e:
        print(f"Configuration error: {e}")
