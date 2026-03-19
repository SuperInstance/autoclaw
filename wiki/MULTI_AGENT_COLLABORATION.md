# Multi-Agent Collaboration Patterns

Orchestrating complex workflows with multiple specialized agents.

---

## 🤝 Collaboration Models

**Sequential**: Task 1 → Task 2 → Task 3
**Parallel**: Task 1, 2, 3 → Merge
**Hierarchical**: Coordinator → Subtasks → Aggregate
**Mesh**: All agents can collaborate freely

---

## 📦 Task Decomposition

1. **Identify subtasks** from main goal
2. **Determine dependencies** (A before B?)
3. **Assign to specialized agents** (who's best?)
4. **Define handoff protocol** (how to pass data?)
5. **Aggregate results** (combine findings)

---

## 💬 Communication Pattern

```
Agent A → MessageBus → Agent B
              ↓
        [persisted]
              ↓
        Agent C subscribes
```

---

## 🔄 Coordination Strategies

- **Work-stealing**: Idle agents help busy ones
- **Consensus**: All agents agree before proceeding
- **Majority voting**: Use most common answer
- **Expert selection**: Trust highest-confidence agent

---

## 🔗 See Also

- [MESSAGE_BUS.md](MESSAGE_BUS.md)
- [AGENTS.md](AGENTS.md)
- [WORKFLOWS.md](WORKFLOWS.md)

**See also**: [HOME.md](HOME.md)
