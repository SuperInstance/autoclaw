# Advanced Prompting Techniques

Sophisticated prompt engineering for AutoClaw agents.

---

## 📝 Prompt Architecture Patterns

**System Role Definition**:
```
You are a specialized [domain] expert agent focused on [specific task].
Your role: [responsibilities]
Constraints: [limitations]
Output format: [structured format]
```

**Few-Shot Examples**:
```
Example 1: [input] → [expected output]
Example 2: [input] → [expected output]
Now apply this to: [actual input]
```

**Chain-of-Thought Prompting**:
```
Step 1: [Analyze the problem]
Step 2: [Identify key factors]
Step 3: [Generate options]
Step 4: [Evaluate each option]
Step 5: [Select best approach]
```

---

## 🎯 Specialized Techniques

**Role-Playing**: "You are a forensic analyst..."
**Constraint Injection**: "Never mention X, Always include Y"
**Structured Output**: "Return JSON with keys: ..."
**Temperature Calibration**: Cool for facts, warm for creativity
**Instruction Layers**: Primary goal, then constraints, then examples

---

## 🔄 Prompt Optimization Loop

```
Initial prompt → Test → Measure → Refine → Repeat
   ↓              ↓        ↓         ↓
Baseline      Examples  Quality   Better
              Format    Clarity   Prompt
```

---

## 📊 Evaluation Metrics

- **Accuracy**: Correct answers
- **Consistency**: Same input → same output
- **Completeness**: All required elements
- **Conciseness**: Efficient language
- **Clarity**: Easy to understand

---

## 🔗 See Also

- [AGENTS.md](AGENTS.md)
- [KNOWLEDGE_VALIDATION.md](KNOWLEDGE_VALIDATION.md)
- [QUALITY_METRICS.md](QUALITY_METRICS.md)
- [CODE_GENERATION.md](CODE_GENERATION.md)
- [LEARNING_LOOPS.md](LEARNING_LOOPS.md)

**See also**: [HOME.md](HOME.md)
