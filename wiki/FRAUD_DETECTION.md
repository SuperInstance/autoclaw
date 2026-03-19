# Fraud Detection & Prevention

Identifying and preventing fraudulent activities.

---

## 🚨 Fraud Types

**Identity Fraud**: Using someone else's identity
**Account Takeover**: Unauthorized access
**Transaction Fraud**: Unauthorized purchases
**Credit Card Fraud**: Stolen card use
**Chargebacks**: Disputing legitimate charges
**Synthetic Fraud**: Fake identity + real transaction

---

## 🔍 Detection Signals

**Behavioral**: Different from usual pattern
**Device**: New device/location
**Velocity**: Unusual frequency
**Amount**: Unusual transaction size
**Graph**: Unusual connection patterns

---

## 📊 Detection Methods

**Rules**: Heuristic thresholds
```
Amount > $10,000 + international = flag
```

**Statistical**: Anomaly vs baseline
**ML**: Classification models
**Graph**: Network analysis (money flow)
**Ensemble**: Combine multiple signals

---

## ⚖️ Trade-offs

```
Sensitivity: Catch more fraud
         ↓
False positives: Decline good customers
         ↓
Support cost: Investigate false alarms
         ↓
Customer friction: Verify legitimate activity
```

---

## 📈 Metrics

- **Precision**: % flagged are actually fraud
- **Recall**: % actual fraud caught
- **F1**: Balance precision + recall
- **AUC-ROC**: Overall discrimination
- **Cost**: Fraud loss vs false positives

---

## 🔗 See Also

- [ANOMALY_DETECTION.md](ANOMALY_DETECTION.md)
- [MONITORING_AND_ALERTS.md](MONITORING_AND_ALERTS.md)
- [ADVERSARIAL_ROBUSTNESS.md](ADVERSARIAL_ROBUSTNESS.md)
- [GRAPH_DATABASES.md](GRAPH_DATABASES.md)
- [REAL_TIME_SYSTEMS.md](REAL_TIME_SYSTEMS.md)

**See also**: [HOME.md](HOME.md)
