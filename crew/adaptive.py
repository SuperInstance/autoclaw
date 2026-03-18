"""Adaptive scheduler using Thompson sampling.

Learns which research directions produce the best ROI (results) over time.

The scheduler maintains a Beta distribution for each research direction,
updated based on:
- Task outcomes (success rate)
- Findings produced (knowledge entries)
- Time and compute efficiency
- Discovery novelty (new knowledge vs. validation)

Thompson sampling balances exploration (trying new directions) with
exploitation (focusing on proven directions).

Usage:
    scheduler = AdaptiveScheduler()
    # At task creation time:
    priority_boost = scheduler.compute_priority_adjustment(task)
    task.priority += priority_boost

    # At task completion:
    scheduler.update_from_task_result(task, findings, success_rate)

    # Periodically:
    recommendations = scheduler.suggest_research_directions()
"""

import logging
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
import yaml

logger = logging.getLogger(__name__)


@dataclass
class BetaDistribution:
    """Beta distribution parameters for a research direction.

    Represents uncertainty about the probability that a task in this
    direction will produce valuable findings.

    Alpha and beta are shape parameters:
    - alpha = number of "successes" (found valuable insights)
    - beta = number of "failures" (task didn't produce insights)
    """

    alpha: float = 1.0  # Successes
    beta: float = 1.0  # Failures
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def sample(self) -> float:
        """Draw a sample from the Beta distribution.

        Returns: A value between 0 and 1 representing estimated value
        """
        return np.random.beta(self.alpha, self.beta)

    def mean(self) -> float:
        """Get the mean of the distribution."""
        return self.alpha / (self.alpha + self.beta)

    def variance(self) -> float:
        """Get the variance (uncertainty) of the distribution."""
        denom = (self.alpha + self.beta) ** 2 * (self.alpha + self.beta + 1)
        return (self.alpha * self.beta) / denom if denom > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for YAML serialization."""
        return {
            "alpha": float(self.alpha),
            "beta": float(self.beta),
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BetaDistribution":
        """Load from dict."""
        return cls(
            alpha=d.get("alpha", 1.0),
            beta=d.get("beta", 1.0),
            last_updated=d.get("last_updated", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class ResearchDirection:
    """A research direction being tracked by the adaptive scheduler.

    Examples:
    - "transformer_optimization"
    - "training_efficiency"
    - "knowledge_distillation"
    """

    name: str
    value_distribution: BetaDistribution = field(default_factory=BetaDistribution)
    tasks_attempted: int = 0
    findings_produced: int = 0
    discoveries_produced: int = 0  # Novel findings (new knowledge entries)
    compute_hours_spent: float = 0.0
    roi_score: float = 0.0  # Findings per compute hour

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for YAML serialization."""
        return {
            "name": self.name,
            "value_distribution": self.value_distribution.to_dict(),
            "tasks_attempted": self.tasks_attempted,
            "findings_produced": self.findings_produced,
            "discoveries_produced": self.discoveries_produced,
            "compute_hours_spent": self.compute_hours_spent,
            "roi_score": self.roi_score,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResearchDirection":
        """Load from dict."""
        return cls(
            name=d.get("name", "unknown"),
            value_distribution=BetaDistribution.from_dict(d.get("value_distribution", {})),
            tasks_attempted=d.get("tasks_attempted", 0),
            findings_produced=d.get("findings_produced", 0),
            discoveries_produced=d.get("discoveries_produced", 0),
            compute_hours_spent=d.get("compute_hours_spent", 0.0),
            roi_score=d.get("roi_score", 0.0),
        )


class AdaptiveScheduler:
    """Learns which research directions are most productive.

    Maintains a portfolio of research directions with learned value
    distributions. Uses Thompson sampling to balance exploring new
    directions with exploiting known-good ones.
    """

    PERSIST_FILE = Path("data/adaptive_scheduler.yaml")

    def __init__(self):
        """Initialize adaptive scheduler."""
        self.directions: Dict[str, ResearchDirection] = {}
        self._total_samples_drawn = 0
        self._load()

    def _load(self):
        """Load scheduler state from disk."""
        if not self.PERSIST_FILE.exists():
            return

        try:
            data = yaml.safe_load(self.PERSIST_FILE.read_text()) or {}
            directions = data.get("directions", {})

            for name, dir_data in directions.items():
                self.directions[name] = ResearchDirection.from_dict(dir_data)

            logger.info(f"Loaded adaptive scheduler with {len(self.directions)} directions")
        except Exception as e:
            logger.error(f"Error loading adaptive scheduler: {e}")

    def _save(self):
        """Save scheduler state to disk."""
        try:
            self.PERSIST_FILE.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "directions": {
                    name: dir_obj.to_dict()
                    for name, dir_obj in self.directions.items()
                },
                "total_samples": self._total_samples_drawn,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            self.PERSIST_FILE.write_text(yaml.dump(data, default_flow_style=False))
        except Exception as e:
            logger.error(f"Error saving adaptive scheduler: {e}")

    def compute_priority_adjustment(
        self, task: Any
    ) -> float:
        """Compute priority adjustment for a task based on research direction.

        Higher-value directions get boosted priority.

        Args:
            task: Task object with tags/category

        Returns:
            Priority boost (0 to 2.0)
        """
        direction_name = self._extract_direction(task)

        if not direction_name:
            return 0.0

        # Ensure direction exists
        if direction_name not in self.directions:
            self.directions[direction_name] = ResearchDirection(name=direction_name)

        direction = self.directions[direction_name]

        # Base boost on mean value (0.5 = no boost, 1.0 = high boost)
        mean_value = direction.value_distribution.mean()
        boost = mean_value * 2.0  # Scale to 0-2.0 range

        logger.debug(f"Priority boost for {direction_name}: +{boost:.2f}")
        return boost

    def update_from_task_result(
        self,
        task: Any,
        findings: List[str],
        success_rate: float = 1.0,
        compute_hours: float = 0.1,
        num_knowledge_entries: int = 0,
    ):
        """Update direction value distribution based on task results.

        Args:
            task: Completed task
            findings: List of findings produced
            success_rate: Fraction of experiments that succeeded (0-1)
            compute_hours: CPU/GPU hours spent
            num_knowledge_entries: Number of new knowledge entries created
        """
        direction_name = self._extract_direction(task)

        if not direction_name:
            return

        if direction_name not in self.directions:
            self.directions[direction_name] = ResearchDirection(name=direction_name)

        direction = self.directions[direction_name]

        # Update statistics
        direction.tasks_attempted += 1
        direction.findings_produced += len(findings)
        direction.discoveries_produced += num_knowledge_entries
        direction.compute_hours_spent += compute_hours

        # Compute ROI
        if compute_hours > 0:
            direction.roi_score = direction.findings_produced / direction.compute_hours_spent

        # Update Beta distribution
        # Treat "success" as producing findings, "failure" as not
        if len(findings) > 0:
            direction.value_distribution.alpha += success_rate
        else:
            direction.value_distribution.beta += (1.0 - success_rate)

        direction.value_distribution.last_updated = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"Updated {direction_name}: "
            f"tasks={direction.tasks_attempted}, "
            f"findings={direction.findings_produced}, "
            f"roi={direction.roi_score:.2f}"
        )

        self._save()

    def suggest_research_directions(
        self, num_suggestions: int = 3
    ) -> List[Dict[str, Any]]:
        """Suggest high-potential research directions.

        Uses Thompson sampling to balance exploration and exploitation.

        Returns:
            List of suggested directions with rationale
        """
        if not self.directions:
            return []

        # Sample from each direction's distribution
        samples = {}
        for name, direction in self.directions.items():
            sample_value = direction.value_distribution.sample()
            samples[name] = sample_value
            self._total_samples_drawn += 1

        # Sort by sampled value (exploit the best, explore uncertain ones)
        ranked = sorted(samples.items(), key=lambda x: x[1], reverse=True)

        suggestions = []
        for name, sample_value in ranked[:num_suggestions]:
            direction = self.directions[name]
            mean = direction.value_distribution.mean()
            variance = direction.value_distribution.variance()

            suggestions.append({
                "direction": name,
                "estimated_value": float(sample_value),
                "mean_value": float(mean),
                "uncertainty": float(variance) ** 0.5,
                "roi": float(direction.roi_score),
                "tasks_tried": direction.tasks_attempted,
                "findings": direction.findings_produced,
                "discoveries": direction.discoveries_produced,
                "rationale": (
                    f"Thompson sample={sample_value:.2f}, "
                    f"mean={mean:.2f}, "
                    f"roi={direction.roi_score:.2f} findings/hour"
                ),
            })

        return suggestions

    def _extract_direction(self, task: Any) -> Optional[str]:
        """Extract research direction from task.

        Looks for tags, category, or title keywords that indicate
        the research direction.

        Args:
            task: Task object

        Returns:
            Direction name or None
        """
        # Try tags first
        if hasattr(task, "tags") and task.tags:
            # First tag is usually the primary direction
            return task.tags[0] if isinstance(task.tags, list) else str(task.tags)

        # Try description/title keywords
        if hasattr(task, "description"):
            desc = str(task.description).lower()

            # Common research direction keywords
            keywords = {
                "transformer": "transformer_optimization",
                "attention": "attention_mechanisms",
                "efficient": "training_efficiency",
                "distill": "knowledge_distillation",
                "quantiz": "quantization",
                "pruning": "model_pruning",
                "scaling": "scaling_laws",
                "optimization": "optimization_methods",
                "loss": "loss_functions",
                "regulariz": "regularization",
            }

            for keyword, direction in keywords.items():
                if keyword in desc:
                    return direction

        return None

    def stats(self) -> Dict[str, Any]:
        """Get statistics about tracked directions."""
        return {
            "total_directions": len(self.directions),
            "directions": [d.to_dict() for d in self.directions.values()],
            "total_samples_drawn": self._total_samples_drawn,
        }


# Singleton
_adaptive_scheduler = None


def get_adaptive_scheduler() -> AdaptiveScheduler:
    """Get or create global adaptive scheduler instance."""
    global _adaptive_scheduler
    if _adaptive_scheduler is None:
        _adaptive_scheduler = AdaptiveScheduler()
    return _adaptive_scheduler
