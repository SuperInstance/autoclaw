"""
Failure Mode Injection Tests for CNS v3 Telemetry Invariants.

For each rule in the Verification Checklist, intentionally construct a
TelemetryQuantum that violates it, then assert the monitor flags it.
These tests document what breaks and whether the fleet halts or degrades.
"""
from dataclasses import dataclass
from typing import List

# Use the same definitions as the monitor to avoid import drift.
# In production this would import from cns_monitor_v3_telemetry.


@dataclass
class TelemetryQuantum:
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
        errors = []
        total = self.gamma + self.eta + self.delta
        if abs(total - 1.0) > 0.001:
            errors.append(f"CONS-1 violation: γ+η+δ={total:.4f} (must be 1.0)")
        if not 0.0 <= self.gamma <= 1.0:
            errors.append(f"CONS-2: gamma={self.gamma} out of [0,1]")
        if not 0.0 <= self.eta <= 1.0:
            errors.append(f"CONS-2: eta={self.eta} out of [0,1]")
        if not 0.0 <= self.delta <= 0.25:
            errors.append(f"CONS-2: delta={self.delta} out of [0,0.25]")
        if self.temperature < 0.0:
            errors.append(f"DRM: temperature={self.temperature} < 0")
        if self.capability < 0.0 or self.capability > 1.0:
            errors.append(f"MOLT-4: capability={self.capability} out of [0,1]")
        if self.molt_count > 5:
            errors.append(f"MOLT-6: molt_count={self.molt_count} > 5")
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
        if self.melt_pressure > self.max_crystallization_rate:
            self.molt_threshold_exceeded = True
            return True
        return False

    def is_frozen(self) -> bool:
        return abs(self.delta) < 1e-9

    def is_in_creative_zone(self) -> bool:
        return 0.4 <= self.semantic_distance <= 0.6

    def is_in_oneiric_zone(self) -> bool:
        return 0.6 <= self.semantic_distance <= 0.8

    def confidence_zone(self) -> str:
        if self.tau < 0.3:
            return "RED"
        elif self.tau < 0.7:
            return "YELLOW"
        else:
            return "GREEN"


class FailureTester:
    def __init__(self):
        self.results = []

    def expect_violations(self, name, tq, expected_rules):
        violations = tq.validate()
        found = [v for v in violations if any(rule in v for rule in expected_rules)]
        passed = len(found) == len(expected_rules)
        self.results.append((name, passed, violations, found))
        if not passed:
            print(f"FAIL: {name}")
            print(f"  expected {expected_rules}")
            print(f"  got violations: {violations}")
        else:
            print(f"PASS: {name}")

    def report(self):
        passed = sum(1 for _, p, _, _ in self.results if p)
        print(f"\nRESULT: {passed}/{len(self.results)} tests passed")
        return passed == len(self.results)


def test_cons1_gamma_eta_delta_sum():
    t = TelemetryQuantum(agent_id="x", gamma=0.5, eta=0.5, delta=0.5)  # sum=1.5
    return t


def test_cons1_under_crystallized():
    t = TelemetryQuantum(agent_id="x", gamma=0.1, eta=0.1, delta=0.1)  # sum=0.3
    return t


def test_cons2_gamma_high():
    t = TelemetryQuantum(agent_id="x", gamma=1.5, eta=0.0, delta=0.0)  # sum=1.5 but bounds fail
    return t


def test_cons2_eta_negative():
    t = TelemetryQuantum(agent_id="x", gamma=1.0, eta=-0.1, delta=0.1)
    return t


def test_cons2_delta_out_of_range():
    t = TelemetryQuantum(agent_id="x", gamma=0.8, eta=0.0, delta=0.3)  # delta>0.25
    return t


def test_drm_negative_temperature():
    t = TelemetryQuantum(agent_id="x", gamma=0.5, eta=0.3, delta=0.2, temperature=-0.5)
    return t


def test_molt4_capability_overflow():
    t = TelemetryQuantum(agent_id="x", gamma=0.5, eta=0.3, delta=0.2, capability=1.5)
    return t


def test_molt6_molt_count_exceeded():
    t = TelemetryQuantum(agent_id="x", gamma=0.5, eta=0.3, delta=0.2, molt_count=6)
    return t


def test_ua2_tau_overflow():
    t = TelemetryQuantum(agent_id="x", gamma=0.5, eta=0.3, delta=0.2, tau=1.5)
    return t


def test_molt7_phase_invalid():
    t = TelemetryQuantum(agent_id="x", gamma=0.5, eta=0.3, delta=0.2, molt_phase="chaos")
    return t


def test_mlt1_negative_validation_time():
    t = TelemetryQuantum(agent_id="x", gamma=0.5, eta=0.3, delta=0.2, time_since_validation_seconds=-1.0)
    return t


def test_drm2_temp_rise_negative():
    t = TelemetryQuantum(agent_id="x", gamma=0.5, eta=0.3, delta=0.2, temp_rise_rate=-0.5)
    return t


def test_ck2_creative_value_overflow():
    t = TelemetryQuantum(agent_id="x", gamma=0.5, eta=0.3, delta=0.2, creative_value=1.5)
    return t


def test_g1_determinism():
    t = TelemetryQuantum(agent_id="x", gamma=0.5, eta=0.3, delta=0.2, deterministic=True, temperature=1.0)
    # G1 is enforced in alerts, not in validate(); test separately
    return t


def test_melt_trigger():
    t = TelemetryQuantum(agent_id="x", gamma=0.5, eta=0.3, delta=0.2, melt_pressure=0.02, max_crystallization_rate=0.01)
    assert t.is_melt_triggered(), "expected melt triggered"


def test_frozen_delta_zero():
    t = TelemetryQuantum(agent_id="x", gamma=1.0, eta=0.0, delta=0.0)
    assert t.is_frozen(), "expected frozen"


if __name__ == "__main__":
    tester = FailureTester()

    # Validation-bound failures
    cases = [
        ("FAIL-CONS1-sum-too-high", test_cons1_gamma_eta_delta_sum(), ["CONS-1"]),
        ("FAIL-CONS1-under-crystallized", test_cons1_under_crystallized(), ["CONS-1"]),
        ("FAIL-CONS2-gamma-over", test_cons2_gamma_high(), ["CONS-2"]),
        ("FAIL-CONS2-eta-negative", test_cons2_eta_negative(), ["CONS-2"]),
        ("FAIL-CONS2-delta-over", test_cons2_delta_out_of_range(), ["CONS-2"]),
        ("FAIL-DRM-negative-T", test_drm_negative_temperature(), ["DRM"]),
        ("FAIL-MOLT4-capability-over", test_molt4_capability_overflow(), ["MOLT-4"]),
        ("FAIL-MOLT6-molt-over", test_molt6_molt_count_exceeded(), ["MOLT-6"]),
        ("FAIL-UA2-tau-over", test_ua2_tau_overflow(), ["UA-2"]),
        ("FAIL-MOLT7-phase", test_molt7_phase_invalid(), ["MOLT-7"]),
        ("FAIL-MLT1-negative-tv", test_mlt1_negative_validation_time(), ["MLT-1"]),
        ("FAIL-DRM2-temp-rise-negative", test_drm2_temp_rise_negative(), ["DRM-2"]),
        ("FAIL-CK2-creative-value", test_ck2_creative_value_overflow(), ["CK-2"]),
    ]

    for name, tq, expected in cases:
        tester.expect_violations(name, tq, expected)

    # Behavioral failures
    print("\n--- Behavioral invariants ---")
    try:
        test_melt_trigger()
        print("PASS: FAIL-MELT-trigger")
    except AssertionError as e:
        print(f"FAIL: FAIL-MELT-trigger — {e}")

    try:
        test_frozen_delta_zero()
        print("PASS: FAIL-FROZEN-delta-zero")
    except AssertionError as e:
        print(f"FAIL: FAIL-FROZEN-delta-zero — {e}")

    tester.report()
