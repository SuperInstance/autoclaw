# AutoCrew Swarm Architecture

**Version:** 2.0
**Status:** Design + Schema Phase
**Goal:** Transform single-GPU crew into a distributed, collaborative, self-improving swarm

---

## Philosophy

> "A single crew member is useful. A crew that teaches each other, challenges each other's assumptions, and builds shared understanding is transformative."

The swarm extends the existing crew model:
- **Before:** One autonomous GPU agent working a task board
- **After:** Multiple specialized agents collaborating, with shared knowledge, Cloudflare-distributed compute, and hardware-aware scaling

The swarm remains *captain-steerable* — humans guide without micromanaging. All human interaction still goes through `crew` CLI.

---

## System Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 0: Human Interface                                           │
│  crew CLI  →  Unix Socket  →  Daemon Orchestrator                  │
└─────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 1: Hardware Profile                                          │
│  Auto-detect device class → select runtime profile                 │
│  nano | laptop | workstation | multi-gpu | cloud                   │
└─────────────────────────────────────────────────────────────────────┘
              │ Profile dictates: concurrency, model size, backends
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 2: Agent Pool (Multi-Agent Collaboration)                   │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │Researcher│  │ Teacher  │  │  Critic  │  │Distiller │          │
│  │          │  │          │  │          │  │          │          │
│  │web search│  │training  │  │devil's   │  │knowledge │          │
│  │LLM calls │  │data gen  │  │advocate  │  │synthesis │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       │              │              │              │               │
│       └──────────────┴──────────────┴──────────────┘               │
│                              │                                      │
│                    Message Bus (SQLite)                             │
└─────────────────────────────────────────────────────────────────────┘
              │ Agents produce Knowledge + Training Data
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 3: Knowledge Store (Tiered Storage)                         │
│                                                                     │
│  HOT  → in-memory cache (last 24h, < 1000 entries)                │
│  WARM  → SQLite / D1     (last 30d, < 100k entries)               │
│  COLD  → R2 / local disk (older, compressed)                       │
│  ARCHIVE → summarized, minimal footprint                           │
│  DELETED → final summarization, then purge                         │
│                                                                     │
│  + Vector embeddings for semantic retrieval                        │
│  + LoRA datasets for fine-tuning specialists                       │
└─────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 4: Cloudflare Free Tier (Credit Gaming)                     │
│                                                                     │
│  Workers AI     10k neurons/day  → Low-cost inference              │
│  D1 Database    25M reads/day    → Knowledge warm store            │
│  R2 Storage     10GB/1M ops/mo   → Cold knowledge archive          │
│  KV Store       100k reads/day   → Fast lookups, counters          │
│  Pages          Unlimited        → Status dashboard                │
│                                                                     │
│  Credit Manager: Track budgets → schedule by priority + expiry    │
│  End-of-day: Burn remaining credits on batch image/audio gen       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agent Roles

### Researcher Agent
**Purpose:** Gather information from external sources
**Inputs:** Research topic (from task, study session, or trigger)
**Outputs:** Raw facts, articles, code samples, papers
**Tools:** Web search (DuckDuckGo/SerpAPI), LLM API calls, RSS feeds
**Can call teachers:** Yes — asks teacher LLMs to explain concepts
**Priority claim on Cloudflare:** Medium (Workers AI for summarization)

```yaml
role: researcher
capabilities:
  - web_search
  - rss_fetch
  - llm_query       # "Explain X to me like I'm training a model on it"
  - code_search     # Search GitHub/HuggingFace
  - paper_fetch     # Download arxiv PDFs
outputs:
  - raw_research    # Unprocessed findings
  - source_list     # URLs and citations
```

### Teacher Agent
**Purpose:** Generate training data from existing knowledge
**Inputs:** Knowledge topic + sample documents
**Outputs:** Q&A pairs, instruction-following examples, dialogue data
**Persona:** Calls LLM APIs in "teacher mode" — generate explanations at varying levels
**Priority claim on Cloudflare:** High (this is the primary use of Workers AI)

```yaml
role: teacher
capabilities:
  - qa_generation         # Generate Q&A from source text
  - instruction_tuning    # Create (instruction, response) pairs
  - socratic_dialogue     # Multi-turn Q&A exploration
  - explanation_levels    # Generate same topic at 5 different depths
  - adversarial_examples  # Tricky questions to test understanding
outputs:
  - training_examples     # JSONL for fine-tuning
  - instruction_pairs     # (prompt, completion) format
  - lora_dataset          # Formatted for LoRA training
```

### Critic Agent
**Purpose:** Challenge assumptions, find weaknesses, improve quality
**Inputs:** Training data, knowledge entries, experiment conclusions
**Outputs:** Challenges, alternative hypotheses, quality scores
**Persona:** Devil's advocate — always asks "but what if..."
**Priority claim on Cloudflare:** Low (spot-checking only)

```yaml
role: critic
capabilities:
  - fact_check            # Verify claims against multiple sources
  - devil_advocate        # Generate counter-arguments
  - consistency_check     # Find contradictions in knowledge base
  - quality_score         # Rate training examples by quality
  - edge_case_finder      # What scenarios would break this?
outputs:
  - challenges            # Counter-arguments and critiques
  - quality_ratings       # Numerical quality scores
  - contradictions        # Found inconsistencies
```

### Distiller Agent
**Purpose:** Synthesize knowledge from multiple sources into coherent understanding
**Inputs:** Researcher outputs + Critic challenges + raw experiment results
**Outputs:** Clean knowledge entries, summaries, structured insights
**Priority claim on Cloudflare:** Medium-High (primary consumer of stored data)

```yaml
role: distiller
capabilities:
  - synthesis             # Combine multiple sources into coherent summary
  - conflict_resolution   # When sources disagree, find truth
  - knowledge_extraction  # Pull structured facts from prose
  - compression           # Summarize long content to key points
  - embedding_generation  # Create vector embeddings for retrieval
outputs:
  - knowledge_entries     # Structured knowledge (extends existing schema)
  - summaries             # Compressed representations
  - embeddings            # Vector representations for search
```

### Specialist Agent (Inference)
**Purpose:** Fast, focused inference using fine-tuned knowledge
**When:** After LoRA training, provides domain-specific answers
**Hardware:** Uses quantized GGUF models on Jetson, fp16 on GPU, or API on cloud
**Priority claim on Cloudflare:** On-demand (called when needed)

```yaml
role: specialist
capabilities:
  - domain_inference      # Fast answers using specialized model
  - uncertainty_estimate  # Rate confidence of answer
  - fallback_to_llm       # When uncertain, escalate to full API
outputs:
  - answers               # Domain-specific responses
  - confidence_scores     # How certain the specialist is
```

---

## Message Bus Protocol

All agents communicate via a SQLite-backed durable message bus.

```
Message Format:
  id:          auto-increment
  from_agent:  researcher_1 | teacher_1 | critic_1 | distiller_1 | ...
  to_agent:    specific ID | "broadcast" | "any_researcher"
  type:        task_request | result | challenge | knowledge | heartbeat
  priority:    1-10 (same scale as task board)
  content:     JSON payload (type-specific)
  created_at:  timestamp
  delivered:   boolean
  expires_at:  optional TTL

Message Types:
  task_request:  Assign work to another agent
  result:        Deliver findings
  challenge:     Critic challenging a result
  knowledge:     New knowledge entry for storage
  heartbeat:     "I'm alive, this is my status"
  credit_alert:  "CF budget at X% for service Y"
  study_request: "I need research on topic X"
```

---

## Cloudflare Credit Management

### Free Tier Limits (as of 2025)
| Service     | Daily Limit       | Monthly Limit        | Reset    |
|-------------|-------------------|----------------------|----------|
| Workers AI  | 10k neurons       | -                    | Midnight |
| D1          | 25M reads         | -                    | Midnight |
| D1          | 50k writes        | -                    | Midnight |
| R2          | 10M Class B ops   | 10GB storage         | Monthly  |
| R2          | 1M Class A ops    | -                    | Monthly  |
| KV          | 100k reads        | -                    | Midnight |
| KV          | 1k writes         | -                    | Midnight |
| Pages       | Unlimited         | 500 builds           | Monthly  |

### Credit Gaming Strategy
1. **Track real-time usage** — Every CF call decrements a counter
2. **Priority mapping** — High-priority tasks get CF credits first
3. **End-of-day sprint** — At 23:45 UTC, schedule "credit burn" tasks
   - Use remaining Workers AI neurons on batch inference
   - Generate training data from day's research
   - Create image/audio from accumulated prompts
4. **Monthly R2 pacing** — Spread writes across the month (1M ÷ 30 = ~33k/day)
5. **Credit-aware scheduling** — Low-priority tasks wait for off-peak hours when credits are fresh
6. **Teacher pacing** — If acting as teacher model trainer, pace instruction generation to end *just before* midnight reset

### Decision Algorithm
```
Before each CF call:
  1. Check service budget (daily + monthly)
  2. If > 80% used: only schedule if priority < 5
  3. If > 90% used: only schedule if priority < 3 (critical only)
  4. If < 10% remaining and 23:00+ UTC: trigger end-of-day batch
  5. Log all usage for monthly reporting
```

---

## Knowledge Lifecycle

### Storage Tier Rules
```
HOT  (0-24h):   In-memory dict + SQLite. Full-text search. All queries here first.
                Max: 1000 entries. Eviction: LRU → promote to WARM.

WARM (1-30d):   SQLite local + D1 cloud (sync if CF enabled).
                Full metadata, vector embeddings. Max: 100k entries.
                Eviction: score < 0.3 AND age > 7d → compress to COLD.

COLD (30-180d): Compressed YAML on local disk + R2. Summary only, no embeddings.
                Max: unlimited (disk/budget bound).
                Eviction: age > 180d OR low-value → ARCHIVE.

ARCHIVE:        Summarized, max 100 chars per entry. Local SQLite table.
                Kept indefinitely as index. Actual blobs in R2 or purged.

DELETED:        Final summary written to research_log.txt then data purged.
                Deletion candidates: contradicted, superseded, and confirmed false.
```

### Garbage Collection Cycle (daily at 02:00 local)
1. **Score all WARM entries** — `score = confidence × recency × relevance`
2. **Promote** — HOT entries older than 24h → WARM (if score > 0.3)
3. **Compress** — WARM entries older than 30d → COLD
4. **Archive** — COLD entries older than 180d → ARCHIVE summary
5. **Delete** — ARCHIVE entries older than 365d AND score < 0.1 → purge
6. **Summarize** — Generate weekly and monthly summaries of deleted content
7. **Report** — Log GC stats (freed space, entries processed)

### Vector Embeddings
- Generated for all WARM entries
- Stored in SQLite (sqlite-vec) or Qdrant for larger deployments
- Updated when entry is challenged or updated
- Used for: semantic search, duplicate detection, related-entry clustering

---

## Hardware Profiles

### Profile Detection (Auto, runs at startup)
```python
Profile selection:
  1. Check CUDA availability + VRAM
  2. Check RAM
  3. Check CPU cores
  4. Check Jetson-specific flags (/proc/device-tree/model)

  → nano:        ARM CPU, 8GB shared RAM, no dedicated VRAM, CUDA via Tegra
  → laptop_gpu:  CUDA, 4-8GB VRAM, 16-32GB RAM
  → workstation: CUDA, 8-80GB VRAM, 32-128GB RAM
  → multi_gpu:   Multiple CUDA devices
  → cloud:       No GPU, API-only mode
  → cpu_only:    No GPU, local models only (GGUF/llama.cpp)
```

### Profile Specifications

| Profile      | Inference Backend    | Max Agents | LLM                    | Embeddings          |
|--------------|----------------------|------------|------------------------|---------------------|
| nano         | llama.cpp (GGUF Q4)  | 2          | TinyLlama/Phi-2        | sentence-transformers|
| laptop_gpu   | llama.cpp or vllm    | 4          | Mistral-7B or API      | local               |
| workstation  | vllm (fp16)          | 8          | Llama-70B or API       | local               |
| multi_gpu    | vllm (tensor parallel)| 16        | Mixtral/70B+           | local               |
| cloud        | API only             | 32+        | Claude/GPT-4           | API (CF Workers)    |
| cpu_only     | llama.cpp (GGUF Q4)  | 2          | Llama-3.2-3B           | sentence-transformers|

---

## Module Structure (Implementation Plan)

```
crew/
├── [EXISTING - phase 1-3]
│   ├── scheduler.py
│   ├── runner.py
│   ├── brain.py
│   ├── daemon.py
│   └── cli.py
│
├── messaging/                    # Phase 4a: Communication
│   ├── __init__.py
│   ├── bus.py                    # SQLite-backed durable bus
│   └── protocol.py               # Message types, serialization
│
├── agents/                       # Phase 4b: Multi-agent
│   ├── __init__.py
│   ├── base.py                   # BaseAgent (lifecycle, messaging, CF budget)
│   ├── pool.py                   # AgentPool (spawn, monitor, balance)
│   ├── researcher.py             # ResearcherAgent
│   ├── teacher.py                # TeacherAgent
│   ├── critic.py                 # CriticAgent
│   ├── distiller.py              # DistillerAgent
│   └── specialist.py             # SpecialistAgent (inference)
│
├── cloudflare/                   # Phase 4c: CF integration
│   ├── __init__.py
│   ├── client.py                 # CF REST API wrapper
│   ├── credits.py                # Budget tracker + gaming strategy
│   ├── workers_ai.py             # CF Workers AI calls
│   ├── d1.py                     # D1 database operations
│   ├── r2.py                     # R2 object storage
│   └── kv.py                     # KV store operations
│
├── knowledge/                    # Phase 4d: Knowledge management
│   ├── __init__.py
│   ├── store.py                  # Multi-tier storage facade
│   ├── hot.py                    # In-memory hot cache
│   ├── warm.py                   # SQLite warm store
│   ├── cold.py                   # Compressed cold storage
│   ├── lifecycle.py              # GC, promotion, archiving
│   ├── embeddings.py             # Vector embeddings (local or CF)
│   └── lora.py                   # LoRA dataset builder
│
└── hardware/                     # Phase 4e: Resource scaling
    ├── __init__.py
    ├── detector.py               # Auto-detect hardware profile
    ├── profiles.py               # Profile definitions + limits
    └── scaler.py                 # Dynamic allocation
```

---

## Schema Files (to create)

| File                              | Describes                                |
|-----------------------------------|------------------------------------------|
| `schemas/agent.yaml`              | Agent types, roles, state, messages      |
| `schemas/cloudflare.yaml`         | CF services, budgets, gaming rules       |
| `schemas/knowledge_lifecycle.yaml`| Storage tiers, GC rules, scoring         |
| `schemas/hardware_profile.yaml`   | Device profiles, capabilities, limits    |
| `schemas/swarm.yaml`              | Swarm coordination, scaling, topology    |
| `schemas/training_data.yaml`      | LoRA dataset, Q&A format, quality rating |

---

## Integration Points

### With Existing Daemon
The swarm extends daemon.py:
- Agent pool is managed as additional background threads/processes
- Message bus is consulted by daemon's main loop
- Knowledge store replaces simple YAML knowledge entries
- CF credits inform task scheduling decisions
- Hardware profile sets default config values at startup

### With Existing Brain
The brain.py can use agent pool results:
- `brain.plan_experiments()` can query knowledge store (not just YAML)
- Research agents feed distilled findings into brain context
- Teacher generates training data from brain's successful decisions

### With Existing CLI
The CLI gains new commands:
```
crew agents           # Show agent pool status
crew agents start N   # Spawn N additional agents of type
crew cf credits       # Show Cloudflare credit status
crew cf burn          # Trigger end-of-day credit burn
crew knowledge query  # Semantic search over knowledge
crew training-data    # Show LoRA dataset status
```

---

## Scaling Topology

### Single Node (most users)
```
[Daemon] → [AgentPool(2-8)] → [LocalKnowledge] → [LocalModels]
                            ↕ Cloudflare sync (async, optional)
```

### Multi-Node Local (Jetson + workstation)
```
[Workstation Daemon] ←→ [Jetson Daemon]
      │                        │
   Heavy GPU work         Light inference
   Research agents        Specialist agents
         ↓                      ↓
        [Shared SQLite / CF D1 Knowledge Store]
```

### Cloud Swarm
```
[Cloud Coordinator] ←→ [CF Workers AI] ←→ [CF D1/R2/KV]
       ↕
[Multiple Cloud Agents]
  Agent-1: Researcher
  Agent-2: Teacher × N (parallel instruction generation)
  Agent-3: Critic
  Agent-4: Distiller
       ↓
[Training pipeline → LoRA → Local specialization]
```

---

## Implementation Priority

### Phase 4a — Message Bus (Foundation)
`crew/messaging/bus.py` + `crew/messaging/protocol.py`
- SQLite-backed durable message queue
- Publisher/subscriber pattern
- Message TTL and cleanup
- No external deps

### Phase 4b — Agent Pool
`crew/agents/base.py` + `crew/agents/pool.py`
- BaseAgent: lifecycle, message handlers, resource checking
- AgentPool: spawn threads/processes, health monitoring
- ResearcherAgent: web search + LLM query
- TeacherAgent: training data generation
- CriticAgent: fact-checking and challenge
- DistillerAgent: synthesis

### Phase 4c — Cloudflare
`crew/cloudflare/credits.py` + `crew/cloudflare/client.py`
- Credit tracker with daily/monthly budgets
- Credit gaming algorithm
- Workers AI wrapper
- D1, R2, KV wrappers
- End-of-day batch scheduler

### Phase 4d — Knowledge Store
`crew/knowledge/store.py` + lifecycle components
- Hot/warm/cold/archive tiers
- Daily GC cycle
- Vector embeddings (sqlite-vec or numpy fallback)
- LoRA dataset builder

### Phase 4e — Hardware Profiles
`crew/hardware/detector.py` + profiles
- Auto-detect on startup
- Set runtime constraints
- Model selection guidance
- Dynamic allocation

---

*This document drives implementation. Each schema file below provides the detailed data model. Developers should read this architecture, then the relevant schema, then implement the module.*
