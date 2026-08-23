# Autoclaw Integration Spec
## Hooking CNS v3 Telemetry into the Autoclaw Daemon

**Date:** 2026-08-22
**Source:** `/c/Users/casey/projects/autoclaw/`
**Target:** `autoclaw/crew/` and `autoclaw/cudaclaw_wizard.py`

---

## Current State

Autoclaw has a daemon (`crew/daemon.py`) that runs experiments via `crew/runner.py`. It tracks:
- GPU temperature and memory
- Experiment success/failure
- Git commits per experiment

**It does NOT track:** γ, η, δ, T (model temperature), Δ, P_melt, τ, capability

This is the integration point for CNS v3 telemetry.

---

## Integration Points

### 1. Daemon Heartbeat → CNS Pulse

**File:** `autoclaw/crew/daemon.py`
**Function:** The daemon already has a heartbeat thread. Add CNS packet emission.

**Insert after `self.heartbeat()` call in the main loop:**

```python
# In crew/daemon.py — add to imports
import json
from datetime import datetime, timezone

# Add CNS pulse emission
def _emit_cns_pulse(self):
    """Send γ, η, δ, T to CNS for fleet-wide tracking."""
    try:
        tq = self._current_telemetry()  # see #2 below
        packet = {
            "header": {
                "origin_id": "autoclaw-daemon",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "priority": "NORMAL",
                "destination_id": "hermes-cns",
            },
            "body": {
                "intent": "CNS_PULSE_STATUS",
                "payload": {
                    "type": "fleet_telemetry",
                    "gamma_eta": {
                        "per_agent": {
                            "autoclaw": {
                                "gamma": tq.gamma,
                                "eta": tq.eta,
                                "delta": tq.delta,
                            }
                        },
                        "fleet_sum": {
                            "total_gamma_eta": tq.gamma + tq.eta,
                            "utilization": (tq.gamma + tq.eta) / 4.0,
                        }
                    },
                    "thermal": {
                        "temperature": tq.temperature,
                        "temperature_task": tq.temperature_task,
                        "temperature_idle": max(tq.temperature, tq.temperature + 0.5),
                        "is_dreaming": False,
                    },
                    "creative": {
                        "semantic_distance": tq.semantic_distance,
                        "is_in_creative_zone": 0.4 <= tq.semantic_distance <= 0.6,
                        "is_in_oneiric_zone": 0.6 <= tq.semantic_distance <= 0.8,
                    },
                    "melt": {
                        "melt_pressure": tq.melt_pressure,
                        "max_crystallization_rate": tq.max_crystallization_rate,
                        "melt_threshold_exceeded": tq.is_melt_triggered(),
                    },
                    "molt": {
                        "molt_count": tq.molt_count,
                        "max_molt_chain": 5,
                        "capability": tq.capability,
                    },
                    "uncertainty": {
                        "tau": tq.tau,
                        "confidence_zone": tq.confidence_zone(),
                    }
                }
            },
            "signature": {
                "type": "USCP-v3",
                "version": "3.0",
                "extensions": ["gamma_eta", "thermal", "creative", "melt", "molt", "uncertainty"]
            }
        }
        inbox = os.path.expanduser("~/.hermes/cns_inbox/")
        fname = f"autoclaw_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        with open(os.path.join(inbox, fname), 'w') as f:
            json.dump(packet, f, indent=2)
```

### 2. Telemetry Source: `cudaclaw_wizard.py`

**File:** `autoclaw/cudaclaw_wizard.py`
**Role:** This is the largest file in autoclaw (33 KB). It already tracks GPU state, learning rate, loss. Add the P56-60 metrics.

**Add a `TelemetryQuantum` property to the `CudaclawWizard` class:**

```python
# At top of cudaclaw_wizard.py
from dataclasses import dataclass
import math

@dataclass
class CudaclawTelemetry:
    gamma: float = 0.5      # Start mid-crystallized
    eta: float = 0.25       # Some liquid intelligence
    delta: float = 0.25     # Max deviation (conservative start)
    temperature: float = 1.0
    semantic_distance: float = 0.5
    molt_count: int = 0
    capability: float = 1.0
    last_validation: str = ""

    def update_from_experiment(self, result):
        """P56: Update γ based on whether we're in creative zone."""
        if 0.4 <= self.semantic_distance <= 0.6:
            # In creative zone: γ crystallizes
            self.gamma = min(1.0, self.gamma + 0.01)
        elif self.semantic_distance > 0.8 or self.semantic_distance < 0.2:
            # Out of creative zone: γ decays, η rises
            self.gamma = max(0.0, self.gamma - 0.005)
        # Conservation: δ = 1 − (γ + η), η = (1−γ)² in ONE_PHASE
        eta_computed = (1 - self.gamma) ** 2
        self.delta = 1.0 - (self.gamma + eta_computed)
        self.eta = eta_computed
        # Clamp δ
        self.delta = max(0.0, min(0.25, self.delta))

    def compute_melt_pressure(self, time_since_validation_s: float, distribution_shift: float) -> float:
        mu = 0.01
        return mu * distribution_shift * time_since_validation_s * self.gamma

    def compute_max_crystallization_rate(self) -> float:
        sigma_c = 0.1
        alpha, beta = 1.0, 0.5
        kappa = math.exp(-((self.semantic_distance - 0.5)**2) / (2 * sigma_c**2))
        Phi = 1.0 / (1.0 + beta * self.temperature)
        return alpha * kappa * (1.0 - self.gamma) * Phi

    def check_molt_trigger(self) -> bool:
        return self.melt_pressure > self.max_crystallization_rate
```

**Add to `CudaclawWizard.__init__`:**
```python
self.telemetry = CudaclawTelemetry()
```

**Add to `ExperimentRunner.run_experiment()` after result is recorded:**
```python
# Update telemetry from experiment result
if result.success and result.metric_value is not None:
    # Use val_bpb as proxy for semantic distance (lower bpb = closer to KB)
    self.wizard.telemetry.semantic_distance = min(1.0, max(0.0, result.metric_value))
    self.wizard.telemetry.update_from_experiment(result)
    self.wizard.telemetry.last_validation = datetime.now(timezone.utc).isoformat()
```

### 3. Runner Temperature Tracking

**File:** `autoclaw/crew/runner.py`
**Current:** Tracks GPU temp, memory, wall-clock.
**Add:** Model temperature tracking.

```python
# Add to ExperimentRunner state
self.current_temperature = 1.0  # Starts in task mode
self.temperature_task = 1.0
self.temperature_idle = 2.0
self.last_task_end = None

# In run_experiment(), at start:
self.current_temperature = self.temperature_task

# At end of run_experiment():
self.last_task_end = datetime.now(timezone.utc)
```

---

## Validation: Checklist Runner

**File:** `~/.hermes/scripts/verification_checklist_runner.py` (just created)
**Usage:**
```bash
# Against a JSON snapshot
python3 ~/.hermes/scripts/verification_checklist_runner.py /path/to/snapshot.json

# Against live telemetry state
python3 ~/.hermes/scripts/verification_checklist_runner.py
```

**Add to cron (every 5 min):**
```json
{
  "schedule": "*/5 * * * *",
  "prompt": "Run verification_checklist_runner.py against ~/.hermes/cns_telemetry_state.json and report any FAIL rules to this channel.",
  "name": "Verification Checklist (CNS v3)",
  "no_agent": false
}
```

---

## Deployment Order

1. **Today:** Run `cns_monitor_v3_telemetry.py` in background alongside v2. Both can coexist.
2. **This week:** Add `_emit_cns_pulse()` to autoclaw daemon.
3. **Next:** Add `CudaclawTelemetry` to `cudaclaw_wizard.py`.
4. **Validate:** Run Checklist runner against live telemetry. All CONs must pass.

---

## Risk: Cold Start

The first telemetry reading will have default values (γ=0.5, η=0.25, δ=0.25). This is a valid starting point but will trigger CONS-1 warnings if other agents report different values. The fleet should expect a "warm-up" period of ~10 pulses before variance stabilizes.
