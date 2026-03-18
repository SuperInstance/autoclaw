# Documentation

Complete documentation for understanding and using AutoResearch.

## 📚 Documentation Guide

### For New Users

Start here in this order:

1. **[../README.md](../README.md)** (5 min read)
   - What is AutoResearch?
   - Quick navigation
   - Key features overview

2. **[../CONCEPTS.md](../CONCEPTS.md)** (20 min read)
   - Core ideas explained clearly
   - What is semantic linking?
   - What is constraint-theory validation?
   - What is cold storage?
   - What is flowstate mode?

3. **[../install/INSTALLATION_GUIDE.md](../install/INSTALLATION_GUIDE.md)** (15 min setup)
   - Step-by-step installation
   - Configuration wizard walkthrough
   - Troubleshooting guide

### For Understanding the System

Deep dives into architecture and design:

1. **[../ARCHITECTURE.md](../ARCHITECTURE.md)** (60 min read)
   - 7-layer system architecture
   - Complete data flows
   - Integration with SuperInstance ecosystem
   - Fact-checking pipeline details
   - Cold storage system

2. **[../INTEGRATION_GUIDE.md](../INTEGRATION_GUIDE.md)** (45 min read)
   - How to use each SuperInstance component
   - spreader-tool orchestration
   - murmur wiki integration
   - constraint-theory validation
   - spreadsheet-moment monitoring

### For Operations

How to run and manage the system:

1. **[../install/README.md](../install/README.md)**
   - Installation quick start
   - Configuration files generated
   - Environment validation

2. **[../config/README.md](../config/README.md)**
   - Configuration file structure
   - Agent profiles (YAML)
   - Service templates (pre-commented)
   - Data retention policies
   - How to customize

3. **[../agents/README.md](../agents/README.md)**
   - Agent system overview
   - Running agents
   - Interacting with agents (chat, focus, priority)
   - Real-time monitoring
   - Creating custom agents

4. **[../docker/README.md](../docker/README.md)**
   - Docker setup and usage
   - Multi-service orchestration
   - GPU support configuration
   - Troubleshooting containers

5. **[../results/README.md](../results/README.md)**
   - Understanding experiment results
   - Analyzing metrics
   - Knowledge graph exports
   - Podcast content generation
   - Data retention and cold storage

## 🗺️ Documentation Map

```
├── README.md                    # Start here!
├── CONCEPTS.md                  # Understand the ideas
├── ARCHITECTURE.md              # Technical deep dive
├── INTEGRATION_GUIDE.md         # Connect components
│
├── install/
│   ├── README.md               # Quick installation
│   └── INSTALLATION_GUIDE.md   # Detailed setup
│
├── config/
│   └── README.md               # Configuration guide
│
├── agents/
│   └── README.md               # Agent system
│
├── docker/
│   └── README.md               # Container deployment
│
├── results/
│   └── README.md               # Results and outputs
│
└── docs/
    └── README.md               # You are here
```

## 🎓 Learning Paths

### Path 1: Quick Start (30 minutes)
- [../README.md](../README.md) - Overview
- [../install/INSTALLATION_GUIDE.md](../install/INSTALLATION_GUIDE.md) - Get it running
- `ar start --agents 1` - Launch agents
- `ar chat default` - Talk to agent

**Result:** You have AutoResearch running!

### Path 2: Understand the System (2 hours)
- [../CONCEPTS.md](../CONCEPTS.md) - Core ideas
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - System design
- [../config/README.md](../config/README.md) - Configuration
- [../agents/README.md](../agents/README.md) - Agents

**Result:** You understand how everything works

### Path 3: Advanced Deployment (4 hours)
- [../docker/README.md](../docker/README.md) - Containers
- [../INTEGRATION_GUIDE.md](../INTEGRATION_GUIDE.md) - SuperInstance integration
- [../results/README.md](../results/README.md) - Results management
- Production setup with PostgreSQL, Redis, monitoring

**Result:** Enterprise-ready deployment

### Path 4: Custom Research (varies)
- [../config/README.md](../config/README.md) - Configuration
- [../agents/README.md](../agents/README.md) - Custom agents
- Create custom agent profiles
- Define research objectives
- Monitor and iterate

**Result:** Autonomous research running 24/7

## 📖 Topic Index

### Installation & Setup
- [Installation Guide](../install/INSTALLATION_GUIDE.md) - Step-by-step setup
- [Installation README](../install/README.md) - Quick reference
- [Docker Setup](../docker/README.md) - Containerized deployment

### Configuration
- [Config Guide](../config/README.md) - Complete configuration
- [API Services](../config/services/) - Service templates
- [Agent Profiles](../config/agents/) - Agent configurations

### Running Research
- [Agent System](../agents/README.md) - How agents work
- [CLI Commands](../agents/README.md#-running-agents) - Command reference
- [Monitoring](../agents/README.md#-monitoring-agents) - Track progress

### Understanding the System
- [CONCEPTS.md](../CONCEPTS.md) - Core ideas
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design
- [INTEGRATION_GUIDE.md](../INTEGRATION_GUIDE.md) - SuperInstance integration

### Results & Analysis
- [Results README](../results/README.md) - Understanding outputs
- [Data Format](../results/README.md#-understanding-experiment-results) - Metrics structure
- [Analysis Tasks](../results/README.md#-common-analysis-tasks) - Example queries

## 💬 Common Questions

### How do I get started?
**Answer:** Start with [../README.md](../README.md), then follow [INSTALLATION_GUIDE.md](../install/INSTALLATION_GUIDE.md)

### What are the system requirements?
**Answer:** See [../README.md](../README.md#-system-requirements) - Python 3.10+, 8GB RAM, 250GB disk

### How much does it cost?
**Answer:** Depends on API services:
- OpenAI: ~$2-5/hour per agent
- Local models (Ollama): Free
- Anthropic: Similar to OpenAI

### Can I use local models only?
**Answer:** Yes! See [../config/services/local-services.yaml](../config/services/local-services.yaml)

### How do I customize agents?
**Answer:** See [../config/README.md](../config/README.md#-creating-custom-agents)

### How long do experiments take?
**Answer:** Each experiment is exactly 5 minutes (fixed time budget)

### Where are my results?
**Answer:** In `results/experiments/` directory. See [../results/README.md](../results/README.md)

### Can I run agents on my laptop?
**Answer:** Yes, but CPU-only mode is slow. See [../install/INSTALLATION_GUIDE.md](../install/INSTALLATION_GUIDE.md#troubleshooting)

### How do I integrate with GitHub wiki?
**Answer:** Configure in [../config/system.yaml](../config/system.yaml) or [../config/README.md](../config/README.md)

## 🔗 External Resources

### AutoResearch Ecosystem
- [SuperInstance GitHub](https://github.com/SuperInstance)
- [SuperInstance Papers](https://github.com/SuperInstance/superinstance-papers) - 65+ research papers
- [murmur - Semantic Wiki](https://github.com/SuperInstance/murmur)
- [spreader-tool - Multi-agent Orchestration](https://github.com/SuperInstance/spreader-tool)
- [constraint-theory - Deterministic Validation](https://github.com/SuperInstance/constraint-theory)

### Tools & Services
- [OpenAI API](https://platform.openai.com)
- [Anthropic Claude](https://www.anthropic.com/claude)
- [Ollama](https://ollama.ai) - Local LLMs
- [vLLM](https://github.com/lm-sys/vllm) - Fast local inference

### Learning Resources
- [PyTorch Tutorials](https://pytorch.org/tutorials/)
- [Hugging Face Transformers](https://huggingface.co/transformers/)
- [Large Language Models](https://en.wikipedia.org/wiki/Large_language_model)

## 📝 Documentation Standards

All documentation follows these principles:

- **Clear**: Use simple language, examples for complex concepts
- **Complete**: Answer common questions, include troubleshooting
- **Current**: Updated with latest features and best practices
- **Consistent**: Same style and structure across all docs
- **Linked**: Cross-references to related sections

## 🤝 Contributing Documentation

Help us improve documentation:

1. **Found an error?** File an issue on GitHub
2. **Want to add clarification?** Submit a PR
3. **Have a tutorial?** Share it with the community
4. **Found a gap?** Let us know what's missing

## 📋 Documentation Checklist

- [x] Main README - Start here
- [x] CONCEPTS - Core ideas explained
- [x] ARCHITECTURE - Technical design
- [x] INTEGRATION_GUIDE - SuperInstance integration
- [x] Install README - Quick reference
- [x] INSTALLATION_GUIDE - Detailed setup
- [x] Config README - Configuration guide
- [x] Agents README - Agent system
- [x] Docker README - Container setup
- [x] Results README - Results analysis
- [x] Docs README - This file

## 🎯 Next Steps

Choose your path:

**New User?**
→ Start with [../README.md](../README.md)

**Ready to Install?**
→ Follow [../install/INSTALLATION_GUIDE.md](../install/INSTALLATION_GUIDE.md)

**Want to Understand?**
→ Read [../CONCEPTS.md](../CONCEPTS.md)

**Ready to Run?**
→ See [../agents/README.md](../agents/README.md)

**Need Help?**
→ Check documentation index above or file GitHub issue

---

**Happy learning!** 🚀

*Last updated: March 17, 2026*
