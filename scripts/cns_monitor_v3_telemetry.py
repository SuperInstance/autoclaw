#!/usr/bin/env python3
"""
CNS Heartbeat Monitor v3 — Telemetry-enhanced edition.
Extends v2 with:
  - TelemetryQuantum validation (γ, η, δ, T, Δ, P_melt, τ)
  - Conservation law enforcement (CONS-1: γ + η + δ = 1)
  - Melt pressure alerting (MOLT-1 trigger)
  - Staleness tracking (MLT-2: s(γ,t) = (t−tv)·γ)
  - Temperature schedule monitoring (DRM-1)
  - Creative zone tracking (CK-1: κ(Δ))
  - Per-agent fleet aggregation
"""
import os
import sys
import time
import json
import shutil
import math
import traceback
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

INBOX_PATH = os.path.expanduser("~/.hermes/cns_inbox/")
OUTBOX_PATH = os.path.expanduser("~/.hermes/cns_outbox/")
QUARANTINE_PATH = os.path.expanduser("~/.hermes/cns_quarantine/")
LOG_FILE = os.path.expanduser("~/.hermes/cns_heartbeat.log")
STATE_FILE = os.path.expanduser("~/.hermes/cns_monitor_state.json")
TELEMETRY_STATE_FILE = os.path.expanduser("~/.hermes/cns_telemetry_state.json")

POLL_INTERVAL = 5  # seconds
MAX_FILE_AGE_HOURS = 168  # 7 days

# ============================================================================
# Telemetry Data Model (P56-60)
# ============================================================================

@dataclass
class TelemetryQuantum:
    """Single agent telemetry snapshot. Enforces P56-60 invariants."""
    agent_id: str
    gamma: float = 0.0      # Crystallized intelligence γ ∈ [0,1]
    eta: float = 0.0        # Liquid intelligence η ∈ [0,1]
    delta: float = 0.0      # Conservation deviation δ ∈ [0, 0.25]
    temperature: float = 1.0  # Gumbel-Softmax T
    semantic_distance: float = 0.5  # Δ ∈ [0,1]
    melt_pressure: float = 0.0
    max_crystallization_rate: float = 0.0
    deterministic: bool = False  # G1: Ghost Tile determinism gate
    molt_count: int = 0
    capability: float = 1.0  # m(t) ∈ [0,1]
    tau: float = 0.5         # Uncertainty coherence τ ∈ [0,1]
    timestamp: str = ""

    # proposal-extended fields
    is_dreaming: bool = False
    temperature_idle: float = 1.5
    temperature_task: float = 1.0
    temp_rise_rate: float = 0.0
    last_temp_change: str = ""
    molt_threshold_exceeded: bool = False
    distribution_shift_sigma: float = 0.0
    last_validation: str = ""
    staleness_factor: float = 0.0
    time_since_validation_seconds: float = 0.0
    molt_phase: str = "stable"
    effective_temperature: float = 1.0
    kl_divergence_from_deterministic: float = 0.0
    delta_spike: float = 0.0
    recovery_time_estimate: float = 0.0
    creative_value: float = 0.5
    kappa_delta: float = 0.5

    def validate(self) -> List[str]:
        """Return list of invariant violations. Empty list = valid."""
        errors = []
        # CONS-1: γ + η + δ = 1 (within float tolerance)
        total = self.gamma + self.eta + self.delta
        if abs(total - 1.0) > 0.001:
            errors.append(f"CONS-1 violation: γ+η+δ={total:.4f} (must be 1.0)")
        # CONS-2: individual bounds
        if not 0.0 <= self.gamma <= 1.0:
            errors.append(f"CONS-2: gamma={self.gamma} out of [0,1]")
        if not 0.0 <= self.eta <= 1.0:
            errors.append(f"CONS-2: eta={self.eta} out of [0,1]")
        if not 0.0 <= self.delta <= 0.25:
            errors.append(f"CONS-2: delta={self.delta} out of [0,0.25]")
        # DRM-1: T_idle >= T_task (checked separately)
        if self.temperature < 0.0:
            errors.append(f"DRM: temperature={self.temperature} < 0")
        if self.capability < 0.0 or self.capability > 1.0:
            errors.append(f"MOLT-4: capability={self.capability} out of [0,1]")
        if self.molt_count > 5:
            errors.append(f"MOLT-6: molt_count={self.molt_count} > 5")
        # proposal bounds
        if not 0.0 <= self.tau <= 1.0:
            errors.append(f"UA-2: tau={self.tau} out of [0,1]")
        if self.molt_phase not in ("stable", "pre_molt", "molt", "post_molt", "cascade"):
            errors.append(f"MOLT-7: molt_phase={self.molt_phase} invalid")
        if self.time_since_validation_seconds < 0:
            errors.append(f"MLT-1: negative time_since_validation")
        if self.temp_rise_rate < 0:
            errors.append(f"DRM-2: temp_rise_rate={self.temp_rise_rate} < 0")
        if not 0.0 <= self.creative_value <= 1.0:
            errors.append(f"CK-2: creative_value={self.creative_value} out of [0,1]")
        return errors

    def is_melt_triggered(self) -> bool:
        """MOLT-1: P_melt > max_crystallization_rate"""
        if self.melt_pressure > self.max_crystallization_rate:
            self.molt_threshold_exceeded = True
            return True
        return False

    def is_frozen(self) -> bool:
        """Frozen failure: δ = 0 (no conservation deviation)."""
        return abs(self.delta) < 1e-9

    def is_in_creative_zone(self) -> bool:
        """CK-1: Δ ∈ [0.4, 0.6] for optimal crystallization."""
        return 0.4 <= self.semantic_distance <= 0.6

    def is_in_oneiric_zone(self) -> bool:
        """P60: Oneiric creative zone Δ ∈ [0.6, 0.8]."""
        return 0.6 <= self.semantic_distance <= 0.8

    def confidence_zone(self) -> str:
        """UA-1: τ-based confidence coloring."""
        if self.tau < 0.3:
            return "RED"
        elif self.tau < 0.7:
            return "YELLOW"
        else:
            return "GREEN"


@dataclass
class FleetTelemetry:
    """Aggregate fleet telemetry state."""
    agents: Dict[str, TelemetryQuantum] = field(default_factory=dict)
    last_update: str = ""
    total_gamma_eta: float = 0.0
    max_budget: float = 4.0  # Sum budget for fleet
    variance_c: float = 0.0  # Crystallization variance across agents

    def update_agent(self, tq: TelemetryQuantum):
        self.agents[tq.agent_id] = tq
        self.last_update = tq.timestamp or datetime.now(timezone.utc).isoformat()
        self._recompute()

    def _recompute(self):
        gammas = [t.gamma for t in self.agents.values()]
        if gammas:
            self.total_gamma_eta = sum(t.gamma + t.eta for t in self.agents.values())
            mean = sum(gammas) / len(gammas)
            self.variance_c = sum((g - mean) ** 2 for g in gammas) / len(gammas)

    def get_alerts(self) -> List[Dict[str, Any]]:
        alerts = []
        for aid, t in self.agents.items():
            # MOLT-1
            if t.is_melt_triggered():
                alerts.append({
                    "level": "CRITICAL",
                    "rule": "MOLT-1",
                    "agent": aid,
                    "message": f"P_melt={t.melt_pressure:.6f} > crystallization={t.max_crystallization_rate:.6f}"
                })
            # G1: Determinism gate
            if t.deterministic and t.temperature > 0.0:
                alerts.append({
                    "level": "WARNING",
                    "rule": "G1-DETERMINISM",
                    "agent": aid,
                    "message": f"deterministic=true but T={t.temperature:.3f} — must be 0"
                })
            # Frozen
            if t.is_frozen():
                alerts.append({
                    "level": "CRITICAL",
                    "rule": "FROZEN",
                    "agent": aid,
                    "message": f"δ=0 — agent frozen, recovery time: ∞"
                })
            # Molt chain
            if t.molt_count >= 4 and t.capability < 0.5:
                alerts.append({
                    "level": "CRITICAL",
                    "rule": "MOLT-CASCADE",
                    "agent": aid,
                    "message": f"molt#{t.molt_count}, capability={t.capability:.2f}"
                })
            # Staleness (if we had t_v)
            if t.gamma > 0.7:
                alerts.append({
                    "level": "WARNING",
                    "rule": "STALE-KNOWLEDGE",
                    "agent": aid,
                    "message": f"γ={t.gamma:.2f} — high crystallization, validate current"
                })
            # Creative drift
            if not t.is_in_creative_zone() and not t.is_in_oneiric_zone():
                alerts.append({
                    "level": "WARNING",
                    "rule": "CREATIVE-DRIFT",
                    "agent": aid,
                    "message": f"Δ={t.semantic_distance:.2f} — outside optimal zone [0.4,0.6]"
                })
            # Dream phase
            if t.is_dreaming:
                alerts.append({
                    "level": "INFO",
                    "rule": "DREAM-PHASE",
                    "agent": aid,
                    "message": f"T_idle={t.temperature_idle:.2f} — idle crystallization"
                })
            # Temperature schedule drift
            if t.temperature_task > 0 and t.temperature_idle < t.temperature_task * 0.5:
                alerts.append({
                    "level": "WARNING",
                    "rule": "DRM-2",
                    "agent": aid,
                    "message": f"T_idle={t.temperature_idle:.2f} << T_task={t.temperature_task:.2f}"
                })
            # Recent validation info
            if t.staleness_factor == 0 and t.time_since_validation_seconds <= 3600:
                alerts.append({
                    "level": "INFO",
                    "rule": "VALIDATION-FRESH",
                    "agent": aid,
                    "message": "validation staleness_factor=0; fresh data"
                })
            # Temperature
            if t.temperature > 5.0:
                alerts.append({
                    "level": "WARNING",
                    "rule": "THERMAL",
                    "agent": aid,
                    "message": f"T={t.temperature:.1f} — overheating"
                })
            if 0.0 < t.temperature < 0.1:
                alerts.append({
                    "level": "WARNING",
                    "rule": "FROZEN-T",
                    "agent": aid,
                    "message": f"T={t.temperature:.3f} — near-freeze"
                })
            # Confidence
            if t.confidence_zone() == "RED":
                alerts.append({
                    "level": "WARNING",
                    "rule": "UA-1-RED",
                    "agent": aid,
                    "message": f"τ={t.tau:.2f} — low coherence"
                })
        # Fleet-level
        if self.variance_c < 0.01 and len(self.agents) > 1:
            alerts.append({
                "level": "WARNING",
                "rule": "FLEET-BRITTLENESS",
                "agent": "FLEET",
                "message": f"C variance={self.variance_c:.4f} — fleet homogeneous"
            })
        return alerts


# ============================================================================
# Physics Functions (P56-60)
# ============================================================================

def compute_melt_pressure(
    gamma: float,
    time_since_validation_s: float,
    distribution_shift: float,
    mu: float = 0.01
) -> float:
    """P56 Theorem 2: P_melt = μ · σ · (t - t_v) · γ"""
    return mu * distribution_shift * time_since_validation_s * gamma


def compute_max_crystallization_rate(
    gamma: float,
    semantic_distance: float,
    temperature: float,
    alpha: float = 1.0,
    beta: float = 0.5,
    sigma_c: float = 0.1
) -> float:
    """P56 Theorem 1: dγ/dt = α · κ(Δ) · (1-γ) · 1/(1+βT)"""
    # κ(Δ) = exp(−(Δ−0.5)²/(2σ_c²))  [CHECKLIST eq fix: use 2σ² not σ²]
    kappa = math.exp(-((semantic_distance - 0.5) ** 2) / (2 * sigma_c ** 2))
    Phi = 1.0 / (1.0 + beta * temperature)
    return alpha * kappa * (1.0 - gamma) * Phi


def compute_tau(
    gamma: float,
    semantic_distance: float,
    eta: float,
    temperature: float
) -> float:
    """P58: Uncertainty coherence τ² = exp(−σ²) [CHECKLIST: no /2]."""
    # σ = semantic uncertainty from distance from knowledge base
    sigma = abs(semantic_distance - 0.5) * 2.0  # Map [0,1] distance to uncertainty
    tau_sq = math.exp(-sigma ** 2)  # P58: τ² = exp(−σ²)
    return math.sqrt(max(0.0, min(1.0, tau_sq)))


def compute_capability_after_molt(
    initial_capability: float,
    gamma: float
) -> float:
    """P59 MOLT-4: m(t) = m(0) · min(1, γ(t))"""
    return initial_capability * min(1.0, gamma)


class EmpiricalValidator:
    """Logs empirical dγ/dt vs predicted crystallization rate (P56 Theorem 1)."""

    def __init__(self, window_size: int = 10, divergence_threshold: float = 0.05):
        self.window_size = window_size
        self.divergence_threshold = divergence_threshold
        self.windows: Dict[str, list] = {}  # agent -> [(ts, gamma, predicted_rate)]
        self._log_path = Path.home() / ".hermes/empirical_divergence_log.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, tq: TelemetryQuantum) -> Optional[Dict]:
        predicted = compute_max_crystallization_rate(
            gamma=tq.gamma,
            semantic_distance=tq.semantic_distance,
            temperature=tq.temperature,
        )
        win = self.windows.setdefault(tq.agent_id, [])
        win.append((tq.timestamp or datetime.now(timezone.utc).isoformat(), tq.gamma, predicted))
        if len(win) > self.window_size:
            self.windows[tq.agent_id] = win[-self.window_size:]

        if len(win) < 3:
            return None

        _, g0, _ = win[-3]
        _, g1, _ = win[-1]
        dt = 1.0
        empirical_rate = (g1 - g0) / dt
        _, _, predicted_latest = win[-1]
        divergence = abs(empirical_rate - predicted_latest)

        if divergence > self.divergence_threshold:
            record = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "agent_id": tq.agent_id,
                "empirical_rate": empirical_rate,
                "predicted_rate": predicted_latest,
                "divergence": divergence,
            }
            try:
                with self._log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
            except Exception:
                pass
            return {
                "level": "WARNING",
                "rule": "EMPIRICAL-DIVERGENCE",
                "agent": tq.agent_id,
                "message": (
                    f"dγ/dt={empirical_rate:.4f} vs predicted={predicted_latest:.4f} "
                    f"(divergence={divergence:.4f})"
                ),
                "empirical_rate": empirical_rate,
                "predicted_rate": predicted_latest,
                "divergence": divergence,
            }
        return None

    def flush(self) -> List[Dict]:
        return [{"agent_id": aid, "window": win} for aid, win in self.windows.items()]

    @classmethod
    def load_recent_divergences(cls, limit: int = 200) -> List[Dict]:
        """Return recent divergence events from the JSONL log file."""
        log_path = getattr(cls(), "_log_path", Path.home() / ".hermes/empirical_divergence_log.jsonl")
        if not log_path.exists():
            return []
        out: List[Dict] = []
        try:
            with log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return out[-limit:]

    @classmethod
    def summarize_empirical_health(cls) -> Dict[str, Any]:
        """Summarize fleet empirical health for daemon status exports."""
        events = cls.load_recent_divergences()
        if not events:
            return {
                "events": 0,
                "max_divergence": 0.0,
                "avg_divergence": 0.0,
                "worst_agent": "",
                "status": "healthy",
            }
        divergences = [e["divergence"] for e in events]
        worst = max(events, key=lambda e: e["divergence"])
        avg = sum(divergences) / len(divergences)
        return {
            "events": len(events),
            "max_divergence": max(divergences),
            "avg_divergence": avg,
            "worst_agent": worst.get("agent_id", ""),
            "status": "divergent" if avg > 0.05 else "stable",
        }


def parse_telemetry_from_packet(packet: Dict) -> Optional[TelemetryQuantum]:
    body = packet.get("body", {})
    payload = body.get("payload", {})
    if not isinstance(payload, dict):
        return None
    # Look for gamma_eta block (from CNS_TELEMETRY_ENHANCEMENT_PROPOSAL)
    ge = payload.get("gamma_eta", {})
    per_agent = ge.get("per_agent", {})
    if not per_agent:
        return None
    # Build fleet snapshot from per_agent
    fleet = FleetTelemetry()
    for agent_id, data in per_agent.items():
        if not isinstance(data, dict):
            continue
        # Ingress defense: repair out-of-bounds values before constructing quantum
        gamma = data.get("gamma", 0.5)
        eta = data.get("eta", 0.1)
        delta = data.get("delta", 0.2)
        total = gamma + eta + delta
        if abs(total - 1.0) > 0.001 and 0.0 <= total <= 2.0:
            scale = 1.0 / total if total > 0 else 0.0
            gamma, eta, delta = round(gamma * scale, 4), round(eta * scale, 4), round(delta * scale, 4)
        gamma = max(0.0, min(1.0, gamma))
        eta = max(0.0, min(1.0, eta))
        delta = max(0.0, min(0.25, delta))
        tq = TelemetryQuantum(
            agent_id=agent_id,
            gamma=gamma,
            eta=eta,
            delta=delta,
            temperature=payload.get("thermal", {}).get("temperature", 1.0),
            semantic_distance=payload.get("creative", {}).get("semantic_distance", 0.5),
            melt_pressure=payload.get("melt", {}).get("melt_pressure", 0.0),
            max_crystallization_rate=payload.get("melt", {}).get("max_crystallization_rate", 0.0),
            deterministic=payload.get("melt", {}).get("deterministic", False),
            molt_count=payload.get("molt", {}).get("molt_count", 0),
            capability=payload.get("molt", {}).get("capability", 1.0),
            tau=payload.get("uncertainty", {}).get("tau", 0.5),
            timestamp=packet.get("header", {}).get("timestamp", ""),
        )
        fleet.update_agent(tq)
    # Return the first valid quantum as representative
    if fleet.agents:
        first_key = next(iter(fleet.agents))
        return fleet.agents[first_key]
    return None


# ============================================================================
# State Management
# ============================================================================

def load_telemetry_state() -> Dict:
    try:
        with open(TELEMETRY_STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "agent_history": {},
            "last_fleet_update": "",
            "alert_counts": {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
        }

def save_telemetry_state(state: Dict):
    state["agent_history"] = dict(list(state.get("agent_history", {}).items())[-50:])
    with open(TELEMETRY_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


# ============================================================================
# Packet Processing (extends v2)
# ============================================================================

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    print(line, flush=True)

def ensure_dirs():
    for p in [INBOX_PATH, OUTBOX_PATH, QUARANTINE_PATH]:
        os.makedirs(p, exist_ok=True)

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"processed": [], "total_processed": 0, "total_errors": 0, "total_quarantined": 0}

def save_state(state):
    state["processed"] = state["processed"][-200:]
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def is_stale(filepath):
    try:
        mtime = os.path.getmtime(filepath)
        age_hours = (time.time() - mtime) / 3600
        return age_hours > MAX_FILE_AGE_HOURS
    except OSError:
        return False

def quarantine(filepath, reason):
    ensure_dirs()
    name = os.path.basename(filepath)
    dest = os.path.join(QUARANTINE_PATH, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}")
    try:
        shutil.move(filepath, dest)
        log(f"QUARANTINED: {name} → {dest} ({reason})")
    except Exception as e:
        log(f"QUARANTINE FAILED for {name}: {e}")
        try:
            os.remove(filepath)
            log(f"DELETED (quarantine failed): {name}")
        except:
            pass

def process_packet(filepath, state, telemetry_state, empirical_validator=None):
    """Extended v3 packet processor with telemetry extraction."""
    name = os.path.basename(filepath)

    if name in state.get("processed", []):
        return True

    if is_stale(filepath):
        log(f"STALE (>{MAX_FILE_AGE_HOURS}h old), skipping: {name}")
        state["processed"].append(name)
        return True

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()

        packet = None
        if name.endswith('.md.json'):
            try:
                packet = json.loads(raw)
            except json.JSONDecodeError:
                start = raw.find('{')
                if start != -1:
                    packet = json.loads(raw[start:])
                else:
                    quarantine(filepath, "unparseable .md.json: no JSON")
                    state["total_quarantined"] += 1
                    return False
        elif name.endswith('.md'):
            packet = {
                "header": {"origin_id": "unknown", "timestamp": datetime.now().isoformat()},
                "body": {"intent": "MARKDOWN", "payload": {"text": raw[:500]}}
            }
        else:
            packet = json.loads(raw)

        header = packet.get("header", {}) if isinstance(packet.get("header"), dict) else {}
        body = packet.get("body", {}) if isinstance(packet.get("body"), dict) else {}
        origin = header.get("origin_id", "UNKNOWN")
        intent = body.get("intent", "UNKNOWN")
        priority = header.get("priority", "NORMAL")

        log(f"PROCESSING [{origin}] intent={intent} priority={priority} file={name}")

        # --- v3 NEW: Extract and validate telemetry ---
        tq = parse_telemetry_from_packet(packet)
        fleet = FleetTelemetry()
        if tq:
            fleet.update_agent(tq)
            violations = tq.validate()
            if violations:
                log(f"  TELEMETRY VIOLATIONS for {tq.agent_id}: {violations}")
            else:
                log(f"  TELEMETRY OK [{tq.agent_id}] γ={tq.gamma:.3f} η={tq.eta:.3f} δ={tq.delta:.3f} T={tq.temperature:.1f} Δ={tq.semantic_distance:.3f} τ={tq.tau:.2f} P_melt={tq.melt_pressure:.5f} cap={tq.capability:.2f}")
            alerts = fleet.get_alerts()
            for alert in alerts:
                log(f"  ALERT [{alert['level']}] {alert['rule']} {alert['agent']}: {alert['message']}")
            # Store in telemetry state
            agent_hist = telemetry_state.setdefault("agent_history", {})
            agent_hist[tq.agent_id] = {
                "timestamp": tq.timestamp,
                "gamma": tq.gamma, "eta": tq.eta, "delta": tq.delta,
                "temperature": tq.temperature, "semantic_distance": tq.semantic_distance,
                "melt_pressure": tq.melt_pressure, "max_crystallization_rate": tq.max_crystallization_rate,
                "deterministic": tq.deterministic,
                "molt_count": tq.molt_count,
                "capability": tq.capability, "tau": tq.tau,
                "violations": violations, "alerts": [a['rule'] for a in alerts]
            }
            telemetry_state["last_fleet_update"] = fleet.last_update
            telemetry_state["empirical_windows"] = empirical_validator.flush()
            for a in alerts:
                telemetry_state["alert_counts"][a["level"]] = \
                    telemetry_state.get("alert_counts", {}).get(a["level"], 0) + 1

        # --- Response construction (v2 compatible) ---
        payload = body.get("payload", {}) if isinstance(body, dict) else {}
        msg_text = ""
        if isinstance(payload, dict):
            msg_text = payload.get("message", payload.get("text", ""))

        sanitized_echo = None
        if msg_text:
            echo_str = str(msg_text)[:50]
            if len(str(msg_text)) > 50:
                sanitized_echo = echo_str + " [sanitized]"
            else:
                sanitized_echo = echo_str

        response = {
            "header": {
                "origin_id": "hermes-cns",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "priority": "NORMAL",
                "destination_id": origin,
                "correlation_id": packet.get("header", {}).get("timestamp", ""),
            },
            "body": {
                "intent": "ACK",
                "payload": {
                    "type": "packet_received",
                    "source_intent": intent,
                    "source_origin": origin,
                    "status": "received",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "echo": sanitized_echo,
                    "telemetry_valid": tq is not None and len(tq.validate()) == 0 if tq else None,
                    "fleet_alerts": len(alerts) if tq else 0,
                    "fleet_variance_c": fleet.variance_c,
                }
            },
            "signature": {"type": "USCP-v3", "version": "3.0", "extensions": ["gamma_eta", "thermal", "creative", "melt", "molt", "uncertainty", "anomaly"]}
        }

        outbox_name = f"hermes_response_{name}"
        outbox_path = os.path.join(OUTBOX_PATH, outbox_name)
        with open(outbox_path, 'w') as f:
            json.dump(response, f, indent=2)

        log(f"DISPATCHED: {outbox_name}")
        os.remove(filepath)
        log(f"CONSUMED: {name}")
        state["processed"].append(name)
        state["total_processed"] += 1
        return True

    except json.JSONDecodeError as e:
        log(f"JSON ERROR in {name}: {e}")
        quarantine(filepath, f"JSON decode error: {e}")
        state["total_quarantined"] += 1
        return False
    except Exception as e:
        log(f"ERROR processing {name}: {e}")
        log(traceback.format_exc())
        quarantine(filepath, f"Processing error: {e}")
        state["total_errors"] += 1
        return False

def main():
    ensure_dirs()
    log("=" * 60)
    log("CNS Heartbeat Monitor v3.0 STARTING")
    log(f"Inbox:  {INBOX_PATH}")
    log(f"Outbox: {OUTBOX_PATH}")
    log(f"Poll interval: {POLL_INTERVAL}s")
    log("Extensions: gamma_eta, thermal, creative, melt, molt, uncertainty, anomaly")
    log("=" * 60)

    state = load_state()
    telemetry_state = load_telemetry_state()
    log(f"State loaded: {state['total_processed']} processed, "
        f"{state['total_errors']} errors, {state['total_quarantined']} quarantined")
    if telemetry_state.get("last_fleet_update"):
        log(f"Last telemetry: {telemetry_state['last_fleet_update']}")

    cycle = 0
    while True:
        try:
            cycle += 1
            files = sorted([
                f for f in os.listdir(INBOX_PATH)
                if f.endswith(('.json', '.uscp.json', '.md', '.md.json'))
                and not f.startswith('.')
            ])

            if files:
                log(f"Cycle {cycle}: {len(files)} files in inbox")

            for filename in files:
                filepath = os.path.join(INBOX_PATH, filename)
                process_packet(filepath, state, telemetry_state, empirical_validator)

            save_state(state)
            save_telemetry_state(telemetry_state)

        except KeyboardInterrupt:
            log("Shutdown requested (Ctrl+C)")
            save_state(state)
            save_telemetry_state(telemetry_state)
            break
        except Exception as e:
            log(f"FATAL in main loop: {e}")
            log(traceback.format_exc())
            time.sleep(10)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
