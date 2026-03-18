# AutoClaw Troubleshooting Guide

## Common Issues and Solutions

### Knowledge Store Issues

#### "Knowledge entry not found"
**Symptom**: Query returns empty results for expected entries

**Causes**:
1. Entry was auto-pruned (older than 30 days without validation)
2. Query filters too restrictive
3. Tags or category don't match

**Solutions**:
```python
# Check what's actually in the store
from crew.knowledge import get_knowledge_store
store = get_knowledge_store()

# View all entries
for entry in store.entries.values():
    print(f"ID: {entry.id}, Tags: {entry.tags}, Status: {entry.status}")

# Query with looser filters
results = store.query()  # Get all
```

#### "Entry exceeds max size (500 entries)"
**Symptom**: New knowledge entries automatically deleted

**Cause**: Store reached max 500 entries, auto-pruning removed oldest low-confidence entries

**Solution**:
1. Review high-confidence entries more frequently
2. Increase validation tasks to maintain entries longer
3. Adjust max_entries in config

#### "Contradiction detection too aggressive"
**Symptom**: Related but different findings flagged as contradictions

**Cause**: Heuristic keyword matching is simple (looks for antonym keywords)

**Solution**:
```python
# Manually review contradictions
contradictions = store.detect_contradictions(entry_id)

# Un-mark if false positive
store.update(entry_id, contradicting_entries=[])
```

---

### Trigger Issues

#### "Trigger never fires"
**Symptom**: Configured trigger doesn't create tasks

**Causes**:
1. Trigger disabled
2. Trigger doesn't match RSS entries
3. Cooldown prevents firing
4. Network error fetching RSS

**Debug**:
```python
from crew.triggers import TriggerDaemon

daemon = TriggerDaemon()
triggers = daemon.list_triggers()

# Check trigger status
for t in triggers:
    print(f"ID: {t['id']}, Name: {t['name']}, Enabled: {t['enabled']}")

# Manual test
handler = RSSHandler(trigger_id=1, config=trigger_config)
events = handler.check()
print(f"Found {len(events)} events")
```

**Solutions**:
- Check trigger is enabled: `daemon.enable_trigger(trigger_id)`
- Verify RSS URL is accessible
- Check keyword filters match actual entries
- Review log for errors

#### "Trigger fires too frequently"
**Symptom**: Too many tasks created

**Causes**:
1. Cooldown too short
2. Filter too broad

**Solutions**:
```yaml
# In trigger config:
filter:
  cooldown_minutes: 60        # Increase this
  max_fires_per_day: 5        # Or decrease this
  keywords: [more, specific]  # Make filters stricter
```

---

### Message Bus Issues

#### "Messages accumulating in queue"
**Symptom**: `get_queue_depths()` shows thousands of pending messages

**Causes**:
1. Agent processing slow or crashed
2. Message payload too large (agent OOM)
3. Circular message routing

**Debug**:
```python
from crew.messaging.bus import MessageBus

bus = MessageBus()
depths = bus.get_queue_depths()

print(f"Total pending: {depths['by_status']['pending']}")

# Check for specific agent queue
for agent, count in depths['by_agent'].items():
    if count > 100:
        print(f"Agent {agent} has {count} pending messages")
```

**Solutions**:
1. Check agent is running: look for agent process
2. Restart agent if stuck
3. Reduce message payload size
4. Add message TTL to prevent indefinite accumulation

```python
# Set message TTL
msg_id = bus.publish(Message(
    ...,
    expires_in_hours=24.0  # Auto-delete after 24 hours
))
```

#### "Dead letter queue growing"
**Symptom**: Many failed messages

**Causes**:
1. Agent crash/unavailable
2. Message processing error
3. Rate limiting

**Debug**:
```python
# Check dead letter entries
with bus._get_conn() as conn:
    dead = conn.execute("SELECT * FROM dead_letters ORDER BY failed_at DESC LIMIT 10")
    for row in dead:
        print(f"Message {row['original_id']}: {row['reason']}")
```

**Solutions**:
1. Review error reasons
2. Check agent logs for processing errors
3. Reduce message volume if rate-limited
4. Manual intervention to replay critical messages

---

### Agent Issues

#### "Agent keeps crashing"
**Symptom**: Agent status = "stopped", see logs with exceptions

**Causes**:
1. Unhandled exception in process_message()
2. Resource exhaustion (memory, file handles)
3. External API failure

**Debug**:
```python
# Check agent state file
import yaml
from pathlib import Path

agent_state = Path("data/agents/agent_1/state.yaml")
state = yaml.safe_load(agent_state.read_text())

print(f"Status: {state['status']}")
print(f"Errors: {state['errors_count']}")

# Check logs
import subprocess
subprocess.run(["tail", "-100", "/var/log/autoclaw/agents.log"])
```

**Solutions**:
1. Fix the exception in process_message()
2. Add error handling with @handle_error decorator
3. Increase resource limits
4. Implement circuit breaker for external APIs

#### "Agent queue full"
**Symptom**: Agent not processing messages despite available

**Causes**:
1. Agent busy with single long operation
2. Blocking network call in process_message()
3. Infinite loop

**Solution**:
```python
# Add timeout to process_message
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Message processing timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)  # 30 second timeout

try:
    self.process_message(msg)
finally:
    signal.alarm(0)  # Cancel alarm
```

---

### Context Handoff Issues

#### "Context handoff not triggering"
**Symptom**: Task runs to completion without generating handoff

**Cause**: Context usage below 75% threshold

**Solution**: Set lower threshold in daemon.py or increase context limit

#### "Can't resume task from handoff"
**Symptom**: ContextHandoff exists but task doesn't pick it up

**Cause**: Task ID mismatch or generation not loaded

**Debug**:
```python
from crew.handoff import get_handoff_manager

hm = get_handoff_manager()

# Check handoff exists
current = hm.get_current(task_id=1)
if not current:
    print("No handoff for task 1")
else:
    print(f"Found generation {current.generation}")
    print(f"Summary: {hm.generate_summary_for_context(current)[:100]}")
```

---

### Performance Issues

#### "System running slowly"
**Symptom**: Experiments slow, tasks stuck

**Causes**:
1. Knowledge store query slow (many entries)
2. Message bus DB slow (index missing)
3. Notification delivery blocking

**Solutions**:
```python
# Optimize knowledge queries
store.query(
    tags=["specific_tag"],  # Use specific filters
    min_confidence="high"    # Reduce result set
)

# Check message bus indices
# Should have:
# - idx_status (for filtering by status)
# - idx_to_agent (for routing)
# - idx_priority (for ordering)

# Make notifications async
nm.create(..., auto_deliver=False)  # Deliver later
```

#### "High memory usage"
**Symptom**: Process memory growing, eventually OOM

**Causes**:
1. Circular references in message queue
2. Knowledge store not pruning
3. Agent buffer overflowing

**Solutions**:
```python
# Force cleanup
store.cleanup_old_entries(days=7)  # More aggressive

# Set message TTL
bus.publish(msg, expires_in_hours=4)

# Monitor memory
import psutil
proc = psutil.Process()
print(f"Memory: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
```

---

### Notification Issues

#### "Notifications not being delivered"
**Symptom**: Created notification but never received

**Causes**:
1. No channels configured in config.yaml
2. Channel misconfigured (bad URL, invalid SMTP)
3. auto_deliver=False but never manually delivered

**Debug**:
```python
from crew.notifications import NotificationManager

nm = NotificationManager()

# Check configured channels
# Look at logging output when created: "Loaded N channels"

# If 0 channels: add config.yaml notifications section

# Check notification status
unread = nm.get_unread()
for notif in unread:
    print(f"Notif {notif.id}: delivered={notif.delivered}")
```

**Solutions**:
1. Add channels to config.yaml
2. Test each channel individually
3. Enable auto_deliver for important notifications
4. Check firewall/network allows outgoing connections

#### "Webhook delivery failing silently"
**Symptom**: Log shows "notification created" but webhook not called

**Debug**:
```python
# Check webhook channel config
config_yaml = Path("data/config.yaml")
config = yaml.safe_load(config_yaml.read_text())

webhook_config = config['notifications']['external_channels'][0]
print(f"URL: {webhook_config['url']}")

# Test webhook manually
import requests
resp = requests.post(
    webhook_config['url'],
    json={"test": "message"},
    headers=webhook_config.get('headers', {})
)
print(f"Response: {resp.status_code}")
```

---

### Adaptive Scheduler Issues

#### "Direction priority not changing"
**Symptom**: `compute_priority_adjustment()` always returns 0

**Causes**:
1. No tasks completed for this direction yet
2. Task title/tags don't match direction keywords
3. Beta distribution still at default (1.0, 1.0)

**Debug**:
```python
from crew.adaptive import get_adaptive_scheduler

scheduler = get_adaptive_scheduler()
stats = scheduler.stats()

print(f"Tracked directions: {len(stats['directions'])}")
for d in stats['directions']:
    print(f"{d['name']}: tasks={d['tasks_attempted']}, alpha={d['value_distribution']['alpha']}")
```

**Solution**:
- Complete tasks for this direction
- Update task title/tags to match keywords
- Check direction extraction in `_extract_direction()`

---

### Flowstate Issues

#### "Sandbox not cleaning up"
**Symptom**: Old completed sandboxes taking disk space

**Solution**:
```python
from crew.flowstate import get_flowstate_manager

manager = get_flowstate_manager()

# Manual cleanup
manager.cleanup_old_sandboxes(days=7)
```

#### "Can't promote findings from sandbox"
**Symptom**: promote_findings() fails

**Causes**:
1. Flowstate sandbox ID wrong
2. Knowledge store full
3. Files locked

**Solution**:
```python
flow = manager.get(sandbox_id)
if not flow:
    print("Sandbox not found")
else:
    # Check status
    print(f"Status: {flow.status}, Findings: {len(flow.findings)}")

    # Try promoting
    ids = manager.promote_findings(
        sandbox_id,
        findings=["Manually promoting"],
        validation_task_ids=[1, 2]
    )
```

---

## Debug Mode

Enable detailed logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)

# Also enable in config.yaml
daemon:
  log_level: debug
```

## Getting Help

1. **Check logs**: `/var/log/autoclaw/` or daemon output
2. **Run comprehensive tests**: `python3 test_comprehensive_debugging.py`
3. **Use error auditor**: Check `get_error_auditor().get_stats()`
4. **Check circuit breakers**: `CircuitBreaker.status()`
5. **Inspect state files**: Look in `data/` directory YAML files

---

## See Also

- [API Reference](API_REFERENCE.md)
- [Integration Guide](INTEGRATION_GUIDE.md)
