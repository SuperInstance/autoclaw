# Retrieval-Augmented Generation (RAG)

Combining retrieval with generation for grounded outputs.

---

## 🔄 RAG Pipeline

```
User query
   ↓
Retrieve relevant documents
   ↓
Combine query + documents
   ↓
Generate answer grounded in retrieved info
   ↓
Cite sources
```

---

## 🎯 Why RAG?

**Problems it solves**:
- Hallucination (grounded in facts)
- Currency (uses fresh data)
- Citations (source attribution)
- Domain-specific (knows your data)

---

## 📚 Retrieval Strategies

**Sparse Retrieval**:
- BM25 keyword matching
- Fast and interpretable
- Works for factual queries

**Dense Retrieval**:
- Vector similarity
- Semantic understanding
- Better for nuanced queries

**Hybrid**:
- Combine both methods
- Best of both worlds
- Slightly slower

---

## 🔗 Generation Methods

**Prompt Engineering**:
```
Context: [Retrieved documents]
Question: [User query]
Answer: [Generated response]
```

**Fine-tuning**:
- Train on RAG examples
- Better quality generations
- Requires labeled data

---

## 📊 Evaluation

**Retrieval Quality**:
- Precision: % relevant documents
- Recall: % of relevant docs found
- MRR: Rank of first relevant

**Generation Quality**:
- Relevance: Answers the question
- Consistency: Uses retrieved facts
- Fluency: Natural language
- Citations: Proper attribution

---

## 🔗 See Also

- [VECTOR_DATABASES.md](VECTOR_DATABASES.md)
- [SEMANTIC_SEARCH.md](SEMANTIC_SEARCH.md)
- [KNOWLEDGE_SYSTEM.md](KNOWLEDGE_SYSTEM.md)
- [KNOWLEDGE_EXTRACTION.md](KNOWLEDGE_EXTRACTION.md)
- [STRUCTURED_OUTPUT.md](STRUCTURED_OUTPUT.md)

**See also**: [HOME.md](HOME.md)
