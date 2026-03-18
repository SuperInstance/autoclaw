# AutoClaw Integration Guide

This guide shows how to use AutoClaw components together to build complete workflows.

## Complete Research Workflow

This example demonstrates a full research cycle: planning → experimentation → learning → scheduling.

```python
from crew.scheduler import Task
from crew.knowledge import get_knowledge_store
from crew.daemon_integration import get_daemon_integration
from crew.flowstate import get_flowstate_manager
from crew.adaptive import get_adaptive_scheduler

# 1. Create a research task
task = Task(
    id=1,
    title="Investigate attention mechanisms",
    description="Explore whether causal masking improves convergence",
    tags=["architecture", "transformers"]
)

# 2. Get learning hints from knowledge store
di = get_daemon_integration()
hints = di.enhance_experiment_planning(task)  # -> List of relevant findings
# Example: ["Causal masking enables faster convergence in small models",
#           "Attention heads learn different masking patterns"]

# 3. Run experiment (with hints to guide it)
results = run_experiment(task, hints)
findings = [
    "Causal masking reduced training time by 12%",
    "Critical for convergence when using low learning rates"
]

# 4. Store findings as knowledge
di.create_knowledge_from_findings(task, findings, experiments_run=10)

# 5. Adaptive scheduler learns which research directions are valuable
di.schedule_next_direction()
```

## Multi-Agent Research Coordination

Coordinate agents for complex research using the message bus.

```python
from crew.agents.coordinator import CoordinatorAgent
from crew.agents.researcher import ResearcherAgent
from crew.agents.teacher import TeacherAgent
from crew.messaging.bus import MessageBus

# Create agents
coordinator = CoordinatorAgent("coord_1")
researcher = ResearcherAgent("researcher_1")
teacher = TeacherAgent("teacher_1")

# Workflow: Research -> Generate Training Data -> Train

# Step 1: Coordinator asks researcher to explore a topic
msg_id = coordinator.request_research(
    topic="Vision transformer architecture",
    context="We're building a new image classification model",
    priority=8
)

# Researcher processes the message and returns findings
# (In a real system, the researcher would run in another process)

# Step 2: Use research to generate training data
researcher_findings = "Vision transformers use patch-based embeddings..."

msg_id = coordinator.request_training_data(
    topic="Vision transformer embeddings",
    source_text=researcher_findings,
    n_examples=50,
    priority=7
)

# Step 3: Teacher generates examples
# (Teacher processes the message independently)

# Check message bus status
bus = MessageBus()
depths = bus.get_queue_depths()
print(f"Pending messages: {depths['by_agent']}")
```

## Knowledge-Driven Task Planning

Use accumulated knowledge to make better decisions about what to research.

```python
from crew.knowledge import get_knowledge_store
from crew.adaptive import get_adaptive_scheduler

# Get knowledge store and scheduler
store = get_knowledge_store()
scheduler = get_adaptive_scheduler()

# Research direction 1: Low hanging fruit (high-confidence knowledge)
high_conf = store.query(min_confidence="high")
if high_conf:
    # These are proven findings - good for building on
    task_1 = Task(
        title=f"Build on: {high_conf[0].insight}",
        tags=high_conf[0].tags
    )

# Research direction 2: Uncertain findings (needs validation)
questioned = store.query(status="questioned")
if questioned:
    # These are disputed - good for validation tasks
    task_2 = Task(
        title=f"Validate: {questioned[0].insight}",
        tags=["validation"]
    )

# Research direction 3: Adaptive suggestion (Thompson sampling)
suggestions = scheduler.suggest_research_directions(num_suggestions=1)
if suggestions:
    suggestion = suggestions[0]
    # {direction, estimated_value, roi, rationale}
    task_3 = Task(
        title=suggestion['direction'],
        description=suggestion['rationale']
    )

# Scheduler learns from the outcomes
for task in [task_1, task_2, task_3]:
    findings = run_task(task)
    scheduler.update_from_task_result(
        task,
        findings=findings,
        success_rate=0.8,
        compute_hours=2.5,
        num_knowledge_entries=3
    )
```

## Sandboxed Exploration with Safe Promotion

Safely explore risky ideas in isolation, then promote results if successful.

```python
from crew.flowstate import get_flowstate_manager
from crew.knowledge import get_knowledge_store

manager = get_flowstate_manager()
store = get_knowledge_store()

# Start isolated exploration
sandbox = manager.create(
    title="Experiment with mixed precision training",
    description="Test float16 with gradient checkpointing",
    budget_gb=20.0,
    budget_hours=8.0,
    max_experiments=50
)

# Run risky experiments in sandbox (isolated, no side effects)
for i in range(10):
    success = run_experiment_in_sandbox(sandbox.id)
    manager.record_experiment(
        task_id=sandbox.id,
        success=success,
        result_summary=f"Attempt {i}: accuracy {92.3}%"
    )

# Check results
final_state = manager.get(sandbox.id)
if final_state.experiments_successful > 5:
    # Promote findings to main knowledge store
    knowledge_ids = manager.promote_findings(
        task_id=sandbox.id,
        findings=[
            "Mixed precision training with checkpointing is viable",
            "Requires batch size >= 64 for convergence",
            "Memory usage reduced by 35%"
        ],
        confidence="high",
        validation_task_ids=[1, 2, 3]  # Tasks that validated this
    )
    print(f"Promoted {len(knowledge_ids)} knowledge entries")
else:
    # Abandon failed experiments
    manager.discard(sandbox.id)
    print("Sandbox discarded, learned nothing")
```

## Error Handling and Recovery

Use the error handling framework for robust operations.

```python
from crew.error_handling import (
    CircuitBreaker,
    retry,
    handle_error,
    get_error_auditor
)
import time

# Pattern 1: Retry transient failures with backoff
@retry(max_attempts=3, retryable_exceptions=(TimeoutError, ConnectionError))
def fetch_research_paper(url):
    """Fetch with automatic retry on timeout."""
    return requests.get(url, timeout=5)

# Pattern 2: Circuit breaker for external APIs
breaker = CircuitBreaker("external_api", failure_threshold=5)

for item in items:
    if breaker.is_available():
        try:
            result = call_external_api(item)
            breaker.record_success()
        except Exception as e:
            breaker.record_failure()
    else:
        # Circuit open, skip this item
        use_cached_result(item)

# Pattern 3: Graceful degradation
@handle_error("knowledge", "query", default_return=[])
def query_knowledge(tags):
    """Return empty list if query fails."""
    return store.query(tags=tags)

# Pattern 4: Error analysis
auditor = get_error_auditor()
stats = auditor.get_stats()
print(f"Total errors: {stats['total_errors']}")

hotspots = auditor.get_hotspots(top_n=5)
for operation, count in hotspots:
    print(f"{operation}: {count} failures")
```

## Notification Workflow

Create multi-channel notifications for important events.

```python
from crew.notifications import NotificationManager

nm = NotificationManager()

# Create important notification with immediate delivery
notif = nm.create(
    title="Research Finding Confirmed",
    body="Attention mechanism hypothesis validated with 95% confidence",
    severity="important",
    source="validation_agent",
    tags=["research", "breakthrough"],
    auto_deliver=True
)

# Create batch of notifications to deliver later
notifications = []
for finding in findings:
    n = nm.create(
        title=f"Finding: {finding.title}",
        body=finding.description,
        severity="info",
        auto_deliver=False  # Deliver in batch later
    )
    notifications.append(n)

# Later, deliver all at once
for notif in notifications:
    nm.deliver(notif.id)

# Check delivery status
unread = nm.get_unread()
print(f"Unread notifications: {len(unread)}")

# Get statistics
stats = nm.stats()
print(f"Delivered: {stats['total_notifications'] - stats['unread']}")
```

## Context Handoff for Long-Running Tasks

Seamlessly resume long-running tasks with context preservation.

```python
from crew.handoff import get_handoff_manager

hm = get_handoff_manager()
task_id = 42

# During execution, check if context is filling up
context_used = 6000  # tokens
context_limit = 8000  # tokens

if hm.should_handoff(context_used, context_limit):
    # Time to hand off - save current generation
    handoff = hm.create(task_id=task_id, generation=1)

    # Save all important state
    handoff.context_summary = "Current progress: tested 50 hypotheses, found 3 promising..."
    handoff.task_checkpoint = current_results
    handoff.current_direction = "exploring attention mechanisms"

    hm.save(handoff)
    print(f"Handoff saved for task {task_id} gen 1")

    # New context window picks up from generation 1
    return "CONTEXT_FULL"

# Later, in a new context window:
def resume_task(task_id):
    handoff = hm.get_current(task_id)
    if handoff:
        # Reconstruct from summary
        context = hm.generate_summary_for_context(handoff)
        print(f"Resuming gen {handoff.generation}: {context}")
        # Continue from where we left off
    else:
        # First generation of this task
        pass
```

## Trigger-Driven Task Creation

Automatically create tasks based on external events.

```python
from crew.triggers import TriggerDaemon
from crew.scheduler import Scheduler

daemon = TriggerDaemon()
scheduler = Scheduler()

# Configure triggers
triggers = [
    {
        'id': 1,
        'name': 'arxiv_new_papers',
        'type': 'RSS',
        'source': {'url': 'https://arxiv.org/rss/cs.LG'},
        'filter': {
            'keywords': ['transformer', 'attention'],
            'cooldown_minutes': 60,
            'max_fires_per_day': 5
        },
        'action': 'create_research_task',
        'enabled': True
    },
    {
        'id': 2,
        'name': 'daily_maintenance',
        'type': 'Schedule',
        'source': {'cron': '0 2 * * *'},  # 2 AM daily
        'action': 'run_gc',
        'enabled': True
    }
]

for trigger_config in triggers:
    daemon.add_trigger(trigger_config)

# Start monitoring
daemon.start()

# Triggers fire automatically and create tasks:
# - arxiv_new_papers fires when paper matches, creates research task
# - daily_maintenance fires at 2 AM, creates maintenance task

# Check what fired
stats = daemon.stats()
print(f"Fired today: {stats['fired_today']}")
print(f"Next check: {stats['next_check_time']}")

# Clean up
daemon.stop()
```

## System Observability

Monitor and diagnose system health.

```python
from crew.error_handling import get_error_auditor
from crew.daemon_integration import get_daemon_integration
from crew.messaging.bus import MessageBus

# Overall system status
di = get_daemon_integration()
stats = di.get_stats()

print(f"Knowledge entries: {stats['total_knowledge_entries']}")
print(f"Message queue depth: {stats['message_queue_depth']}")
print(f"Notifications sent: {stats['total_notifications']}")

# Message bus health
bus = MessageBus()
depths = bus.get_queue_depths()

print(f"Pending: {depths['by_status']['pending']}")
print(f"Processing: {depths['by_status']['processing']}")
print(f"Failed: {depths['by_status']['failed']}")

for agent, count in depths['by_agent'].items():
    if count > 50:
        print(f"⚠️ Agent {agent} has {count} pending messages!")

# Error hotspots
auditor = get_error_auditor()
hotspots = auditor.get_hotspots(top_n=5)

print("\nTop error sources:")
for operation, count in hotspots:
    print(f"  {operation}: {count} errors")

# Recent errors
recent = auditor.get_stats()['recent_errors'][-5:]
for err in recent:
    print(f"  [{err['severity']}] {err['component']}.{err['operation']}")
```

## Complete Task Execution Flow

End-to-end example with all components working together.

```python
from crew.scheduler import Task
from crew.daemon_integration import get_daemon_integration
from crew.knowledge import get_knowledge_store
from crew.adaptive import get_adaptive_scheduler
from crew.notifications import NotificationManager
from crew.handoff import get_handoff_manager

def execute_research_task(task: Task):
    """Execute a research task with full system integration."""

    di = get_daemon_integration()
    store = get_knowledge_store()
    scheduler = get_adaptive_scheduler()
    nm = NotificationManager()
    hm = get_handoff_manager()

    # Phase 1: Planning
    print(f"Starting task {task.id}: {task.title}")

    # Get hints from existing knowledge
    hints = di.enhance_experiment_planning(task)

    # Get direction priority boost
    priority_boost = scheduler.compute_priority_adjustment(task)
    task.priority *= priority_boost

    # Phase 2: Execution
    context_tokens = 0
    findings = []

    for experiment_num in range(5):
        # Check if context is full
        if hm.should_handoff(context_tokens, 8000):
            handoff = hm.create(task_id=task.id, generation=1)
            hm.save(handoff)
            print(f"Context full, saved handoff")
            break

        # Run experiment
        result = run_experiment(task, hints)
        findings.extend(result.findings)
        context_tokens += result.tokens_used

        # Notify on major findings
        if result.confidence > 0.9:
            nm.create(
                title=f"High-confidence finding in task {task.id}",
                body=result.findings[0],
                severity="important",
                auto_deliver=True
            )

    # Phase 3: Learning
    # Store findings as knowledge
    di.create_knowledge_from_findings(
        task,
        findings,
        experiments_run=5
    )

    # Update adaptive scheduler
    scheduler.update_from_task_result(
        task,
        findings=findings,
        success_rate=len([f for f in findings if f.validated]) / len(findings),
        compute_hours=2.5,
        num_knowledge_entries=len(findings)
    )

    # Phase 4: Completion
    print(f"Task {task.id} complete, learned {len(findings)} findings")

    # Notify completion
    nm.create(
        title=f"Task {task.id} complete",
        body=f"Generated {len(findings)} findings",
        severity="info",
        auto_deliver=True
    )

# Execute the task
task = Task(
    id=1,
    title="Explore mixed precision training",
    tags=["training", "optimization"]
)
execute_research_task(task)
```

## Configuration-Driven Setup

Use config.yaml to set up the entire system.

```yaml
# data/config.yaml

crew:
  name: "AutoClaw Research Crew"
  personality: "balanced"

llm:
  provider: "anthropic"
  model: "claude-opus-4-6"
  api_key: "${ANTHROPIC_API_KEY}"

knowledge:
  max_entries: 500
  cleanup_days: 30  # Auto-remove unvalidated entries older than 30 days

triggers:
  enabled: true
  default_poll_minutes: 30
  triggers:
    - id: 1
      name: arxiv_monitor
      type: RSS
      source:
        url: https://arxiv.org/rss/cs.LG
      filter:
        keywords: [transformer, attention]
        cooldown_minutes: 60

notifications:
  external_channels:
    - type: webhook
      url: https://hooks.example.com/notify
      headers:
        Authorization: "Bearer token"
    - type: email
      smtp_host: smtp.gmail.com
      sender: crew@example.com
      recipients: [captain@example.com]

experiments:
  time_budget_seconds: 300
  git_commit_each: false
  keep_checkpoints: best_only

adaptive:
  enabled: true
  thompson_samples_per_decision: 100

flowstate:
  enabled: true
  default_budget_gb: 10.0
  default_budget_hours: 4.0

hardware:
  profile: null  # Auto-detect
```

Then load and use:

```python
import yaml
from pathlib import Path

config = yaml.safe_load(Path("data/config.yaml").read_text())

# Configure each component
from crew.knowledge import get_knowledge_store
store = get_knowledge_store()
store.max_entries = config['knowledge']['max_entries']

from crew.notifications import NotificationManager
nm = NotificationManager()
nm.load_channels(config['notifications']['external_channels'])

from crew.triggers import TriggerDaemon
daemon = TriggerDaemon()
for trigger in config['triggers'].get('triggers', []):
    daemon.add_trigger(trigger)
daemon.start()
```

## See Also

- [API Reference](API_REFERENCE.md) - Detailed method documentation
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [Deployment Guide](DEPLOYMENT.md) - Production deployment
