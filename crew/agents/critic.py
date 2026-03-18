"""Critic agent — challenges assumptions and quality-scores outputs.

The critic is the crew's adversarial thinker. It:
  1. Reviews knowledge entries and challenges weak ones
  2. Rates training data quality
  3. Finds contradictions in the knowledge base
  4. Generates adversarial test questions

Runs with lower priority by default — critic work is valuable but
not time-critical like research or training data generation.
"""

import re
import json
import logging
from typing import Optional, List, Dict, Any

from crew.agents.base import BaseAgent
from crew.messaging.bus import Message

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    """Agent that challenges knowledge and quality-scores training data."""

    ROLE = "critic"
    DEFAULT_PRIORITY = 7  # Lower priority than researcher/teacher

    def get_capabilities(self) -> List[str]:
        return [
            "fact_check",
            "devil_advocate",
            "consistency_check",
            "quality_score",
            "edge_case_finder",
        ]

    def process_message(self, message: Message) -> Optional[Message]:
        """Process a message needing criticism.

        - training_data: Quality-score and optionally reject
        - knowledge: Challenge if weak evidence
        - result: Fact-check findings
        """
        if message.type == "training_data":
            return self._review_training_data(message)
        elif message.type == "knowledge":
            return self._review_knowledge(message)
        elif message.type == "result":
            return self._fact_check_result(message)
        return None

    def _review_training_data(self, message: Message) -> Optional[Message]:
        """Score training data quality and flag bad examples."""
        payload = message.payload
        examples = payload.get("examples", [])
        topic = payload.get("source_topic", "")

        if not examples:
            return None

        self.logger.info(
            f"Reviewing {len(examples)} training examples for: {topic}"
        )

        reviewed = []
        rejected_count = 0

        for example in examples:
            score, issues = self._score_example(example, topic)
            example["quality_score"] = score
            example["critic_notes"] = issues
            example["accepted"] = score >= 0.5

            if not example["accepted"]:
                rejected_count += 1
            reviewed.append(example)

        accepted = [e for e in reviewed if e["accepted"]]
        avg_quality = (
            sum(e["quality_score"] for e in accepted) / len(accepted)
            if accepted else 0.0
        )

        self.logger.info(
            f"Reviewed {len(examples)} examples: "
            f"{len(accepted)} accepted, {rejected_count} rejected, "
            f"avg quality={avg_quality:.2f}"
        )

        return Message(
            from_agent=self.agent_id,
            to_agent=message.from_agent,
            type="quality_rating",
            priority=message.priority,
            payload={
                "original_message_id": message.id,
                "examples_reviewed": len(examples),
                "examples_accepted": len(accepted),
                "examples_rejected": rejected_count,
                "avg_quality": round(avg_quality, 2),
                "reviewed_examples": reviewed,
                "dataset_tag": payload.get("dataset_tag"),
            },
            tags=message.tags,
        )

    def _review_knowledge(self, message: Message) -> Optional[Message]:
        """Challenge a knowledge entry if confidence seems unwarranted."""
        entry = message.payload.get("entry", {})
        insight = entry.get("insight", "")
        confidence = entry.get("confidence", "low")
        evidence = entry.get("evidence", {})

        if not insight:
            return None

        experiments = evidence.get("experiments_supporting", 0)

        # Challenge if confidence is high but evidence is thin
        should_challenge = False
        challenge_reason = ""

        if confidence == "very_high" and experiments < 5:
            should_challenge = True
            challenge_reason = f"very_high confidence with only {experiments} experiments"
        elif confidence == "high" and experiments < 3:
            should_challenge = True
            challenge_reason = f"high confidence with only {experiments} experiments"
        elif "not yet validated" in insight.lower() or "unvalidated" in insight.lower():
            should_challenge = True
            challenge_reason = "Insight notes it is unvalidated"

        if should_challenge:
            self.logger.info(f"Challenging knowledge entry: {challenge_reason}")
            return Message(
                from_agent=self.agent_id,
                to_agent="daemon",
                type="challenge",
                priority=6,
                payload={
                    "challenges": [challenge_reason],
                    "counter_evidence": [],
                    "severity": "minor",
                    "recommendation": "verify",
                    "knowledge_insight": insight[:100],
                },
                tags=message.tags,
            )

        return None

    def _fact_check_result(self, message: Message) -> Optional[Message]:
        """Spot-check a research result for obvious errors."""
        payload = message.payload
        summary = payload.get("summary", "")
        confidence = payload.get("confidence", "low")

        # Only deeply fact-check high-confidence results
        if confidence not in ("high", "very_high"):
            return None

        issues = self._find_obvious_issues(summary)

        if issues:
            return Message(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                type="challenge",
                priority=message.priority,
                payload={
                    "challenges": issues,
                    "counter_evidence": [],
                    "severity": "minor",
                    "recommendation": "review",
                },
                tags=message.tags,
            )

        return None

    # ========================================================================
    # Scoring Logic
    # ========================================================================

    def _score_example(self, example: Dict, topic: str) -> tuple[float, List[str]]:
        """Score a training example 0.0-1.0 with identified issues.

        Args:
            example: Training example dict
            topic: Topic for relevance check

        Returns: (score, list_of_issues)
        """
        score = 1.0
        issues = []

        # Get the text fields
        if "question" in example and "answer" in example:
            question = example.get("question", "")
            answer = example.get("answer", "")
        elif "instruction" in example and "output" in example:
            question = example.get("instruction", "")
            answer = example.get("output", "")
        elif "prompt" in example and "completion" in example:
            question = example.get("prompt", "")
            answer = example.get("completion", "")
        else:
            return 0.3, ["Unknown format — missing expected fields"]

        # Length checks
        if len(question) < 10:
            score -= 0.3
            issues.append("Question too short (<10 chars)")

        if len(answer) < 20:
            score -= 0.4
            issues.append("Answer too short (<20 chars)")

        if len(answer) > 5000:
            score -= 0.1
            issues.append("Answer very long (>5000 chars)")

        # Quality indicators
        vague_phrases = [
            "it depends", "various factors", "many things", "quite complex",
            "as mentioned", "as noted above",
        ]
        for phrase in vague_phrases:
            if phrase in answer.lower():
                score -= 0.05
                issues.append(f"Vague phrase: '{phrase}'")

        # Check relevance to topic
        topic_words = set(topic.lower().split())
        combined_text = (question + " " + answer).lower()
        relevance = sum(1 for w in topic_words if w in combined_text)
        if relevance == 0 and len(topic_words) > 0:
            score -= 0.2
            issues.append(f"Not relevant to topic: {topic}")

        # Penalize for template markers
        template_markers = ["{topic}", "{sentence}", "INSERT", "FILL_IN"]
        for marker in template_markers:
            if marker in question or marker in answer:
                score -= 0.5
                issues.append(f"Contains template placeholder: {marker}")

        # Use existing quality_score from generator if present
        gen_score = example.get("quality_score")
        if gen_score is not None:
            # Blend generator's self-assessment with our checks
            score = (score * 0.6) + (float(gen_score) * 0.4)

        return max(0.0, min(1.0, score)), issues

    def _find_obvious_issues(self, text: str) -> List[str]:
        """Find obvious factual issues in a text (heuristic)."""
        issues = []

        # Check for very specific numbers that might be wrong
        # (This is very heuristic — just looks for suspicious patterns)
        if re.search(r"\b(100|1000|10000)%\b", text):
            issues.append("Contains suspicious percentage claim (100/1000/10000%)")

        # Check for contradictory statements
        contradictions = [
            ("always", "never"),
            ("increases", "decreases"),
            ("improves", "worsens"),
        ]
        for pos, neg in contradictions:
            if pos in text.lower() and neg in text.lower():
                issues.append(f"Contains potentially contradictory terms: '{pos}' and '{neg}'")
                break

        return issues
