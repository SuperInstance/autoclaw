#!/usr/bin/env python3
"""
Melt Pressure Monitor — Active CNS v3 Telemetry Watchdog

Continuously polls fleet telemetry, detects melt pressure trends before
critical breach, and emits actionable CNS response packets.

Runs as:
  - Standalone daemon:   python3 scripts/melt_pressure_monitor.py
  - Inline in crew/     from scripts.melt_pressure_monitor import MeltPressureMonitor

Thresholds (configurable):
  WATCH:      P_melt > 0.5 * max_crystallization_rate
  WARNING:    P_melt > max_crystallization_rate  (MOLT-1)
  CRITICAL:   P_melt > 1.5 * max_crystallization_rate  OR molt_count >= 4
  THERMAL:    temperature > 5.0  (overheating)
  FROZEN:     delta == 0  (agent frozen)

Actions emitted as CNS packets:
  COOL_DOWN, VALIDATE, THROTTLE, MOLT, MONITOR
"""
import os
import sys
import json
import time
import math
import signal
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

# Paths (match cns_monitor_v3_telemetry.py)
INBOX_PATH = os.path.expanduser("~/.hermes/cns_inbox/")
OUTBOX_PATH = os.path.expanduser("~/.hermes/cns_outbox/")
STATE_FILE = os.path.expanduser("~/.hermes/cns_melt_pressure_state.json")
LOG_FILE = os.path.expanduser("~/.hermes/cns_melt_pressure.log")

POLL_INTERVAL = 5  # seconds
HISTORY_WINDOW = 20  # rolling window size per agent
MAX_MOLT_COUNT = 5
MAX_STALENESS_SECONDS = 7200  # 2 hours

LEVEL_RANK = {"NORMAL": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3}
def _max_level(*levels: str) -> str:
    return max(levels, key=lambda x: LEVEL_RANK[x])

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TelemetryQuantum:
    """Single agent telemetry snapshot."""
    agent_id: str
    gamma: float = 0.0
    eta: float = 0.0
    delta: float = 0.0
    temperature: float = 1.0
    semantic_distance: float = 0.5
    melt_pressure: float = 0.0
    max_crystallization_rate: float = 0.0
    deterministic: bool = False
    molt_count: int = 0
    capability: float = 1.0
    tau: float = 0.5
    timestamp: str = ""
    is_dreaming: bool = False
    temperature_idle: float = 1.5
    temperature_task: float = 1.0
    temp_rise_rate: float = 0.0
    last_validation: str = ""
    time_since_validation_seconds: float = 0.0
    molt_phase: str = "stable"
    creative_value: float = 0.5
    kappa_delta: float = 0.5


@dataclass
class AgentHealthWindow:
    """Rolling window of telemetry for one agent."""
    agent_id: str
    history: List[Dict[str, Any]] = field(default_factory=list)
    alert_level: str = "NORMAL"  # NORMAL, WATCH, WARNING, CRITICAL
    last_action: str = ""
    last_action_time: str = ""

    def push(self, tq: TelemetryQuantum):
        entry = {
            "timestamp": tq.timestamp or datetime.now(timezone.utc).isoformat(),
            "melt_pressure": tq.melt_pressure,
            "max_crystallization_rate": tq.max_crystallization_rate,
            "temperature": tq.temperature,
            "molt_count": tq.molt_count,
            "delta": tq.delta,
            "gamma": tq.gamma,
            "capability": tq.capability,
            "tau": tq.tau,
        }
        self.history.append(entry)
        if len(self.history) > HISTORY_WINDOW:
            self.history = self.history[-HISTORY_WINDOW:]

    def trend(self, field: str, window: int = 5) -> float:
        """Slope of field over last N samples. Positive = worsening."""
        if len(self.history) < 2:
            return 0.0
        pts = self.history[-window:]
        xs = list(range(len(pts)))
        ys = [p[field] for p in pts]
        n = len(pts)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den = sum((x - mean_x) ** 2 for x in xs)
        return num / den if den else 0.0

    def latest(self, field: str) -> Any:
        return self.history[-1].get(field) if self.history else None


# ---------------------------------------------------------------------------
# CNS helpers
# ---------------------------------------------------------------------------

def _write_packet(packet: dict, filename: str) -> str:
    """Atomic write to outbox."""
    outbox = Path(OUTBOX_PATH)
    outbox.mkdir(parents=True, exist_ok=True)
    tmp = outbox / f".{filename}.tmp"
    final = outbox / filename
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2)
    os.replace(str(tmp), str(final))
    return str(final)


def emit_response(target_id: str, intent: str, payload: dict, priority: str = "NORMAL") -> str:
    """Emit a USCP-v3 response packet."""
    pkt = {
        "header": {
            "origin_id": "melt-pressure-monitor",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "priority": priority,
            "correlation_id": datetime.now(timezone.utc).isoformat(),
            "destination_id": target_id,
        },
        "body": {
            "intent": intent,
            "payload": payload,
        },
        "signature": {
            "type": "USCP-v3",
            "version": "3.0",
            "extensions": ["melt-pressure-monitor"],
        },
    }
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    return _write_packet(pkt, f"melt_pressure_monitor_{target_id}_{ts}_001.json")


# ---------------------------------------------------------------------------
# Threshold evaluation
# ---------------------------------------------------------------------------

def evaluate_alert(tq: TelemetryQuantum, window: AgentHealthWindow) -> Dict[str, Any]:
    """Return alert dict if threshold breached, else empty dict."""
    level = "NORMAL"
    rules = []
    actions = []

    # MOLT-1: P_melt > max crystallization rate
    if tq.melt_pressure > tq.max_crystallization_rate:
        level = "WARNING"
        rules.append("MOLT-1")
        actions.append("VALIDATE")

    # CRITICAL: P_melt > 1.5 * max crystallization rate
    if tq.melt_pressure > 1.5 * tq.max_crystallization_rate:
        level = "CRITICAL"
        rules.append("MELT-PRESSURE-CRITICAL")
        actions.append("COOL_DOWN")
        actions.append("THROTTLE")

    # MOLT cascade: molt_count >= 4 and capability degraded
    if tq.molt_count >= 4 and tq.capability < 0.5:
        level = "CRITICAL"
        rules.append("MOLT-CASCADE")
        actions.append("MOLT")

    # Thermal overheating
    if tq.temperature > 5.0:
        level = _max_level(level, "WARNING")
        rules.append("THERMAL")
        actions.append("COOL_DOWN")

    # Frozen (delta == 0)
    if tq.delta == 0.0:
        level = "CRITICAL"
        rules.append("FROZEN")
        actions.append("THROTTLE")

    # Stale knowledge: high gamma but old validation
    if tq.gamma > 0.7 and tq.time_since_validation_seconds > MAX_STALENESS_SECONDS:
        level = _max_level(level, "WARNING")
        rules.append("STALE-KNOWLEDGE")
        actions.append("VALIDATE")

    # Trend: melt pressure rising
    melt_trend = window.trend("melt_pressure", window=5)
    if melt_trend > 0.01 and tq.melt_pressure > 0.3:
        level = _max_level(level, "WATCH")
        rules.append("MELT-TREND-RISING")

    # Trend: temperature rising faster than expected
    temp_trend = window.trend("temperature", window=5)
    if temp_trend > 0.1 and tq.temperature > tq.temperature_task * 2.0:
        level = _max_level(level, "WARNING")
        rules.append("THERMAL-TREND")

    if not rules:
        return {}

    return {
        "level": level,
        "rules": rules,
        "actions": list(set(actions)),
        "agent_id": tq.agent_id,
        "melt_pressure": tq.melt_pressure,
        "max_crystallization_rate": tq.max_crystallization_rate,
        "molt_count": tq.molt_count,
        "temperature": tq.temperature,
        "delta": tq.delta,
        "capability": tq.capability,
        "trend": {
            "melt_pressure": window.trend("melt_pressure"),
            "temperature": window.trend("temperature"),
        },
    }


# ---------------------------------------------------------------------------
# Monitor core
# ---------------------------------------------------------------------------

class MeltPressureMonitor:
    """Active watch dog for fleet melt pressure."""

    def __init__(self, poll_interval: int = POLL_INTERVAL):
        self.poll_interval = poll_interval
        self.windows: Dict[str, AgentHealthWindow] = {}
        self.running = False
        self.state = self._load_state()
        self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler(),
            ],
        )
        self.log = logging.getLogger("melt_pressure_monitor")

    def _load_state(self) -> Dict:
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"windows": {}, "last_run": ""}

    def _save_state(self):
        self.state["windows"] = {
            k: {
                "agent_id": v.agent_id,
                "history": v.history[-10:],
                "alert_level": v.alert_level,
                "last_action": v.last_action,
                "last_action_time": v.last_action_time,
            }
            for k, v in self.windows.items()
        }
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def ingest_telemetry(self, tq: TelemetryQuantum):
        """Feed a new telemetry snapshot."""
        aid = tq.agent_id
        if aid not in self.windows:
            self.windows[aid] = AgentHealthWindow(agent_id=aid)
        self.windows[aid].push(tq)
        alert = evaluate_alert(tq, self.windows[aid])
        if alert:
            self._handle_alert(alert, tq)
        self._save_state()

    def _handle_alert(self, alert: Dict, tq: TelemetryQuantum):
        aid = alert["agent_id"]
        win = self.windows[aid]
        level = alert["level"]
        rules = alert["rules"]
        actions = alert["actions"]

        # Avoid spamming same action within cooldown
        cooldown_key = f"{aid}:{','.join(actions)}"
        now = datetime.now(timezone.utc).isoformat()
        if win.last_action == cooldown_key:
            last = datetime.fromisoformat(win.last_action_time)
            if (datetime.now(timezone.utc) - last).total_seconds() < 60:
                return  # cooldown active

        win.alert_level = level
        win.last_action = cooldown_key
        win.last_action_time = now

        # Log
        self.log.warning(
            f"ALERT {level} | {aid} | rules={rules} | "
            f"P={alert['melt_pressure']:.4f} max={alert['max_crystallization_rate']:.4f} "
            f"T={alert['temperature']:.2f} molt={alert['molt_count']}"
        )

        # Emit CNS response
        priority_map = {"NORMAL": "NORMAL", "WATCH": "LOW", "WARNING": "MEDIUM", "CRITICAL": "CRITICAL"}
        payload = {
            "type": "melt_pressure_alert",
            "alert_level": level,
            "rules": rules,
            "recommended_actions": actions,
            "telemetry": asdict(tq),
            "trend": alert["trend"],
        }
        emit_response(aid, "MELT_PRESSURE_ALERT", payload, priority=priority_map.get(level, "MEDIUM"))

    def run_once(self):
        """Single polling cycle — read CNS inbox for telemetry packets."""
        try:
            files = sorted(
                [f for f in os.listdir(INBOX_PATH) if f.endswith(".json")],
                reverse=True,
            )
        except FileNotFoundError:
            self.log.error(f"Inbox not found: {INBOX_PATH}")
            return

        for fname in files:
            path = os.path.join(INBOX_PATH, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    packet = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            # Only process telemetry packets
            body = packet.get("body", {})
            intent = body.get("intent", "")
            if intent not in ("CNS_PULSE_STATUS", "TELEMETRY", "SENSORY_DATA"):
                continue

            payload = body.get("payload", {})
            ge = payload.get("gamma_eta", {})
            per_agent = ge.get("per_agent", {})
            if not per_agent:
                continue

            thermal = payload.get("thermal", {})
            melt = payload.get("melt", {})
            molt = payload.get("molt", {})
            uncertainty = payload.get("uncertainty", {})

            for agent_id, data in per_agent.items():
                if not isinstance(data, dict):
                    continue
                tq = TelemetryQuantum(
                    agent_id=agent_id,
                    gamma=data.get("gamma", 0.5),
                    eta=data.get("eta", 0.1),
                    delta=data.get("delta", 0.2),
                    temperature=thermal.get("temperature", 1.0),
                    semantic_distance=payload.get("creative", {}).get("semantic_distance", 0.5),
                    melt_pressure=melt.get("melt_pressure", 0.0),
                    max_crystallization_rate=melt.get("max_crystallization_rate", 0.0),
                    deterministic=melt.get("deterministic", False),
                    molt_count=molt.get("molt_count", 0),
                    capability=melt.get("capability", 1.0),
                    tau=uncertainty.get("tau", 0.5),
                    timestamp=packet.get("header", {}).get("timestamp", ""),
                    is_dreaming=thermal.get("is_dreaming", False),
                    temperature_idle=thermal.get("temperature_idle", 1.5),
                    temperature_task=thermal.get("temperature_task", 1.0),
                    last_validation=melt.get("last_validation", ""),
                    time_since_validation_seconds=melt.get("time_since_validation_seconds", 0.0),
                    molt_phase=melt.get("molt_phase", "stable"),
                    creative_value=payload.get("creative", {}).get("creative_value", 0.5),
                    kappa_delta=payload.get("creative", {}).get("kappa_delta", 0.5),
                )
                self.ingest_telemetry(tq)

    def start(self):
        """Run continuous loop until interrupted."""
        self.running = True
        self.log.info("Melt Pressure Monitor started")
        while self.running:
            try:
                self.run_once()
            except Exception:
                self.log.exception("Poll cycle failed")
            time.sleep(self.poll_interval)

    def stop(self):
        self.running = False
        self.log.info("Melt Pressure Monitor stopped")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    mon = MeltPressureMonitor()
    def _sig_handler(sig, frame):
        mon.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)
    mon.start()


if __name__ == "__main__":
    main()
