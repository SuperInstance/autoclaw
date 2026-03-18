"""Trigger daemon: monitors external events and creates tasks.

Runs as a background thread, polling external sources and creating
tasks when events match filter criteria. Integrates with the main
daemon's task board.
"""

import threading
import logging
import yaml
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from crew.triggers.rss import RSSHandler
from crew.knowledge import get_knowledge_store

logger = logging.getLogger(__name__)


class TriggerDaemon:
    """Monitors external triggers and creates tasks."""

    TRIGGERS_DIR = Path("data/triggers")
    CONFIG_FILE = Path("data/config.yaml")

    def __init__(self, task_board=None):
        """Initialize trigger daemon.

        Args:
            task_board: Reference to task board (for creating tasks)
        """
        self.task_board = task_board
        self.triggers: Dict[int, Dict[str, Any]] = {}
        self.handlers = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._ensure_dirs()
        self._load_triggers()

    def _ensure_dirs(self):
        """Ensure trigger directory exists."""
        self.TRIGGERS_DIR.mkdir(parents=True, exist_ok=True)

    def _load_triggers(self):
        """Load trigger configurations from data/triggers/*.yaml"""
        if not self.TRIGGERS_DIR.exists():
            logger.info("No triggers directory found")
            return

        trigger_files = sorted(self.TRIGGERS_DIR.glob("*.yaml"))
        if not trigger_files:
            logger.info("No trigger files found")
            return

        for trigger_file in trigger_files:
            try:
                with open(trigger_file, 'r') as f:
                    trigger_data = yaml.safe_load(f)
                    if trigger_data:
                        trigger_id = trigger_data.get('id')
                        if trigger_id:
                            self.triggers[trigger_id] = trigger_data
                            logger.info(f"Loaded trigger #{trigger_id}: {trigger_data.get('name', 'unnamed')}")
            except Exception as e:
                logger.error(f"Error loading trigger {trigger_file}: {e}")

        logger.info(f"Loaded {len(self.triggers)} triggers")

    def start(self):
        """Start trigger daemon thread."""
        if self.running:
            logger.warning("Trigger daemon already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._main_loop, daemon=True)
        self.thread.start()
        logger.info("Trigger daemon started")

    def stop(self):
        """Stop trigger daemon thread."""
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Trigger daemon stopped")

    def _main_loop(self):
        """Main trigger polling loop (runs in background thread)."""
        logger.info("Trigger daemon main loop started")

        while self.running:
            try:
                # Check if triggers are enabled in config
                if not self._triggers_enabled():
                    time.sleep(60)
                    continue

                # Check each trigger
                for trigger_id, trigger_config in self.triggers.items():
                    if not trigger_config.get('enabled', True):
                        continue

                    self._check_trigger(trigger_id, trigger_config)

                # Sleep before next check
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in trigger daemon loop: {e}")
                time.sleep(60)

        logger.info("Trigger daemon main loop ended")

    def _triggers_enabled(self) -> bool:
        """Check if triggers are enabled in config."""
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                config = yaml.safe_load(f) or {}
                return config.get('triggers', {}).get('enabled', True)
        except:
            return True  # Default to enabled

    def _check_trigger(self, trigger_id: int, trigger_config: Dict[str, Any]):
        """Check a single trigger for new events."""
        trigger_type = trigger_config.get('type')
        last_checked = trigger_config.get('last_checked')
        poll_interval = trigger_config.get('source', {}).get('poll_interval_minutes', 60)

        # Check poll interval
        if last_checked:
            try:
                last_check_time = datetime.fromisoformat(last_checked)
                elapsed = (datetime.now(timezone.utc) - last_check_time).total_seconds() / 60
                if elapsed < poll_interval:
                    return  # Not time to check yet
            except:
                pass

        # Get handler for this trigger type
        handler = self._get_handler(trigger_id, trigger_type, trigger_config)
        if not handler:
            return

        # Check for events
        try:
            events = handler.check()
        except Exception as e:
            logger.error(f"Error checking trigger #{trigger_id}: {e}")
            return

        # Update last_checked timestamp
        self._update_trigger_timestamp(trigger_id)

        # Process matching events
        for event in events:
            self._handle_event(trigger_id, trigger_config, event, handler)

    def _get_handler(self, trigger_id: int, trigger_type: str, config: Dict[str, Any]):
        """Get or create handler for trigger type."""
        if trigger_type == 'rss':
            if trigger_id not in self.handlers:
                self.handlers[trigger_id] = RSSHandler(trigger_id, config)
            return self.handlers[trigger_id]
        else:
            logger.warning(f"Unsupported trigger type: {trigger_type}")
            return None

    def _handle_event(self, trigger_id: int, trigger_config: Dict[str, Any], 
                     event: Dict[str, Any], handler):
        """Handle a trigger event (create task, notify, etc.)."""
        action = trigger_config.get('action', 'notify_captain')

        if action == 'create_task':
            self._create_task_from_event(trigger_id, trigger_config, event)
        elif action == 'notify_captain':
            self._notify_captain(trigger_id, trigger_config, event)
        else:
            logger.warning(f"Unknown trigger action: {action}")

        # Update fire counts
        handler.on_fired()
        self._increment_fire_count(trigger_id)

    def _create_task_from_event(self, trigger_id: int, trigger_config: Dict[str, Any],
                               event: Dict[str, Any]):
        """Create a task from a trigger event."""
        if not self.task_board:
            logger.warning("Task board not available, skipping task creation")
            return

        template = trigger_config.get('task_template', {})
        title = self._format_template(template.get('title', '{title}'), event)
        description = self._format_template(template.get('description', ''), event)

        logger.info(f"Creating task from trigger #{trigger_id}: {title}")

        # Create task
        try:
            task = self.task_board.create(
                title=title,
                description=description,
                task_type=template.get('type', 'triggered'),
                priority=template.get('priority', 4),
                tags=template.get('tags', []) + ['auto-triggered', f'trigger-{trigger_id}'],
                source={
                    'creator': 'trigger',
                    'trigger_id': trigger_id,
                    'parent_task_id': None,
                    'reason': f"Triggered by trigger #{trigger_id}: {trigger_config.get('name', 'unnamed')}"
                }
            )
            logger.info(f"Created task #{task.id} from trigger #{trigger_id}")
        except Exception as e:
            logger.error(f"Error creating task from trigger: {e}")

    def _notify_captain(self, trigger_id: int, trigger_config: Dict[str, Any],
                       event: Dict[str, Any]):
        """Notify captain of a trigger event."""
        template = trigger_config.get('notification_template', {})
        title = self._format_template(template.get('title', '{title}'), event)
        body = self._format_template(template.get('body', ''), event)

        logger.info(f"Notification from trigger #{trigger_id}: {title}")
        # TODO: Integrate with notification delivery system
        # For now, just log it

    def _format_template(self, template: str, event: Dict[str, Any]) -> str:
        """Format a template with event data.

        Supports: {title}, {url}, {summary}, {timestamp}
        """
        return (
            template
            .replace('{title}', event.get('title', ''))
            .replace('{url}', event.get('url', ''))
            .replace('{summary}', event.get('summary', '')[:200])
            .replace('{timestamp}', event.get('timestamp', ''))
        )

    def _update_trigger_timestamp(self, trigger_id: int):
        """Update last_checked timestamp for trigger."""
        if trigger_id not in self.triggers:
            return

        self.triggers[trigger_id]['last_checked'] = datetime.now(timezone.utc).isoformat()
        self._save_trigger(trigger_id, self.triggers[trigger_id])

    def _increment_fire_count(self, trigger_id: int):
        """Increment fire count for trigger."""
        if trigger_id not in self.triggers:
            return

        trigger = self.triggers[trigger_id]
        trigger['fires_today'] = trigger.get('fires_today', 0) + 1
        trigger['total_fires'] = trigger.get('total_fires', 0) + 1
        trigger['last_fired'] = datetime.now(timezone.utc).isoformat()
        self._save_trigger(trigger_id, trigger)

    def _save_trigger(self, trigger_id: int, config: Dict[str, Any]):
        """Save trigger configuration."""
        trigger_file = self.TRIGGERS_DIR / f"{trigger_id}.yaml"
        try:
            with open(trigger_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            logger.error(f"Error saving trigger #{trigger_id}: {e}")

    def add_trigger(self, trigger_config: Dict[str, Any]) -> int:
        """Add a new trigger dynamically."""
        trigger_id = max(self.triggers.keys()) + 1 if self.triggers else 1
        trigger_config['id'] = trigger_id
        trigger_config['created_at'] = datetime.now(timezone.utc).isoformat()
        trigger_config['enabled'] = True
        
        self.triggers[trigger_id] = trigger_config
        self._save_trigger(trigger_id, trigger_config)
        logger.info(f"Added trigger #{trigger_id}: {trigger_config.get('name', 'unnamed')}")
        return trigger_id

    def disable_trigger(self, trigger_id: int):
        """Disable a trigger."""
        if trigger_id in self.triggers:
            self.triggers[trigger_id]['enabled'] = False
            self._save_trigger(trigger_id, self.triggers[trigger_id])
            logger.info(f"Disabled trigger #{trigger_id}")

    def enable_trigger(self, trigger_id: int):
        """Enable a trigger."""
        if trigger_id in self.triggers:
            self.triggers[trigger_id]['enabled'] = True
            self._save_trigger(trigger_id, self.triggers[trigger_id])
            logger.info(f"Enabled trigger #{trigger_id}")

    def list_triggers(self) -> List[Dict[str, Any]]:
        """List all triggers."""
        return list(self.triggers.values())

    def stats(self) -> Dict[str, Any]:
        """Get trigger statistics."""
        enabled = sum(1 for t in self.triggers.values() if t.get('enabled', True))
        total_fires = sum(t.get('total_fires', 0) for t in self.triggers.values())
        
        return {
            'total_triggers': len(self.triggers),
            'enabled': enabled,
            'disabled': len(self.triggers) - enabled,
            'total_fires': total_fires,
        }
