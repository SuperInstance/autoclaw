# autoclaw — Agents as Apps

## Principle

autoclaw **IS** the training operator. It is not a library to be called, nor a service to be configured — it is an agent-facing application that owns the training lifecycle.

## How Agents Use autoclaw

An agent does not manage training runs. An agent **decides what to train**.

1. **Intent** — The agent expresses a training goal: "I need a model that scores > 0.92 on benchmark X."
2. **Data** — The agent (or openmind) prepares synthetic data and places it in the watched directory.
3. **autoclaw handles the rest** — Training, evaluation, promotion, rollback, budget enforcement.

## Why This Matters

Training is mechanical. The agent's value is in **deciding what to train** and **curating the data**, not in babysitting GPU processes. autoclaw removes the agent from the mechanics entirely.

## Integration with the Ecosystem

- **openmind**: Decomposes problems. When a cell needs training, openmind drops an intent. autoclaw fulfills it.
- **nanochat**: The training engine autoclaw orchestrates.
- **conservation-law**: The budget autoclaw respects.
- **categorical-agents**: The composition algebra that lets agents declare training needs as typed intents.
