# Real-World Use Cases

Typical scenarios and how to use AutoClaw for them.

---

## 🔬 Research Automation

**Goal**: Gather information on a topic

```bash
crew add "Research the latest advances in transformer models"
# Wait for completion
crew knowledge query "transformer models"
```

**Timeline**: 2-5 minutes per task

---

## 📚 Content Generation

**Goal**: Create learning materials

```bash
crew add "Create a comprehensive quiz on attention mechanisms"
crew knowledge query "quiz"
```

**Timeline**: 3-10 minutes

---

## 👀 Code Review

**Goal**: Analyze code quality

```bash
crew add "Review code in src/agents/researcher.py for quality and bugs"
crew show <task_id>  # View detailed review
```

**Timeline**: 5-15 minutes

---

## 📊 Analysis & Synthesis

**Goal**: Summarize research findings

```bash
crew add "Analyze findings about neural architecture search and create summary"
crew knowledge query "neural architecture search"
```

**Timeline**: 10-20 minutes

---

## 🔗 See Also

- [WORKFLOWS.md](WORKFLOWS.md) - Common patterns
- [QUICK_START.md](QUICK_START.md) - Getting started
- [CLI_COMMANDS.md](CLI_COMMANDS.md) - All commands

**See also**: [HOME.md](HOME.md)
