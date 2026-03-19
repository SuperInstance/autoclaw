# AutoClaw A2A Quick Reference Card

**For: AI Agents, Claude Code, Autonomous Systems**

---

## ⚡ 30-Second Setup

```bash
python3 A2A_SETUP_SCRIPT.py
```

Done! System is running. Next: `crew health`

---

## 📋 System At a Glance

| Aspect | Details |
|--------|---------|
| **Language** | Python 3.9+ |
| **Type** | Multi-agent knowledge system |
| **Backend** | SQLite + in-memory cache |
| **Agents** | Researcher, Teacher, Critic, Distiller |
| **CLI** | 30+ commands (`crew health`, `crew knowledge add`, etc.) |
| **API** | Python (from crew.daemon import AutoClawDaemon) |
| **Runtime** | Daemon (24/7 background) |
| **Status** | Production-ready (91.8% test pass) |

---

## 🚀 Agent Deployment Flow

```
1. VERIFY
   └─ Python 3.9+, pip, git available

2. SETUP
   └─ python3 A2A_SETUP_SCRIPT.py

3. VERIFY
   └─ crew health (expect: HEALTHY)

4. START
   └─ crew start

5. HANDOFF
   └─ User can now use: crew knowledge add/query/etc
```

---

## 🔑 Key Components

```
MessageBus (SQLite)
    ↓
    ├─ Researcher Agent (search/synthesis)
    ├─ Teacher Agent (Q&A generation)
    ├─ Critic Agent (quality validation)
    └─ Distiller Agent (knowledge synthesis)
    ↓
KnowledgeStore (Hot/Warm/Cold tiers)
    ↓
User Output
```

---

## 💻 Core Commands

### System
```bash
crew start              # Start daemon
crew stop               # Stop daemon
crew health             # Full health check
crew status             # Quick status
```

### Knowledge
```bash
crew knowledge add --content "text" --tag "tag"
crew knowledge query --tag "tag"
crew knowledge list
crew knowledge delete --id <id>
```

### Admin
```bash
crew config show        # View configuration
crew cache clear        # Clear memory cache
crew logs show          # View logs
```

---

## 🐍 Python API

```python
from crew.daemon import AutoClawDaemon

# Initialize
daemon = AutoClawDaemon()
daemon.startup()

# Use
store = daemon.knowledge_store
entry = store.add({"content": "...", "tags": ["tag"]})
results = store.query(tags=["tag"])

# Cleanup
daemon.shutdown()
```

---

## ✅ Verification Steps

Agent should verify:

```bash
# 1. Imports work
python3 -c "import crew; print('✅')"

# 2. Health check passes
crew health

# 3. CLI responds
crew --help

# 4. Knowledge CRUD works
crew knowledge add --content "test" --tag "demo"
crew knowledge query --tag "demo"

# 5. Tests pass (optional)
python -m pytest test_comprehensive_debugging.py -v
```

---

## 🔧 Configuration

### Minimal config.yaml
```yaml
system:
  environment: production
  log_level: INFO

database:
  path: ./crew/knowledge/store.db

agents:
  pool_size: 4
```

### Environment Variables
```bash
export AUTOCLAW_ENV=production
export AUTOCLAW_LOG_LEVEL=INFO
export AUTOCLAW_POOL_SIZE=4
```

---

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| ModuleNotFoundError | `source venv/bin/activate` |
| Database locked | `crew stop && rm crew/knowledge/store.db-journal` |
| Out of memory | `crew cache clear` |
| Command not found | `python3 -m crew <cmd>` |
| Import fails | `pip install -r requirements.txt --force-reinstall` |
| Health check fails | `crew logs show` |

---

## 📊 Performance Specs

| Metric | Value |
|--------|-------|
| **Startup** | 2-5 seconds |
| **Query latency** | <100ms (10K entries) |
| **Add latency** | <10ms |
| **Agent processing** | 1-5 seconds |
| **Concurrent agents** | 4 (configurable) |
| **Max cache entries** | 1,000 |
| **RAM per 1000 entries** | ~50MB |

---

## 📚 Documentation Map

```
A2A_QUICK_REFERENCE.md (this file)
    ↓
CLAUDE_CODE_SETUP.md (quick start)
    ↓
A2A_AGENT_MANUAL.md (complete reference)
    ↓
A2A_SYSTEM_METADATA.json (machine-readable)
```

---

## 🎯 Agent Success Criteria

Agent deployment successful if:

- [x] Prerequisites verified
- [x] Setup completed without errors
- [x] `crew health` returns HEALTHY
- [x] CLI commands respond
- [x] Knowledge CRUD works
- [x] Tests pass (85%+)
- [x] Daemon starts without errors
- [x] System survives restart

---

## 🔌 Integration Example

**Claude Code agent deploying AutoClaw:**

```python
import subprocess
import sys

# 1. Run setup
result = subprocess.run([sys.executable, "A2A_SETUP_SCRIPT.py"])
if result.returncode != 0:
    print("Setup failed!")
    sys.exit(1)

# 2. Verify health
result = subprocess.run(["crew", "health"], capture_output=True, text=True)
if "HEALTHY" not in result.stdout:
    print("Health check failed!")
    sys.exit(1)

# 3. Start daemon
subprocess.Popen(["crew", "start"])

# 4. Confirm to user
print("✅ AutoClaw deployed successfully!")
print("Try: crew knowledge add --content 'hello' --tag 'test'")
```

---

## 📞 Quick Help

### Agent Debugging
```bash
# Verbose output
python3 A2A_SETUP_SCRIPT.py --debug

# Verify only (don't install)
python3 A2A_SETUP_SCRIPT.py --verify-only

# Check logs
crew logs show --lines 50

# Enable debug logging
AUTOCLAW_LOG_LEVEL=DEBUG crew health
```

### For Humans
```bash
# Read quick start
cat CLAUDE_CODE_SETUP.md

# Read full agent manual
cat A2A_AGENT_MANUAL.md

# Read user guide
cat ONBOARDING.md

# Read setup guide
cat QUICKSTART.md
```

---

## 🤝 Handoff to User

After deployment, provide user with:

```
✅ AutoClaw is ready!

Quick start:
  crew knowledge add --content "My note" --tag "personal"
  crew knowledge query --tag "personal"

Next steps:
  1. Read ONBOARDING.md (5 min)
  2. Read QUICKSTART.md (15 min)
  3. Check docs/COMPLETE_GUIDE.md (reference)

Help:
  crew --help               # All commands
  crew health               # Check status
  crew logs show            # View logs
```

---

## ⚙️ System Files

**Key Locations:**

```
autoclaw/
├── crew/                      # Main code
│   ├── daemon.py             # Background process
│   ├── message_bus.py        # Task routing
│   ├── knowledge/            # Storage layer
│   ├── agents/               # Worker agents
│   ├── cli.py                # User commands
│   └── *.py                  # 50+ modules
├── config.yaml               # Configuration (created by bootstrap)
├── crew/knowledge/store.db   # Database (created by bootstrap)
├── requirements.txt          # Python dependencies
├── test_*.py                 # Test suites
└── docs/                     # Documentation
```

**Agent Entry Points:**

```
python3 A2A_SETUP_SCRIPT.py    → Automated setup
from crew.daemon import ...    → Python API
crew <command>                 → CLI commands
```

---

## 📈 Scaling Guide

| Scale | Hot | Warm | Cold | Storage |
|-------|-----|------|------|---------|
| Small | <1K | 0 | 0 | <50MB |
| Medium | 100-1K | 1K-10K | 0 | <500MB |
| Large | 1K | 10K-50K | 50K+ | <5GB |

---

## 🔒 Security

Agent should ensure:

- ✅ No credentials in code
- ✅ API keys in environment
- ✅ Audit logging enabled
- ✅ Input validation active
- ✅ Database file protected

---

## 📊 Testing Results

```
Total tests: 56+
Pass rate: 91.8%
Critical issues: 0
Blocking issues: 0
Status: PRODUCTION READY
```

---

## 🎓 Learning Path

**For Agents:**
1. This file (quick reference)
2. CLAUDE_CODE_SETUP.md (setup guide)
3. A2A_AGENT_MANUAL.md (full reference)
4. Review A2A_SYSTEM_METADATA.json (integration)
5. Review source code (implementation)

**For Users:**
1. ONBOARDING.md (introduction)
2. QUICKSTART.md (detailed guide)
3. INSTALL.md (troubleshooting)
4. docs/COMPLETE_GUIDE.md (everything)

---

## 🚀 Next Steps

**For Agents:**
```bash
# 1. Run setup
python3 A2A_SETUP_SCRIPT.py

# 2. Verify
crew health

# 3. Test
python -m pytest test_comprehensive_debugging.py -v

# 4. Start
crew start

# 5. Done!
```

**For Users:**
```bash
# Read getting started guides
cat ONBOARDING.md         # 5-15 min
cat QUICKSTART.md         # 10-30 min
cat docs/COMPLETE_GUIDE.md # Full reference
```

---

**Last Updated**: March 18, 2026
**For**: AI Agents, Claude Code, Autonomous Systems
**Status**: Production Ready ✅
