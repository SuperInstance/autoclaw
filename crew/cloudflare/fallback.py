"""Local fallback adapters for Cloudflare services.

Every CF adapter (cf_kv.py, cf_d1.py, cf_r2.py, cf_ai.py) has an identical
local fallback here. The calling code never needs to know which is in use.

Fallback implementations:
  LocalKV  → Python dict + YAML file (same interface as CF KV)
  LocalD1  → SQLite database (same interface as CF D1)
  LocalR2  → Local filesystem directory (same interface as CF R2)
  LocalAI  → Ollama (if available) → None (no inference)

All adapters follow the same contract:
  - read(key) → value or None
  - write(key, value, metadata) → True/False
  - delete(key) → True/False
  - list(prefix) → list of keys

The CreditTracker decides which backend to use:
  1. Check credits.can_use("service", ...)
  2. If OK → call CF adapter
  3. If limited → call Local fallback
"""

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Optional, Any, List, Dict
import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# LocalKV — replaces Cloudflare KV
# ============================================================================

class LocalKV:
    """File-backed key-value store. Interface matches CF KV.

    Data: data/fallback/kv/{namespace}.yaml
    """

    def __init__(self, namespace: str = "default"):
        """Args:
            namespace: KV namespace name (matches CF KV namespace)
        """
        self.namespace = namespace
        self._path = Path(f"data/fallback/kv/{namespace}.yaml")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        self._load()

    def get(self, key: str) -> Optional[Any]:
        """Get a value by key. Returns None if not found."""
        with self._lock:
            return self._data.get(key)

    def put(self, key: str, value: Any, metadata: Optional[Dict] = None) -> bool:
        """Write a key-value pair."""
        with self._lock:
            self._data[key] = value
        self._save()
        return True

    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if deleted."""
        with self._lock:
            existed = key in self._data
            self._data.pop(key, None)
        if existed:
            self._save()
        return existed

    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys matching prefix."""
        with self._lock:
            return [k for k in self._data.keys() if k.startswith(prefix)]

    def _load(self):
        if self._path.exists():
            try:
                self._data = yaml.safe_load(self._path.read_text()) or {}
            except Exception:
                self._data = {}

    def _save(self):
        with self._lock:
            try:
                self._path.write_text(yaml.dump(self._data, default_flow_style=False))
            except Exception as e:
                logger.debug(f"LocalKV save failed: {e}")


# ============================================================================
# LocalD1 — replaces Cloudflare D1 (SQLite)
# ============================================================================

class LocalD1:
    """Local SQLite database. Interface matches CF D1.

    Data: data/fallback/d1/{database_name}.db
    """

    def __init__(self, database_name: str = "autocrew"):
        """Args:
            database_name: D1 database name
        """
        self.database_name = database_name
        self._path = Path(f"data/fallback/d1/{database_name}.db")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def execute(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute SQL and return results as list of dicts.

        Args:
            sql: SQL statement
            params: Query parameters (positional)

        Returns: List of row dicts
        """
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute(sql, params)
                conn.commit()
                if cursor.description:
                    cols = [d[0] for d in cursor.description]
                    return [dict(zip(cols, row)) for row in cursor.fetchall()]
                return []
            except Exception as e:
                logger.debug(f"LocalD1 execute failed: {e}")
                raise
            finally:
                conn.close()

    def execute_many(self, sql: str, params_list: List[tuple]) -> int:
        """Execute SQL for multiple parameter sets.

        Returns: Number of rows affected
        """
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.executemany(sql, params_list)
                conn.commit()
                return cursor.rowcount
            except Exception as e:
                logger.debug(f"LocalD1 executemany failed: {e}")
                return 0
            finally:
                conn.close()

    def create_table(self, sql: str):
        """Create a table if it doesn't exist."""
        self.execute(sql)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn


# ============================================================================
# LocalR2 — replaces Cloudflare R2 (object storage)
# ============================================================================

class LocalR2:
    """Local filesystem object store. Interface matches CF R2.

    Data: data/fallback/r2/{bucket_name}/
    """

    def __init__(self, bucket_name: str = "autocrew-cold"):
        """Args:
            bucket_name: R2 bucket name
        """
        self.bucket_name = bucket_name
        self._root = Path(f"data/fallback/r2/{bucket_name}")
        self._root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes, metadata: Optional[Dict] = None) -> bool:
        """Upload an object.

        Args:
            key: Object key (path-like, e.g., 'knowledge/cold/2026/01/entry_1.json.gz')
            data: Raw bytes to store
            metadata: Optional metadata dict (stored as sidecar .meta.json)

        Returns: True on success
        """
        try:
            obj_path = self._root / key
            obj_path.parent.mkdir(parents=True, exist_ok=True)
            obj_path.write_bytes(data)

            if metadata:
                meta_path = obj_path.with_suffix(obj_path.suffix + ".meta.json")
                meta_path.write_text(json.dumps(metadata))

            return True
        except Exception as e:
            logger.debug(f"LocalR2 put failed: {e}")
            return False

    def get(self, key: str) -> Optional[bytes]:
        """Download an object.

        Returns: Raw bytes or None if not found
        """
        obj_path = self._root / key
        if obj_path.exists():
            try:
                return obj_path.read_bytes()
            except Exception as e:
                logger.debug(f"LocalR2 get failed: {e}")
        return None

    def delete(self, key: str) -> bool:
        """Delete an object. Returns True if deleted."""
        obj_path = self._root / key
        meta_path = obj_path.with_suffix(obj_path.suffix + ".meta.json")
        try:
            if obj_path.exists():
                obj_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
            return True
        except Exception as e:
            logger.debug(f"LocalR2 delete failed: {e}")
            return False

    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List objects with a prefix.

        Returns: List of {key, size, last_modified} dicts
        """
        results = []
        prefix_path = self._root / prefix if prefix else self._root

        try:
            for obj_path in self._root.rglob("*"):
                if obj_path.is_file() and not obj_path.name.endswith(".meta.json"):
                    key = str(obj_path.relative_to(self._root))
                    if not prefix or key.startswith(prefix):
                        stat = obj_path.stat()
                        results.append({
                            "key": key,
                            "size": stat.st_size,
                            "last_modified": stat.st_mtime,
                        })
        except Exception as e:
            logger.debug(f"LocalR2 list failed: {e}")

        return results

    def head(self, key: str) -> Optional[Dict[str, Any]]:
        """Get object metadata without downloading.

        Returns: {key, size, last_modified} or None
        """
        obj_path = self._root / key
        if obj_path.exists():
            stat = obj_path.stat()
            return {
                "key": key,
                "size": stat.st_size,
                "last_modified": stat.st_mtime,
            }
        return None

    def get_usage_gb(self) -> float:
        """Get total storage used in GB."""
        try:
            total = sum(f.stat().st_size for f in self._root.rglob("*") if f.is_file())
            return total / (1024 ** 3)
        except Exception:
            return 0.0


# ============================================================================
# LocalAI — replaces Cloudflare Workers AI
# ============================================================================

class LocalAI:
    """Local AI inference fallback. Tries Ollama, then returns None.

    Interface matches what CF Workers AI would return — just a text string.
    """

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        """Args:
            ollama_url: Ollama API base URL
        """
        self.ollama_url = ollama_url
        self._ollama_available: Optional[bool] = None

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 500,
        system: Optional[str] = None,
    ) -> Optional[str]:
        """Generate text.

        Args:
            prompt: User prompt
            model: Model to use (defaults to smallest available)
            max_tokens: Max tokens in response
            system: System prompt

        Returns: Generated text or None if unavailable
        """
        if not self._check_ollama():
            return None

        import json
        import urllib.request

        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            data = json.dumps({
                "model": model or "tinyllama",
                "messages": messages,
                "options": {"num_predict": max_tokens},
                "stream": False,
            }).encode()

            req = urllib.request.Request(
                f"{self.ollama_url}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                return result.get("message", {}).get("content")

        except Exception as e:
            logger.debug(f"Ollama generate failed: {e}")
            return None

    def embed(self, text: str, model: Optional[str] = None) -> Optional[List[float]]:
        """Generate embeddings.

        Returns: Float list or None
        """
        if not self._check_ollama():
            return None

        import json
        import urllib.request

        try:
            data = json.dumps({
                "model": model or "nomic-embed-text",
                "prompt": text,
            }).encode()

            req = urllib.request.Request(
                f"{self.ollama_url}/api/embeddings",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return result.get("embedding")

        except Exception as e:
            logger.debug(f"Ollama embed failed: {e}")
            return None

    def _check_ollama(self) -> bool:
        """Check if Ollama is running."""
        if self._ollama_available is not None:
            return self._ollama_available

        import urllib.request
        try:
            with urllib.request.urlopen(f"{self.ollama_url}/api/tags", timeout=2) as resp:
                resp.read()
            self._ollama_available = True
        except Exception:
            self._ollama_available = False

        if not self._ollama_available:
            logger.debug("Ollama not available, AI inference disabled in fallback mode")

        return self._ollama_available


# ============================================================================
# Adapter Factory (returns CF or Local based on availability/credits)
# ============================================================================

def get_kv(namespace: str = "default") -> LocalKV:
    """Get KV adapter. Returns local fallback (CF adapter NYI)."""
    return LocalKV(namespace)


def get_d1(database_name: str = "autocrew") -> LocalD1:
    """Get D1 adapter. Returns local fallback (CF adapter NYI)."""
    return LocalD1(database_name)


def get_r2(bucket_name: str = "autocrew-cold") -> LocalR2:
    """Get R2 adapter. Returns local fallback (CF adapter NYI)."""
    return LocalR2(bucket_name)


def get_ai(ollama_url: str = "http://localhost:11434") -> LocalAI:
    """Get AI adapter. Returns Ollama-based local fallback."""
    return LocalAI(ollama_url)
