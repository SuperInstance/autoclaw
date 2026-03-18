# Schemas: Data Models for the Crew System

These schemas define every data structure in the system. They are the **source
of truth** for what data looks like. Implementation code must match these schemas.

## Files

### Core Schemas (Phase 1–4, implemented)

| Schema | What it defines | Key types |
|--------|----------------|-----------|
| [task.yaml](task.yaml) | Work items on the task board | Task, ExperimentSpec, TaskResults |
| [crew.yaml](crew.yaml) | Crew member state and lifecycle | CrewState, StudyState, GPU stats |
| [agent.yaml](agent.yaml) | Multi-agent pool, roles, messages | Agent, Message, AgentPool, PayloadSchemas |
| [trigger.yaml](trigger.yaml) | External event watchers | Trigger, TriggerSource, TriggerFilter |
| [notification.yaml](notification.yaml) | Crew → captain messages | Notification types and severity |
| [knowledge.yaml](knowledge.yaml) | Crew's accumulated learning | KnowledgeEntry, evidence, confidence |
| [knowledge_lifecycle.yaml](knowledge_lifecycle.yaml) | Storage tiers, GC, scoring | StorageTier, GCRules, LifecycleScore |
| [hardware_profile.yaml](hardware_profile.yaml) | Device profiles, inference backends | HardwareProfile, InferenceBackend, Scaler |
| [cloudflare.yaml](cloudflare.yaml) | CF services, budgets, credit gaming | CFService, CreditBudget, BurnStrategy |
| [config.yaml](config.yaml) | System configuration | LLM, GPU, experiments, tasks, triggers, storage |

### Extended Schemas (Phase 5+, design complete)

| Schema | What it defines | Key types | Why it matters |
|--------|----------------|-----------|----------------|
| [training_data.yaml](training_data.yaml) | LoRA training data generation & curation | TrainingExample, Dataset, QualityControl | Crew's primary output for fine-tuning specialist models |
| [context_handoff.yaml](context_handoff.yaml) | Infinite-context operation via Baton pattern | ContextHandoff, DecisionRationale, SkillExtraction | Enables tasks that run hours/days without losing thread |
| [llm_router.yaml](llm_router.yaml) | Intelligent LLM routing across backends | LLMBackend, RoutingRule, CascadeRouter | Cost optimization + fallback resilience |
| [adaptive_scheduler.yaml](adaptive_scheduler.yaml) | Bayesian adaptive task & agent scheduling | BanditArm, ThompsonSampling, InstructionalDelta | Crew learns which configurations produce best outcomes |
| [flowstate.yaml](flowstate.yaml) | Exploratory sandbox mode | FlowstateSession, PromotionCandidate, ExplorationLog | Radical exploration without contaminating primary knowledge |

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
│   ├── bandit_state.yaml    # Adaptive scheduler state (adaptive_scheduler.yaml)
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
├── training/
│   └── {dataset_tag}/       # Training datasets (training_data.yaml schema)
│       ├── meta.yaml        # Dataset metadata
│       ├── raw/             # All generated examples
│       ├── curated/         # Quality-filtered examples
│       └── lora.jsonl       # LoRA-ready export
├── handoffs/
│   └── {task_id}/           # Context handoffs (context_handoff.yaml schema)
│       ├── CURRENT -> gen003.yaml
│       ├── gen001.yaml
│       └── gen003.yaml
├── flowstate/
│   ├── {session_id}/        # Active flowstate sessions (flowstate.yaml schema)
│   │   ├── session.yaml     # Session metadata
│   │   ├── knowledge.yaml   # Sandbox knowledge entries
│   │   └── experiments/     # Flowstate experiments
│   └── archive/             # Completed sessions (compressed)
├── llm_routing.log          # LLM routing decisions log
├── crew.pid                 # Daemon PID
├── crew.sock                # Unix socket for CLI
└── crew.log                 # Daemon log
```
