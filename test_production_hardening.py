#!/usr/bin/env python3
"""Comprehensive tests for production hardening modules.

Tests:
1. Input validation (all validators)
2. Configuration loading and validation
3. Health checks (all components)
4. Performance optimization (caching, pooling)
5. Security (API keys, audit logging, rate limiting)
6. Startup sequence
"""

import logging
import tempfile
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class TestRunner:
    """Run test groups and track results."""

    def __init__(self):
        """Initialize test runner."""
        self.passed = 0
        self.failed = 0
        self.current_group = None
        self.group_results = {}

    def run_group(self, group_name: str):
        """Start a test group."""
        self.current_group = group_name
        self.group_results[group_name] = []
        logger.info(f"\n{'=' * 60}")
        logger.info(f"TEST GROUP: {group_name}")
        logger.info('=' * 60)

    def test(self, name: str, func):
        """Run a test."""
        try:
            func()
            logger.info(f"  ✓ {name}")
            self.passed += 1
            self.group_results[self.current_group].append((name, True, None))
        except Exception as e:
            logger.error(f"  ✗ {name}: {e}")
            self.failed += 1
            self.group_results[self.current_group].append((name, False, str(e)))

    def report(self):
        """Print test report."""
        logger.info(f"\n{'=' * 60}")
        logger.info("TEST REPORT")
        logger.info('=' * 60)

        for group, results in self.group_results.items():
            passed = sum(1 for _, success, _ in results if success)
            total = len(results)
            status = "✓ PASSED" if passed == total else "✗ FAILED"
            logger.info(f"\n{group}: {passed}/{total} {status}")

            for name, success, error in results:
                if not success:
                    logger.info(f"  - {name}: {error}")

        logger.info(f"\n{'=' * 60}")
        logger.info(f"TOTAL: {self.passed} passed, {self.failed} failed")
        logger.info('=' * 60)

        return self.failed == 0


# ============================================================================
# INPUT VALIDATION TESTS
# ============================================================================

def test_string_validator():
    """Test string input validation."""
    from crew.validation import StringValidator, ValidationError

    # Valid string
    result = StringValidator.validate("hello world", "test")
    assert result == "hello world"

    # Empty string
    try:
        StringValidator.validate("", "test")
        assert False, "Should reject empty string"
    except ValidationError:
        pass

    # Too long
    try:
        StringValidator.validate("x" * 20000, "test", max_length=1000)
        assert False, "Should reject long string"
    except ValidationError:
        pass

    # XSS pattern
    try:
        StringValidator.validate("<script>alert('xss')</script>", "test")
        assert False, "Should reject XSS"
    except ValidationError:
        pass

    logger.info("String validation: all checks passed")


def test_int_validator():
    """Test integer input validation."""
    from crew.validation import IntValidator, ValidationError

    # Valid int
    result = IntValidator.validate(42, "test", min_val=0, max_val=100)
    assert result == 42

    # Below min
    try:
        IntValidator.validate(-5, "test", min_val=0)
        assert False, "Should reject below min"
    except ValidationError:
        pass

    # Above max
    try:
        IntValidator.validate(150, "test", max_val=100)
        assert False, "Should reject above max"
    except ValidationError:
        pass

    logger.info("Integer validation: all checks passed")


def test_list_validator():
    """Test list input validation."""
    from crew.validation import ListValidator, ValidationError

    # Valid list
    result = ListValidator.validate([1, 2, 3], "test", element_type=int)
    assert result == [1, 2, 3]

    # Wrong element type
    try:
        ListValidator.validate([1, "two", 3], "test", element_type=int)
        assert False, "Should reject mixed types"
    except ValidationError:
        pass

    # Too long
    try:
        ListValidator.validate([1] * 2000, "test", max_length=100)
        assert False, "Should reject long list"
    except ValidationError:
        pass

    logger.info("List validation: all checks passed")


def test_knowledge_validator():
    """Test knowledge store input validation."""
    from crew.validation import KnowledgeValidator, ValidationError

    # Valid knowledge entry
    result = KnowledgeValidator.validate_create(
        insight="This is a test insight",
        category="architecture",
        tags=["test"],
        source_task_ids=[1],
        experiments_supporting=5
    )
    assert result["insight"] == "This is a test insight"

    # Invalid category
    try:
        KnowledgeValidator.validate_create(
            insight="Test",
            category="invalid_category",
            tags=[],
            source_task_ids=[1],
            experiments_supporting=0
        )
        assert False, "Should reject invalid category"
    except ValidationError:
        pass

    logger.info("Knowledge validation: all checks passed")


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

def test_config_loading():
    """Test configuration loading."""
    from crew.config import ConfigLoader
    import yaml

    # Create temp config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_data = {
            'crew': {'name': 'TestCrew'},
            'llm': {'provider': 'anthropic', 'model': 'test-model', 'api_key': 'test-key'},
            'knowledge': {'max_entries': 100},
            'triggers': {'enabled': True, 'triggers': []},
            'notifications': {'external_channels': []},
            'experiments': {'time_budget_seconds': 100},
            'adaptive': {'enabled': True},
            'flowstate': {'enabled': False},
            'hardware': {'profile': None},
            'daemon': {'log_level': 'info'},
            'message_bus': {'database': 'test.db'},
            'error_handling': {'enable_audit': True},
            'performance': {'db_pool_size': 3},
            'security': {'validate_api_keys': False},
            'features': {'swarm_mode': False},
        }
        yaml.dump(config_data, f)
        temp_file = f.name

    try:
        loader = ConfigLoader(Path(temp_file))
        assert loader.get('crew.name') == 'TestCrew'
        assert loader.get('llm.model') == 'test-model'
        assert loader.get('knowledge.max_entries') == 100
        logger.info("Configuration loading: all checks passed")
    finally:
        Path(temp_file).unlink()


def test_config_env_interpolation():
    """Test environment variable interpolation."""
    from crew.config import ConfigLoader
    import yaml
    import os

    os.environ['TEST_API_KEY'] = 'secret-key-123'

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_data = {
            'crew': {'name': 'TestCrew'},
            'llm': {'provider': 'anthropic', 'model': 'test', 'api_key': '${TEST_API_KEY}'},
            'knowledge': {'max_entries': 100},
            'triggers': {'enabled': True, 'triggers': []},
            'notifications': {'external_channels': []},
            'experiments': {},
            'adaptive': {},
            'flowstate': {},
            'hardware': {},
            'daemon': {},
            'message_bus': {},
            'error_handling': {},
            'performance': {},
            'security': {},
            'features': {},
        }
        yaml.dump(config_data, f)
        temp_file = f.name

    try:
        loader = ConfigLoader(Path(temp_file))
        assert loader.get('llm.api_key') == 'secret-key-123'
        logger.info("Environment interpolation: all checks passed")
    finally:
        Path(temp_file).unlink()


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

def test_health_checker():
    """Test health checking."""
    from crew.healthcheck import HealthChecker, HealthStatus

    checker = HealthChecker()
    overall_status, components = checker.check_all()

    # Should return valid status
    assert overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]

    # Should check multiple components
    assert len(components) >= 5

    # Each component should have status
    for component in components:
        assert component.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert component.latency_ms >= 0

    logger.info(f"Health check: {overall_status.value} ({len(components)} components checked)")


def test_health_metrics():
    """Test Prometheus metrics export."""
    from crew.healthcheck import HealthChecker

    checker = HealthChecker()
    metrics = checker.get_prometheus_metrics()

    # Should contain Prometheus format
    assert "autoclaw_health_status" in metrics
    assert "autoclaw_component_health" in metrics
    assert "autoclaw_component_latency_ms" in metrics

    logger.info("Health metrics: Prometheus export working")


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

def test_query_cache():
    """Test query caching."""
    from crew.performance import QueryCache

    cache = QueryCache(max_size=10, ttl_seconds=300)

    # Put and get
    cache.put("key1", "value1")
    assert cache.get("key1") == "value1"

    # Cache miss
    assert cache.get("missing") is None

    # TTL expiration
    cache2 = QueryCache(max_size=10, ttl_seconds=0)
    cache2.put("key2", "value2")
    import time
    time.sleep(0.1)
    assert cache2.get("key2") is None

    logger.info("Query cache: all checks passed")


def test_connection_pool():
    """Test connection pooling."""
    from crew.performance import ConnectionPool
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        pool = ConnectionPool(db_path, pool_size=3)

        # Get connections
        conn1 = pool.get()
        assert conn1 is not None

        # Release
        pool.release(conn1)

        # Get again
        conn2 = pool.get()
        assert conn2 is not None

        pool.release(conn2)
        pool.close_all()

        logger.info("Connection pooling: all checks passed")
    finally:
        Path(db_path).unlink()


def test_performance_monitor():
    """Test performance monitoring."""
    from crew.performance import PerformanceMonitor

    monitor = PerformanceMonitor()

    # Record operations
    monitor.record_operation("test_op", 10.5)
    monitor.record_operation("test_op", 20.3)
    monitor.record_operation("test_op", 15.2)

    # Get stats
    stats = monitor.get_stats("test_op")
    assert stats["count"] == 3, f"Count mismatch: {stats['count']}"
    assert stats["min_ms"] == 10.5, f"Min mismatch: {stats['min_ms']}"
    assert stats["max_ms"] == 20.3, f"Max mismatch: {stats['max_ms']}"
    assert abs(stats["avg_ms"] - 15.33) < 0.01, f"Avg mismatch: {stats['avg_ms']}"

    logger.info("Performance monitoring: all checks passed")


# ============================================================================
# SECURITY TESTS
# ============================================================================

def test_api_key_manager():
    """Test API key management."""
    from crew.security import APIKeyManager
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name

    try:
        manager = APIKeyManager(Path(temp_file))

        # Create key
        key_id, secret = manager.create_key("test_key", ["read", "write"])
        assert key_id is not None
        assert secret is not None

        # Validate key
        assert manager.validate_key(key_id, secret) is True

        # Invalid secret
        assert manager.validate_key(key_id, "wrong-secret") is False

        # Revoke key
        manager.revoke_key(key_id)
        assert manager.validate_key(key_id, secret) is False

        # Rotate key
        new_id, new_secret = manager.rotate_key(key_id)
        assert new_id != key_id
        assert manager.validate_key(new_id, new_secret) is True

        logger.info("API key management: all checks passed")
    finally:
        Path(temp_file).unlink()


def test_audit_logger():
    """Test audit logging."""
    from crew.security import AuditLogger
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        temp_file = f.name

    try:
        logger_obj = AuditLogger(Path(temp_file))

        # Log event
        logger_obj.log_event(
            event_type="test",
            operation="test_op",
            user="test_user",
            details={"key": "value"},
            status="success"
        )

        # Get events
        events = logger_obj.get_events(event_type="test", hours=24)
        assert len(events) >= 1
        assert events[0]["operation"] == "test_op"
        assert events[0]["user"] == "test_user"

        logger.info("Audit logging: all checks passed")
    finally:
        Path(temp_file).unlink()


def test_rate_limiter():
    """Test rate limiting."""
    from crew.security import RateLimiter

    limiter = RateLimiter(limits_per_minute=5)

    # Should allow requests
    for i in range(5):
        assert limiter.is_allowed("client1") is True

    # Should reject when limit reached
    assert limiter.is_allowed("client1") is False

    # Check remaining
    remaining = limiter.get_remaining("client1")
    assert remaining == 0

    logger.info("Rate limiting: all checks passed")


def test_password_validator():
    """Test password validation."""
    from crew.security import PasswordValidator

    # Strong password
    valid, msg = PasswordValidator.validate("MyP@ssw0rd123")
    assert valid is True

    # Too short
    valid, msg = PasswordValidator.validate("Short1!")
    assert valid is False

    # No uppercase
    valid, msg = PasswordValidator.validate("myp@ssw0rd123")
    assert valid is False

    # No numbers
    valid, msg = PasswordValidator.validate("MyPassword@")
    assert valid is False

    logger.info("Password validation: all checks passed")


# ============================================================================
# STARTUP TESTS
# ============================================================================

def test_directory_creation():
    """Test directory structure creation."""
    from crew.startup import create_directory_structure
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            create_directory_structure()

            # Check directories exist
            assert Path("data").exists()
            assert Path("data/agents").exists()
            assert Path("data/handoffs").exists()
            assert Path("data/flowstate").exists()
            assert Path("data/logs").exists()

            logger.info("Directory creation: all checks passed")
        finally:
            os.chdir(old_cwd)


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all tests."""
    runner = TestRunner()

    # Input validation tests
    runner.run_group("Input Validation")
    runner.test("String Validator", test_string_validator)
    runner.test("Integer Validator", test_int_validator)
    runner.test("List Validator", test_list_validator)
    runner.test("Knowledge Validator", test_knowledge_validator)

    # Configuration tests
    runner.run_group("Configuration")
    runner.test("Config Loading", test_config_loading)
    runner.test("Environment Interpolation", test_config_env_interpolation)

    # Health check tests
    runner.run_group("Health Checks")
    runner.test("Health Checker", test_health_checker)
    runner.test("Health Metrics", test_health_metrics)

    # Performance tests
    runner.run_group("Performance Optimization")
    runner.test("Query Cache", test_query_cache)
    runner.test("Connection Pool", test_connection_pool)
    runner.test("Performance Monitor", test_performance_monitor)

    # Security tests
    runner.run_group("Security Hardening")
    runner.test("API Key Manager", test_api_key_manager)
    runner.test("Audit Logger", test_audit_logger)
    runner.test("Rate Limiter", test_rate_limiter)
    runner.test("Password Validator", test_password_validator)

    # Startup tests
    runner.run_group("Startup Procedures")
    runner.test("Directory Creation", test_directory_creation)

    # Print report
    success = runner.report()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
