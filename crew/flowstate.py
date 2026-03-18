"""Flowstate: Sandbox exploration mode for safe experimentation.

Flowstate allows the crew to explore risky research directions in isolation:
- Experiments run in a sandboxed environment
- Results don't affect the main knowledge base until promotion
- Failed experiments don't block ongoing research
- Novel discoveries can be carefully validated before integration

Usage:
    # Enter flowstate for exploratory task
    flow = FlowStateManager.create("Explore mixed precision training", budget_gb=10)

    # Run experiments in sandbox (results not saved to knowledge yet)
    result = runner.run_experiment(params, task_id=flow.task_id, sandbox=flow.id)

    # If promising, promote findings to main knowledge
    promoted = flow.promote_findings(
        findings=["Mixed precision reduces memory by 40%"],
        confidence="medium",
        validation_tasks=[1, 2, 3]  # Which validation tasks validated this
    )

    # If not promising, discard
    flow.discard()

Design:
  - Separate YAML storage: data/flowstate/{id}/
  - Isolated checkpoint directory: data/flowstate/{id}/checkpoints/
  - Results tracked but not in main knowledge until promoted
  - Promotion requires evidence link to main tasks
  - Automatic GC: discard sandboxes older than N days
"""

import logging
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class FlowStateTask:
    """A sandbox exploration task."""

    id: str  # Unique sandbox ID
    title: str
    description: Optional[str] = None
    parent_task_id: Optional[int] = None  # If started from a regular task
    budget_gb: float = 10.0  # Max storage for this sandbox
    budget_hours: float = 4.0  # Max runtime for this sandbox
    max_experiments: int = 20

    # State
    status: str = "active"  # active | promoting | promoted | discarded
    created_at: str = ""
    completed_at: Optional[str] = None

    # Results
    experiments_run: int = 0
    experiments_successful: int = 0
    findings: List[str] = None
    failures: List[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.findings is None:
            self.findings = []
        if self.failures is None:
            self.failures = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for YAML."""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FlowStateTask":
        """Load from dict."""
        return cls(**{k: v for k, v in d.items() if k in [
            'id', 'title', 'description', 'parent_task_id', 'budget_gb',
            'budget_hours', 'max_experiments', 'status', 'created_at',
            'completed_at', 'experiments_run', 'experiments_successful',
            'findings', 'failures'
        ]})


class FlowStateManager:
    """Manages sandbox exploration tasks."""

    BASE_DIR = Path("data/flowstate")

    def __init__(self):
        """Initialize flowstate manager."""
        self.base_dir = self.BASE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._active_tasks: Dict[str, FlowStateTask] = {}
        self._load_active()

    def _load_active(self):
        """Load all active flowstate tasks from disk."""
        if not self.base_dir.exists():
            return

        for task_dir in self.base_dir.glob("*"):
            if not task_dir.is_dir():
                continue

            state_file = task_dir / "state.yaml"
            if state_file.exists():
                try:
                    data = yaml.safe_load(state_file.read_text())
                    task = FlowStateTask.from_dict(data)
                    if task.status == "active":
                        self._active_tasks[task.id] = task
                except Exception as e:
                    logger.warning(f"Error loading flowstate task {task_dir.name}: {e}")

    def _save_task(self, task: FlowStateTask):
        """Save flowstate task to disk."""
        task_dir = self.base_dir / task.id
        task_dir.mkdir(parents=True, exist_ok=True)

        state_file = task_dir / "state.yaml"
        state_file.write_text(yaml.dump(task.to_dict(), default_flow_style=False))

    def create(
        self,
        title: str,
        description: Optional[str] = None,
        parent_task_id: Optional[int] = None,
        budget_gb: float = 10.0,
        budget_hours: float = 4.0,
        max_experiments: int = 20,
    ) -> FlowStateTask:
        """Create a new sandbox exploration task.

        Args:
            title: Human-readable title
            description: Longer description
            parent_task_id: If this sandbox was spawned from a regular task
            budget_gb: Max storage for sandbox
            budget_hours: Max runtime for sandbox
            max_experiments: Max experiments to run

        Returns:
            FlowStateTask
        """
        # Generate unique ID
        import uuid
        task_id = f"flow_{uuid.uuid4().hex[:12]}"

        task = FlowStateTask(
            id=task_id,
            title=title,
            description=description,
            parent_task_id=parent_task_id,
            budget_gb=budget_gb,
            budget_hours=budget_hours,
            max_experiments=max_experiments,
        )

        self._active_tasks[task_id] = task
        self._save_task(task)

        logger.info(f"Created flowstate task {task_id}: {title}")
        return task

    def get(self, task_id: str) -> Optional[FlowStateTask]:
        """Get a flowstate task by ID."""
        return self._active_tasks.get(task_id)

    def get_checkpoint_dir(self, task_id: str) -> Path:
        """Get the checkpoint directory for a sandbox task."""
        checkpoint_dir = self.base_dir / task_id / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir

    def record_experiment(
        self,
        task_id: str,
        success: bool,
        result_summary: str = "",
    ) -> bool:
        """Record an experiment run in a sandbox.

        Args:
            task_id: Sandbox task ID
            success: Whether the experiment succeeded
            result_summary: Brief summary of results

        Returns:
            True if recorded, False if sandbox doesn't exist
        """
        task = self._active_tasks.get(task_id)
        if not task:
            logger.warning(f"Flowstate task {task_id} not found")
            return False

        task.experiments_run += 1
        if success:
            task.experiments_successful += 1

        if result_summary:
            task.findings.append(result_summary)

        # Check limits
        if task.experiments_run >= task.max_experiments:
            logger.info(f"Flowstate task {task_id} reached max experiments")
            task.status = "complete"
            task.completed_at = datetime.now(timezone.utc).isoformat()

        self._save_task(task)
        return True

    def promote_findings(
        self,
        task_id: str,
        findings: List[str],
        confidence: str = "medium",
        validation_task_ids: Optional[List[int]] = None,
    ) -> List[int]:
        """Promote findings from sandbox to main knowledge base.

        Args:
            task_id: Sandbox task ID
            findings: List of findings to promote
            confidence: Confidence level (low, medium, high)
            validation_task_ids: IDs of tasks that validated these findings

        Returns:
            List of created knowledge entry IDs
        """
        task = self._active_tasks.get(task_id)
        if not task:
            logger.warning(f"Flowstate task {task_id} not found")
            return []

        from crew.knowledge_integration import get_knowledge_integration

        ki = get_knowledge_integration()

        created_ids = []
        for finding in findings:
            entry_id = ki.knowledge_store.create(
                insight=finding,
                category="methodology",  # Sandbox findings are usually methodological
                tags=["flowstate", f"sandbox-{task_id[:8]}"],
                source_task_ids=validation_task_ids or [],
                experiments_supporting=task.experiments_successful,
                experiments_contradicting=0,
                conditions=f"Discovered in sandbox exploration: {task.title}",
            )
            created_ids.append(entry_id.id if hasattr(entry_id, 'id') else entry_id)

        task.status = "promoted"
        task.completed_at = datetime.now(timezone.utc).isoformat()
        self._save_task(task)

        logger.info(f"Promoted {len(created_ids)} findings from sandbox {task_id}")
        return created_ids

    def discard(self, task_id: str):
        """Discard a sandbox task without promoting findings.

        Args:
            task_id: Sandbox task ID to discard
        """
        task = self._active_tasks.pop(task_id, None)
        if not task:
            logger.warning(f"Flowstate task {task_id} not found")
            return

        task.status = "discarded"
        task.completed_at = datetime.now(timezone.utc).isoformat()

        # Save discarded task for audit trail
        self._save_task(task)

        # Optionally clean up checkpoint directory
        checkpoint_dir = self.base_dir / task_id / "checkpoints"
        if checkpoint_dir.exists():
            import shutil
            try:
                shutil.rmtree(checkpoint_dir)
                logger.info(f"Cleaned up checkpoint directory for {task_id}")
            except Exception as e:
                logger.warning(f"Could not clean up checkpoints for {task_id}: {e}")

    def cleanup_old_sandboxes(self, days: int = 7):
        """Remove old completed sandboxes (older than N days).

        Args:
            days: Age threshold in days
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        for task_id, task in list(self._active_tasks.items()):
            if task.status in ["promoted", "discarded"]:
                completed_dt = datetime.fromisoformat(task.completed_at) if task.completed_at else None
                if completed_dt and completed_dt < cutoff:
                    # Remove directory
                    task_dir = self.base_dir / task_id
                    import shutil
                    try:
                        shutil.rmtree(task_dir)
                        del self._active_tasks[task_id]
                        logger.info(f"Cleaned up old flowstate task {task_id}")
                    except Exception as e:
                        logger.warning(f"Error cleaning up flowstate {task_id}: {e}")

    def stats(self) -> Dict[str, Any]:
        """Get statistics about active sandboxes."""
        active = [t for t in self._active_tasks.values() if t.status == "active"]
        promoted = [t for t in self._active_tasks.values() if t.status == "promoted"]
        discarded = [t for t in self._active_tasks.values() if t.status == "discarded"]

        return {
            "active_sandboxes": len(active),
            "promoted_sandboxes": len(promoted),
            "discarded_sandboxes": len(discarded),
            "total_experiments_run": sum(t.experiments_run for t in self._active_tasks.values()),
            "total_successful": sum(t.experiments_successful for t in self._active_tasks.values()),
            "active_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "experiments": t.experiments_run,
                    "findings": len(t.findings),
                }
                for t in active
            ],
        }


# Singleton
_flowstate_manager = None


def get_flowstate_manager() -> FlowStateManager:
    """Get or create global flowstate manager."""
    global _flowstate_manager
    if _flowstate_manager is None:
        _flowstate_manager = FlowStateManager()
    return _flowstate_manager
