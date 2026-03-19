# AutoClaw for Claude SDK

**Use AutoClaw as a persistent runtime backend for your Claude Code projects.**

---

## What This Enables

When you use AutoClaw from Claude Code:

- **Persistent state** across multiple Claude Code sessions
- **Durable task queue** – no work lost if Claude Code crashes/reloads
- **Knowledge accumulation** – every session adds to a growing knowledge base
- **Agent pools** – spawn multiple agents to work in parallel
- **Cost tracking** – see exactly which APIs were called and how much they cost

---

## Quick Start

### 1. Install AutoClaw

```bash
git clone https://github.com/SuperInstance/autoclaw.git
cd autoclaw
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
crew health
```

### 2. Start the Daemon

```bash
# Terminal 1: Start AutoClaw daemon (runs forever)
crew start --swarm

# Terminal 2: Run your Claude Code project
# Your Claude Code can now call crew commands and the daemon will handle them
```

### 3. Use in Your Claude Code

```python
import subprocess
import json

def submit_task(description: str, tags: list = []):
    """Submit a task to AutoClaw."""
    cmd = ["crew", "add", description] + [f"--tag {t}" for t in tags]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)

def query_knowledge(query: str, min_confidence: float = 0.5):
    """Query accumulated knowledge."""
    cmd = ["crew", "knowledge", "query", query, f"--min-confidence {min_confidence}"]
    result = subprocess.run(cmd, capture_output=True, text=True, json=True)
    return json.loads(result.stdout)

# Example
submit_task("Research transformer architectures", tags=["ml", "research"])
results = query_knowledge("transformer mechanisms")
print(results)
```

---

## Available Commands

```bash
# Submit work
crew add "Your task description"

# Check status
crew health
crew board              # Show task queue
crew agents status      # Show agent pool

# Query knowledge
crew knowledge query --tag "ml" --min-confidence high
crew knowledge query "question about topic"

# Manage resources
crew knowledge gc       # Garbage collect old knowledge
crew cf status         # Check Cloudflare API credits

# Control the daemon
crew start             # Start in foreground
crew start --daemon    # Start as background service
crew stop              # Stop gracefully
```

---

## Architecture

```
Your Claude Code
    ↓
    (subprocess calls)
    ↓
crew CLI (client)
    ↓
Message Bus (SQLite) ←→ Durable State
    ↓
Agent Pool (Researcher, Teacher, Critic, Distiller, ...)
    ↓
Knowledge Store (Hot/Warm/Cold tiers)
    ↓
External APIs (Anthropic, OpenAI, Web search, etc.)
```

---

## Memory & State Persistence

AutoClaw stores everything in `data/`:

```
data/
├── messages.db          # Message bus (pending, completed, failed messages)
├── agents/              # Agent state per instance
│   ├── researcher_1/state.yaml
│   └── teacher_1/state.yaml
├── knowledge/           # Knowledge store (hot/warm/cold tiers)
│   ├── hot/
│   ├── warm/knowledge.db
│   └── cold/archive-{date}.gz
└── results/             # Task results
```

If the daemon crashes:
1. Incomplete tasks remain in the message bus (pending)
2. Agents restart and pick them up
3. Knowledge is fully recovered
4. No work is lost

---

## Configuration for Claude Code

If you need AutoClaw to behave differently in your project, create a config:

```yaml
# crew/config/claude_code.yaml
resource_limits:
  max_memory_mb: 512
  max_llm_calls_per_hour: 100
  max_web_searches_per_hour: 30

scheduling:
  max_pending_tasks: 50
  task_timeout_seconds: 1800

knowledge:
  hot_tier_entries: 500
  warm_tier_entries: 50000
```

Then start with:
```bash
crew start --config crew/config/claude_code.yaml
```

---

## Example: Multi-Agent Research Pipeline

```python
import subprocess
import time

def run_research_pipeline(topic: str):
    """Research pipeline: web search → synthesis → Q&A generation."""

    # 1. Submit task (goes to Researcher agent)
    print(f"📚 Researching: {topic}")
    subprocess.run(["crew", "add", f"Research {topic}", "--tag", "research"])

    # 2. Wait for agents to work
    time.sleep(30)

    # 3. Query accumulated knowledge
    print(f"🧠 Querying knowledge...")
    result = subprocess.run(
        ["crew", "knowledge", "query", topic, "--export-jsonl", f"{topic}.jsonl"],
        capture_output=True
    )

    # 4. Results in JSONL format (ready for fine-tuning, RAG, etc.)
    print(f"✅ Results exported to {topic}.jsonl")

    return f"{topic}.jsonl"

# Run it
dataset = run_research_pipeline("LLM scaling laws")
```

---

## Extending with Custom Agents

Create a new agent type:

```python
# my_custom_agent.py
from crew.agents.base import BaseAgent
from crew.messaging.bus import Message
from typing import List, Optional

class MyCustomAgent(BaseAgent):
    ROLE = "my_custom_role"

    def get_capabilities(self) -> List[str]:
        return ["custom_task", "analysis"]

    def process_message(self, message: Message) -> Optional[Message]:
        if message.type == "task_request":
            # Your custom logic here
            reply = Message(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                type="result",
                payload={"result": "..."}
            )
            return reply
        return None

    def idle_work(self):
        pass  # Optional background work

# Use it
if __name__ == "__main__":
    agent = MyCustomAgent("custom_1")
    agent.start()
    # ... stays running in background
```

Register it with AutoClaw:

```bash
crew agents spawn --role my_custom_role --count 2
crew board  # See tasks flowing to your agent
```

---

## Cost Tracking

AutoClaw logs all API calls:

```bash
# See all API usage
crew logs show --filter "api_call"

# Check costs by provider
crew cf status

# Export billing data
crew logs export --format csv > billing.csv
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Agents not picking up tasks | `crew agents status` – are they running? `crew start --swarm` |
| High memory usage | `crew knowledge gc --aggressive` |
| API rate limiting | `crew cf status` – check credit usage |
| Tasks timing out | Increase `task_timeout_seconds` in config |
| Can't connect to daemon | Ensure `crew start` ran in another terminal |

---

**AutoClaw + Claude Code = persistent, scalable, cost-conscious AI development.**
