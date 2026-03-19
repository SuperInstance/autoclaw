# Monitoring & Alerts

Observability and alerting configuration.

---

## 📊 Metrics

Available via `crew metrics`:

```json
{
  "mode": "studying",
  "queued_tasks": 5,
  "completed_tasks": 42,
  "knowledge_entries": 234,
  "memory_mb": 156,
  "disk_gb": 2.4
}
```

---

## 📈 Monitoring Interval

Default: Every 5 minutes

Configure in `data/config.yaml`:
```yaml
monitoring:
  healthcheck_interval: 300  # seconds
```

---

## 🔔 Alert Thresholds

| Metric | Yellow | Red |
|--------|--------|-----|
| Disk | 80% | 95% |
| Memory | 85% | 95% |
| Error rate | 5% | 10% |
| API quota | 70% | 90% |

---

## 📝 Logging

Logs written to `autoclaw.log`:

```bash
# View recent logs
tail -f autoclaw.log

# Filter by level
grep ERROR autoclaw.log
grep WARN autoclaw.log
```

---

## 🔗 See Also

- [HEALTH_CHECK.md](HEALTH_CHECK.md) - Health monitoring
- [CONFIGURATION.md](CONFIGURATION.md) - Alert configuration
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Diagnosing issues

**See also**: [HOME.md](HOME.md)
