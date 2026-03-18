"""Cloudflare free tier credit tracker and gaming strategy.

Tracks daily/monthly usage across all CF services and decides when/how
to use credits to maximize free tier value.

Key behaviors:
  - Track usage per service (workers_ai neurons, d1 reads/writes, r2 ops, kv ops)
  - Alert agents when approaching limits
  - Schedule end-of-day credit burn (23:45-00:00 UTC)
  - Pace teacher instruction generation to end just before midnight reset
  - Never exceed free tier limits (configurable hard cap)
"""

import json
import threading
import logging
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
from typing import Dict, Any, Optional, Tuple
import yaml

logger = logging.getLogger(__name__)

USAGE_FILE = Path("data/cloudflare/usage.yaml")

# ============================================================================
# Free tier limits (update if Cloudflare changes these)
# ============================================================================

FREE_TIER_LIMITS = {
    "workers_ai": {
        "neurons_per_day": 10_000,
    },
    "d1": {
        "reads_per_day": 25_000_000,
        "writes_per_day": 50_000,
        "storage_gb": 5.0,
    },
    "r2": {
        "storage_gb": 10.0,
        "class_a_ops_per_month": 1_000_000,   # PUT, DELETE, LIST
        "class_b_ops_per_month": 10_000_000,  # GET, HEAD
    },
    "kv": {
        "reads_per_day": 100_000,
        "writes_per_day": 1_000,
        "deletes_per_day": 1_000,
        "storage_gb": 1.0,
    },
}

# Approximate neuron cost per operation for Workers AI
NEURON_COSTS = {
    "text_gen_1b_per_1k_tokens": 100,   # ~1B param models
    "text_gen_7b_per_1k_tokens": 450,   # ~7B param models
    "text_gen_70b_per_1k_tokens": 2800, # ~70B param models (if available)
    "embedding_per_input": 1,
    "image_gen": 3000,
    "audio_transcription_per_second": 10,
}


class CreditTracker:
    """Tracks and manages Cloudflare free tier credits.

    Usage:
        tracker = CreditTracker(config)

        # Before a CF call
        ok, reason = tracker.can_use("workers_ai", neurons=450)
        if ok:
            result = call_workers_ai(...)
            tracker.record("workers_ai", neurons=450)
        else:
            logger.info(f"CF credit limited: {reason}")
            # Fall back to local inference

        # Check if end-of-day batch should run
        if tracker.should_run_eod_batch():
            tracker.schedule_eod_batch()
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize credit tracker.

        Args:
            config: Cloudflare config section from main config
        """
        self.config = config or {}
        self._lock = threading.Lock()
        self._limits = self._build_limits()
        self._usage: Dict[str, Any] = {}
        self._load_usage()

        # End-of-day batch state
        self._eod_batch_scheduled = False
        self._eod_batch_ran_today = False

    # ========================================================================
    # Credit Checking
    # ========================================================================

    def can_use(
        self,
        service: str,
        neurons: int = 0,
        d1_reads: int = 0,
        d1_writes: int = 0,
        r2_class_a: int = 0,
        r2_class_b: int = 0,
        kv_reads: int = 0,
        kv_writes: int = 0,
    ) -> Tuple[bool, str]:
        """Check if a CF operation is within budget.

        Args:
            service: 'workers_ai' | 'd1' | 'r2' | 'kv'
            neurons: Workers AI neurons needed
            d1_reads/writes: D1 operations needed
            r2_class_a/b: R2 operations needed
            kv_reads/writes: KV operations needed

        Returns: (ok, reason_if_not_ok)
        """
        self._ensure_fresh_day()

        with self._lock:
            usage = self._usage

            if service == "workers_ai":
                used = usage["workers_ai"]["neurons_used_today"]
                limit = self._limits["workers_ai"]["neurons_per_day"]
                if used + neurons > limit:
                    pct = (used / limit) * 100
                    return False, f"Workers AI at {pct:.0f}% ({used}/{limit} neurons)"

            elif service == "d1":
                reads_used = usage["d1"]["reads_today"]
                writes_used = usage["d1"]["writes_today"]
                reads_limit = self._limits["d1"]["reads_per_day"]
                writes_limit = self._limits["d1"]["writes_per_day"]

                if reads_used + d1_reads > reads_limit:
                    return False, f"D1 reads at limit ({reads_used}/{reads_limit})"
                if writes_used + d1_writes > writes_limit:
                    return False, f"D1 writes at limit ({writes_used}/{writes_limit})"

            elif service == "r2":
                a_used = usage["r2"]["class_a_ops_this_month"]
                b_used = usage["r2"]["class_b_ops_this_month"]
                a_limit = self._limits["r2"]["class_a_ops_per_month"]
                b_limit = self._limits["r2"]["class_b_ops_per_month"]

                if a_used + r2_class_a > a_limit:
                    return False, f"R2 Class A ops at limit ({a_used}/{a_limit})"
                if b_used + r2_class_b > b_limit:
                    return False, f"R2 Class B ops at limit ({b_used}/{b_limit})"

            elif service == "kv":
                reads_used = usage["kv"]["reads_today"]
                writes_used = usage["kv"]["writes_today"]
                reads_limit = self._limits["kv"]["reads_per_day"]
                writes_limit = self._limits["kv"]["writes_per_day"]

                if reads_used + kv_reads > reads_limit:
                    return False, f"KV reads at limit ({reads_used}/{reads_limit})"
                if writes_used + kv_writes > writes_limit:
                    return False, f"KV writes at limit ({writes_used}/{writes_limit})"

        return True, ""

    def record(
        self,
        service: str,
        neurons: int = 0,
        d1_reads: int = 0,
        d1_writes: int = 0,
        r2_class_a: int = 0,
        r2_class_b: int = 0,
        kv_reads: int = 0,
        kv_writes: int = 0,
        agent_id: Optional[str] = None,
        purpose: Optional[str] = None,
    ):
        """Record actual credit consumption after a CF call.

        Args: Same as can_use(), plus agent_id and purpose for tracking
        """
        self._ensure_fresh_day()

        with self._lock:
            usage = self._usage
            now = datetime.now(timezone.utc).isoformat()

            if service == "workers_ai" and neurons:
                usage["workers_ai"]["neurons_used_today"] += neurons
                usage["workers_ai"]["last_call_at"] = now

            elif service == "d1":
                usage["d1"]["reads_today"] += d1_reads
                usage["d1"]["writes_today"] += d1_writes
                usage["d1"]["last_sync_at"] = now

            elif service == "r2":
                usage["r2"]["class_a_ops_this_month"] += r2_class_a
                usage["r2"]["class_b_ops_this_month"] += r2_class_b

            elif service == "kv":
                usage["kv"]["reads_today"] += kv_reads
                usage["kv"]["writes_today"] += kv_writes

        self._save_usage()
        self._check_thresholds(service)

    # ========================================================================
    # Scheduling Helpers
    # ========================================================================

    def priority_for_service(self, service: str) -> str:
        """Get priority level for using a service given current usage.

        Returns: 'free' | 'throttled' | 'critical_only' | 'blocked'
        """
        self._ensure_fresh_day()

        pct = self.usage_pct(service)
        thresholds = self.config.get("credit_strategy", {}).get("thresholds", {})

        critical_threshold = thresholds.get("critical", 0.95)
        throttle_threshold = thresholds.get("throttle", 0.85)
        warn_threshold = thresholds.get("warn", 0.70)

        if pct >= critical_threshold:
            return "critical_only"
        elif pct >= throttle_threshold:
            return "throttled"
        elif pct >= warn_threshold:
            return "warn"
        return "free"

    def usage_pct(self, service: str) -> float:
        """Get usage percentage (0.0-1.0) for daily workers_ai budget.

        Workers AI is the primary bottleneck, so this returns that.
        """
        with self._lock:
            if service == "workers_ai":
                used = self._usage["workers_ai"]["neurons_used_today"]
                limit = self._limits["workers_ai"]["neurons_per_day"]
                return used / limit if limit > 0 else 0.0
            elif service == "d1_writes":
                used = self._usage["d1"]["writes_today"]
                limit = self._limits["d1"]["writes_per_day"]
                return used / limit if limit > 0 else 0.0
        return 0.0

    def remaining_neurons(self) -> int:
        """Get remaining Workers AI neurons for today."""
        with self._lock:
            used = self._usage["workers_ai"]["neurons_used_today"]
            limit = self._limits["workers_ai"]["neurons_per_day"]
            return max(0, limit - used)

    def minutes_until_reset(self) -> int:
        """Minutes until daily limits reset (midnight UTC)."""
        now = datetime.now(timezone.utc)
        tomorrow = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=1)
        return int((tomorrow - now).total_seconds() / 60)

    def should_run_eod_batch(self) -> bool:
        """Check if end-of-day batch should be triggered.

        Conditions:
          - Hour >= 23 UTC
          - Batch hasn't run today
          - Remaining neurons > 0 (otherwise nothing to burn)
          - EOD batch enabled in config
        """
        if self._eod_batch_ran_today:
            return False

        strategy = self.config.get("credit_strategy", {})
        if not strategy.get("end_of_day_batch", {}).get("enabled", True):
            return False

        now = datetime.now(timezone.utc)
        if now.hour < 23:
            return False

        remaining = self.remaining_neurons()
        eod_threshold = strategy.get("thresholds", {}).get("end_of_day_trigger", 0.10)
        eod_min = int(self._limits["workers_ai"]["neurons_per_day"] * eod_threshold)

        return remaining >= eod_min

    def get_teacher_daily_budget(self) -> Dict[str, Any]:
        """Calculate teacher's daily instruction generation budget.

        Returns dict with:
          - neurons_per_token: cost estimate
          - tokens_available: how many tokens teacher can generate today
          - examples_per_hour: recommended rate to spread work across day
          - reserve_neurons: kept for other agents
        """
        strategy = self.config.get("credit_strategy", {})
        reserve_pct = strategy.get("teacher_pacing", {}).get("reserve_pct", 0.10)

        total = self._limits["workers_ai"]["neurons_per_day"]
        reserve = int(total * reserve_pct)
        teacher_budget = total - reserve  # What teacher can use

        # Already used today
        used = self._usage["workers_ai"]["neurons_used_today"]
        available = max(0, teacher_budget - used)

        # Smooth distribution: spread over remaining hours
        now = datetime.now(timezone.utc)
        hours_remaining = max(1, 24 - now.hour)

        # Assume 7B model at ~450 neurons/1k tokens, avg 200 tokens/example
        neurons_per_example = 450 * 0.2  # 90 neurons per example
        examples_available = int(available / neurons_per_example)
        examples_per_hour = max(0, examples_available // hours_remaining)

        return {
            "total_budget_neurons": teacher_budget,
            "used_neurons": used,
            "available_neurons": available,
            "neurons_per_example": neurons_per_example,
            "examples_available": examples_available,
            "examples_per_hour": examples_per_hour,
            "hours_remaining": hours_remaining,
        }

    # ========================================================================
    # Status
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get full credit status summary."""
        self._ensure_fresh_day()

        with self._lock:
            usage = dict(self._usage)

        remaining = self.remaining_neurons()
        minutes = self.minutes_until_reset()

        return {
            "date": str(date.today()),
            "workers_ai": {
                "neurons_used": usage["workers_ai"]["neurons_used_today"],
                "neurons_limit": self._limits["workers_ai"]["neurons_per_day"],
                "neurons_remaining": remaining,
                "pct_used": self.usage_pct("workers_ai"),
                "priority": self.priority_for_service("workers_ai"),
            },
            "d1": {
                "reads_today": usage["d1"]["reads_today"],
                "writes_today": usage["d1"]["writes_today"],
                "reads_limit": self._limits["d1"]["reads_per_day"],
                "writes_limit": self._limits["d1"]["writes_per_day"],
            },
            "r2": {
                "class_a_this_month": usage["r2"]["class_a_ops_this_month"],
                "class_b_this_month": usage["r2"]["class_b_ops_this_month"],
            },
            "kv": {
                "reads_today": usage["kv"]["reads_today"],
                "writes_today": usage["kv"]["writes_today"],
            },
            "minutes_until_reset": minutes,
            "eod_batch_ran": self._eod_batch_ran_today,
            "should_run_eod_batch": self.should_run_eod_batch(),
        }

    # ========================================================================
    # Internal
    # ========================================================================

    def _build_limits(self) -> Dict[str, Any]:
        """Build effective limits from config (allows override of defaults)."""
        limits = {}
        config_limits = self.config.get("limits", {})

        for service, defaults in FREE_TIER_LIMITS.items():
            limits[service] = {}
            for key, default_val in defaults.items():
                limits[service][key] = config_limits.get(service, {}).get(key, default_val)

        return limits

    def _ensure_fresh_day(self):
        """Reset daily counters if it's a new day."""
        today = str(date.today())
        month = datetime.now(timezone.utc).strftime("%Y-%m")

        with self._lock:
            if self._usage.get("date") != today:
                # New day — reset daily counters
                self._usage["date"] = today
                self._usage["workers_ai"]["neurons_used_today"] = 0
                self._usage["d1"]["reads_today"] = 0
                self._usage["d1"]["writes_today"] = 0
                self._usage["kv"]["reads_today"] = 0
                self._usage["kv"]["writes_today"] = 0
                self._usage["kv"]["deletes_today"] = 0
                self._eod_batch_ran_today = False
                logger.info("Daily CF credit counters reset")

            if self._usage.get("month") != month:
                # New month — reset monthly counters
                self._usage["month"] = month
                self._usage["r2"]["class_a_ops_this_month"] = 0
                self._usage["r2"]["class_b_ops_this_month"] = 0
                logger.info("Monthly CF credit counters reset")

        self._save_usage()

    def _check_thresholds(self, service: str):
        """Check if usage crossed a threshold and log/alert."""
        pct = self.usage_pct(service)
        thresholds = self.config.get("credit_strategy", {}).get("thresholds", {})

        warn = thresholds.get("warn", 0.70)
        throttle = thresholds.get("throttle", 0.85)
        critical = thresholds.get("critical", 0.95)

        if pct >= critical:
            logger.warning(f"CF {service} CRITICAL: {pct*100:.0f}% used — critical tasks only")
        elif pct >= throttle:
            logger.warning(f"CF {service} throttled: {pct*100:.0f}% used — priority < 5 only")
        elif pct >= warn:
            logger.info(f"CF {service} at {pct*100:.0f}% — approaching daily limit")

    def _load_usage(self):
        """Load usage state from disk."""
        default_usage = {
            "date": "",
            "month": "",
            "workers_ai": {
                "neurons_used_today": 0,
                "last_call_at": None,
            },
            "d1": {
                "reads_today": 0,
                "writes_today": 0,
                "storage_used_gb": 0.0,
                "last_sync_at": None,
            },
            "r2": {
                "class_a_ops_this_month": 0,
                "class_b_ops_this_month": 0,
                "storage_used_gb": 0.0,
            },
            "kv": {
                "reads_today": 0,
                "writes_today": 0,
                "deletes_today": 0,
            },
            "end_of_day_batch_ran": False,
        }

        if USAGE_FILE.exists():
            try:
                loaded = yaml.safe_load(USAGE_FILE.read_text()) or {}
                # Merge with defaults (add any missing keys)
                for key, val in default_usage.items():
                    if key not in loaded:
                        loaded[key] = val
                    elif isinstance(val, dict):
                        for subkey, subval in val.items():
                            if subkey not in loaded[key]:
                                loaded[key][subkey] = subval
                self._usage = loaded
            except Exception as e:
                logger.warning(f"Could not load CF usage: {e}")
                self._usage = default_usage
        else:
            self._usage = default_usage

    def _save_usage(self):
        """Persist usage state to disk."""
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            USAGE_FILE.write_text(yaml.dump(self._usage, default_flow_style=False))
        except Exception as e:
            logger.debug(f"Could not save CF usage: {e}")
