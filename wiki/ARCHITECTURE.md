# System Architecture

AutoClaw is built on a **modular, message-driven architecture** with persistent storage and autonomous task processing.

---

## 🏗️ High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI (Captain)                          │
│          30+ commands for task management & control         │
└──────────────────────┬──────────────────────────────────────┘
                       │ Unix Socket IPC
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   DAEMON (Always-On)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  Scheduler  │→ │    Runner    │→ │   Brain (LLM)   │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Agent Pool (Researcher, Teacher, etc)       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │      Message Bus (SQLite Pub/Sub + Durable)         │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
      ┌────────────────┼────────────────┐
      ▼                ▼                ▼
┌──────────────┐ ┌─────────────┐ ┌──────────────┐
│ Knowledge    │ │ Task Files  │ │ Notifications│
│ Store (YAML) │ │ (YAML)      │ │ (Events)     │
└──────────────┘ └─────────────┘ └──────────────┘
```

---

## 📦 Core Components (12/12)

All components are critical for system operation:

1. **BaseAgent** - Foundation for all agent types
2. **Researcher** - Web search and knowledge synthesis
3. **Teacher** - Q&A generation and explanation
4. **Critic** - Quality validation and code review
5. **Distiller** - Knowledge compression and synthesis
6. **MessageBus** - SQLite-backed pub/sub with durability
7. **KnowledgeStore** - Hot/warm/cold TTL tiers with confidence
8. **LifecycleManager** - Garbage collection and cleanup
9. **AgentPool** - Concurrent agent management
10. **Scheduler** - Task board and priority queuing
11. **CLI** - Command-line interface (30+ commands)
12. **Daemon** - Always-on process and bootstrap

See **[COMPONENTS.md](COMPONENTS.md)** for deep-dive on each.

---

## 🔄 Data Flow

### Task Submission
```
User → CLI add command
  ↓
Task YAML file created → data/tasks/{id}.yaml
  ↓
Task appears on board (scheduler reads files)
  ↓
Daemon main loop discovers task
  ↓
Agent picked based on priority and capability
```

### Knowledge Creation
```
Agent completes research → findings generated
  ↓
KnowledgeStore.create_entry() called
  ↓
Confidence scored (0-1.0)
  ↓
Stored in hot tier (3600s TTL)
  ↓
Available for queries immediately
  ↓
Auto-promoted to warm (86400s) then cold (604800s)
```

### Inter-Agent Communication
```
Agent publishes message → MessageBus.publish()
  ↓
Message inserted into SQLite DB (durable)
  ↓
Other agents receive via subscription
  ↓
Handlers execute asynchronously
  ↓
Success/failure logged for audit
```

---

## 🔌 Component Interactions

### Scheduler → Runner → Brain Loop
```
1. Scheduler.read_tasks() - Load from data/tasks/
2. Scheduler.sort_by_priority() - Reorder by urgency
3. Runner.execute_task() - Give to appropriate agent
4. Agent.run() - Process via LLM (Brain)
5. Results → Knowledge and notifications
```

### Knowledge Tier Management
```
Hot (3600s)  ← New entries stored here
  ↓
Warm (86400s) ← Auto-promoted after TTL expiry
  ↓
Cold (604800s) ← Long-term archive
  ↓
Garbage Collection ← Cleanup when disk pressure
```

### Agent Lifecycle
```
Creation → Thread pool assignment
  ↓
Task assignment from scheduler
  ↓
Execution with message bus access
  ↓
Result publication
  ↓
Idle/waiting for next task
  ↓
Cleanup on shutdown (LifecycleManager)
```

---

## 🎯 Daemon Main Loop

```python
while running:
    # 1. Load and prioritize tasks
    tasks = scheduler.read_all_tasks()
    tasks.sort_by_priority()

    # 2. Check agent pool capacity
    if available_agents > 0:
        # 3. Assign highest-priority task
        agent = pool.get_available_agent()
        task = tasks.pop(0)
        agent.execute(task)

    # 4. Check for messages
    messages = message_bus.get_pending()
    for msg in messages:
        recipients = subscriptions[msg.topic]
        for handler in recipients:
            handler(msg)

    # 5. Health check
    healthcheck.check_all_systems()

    # 6. Knowledge maintenance
    if disk_usage > threshold:
        knowledge_store.garbage_collect()

    # 7. Sleep briefly
    time.sleep(0.1)
```

---

## 💾 Persistent Storage

All state is written to disk for durability:

```
data/
├── crew/                    # Runtime state
│   ├── knowledge.yaml       # Knowledge store entries
│   ├── tasks/               # Active task queue (YAML files)
│   └── agents/              # Agent registry
├── tasks/                   # Task definitions
│   ├── 1.yaml               # Task ID 1
│   ├── 2.yaml
│   └── ...
├── messages.db              # SQLite message bus
├── experiments/             # Experiment results
└── config.yaml              # System configuration
```

---

## 🔐 Security Layers

1. **Input Validation** - All user input sanitized
2. **API Key Management** - Encrypted storage
3. **Rate Limiting** - Per-provider quota enforcement
4. **Audit Logging** - All operations recorded
5. **Circuit Breakers** - Prevent cascading failures

See **[SECURITY_FEATURES.md](SECURITY_FEATURES.md)** for details.

---

## 📊 Concurrency Model

- **Thread-safe**: Agent pool uses locks for shared state
- **Message-driven**: Agents communicate via pub/sub, not direct calls
- **Non-blocking**: Knowledge queries cached, don't block task processing
- **Resilient**: Failed messages automatically retried
- **Graceful shutdown**: 60-second timeout for in-flight operations

---

## 🚀 Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Task submission | <10ms | File write only |
| Knowledge query | <100ms | Cached results |
| Agent assignment | <50ms | Pool lookup |
| Message delivery | <50ms | SQLite insert + notification |
| Health check | <1s | All systems checked |

See **[PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)** for tuning.

---

## 🔗 Integration Points

- **OpenClaw**: `/autoclaw` skill in Claude Code
- **External APIs**: Rate-limited via security module
- **Event triggers**: File-based trigger system
- **Notifications**: Multiple channel support
- **Custom agents**: BaseAgent extension point

See **[OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md)**.

---

## 🔄 System State Transitions

```
┌──────────┐
│ STARTING │
└────┬─────┘
     │ Load config, init components
     ▼
┌──────────┐
│ STUDYING │ ← Main loop running
└────┬─────┘
     │ Task submitted
     ▼
┌──────────┐
│ WORKING  │ ← Agent executing
└────┬─────┘
     │ Task complete
     ▼
┌──────────┐
│ IDLE     │ ← Waiting for work
└──────────┘
```

---

## 📚 Related Documentation

- **[COMPONENTS.md](COMPONENTS.md)** - Detailed component docs
- **[MESSAGE_BUS.md](MESSAGE_BUS.md)** - Communication system
- **[KNOWLEDGE_SYSTEM.md](KNOWLEDGE_SYSTEM.md)** - Storage and retrieval
- **[API_REFERENCE.md](API_REFERENCE.md)** - Protocol details

**See also**: [HOME.md](HOME.md)
