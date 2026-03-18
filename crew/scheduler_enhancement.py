"""Scheduler enhancement: integrate knowledge in task planning.

Extends existing scheduler with knowledge-aware parameter selection
and dynamic prioritization based on learning.
"""

import logging
from typing import List, Dict, Any, Tuple

from crew.knowledge_integration import get_knowledge_integration

logger = logging.getLogger(__name__)


class SchedulerEnhancement:
    """Enhances scheduler with knowledge-driven planning."""

    def __init__(self):
        """Initialize enhancement."""
        self.knowledge_integration = get_knowledge_integration()

    def get_knowledge_hints_for_task(self, task) -> Dict[str, Any]:
        """Get knowledge hints to improve experiment planning.

        Args:
            task: Task object

        Returns:
            Dict with hints for planning: parameter_suggestions, avoid_configs, etc.
        """
        hints = {
            'relevant_knowledge': [],
            'parameter_suggestions': {},
            'avoid_configurations': [],
            'recommended_baseline': None,
        }

        # Get relevant knowledge
        relevant = self.knowledge_integration.get_relevant_knowledge(task.title)

        if not relevant:
            logger.debug(f"No relevant knowledge for task #{task.id}")
            return hints

        hints['relevant_knowledge'] = relevant

        # Extract parameter suggestions from knowledge
        for entry in relevant:
            insight = entry['insight'].lower()

            # Parse insight for parameter values
            suggestions = self._extract_parameter_suggestions(insight)
            if suggestions:
                hints['parameter_suggestions'].update(suggestions)

            # Look for "avoid" patterns
            if 'avoid' in insight or 'not recommended' in insight or 'poor' in insight:
                hints['avoid_configurations'].append(entry['insight'])

        logger.info(f"Found {len(hints['relevant_knowledge'])} knowledge hints for task #{task.id}")

        return hints

    def refine_experiment_parameters(self, task, experiment_params: Dict[str, Any],
                                    knowledge_hints: Dict[str, Any]) -> Dict[str, Any]:
        """Refine experiment parameters using knowledge.

        Uses knowledge to:
        - Suggest good starting values
        - Warn about known bad configurations
        - Set tighter search ranges (based on prior findings)

        Args:
            task: Task object
            experiment_params: Original experiment parameters
            knowledge_hints: Hints from get_knowledge_hints_for_task()

        Returns:
            Refined experiment parameters
        """
        refined = dict(experiment_params)

        # Apply parameter suggestions from knowledge
        suggestions = knowledge_hints.get('parameter_suggestions', {})
        for param, value in suggestions.items():
            if param in refined:
                # Knowledge suggests this parameter
                if isinstance(refined[param], list):
                    # If it's a search range, use suggestion as starting point
                    logger.info(f"Knowledge suggests {param}={value}, narrowing range")
                    refined[param] = [value] if not isinstance(value, list) else value
                else:
                    refined[param] = value

        return refined

    def compute_task_priority_adjustment(self, task) -> float:
        """Compute priority adjustment based on knowledge.

        Returns:
            Adjustment factor (-1.0 to +1.0):
              negative = lower priority (less important)
              positive = higher priority (more important)
        """
        adjustment = 0.0

        # Check if this task relates to knowledge we're uncertain about
        relevant = self.knowledge_integration.get_relevant_knowledge(task.title)

        uncertain_entries = [e for e in relevant if e['confidence'] in ['low', 'medium']]
        if uncertain_entries:
            # This task addresses uncertain knowledge → boost priority
            adjustment += min(0.5, len(uncertain_entries) * 0.1)
            logger.debug(f"Task #{task.id}: +{adjustment} priority adjustment (addresses {len(uncertain_entries)} uncertain items)")

        return adjustment

    def should_skip_redundant_task(self, task) -> bool:
        """Check if task would be redundant with recent findings.

        Returns:
            True if task seems redundant (already well-understood)
        """
        # Get knowledge entries relevant to this task
        relevant = self.knowledge_integration.get_relevant_knowledge(task.title)

        # If we have very high confidence entries covering this area, might be redundant
        high_confidence = [e for e in relevant if e['confidence'] == 'very_high']

        if len(high_confidence) >= 3:
            logger.info(f"Task #{task.id} may be redundant ({len(high_confidence)} high-confidence entries)")
            return True

        return False

    def suggest_follow_up_studies(self) -> List[Dict[str, Any]]:
        """Suggest follow-up study tasks based on knowledge gaps.

        Returns:
            List of suggested study tasks
        """
        suggestions = []

        # Get validation suggestions
        validation_needed = self.knowledge_integration.suggest_knowledge_validation()

        for item in validation_needed:
            suggestion = {
                'title': f"Validate: {item['insight'][:50]}...",
                'description': f"Re-test knowledge entry #{item['entry_id']}: {item['insight']}. Reason: {item['reason']}",
                'type': 'study',
                'priority': 8,  # Medium priority
                'tags': ['knowledge-validation'],
                'source': {
                    'creator': 'crew',
                    'trigger_id': None,
                    'parent_task_id': None,
                    'reason': f"Knowledge validation: {item['reason']}"
                }
            }
            suggestions.append(suggestion)

        logger.info(f"Suggested {len(suggestions)} follow-up study tasks")
        return suggestions

    def _extract_parameter_suggestions(self, insight_text: str) -> Dict[str, Any]:
        """Extract parameter values from insight text.

        Heuristic parsing of insights like:
          "LR=0.005 optimal"
          "batch size 64 shows best convergence"
          "learning rate between 0.003 and 0.008"
        """
        suggestions = {}
        text = insight_text.lower()

        # Simple patterns
        if 'lr=' in text or 'learning rate=' in text:
            import re
            match = re.search(r'lr\s*=\s*([\d.]+)', text)
            if match:
                try:
                    suggestions['learning_rate'] = float(match.group(1))
                except:
                    pass

        if 'batch' in text and 'size' in text:
            import re
            match = re.search(r'batch\s*size\s*(?:of\s+)?([\d]+)', text)
            if match:
                try:
                    suggestions['batch_size'] = int(match.group(1))
                except:
                    pass

        if 'warmup' in text:
            import re
            match = re.search(r'warmup\s*(?:steps?\s+)?(?:of\s+)?([\d]+)', text)
            if match:
                try:
                    suggestions['warmup_steps'] = int(match.group(1))
                except:
                    pass

        return suggestions


# Singleton instance
_enhancement = None

def get_scheduler_enhancement() -> SchedulerEnhancement:
    """Get or create global scheduler enhancement."""
    global _enhancement
    if _enhancement is None:
        _enhancement = SchedulerEnhancement()
    return _enhancement
