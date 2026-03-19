# Information Extraction

Structured data from unstructured text.

---

## 📋 Extraction Tasks

**Named Entity Recognition (NER)**: Find names, places, organizations
**Relation Extraction**: Find relationships between entities
**Event Extraction**: Who did what, when, where?
**Attribute Extraction**: Properties and features
**Coreference**: Which mentions refer to same entity?

---

## 🔄 Extraction Pipeline

```
Raw text
   ↓
Tokenization
   ↓
Sentence splitting
   ↓
Entity detection
   ↓
Relation detection
   ↓
Structured output
```

---

## 📚 Common Patterns

**"John Smith worked at Google from 2015 to 2020"**
→ Entity: John Smith (person), Google (organization)
→ Relation: worked_at
→ Temporal: 2015-2020

**"Apple released iPhone 15 with USB-C"**
→ Entity: Apple, iPhone 15, USB-C
→ Relation: released, has_feature
→ Attribute: version=15, feature=USB-C

---

## 🛠️ Approaches

**Rule-based**: Regex patterns, templates
**Statistical**: CRF, structured prediction
**Neural**: LSTM, Transformer models
**Hybrid**: Combine methods

---

## 📊 Evaluation

- **Precision**: Correct extractions / Total extractions
- **Recall**: Correct extractions / Total correct
- **F1-score**: Harmonic mean of precision/recall

---

## 🔗 See Also

- [KNOWLEDGE_EXTRACTION.md](KNOWLEDGE_EXTRACTION.md)
- [DOCUMENT_ANALYSIS.md](DOCUMENT_ANALYSIS.md)
- [STRUCTURED_OUTPUT.md](STRUCTURED_OUTPUT.md)
- [KNOWLEDGE_GRAPH_DESIGN.md](KNOWLEDGE_GRAPH_DESIGN.md)
- [NLP_PROCESSING.md](NLP_PROCESSING.md)

**See also**: [HOME.md](HOME.md)
