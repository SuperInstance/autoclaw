# Specs: Implementation Guides for the Crew System

These specs define **how the system behaves**. Each spec maps to one Python
module. They contain algorithms, state machines, API definitions, error handling,
and implementation checklists.

## Files

| Spec | Implements | Python Module |
|------|-----------|---------------|
| [daemon.md](daemon.md) | The always-on process | `crew/daemon.py` |
| [scheduler.md](scheduler.md) | Task scheduling algorithm | `crew/scheduler.py` |
| [crew-brain.md](crew-brain.md) | LLM-powered decision engine | `crew/brain.py` |
| [captain-cli.md](captain-cli.md) | Human interface (CLI) | `crew/cli.py` |
| [experiment-runner.md](experiment-runner.md) | GPU experiment execution | `crew/runner.py` |

## Implementation Order

Build in this order (each depends on the ones before it):

```
1. crew/scheduler.py     ← Pure Python, no dependencies. Start here.
2. crew/runner.py        ← Needs train.py and git. Test with real experiments.
3. crew/brain.py         ← Needs LLM API. Has fallback mode without LLM.
4. crew/daemon.py        ← Orchestrates everything. Build last.
5. crew/cli.py           ← Talks to daemon via socket. Build alongside daemon.
```

## Module Dependency Graph

```
crew/cli.py ──socket──▶ crew/daemon.py
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              crew/scheduler  crew/brain  crew/runner
                    │              │         │
                    ▼              ▼         ▼
              schemas/task    LLM API    train.py
              (YAML files)               prepare.py
```

## How to Use These Specs

Each spec contains:
1. **Purpose**: What this module does
2. **Algorithm/Process**: Step-by-step behavior
3. **Code Skeleton**: Python classes and methods
4. **Error Handling**: What can go wrong and how to handle it
5. **Implementation Checklist**: Specific tasks with test criteria

### For Haiku (or any implementer):

1. Read the spec top to bottom
2. Create the Python file
3. Implement each method from the code skeleton
4. Follow the error handling table
5. Check off each item in the implementation checklist
6. Run the specified tests

## Testing Strategy

```
Unit Tests (per module):
  crew/scheduler.py → test_scheduler.py
    - Priority ordering
    - Duplicate detection
    - Board pruning
    - State persistence

  crew/runner.py → test_runner.py
    - Experiment lifecycle (backup → modify → run → restore)
    - Syntax validation
    - Metrics parsing
    - Git commit creation

  crew/brain.py → test_brain.py
    - LLM prompt generation
    - JSON response parsing
    - Fallback mode (no LLM)
    - Token budget management

Integration Tests:
  test_daemon.py
    - Start → add task → run experiments → complete → stop
    - Crash recovery (kill -9 → restart → verify state)
    - Trigger firing → task creation
    - CLI commands → correct responses

  test_e2e.py
    - Full cycle: start crew → add LR sweep → wait for completion →
      verify results.tsv → check notifications → stop crew
```

## Architecture Summary

```
Captain (Human)
    │
    │ crew add/status/hint/...
    ▼
┌────────────────────────────────────┐
│           crew/cli.py              │ ← Captain's interface
└────────────┬───────────────────────┘
             │ Unix socket
             ▼
┌────────────────────────────────────┐
│          crew/daemon.py            │ ← Always-on process
│                                    │
│  Main Loop:                        │
│   1. Check board → work            │
│   2. Check triggers                │
│   3. Maintain                      │
│   4. Study                         │
│                                    │
│  Threads:                          │
│   - Heartbeat (GPU stats)          │
│   - Trigger watcher                │
│   - Webhook server                 │
│   - Command listener               │
└────┬──────────┬──────────┬─────────┘
     │          │          │
     ▼          ▼          ▼
┌─────────┐ ┌──────┐ ┌────────┐
│scheduler│ │brain │ │runner  │
│         │ │      │ │        │
│ Task    │ │ LLM  │ │ GPU    │
│ board   │ │ API  │ │ train  │
│ YAML    │ │      │ │ .py    │
└─────────┘ └──────┘ └────────┘
```
