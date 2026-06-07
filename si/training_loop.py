#!/usr/bin/env python3
"""autoclaw training loop — watches for new data, trains, evaluates, promotes or rolls back."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

WATCH_DIR = Path(os.getenv("AUTOCLAW_WATCH_DIR", "./data/incoming"))
MODEL_DIR = Path(os.getenv("AUTOCLAW_MODEL_DIR", "./models"))
BENCHMARK_SCRIPT = Path(os.getenv("AUTOCLAW_BENCHMARK", "./scripts/evaluate.sh"))
CONSERVATION_ENDPOINT = os.getenv("CONSERVATION_ENDPOINT", "")  # optional
CURRENT_LINK = MODEL_DIR / "current"
GPU_HOURS_BUDGET = float(os.getenv("AUTOCLAW_GPU_BUDGET", "10.0"))

STATE_FILE = Path(os.getenv("AUTOCLAW_STATE", "./si/state.json"))


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"processed": [], "gpu_hours_used": 0.0}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def check_budget(state, estimated_hours=1.0):
    remaining = GPU_HOURS_BUDGET - state["gpu_hours_used"]
    if remaining < estimated_hours:
        print(f"[budget] insufficient GPU hours: {remaining:.2f} remaining, {estimated_hours:.2f} needed")
        return False
    return True


def report_budget(hours):
    """Report actual GPU hours to conservation-law (optional)."""
    if CONSERVATION_ENDPOINT:
        try:
            import urllib.request
            data = json.dumps({"hours": hours}).encode()
            req = urllib.request.Request(CONSERVATION_ENDPOINT, data=data,
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"[budget] failed to report: {e}")


def data_hash(path):
    h = hashlib.sha256()
    for f in sorted(Path(path).rglob("*")):
        if f.is_file():
            h.update(f.read_bytes())
    return h.hexdigest()


def run_training(data_path, output_model):
    """Invoke nanochat training."""
    cmd = ["python", "-m", "nanochat.train", "--data", str(data_path), "--output", str(output_model)]
    print(f"[train] running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[train] failed: {result.stderr}")
        return False
    print("[train] completed successfully")
    return True


def run_evaluation(model_path):
    """Run benchmark and return score."""
    cmd = [str(BENCHMARK_SCRIPT), str(model_path)]
    print(f"[eval] running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[eval] failed: {result.stderr}")
        return -1.0
    try:
        return float(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print(f"[eval] could not parse score from: {result.stdout}")
        return -1.0


def get_current_score():
    if CURRENT_LINK.exists() and CURRENT_LINK.is_symlink():
        return run_evaluation(CURRENT_LINK.resolve())
    return 0.0


def promote_model(model_path):
    """Update the 'current' symlink to point at the new model."""
    if CURRENT_LINK.exists() or CURRENT_LINK.is_symlink():
        CURRENT_LINK.unlink()
    CURRENT_LINK.symlink_to(model_path.resolve())
    print(f"[promote] current → {model_path}")


def main():
    state = load_state()
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[watch] scanning {WATCH_DIR} for new data batches...")
    for entry in sorted(WATCH_DIR.iterdir()):
        if not entry.is_dir():
            continue
        dh = data_hash(entry)
        if dh in state["processed"]:
            continue
        print(f"[found] new batch: {entry.name} (hash={dh[:12]})")

        estimated_hours = 1.0  # conservative default
        if not check_budget(state, estimated_hours):
            print(f"[skip] queueing {entry.name} — budget exhausted")
            continue

        candidate = MODEL_DIR / f"candidate_{dh[:12]}"
        start = time.time()
        success = run_training(entry, candidate)
        elapsed_hours = (time.time() - start) / 3600.0
        state["gpu_hours_used"] += elapsed_hours
        report_budget(elapsed_hours)

        if not success:
            shutil.rmtree(candidate, ignore_errors=True)
            state["processed"].append(dh)
            save_state(state)
            continue

        new_score = run_evaluation(candidate)
        old_score = get_current_score()
        print(f"[compare] new={new_score:.4f} current={old_score:.4f}")

        if new_score > old_score:
            promote_model(candidate)
            print(f"[accept] promoted model from {entry.name}")
        else:
            shutil.rmtree(candidate, ignore_errors=True)
            print(f"[rollback] rejected model from {entry.name} (no improvement)")

        state["processed"].append(dh)
        save_state(state)

    print("[done] training loop complete")


if __name__ == "__main__":
    main()
