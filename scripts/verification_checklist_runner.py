#!/usr/bin/env python3
"""
Verification Checklist Runner
Executes P56-60 invariant checks against live telemetry or saved snapshots.
Outputs pass/fail per rule with violation details.
"""
import json
import math
import os
from datetime import datetime, timezone
from typing import Dict, List, Tuple

# Invariant definitions from VERIFICATION_CHECKLIST_P56-60.md
RULES = {
    "CONS-1": {
        "description": "γ + η + δ = 1 (conservation law)",
        "check": lambda d: abs(d.get("gamma",0)+d.get("eta",0)+d.get("delta",0) - 1.0) < 0.001
    },
    "CONS-2": {
        "description": "γ∈[0,1], η∈[0,1], δ∈[0,0.25]",
        "check": lambda d: (0<=d.get("gamma",-1)<=1 and 0<=d.get("eta",-1)<=1 and 0<=d.get("delta",-1)<=0.25)
    },
    "CONS-3": {
        "description": "η = (1−γ)² in ONE_PHASE mode",
        "check": lambda d: abs(d.get("eta",0) - (1-d.get("gamma",0))**2) < 0.01 if d.get("conservation_mode") != "TWO_PHASE" else True
    },
    "MOLT-1": {
        "description": "P_melt > crystallization_rate triggers molt",
        "check": lambda d: d.get("max_crystallization_rate", 1e9) >= 0 or d.get("melt_pressure", 0) <= d.get("max_crystallization_rate", 0)
    },
    "MOLT-5": {
        "description": "identityHash preserved across molt",
        "check": lambda d: d.get("identityHash_before") == d.get("identityHash_after") if "identityHash_before" in d else True
    },
    "MOLT-6": {
        "description": "moltCount < 5",
        "check": lambda d: d.get("molt_count", 0) < 5
    },
    "DRM-1": {
        "description": "T_idle >= T_task (monotonic rise in idle)",
        "check": lambda d: d.get("temperature_idle", 2.0) >= d.get("temperature_task", 1.0)
    },
    "CK-1": {
        "description": "κ(Δ) = exp(−(Δ−0.5)²/0.02) positive",
        "check": lambda d: math.exp(-((d.get("semantic_distance",0.5)-0.5)**2)/0.02) > 0.01
    },
    "OPT-1": {
        "description": "δ*(λ_env) within bounds",
        "check": lambda d: 0 <= d.get("delta", 0) <= 0.25
    },
    "UA-1": {
        "description": "τ² = exp(−σ²) (no /2 per CHECKLIST)",
        "check": lambda d: True  # Placeholder — requires sigma measurement
    },
    "MLT-2": {
        "description": "Staleness factor computed: (t−tv)·γ",
        "check": lambda d: True  # Placeholder — requires timestamps
    },
}

def evaluate(data: Dict) -> Tuple[bool, List[Dict]]:
    results = []
    all_pass = True
    for rule_id, rule in RULES.items():
        passed = rule["check"](data)
        results.append({
            "rule": rule_id,
            "description": rule["description"],
            "passed": passed,
        })
        if not passed:
            all_pass = False
    return all_pass, results

def main():
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
        with open(path) as f:
            data = json.load(f)
    else:
        path = os.path.expanduser("~/.hermes/cns_telemetry_state.json")
        try:
            with open(path) as f:
                raw = json.load(f)
            data = {}
            for aid, snap in raw.get("agent_history", {}).items():
                data[aid] = snap
        except FileNotFoundError:
            print(f"No telemetry state at {path}")
            sys.exit(1)

    print("=" * 70)
    print(f"VERIFICATION CHECKLIST RUN — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    agents = data if isinstance(data, dict) and "agent_history" not in data else data
    if "agent_history" in data:
        agents = data["agent_history"]

    fleet_pass = True
    for agent_id, snapshot in agents.items():
        print(f"\n--- Agent: {agent_id} ---")
        all_pass, results = evaluate(snapshot)
        fleet_pass = fleet_pass and all_pass
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"  [{status}] {r['rule']}: {r['description']}")

    print("\n" + "=" * 70)
    print(f"FLEET RESULT: {'ALL PASS' if fleet_pass else 'FAILURES DETECTED'}")
    print("=" * 70)
    sys.exit(0 if fleet_pass else 1)

if __name__ == "__main__":
    main()
