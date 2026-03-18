# AutoResearch: Scope & Roadmap

**Last Updated:** March 17, 2026
**Status:** MVP released, extended features in development

This document clarifies what exists today vs. what's planned. It addresses the gap between promises in documentation and current implementation.

---

## ✅ MVP: What Exists Now (March 2026)

### Core Capability
Give an AI agent a small LLM training setup and let it experiment autonomously.

**What Works:**
- Single-GPU model optimization (train.py modification by agents)
- 5-minute time-budgeted experiments (fixed wall-clock limit)
- Validation metric tracking (val_bpb = bits per byte, lower is better)
- Git-based experiment history (each experiment is a commit)
- 100+ experiments per night possible (on H100)
- Results analysis (results.tsv, metrics.json, checkpoints)

**System Requirements:**
- Python 3.10+
- NVIDIA GPU (H100, A100, L4 or better)
- 8GB RAM minimum
- 250GB disk (for experiments)
- OpenAI, Anthropic, or local LLM access

**Installation:**
```bash
curl -fsSL https://raw.githubusercontent.com/SuperInstance/autoclaw/main/install/install.sh | bash
# Or on Windows: powershell -Command "iex ((New-Object System.Net.WebClient).DownloadString('...'))"
```

### Configuration System
- YAML-based agent profiles (hyperparameter-specialist, architecture-explorer, etc.)
- Service templates for OpenAI, Anthropic, local services
- Multi-agent coordination (resource allocation, specialization)
- Data retention policies (hot/warm/cold storage)

**Status:** ✅ Complete (install.py, config-wizard.py, service templates working)

### Docker Support
- Multi-stage Dockerfile with CUDA, non-root user, health checks
- Docker Compose orchestration (autoresearch + PostgreSQL + Redis)
- GPU support configuration
- Development stage with debugging tools

**Status:** ⚠️ Partial (Docker builds and runs, but external service references need fixing)

### Documentation
- README.md - Quick overview
- INSTALLATION_GUIDE.md - Step-by-step setup
- ARCHITECTURE.md - System design (500+ lines)
- CONCEPTS.md - Core ideas explained
- Agent system guide
- Results analysis guide
- Docker deployment guide

**Status:** ✅ Complete (comprehensive README files for all directories)

### Readiness Assessment
| Component | Status | Score |
|-----------|--------|-------|
| Installation | ✅ Working | 4.5/5 |
| Configuration | ✅ Working | 4.5/5 |
| Core training loop | ✅ Working | 5/5 |
| Agent system (prompts/tools) | ⚠️ Framework only | 2/5 |
| Multi-agent orchestration | ⚠️ Framework only | 2/5 |
| Docker | ⚠️ Partial | 3/5 |
| **MVP Overall** | **⚠️ Functional but incomplete** | **3.5/5** |

---

## 🚧 Near-term: Q2-Q3 2026 (2-3 months)

### High Priority

**1. Agent System Implementation**
- Write functional prompts (currently empty in agents/prompts/)
  - hyperparameter-specialist.md
  - architecture-explorer.md
  - optimizer-researcher.md
  - synthesis-agent.md
- Implement agent tools (currently empty in agents/tools/)
  - run_experiment.py
  - modify_train.py
  - parse_results.py
- Test multi-agent coordination and debate protocols

**Timeline:** 2-3 weeks
**Impact:** Makes "multi-agent" claim real; enables autonomous research teams

---

**2. Business Documentation**
- SCOPE.md ← **You are reading this**
- BUSINESS.md (2-3 page stakeholder summary)
  - Problem: Manual hyperparameter tuning is slow
  - Solution: Autonomous agent approach
  - Benefits: Time saved, cost reduction, insight velocity
  - Investment required: GPU costs + engineer time
  - ROI timeline and payback period
- Cost calculator (web form or spreadsheet)
- Concrete example (real experiment end-to-end)

**Timeline:** 1-2 weeks
**Impact:** Enables internal pitching and budget justification

---

**3. Docker Stabilization**
- Fix docker-compose.yml references to non-existent services
- Either implement or remove broken integrations (murmur, spreadsheet-moment)
- Test end-to-end deployment
- Document GPU setup and troubleshooting

**Timeline:** 1 week
**Impact:** docker-compose up works reliably

---

### Medium Priority

**4. Murmur Wiki Integration (POC)**
```
autoresearch results
    ↓
Parse metrics
    ↓
Format as markdown article
    ↓
Push to murmur wiki API
    ↓
Visible in semantic knowledge graph
```

**Timeline:** 2-3 weeks
**Impact:** Validates extended vision, enables finding publication

---

**5. Basic Monitoring**
- Dashboard showing current agent status
- Experiment success/failure tracking
- GPU utilization metrics
- Cost tracking

**Timeline:** 1 week
**Impact:** Operational visibility

---

## 🔮 Long-term: Q4 2026 - 2027 (4+ months)

### Aspirational Features (Research Phase)

**1. Constraint-Theory Validation**
Auto-validate findings against constraint-theory determinism. Currently conceptual; requires theoretical framework development.

**Timeline:** TBD (research-dependent)

---

**2. Podcast Generation**
Auto-generate podcast episodes from research findings. Requires:
- Text-to-speech integration
- Episode structure templates
- Multi-agent narration synthesis

**Timeline:** Q4 2026 estimate

---

**3. Full SuperInstance Integration**
Deep integration with SuperInstance ecosystem:
- spreader-tool orchestration
- Multi-repository research coordination
- Distributed agent networks
- Cross-project knowledge synthesis

**Timeline:** 2027+ (significant engineering effort)

---

**4. Semantic Knowledge Graph**
Full semantic linking of research findings with:
- Automatic relationship detection
- Cross-experiment insight synthesis
- Recommendation engine for related studies

**Timeline:** 2027+ (requires constraint-theory validation first)

---

## 🎯 What This Means

### If you want to use AutoResearch TODAY (March 2026):
- ✅ Install: `curl ... | bash`
- ✅ Configure agents and services
- ✅ Run autonomous experiments for 5-24 hours
- ✅ Analyze results with provided tools
- ⚠️ Multi-agent coordination is framework-only (single agent recommended)
- ⚠️ Wiki integration not implemented yet

**Best Use Case:** Single GPU optimization of one model, 24-48 hours of autonomous tuning

---

### If you're evaluating for production:
- **NOT ready yet** for autonomous 24/7 operation
- **Ready in Q2 2026** (2-3 weeks) after agent system implementation
- **Recommended timeline:** Wait for Tier 1 complete (mid-April 2026)

---

### If you need the "semantic wiki + fact-checking" system:
- **Not implemented** as of March 2026
- **POC expected:** Q3 2026 (murmur integration)
- **Full system:** 2027 (constraint-theory + semantic graph)

If this was why you downloaded AutoResearch, we recommend:
1. Try the MVP now (single-agent model optimization)
2. Provide feedback on what's working/not working
3. We'll prioritize extended features based on your needs

---

## 📊 Readiness Timeline

| Quarter | MVP Status | Extended Vision | Ready for |
|---------|-----------|-----------------|-----------|
| **Q1 2026 (now)** | 3.5/5 - Partial | 0/5 - Framework | Single-agent experiments |
| **Q2 2026 (Apr-Jun)** | 4.5/5 - Solid | 2/5 - Partial | Multi-agent coordination |
| **Q3 2026 (Jul-Sep)** | 4.5/5 - Solid | 3/5 - POC | Wiki integration (beta) |
| **Q4 2026 (Oct-Dec)** | 5/5 - Complete | 4/5 - Feature-rich | Production deployment |
| **2027** | 5/5 - Complete | 5/5 - Full vision | Enterprise-grade system |

---

## 🚀 Getting Started

**Pick your path:**

### Path A: Try the MVP
```bash
# Install
curl -fsSL https://raw.githubusercontent.com/SuperInstance/autoclaw/main/install/install.sh | bash

# Configure (interactive wizard)
python install/config-wizard.py

# Run single agent for 24 hours
ar start --agents 1 --duration 24h

# Check results
ls -la results/experiments/
```

**Time required:** 30 min setup + 24 hours running

---

### Path B: Understand the System
```bash
# Read docs
- README.md (5 min overview)
- CONCEPTS.md (20 min core ideas)
- ARCHITECTURE.md (60 min technical deep dive)
- SCOPE.md (10 min - this file)
- BUSINESS.md (coming soon - 5 min stakeholder summary)
```

**Time required:** 2 hours

---

### Path C: Contribute to Extended Vision
We're actively developing:
1. Agent prompts and tools (help wanted!)
2. Murmur wiki integration (help wanted!)
3. Constraint-theory validation framework

See CONTRIBUTING.md for details (coming soon)

---

## 📋 Frequently Asked Questions

**Q: Is this production-ready?**
A: MVP yes (single-agent, 24-48h runs). Multi-agent and wiki features coming Q2-Q3 2026.

**Q: When will you have the semantic wiki?**
A: POC in Q3 2026 (murmur integration), full system in 2027.

**Q: Can I use this with my own LLM?**
A: Yes! See config/services/local-services.yaml for Ollama and vLLM setup.

**Q: How much does it cost?**
A: Depends on APIs:
- OpenAI: ~$2-5/hour per agent
- Anthropic: ~$3-6/hour per agent
- Local (Ollama): Free (but slower)

See BUSINESS.md (coming soon) for cost calculator.

**Q: What if I find a bug in the MVP?**
A: File a GitHub issue! The MVP is solid but we're actively fixing edge cases.

**Q: When will multi-agent work?**
A: Agent framework exists now, prompts/tools coming in next 2-3 weeks (mid-April 2026).

---

## 📞 Feedback & Roadmap Influence

We're building in public. Your feedback shapes priorities:

1. Using the MVP? → Share results and suggestions
2. Waiting for extended features? → Comment on GitHub discussions
3. Want to contribute? → See CONTRIBUTING.md

Our decision-making framework:
- **Tier 1:** Fix critical blockers (2 weeks)
- **Tier 2:** Implement planned features (1 month)
- **Tier 3:** Long-term vision (2027+)

We prioritize based on:
1. User demand
2. Technical dependencies
3. Resource availability

---

**Ready to get started?** → Go to [INSTALLATION_GUIDE.md](install/INSTALLATION_GUIDE.md)

**Want the full vision?** → See [VISION.md](VISION.md) (coming soon)

**Need business context?** → See [BUSINESS.md](BUSINESS.md) (coming soon)

**Want to understand the code?** → Start with [ARCHITECTURE.md](ARCHITECTURE.md)

---

*This document is updated quarterly as features ship. Last sync: March 17, 2026.*
