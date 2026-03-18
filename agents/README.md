# Agents System

The agent orchestration system that coordinates multi-agent research.

## 📋 Directory Structure

```
agents/
├── agent-manager.py              # Core orchestration
├── cli-interface.py              # Command-line interface
├── dashboard.py                  # Real-time monitoring
├── resource-allocator.py         # GPU/API management
├── collaboration-framework.py    # Agent debate/discussion
├── prompts/                      # Agent instruction files
│   ├── hyperparameter-specialist.md
│   ├── architecture-explorer.md
│   ├── optimizer-researcher.md
│   └── synthesis-agent.md
└── tools/                        # Research tools
    ├── run_experiment.py         # Execute autoresearch
    ├── modify_train.py           # Modify train.py
    └── parse_results.py          # Parse metrics
```

## 🤖 What Are Agents?

Agents are AI-driven researchers that:
- Run experiments on a **fixed 5-minute budget**
- **Modify code** (train.py) to test hypotheses
- **Evaluate results** (did val_bpb improve?)
- **Keep improvements, discard failures**
- **Collaborate** with other agents on discoveries

## 🎯 Agent Types

### 1. Hyperparameter Specialist
- **Focus:** Learning rate, batch size, weight decay
- **Goal:** Find optimal hyperparameter configuration
- **GPU Allocation:** 35% (default)
- **Speed:** 12 experiments/hour

### 2. Architecture Explorer
- **Focus:** Model depth, width, attention patterns
- **Goal:** Discover better model architectures
- **GPU Allocation:** 30% (default)
- **Speed:** 12 experiments/hour

### 3. Optimizer Researcher
- **Focus:** Optimizer selection and tuning
- **Goal:** Compare Adam, SGD, Muon, custom optimizers
- **GPU Allocation:** 20% (default)
- **Speed:** 12 experiments/hour

### 4. Synthesis Agent
- **Focus:** Aggregate findings, identify patterns
- **Goal:** Create coherent research narratives
- **GPU Allocation:** 10% (default)
- **Speed:** Continuous analysis

## 🚀 Running Agents

### Start Single Agent
```bash
ar start --agents 1

# Monitor
ar status
ar metrics --last 1h
```

### Start Multi-Agent Swarm
```bash
ar start --agents 4

# View each agent's progress
ar status
ar chat hyperparameter-specialist
ar chat synthesis-agent
```

### Custom Agent Configuration
```bash
ar start --agents 2 --agent-profiles custom1 custom2
```

## 💬 Interacting with Agents

### Chat with an Agent
```bash
ar chat hyperparameter-specialist

> "What's the best learning rate you've found?"
Agent: "Based on my experiments, LR=0.04 is optimal..."

> "Try batch size 64"
Agent: "Running experiment with BS=64..."

> "exit"
```

### Guide Agent Focus
```bash
# Change what an agent is researching
ar focus architecture-explorer "test depth 10 specifically"

# View agent's current focus
ar chat architecture-explorer
> "What are you working on?"
```

### Adjust Agent Priority
```bash
# Give more GPU to an agent
ar priority --increase hyperparameter-specialist

# Reduce API budget for another
ar priority --decrease optimizer-researcher
```

## 📊 Monitoring Agents

### Check Status
```bash
ar status

# Output:
# hyperparameter-specialist: 47/100 experiments, val_bpb=0.984
# architecture-explorer: 28/100 experiments, val_bpb=1.002
# optimizer-researcher: 12/100 experiments (idle, waiting)
# synthesis-agent: analyzing, 3/5 rounds
```

### View Real-Time Dashboard
```bash
ar dashboard

# Shows:
# - Progress bars for each agent
# - GPU/API resource usage
# - Best result so far
# - Experiment metrics
```

### Get Detailed Metrics
```bash
# Last hour of metrics
ar metrics --last 1h

# Plot val_bpb improvement
ar metrics --graph val_bpb

# Export to JSON
ar metrics --format json > metrics.json
```

## 🛠️ Agent Customization

### Create Custom Agent

1. **Copy template:**
   ```bash
   cp config/agents/default.yaml config/agents/my-agent.yaml
   ```

2. **Edit configuration:**
   ```yaml
   name: my-agent
   model: gpt-4-turbo
   focus: "Your research focus"
   gpu_allocation: 0.25
   ```

3. **Create prompt file:**
   ```bash
   cat > agents/prompts/my-agent.md << 'EOF'
   You are a specialized research agent focused on...
   Your goal is to...
   You have access to these tools: run_experiment, modify_train, parse_results
   EOF
   ```

4. **Start agent:**
   ```bash
   ar start --agents 1 --agent-profile config/agents/my-agent.yaml
   ```

### Agent Configuration Fields

| Field | Purpose | Example |
|-------|---------|---------|
| `name` | Unique identifier | `my-agent` |
| `model` | AI model to use | `gpt-4-turbo` |
| `gpu_allocation` | % of GPU (0.0-1.0) | `0.25` |
| `api_rate_limit` | tokens/min | `12000` |
| `focus` | Research objective | `"Test learning rates"` |
| `strategy` | Exploration method | `grid-search` |
| `keep_threshold` | Min improvement % | `0.01` |
| `parallelism` | Concurrent experiments | `3` |

## 🤝 Agent Collaboration

### How Agents Work Together

1. **Knowledge Sharing:** Agents share interesting findings
2. **Debate Protocol:** Agents debate disputed discoveries
3. **Consensus Building:** Synthesis agent mediates disagreements
4. **Cross-Pollination:** Insights from one agent inform others

### Example Debate

```
Hyperparameter Agent: "LR=0.04 is optimal"
Architecture Agent: "But at depth=10, LR=0.02 is better"
Synthesis Agent: "Both might be right - dependency on architecture!
                  Recommend: LR depends on depth"
```

### Enable Collaboration
```yaml
# In config/agents/my-agent.yaml
communication:
  team: ["architecture-explorer", "synthesis-agent"]
  frequency_minutes: 30
```

## 🔧 Available Tools for Agents

### run_experiment(hyperparameters)
Execute a 5-minute training experiment
```python
result = run_experiment({
    'learning_rate': 0.04,
    'batch_size': 32,
    'weight_decay': 0.01
})
# Returns: {'val_bpb': 0.984, 'memory_gb': 42, 'time_seconds': 285}
```

### modify_train(changes)
Modify train.py with new parameters
```python
modify_train({
    'LEARNING_RATE': 0.04,
    'DEVICE_BATCH_SIZE': 32,
    'WEIGHT_DECAY': 0.01
})
```

### parse_results(log_file)
Extract metrics from experiment logs
```python
metrics = parse_results('run.log')
# Returns: {'val_bpb': 0.984, 'peak_memory_gb': 42, ...}
```

## 📈 Agent Performance

### Typical Metrics
- **Experiments/hour:** 12 per agent
- **API cost:** $2-5/hour per agent (with GPT-4)
- **GPU memory:** 35-40GB per agent (H100)
- **Improvement per hour:** 0.5-2% on val_bpb

### Optimization Tips

**For Speed:**
- Use GPT-4-mini instead of GPT-4 (2x faster, slightly less capable)
- Use local models (Ollama) - 0 API cost
- Reduce `max_concurrent_experiments` to 1 (faster per-experiment)

**For Cost:**
- Use Claude Haiku instead of Claude Opus
- Use local models (Ollama, vLLM) - free!
- Reduce `api_rate_limit` to lower throughput
- Use fewer agents

**For Quality:**
- Use Claude Opus or GPT-4 (most capable)
- Increase `gpu_allocation` for more data
- More agents = more parallel exploration

## 🐛 Debugging Agents

### View Agent Logs
```bash
# Last 100 lines of agent logs
ar logs hyperparameter-specialist --tail 100

# All logs from past hour
ar logs hyperparameter-specialist --since 1h

# Search logs
ar logs hyperparameter-specialist --grep "error"
```

### Check Agent Health
```bash
# Is agent responsive?
ar health hyperparameter-specialist

# GPU memory usage
ar resources --agent hyperparameter-specialist

# API rate limit usage
ar api-stats hyperparameter-specialist
```

### Stop Misbehaving Agent
```bash
ar stop hyperparameter-specialist

# Restart it
ar start --agents 1 --agent-profile hyperparameter-specialist
```

## 📚 Agent Prompts

Each agent has an instruction file in `agents/prompts/`:

- `hyperparameter-specialist.md` - HyperParameter tuning instructions
- `architecture-explorer.md` - Architecture search instructions
- `optimizer-researcher.md` - Optimizer comparison instructions
- `synthesis-agent.md` - Synthesis and debate instructions

### Editing Agent Prompts
```bash
# Edit how hyperparameter specialist thinks
nano agents/prompts/hyperparameter-specialist.md

# Agent picks up new instructions on next run
ar restart hyperparameter-specialist
```

### Prompt Best Practices
- Be specific about research objective
- Provide examples of good/bad discoveries
- Include success criteria
- Document constraints (GPU, API budget)

## 🎓 Learning More

- **[../README.md](../README.md)** - Main documentation
- **[../ARCHITECTURE.md](../ARCHITECTURE.md)** - Agent architecture details
- **[../CONCEPTS.md](../CONCEPTS.md)** - Core concepts
- **[../config/README.md](../config/README.md)** - Agent configuration

## ❓ FAQ

**Q: Can agents share context?**
A: Yes, via synthesis agent and shared knowledge graph

**Q: What if an agent gets stuck?**
A: You can manually reset: `ar reset agent-name`

**Q: How do agents handle failures?**
A: Failures are logged and analyzed for patterns

**Q: Can I create agent chains?**
A: Yes, one agent can trigger another via collaboration framework

**Q: What's the max number of agents?**
A: Limited by GPU memory and API budget (typically 4-8)

---

**Ready to run agents?** Start with `ar start --agents 1` 🚀
