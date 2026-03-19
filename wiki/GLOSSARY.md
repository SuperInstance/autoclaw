# Glossary

Key terms and definitions used throughout AutoClaw.

---

## A

**Agent**: Autonomous worker that executes tasks (Researcher, Teacher, Critic, Distiller)

**AgentPool**: Concurrent manager of agents, handles assignment and lifecycle

**API Key**: Secret credential for external service access (encrypted in AutoClaw)

**Audit Log**: Record of all operations for security and compliance

---

## B

**BaseAgent**: Foundation class that all agents inherit from

**Board**: Task queue view showing all tasks and their status

**Bootstrap**: 8-step initialization sequence on daemon startup

---

## C

**Circuit Breaker**: Pattern to prevent cascading failures (CLOSED/OPEN/HALF_OPEN)

**CLI**: Command-line interface for controlling AutoClaw

**Confidence**: Score (0-1.0) indicating trust in a knowledge entry

---

## D

**Daemon**: Always-on process that runs the main loop

**Distiller**: Agent that synthesizes and compresses knowledge

---

## E

**Entry**: Single piece of knowledge with metadata

**Error Handling**: Retry + circuit breaker + graceful degradation

---

## F

**Findings**: Results from task execution, converted to knowledge

**Flowstate**: Sandbox mode for safe experimentation

---

## G

**Garbage Collection**: Cleanup of old/expired knowledge entries

**Graceful Degradation**: Continue operating with reduced capability

---

## H

**Handoff**: Context transfer for long-running tasks

**Health Check**: Verification that all components are operational

**Hot Tier**: Knowledge storage tier with 3600s TTL

---

## K

**Knowledge**: Learned facts with confidence, created from task results

**Knowledge Store**: Tiered persistence system (hot/warm/cold)

---

## L

**Lifecycle Manager**: Component that handles cleanup and resource management

---

## M

**Message Bus**: SQLite-backed pub/sub system for inter-agent communication

**Metrics**: System statistics (throughput, latency, resource usage)

---

## N

**Notification**: Event sent when task completes or finding discovered

---

## P

**Priority**: Task urgency (1-9, where 9 is highest)

**Publication**: Sending message to all subscribers of a topic

---

## Q

**Query**: Search operation on knowledge store

**Queue**: Task waiting list, ordered by priority

---

## R

**Researcher**: Agent that searches web and synthesizes findings

**Retry**: Automatic reattempt with exponential backoff

---

## S

**Scheduler**: Component that reads tasks and assigns to agents

**Socket**: Unix domain socket for CLI ↔ Daemon communication

**Subscription**: Registration to receive messages on a topic

---

## T

**Task**: Unit of work submitted by user, assigned to agent

**Teacher**: Agent that generates Q&A and educational content

**Tier**: Knowledge storage category (hot/warm/cold based on TTL)

**Topic**: Message routing key in pub/sub system

**Trigger**: External event that spawns autonomous task

**TTL**: Time-to-live before knowledge expires and moves to next tier

---

## W

**Warm Tier**: Knowledge storage tier with 86400s (1 day) TTL

**Workflow**: Multi-step pattern for complex operations

---

## 🔗 See Also

- [QUICK_START.md](QUICK_START.md) - Getting started
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [HOME.md](HOME.md) - Documentation index

**See also**: All other wiki pages
