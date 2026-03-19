# CLI Commands Reference

All 30+ commands available via `python crew/cli.py`.

---

## 📋 Task Management

| Command | Purpose |
|---------|---------|
| `add "description"` | Submit new task |
| `board` | View task queue |
| `show <id>` | View task details |
| `cancel <id>` | Cancel task |
| `priority <id> <1-9>` | Change priority |
| `pause <id>` | Pause task |
| `resume <id>` | Resume task |

**Example**:
```bash
crew add "Research neural architecture search"
crew board
crew priority 5 9  # Boost task 5 to priority 9
```

---

## 🔍 Monitoring

| Command | Purpose |
|---------|---------|
| `status` | Check daemon status |
| `metrics` | View system metrics |
| `agents status` | List agents |
| `log <id>` | View task log |
| `findings` | Recent findings |

---

## 🧠 Knowledge Management

| Command | Purpose |
|---------|---------|
| `knowledge query "term"` | Search knowledge |
| `knowledge gc` | Garbage collect |
| `knowledge stats` | Statistics |

**Example**:
```bash
crew knowledge query "optimization"
crew knowledge gc
```

---

## ⚙️ Configuration

| Command | Purpose |
|---------|---------|
| `config show` | Display configuration |
| `config set <key> <value>` | Update setting |

---

## 🚀 System Control

| Command | Purpose |
|---------|---------|
| `start` | Start daemon |
| `stop` | Stop daemon |
| `restart` | Restart daemon |

---

## 📊 Advanced

| Command | Purpose |
|---------|---------|
| `agents spawn <role>` | Create agent |
| `cf status` | Cloudflare credits |
| `study` | Auto-learning mode |
| `gpu status` | GPU info |

---

## 🔗 See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [WORKFLOWS.md](WORKFLOWS.md) - Common patterns
- [QUICK_START.md](QUICK_START.md) - Getting started

**See also**: [HOME.md](HOME.md)
