# Spreadsheet-Moment: Cellular Instances for Data-Driven Agent Coordination

## Repository Overview
**URL:** https://github.com/SuperInstance/Spreadsheet-moment
**Base:** Fork of Univer (isomorphic full-stack spreadsheet framework)
**Key Concept:** Scalable cellular instances for agents to monitor cell changes and execute programs
**Tech Stack:** Rust (performance), TypeScript/Node.js (framework), Canvas rendering, Web Workers

## What Makes It Intelligent

### Cellular Computation Paradigm
Traditional spreadsheets are passive computation models (formulas, no agents). Spreadsheet-moment adds:
- **Active Agents:** Each cell/range can have associated agents that monitor and react
- **Event-Driven:** Agents trigger on cell value changes
- **Distributed:** Agents scale across local/LAN/cloud deployments
- **Composable:** Complex behaviors from simple cell-agent interactions

## How This Transforms AutoCrew

### Current AutoCrew Limitation
AutoCrew builds knowledge (facts + confidence scores) in SQLite tables. But users interact with knowledge as flat data, not as active systems that respond to changes.

### The Spreadsheet-Cellular Advantage
Imagine AutoCrew's knowledge as a **living, reactive spreadsheet** where:
- Each fact is a cell
- Confidence scores auto-update as sources change
- Agents monitor cells for inconsistencies
- Related facts automatically notify each other
- Users can visualize knowledge evolution in real-time

## Concrete Integration Points

### 1. **Knowledge as Living Spreadsheet**

Current AutoCrew knowledge storage:
```
SQLite tables:
- facts (id, content, source, confidence)
- sources (id, url, credibility)
- relationships (fact_a, fact_b, relationship_type)
(Static schema, no reactivity)
```

With Spreadsheet-Moment:
```
Live Spreadsheet:
┌─────────────────────────────────────────────────────────┐
│ Fact ID │ Content         │ Source │ Confidence │ Status │
├─────────────────────────────────────────────────────────┤
│ F1      │ "Paris capital" │ S1     │ 0.95       │ ✓      │  ← Agent monitoring
│ F2      │ "France area"   │ S2     │ 0.87       │ ✓      │  ← Agent detects change
│ F3      │ "Pop. France"   │ S3     │ 0.42       │ ⚠      │  ← Alert: needs review
└─────────────────────────────────────────────────────────┘

Agents active on this sheet:
- ConsistencyAgent: Monitors F1,F2,F3 for contradictions
- ConfidenceAgent: Updates confidence as sources update
- SynthesisAgent: Creates new facts from F1+F2 combinations
- AlertAgent: Flags low-confidence facts for Critic review
```

### 2. **Real-Time Confidence Propagation**

**Scenario:** Source credibility changes, should cascade through knowledge

```
Traditional approach (current AutoCrew):
1. Source S1 credibility updated (0.9 → 0.6)
2. Manual query: Find all facts citing S1
3. Manual update: Decrease their confidence
(Requires explicit logic)

Spreadsheet-Moment approach:
1. Cell (source_credibility, S1) changes to 0.6
2. CellChangedEvent fires
3. All cells with formula =confidence(Source:S1) auto-recalculate
4. Dependent facts (F1, F4, F7) confidence scores update automatically
5. Agents watching those cells receive notifications
6. Critic agent automatically reviews newly-flagged facts
(Automatic, emergent, reactive)
```

### 3. **Visualization of Knowledge Evolution**

Canvas-based rendering (inherited from Univer) enables:

```
Real-time visualization:
┌──────────────────────────────────────────┐
│ Confidence Score Trends for 'AI Safety'  │
│                                          │
│ 100% ─────╲                              │
│         ╱─ ╲─ ╱────────               │
│  50% ──╱     X  ─────                 │
│        │    ╱  ╲                       │
│   0% ──┴────────────────────────       │
│       Day 1  5   10   15   20   25    │
│                                        │
│ • Fact improves as more sources added │
│ • Confidence drops as source questioned
│ • Cyan line: network consensus forms   │
└──────────────────────────────────────────┘

Interactive: Click cell to see source history, agent actions, change timeline
```

### 4. **Agent Cells Monitor Fact Cells**

Unlike spreadsheets where formulas compute values, here agents are first-class:

```
Cell Structure:

Value Cells (hold data):
├─ Facts (F1, F2, F3, ...)
├─ Sources (S1, S2, S3, ...)
└─ Relationships (R1, R2, R3, ...)

Agent Cells (compute + monitor):
├─ ConsistencyAgent: watches Facts & Relationships
│  └─ Triggers when: New relationship created or fact contradicts existing
│     Action: Flag contradiction for Critic agent
│
├─ ConfidenceAgent: watches Sources & Facts
│  └─ Triggers when: Source credibility changes
│     Action: Recalculate dependent fact confidences
│
├─ SynthesisAgent: watches Fact groups
│  └─ Triggers when: 2+ related facts high-confidence
│     Action: Create new synthetic fact
│
└─ AlertAgent: watches low-confidence facts
   └─ Triggers when: Confidence < threshold
      Action: Route to Critic for validation
```

### 5. **Distributed Agent Instances for Scale**

From Spreadsheet-Moment's description: *"Scalable cellular instances for Claw agents to sit and monitor"*

```
Local Deployment (single user):
┌─ Spreadsheet-Moment (all cells + agents on laptop)
│  ├─ Facts (in-memory)
│  ├─ Sources (in-memory)
│  └─ Agents (running on CPU)
└─ Users: 1-2

LAN Deployment (team):
┌─ Central Spreadsheet Server (Rust-based for perf)
│  ├─ Cells (shared state)
│  ├─ Agents (distributed across LAN)
│  └─ Web clients (view on each device)
└─ Users: 5-20, Agents: 10-30

Cloud Deployment (organization):
┌─ Spreadsheet-Moment on Cloudflare Workers
│  ├─ Global edge locations (geography-distributed)
│  ├─ Agent instances scaled by region
│  └─ Web clients worldwide
└─ Users: 100+, Agents: 100+
```

## Self-Improving Aspect

### Emergent Consensus Through Agent Interaction

Imagine 5 agents monitoring the same fact:

```
Fact F1: "Earth population is 8 billion"

Agent1 (Researcher): Adds source from WHO, confidence 0.95
Agent2 (Source Validator): Checks WHO credibility, 0.98
Agent3 (Temporal): Checks how recent, adjusts confidence
Agent4 (Consistency): Checks against other population facts
Agent5 (Aggregate): Synthesizes all inputs

Each agent modifies the confidence cell independently:
├─ Agent1 sets: 0.95
├─ Agent2 adjusts: 0.96 (source valid)
├─ Agent3 adjusts: 0.94 (slightly outdated)
├─ Agent4 adjusts: 0.93 (slightly contradicts related fact)
└─ Agent5 computes: average/vote = 0.945

Result: Emergent consensus confidence without central coordinator
```

### Learning from Cell History

Spreadsheet-Moment can track cell change history:

```
Fact F1 confidence over time:
│ 0.50 (initial research)
├─ 0.65 (second source confirms)
├─ 0.72 (third source agrees)
├─ 0.68 (source 2 questioned)
├─ 0.75 (source 4 authoritative)
└─ 0.79 (consensus stabilizes)

Pattern learning:
- After 3 sources align, confidence stabilizes (self-improving threshold)
- When new source contradicts, confidence drops by avg 0.04
- Authoritative sources contribute 0.08 confidence boost

Agents learn these patterns and apply to future facts
```

## Architecture Integration

### AutoCrew + Spreadsheet-Moment Stack

```
Current AutoCrew:
Researcher → Teacher → Critic → Distiller → SQLite Tables

Enhanced with Spreadsheet-Moment:
Researcher → (Values) → Agent Cells ← (Monitor/React) ← Teacher
                ↓
           Spreadsheet-Moment (live reactive state)
                ↓
            Critic Agent Cell (monitors contradictions)
                ↓
            Distiller Agent Cell (synthesizes patterns)
                ↓
            User Visualization (canvas, real-time updates)
```

### Replacing SQLite with Spreadsheet Model

```
Cold Tier (Archived, long-term)
  ↓ (Warm facts promoted)
Warm Tier (SQLite) → Spreadsheet-Moment Snapshot
  ↓ (Hot facts changing)
Hot Tier (RAM) → Spreadsheet-Moment Live Cells + Agents
  ↓ (User interaction)
User Views (Canvas visualization, multi-device)
```

## Why This Matters for AutoCrew Evolution

### 1. **Reactive Knowledge System**
Knowledge doesn't sit static. Agents continuously monitor and improve.

### 2. **Visual Transparency**
Users see why knowledge has certain confidence (traced through agent actions, not black box).

### 3. **Distributed Teams**
Same knowledge system works locally (single user), LAN (team), cloud (organization).

### 4. **User Engagement**
Watching facts evolve in real-time is more engaging than querying static database.

### 5. **Emergent Behavior**
Agents interacting with cells create unexpected intelligence (not programmed explicitly).

## Implementation Challenges

1. **Cell Change Frequency:** With agents constantly updating cells, network sync becomes bottleneck
2. **Agent Cascades:** One agent's action triggers another's trigger → computation explosion
3. **Deadlock Prevention:** Multiple agents updating same cell simultaneously
4. **Memory vs. Scale:** Full history tracking expensive for large knowledge bases
5. **User Experience:** Too many real-time updates overwhelming; need intelligent aggregation

## Risk Assessment

- **Integration Complexity:** Moderate (wrap AutoCrew data in spreadsheet model)
- **Safe Path:** Prototype with small knowledge subset (50 facts, 5 agents)
- **Fallback:** Keep SQLite as backup store; Spreadsheet-Moment for visualization/reactivity
- **Performance:** Measure overhead of agent monitoring vs. SQLite batch updates

## Next Steps

1. **Build Data Adapter:** Map AutoCrew SQLite schema to Spreadsheet-Moment cells
2. **Implement 3 Agent Types:** Consistency, Confidence, Synthesis
3. **Prototype Visualization:** Canvas-based confidence trend display
4. **Test Reactivity:** Modify source, watch cascading updates
5. **Measure Performance:** Query latency with agents active vs. inactive
6. **Expand Agents:** Add more types based on observed opportunities
7. **User Study:** How do users interact with reactive knowledge vs. static?

## Long-Term Vision

**From Static Knowledge Base to Living Knowledge Organism**

Current: AutoCrew compiles knowledge into database
Future: AutoCrew maintains living, reactive knowledge that evolves continuously

Imagine:
- Fact confidence updates in real-time as new sources appear
- Contradictions automatically surface to human review
- Related facts notify each other of updates
- Visualization shows knowledge health (green=stable, yellow=needs review, red=contradicted)
- Agents optimize their own behavior based on success patterns
- Teams collaborate within same knowledge spreadsheet, seeing edits in real-time
- Knowledge becomes valuable not for being complete, but for being *alive and improving*

This transforms AutoCrew from "knowledge compiler" to "knowledge organism."
