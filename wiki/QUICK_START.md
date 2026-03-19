# Quick Start (5 Minutes)

Get AutoClaw up and running in 5 minutes.

---

## 🚀 Installation

```bash
# 1. Clone and setup
git clone <repo-url>
cd autoclaw
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Create data directory
mkdir -p data

# 3. Start daemon
python crew/cli.py start

# 4. Verify running
python crew/cli.py board
```

---

## ✨ Your First Task

```bash
# Submit a task
python crew/cli.py add "Research the latest advances in large language models"

# Check task board
python crew/cli.py board

# View status
python crew/cli.py status
```

---

## 🔍 Query Knowledge

```bash
# Search what the system has learned
python crew/cli.py knowledge query "language models"

# View statistics
python crew/cli.py metrics
```

---

## 🎯 Next Steps

**Administrators**: Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

**Developers**: Read [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)

**Users**: Read [CLI_COMMANDS.md](CLI_COMMANDS.md) and [USE_CASES.md](USE_CASES.md)

**Claude Code Integration**: Read [OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md)

---

## 📚 Full Navigation

See [HOME.md](HOME.md) for complete documentation index.

**Status**: ✅ Ready to use
