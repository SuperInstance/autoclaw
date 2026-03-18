# Schemas: Data Models for the Crew System

These schemas define every data structure in the system. They are the **source
of truth** for what data looks like. Implementation code must match these schemas.

## Files

| Schema | What it defines | Key types |
|--------|----------------|-----------|
| [task.yaml](task.yaml) | Work items on the task board | Task, ExperimentSpec, TaskResults |
| [crew.yaml](crew.yaml) | Crew member state and lifecycle | CrewState, StudyState, GPU stats |
| [trigger.yaml](trigger.yaml) | External event watchers | Trigger, TriggerSource, TriggerFilter |
| [notification.yaml](notification.yaml) | Crew → captain messages | Notification types and severity |
| [knowledge.yaml](knowledge.yaml) | Crew's accumulated learning | KnowledgeEntry, evidence, confidence |
| [config.yaml](config.yaml) | System configuration | LLM, GPU, experiments, tasks, triggers, storage |

## How to Read These

Each schema file contains:
1. **Field definitions** with types, defaults, and descriptions
2. **State transitions** (where applicable)
3. **Implementation notes** for the developer
4. **Examples** of real data instances

## For Implementers (Haiku)

1. Read a schema file
2. Create the corresponding Python dataclass or dict structure
3. Implement YAML serialization (load/save)
4. Follow the validation rules in each field
5. Use the examples as test fixtures

## Data Directory Structure

All data lives under `data/`:

```
data/
├── config.yaml              # User configuration
├── crew/
│   ├── state.yaml           # Crew state (crew.yaml schema)
│   ├── knowledge.yaml       # Knowledge base (knowledge.yaml schema)
│   ├── study_queue.yaml     # Study topics
│   └── heartbeat            # Last heartbeat (plain text timestamp)
├── tasks/
│   ├── ACTIVE -> 42.yaml    # Symlink to active task
│   ├── 42.yaml              # Task files (task.yaml schema)
│   └── completed/           # Finished tasks
├── triggers/
│   └── 1.yaml               # Trigger configs (trigger.yaml schema)
├── notifications/
│   ├── feed.log             # Append-only log
│   ├── unread_count         # Plain text integer
│   └── 156.yaml             # Notifications (notification.yaml schema)
├── experiments/
│   ├── results.tsv          # All experiment results
│   ├── exp_0001/            # Per-experiment data
│   └── .counter             # Next experiment number
├── crew.pid                 # Daemon PID
├── crew.sock                # Unix socket for CLI
└── crew.log                 # Daemon log
```
