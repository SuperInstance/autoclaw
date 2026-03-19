# Custom Agent Development

Building specialized agents for domain-specific tasks.

---

## 🛠️ Custom Agent Template

```python
from crew.agents.base import BaseAgent

class SpecializedAgent(BaseAgent):
    """Agent for [specific domain]"""

    def __init__(self, config):
        super().__init__(config)
        self.expertise = ["skill1", "skill2"]

    def run(self, task):
        # 1. Query related knowledge
        context = self.knowledge_store.query(task.description)

        # 2. Process with specialization
        result = self.process_with_expertise(task, context)

        # 3. Publish results
        self.publish_result(result)
        return result

    def process_with_expertise(self, task, context):
        # Custom logic here
        pass
```

---

## 📋 Agent Design Patterns

**Task Analyzer**: Understand requirements
**Researcher**: Gather information
**Validator**: Check quality
**Formatter**: Prepare output
**Coordinator**: Orchestrate others

---

## 🎯 Capability Definition

- What types of tasks?
- What knowledge needed?
- What outputs generated?
- What failure modes?
- What skill requirements?

---

## 🔗 See Also

- [AGENTS.md](AGENTS.md)
- [COMPONENTS.md](COMPONENTS.md)
- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)

**See also**: [HOME.md](HOME.md)
