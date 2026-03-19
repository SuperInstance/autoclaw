# Evaluation Metrics & Benchmarking

Comprehensive metrics for system evaluation.

---

## 📊 Metric Categories

**Accuracy Metrics**: How correct?
**Efficiency Metrics**: How fast?
**Cost Metrics**: How expensive?
**Quality Metrics**: How good?
**Impact Metrics**: What changed?

---

## 🎯 Task-Specific Metrics

**Classification**:
- Accuracy, Precision, Recall, F1
- ROC-AUC, Confusion Matrix

**Ranking**:
- NDCG, MRR, MAP
- Coverage, Diversity

**Text Generation**:
- BLEU, ROUGE, METEOR
- Perplexity, Human evaluation

**Recommendation**:
- CTR, Conversion, Engagement
- Coverage, Diversity

---

## 📈 Aggregation Methods

**Micro**: Average all instances
**Macro**: Average per class
**Weighted**: Weight by class size

---

## 🔍 Evaluation Approach

```
1. Define success metrics
2. Collect baseline
3. Run experiment
4. Measure metrics
5. Statistical test
6. Report results
```

---

## ⚠️ Common Pitfalls

- **Cherry-picking**: Reporting best results
- **Multiple Comparisons**: P-hacking
- **Biased Dataset**: Non-representative
- **Data Leakage**: Test in train data
- **Ignoring Baselines**: Not comparing to simple methods

---

## 🔗 See Also

- [QUALITY_METRICS.md](QUALITY_METRICS.md)
- [AUTOMATED_TESTING.md](AUTOMATED_TESTING.md)
- [PERFORMANCE_BENCHMARKING.md](PERFORMANCE_BENCHMARKING.md)
- [WORKFLOW_OPTIMIZATION.md](WORKFLOW_OPTIMIZATION.md)
- [LEARNING_LOOPS.md](LEARNING_LOOPS.md)

**See also**: [HOME.md](HOME.md)
