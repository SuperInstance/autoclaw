# Integration Patterns

Common patterns for integrating AutoClaw with external systems.

---

## 🔌 REST API Integration

```
1. Agent queries external API
2. Format request with validation
3. Retry on failure
4. Parse and validate response
5. Store in knowledge base
6. Notify on completion
```

---

## 🗄️ Database Integration

- Connection pooling
- Transaction management
- Error handling
- Query optimization
- Caching strategies

---

## 📨 Message Queue Integration

- Publish task results to queues
- Subscribe to external events
- Async processing
- Retry logic
- Dead letter handling

---

## 🪝 Webhook Integration

- Receive external events
- Trigger agent workflows
- Validate signatures
- Handle idempotency
- Timeout management

---

## 🔗 See Also

- [API_REFERENCE.md](API_REFERENCE.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ADVANCED_TOPICS.md](ADVANCED_TOPICS.md)

**See also**: [HOME.md](HOME.md)
