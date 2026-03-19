# Development Guide

For contributing to AutoClaw.

---

## 📂 Codebase Structure

```
autoclaw/
├── crew/                 # Core system
│   ├── agents/          # Agent implementations
│   ├── messaging/       # Message bus
│   ├── knowledge/       # Knowledge store
│   ├── scheduler.py     # Task scheduler
│   ├── daemon.py        # Main daemon
│   ├── cli.py          # Command interface
│   └── *.py            # Production modules
├── tests/              # Test suites
├── docs/               # Documentation
└── wiki/               # Wiki (you are here)
```

---

## 🧪 Writing Tests

Tests validate functionality and prevent regressions.

```python
def test_knowledge_store():
    store = KnowledgeStore()
    entry = store.create_entry("title", "content", 0.9)
    assert entry.id
    assert entry.confidence == 0.9
```

Run tests:
```bash
python test_comprehensive_debugging.py
```

---

## 🚀 Creating Custom Agents

```python
from crew.agents.base import BaseAgent

class MyAgent(BaseAgent):
    def run(self, task):
        # Implement your logic
        result = self.process_task(task)
        self.publish_result(result)
        return result
```

---

## ✅ Pre-Commit Checklist

- [ ] Code passes linter
- [ ] Tests pass (100%)
- [ ] Documentation updated
- [ ] No security issues introduced
- [ ] Code review approved

---

## 🔗 See Also

- [TEST_COVERAGE.md](TEST_COVERAGE.md) - Testing guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [COMPONENTS.md](COMPONENTS.md) - Component details

**See also**: [HOME.md](HOME.md)
