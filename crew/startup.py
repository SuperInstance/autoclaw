"""AutoClaw startup and initialization procedures.

Handles:
- Configuration validation
- Directory structure creation
- Database initialization
- Component health checks
- Graceful startup/shutdown
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import atexit
import signal

logger = logging.getLogger(__name__)

# Global state for graceful shutdown
_shutdown_handlers = []
_is_shutting_down = False


def register_shutdown_handler(handler):
    """Register a handler to run on shutdown."""
    _shutdown_handlers.append(handler)


def _graceful_shutdown(signum=None, frame=None):
    """Graceful shutdown: run all handlers."""
    global _is_shutting_down

    if _is_shutting_down:
        logger.warning("Shutdown already in progress, forcing exit")
        sys.exit(1)

    _is_shutting_down = True
    logger.info(f"Graceful shutdown initiated (signal {signum})")

    # Run handlers in reverse order
    for i, handler in enumerate(reversed(_shutdown_handlers)):
        try:
            logger.debug(f"Running shutdown handler {len(_shutdown_handlers) - i}/{len(_shutdown_handlers)}")
            handler()
        except Exception as e:
            logger.error(f"Error in shutdown handler: {e}")

    logger.info("Shutdown complete")
    sys.exit(0)


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGTERM, _graceful_shutdown)
    signal.signal(signal.SIGINT, _graceful_shutdown)
    atexit.register(_graceful_shutdown)
    logger.debug("Signal handlers registered")


def create_directory_structure():
    """Create required data directories."""
    directories = [
        "data",
        "data/agents",
        "data/handoffs",
        "data/flowstate",
        "data/logs",
        "data/checkpoints",
    ]

    for dir_path in directories:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {dir_path}")

    logger.info(f"Directory structure initialized ({len(directories)} directories)")


def validate_configuration() -> bool:
    """Validate configuration file."""
    from crew.validation import validate_config_on_startup

    config_path = Path("data/config.yaml")

    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        logger.error("Create configuration file with:")
        logger.error("  cp docs/config.example.yaml data/config.yaml")
        logger.error("  nano data/config.yaml")
        return False

    if not validate_config_on_startup(config_path):
        logger.error("Configuration validation failed")
        return False

    return True


def check_dependencies() -> bool:
    """Check that all required packages are installed."""
    required_packages = [
        "anthropic",
        "sqlalchemy",
        "yaml",
        "requests",
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        logger.error(f"Missing required packages: {', '.join(missing)}")
        logger.error("Install with: pip install -r requirements.txt")
        return False

    logger.info(f"All dependencies available ({len(required_packages)} packages)")
    return True


def initialize_databases() -> bool:
    """Initialize SQLite databases."""
    try:
        from crew.knowledge import get_knowledge_store
        from crew.messaging.bus import MessageBus

        # Initialize knowledge store
        store = get_knowledge_store()
        stats = store.stats()
        logger.info(f"Knowledge store initialized ({stats['total_entries']} entries)")

        # Initialize message bus
        bus = MessageBus()
        depths = bus.get_queue_depths()
        logger.info(f"Message bus initialized ({depths.get('pending', 0)} pending messages)")

        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def health_check() -> bool:
    """Run health checks on all components."""
    checks = {
        "Knowledge Store": _check_knowledge_store,
        "Message Bus": _check_message_bus,
        "Notifications": _check_notifications,
        "Handoff Manager": _check_handoff_manager,
        "Trigger Daemon": _check_trigger_daemon,
        "Adaptive Scheduler": _check_adaptive_scheduler,
        "Flowstate Manager": _check_flowstate_manager,
    }

    passed = 0
    failed = 0

    for name, check_func in checks.items():
        try:
            check_func()
            logger.info(f"✓ {name}")
            passed += 1
        except Exception as e:
            logger.warning(f"✗ {name}: {e}")
            failed += 1

    logger.info(f"Health check: {passed}/{len(checks)} components OK")
    return failed == 0


def _check_knowledge_store():
    """Check knowledge store."""
    from crew.knowledge import get_knowledge_store
    store = get_knowledge_store()
    store.stats()


def _check_message_bus():
    """Check message bus."""
    from crew.messaging.bus import MessageBus
    bus = MessageBus()
    bus.get_queue_depths()


def _check_notifications():
    """Check notifications."""
    from crew.notifications import NotificationManager
    nm = NotificationManager()
    nm.stats()


def _check_handoff_manager():
    """Check handoff manager."""
    from crew.handoff import get_handoff_manager
    hm = get_handoff_manager()
    hm.list_generations(task_id=1)


def _check_trigger_daemon():
    """Check trigger daemon."""
    from crew.triggers import TriggerDaemon
    daemon = TriggerDaemon()
    daemon.list_triggers()


def _check_adaptive_scheduler():
    """Check adaptive scheduler."""
    from crew.adaptive import get_adaptive_scheduler
    scheduler = get_adaptive_scheduler()
    scheduler.stats()


def _check_flowstate_manager():
    """Check flowstate manager."""
    from crew.flowstate import get_flowstate_manager
    manager = get_flowstate_manager()
    manager.stats()


def startup() -> bool:
    """Complete startup sequence."""
    logger.info("=" * 60)
    logger.info("AutoClaw Startup Sequence")
    logger.info("=" * 60)

    # Step 1: Setup signal handlers
    logger.info("\n[1/6] Setting up signal handlers...")
    setup_signal_handlers()

    # Step 2: Create directory structure
    logger.info("[2/6] Creating directory structure...")
    create_directory_structure()

    # Step 3: Check dependencies
    logger.info("[3/6] Checking dependencies...")
    if not check_dependencies():
        return False

    # Step 4: Validate configuration
    logger.info("[4/6] Validating configuration...")
    if not validate_configuration():
        return False

    # Step 5: Initialize databases
    logger.info("[5/6] Initializing databases...")
    if not initialize_databases():
        return False

    # Step 6: Health check
    logger.info("[6/6] Running health checks...")
    if not health_check():
        logger.warning("Some components failed health checks, but continuing...")

    logger.info("=" * 60)
    logger.info("✓ Startup complete")
    logger.info("=" * 60)
    return True


def shutdown():
    """Shutdown sequence."""
    logger.info("Shutting down AutoClaw...")

    # Cleanup components
    try:
        from crew.triggers import TriggerDaemon
        daemon = TriggerDaemon()
        daemon.stop()
        logger.info("Stopped trigger daemon")
    except Exception as e:
        logger.warning(f"Error stopping trigger daemon: {e}")

    try:
        from crew.daemon_integration import get_daemon_integration
        di = get_daemon_integration()
        # Save any pending state
        logger.info("Saved daemon state")
    except Exception as e:
        logger.warning(f"Error saving daemon state: {e}")

    logger.info("Shutdown complete")


if __name__ == "__main__":
    # Test startup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    )

    success = startup()
    sys.exit(0 if success else 1)
