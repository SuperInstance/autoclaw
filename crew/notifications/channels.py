"""Notification delivery channels (webhook, email, command, file)."""

import logging
import subprocess
import json
import requests
import smtplib
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Abstract base for notification delivery channels."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize channel with config."""
        self.config = config
        self.min_severity = config.get('min_severity', 'important')

    @abstractmethod
    def send(self, notification: Dict[str, Any]) -> bool:
        """Send notification via this channel."""
        pass

    def _severity_ok(self, severity: str) -> bool:
        """Check if notification meets minimum severity threshold."""
        severity_levels = {'info': 0, 'important': 1, 'urgent': 2}
        min_level = severity_levels.get(self.min_severity, 1)
        notification_level = severity_levels.get(severity, 0)
        return notification_level >= min_level


class WebhookChannel(NotificationChannel):
    """Deliver notifications via HTTP webhook."""

    def send(self, notification: Dict[str, Any]) -> bool:
        """POST notification to webhook URL."""
        if not self._severity_ok(notification.get('severity', 'info')):
            return True  # Filtered, not an error

        url = self.config.get('url')
        if not url:
            logger.warning("Webhook channel: No URL configured")
            return False

        try:
            headers = self.config.get('headers', {})
            headers['Content-Type'] = 'application/json'

            response = requests.post(
                url,
                json=notification,
                headers=headers,
                timeout=10
            )

            if response.status_code >= 400:
                logger.error(f"Webhook failed ({response.status_code}): {url}")
                return False

            logger.info(f"Webhook delivered: {notification.get('title', 'notification')}")
            return True

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return False


class CommandChannel(NotificationChannel):
    """Deliver notifications by executing a shell command."""

    def send(self, notification: Dict[str, Any]) -> bool:
        """Execute shell command with notification JSON on stdin."""
        if not self._severity_ok(notification.get('severity', 'info')):
            return True

        command = self.config.get('command')
        if not command:
            logger.warning("Command channel: No command configured")
            return False

        try:
            # Pass notification as JSON on stdin
            notification_json = json.dumps(notification)
            result = subprocess.run(
                command,
                input=notification_json,
                shell=True,
                capture_output=True,
                timeout=30,
                text=True
            )

            if result.returncode != 0:
                logger.warning(f"Command returned {result.returncode}: {result.stderr}")
                return False

            logger.info(f"Command executed: {command}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {command}")
            return False
        except Exception as e:
            logger.error(f"Command error: {e}")
            return False


class EmailChannel(NotificationChannel):
    """Deliver notifications via email (SMTP)."""

    def send(self, notification: Dict[str, Any]) -> bool:
        """Send notification via email."""
        if not self._severity_ok(notification.get('severity', 'info')):
            return True

        # Check required config
        smtp_host = self.config.get('smtp_host')
        smtp_port = self.config.get('smtp_port', 587)
        to_address = self.config.get('to_address')
        from_address = self.config.get('from_address')

        if not all([smtp_host, to_address, from_address]):
            logger.warning("Email channel: Missing SMTP configuration")
            return False

        try:
            # Build message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{notification.get('severity', 'info').upper()}] {notification.get('title', 'Notification')}"
            msg['From'] = from_address
            msg['To'] = to_address
            msg['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

            # Text body
            text_body = f"{notification.get('body', '')}\n\n--- AutoClaw Notification ---\nTime: {notification.get('timestamp', '')}"
            msg.attach(MIMEText(text_body, 'plain'))

            # HTML body
            html_body = f"""
            <html><body>
              <h2>{notification.get('title', 'Notification')}</h2>
              <p>{notification.get('body', '')}</p>
              <hr>
              <p><em>AutoClaw Notification - {notification.get('timestamp', '')}</em></p>
            </body></html>
            """
            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                # Optional: add authentication if needed
                server.sendmail(from_address, [to_address], msg.as_string())

            logger.info(f"Email sent to {to_address}: {notification.get('title', 'notification')}")
            return True

        except Exception as e:
            logger.error(f"Email error: {e}")
            return False


class FileChannel(NotificationChannel):
    """Log notifications to a file."""

    def send(self, notification: Dict[str, Any]) -> bool:
        """Append notification to file."""
        if not self._severity_ok(notification.get('severity', 'info')):
            return True

        filepath = self.config.get('path')
        if not filepath:
            logger.warning("File channel: No path configured")
            return False

        try:
            # Ensure parent directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Append to file
            with open(filepath, 'a') as f:
                timestamp = notification.get('timestamp', datetime.utcnow().isoformat())
                severity = notification.get('severity', 'info').upper()
                title = notification.get('title', 'notification')
                body = notification.get('body', '')

                f.write(f"\n[{timestamp}] {severity}: {title}\n")
                f.write(f"{body}\n")
                f.write("-" * 80 + "\n")

            logger.debug(f"File logged: {filepath}")
            return True

        except Exception as e:
            logger.error(f"File channel error: {e}")
            return False


def create_channel(channel_type: str, config: Dict[str, Any]) -> Optional[NotificationChannel]:
    """Factory: create appropriate channel by type."""
    if channel_type == 'webhook':
        return WebhookChannel(config)
    elif channel_type == 'email':
        return EmailChannel(config)
    elif channel_type == 'command':
        return CommandChannel(config)
    elif channel_type == 'file':
        return FileChannel(config)
    else:
        logger.warning(f"Unknown notification channel type: {channel_type}")
        return None
