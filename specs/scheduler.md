# Scheduler Specification

**File to implement:** `crew/scheduler.py`
**Depends on:** `schemas/task.yaml`, `schemas/crew.yaml`
**Depended on by:** `crew/daemon.py`

## Purpose

The scheduler decides **what to work on next**. It looks at the task board,
applies priority rules, and returns the next task. Simple and deterministic —
no ML, no fancy algorithms. Just priority ordering with a few tiebreakers.

## Core Algorithm

```python
def get_next_task(self) -> Optional[Task]:
    """Return the highest-priority queued task, or None if board is empty."""

    # 1. Get all queued tasks
    queued = [t for t in self.tasks if t.status == "queued"]

    if not queued:
        return None

    # 2. Sort by priority (ascending: 1=highest), then by creation time (oldest first)
    queued.sort(key=lambda t: (t.priority, t.created_at))

    # 3. Return the winner
    return queued[0]
```

That's it. The scheduler is intentionally simple. Complexity lives in how
tasks get their priority, not in the scheduling algorithm.

## Priority Assignment Rules

When a task is created, it gets a default priority based on type:

| Type | Default Priority | Can be overridden by |
|------|-----------------|---------------------|
| captain_order | 2 | Captain (always) |
| triggered | 4 | Captain, trigger config |
| follow_up | 5 | Captain, crew (based on perceived importance) |
| maintenance | 7 | Captain |
| study | 9 | Captain |

**Priority 1** is reserved for captain's URGENT tasks (explicit `crew add --urgent`).
**Priority 10** is reserved for low-value study topics.

## Captain Override

The captain can change any task's priority at any time:

```
crew priority 42 1     # Make task #42 urgent
crew priority 43 8     # Deprioritize task #43
```

This takes effect immediately. If the crew is working on a lower-priority task
and a priority-1 task appears, the crew should:

1. Finish the current experiment (don't abort mid-experiment)
2. Pause the current task
3. Switch to the higher-priority task

## Preemption Rules

```
Current task priority | New task priority | Action
≤ 3 (high)           | 1 (urgent)        | Finish current experiment, switch
≤ 3 (high)           | 2-3               | Don't preempt, run after current
4-6 (medium)         | 1-2               | Finish current experiment, switch
4-6 (medium)         | 3-6               | Don't preempt
7-10 (low)           | 1-3               | Finish current experiment, switch
7-10 (low)           | 4-6               | Finish current experiment, switch
7-10 (low)           | 7-10              | Don't preempt
```

**Rule of thumb:** Preempt if the new task is at least 3 priority levels higher
than current, OR if the new task is priority 1 (urgent).

## Task Lifecycle in Scheduler

```
                 ┌───────────┐
  crew add ────▶│  QUEUED   │◀──── trigger fires
                 └─────┬─────┘      follow-up created
                       │ scheduler picks
                       ▼
                 ┌───────────┐
                 │  ACTIVE   │
                 └─────┬─────┘
                    ┌──┼──┐
                    │  │  │
          ┌─────┐  │  │  │  ┌──────────┐
          │PAUSE│◀─┘  │  └─▶│ CANCELLED│ (crew cancel, captain cancel)
          └──┬──┘     │     └──────────┘
             │        │
             │  ┌─────┴─────┐
             │  │           │
             ▼  ▼           ▼
         ┌────────┐   ┌────────┐
         │COMPLETE│   │ FAILED │
         └────────┘   └───┬────┘
                          │ can retry
                          ▼
                    ┌───────────┐
                    │  QUEUED   │ (re-queued for retry)
                    └───────────┘
```

## Board Management

### Pruning
When task count exceeds `config.tasks.max_queue_depth`:
1. Never prune active, paused, or captain_order tasks
2. Prune oldest study tasks (priority 9-10) first
3. Then oldest maintenance tasks (priority 7-8)
4. Then oldest follow_up tasks (priority 5-6)
5. Then oldest triggered tasks (priority 4-5)
6. Pruned tasks are moved to `data/tasks/completed/` with status=cancelled, reason="pruned"

### Duplicate Detection
Before creating a task, check for duplicates:
- Same title (normalized: lowercase, stripped whitespace)
- Same type
- Status = queued or active
If duplicate found: Don't create new task. Log "skipped duplicate."

### Stale Task Detection
During maintenance, check for stale tasks:
- Queued tasks older than 7 days with priority > 6 → auto-cancel with note
- Paused tasks older than 3 days → notify captain "did you forget about #N?"

## Implementation

```python
# crew/scheduler.py

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
import yaml

@dataclass
class Task:
    """Loaded from data/tasks/{id}.yaml. See schemas/task.yaml for all fields."""
    id: int
    title: str
    type: str
    priority: int
    status: str
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # ... other fields from schema

class Scheduler:
    def __init__(self, tasks_dir: Path):
        self.tasks_dir = tasks_dir
        self.tasks: List[Task] = []
        self.next_id: int = 1
        self.load_tasks()

    def load_tasks(self):
        """Load all tasks from YAML files in tasks_dir."""
        self.tasks = []
        for f in self.tasks_dir.glob("*.yaml"):
            if f.name == "ACTIVE":
                continue
            task_data = yaml.safe_load(f.read_text())
            self.tasks.append(Task(**task_data))
        if self.tasks:
            self.next_id = max(t.id for t in self.tasks) + 1

    def get_next_task(self) -> Optional[Task]:
        """Return highest-priority queued task."""
        queued = [t for t in self.tasks if t.status == "queued"]
        if not queued:
            return None
        queued.sort(key=lambda t: (t.priority, t.created_at))
        return queued[0]

    def add_task(self, title: str, type: str = "captain_order",
                 priority: int = None, description: str = "",
                 **kwargs) -> Task:
        """Create a new task and add to board."""
        if priority is None:
            priority = self.default_priority(type)
        if self.is_duplicate(title, type):
            return None  # Skip duplicate
        task = Task(
            id=self.next_id,
            title=title,
            type=type,
            priority=priority,
            status="queued",
            description=description,
            **kwargs
        )
        self.next_id += 1
        self.save_task(task)
        self.tasks.append(task)
        self.prune_if_needed()
        return task

    def default_priority(self, type: str) -> int:
        return {
            "captain_order": 2,
            "triggered": 4,
            "follow_up": 5,
            "maintenance": 7,
            "study": 9,
        }.get(type, 5)

    def activate_task(self, task: Task):
        """Move task from queued to active."""
        task.status = "active"
        task.started_at = datetime.now(timezone.utc)
        self.save_task(task)
        # Update ACTIVE symlink
        active_link = self.tasks_dir / "ACTIVE"
        active_link.unlink(missing_ok=True)
        active_link.symlink_to(f"{task.id}.yaml")

    def complete_task(self, task: Task, results: dict):
        """Mark task as completed with results."""
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        task.results = results
        # Move to completed/
        src = self.tasks_dir / f"{task.id}.yaml"
        dst = self.tasks_dir / "completed" / f"{task.id}.yaml"
        self.save_task(task, dst)
        src.unlink(missing_ok=True)
        # Remove ACTIVE symlink
        (self.tasks_dir / "ACTIVE").unlink(missing_ok=True)

    def pause_task(self, task: Task):
        """Pause task (captain requested or preempted)."""
        task.status = "paused"
        task.paused_at = datetime.now(timezone.utc)
        self.save_task(task)
        (self.tasks_dir / "ACTIVE").unlink(missing_ok=True)

    def should_preempt(self, current_priority: int, new_priority: int) -> bool:
        """Check if new task should preempt current work."""
        if new_priority == 1:
            return True  # Urgent always preempts
        return (current_priority - new_priority) >= 3

    def is_duplicate(self, title: str, type: str) -> bool:
        normalized = title.strip().lower()
        for t in self.tasks:
            if t.status in ("queued", "active"):
                if t.title.strip().lower() == normalized and t.type == type:
                    return True
        return False

    def prune_if_needed(self, max_depth: int = 50):
        """Remove lowest-priority tasks if board is too full."""
        queued = [t for t in self.tasks if t.status == "queued"]
        if len(queued) <= max_depth:
            return
        # Sort by priority descending (lowest priority first = candidates for pruning)
        queued.sort(key=lambda t: (-t.priority, t.created_at))
        while len(queued) > max_depth:
            victim = queued.pop(0)
            if victim.type == "captain_order":
                continue  # Never prune captain's tasks
            victim.status = "cancelled"
            self.complete_task(victim, {"summary": "Pruned: board full"})

    def save_task(self, task: Task, path: Path = None):
        """Persist task to YAML file."""
        if path is None:
            path = self.tasks_dir / f"{task.id}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(task.__dict__, default_flow_style=False))

    # --- Board queries (used by CLI) ---

    def get_board(self) -> List[Task]:
        """All non-completed tasks, sorted by priority."""
        active = [t for t in self.tasks if t.status in ("queued", "active", "paused")]
        active.sort(key=lambda t: (t.priority, t.created_at))
        return active

    def get_active(self) -> Optional[Task]:
        """Currently active task."""
        for t in self.tasks:
            if t.status == "active":
                return t
        return None

    def get_task(self, task_id: int) -> Optional[Task]:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def get_completed(self, limit: int = 20) -> List[Task]:
        """Recent completed tasks."""
        completed = [t for t in self.tasks if t.status == "completed"]
        completed.sort(key=lambda t: t.completed_at or t.created_at, reverse=True)
        return completed[:limit]
```

## Implementation Checklist for Haiku

```
[ ] Create crew/scheduler.py with Scheduler class
[ ] Implement Task dataclass matching schemas/task.yaml
[ ] Implement load_tasks() from YAML files
[ ] Implement get_next_task() with priority + creation time ordering
[ ] Implement add_task() with default priorities and duplicate detection
[ ] Implement activate_task() with ACTIVE symlink
[ ] Implement complete_task() with move to completed/
[ ] Implement pause_task()
[ ] Implement should_preempt() for priority comparison
[ ] Implement prune_if_needed() respecting captain_order protection
[ ] Implement board query methods (get_board, get_active, get_completed)
[ ] Implement save_task() YAML persistence
[ ] Test: add 3 tasks, verify get_next_task returns highest priority
[ ] Test: add duplicate, verify it's rejected
[ ] Test: fill board to max_depth+5, verify pruning removes correct tasks
[ ] Test: preemption logic for all priority combinations
[ ] Test: persist → reload → verify state matches
```
