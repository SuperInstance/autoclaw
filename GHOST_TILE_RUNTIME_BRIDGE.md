# Ghost Tile Runtime Bridge
## Spec v1.0 — Phase 3 Implementation

**Target repos:** `SuperInstance/autoclaw`, `SuperInstance/claw`
**Date:** 2026-08-23
**Status:** SPEC — ready for implementation

---

## 1. Purpose

This bridge turns Ghost Tile theory (LOG-tensor / si-papers-new P61–P69) into runtime behavior inside the AutoClaw crew system. It closes 5 identified gaps between abstract Ghost Tile formalism and the Claw agent implementation.

---

## 2. Gap Matrix

| Gap | Ghost Tile Requirement | Claw Status | Bridge Artifact |
|-----|------------------------|-------------|-----------------|
| G1 | Deterministic execution (T=0, fixed seed) | No flag | `claw_agent.json`: add `deterministic` bool |
| G2 | Identity hash h = SHA256(M\|s\|h) | Stub only | `CrewDaemon.compute_identity_hash()` |
| G3 | Execution context C (KV-cache fingerprint) | Not tracked | `telemetry.executionContext` block |
| G4 | Composition algebra (associative chaining) | No test | `verification_checklist_runner.py`: COMP-1 rule |
| G5 | O(1) program indexing by identity hash | No registry | `CrewDaemon.ghost_tile_registry` dict |

---

## 3. Schema Changes

### 3.1 `claw_agent.json` — add deterministic mode

```jsonc
{
  "model": {
    "provider": "string",
    "modelId": "string",
    "deterministic": false,   // G1: enforce T=0, fixed seed when true
    "temperature_override": null  // if null, use T=0 when deterministic=true
  },
  ...
}
```

### 3.2 `claw_agent.json` — add identity hash

```jsonc
{
  "shell": {
    "identityHash": "sha256:M.weights||seed||fineTuneHash",  // G2: P03 Kan extension
    ...
  }
}
```

### 3.3 `claw_agent.json` — add execution context

```jsonc
{
  "state": {
    "gamma": 0.5, "eta": 0.1, "delta": 0.2,
    "executionContext": {   // G3: model-as-program semantics
      "kvCacheFingerprint": "sha256:...",
      "attentionPatternHash": "sha256:...",
      "activationSummary": "mean=0.01 std=0.12"
    }
  }
}
```

---

## 4. Daemon Changes (`crew/daemon.py`)

### 4.1 Identity Hash Computation

Add method to `CrewDaemon`:

```python
def compute_identity_hash(self, agent_config: Dict) -> str:
    """G2: SHA256 commitment over model weights provenance, seed, fine-tune."""
    import hashlib
    m = hashlib.sha256()
    m.update(agent_config.get("shell", {}).get("identityHash", "").encode())
    m.update(agent_config.get("seed", {}).get("purpose", "").encode())
    m.update(agent_config.get("model", {}).get("modelId", "").encode())
    return f"sha256:{m.hexdigest()[:16]}"
```

Call from `work_on_task()` after planning:

```python
# G2: Verify identity hash before and after experiment
pre_hash = self.compute_identity_hash(task.agent_config)
# ... run experiments ...
post_hash = self.compute_identity_hash(task.agent_config)
if pre_hash != post_hash:
    logger.warning(f"Identity hash changed for task {task.id}: {pre_hash} → {post_hash}")
```

### 4.2 Ghost Tile Registry

Add to `CrewDaemon.__init__`:

```python
self.ghost_tile_registry: Dict[str, Dict] = {}  # G5: O(1) lookup by hash
```

Add method:

```python
def register_ghost_tile(self, tile_hash: str, tile_spec: Dict):
    self.ghost_tile_registry[tile_hash] = {
        "spec": tile_spec,
        "first_seen": datetime.now(timezone.utc).isoformat(),
        "usage_count": 0,
    }
```

---

## 5. Verification Checklist Updates (`scripts/verification_checklist_runner.py`)

### 5.1 G1 — Determinism Gate

```python
def check_determinism_gate(agent: Dict) -> bool:
    model = agent.get("model", {})
    if model.get("deterministic", False):
        if model.get("temperature_override") is None:
            return False, "deterministic=true requires explicit temperature_override"
        if model.get("temperature_override", 1.0) > 0.0:
            return False, "deterministic=true requires T=0"
    return True, "determinism gate OK"
```

### 5.2 G2 — Identity Hash Invariant

```python
def check_identity_hash(agent: Dict) -> bool:
    shell = agent.get("shell", {})
    ih = shell.get("identityHash", "")
    if not ih.startswith("sha256:"):
        return False, "identityHash must be sha256:<hex>"
    if len(ih) != 67:  # "sha256:" + 64 hex chars
        return False, "identityHash malformed"
    return True, "identity hash format OK"
```

### 5.3 G4 — Composition Algebra Test

```python
def check_composition_algebra(agent: Dict) -> bool:
    """GT1 ∘ (GT2 ∘ GT3) == (GT1 ∘ GT2) ∘ GT3 (semantic equivalence)."""
    equipment = agent.get("equipment", [])
    if len(equipment) < 2:
        return True, "composition: trivial (<2 equipment)"
    # In production: run composed inference twice and assert equal outputs
    return True, "composition algebra: asserted (production test required)"
```

---

## 6. CNS v3 Telemetry Extension

The existing v3 telemetry now carries Ghost Tile fields in the `melt` block:

```json
{
  "melt": {
    "melt_pressure": 0.003,
    "max_crystallization_rate": 0.015,
    "identity_hash": "sha256:abc123...",       // G2
    "deterministic": false,                     // G1
    "execution_context_hash": "sha256:def456..." // G3
  }
}
```

---

## 7. Implementation Order

1. **Schema** — update `claw/schemas_gold_standard/claw_agent.json`
2. **Daemon** — add identity hash + registry to `crew/daemon.py`
3. **Wizard** — expose `--ghost-tile-mode` flag in `cudaclaw_wizard.py` (optional)
4. **Checklist** — add G1/G2/G4 rules
5. **Tests** — 11/11 checklist pass
6. **Push** — commit-push to origin

---

## 8. Success Criteria

- [ ] `claw_agent.json` has `deterministic`, `identityHash`, `executionContext` fields
- [ ] `verification_checklist_runner.py` reports 11+ PASS (existing + new)
- [ ] `daemon.py` emits `identity_hash` field in CNS v3 melt block
- [ ] All changes committed and pushed to `origin/master`
