# AutoClaw API Reference

## Phase A: Autonomous Learning Foundation

### Knowledge Store (`crew/knowledge/store.py`)

Persistent learning with auto-scored confidence levels.

#### KnowledgeEntry
```python
@dataclass
class KnowledgeEntry:
    id: int                          # Unique ID
    insight: str                     # The knowledge itself
    category: str                    # Type: hyperparameter, architecture, training_dynamics, data, methodology
    tags: List[str]                  # For querying
    confidence: ConfidenceLevel      # Auto-scored: low, medium, high, very_high
    status: KnowledgeStatus          # active, outdated, questioned
    source_task_ids: List[int]       # Which tasks generated this
    experiments_supporting: int      # Evidence count
    experiments_contradicting: int   # Counter-evidence count
    created_at: datetime
    last_updated: datetime
    evidence: Dict                   # Supporting information
    conditions: Optional[str]        # When this applies
```

#### KnowledgeStore Methods

**create()** - Create new knowledge entry
```python
entry = store.create(
    insight: str,                          # Required: The knowledge
    category: str,                         # Required: Category type
    tags: List[str],                       # Required: Tags for querying
    source_task_ids: List[int],            # Required: Source tasks
    experiments_supporting: int,           # Required: Supporting experiments
    experiments_contradicting: int = 0,    # Optional: Counter-experiments
    conditions: Optional[str] = None,      # Optional: When it applies
    key_commits: Optional[List[str]] = None # Optional: Git commits
) -> KnowledgeEntry
```

**query()** - Find knowledge entries
```python
results = store.query(
    tags: Optional[List[str]] = None,      # Filter by tags (OR logic)
    category: Optional[str] = None,        # Filter by category
    min_confidence: Optional[str] = None,  # Min confidence: low, medium, high
    status: Optional[str] = None,          # Filter by status: active, outdated, questioned
) -> List[KnowledgeEntry]
```

**get()** - Get entry by ID
```python
entry = store.get(entry_id: int) -> Optional[KnowledgeEntry]
```

**mark_outdated()** - Mark entry as outdated
```python
store.mark_outdated(entry_id: int, replaced_by: int)
```

**mark_questioned()** - Flag entry for validation
```python
store.mark_questioned(entry_id: int, reason: str)
```

**cleanup_old_entries()** - Remove unvalidated old entries
```python
removed = store.cleanup_old_entries(days: int = 30) -> int
```

**stats()** - Get store statistics
```python
stats = store.stats() -> Dict[str, Any]
# Returns: {total_entries, by_confidence, by_category, by_status}
```

---

### Trigger Daemon (`crew/triggers/daemon.py`)

External event monitoring and auto-task creation.

#### TriggerDaemon Methods

**start()** - Begin polling triggers in background thread
```python
daemon.start()
```

**stop()** - Graceful shutdown
```python
daemon.stop()
```

**add_trigger()** - Register a new trigger
```python
daemon.add_trigger(config: Dict[str, Any])
# Config includes: id, name, type, source, filter, action, enabled, poll_interval_minutes
```

**list_triggers()** - Get all triggers
```python
triggers = daemon.list_triggers() -> List[Dict[str, Any]]
```

**enable_trigger()** - Resume monitoring
```python
daemon.enable_trigger(trigger_id: int)
```

**disable_trigger()** - Pause monitoring
```python
daemon.disable_trigger(trigger_id: int)
```

**stats()** - Get daemon statistics
```python
stats = daemon.stats() -> Dict[str, Any]
# Returns: {total_triggers, enabled, fired_today, last_check}
```

#### Trigger Types
- **RSS**: Feed monitoring (requires source.url)
- **Schedule**: Cron-like scheduling (requires source.cron)
- **Webhook**: External event receiver
- **File**: File system monitoring
- **Sensor**: Hardware sensor thresholds

---

### Notification Manager (`crew/notifications/manager.py`)

Multi-channel notification delivery.

#### NotificationManager Methods

**create()** - Create and optionally deliver notification
```python
notif = nm.create(
    title: str,                        # Required: Short title
    body: str,                         # Required: Message body
    severity: str = "important",       # info, important, urgent
    source: str = "system",            # Where it came from
    tags: List[str] = [],              # For filtering
    auto_deliver: bool = True,         # Send immediately?
) -> Notification
```

**deliver()** - Send notification to all channels
```python
success = nm.deliver(notification_id: int) -> bool
```

**get_unread()** - Get undelivered notifications
```python
notifs = nm.get_unread() -> List[Notification]
```

**delete()** - Remove notification
```python
nm.delete(notification_id: int)
```

**stats()** - Get notification statistics
```python
stats = nm.stats() -> Dict[str, Any]
# Returns: {total_notifications, unread, by_severity, by_source}
```

#### Notification Channels (in config.yaml)
```yaml
notifications:
  external_channels:
    - type: webhook
      url: https://example.com/notify
      headers: {Authorization: "Bearer token"}
    - type: email
      smtp_host: smtp.example.com
      sender: autoclaw@example.com
      recipients: [captain@example.com]
    - type: command
      command: "ntfy -p high '{{title}}'"
    - type: file
      path: /var/log/autoclaw/notifications.log
```

---

### Context Handoff / Baton (`crew/handoff.py`)

Resume long-running tasks seamlessly.

#### HandoffManager Methods

**create()** - Start new generation tracking
```python
handoff = hm.create(task_id: int, generation: int) -> ContextHandoff
```

**save()** - Persist handoff to disk
```python
hm.save(handoff: ContextHandoff)
# Saves to: data/handoffs/task{id}/gen{generation}/state.yaml
# Creates symlink: data/handoffs/task{id}/CURRENT -> gen{generation}
```

**load()** - Load specific generation
```python
handoff = hm.load(task_id: int, generation: int) -> Optional[ContextHandoff]
```

**get_current()** - Get latest generation
```python
handoff = hm.get_current(task_id: int) -> Optional[ContextHandoff]
```

**list_generations()** - Get all generations for task
```python
gens = hm.list_generations(task_id: int) -> List[int]
```

**should_handoff()** - Check if context full
```python
yes = hm.should_handoff(context_tokens_used: int, context_limit: int = 8000) -> bool
# Returns True if tokens_used > 75% of limit
```

**generate_summary_for_context()** - Create LLM-readable summary
```python
summary = hm.generate_summary_for_context(handoff: ContextHandoff) -> str
# Condensed description for next context window
```

---

## Phase B: Multi-Agent Collaboration

### Message Bus (`crew/messaging/bus.py`)

Durable SQLite-backed inter-agent communication.

#### MessageBus Methods

**publish()** - Queue message
```python
msg_id = bus.publish(Message(
    from_agent: str,                   # Sender agent ID
    to_agent: str,                     # Recipient: agent_id | any_role | broadcast
    type: str,                         # Message type
    payload: Dict[str, Any],           # Data
    priority: int = 5,                 # 1-10, lower = higher
    tags: List[str] = [],              # For filtering
    expires_in_hours: Optional[float] = None,
)) -> int  # Returns message ID
```

**receive()** - Get pending messages
```python
messages = bus.receive(
    agent_id: str,                     # Receiving agent
    roles: List[str] = [],             # Roles to filter on
    limit: int = 10,                   # Max messages
    status: str = "pending",           # Filter by status
) -> List[Message]
```

**complete()** - Mark message processed
```python
bus.complete(message_id: int)
```

**fail()** - Mark message failed
```python
bus.fail(message_id: int, error_message: str)
# Moves to dead_letters table
```

**mark_processing()** - Update processing status
```python
bus.mark_processing(message_id: int)
```

**subscribe()** - Watch message types
```python
def handler(msg: Message): ...
bus.subscribe("message_type", handler)
```

**get_queue_depths()** - Get queue statistics
```python
depths = bus.get_queue_depths() -> Dict[str, int]
# Returns: {by_agent: {agent_id: count}, by_status: {status: count}}
```

---

### BaseAgent (`crew/agents/base.py`)

All agents inherit from this.

#### BaseAgent Interface

```python
class MyAgent(BaseAgent):
    ROLE = "my_role"  # Set this in subclass

    def get_capabilities(self) -> List[str]:
        """Return list of capabilities."""
        return ["capability_1", "capability_2"]

    def process_message(self, message: Message) -> Optional[Message]:
        """Process incoming message, return reply (optional)."""
        ...

    def idle_work(self):
        """Called when no messages pending."""
        # Optional: implement periodic work
        time.sleep(5)
```

#### Helper Methods

**publish()** - Send message to other agent
```python
msg_id = self.publish(
    to_agent: str,
    msg_type: str,
    payload: Dict[str, Any],
    priority: Optional[int] = None,
    parent_id: Optional[int] = None,
    tags: Optional[List[str]] = None,
    expires_in_hours: Optional[float] = None,
) -> int
```

**reply()** - Send reply to original sender
```python
msg_id = self.reply(
    original: Message,
    msg_type: str,
    payload: Dict[str, Any],
) -> int
```

**check_rate_limit()** - Check if can use resource
```python
ok = self.check_rate_limit("llm_call" or "web_search") -> bool
```

**request_research()** - Ask researcher agent
```python
msg_id = self.request_research(
    topic: str,
    context: Optional[str] = None,
    priority: int = 5,
) -> int
```

**request_training_data()** - Ask teacher agent
```python
msg_id = self.request_training_data(
    topic: str,
    source_text: str,
    n_examples: int = 20,
    priority: int = 6,
) -> int
```

**submit_knowledge()** - Add to knowledge store
```python
msg_id = self.submit_knowledge(
    insight: str,
    category: str,
    tags: List[str],
    confidence: str = "medium",
    evidence: Optional[Dict] = None,
) -> int
```

---

## Phase C: Advanced Learning

### Adaptive Scheduler (`crew/adaptive.py`)

Learn which research directions are most productive.

#### AdaptiveScheduler Methods

**compute_priority_adjustment()** - Boost for high-value directions
```python
boost = scheduler.compute_priority_adjustment(task) -> float
# Returns 0.0-2.0 boost based on direction's learned value
```

**update_from_task_result()** - Learn from outcomes
```python
scheduler.update_from_task_result(
    task,
    findings: List[str],
    success_rate: float = 1.0,
    compute_hours: float = 0.1,
    num_knowledge_entries: int = 0,
)
```

**suggest_research_directions()** - Recommend directions
```python
suggestions = scheduler.suggest_research_directions(num_suggestions: int = 3) -> List[Dict]
# Returns: [{direction, estimated_value, mean_value, uncertainty, roi, rationale}, ...]
```

**stats()** - Get scheduler statistics
```python
stats = scheduler.stats() -> Dict[str, Any]
```

---

### Flowstate (`crew/flowstate.py`)

Safe exploration in isolated sandboxes.

#### FlowStateManager Methods

**create()** - Start sandbox exploration
```python
flow = manager.create(
    title: str,
    description: Optional[str] = None,
    parent_task_id: Optional[int] = None,
    budget_gb: float = 10.0,
    budget_hours: float = 4.0,
    max_experiments: int = 20,
) -> FlowStateTask
```

**record_experiment()** - Log experiment results
```python
ok = manager.record_experiment(
    task_id: str,
    success: bool,
    result_summary: str = "",
) -> bool
```

**promote_findings()** - Move to main knowledge
```python
knowledge_ids = manager.promote_findings(
    task_id: str,
    findings: List[str],
    confidence: str = "medium",
    validation_task_ids: Optional[List[int]] = None,
) -> List[int]
```

**discard()** - Abandon sandbox
```python
manager.discard(task_id: str)
```

**cleanup_old_sandboxes()** - Remove old completed
```python
manager.cleanup_old_sandboxes(days: int = 7)
```

**stats()** - Get sandbox statistics
```python
stats = manager.stats() -> Dict[str, Any]
```

---

## Error Handling Framework (`crew/error_handling.py`)

Robust error handling with recovery.

### Decorators

**@retry** - Automatic retry with exponential backoff
```python
@retry(max_attempts=3, retryable_exceptions=(IOError, TimeoutError))
def fetch_data():
    ...
```

**@handle_error** - Graceful error handling
```python
@handle_error("component_name", "operation", default_return=[])
def dangerous_operation():
    ...
```

### CircuitBreaker

```python
breaker = CircuitBreaker("api_name", failure_threshold=5)
if breaker.is_available():
    try:
        result = api_call()
        breaker.record_success()
    except Exception:
        breaker.record_failure()

# Get status
status = breaker.status()
```

---

## Configuration

### config.yaml

```yaml
# Core system
crew:
  name: "AutoClaw"
  personality: "balanced"

# LLM
llm:
  provider: "anthropic"
  model: "claude-opus-4-6"
  api_key: "${ANTHROPIC_API_KEY}"

# Knowledge store
knowledge:
  max_entries: 500
  cleanup_days: 30  # Remove unvalidated old entries

# Triggers
triggers:
  enabled: true
  default_poll_minutes: 30

# Notifications
notifications:
  external_channels: []  # See channel definitions above

# Experiments
experiments:
  time_budget_seconds: 300
  git_commit_each: false
  keep_checkpoints: "best_only"

# Adaptive scheduling
adaptive:
  enabled: true
  thompson_samples_per_decision: 100

# Flowstate
flowstate:
  enabled: true
  default_budget_gb: 10.0
  default_budget_hours: 4.0

# Hardware
hardware:
  profile: null  # Auto-detect if not set
```

---

## Common Patterns

### Knowledge Learning Loop
```python
# 1. Run experiments and get findings
findings = ["Finding 1", "Finding 2"]

# 2. Create knowledge from findings
di = get_daemon_integration()
di.create_knowledge_from_findings(task, findings, experiments_run=10)

# 3. Future planning uses knowledge
hints = di.enhance_experiment_planning(task)
params = di.refine_parameters_with_knowledge(task, params)
```

### Multi-Agent Workflow
```python
# Coordinator orchestrates workflow
coordinator = CoordinatorAgent("coordinator_1")

# 1. Request research
researcher_msg_id = coordinator.request_research(
    "transformer attention mechanisms"
)

# 2. Ask teacher to generate training data
# (would receive researcher results first)
teacher_msg_id = coordinator.request_training_data(
    "attention mechanisms",
    source_text=researcher_findings,
    n_examples=50
)
```

### Sandbox Exploration
```python
manager = get_flowstate_manager()

# Start risky exploration
flow = manager.create("Explore mixed precision")

# Run experiments (results isolated)
manager.record_experiment(flow.id, success=True, "Good results!")

# If promising, promote to main knowledge
if flow.experiments_successful > 5:
    manager.promote_findings(
        flow.id,
        findings=flow.findings,
        validation_task_ids=[1, 2, 3]
    )
```

---

## Error Handling

All components use consistent error handling:

1. **Retry**: Transient errors are retried with backoff
2. **Circuit Break**: External API failures are rate-limited
3. **Graceful Degrade**: Core functions return defaults on error
4. **Notify**: Critical errors alert the captain
5. **Audit**: All errors logged for analysis

```python
# Use error auditor to analyze issues
auditor = get_error_auditor()
stats = auditor.get_stats()
hotspots = auditor.get_hotspots(top_n=5)
```

---

## See Also

- [Integration Guide](INTEGRATION_GUIDE.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Deployment Guide](DEPLOYMENT.md)
