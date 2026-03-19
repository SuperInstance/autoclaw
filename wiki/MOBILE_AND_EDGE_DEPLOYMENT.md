# Mobile & Edge Deployment

Running AutoClaw on resource-constrained devices.

---

## 📱 Deployment Targets

**Mobile**: Smartphones, tablets
**Edge**: Embedded devices, IoT
**Hybrid**: Mix of cloud and local

---

## 🔧 Optimization Strategies

**Model Compression**:
- Quantization (8-bit instead of 32-bit)
- Knowledge distillation
- Pruning unused weights
- Sparse models

**Computation Offloading**:
- Keep simple tasks local
- Send complex tasks to cloud
- Hybrid inference

**Memory Management**:
- Streaming processing
- Progressive loading
- Cache management
- Disk spillover

---

## 💡 Patterns

**Local-First**:
```
Simple task → Local inference (fast, free)
Complex task → Cloud inference (accurate)
Fallback → Cached results
```

**Hybrid**:
```
Candidate generation → Local (fast)
Ranking → Cloud (accurate)
Caching → Local storage
```

---

## 📊 Trade-offs

| Dimension | Local | Cloud |
|-----------|-------|-------|
| Latency | Low | High |
| Accuracy | Lower | Higher |
| Cost | $0 | Per-call |
| Privacy | High | Lower |

---

## 🔗 See Also

- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)
- [DISTRIBUTED_EXECUTION.md](DISTRIBUTED_EXECUTION.md)
- [COST_ANALYSIS.md](COST_ANALYSIS.md)
- [ENTERPRISE_DEPLOYMENT.md](ENTERPRISE_DEPLOYMENT.md)

**See also**: [HOME.md](HOME.md)
