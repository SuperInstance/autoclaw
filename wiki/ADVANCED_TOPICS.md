# Advanced Topics

For experienced users and contributors.

---

## 🤖 Custom Agents

Extend AutoClaw by creating custom agents:

1. Inherit from `BaseAgent`
2. Implement `run(task)`
3. Register in agent pool
4. Configuration enables it

---

## 🔗 Distributed Operation

Run agents across multiple machines:

1. Shared `messages.db` on network storage
2. Shared `data/` directory (NFS/S3)
3. Multiple daemons connect to shared bus

---

## 📊 Knowledge Export/Import

```bash
# Export to JSON Lines
crew knowledge export > knowledge_backup.jsonl

# Import from backup
crew knowledge import knowledge_backup.jsonl
```

---

## ⚡ Performance Tuning

- Adjust `hot_ttl`, `warm_ttl`, `cold_ttl` for your workload
- Increase pool size for more parallelism
- Enable caching for repeated queries
- Batch similar tasks

---

## 🔗 See Also

- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) - Creating agents
- [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md) - Tuning
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design

**See also**: [HOME.md](HOME.md)
