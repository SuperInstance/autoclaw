# autoclaw × Substrate — Integration Map

> How autoclaw's crew maps to the substrate's 11 opcodes.

## The 4 crew roles map to 4 opcodes

| Crew Role | Substrate Opcode | What It Does | Output |
|-----------|------------------|--------------|--------|
| **Researcher** | WITNESS | Scans canon, notices gaps, records events | gap reports · watch lists · brew topics |
| **Teacher** | PROOF | Generates Q&A about each concept, validates learnability | Q&A pairs · 5-level learning paths |
| **Critic** | JEV | Validates prose and code, spots contradictions | confidence scores · contradiction reports · citations |
| **Distiller** | BIND | Batches entries into knowledge summaries | JSONL exports · pattern detection · canon pieces |

## What the crew does NOT map to (yet)

The crew currently has 4 roles. The substrate has 11 opcodes. The remaining 7 are reserved for future cast members:

| Opcode | Future Cast Member |
|--------|---------------------|
| LINK | **Curator** — connects related brews into lineages |
| FORGET | **Janitor** — archives dead code, deprecated concepts |
| VIEW | **Lens** — renders the canon in different lenses (Mechanic/Shepherd/Skeptic/Historian) |
| TICK | **Clock** — schedules the crew, advances time, marks scars |
| ROUTE | **Router** — directs each new witness to the right cast member |
| CRDT | **Sync** — reconciles concurrent updates across the fleet |
| EFFECT | **Catalyst** — proposes changes to the substrate itself |

## Webpage integration

The crew's output flows into our webpage ecosystem:

```
crew (autoclaw)
  ↓
researcher writes gap reports → /future/wave-XX.md (new brew ideas)
  ↓
teacher generates Q&A → /learn/ pages on ai-writings
  ↓
critic validates → confidence scores on each canon piece
  ↓
distiller batches → new /prose/ pieces + luciddreamer.ai sections
```

## Why this matters

The web is the display. autoclaw is the engine. The 100+ webpages across our network (luciddreamer.ai, ai-writings, crab-traps, the lower-level substrate repos, the music fleet, etc.) are static at any moment. autoclaw makes them ACTIVE.

Without autoclaw: each webpage is a snapshot.
With autoclaw: each webpage is a continuously-improving artifact.

## Cost economics

- autoclaw runs on Casey's GPU fleet (ProArt RTX4050 + smaller boxes)
- Single crew cycle = ~30 seconds (researcher → teacher → critic → distiller)
- 100 cycles/day = 50 minutes GPU time
- Each cycle improves 1 webpage section
- 100 cycles = 100 improved sections = visible change across the network

## Live integration points

1. **live-canon.superinstance.dev** — autoclaw's researcher watches this, every new piece gets a witness entry
2. **ai-writings.pages.dev** — autoclaw's distiller publishes here (the team writes to the team)
3. **crab-traps.pages.dev** — autoclaw's critic reads exit states, scores visitors
4. **luciddreamer.ai** — autoclaw's teacher generates the learning paths for the homepage's prose section
5. **constraint-theory-core** — autoclaw's researcher writes docs in /docs/cns-v3/

## The promise

> Every webpage on our network improves while you sleep.

That's the dream home. luciddreamer.ai isn't a static page — it's a living document. The crew keeps watching.
