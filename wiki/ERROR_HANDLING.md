# Error Handling & Recovery

Comprehensive resilience patterns and failure recovery.

---

## 🔄 Retry Logic

**Exponential Backoff**:
- Attempt 1: Immediate
- Attempt 2: 2s delay
- Attempt 3: 4s delay
- Attempt 4: 8s delay
- Attempt 5: 16s delay

**Max 3 attempts** by default before circuit breaker.

---

## 🔌 Circuit Breaker Pattern

States:
- **CLOSED**: Normal operation
- **OPEN**: Service failing, reject requests
- **HALF_OPEN**: Testing recovery

Triggers on **3 consecutive failures**.
Resets after **60s** of successful calls.

---

## 🛡️ Graceful Degradation

When services fail:
- Continue with cached results
- Fallback to cheaper APIs
- Reduce data freshness requirements
- Use stale knowledge if fresh unavailable
- Degrade feature set rather than fail completely

---

## 📋 Error Catalog

| Error Type | Cause | Recovery |
|-----------|-------|----------|
| ConfigError | Invalid YAML | Restart with fixed config |
| APIError | Network/rate limit | Retry with backoff |
| DatabaseError | Locked DB | Circuit breaker |
| ValidationError | Bad input | Log and skip |
| MemoryError | OOM | Trigger GC |
| DiskError | No space | Aggressive cleanup |

---

## 🔗 See Also

- [PRODUCTION_MODULES.md](PRODUCTION_MODULES.md) - Error handling module
- [SECURITY_FEATURES.md](SECURITY_FEATURES.md) - Security
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues

**See also**: [HOME.md](HOME.md)
