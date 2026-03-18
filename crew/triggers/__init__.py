"""External event triggers for the crew.

Monitors external sources and creates tasks when events match:
- RSS feeds (new papers, news)
- Webhooks (external events)
- Schedules (cron-style)
- Sensors (GPU temp, disk usage)
- File watching (changes)
- Commands (custom logic)
"""

from crew.triggers.daemon import TriggerDaemon

__all__ = ['TriggerDaemon']
