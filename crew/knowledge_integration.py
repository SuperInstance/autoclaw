"""Integration layer between Brain and Knowledge Store.

This module handles:
- Querying knowledge for experiment planning
- Creating knowledge entries from findings
- Maintaining knowledge lifecycle
- Confidence scoring from evidence

Separate module to avoid modifying existing brain.py.
"""

import logging
from typing import List, Dict, Any, Optional

from crew.knowledge import get_knowledge_store

logger = logging.getLogger(__name__)


class KnowledgeIntegration:
    """Integrates Knowledge Store with Brain/Scheduler."""

    def __init__(self):
        """Initialize integration."""
        self.knowledge_store = get_knowledge_store()

    def get_relevant_knowledge(self, task_title: str, tags: List[str] = None) -> List[Dict[str, Any]]:
        """Get relevant knowledge entries for experiment planning.

        Args:
            task_title: Task description
            tags: Optional tags to search for

        Returns:
            List of relevant knowledge entries (by confidence)
        """
        # Extract likely topics from task title
        if tags is None:
            tags = self._extract_tags_from_title(task_title)

        # Query knowledge store
        entries = self.knowledge_store.query(
            tags=tags,
            status='active',
            min_confidence='medium'  # Only use medium+ confidence
        )

        logger.info(f"Found {len(entries)} relevant knowledge entries for task: {task_title}")
        return [self._entry_to_dict(e) for e in entries]

    def create_knowledge_from_findings(self, task_id: int, findings: List[str],
                                      experiments_run: int, best_metric: Optional[float] = None) -> List[int]:
        """Create knowledge entries from task findings.

        Args:
            task_id: The task that generated these findings
            findings: List of finding strings
            experiments_run: How many experiments were run
            best_metric: The best metric value achieved

        Returns:
            List of created knowledge entry IDs
        """
        created_ids = []

        for finding in findings:
            try:
                # Extract insight and tags from finding text
                insight, tags = self._parse_finding(finding)

                # Auto-determine category based on keywords
                category = self._categorize_finding(finding)

                # Create entry with minimal evidence (will be updated as more experiments validate)
                entry = self.knowledge_store.create(
                    insight=insight,
                    category=category,
                    tags=tags,
                    source_task_ids=[task_id],
                    experiments_supporting=min(experiments_run, 3),  # Conservative
                    experiments_contradicting=0,
                    conditions=f"Based on {experiments_run} experiments"
                )

                created_ids.append(entry.id)
                logger.info(f"Created knowledge entry #{entry.id} from finding: {insight[:50]}...")

            except Exception as e:
                logger.error(f"Error creating knowledge entry: {e}")

        return created_ids

    def update_knowledge_from_validation(self, entry_id: int, experiments_supporting: int,
                                        experiments_contradicting: int = 0):
        """Update knowledge entry with new validation evidence.

        Called when a finding is validated by new experiments.
        """
        entry = self.knowledge_store.get(entry_id)
        if not entry:
            logger.warning(f"Knowledge entry #{entry_id} not found")
            return

        # Update evidence counts
        total_supporting = entry.experiments_supporting + experiments_supporting
        total_contradicting = entry.experiments_contradicting + experiments_contradicting

        # Update confidence based on total evidence
        self.knowledge_store.update(
            entry_id,
            experiments_supporting=total_supporting,
            experiments_contradicting=total_contradicting
        )

        logger.info(f"Updated knowledge entry #{entry_id}: {total_supporting} supporting, "
                   f"{total_contradicting} contradicting")

    def detect_conflicting_knowledge(self, new_entry_id: int) -> List[Dict[str, Any]]:
        """Find knowledge entries that contradict a new finding.

        Returns:
            List of conflicting entries with details
        """
        contradictions = self.knowledge_store.detect_contradictions(new_entry_id)

        result = []
        for contra_id in contradictions:
            entry = self.knowledge_store.get(contra_id)
            if entry:
                result.append({
                    'id': entry.id,
                    'insight': entry.insight,
                    'confidence': entry.confidence.value,
                    'status': entry.status.value,
                })

        if result:
            logger.warning(f"Found {len(result)} contradictions for entry #{new_entry_id}")

        return result

    def suggest_knowledge_validation(self) -> List[Dict[str, Any]]:
        """Suggest which knowledge entries should be validated by new experiments.

        Returns:
            List of knowledge entries that need re-testing
        """
        # Find entries that haven't been validated recently
        candidates = []

        for entry in self.knowledge_store.entries.values():
            if entry.status == 'questioned':
                candidates.append(entry)
            elif entry.status == 'active' and entry.confidence.value in ['low', 'medium']:
                # These should be validated more
                candidates.append(entry)

        # Sort by importance (high impact findings first)
        candidates.sort(key=lambda e: (
            -{'very_high': 4, 'high': 3, 'medium': 2, 'low': 1}.get(e.confidence.value, 0),
            e.id  # Oldest first
        ))

        result = []
        for entry in candidates[:5]:  # Top 5
            result.append({
                'entry_id': entry.id,
                'insight': entry.insight,
                'confidence': entry.confidence.value,
                'status': entry.status.value,
                'reason': self._validation_reason(entry)
            })

        return result

    def _extract_tags_from_title(self, title: str) -> List[str]:
        """Extract likely tags from task title."""
        # Simple heuristic: split on common words
        keywords = ['learning-rate', 'batch-size', 'warmup', 'weight-decay',
                   'depth', 'architecture', 'optimizer', 'attention', 'transformer']

        found_tags = []
        title_lower = title.lower()

        for keyword in keywords:
            if keyword in title_lower:
                found_tags.append(keyword)

        return found_tags if found_tags else ['general']

    def _parse_finding(self, finding: str) -> tuple[str, List[str]]:
        """Parse a finding string into insight and tags."""
        # For now, use the whole finding as insight
        # In practice, could use NLP to extract key points

        insight = finding
        tags = []

        # Extract tags from finding text (heuristic)
        finding_lower = finding.lower()
        if 'learning rate' in finding_lower or 'lr' in finding_lower:
            tags.append('learning-rate')
        if 'batch' in finding_lower:
            tags.append('batch-size')
        if 'warmup' in finding_lower:
            tags.append('warmup')
        if 'weight decay' in finding_lower:
            tags.append('weight-decay')
        if 'depth' in finding_lower:
            tags.append('depth')
        if 'optimizer' in finding_lower:
            tags.append('optimizer')

        if not tags:
            tags = ['general']

        return insight[:500], tags  # Limit insight to 500 chars

    def _categorize_finding(self, finding: str) -> str:
        """Determine category for a finding."""
        finding_lower = finding.lower()

        if any(w in finding_lower for w in ['learning rate', 'batch', 'weight decay', 'optimizer']):
            return 'hyperparameter'
        elif any(w in finding_lower for w in ['architecture', 'depth', 'layer', 'head']):
            return 'architecture'
        elif any(w in finding_lower for w in ['stable', 'diverge', 'converge', 'overfitting']):
            return 'training_dynamics'
        elif any(w in finding_lower for w in ['data', 'sample', 'distribution']):
            return 'data'
        else:
            return 'methodology'

    def _entry_to_dict(self, entry) -> Dict[str, Any]:
        """Convert KnowledgeEntry to dictionary for return."""
        return {
            'id': entry.id,
            'insight': entry.insight,
            'category': entry.category,
            'confidence': entry.confidence.value,
            'conditions': entry.conditions,
            'experiments_supporting': entry.experiments_supporting,
        }

    def _validation_reason(self, entry) -> str:
        """Generate reason for validating an entry."""
        if entry.status == 'questioned':
            return "Contradicted by new evidence, needs re-testing"
        elif entry.confidence.value == 'low':
            return "Low confidence, needs more evidence"
        else:
            return "Medium confidence, could be strengthened"


# Singleton instance
_integration = None

def get_knowledge_integration() -> KnowledgeIntegration:
    """Get or create global knowledge integration."""
    global _integration
    if _integration is None:
        _integration = KnowledgeIntegration()
    return _integration
