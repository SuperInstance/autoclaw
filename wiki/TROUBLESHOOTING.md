# Troubleshooting Guide

Common issues and resolution steps.

---

## ❌ Daemon Won't Start

**Symptom**: `crew start` fails

**Diagnosis**:
```bash
tail crew_daemon.log
```

**Common Causes**:
- Missing `data/` directory → `mkdir -p data`
- Invalid `data/config.yaml` → Check YAML syntax
- Port in use → Kill stale process: `pkill -f "crew start"`
- Missing dependencies → `pip install -r requirements.txt`

---

## ❌ Tasks Not Processing

**Symptom**: Tasks stuck in ACTIVE state

**Diagnosis**:
```bash
crew board
crew status
ps aux | grep python
```

**Common Causes**:
- Daemon crashed → Restart: `crew start`
- All agents busy → Wait or increase pool size
- Database locked → Kill stale process
- Configuration error → Check logs

---

## ❌ Knowledge Query Returns Empty

**Symptom**: `crew knowledge query` returns no results

**Diagnosis**:
- No tasks completed yet → Submit tasks with `crew add`
- Wrong search term → Try broader query
- Knowledge tier mismatch → Check `crew knowledge stats`

**Fix**: Run a few tasks first to populate knowledge

---

## ❌ High Memory Usage

**Symptom**: Memory >500MB

**Diagnosis**:
```bash
crew metrics
crew knowledge stats
```

**Fix**:
```bash
crew knowledge gc --aggressive
crew restart
```

---

## ❌ Disk Space Critical

**Symptom**: "No space left" error

**Diagnosis**:
```bash
df -h data/
crew knowledge stats
```

**Fix**:
```bash
crew knowledge gc --aggressive
rm -f data/crew/knowledge.yaml.backup*
```

---

## ❌ API Rate Limit Exceeded

**Symptom**: "API rate limit" error

**Diagnosis**:
```bash
crew cf status
tail autoclaw.log | grep rate
```

**Fix**:
- Wait for quota reset
- Use Groq (free) instead of Anthropic
- Reduce concurrent tasks
- Batch submissions

---

## 📋 Diagnostic Commands

| Command | Purpose |
|---------|---------|
| `crew status` | System health |
| `crew metrics` | Statistics |
| `crew board` | Task queue |
| `crew knowledge stats` | Knowledge store size |
| `tail autoclaw.log` | Recent logs |
| `ps aux \| grep crew` | Process check |
| `df -h data/` | Disk usage |

---

## 🔗 See Also

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Setup troubleshooting
- [ERROR_HANDLING.md](ERROR_HANDLING.md) - Error recovery
- [CONFIGURATION.md](CONFIGURATION.md) - Config validation

**See also**: [HOME.md](HOME.md)
