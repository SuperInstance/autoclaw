# CNS v3 Protocol Specification

**Status:** Canonical  
**Implements:** `SuperInstance/cns-echo@23308a0`, `autoclaw@3b381ba`  
**Audience:** Agents, operators, integrators  
**Normative:** `cns_echo/echo.py` is the reference parser. This doc describes the protocol it accepts.

---

## 1. Packet Topology

Every CNS packet is a JSON object with three mandatory top-level keys:

```json
{
  "header": { ... },
  "body": { ... },
  "signature": { ... }
}
```

### 1.1 `header`

| Field | Type | Required (v2) | Required (v3) | Notes |
|---|---|---|---|---|
| `origin_id` | string | yes | yes | Logical sender (agent, daemon, monitor) |
| `timestamp` | ISO 8601 | yes | yes | UTC preferred |
| `priority` | string | yes | yes | `NORMAL`, `HIGH`, `LOW` |
| `destination_id` | string | yes | yes | Logical recipient |
| `sequence_id` | string | **yes** | **no** | Legacy ordering token; v3 uses `correlation_id` instead |
| `correlation_id` | string | no | yes | Request/response correlation, retry idempotency |

### 1.2 `body`

| Field | Type | Required (v2) | Required (v3) | Notes |
|---|---|---|---|---|
| `intent` | string | yes | yes | Action verb (e.g. `CNS_PULSE_STATUS`) |
| `payload` | object | yes | yes | Intent-specific data |

### 1.3 `signature`

| Field | Type | Required (v2) | Required (v3) | Notes |
|---|---|---|---|---|
| `type` | string | yes | yes | Must be `USCP` or `USCP-v3` |
| `version` | string | yes | yes | `2.0` or `3.0` |
| `checksum` | string | yes | no | v3 skips checksum validation |
| `extensions` | string[] | no | yes | Declares which v3 payload blocks are present |

---

## 2. Intent Registry (non-exhaustive)

| Intent | v2 | v3 | Payload contract |
|---|---|---|---|
| `CNS_PULSE_STATUS` | yes | yes | `type`, `gamma_eta`, `thermal`, `creative`, `melt`, `molt`, `uncertainty`, `anomaly` |
| `MARKDOWN` | yes | yes | `text` |
| `REQUEST_REASONING` | yes | yes | task-specific |
| `SENSORY_DATA` | yes | yes | task-specific |
| `EXECUTE_PLAN` | yes | yes | task-specific |

New intents MAY be added without protocol bump; unknown intents MUST be passed through unchanged.

---

## 3. v3 Payload Blocks

A v3 packet MUST declare every block it uses inside `signature.extensions`.

### 3.1 `gamma_eta`

```json
{
  "gamma_eta": {
    "per_agent": {
      "<agent_id>": {
        "gamma": 0.0–1.0,
        "eta": 0.0–1.0,
        "delta": 0.0–0.25
      }
    },
    "fleet_sum": {
      "total_gamma_eta": 0.0–2.0,
      "utilization": 0.0–0.5
    }
  }
}
```

**Conservation law (CONS-1):** `γ + η + δ == 1.0` within ±0.001 tolerance.  
Repair strategy: proportional renormalization if `0 <= total <= 2.0`, otherwise hard reset to `γ=0.5, η=0.25, δ=0.25`.

### 3.2 `thermal`

```json
{
  "thermal": {
    "temperature": float,
    "temperature_task": float,
    "temperature_idle": float,
    "temp_rise_rate": float,
    "last_temp_change": "ISO 8601",
    "is_dreaming": boolean
  }
}
```

**DRM invariant:** `T_idle >= T_task`.  
**DRM invariant:** `T >= 0`.

### 3.3 `creative`

```json
{
  "creative": {
    "semantic_distance": 0.0–1.0,
    "creative_value": 0.0–1.0,
    "kappa_delta": 0.0–1.0,
    "crystallization_rate": float,
    "is_in_creative_zone": boolean,
    "is_in_oneiric_zone": boolean
  }
}
```

**P56 Theorem 1 (crystallization rate):**

```
dγ/dt = α · κ(Δ) · (1 − γ) / (1 + β · T)
κ(Δ) = exp(−(Δ − 0.5)² / (2 · σ_c²))
```

Default constants: `α=1.0, β=0.5, σ_c=0.1`.

### 3.4 `melt`

```json
{
  "melt": {
    "melt_pressure": float,
    "max_crystallization_rate": float,
    "melt_threshold_exceeded": boolean,
    "last_validation": "ISO 8601",
    "time_since_validation_seconds": float,
    "staleness_factor": float,
    "distribution_shift_sigma": float,
    "identity_hash": "sha256:<16-hex>",
    "deterministic": boolean
  }
}
```

**P56 Theorem 2 (melt pressure):**

```
P_melt = μ · σ · (t − t_v) · γ
```

Default `μ = 0.01`.  
**MOLT-1 trigger:** `P_melt > max_crystallization_rate`.

**G1-DETERMINISM:** `deterministic=true` implies `temperature == 0.0`.  
**G2 P03 Kan extension:** `identity_hash == sha256(role || model || backend)`.

### 3.5 `molt`

```json
{
  "molt": {
    "molt_count": integer,
    "max_molt_chain": 5,
    "capability": 0.0–1.0,
    "molt_phase": "stable" | "molting" | "recovering"
  }
}
```

**MOLT-4:** `capability = m(0) · min(1, γ(t))`.  
**MOLT-6:** `molt_count < 5` before forced reset.

### 3.6 `uncertainty`

```json
{
  "uncertainty": {
    "tau": 0.0–1.0,
    "effective_temperature": float,
    "confidence_zone": "GREEN" | "YELLOW" | "RED",
    "kl_divergence_from_deterministic": float
  }
}
```

**P58:** `τ² = exp(−σ²)` (no `/2`).  
`σ = |Δ − 0.5| · 2`.

### 3.7 `anomaly`

```json
{
  "anomaly": {
    "delta_spike": float,
    "recovery_time_estimate": float,
    "anomaly_spectrum_peaks": float[]
  }
}
```

**Melt pressure anomaly:** when `melt_pressure` exceeds `max_crystallization_rate`, `delta_spike` records the excess magnitude and `recovery_time_estimate` projects cool-down duration.

---

## 4. Version Negotiation

1. **v2 packet** (`signature.type == "USCP"` or `"USCP-v2"`; no `extensions`):
   - Require `sequence_id` and `checksum`.
   - Validate checksum (SHA256 of canonicalized packet).
   - Accept only `gamma_eta` block if present.

2. **v3 packet** (`signature.type == "USCP-v3"` and `signature.version == "3.0"`):
   - `sequence_id` and `checksum` are OPTIONAL and IGNORED if present.
   - `correlation_id` is REQUIRED for request/response flows.
   - `extensions` is REQUIRED and MUST enumerate every non-empty payload block.
   - All declared blocks MUST parse successfully or the packet is quarantined.

3. **Unknown version:** quarantine with `UNKNOWN_PROTOCOL` reason.

---

## 5. Invariant Enforcement

### 5.1 Egress (sender-side)

Implemented in `autoclaw/crew/daemon.py::_validate_telemetry()`:

| Rule | Action |
|---|---|
| CONS-1 violation | Renormalize proportionally (if salvageable) or hard reset |
| CONS-2 out-of-bounds | Clamp to `[lo, hi]` |
| DRM `temperature < 0` | Clamp to `0.0` |
| MOLT-4 `capability` out-of-bounds | Clamp to `[0, 1]` |

All repairs are logged as warnings in the CNS pulse.

### 5.2 Ingress (receiver-side)

Implemented in `cns_echo/echo.py` and `autoclaw/scripts/cns_monitor_v3_telemetry.py`:

- `sequence_id` / `checksum` skipped for v3.
- `gamma`, `eta`, `delta` renormalized if `0 <= total <= 2.0`.
- Individual bounds clamped: `γ∈[0,1]`, `η∈[0,1]`, `δ∈[0,0.25]`.
- `temperature` floor at `0.0`.
- Packets with irreparable violations are quarantined, not dropped silently.

### 5.3 Post-ingress (monitor-side)

`TelemetryQuantum.validate()` runs 13 rules:
- Original 11 from `VERIFICATION_CHECKLIST_P56-60.md`
- `G1-DETERMINISM`: `deterministic=true` ⇒ `temperature == 0.0`
- `G4-COMPOSITION`: equipment stacking algebra (untested list ⇒ WARNING)

---

## 6. Empirical Validation (P56 Theorem 1)

`EmpiricalValidator` (in `cns_monitor_v3_telemetry.py`) compares measured `dγ/dt` against predicted crystallization rate:

```
predicted = α · κ(Δ) · (1 − γ) / (1 + β · T)
empirical = (γ(t) − γ(t−3Δt)) / (3Δt)
divergence = |empirical − predicted|
```

Alert rule: `EMPIRICAL-DIVERGENCE` fires when `divergence > 0.05`.  
Windows are persisted in `telemetry_state["empirical_windows"]`.

---

## 7. Melt Pressure Monitoring

`MeltPressureMonitor` (`autoclaw/scripts/melt_pressure_monitor.py`) watches live CNS telemetry and emits:

| Rule | Condition | Level | Action |
|---|---|---|---|
| MOLT-1 | `P_melt > max_crystallization_rate` | CRITICAL | `MOLT` |
| MELT-PRESSURE-CRITICAL | `P_melt > 0.8` | CRITICAL | `COOL_DOWN` |
| MOLT-CASCADE | `molt_count >= 4` | CRITICAL | `VALIDATE` |
| THERMAL | `T > 2.0` | CRITICAL | `THROTTLE` |
| FROZEN | `T == 0.0 && P_melt == 0.0` | INFO | `MONITOR` |
| STALE-KNOWLEDGE | `time_since_validation > 3600s` | WARNING | `VALIDATE` |
| MELT-TREND | slope > 0.01 | WARNING | `MONITOR` |
| THERMAL-TREND | slope > 0.05 | WARNING | `MONITOR` |

State persisted to `melt_pressure_state.json`; logs to `melt_pressure.log`.

---

## 8. File & Transport Conventions

- **Inbox:** `~/.hermes/cns_inbox/` (Windows: `C:\Users\<user>\.hermes\cns_inbox\`)
- **Outbox:** `~/.hermes/cns_outbox/`
- **Accepted extensions:** `.json`, `.uscp.json`, `.md`, `.md.json`
- **Max file age:** `MAX_FILE_AGE_HOURS` (default 24h) — stale files skipped
- **Atomic write:** `os.replace()` used on Windows to avoid rename races

---

## 9. Identity & Determinism

**Identity hash (G2):**

```
identity_hash = sha256(role || model || backend)[:16]
format: "sha256:<16-hex-chars>"
```

**Ghost Tile block (v3 extension):**

```json
{
  "melt": {
    "deterministic": true,
    "identity_hash": "sha256:abcd1234...",
    ...
  }
}
```

When `deterministic=true`:
- `temperature` MUST be `0.0` (G1).
- vLLM start scripts propagate `--temperature 0.0 --seed <ghost-tile-id>` (`autoclaw/cudaclaw_wizard.py`).

---

## 10. Conformance

The canonical conformance suite is `autoclaw/tests/test_failure_modes.py` (13/13 PASS).  
It verifies every rule in `scripts/verification_checklist_runner.py` by injecting violations and asserting the monitor catches them.

**Parser conformance:** `cns-echo` test suite (`tests/`, 181 passed, 2 skipped) validates v2/v3 negotiation, signature adaptation, Windows rename behavior, and unknown-intent passthrough.

---

## 11. Maintenance

- When adding a new v3 payload block: update `signature.extensions` in the sender, add parsing in `cns_echo/echo.py` `REQUIRED_HEADER_FIELDS` / block extractor, extend `TelemetryQuantum` if telemetry-relevant, add a rule to `verification_checklist_runner.py` if it introduces an invariant.
- When changing a constant (e.g. `MAX_FILE_AGE_HOURS`, `μ`, `α`), document the change here and in `CHANGELOG.md`.
- `autoclaw` is the source of truth for daemon-side emission; `cns-echo` is the source of truth for receiver-side parsing.

---

*This document is the v3 protocol contract. If code and doc diverge, the code wins and this doc is patched.*
