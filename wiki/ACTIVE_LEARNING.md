# Active Learning & Efficient Labeling

Intelligently selecting which data to label next.

---

## 🎯 Core Idea

Instead of random sampling, select examples to maximize learning.

```
Model uncertainty
     ↓
Ask human to label uncertain cases
     ↓
Add to training data
     ↓
Model improves faster
```

---

## 🔍 Uncertainty Sampling Strategies

**Least Confident**:
- Model most unsure about
- Max entropy distribution

**Margin Sampling**:
- Smallest gap between top 2 classes
- Close decision boundary

**Query By Committee**:
- Multiple models disagree
- Ensemble disagreement

**Diversity**:
- Select dissimilar examples
- Better coverage

---

## 📊 Efficiency Gains

```
Random sampling: Need 10,000 labels for 90% accuracy
Active learning: Need 1,000 labels for 90% accuracy
Reduction: 10x fewer labels!
```

---

## 🔄 Workflow

1. Start with small labeled set
2. Train model
3. Find most uncertain examples
4. Get human labels
5. Retrain
6. Repeat until sufficient performance

---

## 💡 Applications

- Medical diagnosis (expensive labels)
- Document classification
- Named entity recognition
- Sentiment analysis

---

## 🔗 See Also

- [LEARNING_LOOPS.md](LEARNING_LOOPS.md)
- [KNOWLEDGE_VALIDATION.md](KNOWLEDGE_VALIDATION.md)
- [COST_ANALYSIS.md](COST_ANALYSIS.md)
- [QUALITY_ASSURANCE_AUTOMATION.md](QUALITY_ASSURANCE_AUTOMATION.md)
- [CONTINUOUS_IMPROVEMENT_SYSTEMS.md](CONTINUOUS_IMPROVEMENT_SYSTEMS.md)

**See also**: [HOME.md](HOME.md)
