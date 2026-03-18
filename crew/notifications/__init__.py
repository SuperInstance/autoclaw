"""Notification delivery system.

Routes notifications to captain via multiple channels:
- Webhook (HTTP POST)
- Email (SMTP)
- Shell command execution
- File logging
"""

from crew.notifications.manager import NotificationManager
from crew.notifications.channels import NotificationChannel

__all__ = ['NotificationManager', 'NotificationChannel']
