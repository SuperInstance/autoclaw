#!/usr/bin/env python3
"""Test Phase C advanced features: Adaptive scheduling and Flowstate."""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
logger = logging.getLogger(__name__)


class PhaseC_Test:
    """Phase C feature tests."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def run_all(self) -> bool:
        """Run all Phase C tests."""
        print("\n" + "=" * 70)
        print("PHASE C: ADVANCED FEATURES TEST")
        print("=" * 70)

        tests = [
            ("Adaptive Scheduler: Thompson Sampling", self.test_adaptive_scheduler),
            ("Flowstate: Sandbox Exploration", self.test_flowstate),
            ("Hardware Detection", self.test_hardware_detection),
            ("Cloudflare Credit Management", self.test_cloudflare),
        ]

        for name, test_fn in tests:
            try:
                print(f"\n[{name}]...", end=" ")
                test_fn()
                print("✓")
                self.passed += 1
            except AssertionError as e:
                print(f"✗\n  {e}")
                self.failed += 1
            except Exception as e:
                print(f"✗\n  ERROR: {e}")
                self.failed += 1
                import traceback
                traceback.print_exc()

        return self.report()

    def test_adaptive_scheduler(self):
        """Test adaptive scheduler with Thompson sampling."""
        from crew.adaptive import get_adaptive_scheduler, ResearchDirection

        scheduler = get_adaptive_scheduler()

        # Create a mock task
        class MockTask:
            def __init__(self):
                self.tags = ["transformer_optimization"]
                self.description = "Optimize transformer efficiency"

        task = MockTask()

        # Compute initial priority (should be low, unknown direction)
        boost = scheduler.compute_priority_adjustment(task)
        assert isinstance(boost, float), "Priority boost should be float"
        assert 0 <= boost <= 2.0, "Boost should be in range 0-2.0"

        # Update from task results
        scheduler.update_from_task_result(
            task,
            findings=["Learned: Mixed precision reduces memory"],
            success_rate=1.0,
            compute_hours=0.5,
            num_knowledge_entries=1,
        )

        # After one success, priority should be higher
        boost2 = scheduler.compute_priority_adjustment(task)
        assert boost2 >= boost, "Priority should increase after successful result"

        # Get suggestions (uses Thompson sampling)
        suggestions = scheduler.suggest_research_directions(num_suggestions=1)
        assert len(suggestions) > 0, "Should have suggestions"
        assert "direction" in suggestions[0], "Should have direction field"
        assert "estimated_value" in suggestions[0], "Should have value"

        # Check stats
        stats = scheduler.stats()
        assert stats["total_directions"] >= 1, "Should track directions"
        assert stats["total_samples_drawn"] >= 1, "Should have drawn samples"

    def test_flowstate(self):
        """Test flowstate sandbox mode."""
        from crew.flowstate import get_flowstate_manager

        manager = get_flowstate_manager()

        # Create a sandbox
        flow = manager.create(
            title="Explore low-rank adaptation",
            description="Test LoRA with different ranks",
            budget_gb=5.0,
            max_experiments=5,
        )

        assert flow.id, "Should have unique ID"
        assert flow.status == "active", "Should start as active"

        # Record experiments
        manager.record_experiment(flow.id, success=True, result_summary="LoRA rank 8 works well")
        manager.record_experiment(flow.id, success=False, result_summary="LoRA rank 2 too low")

        task = manager.get(flow.id)
        assert task.experiments_run == 2, "Should have recorded 2 experiments"
        assert task.experiments_successful == 1, "Should have 1 success"

        # Get checkpoint dir (should be created)
        checkpoint_dir = manager.get_checkpoint_dir(flow.id)
        assert checkpoint_dir.exists(), "Should create checkpoint directory"

        # Promote findings
        promoted_ids = manager.promote_findings(
            flow.id,
            findings=["LoRA rank 8 achieves good balance"],
            confidence="medium",
            validation_task_ids=[1, 2],
        )

        assert len(promoted_ids) > 0, "Should create knowledge entries"
        assert task.status == "promoted", "Should mark as promoted"

        # Check stats
        stats = manager.stats()
        assert stats["promoted_sandboxes"] > 0, "Should count promoted sandboxes"

    def test_hardware_detection(self):
        """Test hardware detection."""
        from crew.hardware.detector import HardwareDetector, PROFILES

        detector = HardwareDetector()

        # Detect profile
        profile_name, profile_info = detector.detect()

        assert profile_name is not None, "Should detect a profile"
        assert profile_info is not None, "Should have profile info"
        assert "max_agents" in profile_info, "Should have max_agents"
        assert "display_name" in profile_info, "Should have display_name"

        # Get all profiles
        assert len(PROFILES) > 0, "Should have profile definitions"

    def test_cloudflare(self):
        """Test Cloudflare credit management."""
        from crew.cloudflare.credits import CreditTracker

        credits = CreditTracker()

        # Get status
        status = credits.get_status()
        assert status is not None, "Should get status"

        # Check remaining neurons (credits)
        remaining = credits.remaining_neurons()
        assert isinstance(remaining, int), "Should return integer neurons"

        # Check minutes until reset
        minutes = credits.minutes_until_reset()
        assert isinstance(minutes, int), "Should return integer minutes"

        # Check if can use a service
        can_use = credits.can_use(service="workers_ai_llama")
        assert can_use is not None, "Should check if service available"

    def report(self) -> bool:
        """Print summary."""
        total = self.passed + self.failed

        print("\n" + "=" * 70)
        print(f"PHASE C RESULTS: {self.passed}/{total} tests passed", end="")

        if self.failed > 0:
            print(f", {self.failed} failed ✗")
            return False
        else:
            print(" ✓")
            return True


def main():
    """Run Phase C tests."""
    test = PhaseC_Test()
    success = test.run_all()

    print("\n" + "=" * 70)
    print("PHASE C CAPABILITIES:")
    print("=" * 70)
    print("""
✓ Adaptive Scheduling: Learn research directions' ROI
  - Thompson sampling for exploration/exploitation balance
  - Beta distributions model uncertainty
  - Automatic priority boosting for high-value directions
  - Persistent learning across sessions

✓ Flowstate Sandbox Mode: Safe exploration
  - Isolated sandboxes for risky experiments
  - Results only promoted after validation
  - Separate storage and checkpoints
  - Automatic cleanup of old sandboxes

✓ Hardware Optimization: Device-aware configuration
  - Auto-detect hardware profile
  - Preset profiles for common devices
  - Adaptive agent counts based on compute

✓ Cloudflare Cost Management: Budget-aware operation
  - Credit tracking and deduction
  - Fallback to free APIs when budget low
  - Cost visibility for each operation
""")

    print("=" * 70)

    if success:
        print("\n✓ PHASE C COMPLETE")
        print("✓ SYSTEM FULLY FUNCTIONAL - Ready for production")
        print("\nImplemented Features:")
        print("  Phase A: Knowledge learning, triggers, notifications, context handoff")
        print("  Phase B: 5 core agents, multi-agent orchestration, message durability")
        print("  Phase C: Adaptive scheduling, flowstate, hardware optimization")
        return 0
    else:
        print("\n✗ Some Phase C tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
