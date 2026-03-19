# Core Components (12/12)

Detailed documentation of all 12 core components that form the foundation of AutoClaw.

---

## 1. BaseAgent (`crew/agents/base.py`)

**Purpose**: Foundation class for all agent types

**Key Responsibilities**:
- Initialize with configuration
- Manage thread lifecycle
- Handle errors and retries
- Publish results to message bus
- Track execution metrics

**Key Methods**:
- `run(task)` - Execute a task
- `get_capabilities()` - List what this agent can do
- `publish_result(result)` - Share findings
- `subscribe(topic)` - Listen to messages

**Usage**: All other agents inherit from BaseAgent

---

## 2. Researcher Agent (`crew/agents/researcher.py`)

**Purpose**: Web search and knowledge synthesis

**Capabilities**:
- Search web via APIs
- Synthesize information from multiple sources
- Extract key findings
- Rate source credibility
- Generate citations

**Task Types It Handles**:
- "Research X topic"
- "Find information about..."
- "Explore recent developments in..."

**Output**: Knowledge entries with sources and confidence scores

---

## 3. Teacher Agent (`crew/agents/teacher.py`)

**Purpose**: Q&A generation and educational content

**Capabilities**:
- Generate quiz questions
- Create explanations
- Develop learning materials
- Assess knowledge gaps
- Suggest learning paths

**Task Types It Handles**:
- "Create quiz on X"
- "Explain concept Y"
- "Generate learning guide for..."

**Output**: Q&A pairs, explanations, study guides

---

## 4. Critic Agent (`crew/agents/critic.py`)

**Purpose**: Quality validation and code review

**Capabilities**:
- Analyze code quality
- Identify bugs and issues
- Review documentation
- Assess performance
- Suggest improvements

**Task Types It Handles**:
- "Review code in..."
- "Validate findings from..."
- "Quality check..."

**Output**: Reviews with scores and recommendations

---

## 5. Distiller Agent (`crew/agents/distiller.py`)

**Purpose**: Knowledge compression and synthesis

**Capabilities**:
- Summarize findings
- Extract key concepts
- Identify patterns
- Create knowledge graphs
- Compress redundancy

**Task Types It Handles**:
- "Summarize research on..."
- "Extract key patterns from..."
- "Synthesize findings about..."

**Output**: Compressed knowledge, concept maps, patterns

---

## 6. MessageBus (`crew/messaging/bus.py`)

**Purpose**: Durable inter-agent communication

**Key Features**:
- SQLite-backed pub/sub
- Message persistence
- Topic-based routing
- Async message delivery
- Failure recovery

**Key Methods**:
- `publish(topic, message)` - Send message
- `subscribe(topic, handler)` - Register listener
- `get_pending()` - Retrieve queued messages
- `ack(message_id)` - Mark as processed

**Data Model**: Messages stored in `messages.db` with:
- Topic
- Payload
- Timestamp
- Source agent
- Status (pending/delivered/failed)

**Durability**: All messages persisted before delivery

---

## 7. KnowledgeStore (`crew/knowledge/store.py`)

**Purpose**: Persistent learning with tiered storage

**Key Features**:
- Hot/warm/cold TTL tiers
- Confidence scoring (0-1.0)
- Full-text search
- Tag-based filtering
- Automatic promotion/demotion

**Key Methods**:
- `create_entry(title, content, confidence)` - Add knowledge
- `query(text, min_confidence)` - Search
- `get_entries_by_tag(tag)` - Filter
- `promote_warm_to_cold()` - Tier management
- `garbage_collect()` - Cleanup old entries

**Storage**: YAML file `data/crew/knowledge.yaml` with entries:
```yaml
entries:
  - id: "knowledge_001"
    title: "Learning rate warmup improves training"
    content: "..."
    confidence: 0.95
    created_at: 2026-03-19T07:00:00Z
    tier: "hot"  # or "warm", "cold"
```

**TTL Settings**:
- Hot: 3600 seconds (1 hour)
- Warm: 86400 seconds (1 day)
- Cold: 604800 seconds (1 week)

---

## 8. LifecycleManager (`crew/lifecycle.py`)

**Purpose**: Garbage collection and cleanup

**Key Responsibilities**:
- Monitor system resources (disk, memory)
- Clean up old knowledge entries
- Archive completed tasks
- Compact databases
- Remove temporary files

**Key Methods**:
- `cleanup_old_knowledge()` - Remove expired entries
- `archive_tasks()` - Move old tasks to archive
- `compact_db()` - Optimize SQLite
- `check_disk_space()` - Monitor storage
- `force_cleanup()` - Immediate deep cleanup

**Triggers**:
- Runs on schedule (configurable interval)
- Triggered on disk pressure
- Called on shutdown

---

## 9. AgentPool (`crew/agents/pool.py`)

**Purpose**: Concurrent agent management

**Key Features**:
- Thread-safe agent registry
- Concurrency control
- Agent assignment
- Load balancing
- Health monitoring

**Key Methods**:
- `spawn_agent(role)` - Create new agent
- `get_available_agent()` - Next idle agent
- `assign_task(agent, task)` - Give work
- `get_status()` - Pool metrics
- `shutdown_all()` - Graceful cleanup

**Configuration**:
```yaml
agents:
  researcher: { enabled: true }
  teacher: { enabled: true }
  critic: { enabled: true }
  distiller: { enabled: true }
  coordinator: { enabled: true }
```

---

## 10. Scheduler (`crew/scheduler.py`)

**Purpose**: Task board and priority queuing

**Key Features**:
- Read tasks from file system
- Priority-based sorting
- Task status tracking
- Dependency management
- Follow-up generation

**Key Methods**:
- `read_all_tasks()` - Load tasks from disk
- `sort_by_priority()` - Reorder queue
- `assign_to_agent()` - Give task
- `update_status(task_id, status)` - Track progress
- `create_followup(parent_task)` - Auto-generate next

**Task States**:
- QUEUED - Waiting for assignment
- ACTIVE - Being processed
- COMPLETED - Done successfully
- FAILED - Error occurred
- PAUSED - Manually paused

---

## 11. CLI (`crew/cli.py`)

**Purpose**: Command-line interface for control

**30+ Commands**:
- Task management: `add`, `board`, `show`, `cancel`
- Monitoring: `status`, `metrics`, `agents`
- Knowledge: `knowledge query`, `knowledge gc`
- Configuration: `config show`, `config set`
- System: `start`, `stop`, `restart`

**Architecture**:
- Unix socket client connecting to daemon
- Command parsing and dispatch
- Result formatting and output
- Error handling and messaging

See **[CLI_COMMANDS.md](CLI_COMMANDS.md)** for complete reference.

---

## 12. Daemon (`crew/daemon.py`)

**Purpose**: Always-on main process

**Responsibilities**:
1. Load configuration
2. Initialize components
3. Start background threads
4. Run main loop (scheduler → runner → brain)
5. Handle graceful shutdown
6. Recover from crashes

**Main Loop** (runs every 100ms):
1. Check for new tasks
2. Assign to available agents
3. Process pending messages
4. Run health checks
5. Manage knowledge tiers
6. Monitor resources

**Threads**:
- Main loop (primary)
- Heartbeat (monitoring)
- Trigger daemon (event listener)
- Message processor (async)

**Exit Codes**:
- 0: Clean shutdown
- 1: Configuration error
- 2: Runtime error
- 130: SIGINT received

---

## 🔗 Component Interactions

```
CLI
 ↓ (Unix socket)
Daemon (main loop)
 ├→ Scheduler (read tasks)
 ├→ AgentPool (get next agent)
 ├→ Agent.run() (execute task)
 ├→ Brain/LLM (reasoning)
 ├→ MessageBus (pub/sub)
 ├→ KnowledgeStore (persist findings)
 ├→ LifecycleManager (cleanup)
 └→ HealthCheck (monitor)
```

---

## 📊 Component Health Status

All 12 components verified:
- ✅ BaseAgent - Core inheritance
- ✅ Researcher - Web search + synthesis
- ✅ Teacher - Q&A generation
- ✅ Critic - Code review
- ✅ Distiller - Knowledge compression
- ✅ MessageBus - Durable communication
- ✅ KnowledgeStore - Tiered storage
- ✅ LifecycleManager - Garbage collection
- ✅ AgentPool - Concurrency
- ✅ Scheduler - Task queuing
- ✅ CLI - Command interface
- ✅ Daemon - Main loop

---

## 🔗 Related Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design
- **[AGENTS.md](AGENTS.md)** - Agent workflows
- **[MESSAGE_BUS.md](MESSAGE_BUS.md)** - Communication
- **[KNOWLEDGE_SYSTEM.md](KNOWLEDGE_SYSTEM.md)** - Storage
- **[PRODUCTION_MODULES.md](PRODUCTION_MODULES.md)** - Support modules

**See also**: [HOME.md](HOME.md)
