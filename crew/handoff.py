"""Context Handoff / Baton Pattern: infinite-context operation.

Enables long-running tasks to continue without losing reasoning thread
when LLM context windows fill. Implements the "Baton" pattern:
- Track context usage during task execution
- Generate handoff document at ~75% capacity
- Resume next generation with handoff as context
- Maintain full lineage across generations

This allows tasks running 8+ hours to continue seamlessly across
multiple LLM invocations.
"""

import logging
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class Accomplishment:
    """Something concrete achieved in this generation."""

    description: str
    outcome: str
    evidence: List[str] = field(default_factory=list)  # commits, knowledge IDs, URLs


@dataclass
class Decision:
    """A decision made and its rationale."""

    decision: str  # What was decided
    rationale: str  # Why this decision
    alternatives: List[str] = field(default_factory=list)  # Other options considered
    confidence: str = "medium"  # low, medium, high


@dataclass
class ContextHandoff:
    """Baton passed between generations of task execution.

    When a long-running task's LLM context approaches capacity,
    this document is generated and passed to the next invocation.
    """

    # Identity
    task_id: int
    generation: int  # Which generation (1, 2, 3...)
    parent_handoff_id: Optional[str] = None  # Previous generation's ID

    # Accomplishments
    accomplishments: List[Accomplishment] = field(default_factory=list)

    # Decision rationale tree
    decisions: List[Decision] = field(default_factory=list)

    # What to do next
    next_steps: List[str] = field(default_factory=list)
    current_focus: str = ""  # Current area of investigation

    # Skills/capabilities discovered
    skills_extracted: List[str] = field(default_factory=list)

    # Open questions and concerns
    open_questions: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context_tokens_used: int = 0
    context_limit: int = 8000  # Typical for Claude Haiku
    generation_duration_seconds: int = 0

    @property
    def id(self) -> str:
        """Generate unique ID for this handoff."""
        return f"task{self.task_id}_gen{self.generation:03d}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        d = asdict(self)
        d['accomplishments'] = [asdict(a) for a in self.accomplishments]
        d['decisions'] = [asdict(d) for d in self.decisions]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextHandoff":
        """Create from dictionary (loaded from YAML)."""
        if 'accomplishments' in data:
            data['accomplishments'] = [
                Accomplishment(**a) if isinstance(a, dict) else a
                for a in data['accomplishments']
            ]
        if 'decisions' in data:
            data['decisions'] = [
                Decision(**d) if isinstance(d, dict) else d
                for d in data['decisions']
            ]
        return cls(**data)

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"=== HANDOFF BATON: Task #{self.task_id}, Generation {self.generation} ===",
            "",
            "ACCOMPLISHMENTS:",
            *[f"  • {a.description} → {a.outcome}" for a in self.accomplishments],
            "",
            "DECISIONS:",
            *[f"  • {d.decision}: {d.rationale}" for d in self.decisions],
            "",
            "NEXT STEPS:",
            *[f"  • {s}" for s in self.next_steps],
            "",
            "SKILLS DISCOVERED:",
            *[f"  • {s}" for s in self.skills_extracted],
            "",
            "OPEN QUESTIONS:",
            *[f"  • {q}" for q in self.open_questions],
            "",
            "CONTEXT USAGE:",
            f"  Tokens: {self.context_tokens_used} / {self.context_limit}",
            f"  Duration: {self.generation_duration_seconds}s",
        ]
        return "\n".join(lines)


class HandoffManager:
    """Manages context handoffs for long-running tasks."""

    HANDOFFS_DIR = Path("data/handoffs")

    def __init__(self):
        """Initialize handoff manager."""
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Ensure handoff directory exists."""
        self.HANDOFFS_DIR.mkdir(parents=True, exist_ok=True)

    def create(self, task_id: int, generation: int = 1,
              parent_handoff_id: Optional[str] = None) -> ContextHandoff:
        """Create a new handoff document."""
        handoff = ContextHandoff(
            task_id=task_id,
            generation=generation,
            parent_handoff_id=parent_handoff_id
        )
        logger.info(f"Created handoff: {handoff.id}")
        return handoff

    def save(self, handoff: ContextHandoff):
        """Save handoff to YAML file."""
        task_dir = self.HANDOFFS_DIR / f"task{handoff.task_id}"
        task_dir.mkdir(parents=True, exist_ok=True)

        handoff_file = task_dir / f"{handoff.id}.yaml"
        current_link = task_dir / "CURRENT"

        try:
            # Save handoff
            with open(handoff_file, 'w') as f:
                yaml.dump(handoff.to_dict(), f, default_flow_style=False, sort_keys=False)

            # Update CURRENT symlink
            if current_link.exists():
                current_link.unlink()
            current_link.symlink_to(handoff_file.name)

            logger.info(f"Saved handoff: {handoff.id}")

        except Exception as e:
            logger.error(f"Error saving handoff: {e}")

    def load(self, task_id: int, generation: Optional[int] = None) -> Optional[ContextHandoff]:
        """Load a handoff document.

        Args:
            task_id: Which task's handoff
            generation: Which generation (None = load CURRENT)

        Returns:
            ContextHandoff or None if not found
        """
        task_dir = self.HANDOFFS_DIR / f"task{task_id}"

        if not task_dir.exists():
            return None

        try:
            if generation is None:
                # Load CURRENT
                current_link = task_dir / "CURRENT"
                if not current_link.exists():
                    return None
                handoff_file = current_link.resolve()
            else:
                # Load specific generation
                handoff_id = f"task{task_id}_gen{generation:03d}"
                handoff_file = task_dir / f"{handoff_id}.yaml"

            if not handoff_file.exists():
                return None

            with open(handoff_file, 'r') as f:
                data = yaml.safe_load(f)
                handoff = ContextHandoff.from_dict(data)
                logger.info(f"Loaded handoff: {handoff.id}")
                return handoff

        except Exception as e:
            logger.error(f"Error loading handoff: {e}")
            return None

    def get_current(self, task_id: int) -> Optional[ContextHandoff]:
        """Get the current (latest) handoff for a task."""
        return self.load(task_id, generation=None)

    def list_generations(self, task_id: int) -> List[int]:
        """List all generations available for a task."""
        task_dir = self.HANDOFFS_DIR / f"task{task_id}"

        if not task_dir.exists():
            return []

        generations = []
        for file in task_dir.glob("task*.yaml"):
            try:
                # Parse generation number from filename
                gen_str = file.stem.split("_gen")[-1]
                gen = int(gen_str)
                generations.append(gen)
            except:
                pass

        return sorted(generations)

    def should_handoff(self, context_tokens_used: int, context_limit: int = 8000) -> bool:
        """Check if it's time to generate a handoff.

        Args:
            context_tokens_used: Tokens used so far in this conversation
            context_limit: Total context window size

        Returns:
            True if tokens exceed 75% of limit
        """
        threshold = int(context_limit * 0.75)
        should_hand = context_tokens_used > threshold

        if should_hand:
            logger.info(f"Context usage {context_tokens_used} > threshold {threshold}. Time to handoff.")

        return should_hand

    def generate_summary_for_context(self, handoff: ContextHandoff) -> str:
        """Generate a concise summary to include in next context.

        This is what gets passed to the LLM to resume the task.
        """
        return f"""
PREVIOUS CONTEXT HANDOFF
========================

Task: #{handoff.task_id} (Generation {handoff.generation})

WHAT WAS ACCOMPLISHED:
{chr(10).join('- ' + a.description + ': ' + a.outcome for a in handoff.accomplishments)}

KEY DECISIONS:
{chr(10).join('- ' + d.decision + ': ' + d.rationale for d in handoff.decisions)}

NEXT STEPS:
{chr(10).join('- ' + s for s in handoff.next_steps)}

CURRENT FOCUS:
{handoff.current_focus}

OPEN QUESTIONS:
{chr(10).join('- ' + q for q in handoff.open_questions)}

Continue from where you left off. You have the full context above.
=================================================================
"""


# Singleton instance
_manager = None

def get_handoff_manager() -> HandoffManager:
    """Get or create global handoff manager."""
    global _manager
    if _manager is None:
        _manager = HandoffManager()
    return _manager
