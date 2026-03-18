"""Performance optimization for AutoClaw.

Optimizations:
- Database query optimization and caching
- Connection pooling
- Batch operations
- Index creation
- Query result caching
"""

import logging
import sqlite3
import functools
import time
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class QueryCache:
    """Simple LRU cache for query results."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """Initialize cache."""
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, tuple] = {}  # (result, timestamp)

    def get(self, key: str) -> Optional[Any]:
        """Get from cache if not expired."""
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                return result
            else:
                del self.cache[key]
        return None

    def put(self, key: str, value: Any):
        """Put value in cache."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(),
                            key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[key] = (value, datetime.now())

    def clear(self):
        """Clear cache."""
        self.cache.clear()

    def invalidate_pattern(self, pattern: str):
        """Invalidate keys matching pattern."""
        keys_to_remove = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_remove:
            del self.cache[key]


class ConnectionPool:
    """Simple connection pool for SQLite databases."""

    def __init__(self, database: str, pool_size: int = 5):
        """Initialize connection pool."""
        self.database = database
        self.pool_size = pool_size
        self.connections: List[sqlite3.Connection] = []
        self.available = []

        # Create connections
        for _ in range(pool_size):
            conn = sqlite3.connect(database, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connections.append(conn)
            self.available.append(True)

        logger.debug(f"Created connection pool ({pool_size} connections)")

    def get(self) -> sqlite3.Connection:
        """Get a connection from the pool."""
        for i, avail in enumerate(self.available):
            if avail:
                self.available[i] = False
                return self.connections[i]

        # All connections busy, wait and retry
        logger.warning("Connection pool exhausted, waiting...")
        while True:
            for i, avail in enumerate(self.available):
                if avail:
                    self.available[i] = False
                    return self.connections[i]
            time.sleep(0.1)

    def release(self, conn: sqlite3.Connection):
        """Release connection back to pool."""
        for i, c in enumerate(self.connections):
            if c is conn:
                self.available[i] = True
                break

    def close_all(self):
        """Close all connections."""
        for conn in self.connections:
            conn.close()
        logger.debug("Closed all connections")


class DatabaseOptimizer:
    """Optimize database performance."""

    @staticmethod
    def create_indices(database_path: str):
        """Create performance indices."""
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        indices = [
            # Knowledge store indices
            ("idx_knowledge_tags", "knowledge_entries", "(tags)"),
            ("idx_knowledge_status", "knowledge_entries", "(status)"),
            ("idx_knowledge_category", "knowledge_entries", "(category)"),
            ("idx_knowledge_created", "knowledge_entries", "(created_at)"),
            ("idx_knowledge_confidence", "knowledge_entries", "(confidence)"),

            # Message bus indices
            ("idx_messages_from_agent", "messages", "(from_agent)"),
            ("idx_messages_to_agent", "messages", "(to_agent)"),
            ("idx_messages_status", "messages", "(status)"),
            ("idx_messages_created", "messages", "(created_at)"),
            ("idx_messages_expires", "messages", "(expires_at)"),

            # Handoff indices
            ("idx_handoff_task", "handoffs", "(task_id)"),
            ("idx_handoff_generation", "handoffs", "(generation)"),

            # Trigger indices
            ("idx_trigger_enabled", "triggers", "(enabled)"),
            ("idx_trigger_last_fired", "triggers", "(last_fired_at)"),
        ]

        for idx_name, table, column in indices:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} {column}")
                logger.debug(f"Created index: {idx_name}")
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not create index {idx_name}: {e}")

        conn.commit()
        conn.close()

    @staticmethod
    def enable_wal_mode(database_path: str):
        """Enable WAL mode for better concurrency."""
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            result = cursor.fetchone()[0]
            logger.info(f"Enabled WAL mode: {result}")
        except Exception as e:
            logger.warning(f"Could not enable WAL mode: {e}")

        conn.close()

    @staticmethod
    def optimize_pragmas(database_path: str):
        """Set performance pragmas."""
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        pragmas = [
            ("PRAGMA synchronous = NORMAL", "Reduce sync overhead"),
            ("PRAGMA cache_size = -64000", "64MB cache"),
            ("PRAGMA temp_store = MEMORY", "Memory temp storage"),
            ("PRAGMA query_only = FALSE", "Allow writes"),
        ]

        for pragma, description in pragmas:
            try:
                cursor.execute(pragma)
                logger.debug(f"Set: {description}")
            except Exception as e:
                logger.warning(f"Could not set {description}: {e}")

        conn.commit()
        conn.close()

    @staticmethod
    def analyze_and_optimize(database_path: str):
        """Run ANALYZE and VACUUM."""
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        try:
            # Analyze tables to update statistics
            cursor.execute("ANALYZE")
            logger.info("Ran ANALYZE on database")

            # Defragment
            cursor.execute("VACUUM")
            logger.info("Ran VACUUM on database")

        except Exception as e:
            logger.warning(f"Error optimizing database: {e}")

        conn.close()


def cached_query(cache: QueryCache, ttl_seconds: int = 300):
    """Decorator to cache query results."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {func.__name__}")
                return cached_result

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            cache.put(cache_key, result)

            return result

        return wrapper
    return decorator


def timed_operation(operation_name: str):
    """Decorator to time operations."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = (time.time() - start) * 1000  # ms

            if elapsed > 100:  # Log slow operations
                logger.warning(f"Slow operation: {operation_name} took {elapsed:.1f}ms")
            else:
                logger.debug(f"Operation: {operation_name} took {elapsed:.1f}ms")

            return result

        return wrapper
    return decorator


class BatchOperations:
    """Batch multiple operations for efficiency."""

    @staticmethod
    def batch_insert_knowledge(store, entries: List[Dict], batch_size: int = 100):
        """Insert knowledge entries in batches."""
        inserted = 0
        for i in range(0, len(entries), batch_size):
            batch = entries[i:i+batch_size]
            for entry in batch:
                try:
                    store.create(**entry)
                    inserted += 1
                except Exception as e:
                    logger.error(f"Error inserting entry: {e}")

        logger.info(f"Batch inserted {inserted}/{len(entries)} knowledge entries")
        return inserted

    @staticmethod
    def batch_delete_messages(bus, message_ids: List[int], batch_size: int = 100):
        """Delete messages in batches."""
        deleted = 0
        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i:i+batch_size]
            for msg_id in batch:
                try:
                    bus.delete(msg_id)
                    deleted += 1
                except Exception as e:
                    logger.error(f"Error deleting message {msg_id}: {e}")

        logger.info(f"Batch deleted {deleted}/{len(message_ids)} messages")
        return deleted


class PerformanceMonitor:
    """Monitor system performance."""

    def __init__(self):
        """Initialize monitor."""
        self.metrics = {}

    def record_operation(self, name: str, duration_ms: float):
        """Record operation timing."""
        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append(duration_ms)

    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return {}

        times = self.metrics[operation]
        if not times:
            return {}

        sorted_times = sorted(times)
        p95_index = max(0, int(len(times) * 0.95) - 1)

        return {
            "count": len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "avg_ms": sum(times) / len(times),
            "p95_ms": sorted_times[p95_index] if times else 0,
        }

    def get_report(self) -> Dict[str, Dict[str, float]]:
        """Get performance report."""
        return {name: self.get_stats(name) for name in self.metrics}


# Global instances
_query_cache = QueryCache(max_size=100, ttl_seconds=300)
_performance_monitor = PerformanceMonitor()


def get_query_cache() -> QueryCache:
    """Get global query cache."""
    return _query_cache


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor."""
    return _performance_monitor


def optimize_databases(data_dir: Path = Path("data")):
    """Optimize all databases."""
    logger.info("Starting database optimization...")

    databases = [
        "knowledge.db",
        "message_bus.db",
        "handoff.db",
        "triggers.db",
    ]

    for db_name in databases:
        db_path = data_dir / db_name
        if db_path.exists():
            logger.info(f"\nOptimizing {db_name}...")
            DatabaseOptimizer.enable_wal_mode(str(db_path))
            DatabaseOptimizer.optimize_pragmas(str(db_path))
            DatabaseOptimizer.create_indices(str(db_path))
            DatabaseOptimizer.analyze_and_optimize(str(db_path))
        else:
            logger.warning(f"Database not found: {db_path}")

    logger.info("\nDatabase optimization complete")
