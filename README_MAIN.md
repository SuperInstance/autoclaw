# AutoResearch: Autonomous AI-Driven Research Platform

Welcome to **AutoResearch**, a system that empowers AI agents to conduct research autonomously, continuously improving through experimentation and collaboration.

## 🎯 What Is AutoResearch?

AutoResearch is a framework where:
- **AI agents run experiments autonomously** on a fixed 5-minute budget
- **Agents modify code, train models, evaluate results**, then keep or discard improvements
- **Multiple agents collaborate** investigating different research directions in parallel
- **Research findings auto-populate a semantic wiki** (knowledge graph)
- **All work is validated and archived** with configurable retention policies

Think of it as **"let your AI researchers work while you sleep"** - wake up to detailed research logs and curated findings.

## 📚 Quick Navigation

**New User?** Start here:
- [`install/INSTALLATION_GUIDE.md`](install/INSTALLATION_GUIDE.md) - Step-by-step setup for all platforms
- [`CONCEPTS.md`](CONCEPTS.md) - Clear explanations of core ideas
- [`config/`](config/) - Configuration templates and examples

**Want to understand the system?**
- [`ARCHITECTURE.md`](ARCHITECTURE.md) - Complete technical design
- [`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md) - How to integrate with SuperInstance ecosystem

**Want to run it?**
```bash
# Linux/macOS
bash install/install.sh --interactive

# Windows 11
.\install\install.ps1 -Mode interactive

# Docker (all platforms)
docker-compose -f docker/docker-compose.yml up -d
```

## 📂 Directory Guide

| Directory | Purpose | See Also |
|-----------|---------|----------|
| **`install/`** | Installation scripts and configuration wizard | [README](install/README.md) |
| **`config/`** | Configuration templates and agent profiles | [README](config/README.md) |
| **`agents/`** | Agent orchestration and CLI interface | [README](agents/README.md) |
| **`docker/`** | Docker and containerization setup | [README](docker/README.md) |
| **`results/`** | Experiment results and research outputs | [README](results/README.md) |
| **`docs/`** | Additional documentation | [README](docs/README.md) |

## 🚀 Getting Started (30 seconds)

```bash
# 1. Clone and navigate
git clone https://github.com/SuperInstance/autoclaw.git
cd autoclaw

# 2. Run installer (choose your platform)
# Linux/macOS:
bash install/install.sh --interactive
# Windows 11:
.\install\install.ps1 -Mode interactive
# Docker:
docker-compose -f docker/docker-compose.yml up -d

# 3. You're done! Next: add API keys to config/services/
# Then: ar start --agents 1
```

## 🎓 Learn the Concepts

**AutoResearch Loop:**
1. Agent modifies `train.py` (hyperparameters, architecture, etc.)
2. Trains for exactly 5 minutes
3. Evaluates: Did it improve `val_bpb` (validation bits per byte)?
4. Keeps improvement or discards → Repeat

**Multi-Agent Research:**
- Hyperparameter specialist → tunes LR, BS, WD
- Architecture explorer → tests depth, width, attention
- Optimizer researcher → compares Adam, SGD, Muon
- Synthesis agent → identifies patterns, debates findings

**Knowledge Management:**
- Findings automatically populate semantic wiki (murmur)
- AI-powered backlinks and semantic clustering
- Community voting on research quality
- Complete audit trail

## ⚙️ Key Features

✅ **Easy Installation**
- Interactive wizard walks you through everything
- Works on Linux, macOS, Windows 11, Docker
- Detects GPU, package managers, dependencies

✅ **Multiple AI Services**
- OpenAI (GPT-4, GPT-4-turbo, GPT-4-mini)
- Anthropic (Claude Opus, Sonnet, Haiku)
- Chinese services (Deepseek, Qwen, Baichuan) - international access
- Local models (Ollama, vLLM) - free, no API keys

✅ **Multi-Agent Research**
- Agents specialize in different research areas
- Collaborate and debate findings
- Resource sharing (GPU, API budget)
- Structured knowledge exchange

✅ **Smart Data Management**
- Hot storage (immediate access)
- Warm storage (compressed, recent data)
- Cold storage (archival, old data)
- Configurable retention policies

✅ **Integration Ready**
- Exports to GitHub wikis
- Stores in PostgreSQL/MongoDB
- Syncs with Murmur knowledge graph
- Validates with constraint-theory
- Monitored via spreadsheet-moment dashboards

## 📖 Documentation Structure

```
├── README.md                   # This file - start here
├── CONCEPTS.md                 # Core concepts explained simply
├── ARCHITECTURE.md             # Complete technical design
├── INTEGRATION_GUIDE.md        # How to use with SuperInstance
│
├── install/README.md           # Installation details
├── config/README.md            # Configuration guide
├── agents/README.md            # Agent system guide
├── docker/README.md            # Container deployment
├── results/README.md           # Results and outputs
└── docs/README.md              # Additional documentation
```

## 🔧 System Requirements

**Minimum:**
- Python 3.10+
- 8GB RAM
- 250GB disk (for data and experiments)

**Recommended:**
- Python 3.11+
- 32GB RAM
- 500GB SSD
- NVIDIA GPU with 40GB+ VRAM (for full swarm)

**Optional:**
- Docker (for containerized deployment)
- PostgreSQL (for knowledge storage)
- Ollama or vLLM (for local LLMs)

## 📝 Common Commands

```bash
# After installation:
ar verify                          # Check setup
ar start --agents 1               # Start single agent
ar start --agents 4               # Start full swarm
ar status                         # Check agent status
ar chat hyperparameter-specialist # Talk to an agent
ar metrics --last 1h              # View metrics
ar focus agent-name "new focus"   # Change agent focus
ar stop                           # Stop all agents
ar graph --export murmur          # Export to wiki
```

## 🤝 Contributing

**Found an issue?** [File an issue](https://github.com/SuperInstance/autoclaw/issues)

**Want to extend?**
- Add custom agent profiles in `config/agents/`
- Add new services in `config/services/`
- Create research templates in templates/
- Submit a PR!

## 📚 Learn More

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Deep dive into system design
- **[CONCEPTS.md](CONCEPTS.md)** - Understand the core ideas
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Connect with SuperInstance
- **[install/INSTALLATION_GUIDE.md](install/INSTALLATION_GUIDE.md)** - Detailed setup
- **[SuperInstance Papers](https://github.com/SuperInstance/superinstance-papers)** - Research foundations

## 🎯 What's Next?

1. **Install & Configure** → Follow [install/INSTALLATION_GUIDE.md](install/INSTALLATION_GUIDE.md)
2. **Understand Concepts** → Read [CONCEPTS.md](CONCEPTS.md)
3. **Start Research** → `ar start --agents 1`
4. **Monitor Progress** → `ar status` and `ar chat default`
5. **Explore Results** → Check `results/experiments/`

## 📄 License

MIT License - See LICENSE file for details

## 🙋 Support

- **Docs**: This README + subdirectory READMEs
- **Issues**: [GitHub Issues](https://github.com/SuperInstance/autoclaw/issues)
- **Community**: [SuperInstance Discord](https://discord.gg/superinstance)

---

**Ready to get started?** Jump to [install/INSTALLATION_GUIDE.md](install/INSTALLATION_GUIDE.md) 🚀
