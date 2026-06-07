# autoclaw — Integration Map

## Overview

autoclaw is the **training operator** for the SuperInstance ecosystem. It automates the full training lifecycle — from watching for new data to producing an improved model — while respecting conservation budgets and reporting outcomes.

## Wiring Diagram

```
openmind (decompose → train intent)
  │
  ▼
autoclaw ◄──── conservation-law (GPU budget tracking)
  │
  ▼
nanochat (training execution)
```

## Integration Points

### nanochat — Automated Training Loop

autoclaw watches a configured directory for new synthetic data batches. When a batch arrives:

1. **Trigger** — autoclaw invokes the nanochat training entrypoint with the new data.
2. **Train** — nanochat executes the fine-tune run on available GPU(s).
3. **Evaluate** — autoclaw runs evaluation against a held-out benchmark.
4. **Decide** — If metrics improve, the new checkpoint is promoted. Otherwise, autoclaw rolls back to the previous checkpoint.

This loop runs unattended. An agent (or openmind decomposition) only needs to drop data into the watched directory.

### openmind — Decompose → Train

openmind decomposes a problem into cells. When a cell's solution requires a trained model, openmind emits a training intent:

- **Input**: cell metadata (data path, target metric, budget).
- **Output**: autoclaw picks up the intent, runs the training loop, and writes the resulting model path back to the cell.

### conservation-law — GPU Budget Tracking

Every training run consumes GPU hours. autoclaw queries conservation-law before starting a job:

- **Check budget**: Is there sufficient GPU allocation for this run?
- **Reserve**: Claim the estimated hours before training begins.
- **Report**: Actual hours consumed are reported back after completion.

If the budget is exhausted, autoclaw queues the job and notifies the requesting agent.

## Configuration

autoclaw reads its configuration from `CAPABILITY.toml` at the repo root. The `si/training_loop.py` script provides a standalone implementation of the core loop.
