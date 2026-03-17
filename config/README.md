# Configuration

All configuration files for AutoResearch. These are YAML-based and easy to edit.

## 📋 Directory Structure

```
config/
├── system.yaml              # Main system configuration
├── retention-policies.yaml  # Data lifecycle management
├── agents/                  # Agent profiles (YAML)
│   ├── default.yaml
│   ├── hyperparameter-specialist.yaml
│   ├── architecture-explorer.yaml
│   ├── optimizer-researcher.yaml
│   └── synthesis-agent.yaml
└── services/                # API service templates
    ├── openai.yaml
    ├── anthropic.yaml
    ├── chinese-apis.yaml
    └── local-services.yaml
```

## 🎯 Main Configuration File: `system.yaml`

This is the primary configuration created by the setup wizard:

```yaml
system:
  institution: "Your Institution"
  username: "Your Name"
  gpu:
    mode: "all"  # or "specific" / "cpu"
    indices: [0, 1]  # if specific
  cache_dir: "/home/user/.cache/autoresearch"

services:
  # Services are defined in services/ subdirectory

research:
  template: "technical_wiki"
  focus: "Machine Learning Research"

agents:
  num_agents: 4
  collaboration_protocol: "round-robin-debate"

retention:
  hot_storage_days: 1
  warm_storage_days: 30
  cold_storage_days: 180
```

## 🔧 Agent Profiles: `agents/`

Each agent is defined in a YAML file with specialization and resource allocation.

### Example: `hyperparameter-specialist.yaml`

```yaml
name: hyperparameter-specialist
model: gpt-4-turbo                    # Which AI model to use
role: "Hyperparameter Optimization Expert"

gpu_allocation: 0.35                  # % of GPU (0.0 to 1.0)
api_rate_limit: 12000                 # tokens/minute
max_concurrent_experiments: 3

focus: |
  Investigate optimal hyperparameters:
  - Learning rate and scheduling
  - Batch size and gradient accumulation
  - Weight decay and regularization

search_space:
  learning_rate:
    min: 0.0001
    max: 0.1
    scale: "logarithmic"
  batch_size:
    values: [8, 16, 32, 64, 128, 256]

experiment_behavior:
  keep_threshold: 0.01                # Keep if >1% improvement
  log_all_experiments: true
```

### Creating Custom Agents

1. Copy existing agent profile:
   ```bash
   cp config/agents/hyperparameter-specialist.yaml config/agents/my-agent.yaml
   ```

2. Modify key fields:
   ```yaml
   name: my-custom-agent
   focus: "Your research focus"
   gpu_allocation: 0.25
   ```

3. Create prompt file:
   ```bash
   # Create agents/prompts/my-agent.md
   You are a custom research agent...
   ```

4. Start with new agent:
   ```bash
   ar start --agent-profile config/agents/my-agent.yaml
   ```

## 🔌 Service Configuration: `services/`

Pre-commented templates for each AI service provider.

### OpenAI (`openai.yaml`)

```yaml
openai:
  enabled: true
  provider: openai
  base_url: "https://api.openai.com/v1"
  model: "gpt-4-turbo"
  api_key: "your key here"                # Replace with sk-...
  max_tokens: 8000
  rate_limit_tokens_per_minute: 10000
  temperature: 0.7
```

**Setup:**
1. Get API key: https://platform.openai.com/api-keys
2. Replace `"your key here"` with actual key
3. Models available: GPT-4, GPT-4-turbo, GPT-4-mini

### Anthropic (`anthropic.yaml`)

```yaml
# anthropic_opus:
#   enabled: false
#   provider: anthropic
#   base_url: "https://api.anthropic.com"
#   model: "claude-opus-4.6"
#   api_key: "your key here"
```

**Setup:**
1. Uncomment the model you want
2. Get API key: https://console.anthropic.com/
3. Replace `"your key here"`

### Chinese APIs (`chinese-apis.yaml`)

```yaml
# deepseek_v3:
#   enabled: false
#   provider: deepseek
#   base_url: "https://api.deepseek.com/v1"
#   model: "deepseek-v3"
#   api_key: "your key here"
```

**Available Chinese Services:**
- Deepseek (https://api.deepseek.com)
- Qwen (https://dashscope.aliyuncs.com)
- Baichuan (https://api.baichuan-ai.com)
- Zhipu (https://open.bigmodel.cn)
- Doubao (ByteDance)

**Note:** All have international access endpoints for US-based users

### Local Services (`local-services.yaml`)

```yaml
ollama_mistral:
  enabled: false
  provider: ollama
  base_url: "http://localhost:11434/v1"
  model: "mistral"
  api_key: "none"  # No key needed!
  rate_limit_tokens_per_minute: "unlimited"
```

**Setup Local LLMs:**

**Option 1: Ollama (easiest)**
```bash
# Install Ollama: https://ollama.ai
ollama serve &
ollama pull mistral
# Then enable in local-services.yaml
```

**Option 2: vLLM (faster)**
```bash
pip install vllm
vllm serve mistral-7b &
# Then enable in local-services.yaml
```

## 📊 Data Retention: `retention-policies.yaml`

Configure how long data is kept and where:

```yaml
retention:
  default:
    hot_storage_days: 1        # Immediate access (SSD)
    warm_storage_days: 30      # Compressed (cloud)
    cold_storage_days: 180     # Archival (very cheap)
    compress_after_days: 14
    summarize_before_archive: true

  overrides:
    # Keep breakthrough results longer
    - pattern: "experiments/breakthrough_*.json"
      retention_days: 730       # 2 years

    # Never delete published findings
    - pattern: "published_findings/**"
      retention_days: null      # Forever
```

## ✏️ Editing Configurations

All configs are YAML (human-friendly):

```bash
# Edit main config
nano config/system.yaml

# Edit service
nano config/services/openai.yaml

# Edit agent
nano config/agents/hyperparameter-specialist.yaml
```

### YAML Rules
- Keys and values separated by colon and space: `key: value`
- Indentation matters (use spaces, not tabs)
- Strings in quotes: `"value"`
- Comments start with #: `# This is a comment`
- Boolean: `true` or `false`

## 🔄 Configuration Validation

After editing, validate your config:

```bash
# Check system configuration
ar validate config/system.yaml

# Check specific agent
ar validate config/agents/my-agent.yaml

# Check all configurations
ar validate --all
```

## 🎯 Common Configuration Tasks

### Change GPU Allocation
```yaml
# In config/agents/my-agent.yaml
gpu_allocation: 0.25  # Increase to use more GPU
```

### Add API Key
```yaml
# In config/services/openai.yaml
api_key: "sk-proj-..."  # Replace placeholder
```

### Reduce Storage Costs
```yaml
# In config/retention-policies.yaml
warm_storage_days: 14      # Keep less long-term data
compress_after_days: 7     # Archive sooner
```

### Use Local LLM Only
```yaml
# In config/services/local-services.yaml
ollama_mistral:
  enabled: true

# In config/system.yaml
disable_api_services: true  # Skip OpenAI/Anthropic
```

### Add Custom Agent
1. Copy existing: `cp config/agents/default.yaml config/agents/custom.yaml`
2. Edit fields: `name`, `focus`, `gpu_allocation`
3. Run: `ar start --agents 2 --agent-profiles default custom`

## 📚 Further Reading

- **[../README.md](../README.md)** - Main documentation
- **[../CONCEPTS.md](../CONCEPTS.md)** - Understand the system
- **[../ARCHITECTURE.md](../ARCHITECTURE.md)** - Deep technical details
- **[../install/INSTALLATION_GUIDE.md](../install/INSTALLATION_GUIDE.md)** - Detailed setup

## ❓ FAQ

**Q: Can I use multiple AI services at once?**
A: Yes! Enable multiple services and agents can choose which to use.

**Q: How do I change agent specialization?**
A: Edit the `focus` field in the agent's YAML file.

**Q: What happens if an API key expires?**
A: Update the `api_key` field and agents will use the new key automatically.

**Q: Can agents use different models?**
A: Yes, specify `model: gpt-4-turbo` or `model: claude-opus-4.6` per agent.

**Q: How do I add a completely new service type?**
A: Create `config/services/my-service.yaml` following the template format.

---

**All configurations are re-loadable** - edit them while agents are running for most changes to take effect without restart.
