# Configuration Guide

All configuration options for AutoClaw.

---

## 📄 Config File Location

`data/config.yaml` - YAML format with environment variable interpolation

---

## 🔧 Configuration Sections

### Crew Settings
```yaml
crew:
  name: "AutoClaw"                # System name
  version: "1.0.0"               # Version
  log_level: "INFO"              # DEBUG|INFO|WARN|ERROR
```

### Agents
```yaml
agents:
  researcher: { enabled: true }
  teacher: { enabled: true }
  critic: { enabled: true }
  distiller: { enabled: true }
```

### Knowledge Storage
```yaml
knowledge:
  hot_ttl: 3600         # 1 hour
  warm_ttl: 86400       # 1 day
  cold_ttl: 604800      # 1 week
```

### Security
```yaml
security:
  api_key_manager:
    encryption: true
  rate_limiting:
    anthropic: 100      # req/min
    openai: 100
    groq: 100
```

### Monitoring
```yaml
monitoring:
  healthcheck_interval: 300       # 5 min
  disk_warn_percent: 80
  disk_alert_percent: 95
```

---

## 🌍 Environment Variables

Use `${VAR}` syntax for interpolation:

```yaml
crew:
  name: ${CREW_NAME}
security:
  anthropic_key: ${ANTHROPIC_API_KEY}
```

---

## ✅ Validation

All configs validated on startup. Invalid settings cause startup failure with detailed error.

---

## 🔗 See Also

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Setup
- [SECURITY_FEATURES.md](SECURITY_FEATURES.md) - Security settings
- [MONITORING_AND_ALERTS.md](MONITORING_AND_ALERTS.md) - Monitoring config

**See also**: [HOME.md](HOME.md)
