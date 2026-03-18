"""RSS/Atom feed trigger handler.

Polls RSS feeds and creates tasks when entries match filter criteria.
"""

try:
    import feedparser
except ImportError:
    # Feedparser may have compatibility issues with newer Python versions
    feedparser = None

import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class RSSHandler:
    """Handles RSS/Atom feed monitoring."""

    def __init__(self, trigger_id: int, config: Dict[str, Any]):
        """Initialize RSS handler.

        Args:
            trigger_id: Unique trigger ID
            config: Trigger configuration (from trigger.yaml)
                - source.url: Feed URL
                - filter.keywords: Keywords to match (ANY)
                - filter.exclude_keywords: Keywords to exclude (ANY)
                - filter.max_fires_per_day: Rate limit
                - filter.cooldown_minutes: Minimum between fires
        """
        self.trigger_id = trigger_id
        self.config = config
        self.url = config.get('source', {}).get('url')
        self.seen_hashes = set()
        self.last_fire_time: Optional[datetime] = None
        self._load_seen_hashes()

    def _load_seen_hashes(self):
        """Load hashes of previously seen entries (to avoid duplicates)."""
        cache_file = Path(f"data/triggers/{self.trigger_id}_rss.hashes")
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self.seen_hashes = set(line.strip() for line in f if line.strip())
                logger.debug(f"Loaded {len(self.seen_hashes)} seen RSS entries")
            except Exception as e:
                logger.error(f"Error loading RSS cache: {e}")

    def _save_seen_hashes(self):
        """Save hashes to avoid re-processing."""
        cache_file = Path(f"data/triggers/{self.trigger_id}_rss.hashes")
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(cache_file, 'w') as f:
                for hash_val in sorted(self.seen_hashes):
                    f.write(f"{hash_val}\n")
            logger.debug(f"Saved {len(self.seen_hashes)} RSS entry hashes")
        except Exception as e:
            logger.error(f"Error saving RSS cache: {e}")

    def check(self) -> List[Dict[str, Any]]:
        """Check feed for new matching entries.

        Returns:
            List of trigger events matching filter criteria
        """
        if feedparser is None:
            logger.warning(f"Trigger #{self.trigger_id}: feedparser not available")
            return []

        if not self.url:
            logger.warning(f"Trigger #{self.trigger_id}: No RSS URL configured")
            return []

        try:
            logger.debug(f"Polling RSS feed: {self.url}")
            feed = feedparser.parse(self.url)

            if feed.status == 401 or feed.status == 403:
                logger.error(f"RSS feed authentication failed: {self.url}")
                return []

            if feed.status >= 400:
                logger.warning(f"RSS feed error ({feed.status}): {self.url}")
                return []

            if not feed.entries:
                logger.debug(f"No entries in RSS feed: {self.url}")
                return []

            events = []
            for entry in feed.entries:
                event = self._check_entry(entry)
                if event:
                    events.append(event)

            logger.info(f"RSS trigger #{self.trigger_id}: Found {len(events)} matching entries")
            self._save_seen_hashes()
            return events

        except Exception as e:
            logger.error(f"Error polling RSS feed {self.url}: {e}")
            return []

    def _check_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if a single entry matches filter criteria.

        Returns:
            Trigger event dict if matches, None otherwise
        """
        # Get entry ID (use link or title as fallback)
        entry_id = entry.get('id') or entry.get('link') or entry.get('title')
        if not entry_id:
            return None

        # Check if we've seen this before
        entry_hash = hashlib.sha256(entry_id.encode()).hexdigest()
        if entry_hash in self.seen_hashes:
            return None

        # Extract content
        title = entry.get('title', '')
        summary = entry.get('summary', '')[:500]  # First 500 chars
        link = entry.get('link', '')
        content = f"{title} {summary}".lower()

        # Check cooldown
        if self._check_cooldown():
            return None

        # Check filters
        if not self._matches_filters(content, title):
            return None

        # Mark as seen
        self.seen_hashes.add(entry_hash)

        # Return event
        return {
            'title': title,
            'url': link,
            'summary': summary,
            'content': content,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

    def _matches_filters(self, content: str, title: str) -> bool:
        """Check if entry matches keyword filters.

        Returns:
            True if entry matches criteria
        """
        filter_config = self.config.get('filter', {})
        keywords = filter_config.get('keywords', [])
        exclude_keywords = filter_config.get('exclude_keywords', [])

        # Check exclude keywords first (MUST NOT match ANY)
        if exclude_keywords:
            for keyword in exclude_keywords:
                if keyword.lower() in content.lower():
                    return False

        # If keywords specified, content MUST match at least ONE
        if keywords:
            matched = False
            for keyword in keywords:
                if keyword.lower() in content.lower():
                    matched = True
                    break
            return matched

        # No filters specified = accept all
        return True

    def _check_cooldown(self) -> bool:
        """Check if trigger has fired too recently (cooldown).

        Returns:
            True if in cooldown (should skip), False if OK to fire
        """
        filter_config = self.config.get('filter', {})
        cooldown_minutes = filter_config.get('cooldown_minutes', 30)

        if not self.last_fire_time:
            return False

        elapsed = datetime.now(timezone.utc) - self.last_fire_time
        if elapsed < timedelta(minutes=cooldown_minutes):
            logger.debug(f"RSS trigger #{self.trigger_id}: In cooldown ({cooldown_minutes} min)")
            return True

        return False

    def on_fired(self):
        """Update state when trigger fires."""
        self.last_fire_time = datetime.now(timezone.utc)
