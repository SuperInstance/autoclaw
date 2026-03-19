# Production Deployment Guide

Step-by-step guide to deploy AutoClaw in production.

---

## 📋 Pre-Deployment Checklist

- [ ] All tests passing (46/46)
- [ ] Code review complete
- [ ] Security audit passed
- [ ] Documentation complete
- [ ] API keys configured
- [ ] Monitoring setup planned

---

## 🚀 Deployment Steps

### 1. Environment Setup

```bash
git clone <repo-url>
cd autoclaw
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration

Create `data/config.yaml`:

```yaml
crew:
  name: AutoClaw
  log_level: INFO

agents:
  researcher: { enabled: true }
  teacher: { enabled: true }
  critic: { enabled: true }
  distiller: { enabled: true }

knowledge:
  hot_ttl: 3600
  warm_ttl: 86400
  cold_ttl: 604800

security:
  rate_limiting:
    anthropic: 100
    openai: 100
```

Set API keys:
```bash
export ANTHROPIC_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
```

### 3. Pre-Deployment Testing

```bash
python test_integration_e2e.py
python test_failure_recovery.py
python test_load_and_stress.py
```

All must pass 100%.

### 4. Start Daemon

```bash
# Foreground (initial verification)
python crew/cli.py start --verbose

# OR background (production)
nohup python crew/cli.py start > autoclaw.log 2>&1 &
```

### 5. Verification

```bash
python crew/cli.py status
python crew/cli.py metrics
python crew/cli.py board
```

---

## 🔍 Health Checks

After deployment, verify:

```bash
# System health
python crew/cli.py status
# Expected: "IDLE" or "STUDYING"

# Knowledge store
python crew/cli.py knowledge query "test"
# Expected: Results or empty

# Metrics
python crew/cli.py metrics
# Expected: JSON with mode, queued_tasks, completed_tasks
```

---

## 🛠️ Troubleshooting

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| Daemon won't start | Check logs | `tail autoclaw.log` |
| Config error | Invalid YAML | Validate with `python -m yaml data/config.yaml` |
| Database locked | Stale process | `pkill -f "crew start"` |
| Low memory | Too many tasks | Run `crew knowledge gc --aggressive` |

---

## 📚 Monitoring

```bash
# Monitor logs
tail -f autoclaw.log

# Watch task board
watch -n 5 'python crew/cli.py board'

# Check health every minute
while true; do python crew/cli.py status; sleep 60; done
```

---

## 🔗 See Also

- [CONFIGURATION.md](CONFIGURATION.md) - All config options
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
- [MONITORING_AND_ALERTS.md](MONITORING_AND_ALERTS.md) - Observability
- [OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md) - Claude Code setup

**See also**: [HOME.md](HOME.md)
