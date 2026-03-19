# Common Workflows

Standard patterns for typical AutoClaw usage.

---

## 🔍 Research Workflow

```
1. User: crew add "Research topic X"
2. Scheduler: Assigns to Researcher agent
3. Researcher: Searches web + synthesizes
4. KnowledgeStore: Creates entry with 0.85 confidence
5. Notification: User alerted of new finding
6. User: crew knowledge query "topic X" → Get results
```

---

## 🎓 Learning Workflow

```
1. User: crew add "Create quiz on topic Y"
2. Scheduler: Assigns to Teacher agent
3. Teacher: Generates 10 Q&A pairs
4. KnowledgeStore: Stores educational content
5. User: crew knowledge query "quiz" → Get learning materials
```

---

## ✔️ Code Review Workflow

```
1. User: crew add "Review code in file Z"
2. Scheduler: Assigns to Critic agent
3. Critic: Analyzes code quality
4. KnowledgeStore: Stores review with issues found
5. Notification: Issues summary sent to user
6. User: crew show <task_id> → See detailed review
```

---

## 📊 Multi-Agent Coordination

```
1. User: crew add "Analyze research and create summary"
2. Coordinator: Breaks into subtasks
   - Subtask A: Researcher gathers data
   - Subtask B: Critic validates findings
   - Subtask C: Distiller creates summary
3. Message Bus: Agents coordinate via pub/sub
4. Result: Comprehensive analysis with validation
```

---

## 🔗 See Also

- [AGENTS.md](AGENTS.md) - Agent capabilities
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [CLI_COMMANDS.md](CLI_COMMANDS.md) - All commands

**See also**: [HOME.md](HOME.md)
