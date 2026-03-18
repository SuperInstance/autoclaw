# Daemon Specification

**File to implement:** `crew/daemon.py`
**Depends on:** `schemas/config.yaml`, `schemas/crew.yaml`
**Depended on by:** Everything else — this is the main process

## Purpose

The daemon is the always-on process that runs the crew. It starts when the
captain says `crew start` and runs until `crew stop` or the machine shuts down.
It never exits on its own. If it crashes, it restarts automatically.

## Process Model

```
crew start
    │
    ▼
┌─────────────┐
│  Load Config │ ← Read data/config.yaml, merge with defaults
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Load State  │ ← Read data/crew/state.yaml (or create fresh)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Start Threads│ ← Trigger watcher, heartbeat, webhook server
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  MAIN LOOP  │ ← Runs forever (see below)
└──────┬──────┘
       │ (SIGTERM or `crew stop`)
       ▼
┌─────────────┐
│  Shutdown   │ ← Finish current experiment, persist state, exit
└─────────────┘
```

## Main Loop

This is the heart of the daemon. It runs forever.

```python
def main_loop(self):
    while not self.shutdown_requested:
        # 1. Check for captain commands (from CLI pipe)
        self.process_commands()

        # 2. Check task board
        next_task = self.scheduler.get_next_task()

        if next_task:
            # 3a. Work on the task
            self.set_mode("working")
            self.work_on_task(next_task)
            # After task: review results, create notifications, update knowledge
            self.set_mode("reviewing")
            self.review_results(next_task)
        else:
            # 3b. No explicit tasks — check triggers
            new_tasks = self.trigger_manager.check_all()
            if new_tasks:
                continue  # Go back to step 2

            # 3c. No triggers fired — do maintenance if needed
            if self.needs_maintenance():
                self.set_mode("maintaining")
                self.run_maintenance()
            elif self.config.tasks.study_enabled:
                # 3d. Nothing else — study
                self.set_mode("studying")
                self.run_study_session()
            else:
                # 3e. Study disabled and nothing to do
                self.set_mode("idle")
                time.sleep(60)  # Check again in 1 minute

        # 4. Persist state after every cycle
        self.persist_state()
```

## Threads

The daemon runs these background threads:

### 1. Heartbeat Thread
```
Every config.daemon.heartbeat_interval_seconds (default: 30s):
  - Read GPU stats via nvidia-smi (utilization, temp, memory, power)
  - Update crew.gpu in state
  - Check temperature thresholds
  - If temp > throttle_c: reduce batch size, notify captain
  - If temp > shutdown_c: stop current experiment, notify captain
  - Check disk usage
  - If disk > warn_pct: create maintenance task
  - If disk > critical_pct: stop experiments, force archive
  - Write heartbeat timestamp to data/crew/heartbeat
  - Reset daily counters if midnight UTC passed
```

### 2. Trigger Watcher Thread
```
Continuously:
  For each enabled trigger:
    If trigger.type == "rss" and time_since(last_checked) > poll_interval:
      Fetch feed, apply filters, create tasks if matched
    If trigger.type == "sensor" and time_since(last_checked) > poll_interval:
      Read sensor, check threshold, fire if exceeded
    If trigger.type == "schedule":
      Evaluate cron expression, fire if matched
    If trigger.type == "file_watch":
      Check inotify events or poll for changes
    If trigger.type == "command" and time_since(last_checked) > poll_interval:
      Run command, check output, fire if non-empty

  Apply rate limits (max_fires_per_day, cooldown_minutes)
  Persist trigger state (last_checked, last_fired, fires_today)
  Sleep 1 second between cycles
```

### 3. Webhook Server Thread (optional)
```
If config.triggers.webhook_port > 0:
  Start HTTP server on config.triggers.webhook_host:webhook_port
  For each POST request:
    Validate HMAC-SHA256 signature (if webhook_secret configured)
    Match against webhook triggers by endpoint path
    Apply filters
    Create task or notify as configured
  Response: 200 OK (accepted) or 404 (no matching trigger)
```

### 4. Command Listener Thread
```
Listen on Unix socket: data/crew.sock (or named pipe on Windows)
Accept commands from CLI (`crew status`, `crew add`, etc.)
Parse command, execute, return response
See specs/captain-cli.md for command format
```

## Startup Sequence

```
1. Parse command line: crew start [--config path] [--foreground] [--verbose]
2. Check for existing PID file
   - If exists and process alive: "Crew already running (PID {pid}). Use 'crew stop' first."
   - If exists and process dead: Remove stale PID file, continue
3. Load config (defaults + user overrides)
4. Validate config (check LLM connectivity, GPU availability, disk space)
5. Load persisted state from data/crew/state.yaml
   - If no state file: Create fresh state
   - If state exists: Resume from last known state
     - Check if last experiment was interrupted
     - If interrupted: Mark as failed, create notification
6. Create PID file
7. Daemonize (unless --foreground)
   - Redirect stdout/stderr to log file
   - Detach from terminal
8. Start background threads (heartbeat, triggers, webhook, command listener)
9. Set mode to "starting"
10. Create notification: "Crew started. Resuming from [last state]."
11. Enter main loop
```

## Shutdown Sequence

```
On SIGTERM, SIGINT, or `crew stop` command:

1. Set shutdown_requested = true
2. Set mode to "shutting_down"
3. If experiment running:
   a. Wait up to graceful_shutdown_timeout_seconds for it to finish
   b. If still running after timeout: kill experiment process, mark task as paused
4. Persist final state to data/crew/state.yaml
5. Stop background threads
6. Remove PID file
7. Remove Unix socket
8. Create notification: "Crew stopped. [N] tasks in queue. Last task: [#id]."
9. Exit 0
```

## Crash Recovery

```
On unexpected exit (crash, OOM, power loss):

Next startup detects:
  - PID file exists but process not running
  - State file has last_persisted timestamp
  - Heartbeat file shows when last heartbeat was

Recovery:
  1. Load state from last persist
  2. Check active task:
     - Was an experiment running? → Mark experiment as failed, keep task active
     - Was in maintenance? → Re-run maintenance
     - Was in study? → Discard study progress, start fresh
  3. Increment restarts counter
  4. Check max_restarts_per_hour
     - If exceeded: Create urgent notification, wait 1 hour before retrying
  5. Create notification: "Crew restarted after crash. Recovering from [state]."
  6. Resume main loop
```

## State Persistence

**What is persisted (survives restart):**
- Crew mode and current task progress
- Task board (all tasks)
- Knowledge base
- Trigger states (last_checked, fires_today)
- Notification history
- Metrics (lifetime counters)

**What is NOT persisted (rebuilt on startup):**
- GPU stats (re-read from nvidia-smi)
- Thread states (threads restarted)
- Socket connections (re-created)
- In-flight experiment (must be re-run)

**Persistence format:** YAML files in data/ directory
**Persistence frequency:** After every mode transition, after every experiment, every heartbeat

## File Locations

```
data/
├── config.yaml              # User configuration (captain edits this)
├── crew/
│   ├── state.yaml           # Current crew state
│   ├── knowledge.yaml       # Knowledge base
│   ├── study_queue.yaml     # Self-study topics
│   └── heartbeat            # Last heartbeat timestamp (plain text)
├── tasks/
│   ├── ACTIVE -> 42.yaml    # Symlink to active task
│   ├── 42.yaml              # Task files
│   ├── 43.yaml
│   └── completed/           # Completed/cancelled tasks
│       ├── 1.yaml
│       └── ...
├── triggers/
│   ├── 1.yaml               # Trigger definitions
│   └── ...
├── notifications/
│   ├── feed.log             # Append-only notification log
│   ├── unread_count         # Plain text: number of unread
│   ├── 156.yaml             # Individual notifications
│   └── archive/             # Old notifications
├── experiments/
│   ├── exp_001/             # Per-experiment directories
│   │   ├── train.py         # Modified train.py for this experiment
│   │   ├── run.log          # Training output
│   │   ├── metrics.json     # Parsed metrics
│   │   └── checkpoint.pt    # Model checkpoint (if kept)
│   └── results.tsv          # Summary of all experiments
├── crew.pid                 # Daemon PID file
├── crew.sock                # Unix socket for CLI communication
└── crew.log                 # Daemon log file
```

## Error Handling

| Error | Action |
|-------|--------|
| LLM API unreachable | Retry 3x with backoff. If still down, switch to pre-programmed behavior (run experiments from existing queue without LLM reasoning). Notify captain. |
| LLM API rate limited | Slow down. Reduce tokens_per_minute by 50%. Retry after cooldown. |
| LLM daily cost exceeded | Stop using LLM. Switch to pre-programmed behavior. Notify captain. Reset at midnight. |
| GPU out of memory | Reduce batch size by 50%, retry. If still OOM, skip experiment, mark failed. |
| GPU not available | Pause all experiments. Retry every 60s. Notify captain after 5 minutes. |
| Disk full | Stop experiments. Run emergency archive. Notify captain (urgent). |
| train.py syntax error | Mark experiment as failed. Revert train.py to last known good. Move to next experiment. |
| train.py runtime error | Log error. Mark experiment as failed. Move to next. If 3 consecutive failures on same task, pause task and notify captain. |
| Git error | Log error. Retry once. If persistent, disable git commits for this session, notify captain. |
| Config file invalid | Reject change. Keep running with previous config. Notify captain. |
| Network error (RSS) | Skip this check cycle. Retry next cycle. Don't notify (transient). |
| Socket error (CLI) | Restart command listener thread. Log warning. |

## Implementation Checklist for Haiku

```
[ ] Create crew/daemon.py with CrewDaemon class
[ ] Implement config loading (defaults + user overlay)
[ ] Implement state persistence (load/save YAML)
[ ] Implement main loop (check board → work → review → maintain → study)
[ ] Implement heartbeat thread (GPU stats, temp monitoring, disk checks)
[ ] Implement trigger watcher thread (RSS, sensor, schedule, file, command)
[ ] Implement webhook server thread (optional HTTP listener)
[ ] Implement command listener thread (Unix socket)
[ ] Implement startup sequence (PID, daemonize, state recovery)
[ ] Implement shutdown sequence (graceful, persist, cleanup)
[ ] Implement crash recovery (detect stale PID, resume from state)
[ ] Implement error handling for all cases in table above
[ ] Create data/ directory structure on first run
[ ] Write unit tests for state persistence (save → crash → reload)
[ ] Write unit tests for main loop state transitions
[ ] Write integration test: start → add task → complete → stop → restart → verify state
```

## Dependencies

```python
import os
import sys
import time
import signal
import socket
import threading
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timezone

import yaml              # PyYAML (already in project)
# No other external dependencies needed for daemon core
```

## Entry Point

```python
# crew/daemon.py

class CrewDaemon:
    def __init__(self, config_path="data/config.yaml"):
        self.config = self.load_config(config_path)
        self.state = self.load_state()
        self.shutdown_requested = False
        self.threads = []

    def start(self, foreground=False):
        """Main entry point. Called by `crew start`."""
        self.check_existing_instance()
        self.validate_environment()
        if not foreground:
            self.daemonize()
        self.write_pid()
        self.start_threads()
        self.set_mode("starting")
        self.notify("status_change", "info", "Crew started", "Ready for work.")
        try:
            self.main_loop()
        except Exception as e:
            self.notify("alert", "urgent", f"Crew crashed: {e}", str(e))
            raise
        finally:
            self.shutdown()

    def stop(self):
        """Called by `crew stop` via command socket."""
        self.shutdown_requested = True
```
