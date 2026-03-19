# CudaClaw – Roadmap & Architecture Schemas
**GPU-Accelerated Multi-Agent Swarm for AutoClaw**
*Version 1.0 · Branch `claude/audit-schemas-e91aS`*

---

## What Is CudaClaw?

CudaClaw is a parallel, role-differentiated multi-agent swarm layer built on top of AutoClaw.
Where a standard OpenClaw session runs one agent at a time, CudaClaw spins up a fleet of
GPU-backed instances with distinct roles, coordinated by a **Foreman**, guarded by a
**CompletionTester**, and reportable back to the directing OpenClaw session.

```
OpenClaw (director)
    │
    │  spawn_swarm(task, preset)
    ▼
CudaClaw Foreman ──► distributes subtasks ──► Worker-1 (GPU / vLLM)
    │                                    ──► Worker-2 (GPU / vLLM)
    │                                    ──► Worker-N (GPU / cloud)
    │
    ├──► CompletionTester (polls: "is job done?")
    │         │ yes → release resources
    │
    └──► progress_report(%) ──► OpenClaw ──► User
```

---

## Core Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Parallel by nature** | Every role runs as an independent instance; no serial bottlenecks |
| **Role separation** | Foreman ≠ Worker ≠ Tester – prevents context pollution |
| **Loop prevention** | Foreman tracks iteration counts, detects duplicates, kills stalled workers |
| **Finite-task awareness** | CompletionTester can declare done and trigger clean shutdown |
| **OpenClaw-composable** | Any OpenClaw session can vibe-code a swarm with one command |
| **Backend-agnostic** | vLLM (local GPU), cloud API, or mixed per-instance |

---

## Architecture Layers

```
Layer 0 – Hardware
  ├── NVIDIA GPU(s)  →  vLLM inference server(s)  →  OpenAI-compatible API
  └── Cloud API      →  Anthropic / OpenAI / Groq / Together / etc.

Layer 1 – Instance Management  (cudaclaw_wizard.py)
  ├── ApiKeyManager        – stores & rotates provider keys
  ├── McpConfigurator      – registers MCP tool servers per instance
  ├── SwarmConfigurator    – builds instance manifest from presets
  └── VllmSetup            – generates per-GPU launch scripts

Layer 2 – Agent Roles  (crew/agents/)
  ├── ForemanAgent          – task distribution, loop detection, reporting
  ├── CompletionTesterAgent – finite-task validation, resource release signal
  ├── WorkerAgent           – general parallel execution
  ├── ResearcherAgent       – GPU-accelerated web search (existing)
  ├── CoderAgent            – code generation / review
  ├── SynthesizerAgent      – knowledge distillation (existing Distiller)
  └── ValidatorAgent        – output quality gating

Layer 3 – Communication  (crew/messaging/)
  └── MessageBus  – SQLite pub/sub (existing)
      Topics added: foreman.*, worker.*, tester.*, openclaw.*

Layer 4 – OpenClaw Integration
  ├── openclaw_manifest.json  – machine-readable swarm capabilities
  └── Progress JSON lines      – stdout stream OpenClaw parses in real time
```

---

## Schema Reference

### 1. Swarm Configuration  (`schemas/cudaclaw_swarm.json`)

The top-level config written by the wizard and read at runtime.

```jsonc
{
  "version": "1.0.0",
  "swarm_name": "my-cudaclaw-swarm",
  "instances": [
    {
      "id": "foreman",
      "role": "foreman",           // see Role Definitions below
      "backend": "cloud",          // "vllm" | "cloud"
      "model": "claude-sonnet-4-6",
      "api_provider": "anthropic", // null for vllm
      "vllm_endpoint": null,
      "capabilities": ["task_distribution", "loop_detection", "progress_reporting"]
    },
    {
      "id": "tester",
      "role": "completion_tester",
      "backend": "cloud",
      "model": "claude-haiku-4-5-20251001",
      "api_provider": "anthropic",
      "capabilities": ["task_validation", "completion_detection"]
    },
    {
      "id": "worker-1",
      "role": "worker",
      "backend": "vllm",
      "model": "meta-llama/Meta-Llama-3-8B-Instruct",
      "vllm_endpoint": "http://localhost:8000/v1",
      "capabilities": ["general_tasks", "parallel_execution"]
    }
  ],
  "foreman": {
    "instance_id": "foreman",
    "model": "claude-sonnet-4-6",
    "report_to_openclaw": true,
    "report_interval_sec": 30
  },
  "loop_detection": {
    "enabled": true,
    "max_iterations_per_task": 50,
    "stall_timeout_seconds": 300,
    "recursion_depth_limit": 10,
    "duplicate_output_threshold": 0.95
  },
  "resource_management": {
    "auto_release_on_completion": true,
    "idle_shutdown_seconds": 120
  }
}
```

Full JSON Schema: `schemas/cudaclaw_swarm.json`

---

### 2. Progress Report  (`schemas/cudaclaw_progress_report.json`)

Emitted by the Foreman at regular intervals as JSON lines on stdout.
OpenClaw reads these to update the user and detect completion.

```jsonc
{
  "swarm_id": "my-cudaclaw-swarm",
  "task_id": "task-abc123",
  "report_seq": 7,
  "timestamp": "2026-03-19T14:22:00Z",
  "status": "running",           // initializing|running|stalled|loop_detected|complete|error|releasing
  "progress_pct": 62,
  "message": "4/7 subtasks complete. Workers active: 3/4.",
  "completed_subtasks": [
    { "id": "sub-1", "description": "Fetch paper abstracts", "assigned_to": "worker-1" }
  ],
  "pending_subtasks": [
    { "id": "sub-5", "description": "Synthesize findings", "assigned_to": "worker-3" }
  ],
  "worker_states": {
    "worker-1": { "status": "idle",    "tasks_completed": 2 },
    "worker-2": { "status": "working", "current_task_id": "sub-4" },
    "worker-3": { "status": "working", "current_task_id": "sub-5" }
  },
  "loop_detection": { "loops_detected": 0, "workers_killed": [] }
}
```

Full JSON Schema: `schemas/cudaclaw_progress_report.json`

---

### 3. OpenClaw Manifest  (`~/.cudaclaw/openclaw_manifest.json`)

Auto-generated by the wizard. OpenClaw reads this to understand
what the local CudaClaw installation can do.

```jsonc
{
  "cudaclaw_version": "1.0.0",
  "capabilities": {
    "gpu_acceleration": true,
    "parallel_workers": 4,
    "cloud_fallback": true,
    "finite_task_completion": true,
    "loop_detection": true
  },
  "swarm_presets": { ... },
  "setup_commands": {
    "launch_swarm": "python3 cudaclaw_wizard.py --launch",
    "status":       "python3 cudaclaw_wizard.py --status"
  },
  "openclaw_integration": {
    "spawn_swarm_for_task": {
      "command": "python3 cudaclaw_wizard.py --agent-mode --preset {preset} --task '{task}'"
    }
  }
}
```

---

## Role Definitions

| Role | Count | Backend | Responsibilities |
|------|-------|---------|-----------------|
| `foreman` | 1 | Cloud (smart model) | Break job → subtasks, assign to workers, detect loops, report progress to OpenClaw |
| `completion_tester` | 1 | Cloud | Poll task list, declare done, trigger resource release |
| `worker` | 1–32 | vLLM or Cloud | Execute subtasks in parallel |
| `researcher` | 1–8 | vLLM or Cloud | GPU-accelerated web search + synthesis |
| `coder` | 1–8 | vLLM | Code generation, review, debugging |
| `synthesizer` | 1–4 | vLLM | Knowledge distillation, summarization |
| `validator` | 1–4 | Cloud | Output quality gating, fact-checking |

---

## Swarm Presets

| Preset | Description | Instances |
|--------|-------------|-----------|
| `minimal` | 1 foreman + 1 worker | 2 |
| `swarm_4worker` | Default GPU swarm | 6 |
| `research_fleet` | 4 researchers + 2 synthesizers | 8 |
| `code_squad` | 4 coders + 2 validators | 8 |
| `cloud_only` | All-cloud, no GPU required | 6 |

---

## Foreman Behaviour Specification

### Task Decomposition
```
receive_task(description, task_id)
  → call LLM to break into N subtasks
  → assign each subtask to capable worker(s)
  → track in task_board: {subtask_id → worker_id → status}
```

### Loop Detection
```
every 30s:
  for each worker:
    if iterations > max_iterations_per_task:  kill + reassign
    if time_since_last_output > stall_timeout: kill + reassign
    if output_similarity(last_3_outputs) > 0.95: kill + reassign
    if recursion_depth > limit: kill + escalate to OpenClaw
```

### Progress Reporting
```
every report_interval_sec:
  emit JSON line to stdout:
    { status, progress_pct, message, worker_states, ... }
OpenClaw reads stdout and forwards to user on request
```

### Resource Release (finite tasks)
```
CompletionTester signals: task_complete = true
Foreman:
  1. Send final progress_report (status=complete, progress_pct=100)
  2. Signal all workers to finish current subtask and idle
  3. Optionally shutdown vLLM processes (auto_release_on_completion)
  4. Write completion receipt to ~/.cudaclaw/completed/{task_id}.json
```

---

## Roadmap: Integration Phases

### Phase 1 – Foundation (This PR) ✅
- [x] `cudaclaw_wizard.py` – installation wizard
- [x] `schemas/cudaclaw_swarm.json` – swarm config schema
- [x] `schemas/cudaclaw_progress_report.json` – reporting schema
- [x] README.md – OpenClaw self-install section

### Phase 2 – Agent Role Implementation
- [ ] `crew/agents/foreman.py` – ForemanAgent class
  - Subtask decomposition via LLM
  - Worker assignment by capability
  - Loop detection engine
  - Progress report emitter
- [ ] `crew/agents/completion_tester.py` – CompletionTesterAgent
  - Periodic task-board polling
  - Completion declaration + resource release signal
- [ ] Extend `crew/agents/base.py` – add `role`, `backend`, `instance_id` fields

### Phase 3 – vLLM Integration
- [ ] `crew/backends/vllm.py` – vLLM OpenAI-compatible client wrapper
- [ ] `crew/backends/cloud.py` – unified cloud API client (Anthropic, OpenAI, Groq…)
- [ ] `crew/backends/router.py` – auto-route by backend field in instance config
- [ ] Per-instance model loading at startup (batch, not sequential)

### Phase 4 – MessageBus Extensions
- [ ] Add topics: `foreman.assign`, `foreman.report`, `worker.complete`,
  `tester.check`, `tester.complete`, `openclaw.progress`
- [ ] Add `MessageBus.subscribe_pattern()` for glob topic matching
- [ ] Durable message delivery for worker crash recovery

### Phase 5 – OpenClaw Integration Protocol
- [ ] `crew/openclaw_bridge.py` – reads `openclaw_manifest.json`, exposes:
  - `spawn_swarm(task, preset) → swarm_id`
  - `get_progress(swarm_id) → ProgressReport`
  - `release_swarm(swarm_id)`
- [ ] Standardized JSON-lines stdout protocol for progress streaming
- [ ] HTTP callback server option for long-running tasks

### Phase 6 – CLI Extensions (`crew/cli.py`)
- [ ] `crew swarm start --preset swarm_4worker --task "..."`
- [ ] `crew swarm status [swarm_id]`
- [ ] `crew swarm add-worker --role coder`
- [ ] `crew swarm stop [swarm_id]`
- [ ] `crew swarm logs [instance_id]`

### Phase 7 – Monitoring & Observability
- [ ] Per-instance metric emission into `crew/monitoring.py`
- [ ] GPU utilization tracking (nvidia-smi polling)
- [ ] Loop detection alerts surfaced to `crew/healthcheck.py`
- [ ] Grafana/Prometheus export endpoint (optional)

### Phase 8 – Production Hardening
- [ ] vLLM process supervision (auto-restart on OOM)
- [ ] API key rotation mid-swarm
- [ ] Graceful degradation (GPU → cloud fallback on CUDA error)
- [ ] Swarm state persistence (resume after crash)

---

## File Plan (New Files)

```
crew/
├── agents/
│   ├── foreman.py                 # Phase 2
│   └── completion_tester.py       # Phase 2
├── backends/
│   ├── __init__.py                # Phase 3
│   ├── vllm.py                    # Phase 3
│   ├── cloud.py                   # Phase 3
│   └── router.py                  # Phase 3
└── openclaw_bridge.py             # Phase 5

schemas/
├── cudaclaw_swarm.json            # ✅ Done
└── cudaclaw_progress_report.json  # ✅ Done

cudaclaw_wizard.py                 # ✅ Done
CUDACLAW_ROADMAP.md                # ✅ Done (this file)
```

---

## OpenClaw Vibe-Coding Guide (Quick Reference)

When an OpenClaw session is given a large parallel task, it can:

```python
# 1. Check CudaClaw availability
import subprocess, json
manifest = json.loads(subprocess.check_output(
    ["python3", "cudaclaw_wizard.py", "--verify-only", "--json"]))

# 2. Launch a swarm
subprocess.Popen([
    "python3", "cudaclaw_wizard.py",
    "--agent-mode", "--preset", "swarm_4worker",
    "--api-key", f"anthropic:{ANTHROPIC_API_KEY}",
    "--worker-count", "4"
])

# 3. Read foreman progress reports (JSON lines on stdout)
for line in process.stdout:
    report = json.loads(line)
    print(f"Progress: {report['progress_pct']}% – {report['message']}")
    if report['status'] == 'complete':
        break
```

---

## Key Configuration Files

| File | Purpose |
|------|---------|
| `~/.cudaclaw/api_keys.json` | All provider API keys (chmod 600) |
| `~/.cudaclaw/mcp_servers.json` | MCP server endpoints |
| `~/.cudaclaw/swarm_config.json` | Active swarm configuration |
| `~/.cudaclaw/openclaw_manifest.json` | Machine-readable capabilities for OpenClaw |
| `~/.cudaclaw/start_vllm.sh` | Auto-generated vLLM launch script |
| `~/.cudaclaw/instances/*.json` | Per-instance config files |
| `~/.cudaclaw/completed/*.json` | Completion receipts for finished tasks |

---

*CudaClaw is parallel by nature. Scale your claws.*
