# Graph Databases & Query Languages

Storing and querying highly connected data.

---

## 🕸️ Why Graphs?

**Network Data**: Relationships are primary
**Queries**: Traverse connections efficiently
**Discovery**: Find paths, patterns
**Recommendation**: Follow relationships

---

## 📊 Graph Structures

**Nodes**: Entities (people, concepts)
**Edges**: Relationships (knows, cites)
**Properties**: Attributes on nodes/edges
**Labels**: Categories and types

---

## 🔍 Query Languages

**Cypher** (Neo4j):
```cypher
MATCH (author:Person)-[:WROTE]->(paper:Paper)
WHERE author.name = "Alan Turing"
RETURN paper.title
```

**Gremlin** (Generic):
```
g.V().has('name','Alan Turing')
 .out('wrote')
 .values('title')
```

---

## 💡 Applications

- **Social networks**: Friends, followers, groups
- **Knowledge graphs**: Concepts and relationships
- **Recommendation**: What similar users liked
- **Fraud detection**: Suspicious connection patterns
- **Impact analysis**: How changes propagate

---

## 🔧 Popular Systems

- **Neo4j**: Most popular, Cypher language
- **ArangoDB**: Multi-model (graph, document)
- **JanusGraph**: Distributed graph DB
- **TigerGraph**: Enterprise graph DB

---

## 📈 Performance

**Strengths**: Fast traversals, relationship queries
**Weaknesses**: Complex joins, aggregations
**Sweet spot**: Highly connected data

---

## 🔗 See Also

- [KNOWLEDGE_GRAPH_DESIGN.md](KNOWLEDGE_GRAPH_DESIGN.md)
- [SEMANTIC_SEARCH.md](SEMANTIC_SEARCH.md)
- [KNOWLEDGE_SYSTEM.md](KNOWLEDGE_SYSTEM.md)
- [DATA_AUTOMATION.md](DATA_AUTOMATION.md)
- [RECOMMENDATION_SYSTEMS.md](RECOMMENDATION_SYSTEMS.md)

**See also**: [HOME.md](HOME.md)
