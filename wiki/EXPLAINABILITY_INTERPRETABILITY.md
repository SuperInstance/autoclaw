# Explainability & Interpretability

Making AutoClaw decisions transparent and understandable.

---

## 🔍 Explanation Types

**Local**: Why this specific decision?
**Global**: How does system work overall?
**Contrastive**: Why this instead of that?
**Example-based**: Similar past cases
**Rule-based**: Decision rules used

---

## 🎯 Explanation Methods

**Attention Visualization**:
- Show which parts mattered
- Highlight source text
- Visualize importance weights

**Feature Attribution**:
- Which inputs drove decision?
- Contribution scores
- Sensitivity analysis

**Decision Rules**:
- Extract if-then rules
- Simplified decision logic
- Auditable guidelines

---

## 📋 Explanation Output

```json
{
  "decision": "approve_loan",
  "confidence": 0.87,
  "reasoning": [
    "Credit score 750 (good): +0.3",
    "Income $120k (sufficient): +0.4",
    "Debt ratio 0.3 (acceptable): +0.2",
    "Employment history (stable): +0.1"
  ],
  "sources": ["credit_bureau", "employer_verification"],
  "similar_cases": ["Case 2341", "Case 2459"]
}
```

---

## 👤 User Communication

- **Non-technical users**: Plain English
- **Experts**: Technical details
- **Regulators**: Compliance justification
- **Data scientists**: Decision logic

---

## 🔗 See Also

- [KNOWLEDGE_VALIDATION.md](KNOWLEDGE_VALIDATION.md)
- [AI_SAFETY.md](AI_SAFETY.md)
- [QUALITY_METRICS.md](QUALITY_METRICS.md)
- [MONITORING_AND_ALERTS.md](MONITORING_AND_ALERTS.md)
- [COMPLIANCE_AUDIT.md](COMPLIANCE_AUDIT.md)

**See also**: [HOME.md](HOME.md)
