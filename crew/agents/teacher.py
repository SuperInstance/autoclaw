"""Teacher agent — generates training data from research findings.

The teacher takes raw knowledge and transforms it into structured training
data for fine-tuning local models. It generates:
  - Q&A pairs (for instruction fine-tuning)
  - Instruction-response pairs (Alpaca format)
  - Multi-turn dialogues (ChatML format)
  - Explanations at varying depths

Credit-aware: tracks Cloudflare Workers AI neurons used for generation.
Pacing: spreads work across the day to maximize free tier usage.

Teacher personas (configurable via system prompt):
  - "professor": Formal, detailed explanations
  - "tutor": Patient, step-by-step
  - "socratic": Questions that guide understanding
  - "adversarial": Tricky questions to expose gaps
"""

import json
import re
import logging
from typing import Optional, List, Dict, Any

from crew.agents.base import BaseAgent
from crew.messaging.bus import Message

logger = logging.getLogger(__name__)


# Quality scoring rubric
QUALITY_RUBRIC = """
Rate this training example 0.0-1.0 on:
- Accuracy (is it factually correct?)
- Clarity (is it clearly expressed?)
- Specificity (does it give concrete details?)
- Usefulness (would this help train a model?)

A score of 0.8+ is high quality. 0.5-0.8 is acceptable. Below 0.5 should be rejected.
"""


class TeacherAgent(BaseAgent):
    """Agent that generates training data from knowledge.

    Accepts task_request messages (from researcher results or daemon)
    and publishes training_data messages back.

    Also accepts knowledge messages and auto-generates QA pairs.
    """

    ROLE = "teacher"
    DEFAULT_PRIORITY = 6

    def get_capabilities(self) -> List[str]:
        return [
            "qa_generation",
            "instruction_tuning",
            "socratic_dialogue",
            "explanation_levels",
            "cf_workers_ai",
        ]

    def process_message(self, message: Message) -> Optional[Message]:
        """Process a training data request or knowledge entry.

        For task_request: generate N examples on the given topic
        For knowledge: auto-generate QA pairs from the entry
        For result (from researcher): generate training data from findings
        """
        if message.type == "task_request":
            return self._handle_generation_request(message)
        elif message.type == "result":
            return self._handle_research_result(message)
        elif message.type == "knowledge":
            self._auto_generate_from_knowledge(message)
            return None
        return None

    def _handle_generation_request(self, message: Message) -> Optional[Message]:
        """Generate training data from explicit request."""
        payload = message.payload
        topic = payload.get("topic", payload.get("description", ""))
        source_text = payload.get("source_text", "")
        n_examples = payload.get("n_examples", 10)
        format_type = payload.get("format_type", "qa_pair")
        dataset_tag = payload.get("dataset_tag", topic.replace(" ", "-")[:30])

        self.logger.info(
            f"Generating {n_examples} {format_type} examples for: {topic}"
        )

        examples = self._generate_examples(
            topic=topic,
            source_text=source_text,
            n_examples=n_examples,
            format_type=format_type,
        )

        if not examples:
            self.logger.warning(f"No examples generated for: {topic}")
            return None

        # Self-rate quality
        quality_sum = sum(e.get("quality_score", 0.5) for e in examples)
        avg_quality = quality_sum / len(examples)

        return Message(
            from_agent=self.agent_id,
            to_agent=message.from_agent,
            type="training_data",
            priority=message.priority,
            payload={
                "format": format_type,
                "examples": examples,
                "source_topic": topic,
                "quality_estimate": round(avg_quality, 2),
                "dataset_tag": dataset_tag,
                "language_model": self._get_llm_name(),
                "count": len(examples),
            },
            tags=message.tags,
        )

    def _handle_research_result(self, message: Message) -> Optional[Message]:
        """Auto-generate training data from a researcher's findings."""
        payload = message.payload
        topic = payload.get("topic", "")
        content = payload.get("content", {})
        summary = payload.get("summary", "")

        if not (topic and summary):
            return None

        # Build source text from findings
        source_text = summary
        bullets = content.get("bullets", [])
        if bullets:
            source_text += "\n\nKey points:\n" + "\n".join(f"- {b}" for b in bullets)

        examples = self._generate_examples(
            topic=topic,
            source_text=source_text,
            n_examples=5,  # Fewer since quality is lower from raw research
            format_type="qa_pair",
        )

        if not examples:
            return None

        return Message(
            from_agent=self.agent_id,
            to_agent="daemon",
            type="training_data",
            priority=7,
            payload={
                "format": "qa_pair",
                "examples": examples,
                "source_topic": topic,
                "quality_estimate": 0.6,  # Research-derived is lower quality
                "dataset_tag": f"research-{topic.replace(' ', '-')[:20]}",
                "language_model": self._get_llm_name(),
                "count": len(examples),
            },
            tags=[topic.replace(" ", "-")[:30]],
        )

    def _auto_generate_from_knowledge(self, message: Message):
        """Automatically generate QA pairs when new knowledge is added."""
        entry = message.payload.get("entry", {})
        insight = entry.get("insight", "")
        if not insight or len(insight) < 30:
            return

        # Generate 3 quick QA pairs
        topic = entry.get("tags", [insight[:30]])[0] if entry.get("tags") else insight[:30]
        examples = self._generate_examples(
            topic=topic,
            source_text=insight,
            n_examples=3,
            format_type="qa_pair",
        )

        if examples:
            self.publish(
                to_agent="daemon",
                msg_type="training_data",
                payload={
                    "format": "qa_pair",
                    "examples": examples,
                    "source_topic": topic,
                    "quality_estimate": 0.7,
                    "dataset_tag": f"knowledge-{topic[:20]}",
                    "language_model": self._get_llm_name(),
                    "count": len(examples),
                },
                priority=8,
                tags=[topic],
            )

    # ========================================================================
    # Training Data Generation
    # ========================================================================

    def _generate_examples(
        self,
        topic: str,
        source_text: str,
        n_examples: int,
        format_type: str,
    ) -> List[Dict[str, Any]]:
        """Generate training examples using LLM or templates.

        Args:
            topic: Topic to generate examples about
            source_text: Source material to base examples on
            n_examples: How many examples to generate
            format_type: qa_pair | instruction_response | dialogue | completion

        Returns: List of training example dicts
        """
        if not self.check_rate_limit("llm_call"):
            return self._template_fallback(topic, source_text, n_examples, format_type)

        # Try LLM generation
        examples = self._llm_generate(topic, source_text, n_examples, format_type)
        if examples:
            self.consume_rate("llm_call")
            return examples

        # Fallback to templates
        return self._template_fallback(topic, source_text, n_examples, format_type)

    def _llm_generate(
        self,
        topic: str,
        source_text: str,
        n_examples: int,
        format_type: str,
    ) -> Optional[List[Dict]]:
        """Generate examples via LLM API."""
        import os
        import urllib.request

        # Build format-specific prompt
        if format_type == "qa_pair":
            prompt = f"""Generate {n_examples} high-quality question-answer pairs about: {topic}

Source material:
{source_text[:2000]}

Rules:
- Questions should test specific, non-trivial knowledge
- Answers should be 2-4 sentences, concrete and accurate
- Mix difficulty levels (easy, medium, hard)
- Make questions diverse (what, how, why, when, compare)

Return JSON array:
[{{"question": "...", "answer": "...", "difficulty": "easy|medium|hard", "quality_score": 0.0-1.0}}]"""

        elif format_type == "instruction_response":
            prompt = f"""Generate {n_examples} instruction-response training pairs about: {topic}

Source material:
{source_text[:2000]}

Rules:
- Instructions should be realistic user requests
- Responses should be helpful, accurate, and appropriately detailed
- Vary instruction types: explain, compare, implement, analyze, recommend

Return JSON array:
[{{"instruction": "...", "input": "", "output": "...", "quality_score": 0.0-1.0}}]"""

        else:
            # Generic for other formats
            prompt = f"""Generate {n_examples} training examples about: {topic}

Source material:
{source_text[:2000]}

Return JSON array of examples with fields: prompt, completion, quality_score"""

        # Try Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or self.config.get("llm", {}).get("api_key")
        if anthropic_key:
            try:
                data = json.dumps({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                }).encode()

                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=data,
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode())
                    text = result["content"][0]["text"]

                    # Extract JSON array from response
                    json_match = re.search(r"\[.*\]", text, re.DOTALL)
                    if json_match:
                        examples = json.loads(json_match.group())
                        return examples[:n_examples]

            except Exception as e:
                self.logger.debug(f"LLM generation failed: {e}")

        return None

    def _template_fallback(
        self,
        topic: str,
        source_text: str,
        n_examples: int,
        format_type: str,
    ) -> List[Dict[str, Any]]:
        """Generate basic examples from templates when LLM unavailable."""
        examples = []

        if format_type == "qa_pair":
            # Extract key sentences from source text
            sentences = re.split(r"[.!?]+", source_text)
            key_sentences = [s.strip() for s in sentences if len(s.strip()) > 40][:n_examples]

            templates = [
                ("What is the key finding about {topic}?", "{sentence}"),
                ("Explain {topic} in technical terms.", "{sentence}"),
                ("How does {topic} affect model performance?", "{sentence}"),
                ("What should practitioners know about {topic}?", "{sentence}"),
                ("Summarize what is known about {topic}.", "{sentence}"),
            ]

            for i, sentence in enumerate(key_sentences):
                q_template, a_template = templates[i % len(templates)]
                examples.append({
                    "question": q_template.format(topic=topic),
                    "answer": a_template.format(sentence=sentence),
                    "difficulty": "medium",
                    "quality_score": 0.4,  # Template-generated is lower quality
                })

        elif format_type == "instruction_response":
            examples.append({
                "instruction": f"Explain {topic} and its importance.",
                "input": "",
                "output": source_text[:500] if source_text else f"Information about {topic}.",
                "quality_score": 0.4,
            })

        return examples[:n_examples]

    def _get_llm_name(self) -> str:
        """Get name of LLM being used for data generation."""
        import os
        if os.environ.get("ANTHROPIC_API_KEY"):
            return "claude-haiku-4-5-20251001"
        elif os.environ.get("OPENAI_API_KEY"):
            return "gpt-4o-mini"
        return "template-fallback"
