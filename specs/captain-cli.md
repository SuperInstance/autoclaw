# Captain CLI Specification

**File to implement:** `crew/cli.py`
**Depends on:** `crew/daemon.py` (communicates via Unix socket)
**Entry point:** `crew` command (installed via pyproject.toml scripts)

## Purpose

The captain's interface to the crew. All human interaction goes through this CLI.
It communicates with the running daemon via Unix socket (data/crew.sock).

## Command Reference

### Lifecycle

```
crew start [--foreground] [--verbose] [--config PATH]
    Start the daemon. Runs in background by default.
    --foreground: Run in terminal (useful for debugging)
    --verbose: Debug-level logging
    --config: Path to config.yaml (default: data/config.yaml)

crew stop
    Gracefully stop the daemon. Waits for current experiment to finish.

crew restart
    Stop then start.

crew status
    Show current crew state (mode, task, GPU, queue depth).
    This is the most-used command. Keep output compact.
```

### Task Management

```
crew add "title" [--priority N] [--description "text"] [--urgent]
    Add a task to the board.
    --priority: 1-10 (default: 2 for captain tasks)
    --urgent: Shortcut for --priority 1
    --description: Detailed description (optional)

    Examples:
      crew add "Sweep LR 0.001-0.01 with cosine annealing"
      crew add "Try DEPTH=12" --description "Deeper model might help"
      crew add "Fix the warmup issue" --urgent

crew board
    Show the task board (all queued, active, paused tasks).

crew show N
    Show full details of task #N.

crew hint N "text"
    Add a hint to task #N. Crew considers hints when planning.
    Example: crew hint 42 "I think weight decay matters more here"

crew pause N
    Pause task #N. Crew finishes current experiment, then stops.

crew resume N
    Resume paused task #N.

crew cancel N
    Cancel task #N. Removes from board.

crew priority N P
    Set task #N to priority P (1-10).
    Example: crew priority 43 1  (make urgent)

crew redirect N "new direction"
    Change the focus of task #N while keeping its history.
    Example: crew redirect 42 "Focus only on LR < 0.005"

crew log [--limit N]
    Show recently completed tasks (default: last 10).
```

### Monitoring

```
crew findings [--limit N]
    Show notable findings from recent tasks.

crew knowledge [--tag TAG] [--category CAT]
    Browse the knowledge base.
    --tag: Filter by tag (e.g., "learning-rate")
    --category: Filter by category (e.g., "hyperparameter")

crew study
    Show what the crew is studying (or study queue if idle).

crew gpu
    Show detailed GPU stats.

crew metrics
    Show lifetime metrics (experiments run, tasks completed, best ever, etc.)

crew notifications [--unread] [--limit N]
    Show notifications.
    --unread: Only show unread
    --limit: How many (default: 20)

crew read N
    Mark notification #N as read.

crew read-all
    Mark all notifications as read.
```

### Triggers

```
crew triggers
    List all configured triggers.

crew trigger add --type TYPE --name NAME [options]
    Add a new trigger.
    Example: crew trigger add --type rss --name "arxiv-ml" \
             --url "https://arxiv.org/rss/cs.LG" \
             --keywords "transformer,attention"

crew trigger enable N
    Enable trigger #N.

crew trigger disable N
    Disable trigger #N.

crew trigger remove N
    Remove trigger #N.

crew trigger test N
    Fire trigger #N immediately (for testing).
```

### Configuration

```
crew config
    Show current configuration (with sensitive values masked).

crew config set KEY VALUE
    Set a config value. Hot-reloads without restart.
    Example: crew config set crew.name "Atlas"
    Example: crew config set llm.max_cost_per_day_usd 10.0

crew config edit
    Open data/config.yaml in $EDITOR.
```

## Output Format

### crew status (compact, always fits in terminal)

```
┌─────────────────────────────────────────────┐
│  CREW: Atlas          Uptime: 127h 14m      │
│  Mode: WORKING                              │
│  Task: #42 — LR sweep with cosine annealing │
│  Progress: 14/20 experiments (70%)          │
│  Best so far: val_bpb=1.006 (LR=0.005)     │
│  ETA: ~30 min                               │
│                                             │
│  Queue: 5 tasks | Today: 31 done            │
│  Findings: 3 new | Alerts: 0               │
│  GPU: 96% | 68°C | 41/80 GB                │
└─────────────────────────────────────────────┘
```

When idle:
```
┌─────────────────────────────────────────────┐
│  CREW: Atlas          Uptime: 130h 02m      │
│  Mode: STUDYING                             │
│  Topic: DEPTH × LR interaction effects      │
│  Progress: 4/9 experiments                  │
│                                             │
│  Queue: 0 tasks | Today: 35 done            │
│  GPU: 94% | 65°C | 38/80 GB                │
└─────────────────────────────────────────────┘
```

### crew board

```
 #   Pri  Status   Type           Title
───  ───  ───────  ─────────────  ────────────────────────────────────────
 42   2   ACTIVE   captain_order  LR sweep with cosine annealing [14/20]
 43   4   queued   triggered      Review: 'Scaling Laws for Warmup'
 45   5   queued   follow_up      Test cyclic LR with warm restarts
 46   7   queued   maintenance    Archive old experiments (disk 85%)
 44   9   queued   study          DEPTH × LR interaction effects

 5 tasks on board | 1 active | 4 queued
```

### crew show 42

```
Task #42: LR sweep with cosine annealing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Type:     captain_order
Priority: 2
Status:   ACTIVE (since 2026-03-18 10:35 UTC)
Created:  2026-03-18 10:00 UTC

Description:
  I read the Chinchilla paper and think we should try cosine annealing
  with our current setup.

Experiment:
  Type:    sweep
  Params:  LR=[0.001,0.002,0.003,0.005,0.008,0.01], schedule=cosine
  Budget:  20 experiments × 300s each
  Metric:  val_bpb (lower is better)
  Baseline: 1.018

Progress: 14/20 experiments
  Best: val_bpb=1.006 (LR=0.005, commit a3f2c1d)

Hints:
  [10:30] Start with the middle values, they're more likely to work

Crew Notes:
  [10:45] Starting with LR=0.005 per captain's hint. First 3 experiments complete.
  [11:15] LR=0.005 confirmed best so far. Testing neighbors.

Tags: learning-rate, cosine-annealing
GPU time: 1.2 hours
```

### crew findings

```
Recent Findings
═══════════════

[2026-03-18 12:15] ★ Task #42
  Cosine annealing improves val_bpb by 0.8-1.5% over fixed LR at same base rate.
  Confidence: high (15 experiments)

[2026-03-18 11:45] ★ Task #42
  Weight decay interacts strongly with cosine annealing — WD>0.02 shows 2x benefit.
  Confidence: medium (6 experiments)

[2026-03-17 22:30]   Task #41
  Warmup of 100 steps is critical for stability at LR > 0.003.
  Confidence: very_high (8 experiments)

 3 findings shown (use --limit N for more)
```

### crew notifications

```
Notifications (3 unread)
════════════════════════

 ● #159 [important] 2026-03-18 12:15
   Milestone: New best val_bpb = 0.994 (experiment #312)

 ● #158 [urgent] 2026-03-18 13:00
   ALERT: Disk space at 92% — archiving old experiments

 ● #157 [important] 2026-03-18 11:45
   Finding: weight decay interacts strongly with cosine annealing

   #156 [info] 2026-03-18 10:35
   Status: Started working on task #42

 ● = unread | Use 'crew read N' to mark as read
```

## Communication Protocol

CLI ↔ Daemon communication via Unix socket (data/crew.sock):

```
REQUEST:  JSON line: {"command": "status", "args": {}}
RESPONSE: JSON line: {"status": "ok", "data": {...}}

REQUEST:  {"command": "add_task", "args": {"title": "...", "priority": 2}}
RESPONSE: {"status": "ok", "data": {"task_id": 43}}

REQUEST:  {"command": "stop", "args": {}}
RESPONSE: {"status": "ok", "data": {"message": "Shutting down..."}}
```

If daemon is not running, CLI prints:
```
Crew is not running. Start with: crew start
```

## pyproject.toml Entry

```toml
[project.scripts]
crew = "crew.cli:main"
```

## Implementation Checklist for Haiku

```
[ ] Create crew/cli.py with CLI argument parsing (argparse or click)
[ ] Implement Unix socket client (connect, send JSON, receive JSON)
[ ] Implement all lifecycle commands (start, stop, restart, status)
[ ] Implement all task commands (add, board, show, hint, pause, resume, cancel, priority, redirect, log)
[ ] Implement all monitoring commands (findings, knowledge, study, gpu, metrics, notifications, read)
[ ] Implement all trigger commands (triggers, trigger add/enable/disable/remove/test)
[ ] Implement config commands (config, config set, config edit)
[ ] Implement pretty output formatting (boxes, tables, colors)
[ ] Handle "daemon not running" gracefully for all commands
[ ] Handle socket timeout (daemon busy) with retry
[ ] Add --json flag for machine-readable output on all commands
[ ] Register entry point in pyproject.toml
[ ] Test: crew start → crew status → crew add → crew board → crew stop
[ ] Test: all commands when daemon is not running → helpful error message
```
