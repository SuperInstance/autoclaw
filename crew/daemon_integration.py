"""Integration of Phase A components into daemon.

This module provides the glue between:
- daemon.py (main loop)
- Phase A components (knowledge, triggers, notifications, handoff)
- Existing scheduler/runner/brain

Handles:
- Knowledge-aware experiment planning
- Knowledge creation from findings
- Trigger monitoring in background
- Notification delivery
- Context handoff for long tasks
- Multi-agent task dispatch (Phase B)
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from crew.knowledge_integration import get_knowledge_integration
from crew.scheduler_enhancement import get_scheduler_enhancement
from crew.triggers import TriggerDaemon
from crew.notifications import NotificationManager
from crew.handoff import get_handoff_manager

logger = logging.getLogger(__name__)


class DaemonIntegration:
    """Coordinates Phase A components with daemon.py."""

    def __init__(self):
        """Initialize all Phase A components."""
        self.knowledge_integration = get_knowledge_integration()
        self.scheduler_enhancement = get_scheduler_enhancement()
        self.trigger_daemon = TriggerDaemon()
        self.notification_manager = NotificationManager()
        self.handoff_manager = get_handoff_manager()
        
        # Track current task for context handoff
        self.current_task_id: Optional[int] = None
        self.current_task_generation: int = 1
        self.context_tokens_used: int = 0

    def start_background_services(self):
        """Start trigger daemon and other background threads."""
        try:
            self.trigger_daemon.start()
            logger.info("Started trigger daemon")
        except Exception as e:
            logger.error(f"Failed to start trigger daemon: {e}")

    def stop_background_services(self):
        """Stop background services gracefully."""
        try:
            self.trigger_daemon.stop()
            logger.info("Stopped trigger daemon")
        except Exception as e:
            logger.error(f"Error stopping trigger daemon: {e}")

    def enhance_experiment_planning(self, task: Any) -> Dict[str, Any]:
        """Get knowledge hints to enhance experiment planning.

        Args:
            task: Task object with experiment spec

        Returns:
            Dict with hints for planning
        """
        try:
            # Check if task is redundant
            if self.scheduler_enhancement.should_skip_redundant_task(task):
                logger.info(f"Task #{task.id} appears redundant - has high-confidence knowledge")
                return {'skip': True}

            # Get relevant knowledge
            hints = self.scheduler_enhancement.get_knowledge_hints_for_task(task)

            # Compute priority adjustment
            priority_adj = self.scheduler_enhancement.compute_task_priority_adjustment(task)

            return {
                'skip': False,
                'knowledge_hints': hints,
                'priority_adjustment': priority_adj
            }

        except Exception as e:
            logger.error(f"Error enhancing planning: {e}")
            return {'skip': False}

    def refine_parameters_with_knowledge(self, task: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Refine experiment parameters using knowledge.

        Args:
            task: Task object
            params: Original parameters from task.experiment

        Returns:
            Refined parameters informed by knowledge
        """
        try:
            hints = self.scheduler_enhancement.get_knowledge_hints_for_task(task)
            refined = self.scheduler_enhancement.refine_experiment_parameters(
                task, params, hints
            )
            return refined

        except Exception as e:
            logger.error(f"Error refining parameters: {e}")
            return params

    def create_knowledge_from_findings(self, task: Any, findings: List[str], 
                                      experiments_run: int, best_metric: Optional[float] = None):
        """Create knowledge entries from task findings.

        Args:
            task: Completed task
            findings: List of finding strings
            experiments_run: How many experiments ran
            best_metric: Best metric achieved
        """
        try:
            if not findings:
                return

            created_ids = self.knowledge_integration.create_knowledge_from_findings(
                task_id=task.id,
                findings=findings,
                experiments_run=experiments_run
            )

            logger.info(f"Created {len(created_ids)} knowledge entries from task #{task.id}")

            # Notify captain of new findings
            if created_ids:
                self.notify_findings(findings, task.id, created_ids)

        except Exception as e:
            logger.error(f"Error creating knowledge: {e}")

    def notify_findings(self, findings: List[str], task_id: int, knowledge_ids: List[int]):
        """Notify captain of new findings.

        Args:
            findings: List of finding strings
            task_id: Which task produced them
            knowledge_ids: IDs of created knowledge entries
        """
        try:
            title = f"New findings from task #{task_id}"
            body = "\n".join(f"• {f}" for f in findings[:3])  # First 3 findings
            
            if len(findings) > 3:
                body += f"\n... and {len(findings)-3} more"

            self.notification_manager.create(
                title=title,
                body=body,
                severity="important",
                source="crew",
                tags=["findings", f"task-{task_id}"],
                auto_deliver=True
            )

        except Exception as e:
            logger.error(f"Error notifying findings: {e}")

    def start_context_handoff(self, task_id: int):
        """Start context handoff for a task.

        Call this when a task begins.
        """
        try:
            self.current_task_id = task_id
            self.current_task_generation = 1
            self.context_tokens_used = 0

            # Check if task has a previous handoff (resuming)
            current = self.handoff_manager.get_current(task_id)
            if current:
                self.current_task_generation = current.generation + 1
                logger.info(f"Resuming task #{task_id} at generation {self.current_task_generation}")
                return self.handoff_manager.generate_summary_for_context(current)

            return None

        except Exception as e:
            logger.error(f"Error starting context handoff: {e}")
            return None

    def update_context_usage(self, tokens_used: int):
        """Update context token usage.

        Call this after each LLM invocation.
        """
        self.context_tokens_used += tokens_used

    def should_generate_handoff(self, context_limit: int = 8000) -> bool:
        """Check if it's time to generate context handoff.

        Args:
            context_limit: Total context window size

        Returns:
            True if should generate handoff (at 75% capacity)
        """
        return self.handoff_manager.should_handoff(self.context_tokens_used, context_limit)

    def generate_handoff(self, accomplishments: List[str], decisions: List[str],
                        next_steps: List[str], open_questions: List[str] = None):
        """Generate and save context handoff.

        Args:
            accomplishments: What was completed in this generation
            decisions: Key decisions made
            next_steps: What to do next
            open_questions: Questions that still need answers
        """
        try:
            if not self.current_task_id:
                logger.warning("No current task for handoff")
                return

            from crew.handoff import Accomplishment, Decision

            handoff = self.handoff_manager.create(
                task_id=self.current_task_id,
                generation=self.current_task_generation
            )

            # Add accomplishments
            for acc in accomplishments:
                handoff.accomplishments.append(
                    Accomplishment(description=acc, outcome="")
                )

            # Add decisions
            for dec in decisions:
                handoff.decisions.append(
                    Decision(decision=dec, rationale="")
                )

            # Add next steps
            handoff.next_steps = next_steps
            handoff.open_questions = open_questions or []
            handoff.context_tokens_used = self.context_tokens_used
            handoff.generation_duration_seconds = 300  # TODO: track real duration

            # Save
            self.handoff_manager.save(handoff)

            logger.info(f"Generated handoff for task #{self.current_task_id}, generation {self.current_task_generation}")

        except Exception as e:
            logger.error(f"Error generating handoff: {e}")

    def suggest_follow_up_studies(self) -> List[Dict[str, Any]]:
        """Get suggestions for follow-up study tasks.

        Returns:
            List of suggested study tasks
        """
        try:
            return self.scheduler_enhancement.suggest_follow_up_studies()
        except Exception as e:
            logger.error(f"Error suggesting studies: {e}")
            return []

    def check_for_trigger_events(self) -> List[Dict[str, Any]]:
        """Check if any triggers have fired (creates tasks).

        Returns:
            List of newly created task IDs
        """
        # Note: Trigger daemon runs in background thread
        # This method is for manual polling if needed
        try:
            stats = self.trigger_daemon.stats()
            logger.debug(f"Trigger stats: {stats}")
            # Real implementation would query task board for tasks created
            # in the last N seconds
            return []
        except Exception as e:
            logger.error(f"Error checking triggers: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get integrated stats from all Phase A components."""
        try:
            return {
                'knowledge': self.knowledge_integration.knowledge_store.stats(),
                'triggers': self.trigger_daemon.stats(),
                'notifications': self.notification_manager.stats(),
                'context': {
                    'current_task': self.current_task_id,
                    'generation': self.current_task_generation,
                    'tokens_used': self.context_tokens_used,
                }
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


# Singleton instance
_integration = None

def get_daemon_integration() -> DaemonIntegration:
    """Get or create global daemon integration."""
    global _integration
    if _integration is None:
        _integration = DaemonIntegration()
    return _integration
