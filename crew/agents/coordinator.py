"""Coordinator agent — orchestrates multi-agent workflows.

The coordinator is the crew's orchestrator. It:
  1. Receives high-level task requests from the daemon
  2. Breaks tasks down into sub-tasks
  3. Routes work to appropriate agents (researcher, teacher, critic, distiller)
  4. Monitors progress and gathers results
  5. Synthesizes final output back to daemon

Used for complex workflows like:
  - "Generate training data about topic X"
    → research X (researcher)
    → generate QA pairs (teacher)
    → quality check (critic)
    → finalize dataset (distiller)

  - "Validate knowledge entry #42"
    → research to find new evidence (researcher)
    → generate test questions (teacher)
    → fact-check against knowledge (critic)
    → update confidence (distiller)

Coordination patterns:
  - Orchestration: Sequential (research → teach → critique → distill)
  - Bidding: Let agents bid on tasks, choose best
  - Consensus: Multiple agents work in parallel, vote on results
  - Pipeline: Pass outputs from one agent as input to next
"""

import json
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from crew.agents.base import BaseAgent
from crew.messaging.bus import Message

logger = logging.getLogger(__name__)


class CoordinatorAgent(BaseAgent):
    """Agent that orchestrates multi-agent workflows.

    Accepts task_request messages and routes work to specialists,
    monitors progress, and publishes final results.
    """

    ROLE = "coordinator"
    DEFAULT_PRIORITY = 4  # High priority - coordinates critical work

    def get_capabilities(self) -> List[str]:
        return [
            "workflow_orchestration",
            "task_decomposition",
            "agent_routing",
            "progress_monitoring",
            "result_synthesis",
            "consensus_voting",
            "pipeline_execution",
        ]

    def process_message(self, message: Message) -> Optional[Message]:
        """Process a workflow request.

        Expected payload:
          description: str (what workflow to run)
          workflow_type: str (orchestration|pipeline|consensus|bidding)
          stages: list of stage dicts with agent_roles and prompts
          timeout_seconds: int (max time for workflow)
          target_agent: str (where to send final result)
        """
        if message.type != "task_request":
            return None

        payload = message.payload
        workflow_type = payload.get("workflow_type", "pipeline")
        stages = payload.get("stages", [])
        description = payload.get("description", "")
        timeout = payload.get("timeout_seconds", 3600)

        self.logger.info(
            f"Starting {workflow_type} workflow: {description}"
        )

        try:
            if workflow_type == "pipeline":
                result = self._run_pipeline(message, stages, timeout)
            elif workflow_type == "orchestration":
                result = self._run_orchestration(message, stages, timeout)
            elif workflow_type == "consensus":
                result = self._run_consensus(message, stages, timeout)
            elif workflow_type == "bidding":
                result = self._run_bidding(message, stages, timeout)
            else:
                result = self._run_pipeline(message, stages, timeout)

            return result

        except Exception as e:
            self.logger.error(f"Workflow error: {e}", exc_info=True)
            return Message(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                type="result",
                payload={
                    "status": "error",
                    "error": str(e),
                    "parent_workflow": description,
                },
                parent_message_id=message.id,
            )

    def _run_pipeline(
        self, original_msg: Message, stages: List[Dict], timeout_sec: int
    ) -> Optional[Message]:
        """Run stages sequentially, passing output to input of next stage.

        Stage format:
          {
            "agent_role": "researcher",  # or teacher, critic, distiller
            "action": "research|generate|review|synthesize",
            "prompt": "What to do",
            "input_field": "previous_output",  # Field to pull from prev stage
          }
        """
        self.logger.info(f"Running pipeline with {len(stages)} stages")

        workflow_id = f"workflow_{int(time.time() * 1000)}"
        current_output = None
        results_by_stage = {}

        for i, stage in enumerate(stages):
            if time.time() - self._stage_start > timeout_sec:
                self.logger.warning(f"Pipeline exceeded timeout ({timeout_sec}s)")
                break

            agent_role = stage.get("agent_role", "")
            action = stage.get("action", "")
            prompt = stage.get("prompt", "")
            input_field = stage.get("input_field")

            self.logger.debug(f"Stage {i+1}: {agent_role} → {action}")

            # Build message for next agent
            payload = {
                "description": prompt,
                "action": action,
                "workflow_id": workflow_id,
                "stage_number": i + 1,
                "total_stages": len(stages),
            }

            if input_field and current_output:
                payload["previous_output"] = current_output.get(input_field)

            # Send to any available agent with this role
            msg_id = self.publish(
                to_agent=f"any_{agent_role}",
                msg_type="task_request",
                payload=payload,
                priority=4,  # High priority for workflow work
                parent_id=original_msg.id,
                tags=[workflow_id, agent_role, f"stage_{i+1}"],
                expires_in_hours=1.0,
            )

            # Wait for result (simplified - real impl would poll the bus)
            result_msg = self._wait_for_result(msg_id, timeout=120)

            if result_msg:
                current_output = result_msg.payload
                results_by_stage[f"stage_{i+1}"] = current_output
                self.logger.debug(f"Stage {i+1} completed")
            else:
                self.logger.warning(f"Stage {i+1} timed out or failed")
                break

        # Return final output
        return Message(
            from_agent=self.agent_id,
            to_agent=original_msg.from_agent,
            type="result",
            payload={
                "status": "success",
                "workflow_id": workflow_id,
                "final_output": current_output,
                "stages_completed": len(results_by_stage),
                "all_results": results_by_stage,
            },
            parent_message_id=original_msg.id,
        )

    def _run_orchestration(
        self, original_msg: Message, stages: List[Dict], timeout_sec: int
    ) -> Optional[Message]:
        """Run a specific orchestration pattern.

        Supports patterns like:
        - research_and_teach: research(topic) → teach(findings)
        - teach_critique_distill: teach(topic) → critique(output) → distill(output)
        """
        pattern = stages[0].get("pattern") if stages else "generic"
        self.logger.info(f"Running orchestration pattern: {pattern}")

        # For now, delegate to pipeline (in full impl would be more sophisticated)
        return self._run_pipeline(original_msg, stages, timeout_sec)

    def _run_consensus(
        self, original_msg: Message, stages: List[Dict], timeout_sec: int
    ) -> Optional[Message]:
        """Run agents in parallel and have them vote on results.

        All agents get the same task, we collect their results and
        find consensus. Useful for:
        - Fact-checking (multiple fact-checkers vote)
        - Quality assessment (multiple critics score)
        """
        self.logger.info(f"Running consensus with {len(stages)} agents")

        task_prompt = original_msg.payload.get("description", "")
        voting_agents = stages

        # Send same task to all agents
        msg_ids = []
        for agent_spec in voting_agents:
            agent_role = agent_spec.get("agent_role", "critic")

            msg_id = self.publish(
                to_agent=f"any_{agent_role}",
                msg_type="task_request",
                payload={
                    "description": task_prompt,
                    "consensus_vote": True,
                },
                priority=5,
                parent_id=original_msg.id,
                tags=["consensus_vote", agent_role],
                expires_in_hours=1.0,
            )
            msg_ids.append((agent_role, msg_id))

        # Collect votes
        votes = {}
        for agent_role, msg_id in msg_ids:
            result_msg = self._wait_for_result(msg_id, timeout=120)
            if result_msg:
                vote = result_msg.payload.get("vote") or result_msg.payload.get(
                    "score"
                )
                votes[agent_role] = vote

        # Simple consensus: average if numeric, majority if boolean
        consensus = self._compute_consensus(votes)

        return Message(
            from_agent=self.agent_id,
            to_agent=original_msg.from_agent,
            type="result",
            payload={
                "status": "success",
                "votes": votes,
                "consensus": consensus,
            },
            parent_message_id=original_msg.id,
        )

    def _run_bidding(
        self, original_msg: Message, stages: List[Dict], timeout_sec: int
    ) -> Optional[Message]:
        """Agents bid on tasks based on capability/availability.

        Instead of routing to any_role, we ask agents to bid.
        Agent with best bid (confidence/availability) wins the work.
        """
        self.logger.info(f"Running bidding workflow")

        task_prompt = original_msg.payload.get("description", "")
        agent_roles = [s.get("agent_role") for s in stages if s.get("agent_role")]

        # Request bids
        msg_id = self.publish(
            to_agent="broadcast",
            msg_type="task_request",
            payload={
                "description": task_prompt,
                "request_bids": True,
                "required_roles": agent_roles,
            },
            priority=4,
            parent_id=original_msg.id,
            tags=["bidding_request"],
            expires_in_hours=0.5,  # Quick decision window
        )

        # Wait for bids and pick winner
        # (simplified - real impl would collect multiple bids)
        winning_bid = self._wait_for_result(msg_id, timeout=30)

        if winning_bid:
            return Message(
                from_agent=self.agent_id,
                to_agent=original_msg.from_agent,
                type="result",
                payload={
                    "status": "success",
                    "winning_agent": winning_bid.from_agent,
                    "bid": winning_bid.payload,
                },
                parent_message_id=original_msg.id,
            )
        else:
            return Message(
                from_agent=self.agent_id,
                to_agent=original_msg.from_agent,
                type="result",
                payload={
                    "status": "error",
                    "error": "No agents submitted bids",
                },
                parent_message_id=original_msg.id,
            )

    def _wait_for_result(self, msg_id: int, timeout: int = 120) -> Optional[Message]:
        """Wait for a message result with timeout.

        Args:
            msg_id: Message ID to wait for
            timeout: Max seconds to wait

        Returns: Result message or None if timeout
        """
        start = time.time()

        while time.time() - start < timeout:
            # Check if result arrived (simplified - real impl would check bus)
            # This is a placeholder - actual implementation would query the bus
            time.sleep(2)

            # In a full implementation, query: bus.get_result(msg_id)
            # For now, return None to avoid infinite loop
            break

        return None

    def _compute_consensus(self, votes: Dict[str, Any]) -> Any:
        """Compute consensus from agent votes.

        Args:
            votes: Dict of agent_role → vote_value

        Returns: Consensus result (average for numbers, majority for boolean)
        """
        if not votes:
            return None

        values = list(votes.values())

        # Try numeric consensus
        try:
            numeric = [float(v) for v in values]
            return sum(numeric) / len(numeric)
        except (TypeError, ValueError):
            pass

        # Boolean consensus
        try:
            boolean = [bool(v) for v in values]
            trues = sum(boolean)
            return trues > len(boolean) / 2
        except:
            pass

        # String consensus (pick most common)
        from collections import Counter

        return Counter(values).most_common(1)[0][0]

    # Helper to track workflow start time
    @property
    def _stage_start(self) -> float:
        """Get workflow start time for timeout tracking."""
        return time.time()

    def idle_work(self):
        """When idle, monitor for stalled workflows."""
        # Could implement cleanup of old workflow data, etc
        time.sleep(5)
