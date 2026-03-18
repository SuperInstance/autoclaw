"""Notification manager: routes notifications to configured channels."""

import logging
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from crew.notifications.channels import create_channel

logger = logging.getLogger(__name__)


@dataclass
class Notification:
    """A notification to send to the captain."""

    id: int
    title: str
    body: str
    severity: str  # info, important, urgent
    source: str  # who/what created this
    timestamp: str = None
    delivered: bool = False
    tags: List[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Notification":
        """Create from dictionary (loaded from YAML)."""
        return cls(**data)


class NotificationManager:
    """Manages notification creation and delivery."""

    DATA_DIR = Path("data/notifications")
    NOTIFICATION_FILE = Path("data/notifications/notifications.yaml")
    MAX_NOTIFICATIONS = 1000
    CONFIG_FILE = Path("data/config.yaml")

    def __init__(self):
        """Initialize notification manager."""
        self.notifications: Dict[int, Notification] = {}
        self.next_id = 1
        self.channels = []
        self.unread_count = 0
        self._ensure_dirs()
        self._load_channels()
        self.load()

    def _ensure_dirs(self):
        """Ensure data directory exists."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _load_channels(self):
        """Load notification channels from config."""
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                config = yaml.safe_load(f) or {}

            channels_config = config.get('notifications', {}).get('external_channels', [])

            for channel_config in channels_config:
                channel_type = channel_config.get('type')
                channel = create_channel(channel_type, channel_config)
                if channel:
                    self.channels.append(channel)
                    logger.info(f"Loaded notification channel: {channel_type}")

            logger.info(f"Loaded {len(self.channels)} notification channels")

        except Exception as e:
            logger.error(f"Error loading notification channels: {e}")

    def load(self):
        """Load notifications from YAML file."""
        if not self.NOTIFICATION_FILE.exists():
            logger.info("No notification history found, starting fresh")
            return

        try:
            with open(self.NOTIFICATION_FILE, 'r') as f:
                data = yaml.safe_load(f) or {}

            notifications = data.get('notifications', [])
            for notif_data in notifications:
                notif = Notification.from_dict(notif_data)
                self.notifications[notif.id] = notif
                self.next_id = max(self.next_id, notif.id + 1)

            logger.info(f"Loaded {len(self.notifications)} notifications")

        except Exception as e:
            logger.error(f"Error loading notifications: {e}")

    def save(self):
        """Save notifications to YAML file."""
        try:
            data = {
                'notifications': [n.to_dict() for n in sorted(
                    self.notifications.values(), key=lambda n: n.id
                )]
            }

            with open(self.NOTIFICATION_FILE, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

            logger.debug(f"Saved {len(self.notifications)} notifications")

        except Exception as e:
            logger.error(f"Error saving notifications: {e}")

    def create(
        self,
        title: str,
        body: str,
        severity: str = 'important',
        source: str = 'crew',
        tags: Optional[List[str]] = None,
        auto_deliver: bool = True
    ) -> Notification:
        """Create and optionally deliver a notification.

        Args:
            title: Notification title
            body: Notification body/message
            severity: info, important, or urgent
            source: Who/what created this
            tags: Optional tags for filtering
            auto_deliver: Immediately deliver to channels

        Returns:
            Created notification object
        """
        notification = Notification(
            id=self.next_id,
            title=title,
            body=body,
            severity=severity,
            source=source,
            tags=tags or []
        )

        self.notifications[notification.id] = notification
        self.next_id += 1
        self.unread_count += 1

        logger.info(f"Created notification #{notification.id}: {title}")

        # Auto-deliver if requested
        if auto_deliver:
            self.deliver(notification.id)

        # Save to disk
        self._prune_if_needed()
        self.save()

        return notification

    def deliver(self, notif_id: int) -> bool:
        """Deliver a notification to all configured channels.

        Returns:
            True if all channels succeeded (or no channels configured)
        """
        notification = self.notifications.get(notif_id)
        if not notification:
            logger.warning(f"Notification #{notif_id} not found")
            return False

        if not self.channels:
            logger.debug(f"No channels configured, notification #{notif_id} not delivered")
            return True

        all_success = True
        for channel in self.channels:
            try:
                success = channel.send(notification.to_dict())
                if not success:
                    all_success = False
                    logger.warning(f"Failed to deliver notification #{notif_id} via {channel.__class__.__name__}")
            except Exception as e:
                all_success = False
                logger.error(f"Channel delivery error: {e}")

        if all_success:
            notification.delivered = True
            self.save()

        return all_success

    def mark_read(self, notif_id: int):
        """Mark notification as read."""
        if notif_id in self.notifications:
            # In a real system, would track read status
            if self.unread_count > 0:
                self.unread_count -= 1
            logger.debug(f"Marked notification #{notif_id} as read")

    def get(self, notif_id: int) -> Optional[Notification]:
        """Get a specific notification."""
        return self.notifications.get(notif_id)

    def get_all(self) -> List[Notification]:
        """Get all notifications, newest first."""
        return sorted(self.notifications.values(), key=lambda n: n.id, reverse=True)

    def get_unread(self) -> List[Notification]:
        """Get unread notifications (simplified: recent ones)."""
        # In full implementation, would track read status
        return self.get_all()[:10]  # Last 10

    def delete(self, notif_id: int):
        """Delete a notification."""
        if notif_id in self.notifications:
            del self.notifications[notif_id]
            self.save()
            logger.info(f"Deleted notification #{notif_id}")

    def _prune_if_needed(self):
        """Remove oldest notifications if exceeding max."""
        max_notifs = self.MAX_NOTIFICATIONS

        if len(self.notifications) > max_notifs:
            # Find oldest notifications to remove
            sorted_notifs = sorted(self.notifications.values(), key=lambda n: n.id)
            to_remove = sorted_notifs[:len(self.notifications) - max_notifs + 1]

            logger.info(f"Pruning {len(to_remove)} old notifications")
            for notif in to_remove:
                del self.notifications[notif.id]

    def stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        by_severity = {}
        by_source = {}

        for notif in self.notifications.values():
            by_severity[notif.severity] = by_severity.get(notif.severity, 0) + 1
            by_source[notif.source] = by_source.get(notif.source, 0) + 1

        return {
            'total_notifications': len(self.notifications),
            'unread': self.unread_count,
            'by_severity': by_severity,
            'by_source': by_source,
            'channels_configured': len(self.channels),
        }
