# Knowledge System

Persistent learning with hot/warm/cold tiers, confidence scoring, and intelligent retrieval.

---

## 🎯 Overview

The Knowledge System is AutoClaw's long-term memory - a tiered storage system that:
- Persists findings from research tasks
- Scores confidence in each piece of knowledge
- Auto-promotes/demotes entries based on age
- Enables efficient querying
- Handles garbage collection under disk pressure

---

## 📊 Tiered Architecture

### Hot Tier (TTL: 3600s = 1 hour)
- Recently discovered knowledge
- High confidence (0.7+)
- Frequently queried
- Stored in memory and YAML
- Checked first on queries
- Example: "Learning rate 0.001 is optimal for this task"

### Warm Tier (TTL: 86400s = 1 day)
- Established knowledge
- Medium confidence (0.5-0.7)
- Validated through use
- Stored in YAML
- Secondary query target
- Example: "Batch size 64 works well with learning rate 0.001"

### Cold Tier (TTL: 604800s = 1 week)
- Archived knowledge
- Low confidence (<0.5) or infrequently used
- Long-term reference
- Stored in compressed YAML
- Only queried on explicit request
- Example: "Initial experiments with LSTM showed promise"

---

## 🔍 Entry Structure

```yaml
entries:
  - id: "knowledge_001"
    title: "Learning rate warmup improves stability"
    content: "Starting with warm-up schedule prevents loss spikes"
    confidence: 0.95
    tags: ["training", "optimization", "hyperparameter"]
    created_at: "2026-03-19T07:00:00Z"
    accessed_at: "2026-03-19T08:15:00Z"
    access_count: 42
    tier: "hot"  # hot|warm|cold
    source: "researcher_agent"
    quality_score: 0.95
```

**Fields**:
- **id**: Unique identifier
- **title**: Short summary
- **content**: Full description
- **confidence**: 0-1.0 (higher = more trusted)
- **tags**: For filtering
- **created_at**: When discovered
- **accessed_at**: Last query time
- **access_count**: Popularity metric
- **tier**: Current storage tier
- **source**: Which agent created it
- **quality_score**: Manual validation result

---

## ⏱️ TTL Management

### Auto-Promotion Timeline

```
Created → Hot (3600s)
  ↓ (after 1 hour)
Accessed <10x per day → Warm (86400s)
  ↓ (after 1 day)
Accessed <1x per day → Cold (604800s)
  ↓ (after 1 week)
Not accessed → Eligible for GC
```

### Tier Demotion

```
High confidence (0.9+) → Hot (even if old)
Medium confidence (0.5-0.7) → Warm
Low confidence (<0.5) → Cold
Unused >30 days → Garbage collection candidate
```

---

## 🔎 Querying Knowledge

### Basic Query
```python
results = knowledge_store.query("learning rate optimization")
# Returns top 10 matches from hot tier, then warm
```

### Filtered Query
```python
results = knowledge_store.query(
    "learning rate",
    min_confidence=0.8,
    tags=["optimization"],
    tier="hot"
)
# Only high-confidence, tagged entries
```

### Query Performance
- **Hot tier hit**: <10ms (memory)
- **Warm tier hit**: <50ms (YAML parse)
- **Cold tier hit**: <100ms (decompress + parse)
- **Cache miss**: ~100ms (full scan)

---

## 📈 Confidence Scoring

Confidence ranges from 0 (unreliable) to 1.0 (highly reliable).

### How Confidence Is Determined

**Agent-assigned scores** (initial):
- Researcher: 0.7-0.95 (based on source credibility)
- Teacher: 0.8+ (pedagogical content)
- Critic: 0.6-0.9 (after validation)
- Distiller: 0.75-0.95 (synthesized knowledge)

**Usage-based adjustments**:
- Every successful reuse: +0.02
- Every failed reuse: -0.05
- Max adjustment: ±0.2 from initial

**Validation by humans**:
- Manual approval: → 0.99
- Manual rejection: → 0.1
- Flagged for review: confidence capped

---

## 🗑️ Garbage Collection

### When GC Runs
- Scheduled: Every 6 hours
- On-demand: `crew knowledge gc`
- Emergency: Disk usage >90%

### GC Strategy
1. Remove entries with `confidence < 0.3` AND `age > 30 days`
2. Remove entries with zero access in `age > 90 days`
3. Compress cold tier YAML
4. Archive to backup

### Emergency GC (--aggressive)
1. Remove all entries in cold tier >30 days old
2. Remove entries with confidence <0.5
3. Archive everything >90 days old
4. Compact database

### Result
```
GC completed:
  - Removed: 47 entries
  - Archived: 234 entries
  - Freed: 124 KB
  - Cold tier size: 1.2 MB → 0.9 MB
```

---

## 📊 Statistics & Monitoring

### Knowledge Store Status
```bash
python crew/cli.py knowledge stats
```

Output:
```
Knowledge Store Statistics
==================================
Total entries:     512
Hot tier:          45 (3600s TTL)
Warm tier:         234 (86400s TTL)
Cold tier:         233 (604800s TTL)

Confidence distribution:
  0.9-1.0:    180 entries (high)
  0.7-0.9:    245 entries (medium)
  0.5-0.7:     67 entries (low)
  <0.5:        20 entries (review)

Total size:        2.4 MB
Hot tier size:     45 KB
Warm tier size:    891 KB
Cold tier size:    1.5 MB

Avg queries/day:   342
Most accessed:     "Learning rate 0.001 is optimal"
Least accessed:    234 entries never queried
```

---

## 🔗 Integration with Agents

### When Agents Create Knowledge

**Researcher agent** → Creates entry after web search
- High confidence (0.8-0.95) based on source
- Tags with topic and source domain

**Teacher agent** → Creates entry from Q&A
- High confidence (0.85+) for verified facts
- Educational context preserved

**Critic agent** → Creates validation entry
- Medium confidence (0.6-0.85)
- Notes specific issues found
- Suggests improvements

**Distiller agent** → Creates synthesized entry
- High confidence (0.85+) after combining sources
- Links to source entries
- Flags areas of disagreement

### When Agents Query Knowledge

Every agent queries before starting work:
```python
def execute_task(task):
    # Search related knowledge first
    related = knowledge_store.query(task.description)
    if related:
        # Use existing knowledge to accelerate work
        task.context = related
    # ... then proceed with task
```

---

## 💾 Backup & Recovery

### Automatic Backups
- Daily backup of knowledge.yaml
- Location: `data/crew/knowledge.yaml.backup`
- Retention: 7 days of backups
- Compression: gzip for backups >1MB

### Manual Export
```bash
# Export to JSON Lines
python crew/cli.py knowledge export --format jsonl > knowledge_export.jsonl

# Export filtered
python crew/cli.py knowledge export --min-confidence 0.8 --tier hot
```

### Recovery
```bash
# Restore from backup
cp data/crew/knowledge.yaml.backup data/crew/knowledge.yaml

# Reimport from export
python crew/cli.py knowledge import knowledge_export.jsonl
```

---

## 🎯 Best Practices

1. **Query before computing**: Always search knowledge first
2. **Score honestly**: Reflect actual confidence, not desired confidence
3. **Tag generously**: Use tags for filtering later
4. **Monitor confidence drift**: Watch for confidence creep or collapse
5. **Regular GC**: Run `crew knowledge gc` weekly
6. **Backup frequently**: Before major operations
7. **Review low-confidence entries**: Delete unreliable knowledge

---

## 🔗 Related Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design
- **[COMPONENTS.md](COMPONENTS.md)** - KnowledgeStore component
- **[PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)** - Query tuning
- **[WORKFLOWS.md](WORKFLOWS.md)** - Knowledge-aware planning
- **[AGENTS.md](AGENTS.md)** - How agents use knowledge

**See also**: [HOME.md](HOME.md)
