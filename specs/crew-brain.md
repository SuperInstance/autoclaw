# Crew Brain Specification

**File to implement:** `crew/brain.py`
**Depends on:** `schemas/knowledge.yaml`, `schemas/task.yaml`, `crew/scheduler.py`
**Depended on by:** `crew/daemon.py`

## Purpose

The crew brain is the decision engine. It uses the LLM to:
1. Plan how to approach a task (which experiments to run)
2. Analyze experiment results (what did we learn?)
3. Generate follow-up tasks (what should we do next?)
4. Decide what to study (when no tasks are queued)
5. Maintain the knowledge base (distill insights)

The brain is the only component that calls the LLM API. Everything else is
deterministic code.

## Design Principle: LLM as Advisor, Code as Executor

The LLM **advises**. It does not execute. The brain asks the LLM:
- "Given this task and what we know, what experiments should I run?"
- "Given these results, what did we learn?"
- "What should we study next?"

The LLM responds with structured data (JSON). The code parses it and acts.
The LLM never runs code directly, never touches train.py directly, never
interacts with the filesystem. It only produces plans and analyses.

## Core Methods

### 1. plan_experiments(task, knowledge) → ExperimentPlan

Called when starting a new task. Produces a concrete plan.

```python
def plan_experiments(self, task: Task, knowledge: List[KnowledgeEntry]) -> ExperimentPlan:
    """
    Ask the LLM to plan experiments for a task.

    Input:
      - task: The task to plan for (title, description, experiment spec, hints)
      - knowledge: Relevant entries from knowledge base

    Output:
      ExperimentPlan with:
        - experiments: List of parameter sets to try
        - rationale: Why these experiments (string)
        - early_stop_condition: When to stop early (optional)
    """

    prompt = f"""You are an autonomous ML research crew member. Plan experiments for this task.

TASK: {task.title}
DESCRIPTION: {task.description}
EXPERIMENT TYPE: {task.experiment.type if task.experiment else 'general'}
PARAMETER SPACE: {task.experiment.parameters if task.experiment else 'open'}
BUDGET: {task.experiment.num_experiments} experiments, {task.experiment.time_budget_seconds}s each
BASELINE: {task.experiment.baseline or 'unknown'}
METRIC: {task.experiment.success_metric} (lower is better)

CAPTAIN'S HINTS:
{self.format_hints(task.hints)}

RELEVANT KNOWLEDGE:
{self.format_knowledge(knowledge)}

Respond with a JSON object:
{{
  "experiments": [
    {{"parameters": {{"learning_rate": 0.005, ...}}, "rationale": "why this config"}},
    ...
  ],
  "overall_rationale": "why this ordering and these experiments",
  "early_stop_condition": "stop if 3 consecutive experiments show < 0.1% improvement",
  "notes": "anything the captain should know about this plan"
}}

Rules:
- Use knowledge to avoid testing known-bad configurations
- Start with most promising configurations first
- If captain gave hints, weight them heavily but use your judgment
- Stay within the parameter space specified
- If the task is exploratory, be creative. If it's a sweep, be systematic.
"""

    response = self.llm.chat(prompt, response_format="json")
    return ExperimentPlan.from_json(response)
```

### 2. analyze_results(task, experiments) → TaskResults

Called after all experiments in a task are done. Produces findings.

```python
def analyze_results(self, task: Task, experiments: List[ExperimentResult]) -> TaskResults:
    """
    Ask the LLM to analyze experiment results and extract insights.

    Input:
      - task: The completed task
      - experiments: All experiment results (parameters, metrics, logs)

    Output:
      TaskResults with:
        - summary: One-paragraph summary
        - findings: List of notable findings
        - knowledge_entries: New insights for the knowledge base
        - suggested_follow_ups: Tasks to create next
        - notification_severity: How important is this result
    """

    prompt = f"""You are an autonomous ML research crew member. Analyze these experiment results.

TASK: {task.title}
DESCRIPTION: {task.description}
BASELINE: {task.experiment.baseline or 'unknown'}

EXPERIMENTS ({len(experiments)} total):
{self.format_experiments_table(experiments)}

EXISTING KNOWLEDGE (for context):
{self.format_knowledge(self.get_relevant_knowledge(task))}

Respond with JSON:
{{
  "summary": "one paragraph summary of what was found",
  "best_experiment": {{
    "index": 0,
    "metric_value": 0.994,
    "parameters": {{...}},
    "improvement_pct": 4.5
  }},
  "findings": [
    "Finding 1: clear, actionable insight",
    "Finding 2: ..."
  ],
  "knowledge_entries": [
    {{
      "insight": "Concise, actionable statement of what was learned",
      "category": "hyperparameter",
      "tags": ["learning-rate"],
      "confidence": "high",
      "conditions": "Under what conditions this holds"
    }}
  ],
  "suggested_follow_ups": [
    {{
      "title": "Task title",
      "reason": "Why this follow-up is warranted",
      "priority": 5,
      "experiment": {{
        "type": "sweep",
        "parameters": {{...}},
        "num_experiments": 10
      }}
    }}
  ],
  "notification_severity": "important"
}}

Rules:
- Be honest about what was found. Don't overclaim.
- If results are inconclusive, say so.
- Knowledge entries must be actionable — something the crew can use later.
- Follow-ups should be justified by the data, not speculative.
- If baseline was beaten, this is "important". If not, this is "info".
"""

    response = self.llm.chat(prompt, response_format="json")
    return TaskResults.from_json(response)
```

### 3. decide_study_topic(knowledge, history) → StudyTopic

Called when the task board is empty and the crew enters study mode.

```python
def decide_study_topic(self, knowledge: List[KnowledgeEntry],
                        recent_tasks: List[Task]) -> StudyTopic:
    """
    Ask the LLM what to study next.

    Input:
      - knowledge: All active knowledge entries
      - recent_tasks: Last 20 completed tasks

    Output:
      StudyTopic with:
        - title: What to study
        - reason: Why this is worth studying
        - experiment_plan: How to investigate
    """

    prompt = f"""You are an autonomous ML research crew member. The task board is empty.
You have free time to study and explore. What would be most valuable to investigate?

WHAT WE KNOW ({len(knowledge)} entries):
{self.format_knowledge_summary(knowledge)}

RECENT WORK (last 20 tasks):
{self.format_task_history(recent_tasks)}

KNOWLEDGE GAPS (entries with low confidence or marked "questioned"):
{self.format_knowledge_gaps(knowledge)}

Respond with JSON:
{{
  "title": "What to study",
  "reason": "Why this is the most valuable use of free time right now",
  "experiment_plan": {{
    "type": "exploration",
    "parameters": {{...}},
    "num_experiments": 5,
    "success_metric": "val_bpb"
  }},
  "expected_value": "What we hope to learn and how it helps future work"
}}

Rules:
- Prioritize filling knowledge gaps (questioned or low-confidence entries)
- Investigate parameter interactions that haven't been tested
- Validate external knowledge (papers) with local experiments
- Don't re-run experiments we've already done
- Keep it small (5-10 experiments max for study sessions)
- Pick the topic with highest expected information gain
"""

    response = self.llm.chat(prompt, response_format="json")
    return StudyTopic.from_json(response)
```

### 4. review_paper(trigger_context) → PaperReview

Called when a paper trigger fires. Assesses relevance without running experiments.

```python
def review_paper(self, trigger_context: dict) -> PaperReview:
    """
    Ask the LLM to review a paper for relevance to current work.

    Output:
      PaperReview with:
        - relevant: bool
        - summary: Brief summary of the paper
        - actionable_ideas: List of experiment ideas from the paper
        - follow_up_task: Task to create (if relevant), or None
    """

    prompt = f"""You are an ML research crew member. A new paper was detected by a trigger.
Assess its relevance to our current work.

PAPER:
Title: {trigger_context['title']}
Abstract: {trigger_context.get('summary', 'No abstract available')}
URL: {trigger_context.get('url', 'N/A')}

OUR CURRENT FOCUS:
{self.format_current_focus()}

Respond with JSON:
{{
  "relevant": true/false,
  "summary": "2-3 sentence summary of the paper",
  "relevance_reason": "Why this is/isn't relevant to our work",
  "actionable_ideas": [
    "Idea we could test based on this paper"
  ],
  "follow_up_task": {{
    "title": "Test [idea from paper]",
    "description": "...",
    "priority": 5,
    "experiment": {{...}}
  }} or null
}}

Rules:
- Be selective. Most papers aren't relevant. That's fine.
- Only create follow-up if there's a concrete, testable idea.
- Don't recommend replicating the paper's full methodology — extract one testable insight.
"""

    response = self.llm.chat(prompt, response_format="json")
    return PaperReview.from_json(response)
```

### 5. generate_modifications(experiment_params) → CodeModification

Called for each experiment. Produces the actual train.py modifications.

```python
def generate_modifications(self, experiment_params: dict,
                            current_train_py: str) -> CodeModification:
    """
    Ask the LLM to generate the specific code changes for train.py.

    This is the only place where code generation happens. The LLM reads
    the current train.py and produces a diff or replacement for the
    specific parameters being tested.

    Output:
      CodeModification with:
        - changes: List of (old_text, new_text) replacements
        - explanation: What was changed and why
    """

    prompt = f"""You are modifying train.py for an experiment.

CURRENT train.py:
```python
{current_train_py}
```

PARAMETERS TO SET:
{yaml.dump(experiment_params)}

Generate the exact text replacements needed. Respond with JSON:
{{
  "changes": [
    {{
      "old_text": "exact text to find in train.py",
      "new_text": "exact replacement text",
      "description": "what this change does"
    }}
  ],
  "explanation": "Summary of all changes"
}}

Rules:
- Make MINIMAL changes. Only modify what's needed for the parameter values.
- old_text must be an EXACT substring of the current train.py.
- Don't restructure code. Don't add comments. Don't refactor.
- If a parameter maps to a constant (like DEPTH=8), just change the value.
- If a parameter requires adding code (like lr_schedule="cosine"), add minimal code.
- Preserve all existing functionality not related to the parameter change.
"""

    response = self.llm.chat(prompt, response_format="json")
    return CodeModification.from_json(response)
```

## LLM Fallback Mode

When the LLM is unavailable (API down, rate limited, cost exceeded), the brain
switches to **pre-programmed mode**:

```python
def plan_experiments_fallback(self, task: Task) -> ExperimentPlan:
    """Plan without LLM — use parameter grid from task spec."""
    if not task.experiment or not task.experiment.parameters:
        return None  # Can't plan without LLM and without parameters

    # Generate grid from task parameters
    experiments = []
    param_names = list(task.experiment.parameters.keys())
    param_values = list(task.experiment.parameters.values())

    # Make values into lists if they aren't already
    param_values = [v if isinstance(v, list) else [v] for v in param_values]

    # Generate grid (itertools.product)
    from itertools import product
    for combo in product(*param_values):
        params = dict(zip(param_names, combo))
        experiments.append({"parameters": params, "rationale": "grid search"})

    # Limit to num_experiments
    experiments = experiments[:task.experiment.num_experiments]

    return ExperimentPlan(
        experiments=experiments,
        rationale="Fallback: systematic grid search (LLM unavailable)",
        early_stop_condition=None,
    )

def generate_modifications_fallback(self, params: dict, train_py: str) -> CodeModification:
    """Generate modifications without LLM — simple constant replacement."""
    changes = []
    for param, value in params.items():
        # Look for PARAM_NAME = ... pattern
        import re
        pattern = rf"({param.upper()}\s*=\s*)([^\n]+)"
        match = re.search(pattern, train_py)
        if match:
            changes.append({
                "old_text": match.group(0),
                "new_text": f"{match.group(1)}{value}",
                "description": f"Set {param} = {value}"
            })
    return CodeModification(changes=changes, explanation="Fallback: regex replacement")
```

## Token Budget Management

The brain tracks LLM token usage to stay within budget:

```python
class TokenBudget:
    def __init__(self, max_per_minute: int, max_cost_per_day: float):
        self.max_per_minute = max_per_minute
        self.max_cost_per_day = max_cost_per_day
        self.tokens_this_minute = 0
        self.cost_today_usd = 0.0
        self.minute_start = time.time()
        self.day_start = datetime.now(timezone.utc).date()

    def can_spend(self, estimated_tokens: int) -> bool:
        self.reset_if_needed()
        if self.tokens_this_minute + estimated_tokens > self.max_per_minute:
            return False
        if self.max_cost_per_day > 0:
            estimated_cost = estimated_tokens * self.cost_per_token
            if self.cost_today_usd + estimated_cost > self.max_cost_per_day:
                return False
        return True

    def record_usage(self, tokens: int, cost_usd: float):
        self.tokens_this_minute += tokens
        self.cost_today_usd += cost_usd
```

## Data Structures

```python
@dataclass
class ExperimentPlan:
    experiments: List[dict]       # [{"parameters": {...}, "rationale": "..."}]
    rationale: str                # Overall plan reasoning
    early_stop_condition: str     # When to stop early (optional)
    notes: str = ""

@dataclass
class TaskResults:
    summary: str
    best_experiment: dict         # {"index": N, "metric_value": F, ...}
    findings: List[str]
    knowledge_entries: List[dict] # New knowledge to add
    suggested_follow_ups: List[dict]
    notification_severity: str

@dataclass
class StudyTopic:
    title: str
    reason: str
    experiment_plan: dict
    expected_value: str

@dataclass
class PaperReview:
    relevant: bool
    summary: str
    relevance_reason: str
    actionable_ideas: List[str]
    follow_up_task: dict          # Task to create, or None

@dataclass
class CodeModification:
    changes: List[dict]           # [{"old_text": ..., "new_text": ..., "description": ...}]
    explanation: str
```

## Implementation Checklist for Haiku

```
[ ] Create crew/brain.py with CrewBrain class
[ ] Implement LLM client wrapper (supports anthropic, openai, ollama, vllm)
[ ] Implement plan_experiments() with proper prompt and JSON parsing
[ ] Implement analyze_results() with findings extraction
[ ] Implement decide_study_topic() for self-directed learning
[ ] Implement review_paper() for trigger-based paper assessment
[ ] Implement generate_modifications() for train.py code changes
[ ] Implement all fallback methods (plan_fallback, modify_fallback)
[ ] Implement TokenBudget for rate limiting and cost control
[ ] Implement format_* helper methods (format_hints, format_knowledge, etc.)
[ ] Handle JSON parse errors from LLM (retry once, then fallback)
[ ] Handle LLM API errors (retry 3x with backoff, then fallback mode)
[ ] Test: plan_experiments with mock LLM returns valid plan
[ ] Test: analyze_results produces knowledge entries
[ ] Test: fallback mode works when LLM unavailable
[ ] Test: token budget correctly limits spending
```
