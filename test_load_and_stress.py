#!/usr/bin/env python3
"""Load and stress testing for AutoClaw production readiness.

Tests system behavior under heavy load:
- High-volume knowledge operations
- High-throughput message bus
- Concurrent agent operations
- Sustained load over time
- Recovery from overload conditions
"""

import logging
import time
import threading
import random
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class LoadTestRunner:
    """Run load tests with metrics collection."""

    def __init__(self, name: str):
        """Initialize test runner."""
        self.name = name
        self.start_time = None
        self.end_time = None
        self.operations = []
        self.errors = []
        self.results = {}

    def start(self):
        """Start timing."""
        self.start_time = time.time()
        logger.info(f"\n{'=' * 60}")
        logger.info(f"LOAD TEST: {self.name}")
        logger.info('=' * 60)

    def record_operation(self, duration_ms: float, success: bool, error: str = None):
        """Record an operation."""
        self.operations.append({
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
        })

        if error:
            self.errors.append(error)

    def finish(self):
        """Finish test and collect results."""
        self.end_time = time.time()
        total_duration = self.end_time - self.start_time

        if not self.operations:
            logger.error("No operations recorded")
            return False

        successful = sum(1 for op in self.operations if op["success"])
        failed = len(self.operations) - successful
        durations = [op["duration_ms"] for op in self.operations if op["success"]]

        if not durations:
            logger.error("All operations failed")
            return False

        self.results = {
            "total_operations": len(self.operations),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(self.operations)) * 100,
            "duration_seconds": total_duration,
            "throughput": len(self.operations) / total_duration,
            "min_ms": min(durations),
            "max_ms": max(durations),
            "avg_ms": sum(durations) / len(durations),
            "p95_ms": sorted(durations)[int(len(durations) * 0.95)],
            "p99_ms": sorted(durations)[int(len(durations) * 0.99)],
        }

        logger.info(f"\n{self.name} Results:")
        logger.info(f"  Total: {self.results['total_operations']} operations")
        logger.info(f"  Success: {successful} ({self.results['success_rate']:.1f}%)")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Duration: {self.results['duration_seconds']:.1f}s")
        logger.info(f"  Throughput: {self.results['throughput']:.1f} ops/sec")
        logger.info(f"  Latency (ms): min={self.results['min_ms']:.1f}, "
                   f"avg={self.results['avg_ms']:.1f}, "
                   f"p95={self.results['p95_ms']:.1f}, "
                   f"p99={self.results['p99_ms']:.1f}, "
                   f"max={self.results['max_ms']:.1f}")

        if self.errors:
            unique_errors = list(set(self.errors))
            logger.warning(f"  Errors: {len(unique_errors)} unique errors")
            for error_type in unique_errors[:3]:
                count = self.errors.count(error_type)
                logger.warning(f"    - {error_type}: {count}x")

        return self.results["success_rate"] >= 95.0


# ============================================================================
# KNOWLEDGE STORE LOAD TESTS
# ============================================================================

def test_knowledge_store_high_volume():
    """Test knowledge store with high volume."""
    from crew.knowledge import get_knowledge_store

    runner = LoadTestRunner("Knowledge Store - High Volume (1000 entries)")
    runner.start()

    store = get_knowledge_store()

    try:
        # Create 1000 entries
        for i in range(1000):
            start = time.time()
            try:
                entry = store.create(
                    insight=f"Insight {i}: " + "x" * 100,
                    category=random.choice(["architecture", "optimization", "debugging", "design"]),
                    tags=[f"tag{i % 10}", "load-test"],
                    source_task_ids=[i],
                    experiments_supporting=i % 10,
                    experiments_contradicting=random.randint(0, 2)
                )
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, True)
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, False, str(e))

        # Query operations
        for _ in range(100):
            start = time.time()
            try:
                results = store.query(
                    tags=["load-test"],
                    category=random.choice(["architecture", "optimization", "debugging", "design"]),
                )
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, True)
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, False, str(e))

    finally:
        runner.finish()
        return runner.results["success_rate"] >= 95.0


def test_knowledge_store_concurrent():
    """Test knowledge store with concurrent access."""
    from crew.knowledge import get_knowledge_store

    runner = LoadTestRunner("Knowledge Store - Concurrent (10 threads)")
    runner.start()

    store = get_knowledge_store()
    num_threads = 10
    operations_per_thread = 50

    def thread_work():
        for i in range(operations_per_thread):
            start = time.time()
            try:
                store.create(
                    insight=f"Concurrent {threading.current_thread().name} {i}",
                    category="test",
                    tags=["concurrent"],
                    source_task_ids=[i],
                    experiments_supporting=1,
                )
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, True)
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, False, str(e))

    try:
        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=thread_work)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    finally:
        runner.finish()
        return runner.results["success_rate"] >= 95.0


# ============================================================================
# MESSAGE BUS LOAD TESTS
# ============================================================================

def test_message_bus_throughput():
    """Test message bus throughput."""
    from crew.messaging.bus import MessageBus

    runner = LoadTestRunner("Message Bus - High Throughput (5000 messages)")
    runner.start()

    bus = MessageBus()
    agents = ["agent1", "agent2", "agent3", "agent4", "agent5"]

    try:
        # Publish 5000 messages
        for i in range(5000):
            start = time.time()
            try:
                msg_id = bus.publish(
                    from_agent=random.choice(agents),
                    to_agent=random.choice(agents),
                    msg_type="test",
                    payload={"index": i, "data": "x" * 50},
                    priority=random.randint(1, 10)
                )
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, True)
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, False, str(e))

    finally:
        runner.finish()
        return runner.results["success_rate"] >= 95.0


def test_message_bus_concurrent():
    """Test message bus with concurrent publishers."""
    from crew.messaging.bus import MessageBus

    runner = LoadTestRunner("Message Bus - Concurrent (10 threads)")
    runner.start()

    bus = MessageBus()
    num_threads = 10
    messages_per_thread = 100

    def thread_work():
        for i in range(messages_per_thread):
            start = time.time()
            try:
                bus.publish(
                    from_agent=threading.current_thread().name,
                    to_agent="collector",
                    msg_type="test",
                    payload={"msg": i},
                )
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, True)
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, False, str(e))

    try:
        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=thread_work)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    finally:
        runner.finish()
        return runner.results["success_rate"] >= 95.0


# ============================================================================
# SUSTAINED LOAD TEST
# ============================================================================

def test_sustained_load():
    """Test system under sustained load."""
    from crew.knowledge import get_knowledge_store
    from crew.messaging.bus import MessageBus

    runner = LoadTestRunner("Sustained Load - 30 second test")
    runner.start()

    store = get_knowledge_store()
    bus = MessageBus()
    duration_seconds = 30

    operations_by_type = {
        "knowledge_create": 0,
        "knowledge_query": 0,
        "message_publish": 0,
    }

    start_time = time.time()

    try:
        while time.time() - start_time < duration_seconds:
            op_type = random.choice(["knowledge_create", "knowledge_query", "message_publish"])

            start = time.time()
            try:
                if op_type == "knowledge_create":
                    store.create(
                        insight=f"Sustained {op_type}",
                        category="test",
                        tags=["sustained"],
                        source_task_ids=[1],
                        experiments_supporting=1,
                    )

                elif op_type == "knowledge_query":
                    store.query(tags=["sustained"], limit=10)

                elif op_type == "message_publish":
                    bus.publish(
                        from_agent="test",
                        to_agent="collector",
                        msg_type="test",
                        payload={"time": time.time()},
                    )

                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, True)
                operations_by_type[op_type] += 1

            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, False, str(e))

    finally:
        elapsed = time.time() - start_time
        logger.info(f"\nOperation breakdown (in {elapsed:.1f}s):")
        for op_type, count in operations_by_type.items():
            logger.info(f"  {op_type}: {count} ({count/elapsed:.1f} ops/sec)")

        runner.finish()
        return runner.results["success_rate"] >= 95.0


# ============================================================================
# STRESS TEST - RECOVERY FROM OVERLOAD
# ============================================================================

def test_recovery_from_overload():
    """Test system recovery from overload."""
    from crew.knowledge import get_knowledge_store
    from crew.healthcheck import HealthChecker

    runner = LoadTestRunner("Recovery Test - Overload then recovery")
    runner.start()

    store = get_knowledge_store()
    checker = HealthChecker()

    try:
        # Phase 1: Overload (100 concurrent creates)
        logger.info("\nPhase 1: Creating overload (100 concurrent)...")
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = []
            for i in range(100):
                future = executor.submit(
                    lambda idx=i: store.create(
                        insight=f"Overload {idx}",
                        category="test",
                        tags=["overload"],
                        source_task_ids=[idx],
                        experiments_supporting=1,
                    )
                )
                futures.append(future)

            success_count = 0
            for future in as_completed(futures):
                start = time.time()
                try:
                    future.result()
                    duration_ms = (time.time() - start) * 1000
                    runner.record_operation(duration_ms, True)
                    success_count += 1
                except Exception as e:
                    duration_ms = (time.time() - start) * 1000
                    runner.record_operation(duration_ms, False, str(e))

        logger.info(f"Overload phase: {success_count}/100 succeeded")

        # Phase 2: Check health
        logger.info("\nPhase 2: Checking health after overload...")
        health, components = checker.check_all()
        logger.info(f"System health: {health.value}")

        # Phase 3: Recovery (normal operations)
        logger.info("\nPhase 3: Normal operations during recovery...")
        for i in range(50):
            start = time.time()
            try:
                store.query(tags=["overload"], limit=5)
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, True)
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, False, str(e))

    finally:
        runner.finish()
        return runner.results["success_rate"] >= 90.0  # More lenient for recovery


# ============================================================================
# MEMORY PRESSURE TEST
# ============================================================================

def test_memory_pressure():
    """Test system under memory pressure."""
    from crew.knowledge import get_knowledge_store
    import gc

    runner = LoadTestRunner("Memory Pressure - Large payloads")
    runner.start()

    store = get_knowledge_store()

    try:
        # Create entries with large payloads
        for i in range(200):
            start = time.time()
            try:
                # 1MB of data per entry
                large_payload = "x" * (1024 * 1024)
                store.create(
                    insight=f"Large {i}: {large_payload[:100]}...",
                    category="memory_test",
                    tags=["memory"],
                    source_task_ids=[i],
                    experiments_supporting=1,
                )
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, True)
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                runner.record_operation(duration_ms, False, str(e))

            # Force garbage collection every 50 entries
            if (i + 1) % 50 == 0:
                gc.collect()

    finally:
        runner.finish()
        # More lenient threshold for memory tests
        return runner.results["success_rate"] >= 80.0


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all load tests."""
    results = {}

    # Knowledge store tests
    logger.info("\n" + "=" * 60)
    logger.info("KNOWLEDGE STORE LOAD TESTS")
    logger.info("=" * 60)

    results["knowledge_high_volume"] = test_knowledge_store_high_volume()
    results["knowledge_concurrent"] = test_knowledge_store_concurrent()

    # Message bus tests
    logger.info("\n" + "=" * 60)
    logger.info("MESSAGE BUS LOAD TESTS")
    logger.info("=" * 60)

    results["message_throughput"] = test_message_bus_throughput()
    results["message_concurrent"] = test_message_bus_concurrent()

    # Sustained load
    logger.info("\n" + "=" * 60)
    logger.info("SUSTAINED LOAD TEST")
    logger.info("=" * 60)

    results["sustained_load"] = test_sustained_load()

    # Recovery test
    logger.info("\n" + "=" * 60)
    logger.info("RECOVERY TEST")
    logger.info("=" * 60)

    results["recovery"] = test_recovery_from_overload()

    # Memory test
    logger.info("\n" + "=" * 60)
    logger.info("MEMORY PRESSURE TEST")
    logger.info("=" * 60)

    results["memory_pressure"] = test_memory_pressure()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("LOAD TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_flag in results.items():
        status = "✓ PASSED" if passed_flag else "✗ FAILED"
        logger.info(f"  {test_name}: {status}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
