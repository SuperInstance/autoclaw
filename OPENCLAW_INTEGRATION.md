# AutoClaw for OpenClaw – Complete Integration Guide

**AutoClaw is built for OpenClaw.** This guide shows how an OpenClaw agent uses AutoClaw as a runtime.

---

## The Big Picture

```
OpenClaw (your AI orchestrator)
    ↓
AutoClaw Runtime (durable, scalable foundation)
    ├── Message Bus (SQLite – persists everything)
    ├── Agent Pool (CPU, GPU, cloud API selection)
    ├── Knowledge Store (hot/warm/cold tiers)
    ├── Scheduler (task board + priority queue)
    └── Health Monitoring (resource guardrails)
    ↓
External APIs (Anthropic, OpenAI, web search, etc.)
Optional: CudaClaw GPU Swarm (if heavy compute needed)
```

---

## Installation for OpenClaw

### Prerequisite: OpenClaw Setup

Ensure your OpenClaw environment has:
- Python 3.10+
- `git` installed
- API keys (Anthropic, OpenAI, etc.) in environment or config

### Step 1 – Clone the Repo

```bash
git clone https://github.com/SuperInstance/autoclaw.git ~/autoclaw
cd ~/autoclaw
```

### Step 2 – Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3 – Verify Installation

```bash
python3 -m crew health
```

Expected output:
```
✅ System Healthy
CPU: 42% | Disk: 156 GB free | Memory: 3.2 / 8 GB
Message Bus: OK (0 pending, 0 processing)
Agent Pool: Ready (0 agents idle)
Knowledge Store: Hot=0, Warm=0, Cold=0
```

### Step 4 – Start the Daemon

```bash
# In a long-running terminal (or systemd service)
python3 -m crew start --daemon

# Verify it's running
python3 -m crew health
```

---

## OpenClaw Agent Integration

Your OpenClaw agent should:

1. **Check AutoClaw availability** before submitting work
2. **Submit tasks** via CLI or message bus
3. **Monitor progress** via health checks and task board
4. **Query results** from the knowledge store
5. **Respect resource guardrails** (see `policy/resource_policy.yaml`)

### Integration Pattern

```python
import subprocess
import json
import os
from pathlib import Path

class OpenClawAutoClawBridge:
    """OpenClaw ↔ AutoClaw integration."""

    def __init__(self, autoclaw_root: str = None):
        self.root = Path(autoclaw_root or "~/autoclaw").expanduser()
        if not (self.root / "crew").exists():
            raise RuntimeError(f"AutoClaw not found at {self.root}")

    def health(self) -> dict:
        """Get AutoClaw system health."""
        result = subprocess.run(
            ["python3", "-m", "crew", "health", "--json"],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def submit_task(self, description: str, tags: list = None, priority: int = 5):
        """Submit a task to AutoClaw agents."""
        cmd = ["python3", "-m", "crew", "add", description]
        if tags:
            for tag in tags:
                cmd.extend(["--tag", tag])
        cmd.extend(["--priority", str(priority)])
        result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True)
        return result.stdout

    def query_knowledge(self, query: str, min_confidence: float = 0.5, tags: list = None):
        """Query accumulated knowledge."""
        cmd = ["python3", "-m", "crew", "knowledge", "query", query,
               "--min-confidence", str(min_confidence), "--json"]
        if tags:
            for tag in tags:
                cmd.extend(["--tag", tag])
        result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True)
        return json.loads(result.stdout)

    def get_task_board(self) -> dict:
        """View current task queue."""
        result = subprocess.run(
            ["python3", "-m", "crew", "board", "--json"],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def agent_pool_status(self) -> dict:
        """Check active agents."""
        result = subprocess.run(
            ["python3", "-m", "crew", "agents", "status", "--json"],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

# Usage
bridge = OpenClawAutoClawBridge()

# 1. Check if AutoClaw is healthy
health = bridge.health()
if health["status"] != "healthy":
    print("❌ AutoClaw not ready")
    exit(1)

# 2. Check resource limits before submitting
policy = yaml.safe_load(open(bridge.root / "policy/resource_policy.yaml"))
if health["agent_pool"]["active"] >= policy["cpu"]["agent_pool_max"]:
    print("⚠️  Agent pool at capacity. Waiting...")
    # Implement backoff logic

# 3. Submit task
print("📝 Submitting task to AutoClaw...")
bridge.submit_task(
    "Research transformer architectures",
    tags=["ml", "research"],
    priority=7
)

# 4. Monitor
print("⏳ Waiting for agents...")
import time
time.sleep(60)

# 5. Query results
results = bridge.query_knowledge("transformers", min_confidence=0.7)
print(f"✅ Found {len(results)} results")
for item in results[:3]:
    print(f"  - {item['summary'][:100]}...")
```

---

## Skill: `/autoclaw` (for Claude Code integration)

When you invoke `/autoclaw` in a Claude Code session, it:

1. Checks if AutoClaw daemon is running
2. Submits your task
3. Streams progress
4. Returns structured results

**Usage from Claude Code:**

```
/autoclaw Research the latest advances in diffusion models
```

The skill is defined in `.claude/commands/autoclaw.md`. It uses the integration pattern above.

---

## Configuration for OpenClaw

### SOUL – Identity & Operating Principles

Read `SOUL.md` for:
- How AutoClaw thinks
- Operating directives
- Fallback strategies
- Resource philosophy

### Policy – Resource Constraints

Edit `policy/resource_policy.yaml` to match your environment:

```yaml
cpu:
  agent_pool_max: 4        # Run max 4 agents simultaneously
api:
  anthropic:
    daily_cost_limit_usd: 50.0
disk:
  minimum_free_gb: 2.0
```

Then load it:

```bash
python3 -m crew start --config policy/resource_policy.yaml
```

---

## Common Workflows

### Workflow 1: One-Off Research Task

```python
bridge = OpenClawAutoClawBridge()
bridge.submit_task("Research the history of neural networks", tags=["research"])
time.sleep(120)  # Wait for agents
results = bridge.query_knowledge("neural network history")
print(json.dumps(results, indent=2))
```

### Workflow 2: Parallel Data Processing

```python
items = ["topic1", "topic2", "topic3", ...]
for item in items:
    bridge.submit_task(f"Extract key insights from {item}", priority=5)

# Monitor progress
for _ in range(60):  # 5 minutes
    board = bridge.get_task_board()
    print(f"Pending: {board['pending']}, Completed: {board['completed']}")
    time.sleep(5)

# Get all results
results = bridge.query_knowledge("insights", tags=["extracted"])
```

### Workflow 3: Knowledge Accumulation Over Time

```python
# Day 1
bridge.submit_task("Research LLMs", tags=["day-1"])
time.sleep(3600)

# Day 2 – query what we learned
knowledge = bridge.query_knowledge("LLM", min_confidence=0.8)

# Day 3 – add more
bridge.submit_task("Research transformers", tags=["day-3"])
```

---

## Monitoring & Health

### Real-time Health Checks

```bash
# Watch system continuously
python3 -m crew health --watch --interval 10

# Export metrics (Prometheus format)
python3 -m crew health --format prometheus > metrics.txt
```

### Logging

```bash
# Show recent logs
python3 -m crew logs show --tail 50

# Filter by level
python3 -m crew logs show --level ERROR

# Export for analysis
python3 -m crew logs export --format json > logs.jsonl
```

### Task Board

```bash
# See all tasks
python3 -m crew board

# Show only pending
python3 -m crew board --status pending

# Export for reporting
python3 -m crew board --export csv > tasks.csv
```

---

## Cost Management

### Check Cloudflare Credits

```bash
python3 -m crew cf status
# Output:
# Anthropic: 42% of daily limit used
# Mistral: 5% used
# Auto-burn at 85% threshold
```

### Export Billing Data

```bash
python3 -m crew logs export --format json | \
  jq '.[] | select(.event=="api_call") | {provider, tokens, cost}' | \
  python3 -m json.tool > costs.json
```

---

## Error Handling

### Task Failures

If a task fails (agent error, API timeout, etc.):

```python
board = bridge.get_task_board()
failed = [t for t in board["tasks"] if t["status"] == "failed"]
for task in failed:
    print(f"Failed: {task['description']}")
    print(f"Error: {task['error_message']}")
    # Decide: retry, skip, escalate to human
```

### Resource Exhaustion

If AutoClaw hits resource limits:

```python
health = bridge.health()
if health["memory_percent"] > 85:
    print("⚠️  Memory pressure")
    bridge.root # Path to data dir
    subprocess.run(["python3", "-m", "crew", "knowledge", "gc", "--aggressive"])
```

---

## Advanced: Custom Agent Roles

AutoClaw comes with: Researcher, Teacher, Critic, Distiller.

To add custom roles:

1. Create agent class:
```python
# crew/agents/my_custom_agent.py
from crew.agents.base import BaseAgent

class MyAgent(BaseAgent):
    ROLE = "my_role"
    def get_capabilities(self): return ["custom_capability"]
    def process_message(self, msg): ...
```

2. Register with OpenClaw:
```bash
python3 -m crew agents spawn --role my_role --count 2
```

3. Task routing:
```bash
python3 -m crew add "task" --route my_role
```

---

## Next Steps

1. **Read `SOUL.md`** – Understand AutoClaw's philosophy
2. **Review `policy/resource_policy.yaml`** – Set appropriate limits
3. **Test the CLI** – Submit a few tasks manually
4. **Integrate programmatically** – Use the bridge pattern above
5. **Deploy to production** – Use systemd or Docker (see `docs/DEPLOYMENT.md`)

---

**AutoClaw + OpenClaw = Durable, scalable, cost-conscious AI orchestration.**
