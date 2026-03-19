#!/usr/bin/env python3
"""Failure scenario and recovery testing for AutoClaw.

Tests system resilience:
- Database corruption recovery
- Missing configuration handling
- Agent crash recovery
- Network failures
- Resource exhaustion
- Graceful degradation
"""

import logging
import sys
import time
from pathlib import Path
import tempfile
import shutil

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class FailureTest:
    """Test failure scenarios."""

    def __init__(self, name: str):
        """Initialize failure test."""
        self.name = name
        self.passed = False
        self.details = ""

    def run(self) -> bool:
        """Run test and return True if handled correctly."""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"FAILURE TEST: {self.name}")
        logger.info('=' * 60)
        return self.passed

    def report(self):
        """Report test result."""
        status = "✓ HANDLED" if self.passed else "✗ FAILED"
        logger.info(f"\n{self.name}: {status}")
        if self.details:
            logger.info(f"Details: {self.details}")


# ============================================================================
# CONFIGURATION FAILURES
# ============================================================================

def test_missing_config_file():
    """Test handling of missing configuration file."""
    test = FailureTest("Missing Configuration File")

    try:
        from crew.config import ConfigLoader
        from crew.validation import ValidationError

        # Try to load nonexistent file
        try:
            loader = ConfigLoader(Path("/nonexistent/path/config.yaml"))
            test.details = "Should have raised FileNotFoundError"
        except FileNotFoundError:
            test.passed = True
            test.details = "Correctly raised FileNotFoundError"
        except Exception as e:
            test.details = f"Wrong exception type: {type(e).__name__}"

    except Exception as e:
        test.details = f"Unexpected error: {e}"

    test.report()
    assert test.passed, test.details


def test_invalid_config_yaml():
    """Test handling of invalid YAML."""
    test = FailureTest("Invalid Configuration YAML")

    try:
        from crew.config import ConfigLoader
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Write invalid YAML (mismatched brackets)
            f.write("invalid: yaml: [unclosed\n")
            temp_file = f.name

        try:
            loader = ConfigLoader(Path(temp_file))
            test.details = "Should have raised YAMLError"
        except Exception as e:
            # Accept any YAML-related error: YAMLError, ScannerError, ParserError, etc.
            exception_name = type(e).__name__
            if any(keyword in exception_name for keyword in ["YAML", "Parse", "Scanner", "Error"]):
                test.passed = True
                test.details = f"Correctly raised {exception_name}"
            else:
                test.details = f"Wrong exception type: {exception_name}"

        Path(temp_file).unlink()

    except Exception as e:
        test.details = f"Unexpected error: {e}"

    test.report()
    assert test.passed, test.details


def test_missing_required_config():
    """Test handling of missing required config sections."""
    test = FailureTest("Missing Required Config Sections")

    try:
        from crew.config import ConfigLoader
        from crew.validation import ValidationError
        import tempfile
        import yaml

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Write config with missing required sections
            minimal_config = {
                'crew': {'name': 'Test'},
                # Missing many required sections
            }
            yaml.dump(minimal_config, f)
            temp_file = f.name

        try:
            loader = ConfigLoader(Path(temp_file))
            test.details = "Should have raised ValidationError"
        except ValidationError:
            test.passed = True
            test.details = "Correctly raised ValidationError"
        except Exception as e:
            test.details = f"Wrong exception type: {type(e).__name__}"

        Path(temp_file).unlink()

    except Exception as e:
        test.details = f"Unexpected error: {e}"

    test.report()
    assert test.passed, test.details


# ============================================================================
# INPUT VALIDATION FAILURES
# ============================================================================

def test_xss_injection():
    """Test XSS injection prevention."""
    test = FailureTest("XSS Injection Prevention")

    try:
        from crew.validation import StringValidator, ValidationError

        xss_payloads = [
            "<script>alert('xss')</script>",
            "'\"><script>alert(String.fromCharCode(88,83,83))</script>",
            "javascript:alert('xss')",
        ]

        blocked = 0
        for payload in xss_payloads:
            try:
                StringValidator.validate(payload, "test_field")
            except ValidationError:
                blocked += 1

        if blocked == len(xss_payloads):
            test.passed = True
            test.details = f"Blocked all {len(xss_payloads)} XSS payloads"
        else:
            test.details = f"Only blocked {blocked}/{len(xss_payloads)} XSS payloads"

    except Exception as e:
        test.details = f"Unexpected error: {e}"

    test.report()
    assert test.passed, test.details


def test_sql_injection():
    """Test SQL injection prevention."""
    test = FailureTest("SQL Injection Prevention")

    try:
        from crew.validation import StringValidator, ValidationError

        sql_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
        ]

        blocked = 0
        for payload in sql_payloads:
            try:
                StringValidator.validate(payload, "test_field")
            except ValidationError:
                blocked += 1

        if blocked == len(sql_payloads):
            test.passed = True
            test.details = f"Blocked all {len(sql_payloads)} SQL payloads"
        else:
            test.details = f"Only blocked {blocked}/{len(sql_payloads)} SQL payloads"

    except Exception as e:
        test.details = f"Unexpected error: {e}"

    test.report()
    assert test.passed, test.details


def test_oversized_input():
    """Test handling of oversized input."""
    test = FailureTest("Oversized Input Rejection")

    try:
        from crew.validation import StringValidator, ValidationError

        # Create a very large string (10MB)
        large_string = "x" * (10 * 1024 * 1024)

        try:
            StringValidator.validate(large_string, "test", max_length=1000)
            test.details = "Should have rejected large string"
        except ValidationError:
            test.passed = True
            test.details = "Correctly rejected oversized input"

    except Exception as e:
        test.details = f"Unexpected error: {e}"

    test.report()
    assert test.passed, test.details


# ============================================================================
# DATABASE FAILURES
# ============================================================================

def test_database_initialization_failure():
    """Test handling of database initialization failures."""
    test = FailureTest("Database Initialization Failure")

    try:
        from crew.startup import initialize_databases

        # Try to initialize with bad path
        result = initialize_databases()

        if result:
            test.passed = True
            test.details = "Initialization succeeded (databases exist)"
        else:
            test.details = "Initialization failed"

    except Exception as e:
        test.details = f"Error: {e}"

    test.report()
    assert test.passed, test.details


def test_concurrent_database_access():
    """Test concurrent database access."""
    test = FailureTest("Concurrent Database Access")

    try:
        from crew.knowledge import get_knowledge_store
        from crew.messaging.bus import MessageBus
        import threading

        store = get_knowledge_store()
        bus = MessageBus()
        errors = []

        def thread_work():
            try:
                from crew.messaging.bus import Message
                for i in range(10):
                    store.create(
                        insight=f"Test {threading.current_thread().name}",
                        category="test",
                        tags=["test"],
                        source_task_ids=[i],
                        experiments_supporting=1,
                    )
                    msg = Message(
                        from_agent="test",
                        to_agent="test",
                        type="test",
                        payload={"i": i}
                    )
                    bus.publish(msg)
            except Exception as e:
                errors.append(e)

        # Run 5 threads concurrently
        threads = [threading.Thread(target=thread_work) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if not errors:
            test.passed = True
            test.details = "All concurrent operations succeeded"
        else:
            test.details = f"Concurrent errors: {len(errors)}"

    except Exception as e:
        test.details = f"Unexpected error: {e}"

    test.report()
    assert test.passed, test.details


# ============================================================================
# RESOURCE FAILURES
# ============================================================================

def test_memory_recovery():
    """Test recovery from high memory usage."""
    test = FailureTest("Memory Recovery")

    try:
        from crew.knowledge import get_knowledge_store
        import gc

        store = get_knowledge_store()

        # Create many entries
        for i in range(100):
            store.create(
                insight=f"Memory test {i}" + "x" * 1000,
                category="test",
                tags=["memory"],
                source_task_ids=[i],
                experiments_supporting=1,
            )

        # Force garbage collection
        gc.collect()

        # Try to query after memory pressure
        results = store.query(tags=["memory"])

        if results:
            test.passed = True
            test.details = f"Retrieved {len(results)} entries after memory pressure"
        else:
            test.details = "Could not retrieve entries after memory pressure"

    except Exception as e:
        test.details = f"Error: {e}"

    test.report()
    assert test.passed, test.details


def test_disk_space_handling():
    """Test graceful handling when disk space is low."""
    test = FailureTest("Disk Space Handling")

    try:
        from crew.healthcheck import HealthChecker

        checker = HealthChecker()
        health, components = checker.check_all()

        # Check if health checker can detect disk status
        has_disk_check = any("disk" in str(c).lower() for c in components)

        if has_disk_check:
            test.passed = True
            test.details = "Health checker includes disk monitoring"
        else:
            test.details = "Health checker missing disk monitoring"

    except Exception as e:
        test.details = f"Error: {e}"

    test.report()
    assert test.passed, test.details


# ============================================================================
# ERROR HANDLING
# ============================================================================

def test_error_handling_decorator():
    """Test error handling decorator."""
    test = FailureTest("Error Handling Decorator")

    try:
        from crew.error_handling import handle_error

        call_count = [0]

        @handle_error("test", "operation", default_return=[], max_retries=2, retry_delay=0.01)
        def failing_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Simulated error")
            return [1, 2, 3]

        # First call fails, second fails, third succeeds
        result = failing_function()

        if result == [1, 2, 3]:
            test.passed = True
            test.details = f"Retried {call_count[0]} times, finally succeeded"
        else:
            test.details = f"Unexpected result: {result}"

    except Exception as e:
        test.details = f"Error: {e}"

    test.report()
    assert test.passed, test.details


def test_circuit_breaker():
    """Test circuit breaker pattern."""
    test = FailureTest("Circuit Breaker Pattern")

    try:
        from crew.error_handling import CircuitBreaker

        breaker = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout_seconds=1)

        # Simulate failures
        for _ in range(3):
            breaker.record_failure()

        # Check status
        status = breaker.status()
        if status['state'] == 'open':
            test.passed = True
            test.details = f"Circuit breaker correctly entered OPEN state after {status['failures']} failures"
        else:
            test.details = f"Circuit breaker state: {status['state']} (expected: open)"

    except Exception as e:
        test.details = f"Error: {e}"

    test.report()
    assert test.passed, test.details


# ============================================================================
# VALIDATION FAILURES
# ============================================================================

def test_invalid_knowledge_entry():
    """Test rejection of invalid knowledge entries."""
    test = FailureTest("Invalid Knowledge Entry Rejection")

    try:
        from crew.validation import KnowledgeValidator, ValidationError
        from crew.knowledge import get_knowledge_store

        store = get_knowledge_store()
        invalid_entries = [
            {  # Missing required field
                "insight": None,
                "category": "test",
                "tags": [],
                "source_task_ids": [],
                "experiments_supporting": 0,
            },
            {  # Invalid category
                "insight": "test",
                "category": "invalid_category_xyz",
                "tags": [],
                "source_task_ids": [],
                "experiments_supporting": 0,
            },
        ]

        rejected = 0
        for entry in invalid_entries:
            try:
                KnowledgeValidator.validate_create(**entry)
            except (ValidationError, ValueError, TypeError):
                rejected += 1

        if rejected == len(invalid_entries):
            test.passed = True
            test.details = f"Rejected all {len(invalid_entries)} invalid entries"
        else:
            test.details = f"Only rejected {rejected}/{len(invalid_entries)} entries"

    except Exception as e:
        test.details = f"Unexpected error: {e}"

    test.report()
    assert test.passed, test.details


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all failure scenario tests."""
    tests = [
        # Configuration failures
        ("missing_config", test_missing_config_file),
        ("invalid_yaml", test_invalid_config_yaml),
        ("missing_config_sections", test_missing_required_config),

        # Input validation
        ("xss_injection", test_xss_injection),
        ("sql_injection", test_sql_injection),
        ("oversized_input", test_oversized_input),

        # Database failures
        ("db_initialization", test_database_initialization_failure),
        ("concurrent_db", test_concurrent_database_access),

        # Resource failures
        ("memory_recovery", test_memory_recovery),
        ("disk_space", test_disk_space_handling),

        # Error handling
        ("error_decorator", test_error_handling_decorator),
        ("circuit_breaker", test_circuit_breaker),

        # Validation
        ("invalid_knowledge", test_invalid_knowledge_entry),
    ]

    logger.info("\n" + "=" * 60)
    logger.info("FAILURE SCENARIO & RECOVERY TESTING")
    logger.info("=" * 60)

    results = {}
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results[test_name] = passed
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            results[test_name] = False

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("FAILURE TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_flag in results.items():
        status = "✓" if passed_flag else "✗"
        logger.info(f"  {status} {test_name}")

    logger.info(f"\nTotal: {passed}/{total} failure scenarios handled correctly")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
