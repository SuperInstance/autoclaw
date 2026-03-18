# Experiment Runner Specification

**File to implement:** `crew/runner.py`
**Depends on:** `crew/brain.py`, `schemas/task.yaml`
**Depended on by:** `crew/daemon.py`

## Purpose

The experiment runner executes individual experiments. It:
1. Takes a parameter set from the brain's plan
2. Modifies train.py accordingly
3. Runs the training
4. Captures metrics
5. Commits to git (optional)
6. Returns results

This is the component that actually uses the GPU.

## Experiment Lifecycle

```
Input: ExperimentParams {learning_rate: 0.005, warmup_steps: 100, ...}

1. BACKUP
   - Save current train.py as train.py.backup
   - Record current git HEAD

2. MODIFY
   - Ask brain.generate_modifications() for code changes
   - Apply changes to train.py
   - Validate: python -c "import ast; ast.parse(open('train.py').read())"
   - If validation fails: revert, mark experiment as failed, return

3. RUN
   - Execute: python train.py (or uv run train.py)
   - Capture stdout/stderr to run.log
   - Monitor for:
     - Timeout (time_budget_seconds + 60s grace period)
     - OOM errors
     - NaN loss
     - Process crash
   - Stream GPU utilization during run

4. PARSE
   - Read run.log for final metrics
   - Extract: val_bpb, train_loss, peak_memory_gb, training_seconds
   - If metrics not found: mark as failed

5. RECORD
   - If git_commit_each: git add train.py && git commit -m "exp_{N}: {params}"
   - Save to experiment directory:
     - train.py (the modified version)
     - run.log
     - metrics.json
     - checkpoint.pt (if keep_checkpoints != "none")
   - Append row to results.tsv

6. RESTORE
   - Restore train.py from backup (for next experiment)
   - Return ExperimentResult

7. EVALUATE
   - Compare metric to baseline
   - Compare to best-so-far
   - If new best: update crew state, create notification
```

## Core Implementation

```python
# crew/runner.py

import subprocess
import shutil
import json
import ast
import time
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

@dataclass
class ExperimentParams:
    """What to test in this experiment."""
    parameters: dict          # {"learning_rate": 0.005, ...}
    rationale: str            # Why we're testing this
    index: int                # Experiment number within task

@dataclass
class ExperimentResult:
    """What happened."""
    index: int
    parameters: dict
    success: bool
    metric_value: Optional[float]  # val_bpb (None if failed)
    train_loss: Optional[float]
    peak_memory_gb: Optional[float]
    training_seconds: Optional[float]
    commit_hash: Optional[str]
    error: Optional[str]      # Error message if failed
    log_path: Path
    timestamp: datetime


class ExperimentRunner:
    def __init__(self, config, brain):
        self.config = config
        self.brain = brain
        self.train_file = Path(config.experiments.train_file)
        self.results_dir = Path(config.experiments.results_dir)
        self.results_tsv = self.results_dir / "results.tsv"
        self.experiment_counter = self._load_counter()

    def run_experiment(self, params: ExperimentParams,
                       task_id: int) -> ExperimentResult:
        """Execute one experiment. Returns result regardless of success/failure."""

        exp_num = self.experiment_counter
        self.experiment_counter += 1
        exp_dir = self.results_dir / f"exp_{exp_num:04d}"
        exp_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc)

        # 1. BACKUP
        backup_path = self.train_file.with_suffix('.py.backup')
        shutil.copy2(self.train_file, backup_path)
        original_content = self.train_file.read_text()

        try:
            # 2. MODIFY
            modifications = self.brain.generate_modifications(
                params.parameters, original_content
            )
            modified_content = self._apply_modifications(
                original_content, modifications
            )

            # Validate syntax
            if not self._validate_python(modified_content):
                return self._failed_result(
                    exp_num, params, timestamp, exp_dir,
                    "Syntax error in modified train.py"
                )

            self.train_file.write_text(modified_content)

            # Save modified train.py to experiment dir
            (exp_dir / "train.py").write_text(modified_content)

            # 3. RUN
            log_path = exp_dir / "run.log"
            result = self._execute_training(log_path)

            if not result["success"]:
                return self._failed_result(
                    exp_num, params, timestamp, exp_dir,
                    result.get("error", "Training failed")
                )

            # 4. PARSE
            metrics = self._parse_metrics(log_path)

            if metrics is None:
                return self._failed_result(
                    exp_num, params, timestamp, exp_dir,
                    "Could not parse metrics from run.log"
                )

            # 5. RECORD
            commit_hash = None
            if self.config.experiments.git_commit_each:
                commit_hash = self._git_commit(exp_num, params.parameters)

            # Save metrics
            (exp_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

            # Handle checkpoint
            self._handle_checkpoint(exp_dir, metrics)

            # Append to results.tsv
            self._append_results_tsv(
                exp_num, task_id, params, metrics, commit_hash
            )

            return ExperimentResult(
                index=exp_num,
                parameters=params.parameters,
                success=True,
                metric_value=metrics.get("val_bpb"),
                train_loss=metrics.get("train_loss"),
                peak_memory_gb=metrics.get("peak_memory_gb"),
                training_seconds=metrics.get("training_seconds"),
                commit_hash=commit_hash,
                error=None,
                log_path=log_path,
                timestamp=timestamp,
            )

        finally:
            # 6. RESTORE (always, even if crashed)
            shutil.copy2(backup_path, self.train_file)
            backup_path.unlink(missing_ok=True)

    def _apply_modifications(self, content: str,
                              modifications) -> str:
        """Apply code modifications to train.py content."""
        result = content
        for change in modifications.changes:
            if change["old_text"] in result:
                result = result.replace(
                    change["old_text"],
                    change["new_text"],
                    1  # Replace only first occurrence
                )
            else:
                raise ValueError(
                    f"Could not find text to replace: {change['old_text'][:80]}..."
                )
        return result

    def _validate_python(self, content: str) -> bool:
        """Check if content is valid Python."""
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False

    def _execute_training(self, log_path: Path) -> dict:
        """Run train.py and capture output."""
        timeout = self.config.experiments.time_budget_seconds + 60  # Grace period

        try:
            with open(log_path, 'w') as log_file:
                proc = subprocess.run(
                    ["python", str(self.train_file)],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                    cwd=Path.cwd(),
                )

            if proc.returncode != 0:
                return {
                    "success": False,
                    "error": f"train.py exited with code {proc.returncode}"
                }

            return {"success": True}

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Training exceeded timeout ({timeout}s)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}"
            }

    def _parse_metrics(self, log_path: Path) -> Optional[dict]:
        """Parse training metrics from run.log.

        Looks for the output format of train.py:
        - val_bpb is printed near the end
        - Training loss is logged during training
        - Memory usage is reported
        """
        content = log_path.read_text()

        metrics = {}

        # Parse val_bpb (the key metric)
        # train.py prints: "val_bpb: X.XXX" or similar
        import re

        # Look for val_bpb
        match = re.search(r'val[_\s]bpb[:\s]+([0-9.]+)', content, re.IGNORECASE)
        if match:
            metrics["val_bpb"] = float(match.group(1))
        else:
            return None  # Can't find the key metric

        # Look for training loss (last reported value)
        losses = re.findall(r'loss[:\s]+([0-9.]+)', content)
        if losses:
            metrics["train_loss"] = float(losses[-1])

        # Look for peak memory
        mem_match = re.search(r'peak[_\s]memory[:\s]+([0-9.]+)', content, re.IGNORECASE)
        if mem_match:
            metrics["peak_memory_gb"] = float(mem_match.group(1))

        # Look for training time
        time_match = re.search(r'training[_\s]time[:\s]+([0-9.]+)', content, re.IGNORECASE)
        if time_match:
            metrics["training_seconds"] = float(time_match.group(1))

        return metrics

    def _git_commit(self, exp_num: int, params: dict) -> Optional[str]:
        """Commit the modified train.py to git."""
        try:
            param_str = ", ".join(f"{k}={v}" for k, v in params.items())
            msg = f"exp_{exp_num:04d}: {param_str}"

            subprocess.run(
                ["git", "add", str(self.train_file)],
                capture_output=True, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", msg],
                capture_output=True, check=True
            )
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, check=True, text=True
            )
            return result.stdout.strip()[:7]
        except subprocess.CalledProcessError:
            return None

    def _handle_checkpoint(self, exp_dir: Path, metrics: dict):
        """Handle model checkpoint based on config."""
        policy = self.config.experiments.keep_checkpoints

        if policy == "none":
            # Delete any checkpoint that was saved
            for f in exp_dir.glob("*.pt"):
                f.unlink()
        elif policy == "best_only":
            # Keep checkpoint only if this is the best experiment
            # (Comparison happens in daemon, not here)
            pass
        elif policy == "all":
            pass  # Keep everything

    def _append_results_tsv(self, exp_num, task_id, params, metrics, commit_hash):
        """Append a row to results.tsv."""
        if not self.results_tsv.exists():
            # Write header
            self.results_tsv.write_text(
                "experiment\ttask\tcommit\tval_bpb\ttrain_loss\t"
                "memory_gb\tseconds\tparameters\ttimestamp\n"
            )

        param_str = json.dumps(params.parameters, separators=(',', ':'))
        row = (
            f"exp_{exp_num:04d}\t{task_id}\t{commit_hash or 'none'}\t"
            f"{metrics.get('val_bpb', 'NaN')}\t{metrics.get('train_loss', 'NaN')}\t"
            f"{metrics.get('peak_memory_gb', 'NaN')}\t{metrics.get('training_seconds', 'NaN')}\t"
            f"{param_str}\t{datetime.now(timezone.utc).isoformat()}\n"
        )
        with open(self.results_tsv, 'a') as f:
            f.write(row)

    def _failed_result(self, exp_num, params, timestamp, exp_dir, error):
        """Create a failed experiment result."""
        # Log the error
        (exp_dir / "error.txt").write_text(error)

        return ExperimentResult(
            index=exp_num,
            parameters=params.parameters,
            success=False,
            metric_value=None,
            train_loss=None,
            peak_memory_gb=None,
            training_seconds=None,
            commit_hash=None,
            error=error,
            log_path=exp_dir / "run.log",
            timestamp=timestamp,
        )

    def _load_counter(self) -> int:
        """Load experiment counter from disk."""
        counter_file = self.results_dir / ".counter"
        if counter_file.exists():
            return int(counter_file.read_text().strip())
        return 1

    def _save_counter(self):
        """Persist experiment counter."""
        counter_file = self.results_dir / ".counter"
        counter_file.write_text(str(self.experiment_counter))
```

## Results.tsv Format

Tab-separated, append-only. One row per experiment.

```
experiment   task  commit   val_bpb  train_loss  memory_gb  seconds  parameters                                    timestamp
exp_0001     42    a3f2c1d  1.038    1.234       42.5       300      {"learning_rate":0.0001,"warmup_steps":100}    2026-03-18T10:40:00Z
exp_0002     42    b4d3e2f  1.032    1.221       42.0       295      {"learning_rate":0.0005,"warmup_steps":100}    2026-03-18T10:46:00Z
exp_0003     42    c5e4f3a  1.006    1.198       42.1       298      {"learning_rate":0.005,"warmup_steps":100}     2026-03-18T10:52:00Z
```

## Safety Measures

### train.py Protection
- ALWAYS backup before modifying
- ALWAYS restore after experiment (even on crash)
- Validate syntax before running
- If 3 consecutive modifications fail syntax check → pause task, notify captain

### Resource Protection
- Monitor GPU temperature during run (via heartbeat thread)
- Kill training process if GPU > shutdown_c temperature
- Monitor disk space before saving checkpoints
- Timeout with grace period (budget + 60 seconds)

### Git Safety
- Never force push
- Never amend commits
- Each experiment is its own commit
- Original train.py is always restored to HEAD after experiment
- If git is broken, disable git commits for session (don't block experiments)

### Experiment Isolation
- Each experiment runs in a fresh subprocess
- No state leaks between experiments
- train.py is always restored to original between experiments
- If an experiment corrupts train.py, backup restores it

## Implementation Checklist for Haiku

```
[ ] Create crew/runner.py with ExperimentRunner class
[ ] Implement ExperimentParams and ExperimentResult dataclasses
[ ] Implement run_experiment() with full lifecycle (backup → modify → run → parse → record → restore)
[ ] Implement _apply_modifications() for code changes
[ ] Implement _validate_python() syntax check
[ ] Implement _execute_training() with subprocess and timeout
[ ] Implement _parse_metrics() for train.py output format
[ ] Implement _git_commit() for experiment tracking
[ ] Implement _handle_checkpoint() for checkpoint management
[ ] Implement _append_results_tsv() for results tracking
[ ] Implement experiment counter persistence
[ ] Implement safety measures (backup/restore, syntax validation)
[ ] Implement failed result handling and error logging
[ ] Test: run experiment with known-good params → metrics parsed correctly
[ ] Test: run experiment with bad params → syntax validation catches error
[ ] Test: crash during experiment → train.py restored from backup
[ ] Test: results.tsv format is correct and parseable
[ ] Test: git commits created with correct messages
```
