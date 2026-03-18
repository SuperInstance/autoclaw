"""Knowledge store: persistent learning system for the crew.

This module provides:
  - YAML-backed persistence of knowledge entries
  - Query interface (by tags, category, confidence, status)
  - Lifecycle management (aging, supersession, pruning)
  - Contradiction detection across entries
  - Confidence scoring

Knowledge entries are stored at: data/crew/knowledge.yaml
Max 500 entries. When full, oldest low-confidence entries are pruned.
"""

import yaml
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence levels for knowledge entries."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class KnowledgeStatus(str, Enum):
    """Status of a knowledge entry."""
    ACTIVE = "active"
    OUTDATED = "outdated"
    QUESTIONED = "questioned"


@dataclass
class KnowledgeEntry:
    """A single insight the crew has learned."""

    id: int
    insight: str
    category: str  # hyperparameter, architecture, training_dynamics, data, infrastructure, methodology, external
    tags: List[str] = field(default_factory=list)

    # Evidence
    source_task_ids: List[int] = field(default_factory=list)
    experiments_supporting: int = 0
    experiments_contradicting: int = 0
    key_commits: List[str] = field(default_factory=list)

    # Confidence
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    conditions: Optional[str] = None  # When this insight holds

    # Lifecycle
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    superseded_by: Optional[int] = None

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_validated: Optional[str] = None

    # Relations
    related_entries: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        d = asdict(self)
        # Convert enums to strings
        d['confidence'] = self.confidence.value
        d['status'] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeEntry":
        """Create from dictionary (loaded from YAML)."""
        # Convert string enums back to enum types
        if isinstance(data['confidence'], str):
            data['confidence'] = ConfidenceLevel(data['confidence'])
        if isinstance(data['status'], str):
            data['status'] = KnowledgeStatus(data['status'])
        return cls(**data)


class KnowledgeStore:
    """Persistent knowledge base for the crew."""

    MAX_ENTRIES = 500
    STORE_FILE = Path("data/crew/knowledge.yaml")

    def __init__(self):
        """Initialize knowledge store."""
        self.entries: Dict[int, KnowledgeEntry] = {}
        self.next_id = 1
        self._lock = threading.Lock()
        self._ensure_dir()
        self.load()

    def _ensure_dir(self):
        """Ensure data directory exists."""
        self.STORE_FILE.parent.mkdir(parents=True, exist_ok=True)

    def load(self):
        """Load knowledge from YAML file."""
        if not self.STORE_FILE.exists():
            logger.info("Knowledge store not found, starting fresh")
            return

        try:
            with open(self.STORE_FILE, 'r') as f:
                data = yaml.safe_load(f) or {}

            entries = data.get('entries', [])
            for entry_data in entries:
                entry = KnowledgeEntry.from_dict(entry_data)
                self.entries[entry.id] = entry
                self.next_id = max(self.next_id, entry.id + 1)

            logger.info(f"Loaded {len(self.entries)} knowledge entries")
        except Exception as e:
            logger.error(f"Error loading knowledge store: {e}")

    def save(self):
        """Save knowledge to YAML file."""
        try:
            data = {
                'entries': [entry.to_dict() for entry in sorted(
                    self.entries.values(), key=lambda e: e.id
                )]
            }

            with open(self.STORE_FILE, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

            logger.debug(f"Saved {len(self.entries)} knowledge entries")
        except Exception as e:
            logger.error(f"Error saving knowledge store: {e}")

    def create(
        self,
        insight: str,
        category: str,
        tags: List[str],
        source_task_ids: List[int],
        experiments_supporting: int,
        experiments_contradicting: int = 0,
        key_commits: Optional[List[str]] = None,
        conditions: Optional[str] = None,
    ) -> KnowledgeEntry:
        """Create a new knowledge entry."""
        with self._lock:
            # Auto-determine confidence based on evidence
            confidence = self._score_confidence(
                experiments_supporting,
                experiments_contradicting
            )

            entry = KnowledgeEntry(
                id=self.next_id,
                insight=insight,
                category=category,
                tags=tags,
                source_task_ids=source_task_ids,
                experiments_supporting=experiments_supporting,
                experiments_contradicting=experiments_contradicting,
                key_commits=key_commits or [],
                confidence=confidence,
                conditions=conditions,
            )

            self.entries[entry.id] = entry
            self.next_id += 1

            # Check if we need to prune
            if len(self.entries) > self.MAX_ENTRIES:
                self._prune_entries()

            self.save()
            logger.info(f"Created knowledge entry #{entry.id}: {insight[:50]}...")
            return entry

    def _score_confidence(self, supporting: int, contradicting: int) -> ConfidenceLevel:
        """Determine confidence level based on evidence."""
        if supporting == 0:
            return ConfidenceLevel.LOW

        if contradicting > 0:
            ratio = contradicting / (supporting + contradicting)
            if ratio > 0.3:  # More than 30% contradicting
                return ConfidenceLevel.LOW

        if supporting == 1 or supporting == 2:
            return ConfidenceLevel.LOW
        elif supporting < 6:
            return ConfidenceLevel.MEDIUM
        elif contradicting == 0:
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.VERY_HIGH

    def update(self, entry_id: int, **updates) -> Optional[KnowledgeEntry]:
        """Update a knowledge entry."""
        with self._lock:
            if entry_id not in self.entries:
                logger.warning(f"Knowledge entry #{entry_id} not found")
                return None

            entry = self.entries[entry_id]

            # Convert enum updates
            if 'confidence' in updates and isinstance(updates['confidence'], str):
                updates['confidence'] = ConfidenceLevel(updates['confidence'])
            if 'status' in updates and isinstance(updates['status'], str):
                updates['status'] = KnowledgeStatus(updates['status'])

            # Apply updates
            for key, value in updates.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)

            entry.last_validated = datetime.now(timezone.utc).isoformat()
            self.save()
            logger.info(f"Updated knowledge entry #{entry.id}")
            return entry

    def query(
        self,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        min_confidence: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[KnowledgeEntry]:
        """Query knowledge by various criteria.

        Args:
            tags: Match ANY of these tags (OR logic)
            category: Match exact category
            min_confidence: Minimum confidence level (low, medium, high, very_high)
            status: Filter by status (active, outdated, questioned)

        Returns:
            List of matching entries, sorted by confidence (highest first)
        """
        with self._lock:
            results = []

            confidence_levels = {
                'low': 0,
                'medium': 1,
                'high': 2,
                'very_high': 3,
            }
            min_conf_value = confidence_levels.get(min_confidence, -1) if min_confidence else -1

            for entry in self.entries.values():
                # Filter by status
                if status and entry.status.value != status:
                    continue

                # Filter by category
                if category and entry.category != category:
                    continue

                # Filter by confidence
                if min_confidence:
                    entry_conf_value = confidence_levels.get(entry.confidence.value, 0)
                    if entry_conf_value < min_conf_value:
                        continue

                # Filter by tags (ANY match)
                if tags:
                    if not any(tag in entry.tags for tag in tags):
                        continue

                results.append(entry)

            # Sort by confidence (highest first), then by creation date (newest first)
            confidence_order = {'very_high': 4, 'high': 3, 'medium': 2, 'low': 1}
            results.sort(
                key=lambda e: (
                    -confidence_order.get(e.confidence.value, 0),
                    -e.id  # Newest first
                )
            )

            return results

    def get(self, entry_id: int) -> Optional[KnowledgeEntry]:
        """Get a specific knowledge entry by ID."""
        with self._lock:
            return self.entries.get(entry_id)

    def mark_outdated(self, entry_id: int, replaced_by: int):
        """Mark an entry as outdated, replaced by another."""
        if entry_id not in self.entries:
            return

        self.update(
            entry_id,
            status=KnowledgeStatus.OUTDATED,
            superseded_by=replaced_by
        )

    def mark_questioned(self, entry_id: int):
        """Mark an entry as questioned (needs re-testing)."""
        if entry_id not in self.entries:
            return

        self.update(entry_id, status=KnowledgeStatus.QUESTIONED)

    def _prune_entries(self):
        """Remove oldest low-confidence entries when max reached."""
        logger.info(f"Knowledge store at capacity ({len(self.entries)}). Pruning...")

        # Find entries to remove: old, low-confidence, active
        candidates = [
            e for e in self.entries.values()
            if e.status == KnowledgeStatus.ACTIVE
            and e.confidence in [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM]
        ]

        # Sort by age (oldest first)
        candidates.sort(key=lambda e: e.created_at)

        # Remove oldest 10%
        num_to_remove = max(1, len(self.entries) // 10)
        for entry in candidates[:num_to_remove]:
            logger.info(f"Pruning entry #{entry.id}: {entry.insight[:40]}...")
            del self.entries[entry.id]

        self.save()

    def detect_contradictions(self, entry_id: int) -> List[int]:
        """Find other entries that contradict this one."""
        with self._lock:
            if entry_id not in self.entries:
                return []

            entry = self.entries[entry_id]
            contradictions = []

            for other_entry in self.entries.values():
                if other_entry.id == entry_id:
                    continue

                # Same category and overlapping tags?
                if entry.category == other_entry.category:
                    if any(tag in other_entry.tags for tag in entry.tags):
                        if self._are_contradictory(entry.insight, other_entry.insight):
                            contradictions.append(other_entry.id)

            return contradictions

    def _are_contradictory(self, insight1: str, insight2: str) -> bool:
        """Heuristic check for contradictory insights."""
        insight1_lower = insight1.lower()
        insight2_lower = insight2.lower()

        opposites = [
            ("improve", "degrade"),
            ("increase", "decrease"),
            ("better", "worse"),
            ("optimal", "suboptimal"),
        ]

        for word1, word2 in opposites:
            if word1 in insight1_lower and word2 in insight2_lower:
                return True
            if word2 in insight1_lower and word1 in insight2_lower:
                return True

        return False

    def cleanup_old_entries(self, days: int = 30):
        """Mark entries as outdated if not validated in N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        for entry in self.entries.values():
            if entry.status == KnowledgeStatus.ACTIVE:
                if entry.last_validated:
                    last_val = datetime.fromisoformat(entry.last_validated)
                    if last_val < cutoff:
                        logger.info(f"Entry #{entry.id} not validated in {days} days. Marking questioned.")
                        self.mark_questioned(entry.id)
                elif datetime.fromisoformat(entry.created_at) < cutoff:
                    logger.info(f"Entry #{entry.id} never validated. Marking questioned.")
                    self.mark_questioned(entry.id)

        self.save()

    def stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        with self._lock:
            by_confidence = {}
            by_status = {}
            by_category = {}

            for entry in self.entries.values():
                by_confidence[entry.confidence.value] = by_confidence.get(entry.confidence.value, 0) + 1
                by_status[entry.status.value] = by_status.get(entry.status.value, 0) + 1
                by_category[entry.category] = by_category.get(entry.category, 0) + 1

            return {
                'total_entries': len(self.entries),
                'by_confidence': by_confidence,
                'by_status': by_status,
                'by_category': by_category,
            }
