"""Bootstrap and initialization for AutoClaw daemon.

Handles:
- Configuration loading and validation
- Database initialization
- Component startup
- Health verification
- Signal handling and graceful shutdown
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class BootstrapSequence:
    """Orchestrate startup sequence."""

    def __init__(self, verbose: bool = False, foreground: bool = False):
        """Initialize bootstrap."""
        self.verbose = verbose
        self.foreground = foreground
        self.startup_log = []

    def log(self, level: str, message: str):
        """Log during startup."""
        self.startup_log.append((level, message))

        if level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        elif level == "debug" and self.verbose:
            logger.debug(message)

    def run(self) -> bool:
        """Run complete bootstrap sequence."""
        try:
            # Step 1: Signal handlers
            self.log("info", "[1/8] Setting up signal handlers...")
            from crew.startup import setup_signal_handlers
            setup_signal_handlers()

            # Step 2: Directory structure
            self.log("info", "[2/8] Creating directory structure...")
            from crew.startup import create_directory_structure
            create_directory_structure()

            # Step 3: Check dependencies
            self.log("info", "[3/8] Checking dependencies...")
            from crew.startup import check_dependencies
            if not check_dependencies():
                self.log("error", "Dependency check failed")
                return False

            # Step 4: Load and validate configuration
            self.log("info", "[4/8] Loading configuration...")
            from crew.config import load_config
            try:
                config = load_config()
                self.log("info", f"Loaded config: {config.config_file}")
            except Exception as e:
                self.log("error", f"Configuration load failed: {e}")
                return False

            # Step 5: Configure logging
            self.log("info", "[5/8] Configuring logging...")
            self._setup_logging(config)

            # Step 6: Initialize databases
            self.log("info", "[6/8] Initializing databases...")
            from crew.startup import initialize_databases
            if not initialize_databases():
                self.log("error", "Database initialization failed")
                return False

            # Step 7: Performance optimization
            self.log("info", "[7/8] Optimizing databases...")
            from crew.performance import optimize_databases
            try:
                optimize_databases()
            except Exception as e:
                self.log("warning", f"Database optimization skipped: {e}")

            # Step 8: Health checks
            self.log("info", "[8/8] Running health checks...")
            from crew.startup import health_check
            if not health_check():
                self.log("warning", "Some health checks failed, but continuing...")

            self.log("info", "=" * 60)
            self.log("info", "✓ Bootstrap complete - daemon ready")
            self.log("info", "=" * 60)

            return True

        except Exception as e:
            self.log("error", f"Bootstrap failed: {e}")
            if self.verbose:
                import traceback
                logger.error(traceback.format_exc())
            return False

    def _setup_logging(self, config):
        """Configure logging based on config."""
        try:
            log_config = config.get_section("daemon")
            log_level = log_config.get("log_level", "info").upper()
            log_file = log_config.get("log_file", "data/logs/autoclaw.log")
            log_format = log_config.get("log_format", "text")

            # Set root logger level
            root_logger = logging.getLogger()
            level = getattr(logging, log_level, logging.INFO)
            root_logger.setLevel(level)

            # File handler
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(level)

            # Format
            if log_format == "json":
                formatter = logging.Formatter(
                    '{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "msg": "%(message)s"}'
                )
            else:
                formatter = logging.Formatter(
                    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                )

            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            self.log("info", f"Logging to {log_file}")

        except Exception as e:
            self.log("warning", f"Error setting up logging: {e}")


def bootstrap(verbose: bool = False, foreground: bool = False) -> bool:
    """Run bootstrap sequence."""
    sequence = BootstrapSequence(verbose=verbose, foreground=foreground)
    return sequence.run()


def get_startup_log() -> list:
    """Get startup log entries."""
    # This would need to be stored somewhere accessible
    # For now, just return empty
    return []


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    )

    success = bootstrap(verbose=True, foreground=True)
    sys.exit(0 if success else 1)
