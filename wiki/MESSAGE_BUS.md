# Message Bus & Communication

SQLite-backed pub/sub system for durable inter-agent communication.

---

## 📨 Architecture

```
Agent A                          Agent B
   │                               │
   └─→ publish("topic", msg) ────→ SQLite DB
                                    │
                              subscribe("topic")
                                    │
                                   │ Handler receives msg
```

---

## 💾 Storage

Messages stored in `messages.db` (SQLite):

```
Table: messages
├─ id (PRIMARY KEY)
├─ topic (index for routing)
├─ payload (JSON)
├─ source (agent name)
├─ timestamp
├─ status (pending|delivered|failed)
└─ attempts (retry count)
```

---

## 🚀 Publishing

```python
message_bus.publish(
    topic="research_complete",
    message={
        "task_id": 42,
        "findings": [...],
        "confidence": 0.95
    }
)
```

Message immediately persisted before delivery.

---

## 📡 Subscribing

```python
def handle_research_result(msg):
    print(f"Received: {msg.payload}")

message_bus.subscribe("research_complete", handle_research_result)
```

---

## ✅ Durability Guarantees

- ✅ All messages persisted before acknowledgment
- ✅ Automatic retry on delivery failure
- ✅ No message loss on crash
- ✅ At-least-once delivery semantics
- ✅ Topic-based routing for scalability

---

## 🔗 See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [COMPONENTS.md](COMPONENTS.md) - MessageBus component
- [WORKFLOWS.md](WORKFLOWS.md) - Communication patterns

**See also**: [HOME.md](HOME.md)
