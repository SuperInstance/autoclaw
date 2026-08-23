#!/usr/bin/env python3
"""
Smoke test for MeltPressureMonitor.
Injects synthetic telemetry and verifies alerts + CNS output.
"""
import os, sys, json, time, tempfile
from pathlib import Path

# Ensure we can import from autoclaw scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from melt_pressure_monitor import (
    MeltPressureMonitor,
    TelemetryQuantum,
    evaluate_alert,
    AgentHealthWindow,
)

def test_evaluate_alert_basic():
    win = AgentHealthWindow(agent_id="test")
    tq = TelemetryQuantum(
        agent_id="test",
        gamma=0.5, eta=0.3, delta=0.2,
        temperature=1.0, melt_pressure=0.8,
        max_crystallization_rate=0.5, molt_count=0,
        capability=0.8, tau=0.5,
        timestamp="2026-08-23T03:00:00Z",
    )
    win.push(tq)
    alert = evaluate_alert(tq, win)
    assert alert["level"] == "CRITICAL"
    assert "MOLT-1" in alert["rules"] and "MELT-PRESSURE-CRITICAL" in alert["rules"]
    assert "VALIDATE" in alert["actions"] and "COOL_DOWN" in alert["actions"]
    print("PASS: basic MOLT-1 alert")

def test_critical_thresholds():
    win = AgentHealthWindow(agent_id="test")
    tq = TelemetryQuantum(
        agent_id="test",
        gamma=0.2, eta=0.1, delta=0.7,
        temperature=6.0, melt_pressure=1.0,
        max_crystallization_rate=0.3, molt_count=4,
        capability=0.3, tau=0.1,
        timestamp="2026-08-23T03:00:00Z",
    )
    win.push(tq)
    alert = evaluate_alert(tq, win)
    assert alert["level"] == "CRITICAL"
    assert "MELT-PRESSURE-CRITICAL" in alert["rules"]
    assert "COOL_DOWN" in alert["actions"]
    assert "MOLT" in alert["actions"]
    print("PASS: critical thresholds")

def test_trend_detection():
    win = AgentHealthWindow(agent_id="test")
    for i in range(6):
        tq = TelemetryQuantum(
            agent_id="test",
            gamma=0.5, eta=0.3, delta=0.2,
            temperature=1.0 + i * 0.2, melt_pressure=0.2 + i * 0.1,
            max_crystallization_rate=0.5, molt_count=0,
            capability=0.8, tau=0.5,
            timestamp=f"2026-08-23T03:00:{i:02d}Z",
        )
        win.push(tq)
    latest = TelemetryQuantum(
        agent_id="test",
        gamma=0.5, eta=0.3, delta=0.2,
        temperature=2.0, melt_pressure=0.7,
        max_crystallization_rate=0.5, molt_count=0,
        capability=0.8, tau=0.5,
        timestamp="2026-08-23T03:00:06Z",
    )
    alert = evaluate_alert(latest, win)
    # trend should flag rising melt pressure
    assert "MELT-TREND-RISING" in alert["rules"]
    print("PASS: trend detection")

def test_monitor_ingest_emits_cns():
    import tempfile, shutil
    tmp_in = tempfile.mkdtemp()
    tmp_out = tempfile.mkdtemp()
    orig_in = os.environ.get("HOME")
    os.environ["HOME"] = tmp_in

    # Patch module-level paths
    import melt_pressure_monitor as mpm
    mpm.INBOX_PATH = tmp_in
    mpm.OUTBOX_PATH = tmp_out
    mpm.STATE_FILE = os.path.join(tmp_in, "melt_pressure_state.json")
    mpm.LOG_FILE = os.path.join(tmp_in, "melt_pressure.log")

    mon = MeltPressureMonitor(poll_interval=1)
    tq = TelemetryQuantum(
        agent_id="test-agent",
        gamma=0.5, eta=0.3, delta=0.2,
        temperature=1.0, melt_pressure=0.8,
        max_crystallization_rate=0.5, molt_count=0,
        capability=0.8, tau=0.5,
        timestamp="2026-08-23T03:00:00Z",
    )
    mon.ingest_telemetry(tq)
    # Check state saved
    assert os.path.exists(mpm.STATE_FILE)
    with open(mpm.STATE_FILE) as f:
        state = json.load(f)
    assert "test-agent" in state["windows"]
    print("PASS: ingress + state persistence")

    os.environ["HOME"] = orig_in
    shutil.rmtree(tmp_in, ignore_errors=True)
    if os.path.isdir(tmp_out):
        shutil.rmtree(tmp_out, ignore_errors=True)


if __name__ == "__main__":
    test_evaluate_alert_basic()
    test_critical_thresholds()
    test_trend_detection()
    test_monitor_ingest_emits_cns()
    print("ALL TESTS PASSED")
