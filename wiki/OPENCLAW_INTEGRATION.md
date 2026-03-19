# OpenClaw Integration (Claude Code)

Integrate AutoClaw with Claude Code's `/autoclaw` skill.

---

## 🔗 Integration Overview

AutoClaw can be controlled from Claude Code using the `/autoclaw` skill:

```
/autoclaw Research deep learning architecture trends
```

---

## 🚀 Setup

1. **Start AutoClaw daemon**:
   ```bash
   python crew/cli.py start
   ```

2. **In Claude Code**, use `/autoclaw` skill:
   ```
   /autoclaw Your task description here
   ```

3. **Monitor progress**:
   ```
   /autoclaw status
   /autoclaw board
   /autoclaw knowledge query "topic"
   ```

---

## 📋 Available Commands

| Skill Command | Purpose |
|---------------|---------|
| `/autoclaw add "task"` | Submit task |
| `/autoclaw board` | View queue |
| `/autoclaw knowledge query "term"` | Search knowledge |
| `/autoclaw status` | System status |

---

## 💡 Common Workflows

### Research Workflow
```
/autoclaw Research the latest advances in [topic]
# Wait for completion
/autoclaw knowledge query "[topic]"
# Review findings
```

### Multi-Step Task
```
/autoclaw Research problem X
/autoclaw Analyze findings for problem X
/autoclaw Create recommendations for problem X
```

---

## 🔗 See Also

- [QUICK_START.md](QUICK_START.md) - Getting started
- [CLI_COMMANDS.md](CLI_COMMANDS.md) - All commands
- [WORKFLOWS.md](WORKFLOWS.md) - Task patterns

**See also**: [HOME.md](HOME.md)
