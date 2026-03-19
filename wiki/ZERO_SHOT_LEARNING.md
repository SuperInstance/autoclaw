# Zero-Shot & Few-Shot Learning

Enabling agents to handle novel tasks with minimal examples.

---

## 🎯 Zero-Shot Learning

Tasks performed without task-specific training.

**Approach**:
- Describe task clearly
- Provide domain context
- Show constraints
- Request specific output format

**Example**:
```
Task: Classify this customer review sentiment
Context: E-commerce product reviews
Constraint: Must choose: positive, neutral, negative
Format: JSON with {sentiment, confidence, reasoning}
```

---

## 📚 Few-Shot Learning

Learning from small number of examples.

**2-3 Good Examples**:
```
Example 1: [Input] → [Output]
Example 2: [Input] → [Output]
Example 3: [Input] → [Output]
Now: [New input] → [Expected output]
```

**Advantages**:
- Better accuracy than zero-shot
- No retraining needed
- Fast adaptation
- Minimal data required

---

## 🔄 Optimization Techniques

**Example Quality**:
- Diverse examples
- Edge cases
- Typical cases
- Clear explanations

**Example Selection**:
- Most relevant examples
- Avoid outliers
- Balance coverage
- Order matters (put best first)

---

## 📊 When to Use

**Zero-Shot**: Standard tasks, clear instructions
**Few-Shot**: Novel tasks, need adaptation
**Fine-tuning**: Repeated custom tasks, large volume

---

## 📈 Performance Progression

```
Zero-shot:     70% accuracy
+1 example:    75% accuracy
+3 examples:   82% accuracy
+5 examples:   85% accuracy
Fine-tuned:    90%+ accuracy
```

---

## 🔗 See Also

- [ADVANCED_PROMPTING_TECHNIQUES.md](ADVANCED_PROMPTING_TECHNIQUES.md)
- [AGENTS.md](AGENTS.md)
- [LEARNING_LOOPS.md](LEARNING_LOOPS.md)
- [CODE_GENERATION.md](CODE_GENERATION.md)
- [KNOWLEDGE_VALIDATION.md](KNOWLEDGE_VALIDATION.md)

**See also**: [HOME.md](HOME.md)
