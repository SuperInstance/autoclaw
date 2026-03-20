# AutoClaw Implementation Instructions

**Step-by-Step Coding Guide for Roadmap Implementation**

---

## Table of Contents
1. [Phase 1: Core Autonomy](#phase-1-core-autonomy)
2. [Phase 2: Multi-Agent Collaboration](#phase-2-multi-agent-collaboration)
3. [Phase 3: Production Readiness](#phase-3-production-readiness)
4. [Phase 4: Scale & Optimization](#phase-4-scale--optimization)

---

## Phase 1: Core Autonomy

### Task 1.1: Knowledge Store Persistence

**File:** `crew/knowledge/store.py`

**Objective:** Make knowledge entries persist to disk and load on startup.

**Step-by-Step Implementation:**

1. **Add YAML import at the top of the file:**
```python
import yaml
from pathlib import Path
```

2. **Add class constants to KnowledgeStore class:**
```python
class KnowledgeStore:
    KNOWLEDGE_FILE = Path.home() / '.autoclaw' / 'knowledge_store.yaml'
    
    def __init__(self):
        self.entries = []
        self.counter = 0
        self._load_from_disk()
```

3. **Implement _save_to_disk method:**
```python
def _save_to_disk(self):
    """Save all knowledge entries to YAML file."""
    try:
        self.KNOWLEDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        entries_data = [entry.to_dict() for entry in self.entries]
        data = {
            'entries': entries_data,
            'counter': self.counter,
            'version': '1.0'
        }
        with open(self.KNOWLEDGE_FILE, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
        logger.info(f"Saved {len(self.entries)} entries to {self.KNOWLEDGE_FILE}")
    except Exception as e:
        logger.error(f"Failed to save knowledge to disk: {e}")
```

4. **Implement _load_from_disk method:**
```python
def _load_from_disk(self):
    """Load knowledge entries from YAML file."""
    try:
        if self.KNOWLEDGE_FILE.exists():
            with open(self.KNOWLEDGE_FILE, 'r') as f:
                data = yaml.safe_load(f)
                if data:
                    self.entries = [KnowledgeEntry.from_dict(e) for e in data.get('entries', [])]
                    self.counter = data.get('counter', 0)
            logger.info(f"Loaded {len(self.entries)} entries from {self.KNOWLEDGE_FILE}")
    except Exception as e:
        logger.error(f"Failed to load knowledge from disk: {e}")
        self.entries = []
        self.counter = 0
```

5. **Modify add_entry method to call save:**
```python
def add_entry(self, entry: KnowledgeEntry) -> int:
    """Add a knowledge entry and persist to disk."""
    entry.id = self.counter + 1
    self.entries.append(entry)
    self.counter += 1
    self._save_to_disk()
    return entry.id
```

**Testing:**
1. Start daemon: `crew start`
2. Add knowledge entry: `crew knowledge add --category test --insight "test insight"`
3. Stop daemon: `crew stop`
4. Start daemon: `crew start`
5. Verify knowledge persists: `crew knowledge list`

---

### Task 1.2: Trigger Task Creation Integration

**File:** `crew/triggers/daemon.py`

**Objective:** Make triggers automatically create tasks when events occur.

**Step-by-Step Implementation:**

1. **Add import for scheduler:**
```python
from crew.scheduler_enhancement import get_scheduler_enhancement
from crew.scheduler import Task
```

2. **Modify TriggerDaemon.__init__ to get scheduler:**
```python
def __init__(self, config_path: str):
    self.config_path = config_path
    self.config = self._load_config()
    self.scheduler = get_scheduler_enhancement()
    self.running = False
    self.triggers = []
    self._initialize_triggers()
```

3. **Implement automatic task creation in _process_trigger:**
```python
def _process_trigger(self, trigger_config: dict, event_data: dict):
    """Process a trigger event and create task automatically."""
    try:
        logger.info(f"Processing trigger: {trigger_config['name']}")
        
        task = Task(
            title=f"Trigger: {trigger_config['name']}",
            description=self._format_task_description(trigger_config, event_data),
            task_type='triggered',
            priority=trigger_config.get('priority', 5),
            metadata={
                'trigger_source': trigger_config['source'],
                'trigger_name': trigger_config['name'],
                'event_data': event_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
        
        task_id = self.scheduler.add_task(task)
        logger.info(f"Created task {task_id} from trigger {trigger_config['name']}")
        
        return task_id
    except Exception as e:
        logger.error(f"Failed to process trigger: {e}")
        return None
```

4. **Implement task description formatting:**
```python
def _format_task_description(self, trigger_config: dict, event_data: dict) -> str:
    """Format a human-readable task description."""
    source = trigger_config['source']
    name = trigger_config['name']
    
    if source == 'rss':
        title = event_data.get('title', 'No title')
        link = event_data.get('link', 'No link')
        return f"RSS Feed: {name}\n\nTitle: {title}\nLink: {link}"
    elif source == 'webhook':
        payload = event_data.get('payload', {})
        return f"Webhook: {name}\n\nPayload: {json.dumps(payload, indent=2)}"
    else:
        return f"Trigger: {name}\n\nData: {json.dumps(event_data, indent=2)}"
```

**Testing:**
1. Configure RSS trigger in config/triggers.yaml
2. Start daemon: `crew start`
3. Wait for RSS feed update
4. Check tasks: `crew tasks list`
5. Verify task created with correct metadata

---

### Task 1.3: Notification Delivery

**File:** `crew/notifications/manager.py`

**Objective:** Deliver notifications to configured channels (email, SMS, etc.).

**Step-by-Step Implementation:**

1. **Implement channel selection:**
```python
def _get_channels_for_severity(self, severity: str) -> List[NotificationChannel]:
    """Get channels that should receive notifications of this severity."""
    channels = []
    severity_level = self._severity_to_level(severity)
    
    for channel in self.channels:
        if channel.min_level <= severity_level:
            channels.append(channel)
    
    return channels

def _severity_to_level(self, severity: str) -> int:
    """Convert severity string to numeric level."""
    levels = {
        'info': 1,
        'warning': 2,
        'error': 3,
        'critical': 4
    }
    return levels.get(severity.lower(), 1)
```

2. **Implement notification delivery:**
```python
def deliver_notification(self, notification: Notification) -> bool:
    """Deliver notification via configured channels."""
    channels = self._get_channels_for_severity(notification.severity)
    
    if not channels:
        logger.warning(f"No channels configured for severity: {notification.severity}")
        return False
    
    success_count = 0
    for channel in channels:
        try:
            channel.send(notification)
            notification.delivered = True
            notification.delivery_timestamp = datetime.now(timezone.utc)
            success_count += 1
            logger.info(f"Delivered notification via {channel.name}")
        except Exception as e:
            logger.error(f"Failed to deliver via {channel.name}: {e}")
    
    return success_count > 0
```

3. **Implement retry logic for failed deliveries:**
```python
def _retry_failed_notifications(self):
    """Retry notifications that failed to deliver."""
    for notification in self.notifications:
        if not notification.delivered and notification.retry_count < 3:
            try:
                self.deliver_notification(notification)
                notification.retry_count += 1
            except Exception as e:
                logger.error(f"Retry failed for notification {notification.id}: {e}")
```

**Testing:**
1. Configure email channel in config/notifications.yaml
2. Create test notification: `crew notifications test --severity info --message "Test notification"`
3. Verify email received
4. Test different severity levels

---

### Task 1.4: Context Handoff

**File:** `crew/handoff.py`

**Objective:** Enable long-running tasks to be resumed after context limits.

**Step-by-Step Implementation:**

1. **Add class constants:**
```python
class ContextHandoff:
    CHECKPOINT_DIR = Path.home() / '.autoclaw' / 'checkpoints'
    
    def __init__(self):
        self.CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
```

2. **Implement context summarization:**
```python
def _summarize_context(self, context: dict) -> str:
    """Summarize context for efficient storage."""
    summary_parts = []
    
    if 'messages' in context:
        messages = context['messages']
        summary_parts.append(f"Messages: {len(messages)} total")
        if messages:
            last_msg = messages[-1]
            summary_parts.append(f"Last message: {last_msg.get('role', 'unknown')}")
    
    if 'results' in context:
        results = context['results']
        summary_parts.append(f"Results: {len(results)} items")
    
    if 'partial_outputs' in context:
        summary_parts.append(f"Partial outputs available")
    
    return '\n'.join(summary_parts)
```

3. **Implement checkpoint saving:**
```python
def save_checkpoint(self, task_id: int, context: dict):
    """Save current task state for resumption."""
    checkpoint_file = self.CHECKPOINT_DIR / f"task_{task_id}.json"
    
    checkpoint = {
        'task_id': task_id,
        'generation': context.get('generation', 1),
        'context_summary': self._summarize_context(context),
        'partial_results': context.get('partial_results', {}),
        'next_steps': context.get('next_steps', []),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'context_keys': list(context.keys())
    }
    
    try:
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        logger.info(f"Saved checkpoint for task {task_id}")
    except Exception as e:
        logger.error(f"Failed to save checkpoint: {e}")
```

4. **Implement checkpoint loading:**
```python
def load_checkpoint(self, task_id: int) -> Optional[dict]:
    """Load saved task state."""
    checkpoint_file = self.CHECKPOINT_DIR / f"task_{task_id}.json"
    
    if not checkpoint_file.exists():
        return None
    
    try:
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
        logger.info(f"Loaded checkpoint for task {task_id}")
        return checkpoint
    except Exception as e:
        logger.error(f"Failed to load checkpoint: {e}")
        return None
```

5. **Implement context reconstruction:**
```python
def reconstruct_context(self, checkpoint: dict, original_context: dict) -> dict:
    """Reconstruct context from checkpoint and original data."""
    reconstructed = {
        'generation': checkpoint['generation'] + 1,
        'partial_results': checkpoint.get('partial_results', {}),
        'next_steps': checkpoint.get('next_steps', []),
        'resumed_from_checkpoint': True,
        'checkpoint_timestamp': checkpoint['timestamp']
    }
    
    for key in checkpoint['context_keys']:
        if key in original_context:
            reconstructed[key] = original_context[key]
    
    return reconstructed
```

**Testing:**
1. Create long-running task: `crew tasks create --title "Long task" --description "Test long task"`
2. Start task: `crew tasks run <task_id>`
3. Interrupt task (Ctrl+C)
4. Resume task: `crew tasks resume <task_id>`
5. Verify task continues from checkpoint

---

## Phase 2: Multi-Agent Collaboration

### Task 2.1: Researcher Agent

**File:** `crew/agents/researcher.py`

**Objective:** Implement agent that researches web sources and extracts insights.

**Step-by-Step Implementation:**

1. **Extend base Agent class:**
```python
from crew.agents.base import Agent
from crew.messaging import Message
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class ResearcherAgent(Agent):
    """Researches web sources, reads papers, extracts insights."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "researcher"
        self.capabilities = ["web_search", "read_urls", "extract_insights"]
```

2. **Implement message processing:**
```python
def process_message(self, message: Message) -> List[Message]:
    """Process research request."""
    content = message.content
    
    if message.message_type == "research_request":
        return self._handle_research_request(content)
    elif message.message_type == "read_url":
        return self._handle_read_url(content)
    else:
        logger.warning(f"Unknown message type: {message.message_type}")
        return []
```

3. **Implement web search:**
```python
def _handle_research_request(self, content: dict) -> List[Message]:
    """Handle research request by searching and reading sources."""
    query = content.get('query', '')
    max_sources = content.get('max_sources', 5)
    
    logger.info(f"Researching: {query}")
    
    try:
        urls = self._web_search(query, max_sources)
        insights = []
        
        for url in urls:
            content = self._read_url(url)
            if content:
                insight = self._extract_insights(content, query)
                insights.append(insight)
        
        response = Message(
            sender=self.name,
            message_type="research_results",
            content={
                'query': query,
                'insights': insights,
                'sources': urls,
                'confidence_score': self._calculate_confidence(insights)
            }
        )
        
        return [response]
    except Exception as e:
        logger.error(f"Research failed: {e}")
        return []
```

4. **Implement URL reading:**
```python
def _read_url(self, url: str) -> Optional[str]:
    """Read and extract text from URL."""
    try:
        headers = {'User-Agent': 'AutoClaw/1.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        
        return text[:10000]
    except Exception as e:
        logger.error(f"Failed to read {url}: {e}")
        return None
```

**Testing:**
1. Start daemon with researcher agent
2. Send research request: `crew agents send --to researcher --message '{"type": "research_request", "query": "machine learning"}'`
3. Review research results
4. Verify confidence scores calculated correctly

---

### Task 2.2: Teacher Agent

**File:** `crew/agents/teacher.py`

**Objective:** Generate Q&A pairs and educational content from knowledge.

**Step-by-Step Implementation:**

1. **Extend base Agent class:**
```python
from crew.agents.base import Agent
from crew.messaging import Message
from crew.knowledge.store import get_knowledge_store
import logging

logger = logging.getLogger(__name__)

class TeacherAgent(Agent):
    """Generates Q&A pairs, creates educational content."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "teacher"
        self.knowledge_store = get_knowledge_store()
```

2. **Implement concept extraction:**
```python
def _extract_concepts(self, text: str) -> List[str]:
    """Extract key concepts from text."""
    concepts = []
    
    words = text.split()
    for i, word in enumerate(words):
        if word[0].isupper() and len(word) > 3:
            concepts.append(word)
    
    return list(set(concepts))[:10]
```

3. **Implement Q&A generation:**
```python
def _generate_qa_pairs(self, concept: str, context: str) -> List[dict]:
    """Generate Q&A pairs for a concept."""
    qa_pairs = []
    
    questions = [
        f"What is {concept}?",
        f"How does {concept} work?",
        f"Why is {concept} important?",
        f"What are the key features of {concept}?"
    ]
    
    for question in questions:
        answer = self._generate_answer(question, concept, context)
        qa_pairs.append({
            'question': question,
            'answer': answer,
            'concept': concept,
            'difficulty': self._estimate_difficulty(answer)
        })
    
    return qa_pairs
```

4. **Implement message processing:**
```python
def process_message(self, message: Message) -> List[Message]:
    """Process teaching request."""
    if message.message_type == "teach_concept":
        return self._handle_teach_concept(message.content)
    elif message.message_type == "generate_qa":
        return self._handle_generate_qa(message.content)
    return []
```

**Testing:**
1. Start daemon with teacher agent
2. Send teaching request: `crew agents send --to teacher --message '{"type": "teach_concept", "concept": "neural networks"}'`
3. Review generated educational content
4. Verify Q&A pairs are relevant and accurate

---

### Task 2.3: Adaptive Scheduling

**File:** `crew/adaptive.py`

**Objective:** Make scheduler learn from past performance and optimize task assignment.

**Step-by-Step Implementation:**

1. **Create performance tracking:**
```python
from crew.scheduler import Task
from typing import Dict, List
import json
from pathlib import Path

class AdaptiveScheduler:
    def __init__(self):
        self.performance_data = {}
        self.task_history = []
        self.load_performance_data()
    
    def load_performance_data(self):
        """Load historical performance data."""
        perf_file = Path.home() / '.autoclaw' / 'performance.json'
        if perf_file.exists():
            with open(perf_file, 'r') as f:
                data = json.load(f)
                self.performance_data = data.get('agent_performance', {})
                self.task_history = data.get('task_history', [])
```

2. **Implement performance tracking:**
```python
def record_task_completion(self, task: Task, agent: str, duration: float, success: bool):
    """Record task completion metrics."""
    task_type = task.task_type
    
    if task_type not in self.performance_data:
        self.performance_data[task_type] = {}
    
    if agent not in self.performance_data[task_type]:
        self.performance_data[task_type][agent] = {
            'count': 0,
            'success_count': 0,
            'total_duration': 0,
            'avg_duration': 0
        }
    
    perf = self.performance_data[task_type][agent]
    perf['count'] += 1
    if success:
        perf['success_count'] += 1
    perf['total_duration'] += duration
    perf['avg_duration'] = perf['total_duration'] / perf['count']
    
    self.save_performance_data()
```

3. **Implement agent selection:**
```python
def select_best_agent(self, task: Task, available_agents: List[str]) -> str:
    """Select the best agent for a task based on performance."""
    task_type = task.task_type
    
    if task_type not in self.performance_data:
        return available_agents[0]
    
    best_agent = None
    best_score = -1
    
    for agent in available_agents:
        if agent in self.performance_data[task_type]:
            perf = self.performance_data[task_type][agent]
            score = self._calculate_agent_score(perf)
            if score > best_score:
                best_score = score
                best_agent = agent
    
    return best_agent if best_agent else available_agents[0]
```

4. **Implement score calculation:**
```python
def _calculate_agent_score(self, perf: dict) -> float:
    """Calculate agent performance score."""
    success_rate = perf['success_count'] / perf['count'] if perf['count'] > 0 else 0
    avg_duration = perf['avg_duration']
    
    score = (success_rate * 0.7) + (1 / (avg_duration + 1) * 0.3)
    return score
```

**Testing:**
1. Complete several tasks with different agents
2. Check performance data: `crew performance show`
3. Verify adaptive scheduler selects best agents
4. Test with new task types

---

## Phase 3: Production Readiness

### Task 3.1: Unit Tests

**File:** `tests/test_knowledge_store.py`

**Objective:** Create comprehensive unit tests for knowledge store.

**Step-by-Step Implementation:**

1. **Create test file structure:**
```python
import pytest
from crew.knowledge.store import KnowledgeStore, KnowledgeEntry
from datetime import datetime, timezone

@pytest.fixture
def store():
    """Create a fresh knowledge store for each test."""
    return KnowledgeStore()

@pytest.fixture
def sample_entry():
    """Create a sample knowledge entry."""
    return KnowledgeEntry(
        insight="Test insight",
        category="test",
        confidence=0.9
    )
```

2. **Implement add_entry test:**
```python
def test_add_entry(store, sample_entry):
    """Test adding a knowledge entry."""
    entry_id = store.add_entry(sample_entry)
    
    assert entry_id == 1
    assert len(store.entries) == 1
    assert store.entries[0].insight == "Test insight"
    assert store.entries[0].category == "test"
```

3. **Implement query by category test:**
```python
def test_query_by_category(store):
    """Test querying entries by category."""
    entry1 = KnowledgeEntry(insight="Test 1", category="test")
    entry2 = KnowledgeEntry(insight="Test 2", category="production")
    entry3 = KnowledgeEntry(insight="Test 3", category="test")
    
    store.add_entry(entry1)
    store.add_entry(entry2)
    store.add_entry(entry3)
    
    results = store.query_by_category("test")
    
    assert len(results) == 2
    assert all(e.category == "test" for e in results)
```

4. **Implement persistence test:**
```python
def test_persistence():
    """Test that entries persist across restarts."""
    store1 = KnowledgeStore()
    entry = KnowledgeEntry(insight="Persistent test", category="test")
    store1.add_entry(entry)
    
    store2 = KnowledgeStore()
    results = store2.query_by_category("test")
    
    assert len(results) == 1
    assert results[0].insight == "Persistent test"
```

**Testing:**
1. Run tests: `pytest tests/test_knowledge_store.py -v`
2. Ensure all tests pass
3. Check coverage: `pytest --cov=crew/knowledge/store`

---

### Task 3.2: Error Handling

**File:** `crew/error_handling.py`

**Objective:** Implement comprehensive error handling and recovery.

**Step-by-Step Implementation:**

1. **Create error handler class:**
```python
from crew.scheduler import Task
from crew.notifications.manager import get_notification_manager
import logging

logger = logging.getLogger(__name__)

class ErrorHandler:
    def __init__(self):
        self.notification_manager = get_notification_manager()
        self.recovery_strategies = {
            'timeout': self._handle_timeout,
            'resource_exhaustion': self._handle_resource_exhaustion,
            'api_failure': self._handle_api_failure,
            'data_corruption': self._handle_data_corruption
        }
```

2. **Implement experiment failure handling:**
```python
def handle_experiment_failure(self, error: Exception, task: Task):
    """Handle failed experiment with automatic recovery."""
    error_type = self._classify_error(error)
    
    logger.error(f"Experiment failed: {error_type} - {error}")
    
    recovery_plan = self._create_recovery_plan(error_type, task)
    self._execute_recovery_plan(recovery_plan)
    
    self._notify_failure(task, error)
    
    return recovery_plan
```

3. **Implement timeout handling:**
```python
def _handle_timeout(self, error: Exception, task: Task) -> dict:
    """Handle task timeout."""
    recovery = {
        'action': 'retry_with_adjusted_params',
        'params': {
            'timeout': task.timeout * 2,
            'memory_limit': task.memory_limit * 1.5
        },
        'max_retries': 3
    }
    
    logger.info(f"Timeout recovery: Increase timeout to {recovery['params']['timeout']}s")
    
    return recovery
```

4. **Implement resource exhaustion handling:**
```python
def _handle_resource_exhaustion(self, error: Exception, task: Task) -> dict:
    """Handle out-of-memory or disk-space situations."""
    recovery = {
        'action': 'free_resources_and_retry',
        'params': {
            'pause_non_critical_tasks': True,
            'archive_old_data': True,
            'reduce_batch_size': 0.5
        },
        'max_retries': 2
    }
    
    logger.warning("Resource exhaustion: Pausing non-critical tasks")
    
    return recovery
```

**Testing:**
1. Simulate timeout error
2. Verify recovery plan created
3. Test resource exhaustion scenario
4. Verify notifications sent

---

### Task 3.3: Monitoring System

**File:** `crew/monitoring.py`

**Objective:** Implement comprehensive monitoring and alerting.

**Step-by-Step Implementation:**

1. **Create monitoring system class:**
```python
from typing import Dict, List
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

class MonitoringSystem:
    def __init__(self):
        self.metrics = {}
        self.alerts = []
        self.collectors = {
            'tasks': self._collect_task_metrics,
            'agents': self._collect_agent_metrics,
            'resources': self._collect_resource_metrics,
            'knowledge': self._collect_knowledge_metrics
        }
```

2. **Implement metric collection:**
```python
def collect_metrics(self) -> Dict:
    """Collect all system metrics."""
    metrics = {}
    
    for name, collector in self.collectors.items():
        try:
            metrics[name] = collector()
        except Exception as e:
            logger.error(f"Failed to collect {name} metrics: {e}")
            metrics[name] = {}
    
    metrics['timestamp'] = datetime.now(timezone.utc).isoformat()
    
    return metrics
```

3. **Implement task metrics collection:**
```python
def _collect_task_metrics(self) -> Dict:
    """Collect task-related metrics."""
    from crew.scheduler import get_scheduler
    
    scheduler = get_scheduler()
    tasks = scheduler.get_all_tasks()
    
    metrics = {
        'total': len(tasks),
        'completed': len([t for t in tasks if t.status == 'completed']),
        'failed': len([t for t in tasks if t.status == 'failed']),
        'in_progress': len([t for t in tasks if t.status == 'in_progress']),
        'pending': len([t for t in tasks if t.status == 'pending']),
        'avg_duration': self._calculate_avg_task_duration(tasks)
    }
    
    return metrics
```

4. **Implement health check:**
```python
def health_check(self) -> Dict:
    """Perform comprehensive health check."""
    health = {
        'status': 'healthy',
        'checks': {},
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    checks = {
        'daemon': self._check_daemon_health,
        'database': self._check_database_health,
        'resources': self._check_resource_health,
        'agents': self._check_agents_health
    }
    
    for name, check_func in checks.items():
        try:
            result = check_func()
            health['checks'][name] = result
            if result['status'] != 'ok':
                health['status'] = 'degraded'
        except Exception as e:
            health['checks'][name] = {'status': 'error', 'message': str(e)}
            health['status'] = 'unhealthy'
    
    return health
```

**Testing:**
1. Start monitoring: `crew monitoring start`
2. Check metrics: `crew metrics show`
3. Test health check: `crew health`
4. Verify alerts configured correctly

---

## Phase 4: Scale & Optimization

### Task 4.1: Performance Optimization

**File:** `crew/performance.py`

**Objective:** Optimize system performance and identify bottlenecks.

**Step-by-Step Implementation:**

1. **Create performance optimizer class:**
```python
import cProfile
import pstats
import time
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    def __init__(self):
        self.profiles = {}
        self.optimizations = []
```

2. **Implement profiling:**
```python
def profile_component(self, component_name: str, func, *args, **kwargs):
    """Profile a component and return results."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = func(*args, **kwargs)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    
    self.profiles[component_name] = {
        'stats': stats,
        'total_calls': stats.total_calls,
        'total_time': stats.total_tt,
        'timestamp': time.time()
    }
    
    return result
```

3. **Implement bottleneck identification:**
```python
def identify_bottlenecks(self, component_name: str) -> List[Dict]:
    """Identify performance bottlenecks in a component."""
    if component_name not in self.profiles:
        return []
    
    profile = self.profiles[component_name]
    stats = profile['stats']
    
    bottlenecks = []
    
    for func, (cc, nc, tt, ct, callers) in stats.stats.items():
        if tt > 0.1:
            bottlenecks.append({
                'function': func,
                'total_time': tt,
                'cumulative_time': ct,
                'calls': nc,
                'per_call': tt / nc if nc > 0 else 0
            })
    
    return sorted(bottlenecks, key=lambda x: x['total_time'], reverse=True)[:10]
```

4. **Implement caching:**
```python
def implement_caching(self, func_name: str, cache_size: int = 100):
    """Add caching to a function."""
    from functools import lru_cache
    
    def decorator(f):
        return lru_cache(maxsize=cache_size)(f)
    
    return decorator
```

**Testing:**
1. Profile components: `crew performance profile --component scheduler`
2. Identify bottlenecks: `crew performance bottlenecks`
3. Apply optimizations
4. Measure performance improvements

---

### Task 4.2: Security Hardening

**File:** `crew/security.py`

**Objective:** Implement comprehensive security measures.

**Step-by-Step Implementation:**

1. **Create security manager:**
```python
import hashlib
import secrets
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self):
        self.tokens = {}
        self.permissions = {}
        self.audit_log = []
```

2. **Implement authentication:**
```python
def authenticate(self, token: str) -> bool:
    """Authenticate user with token."""
    if token not in self.tokens:
        logger.warning(f"Authentication failed: invalid token")
        return False
    
    token_data = self.tokens[token]
    
    if token_data['expired']:
        logger.warning(f"Authentication failed: token expired")
        return False
    
    return True
```

3. **Implement authorization:**
```python
def authorize(self, token: str, resource: str, action: str) -> bool:
    """Check if user is authorized for action on resource."""
    if not self.authenticate(token):
        return False
    
    user_role = self.tokens[token]['role']
    
    if user_role not in self.permissions:
        return False
    
    permissions = self.permissions[user_role]
    
    if resource not in permissions:
        return False
    
    return action in permissions[resource]
```

4. **Implement audit logging:**
```python
def log_action(self, token: str, action: str, resource: str, success: bool):
    """Log action to audit log."""
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'token': token[:10] + '...',  # Partial token
        'action': action,
        'resource': resource,
        'success': success
    }
    
    self.audit_log.append(entry)
    logger.info(f"Audit: {action} on {resource} - {'SUCCESS' if success else 'FAILED'}")
```

**Testing:**
1. Create user token: `crew auth create-token --user captain`
2. Test authentication: `crew auth validate-token <token>`
3. Test authorization: `crew auth check-permission <token> knowledge read`
4. Review audit log: `crew security audit-log`

---

### Task 4.3: Deployment Automation

**File:** `docker/docker-compose.production.yml`

**Objective:** Create automated deployment pipeline.

**Step-by-Step Implementation:**

1. **Create production Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync

# Copy application
COPY . /app
WORKDIR /app

# Create data directories
RUN mkdir -p /app/data /app/logs /app/config

# Health check
HEALTHCHECK --interval=30s --timeout=10s \
    CMD crew health || exit 1

# Start daemon
CMD ["crew", "start", "--daemon"]
```

2. **Create production docker-compose:**
```yaml
version: '3.8'

services:
  autoclaw:
    build: .
    restart: always
    volumes:
      - ./data:/app/data
      - ./config:/app/config
      - ./logs:/app/logs
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=info
      - NVIDIA_VISIBLE_DEVICES=0
    ports:
      - "8080:8080"
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "crew", "health"]
      interval: 30s
      timeout: 10s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    restart: always
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    restart: always
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana-dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"

volumes:
  prometheus-data:
  grafana-data:
```

3. **Create deployment script:**
```bash
#!/bin/bash

# deploy.sh

set -e

echo "Deploying AutoClaw to production..."

# Pull latest code
git pull origin main

# Build Docker images
docker-compose -f docker/docker-compose.production.yml build

# Stop existing containers
docker-compose -f docker/docker-compose.production.yml down

# Start new containers
docker-compose -f docker/docker-compose.production.yml up -d

# Wait for health check
echo "Waiting for AutoClaw to be healthy..."
sleep 30

# Run health check
docker-compose -f docker/docker-compose.production.yml exec autoclaw crew health

echo "Deployment complete!"
```

**Testing:**
1. Build Docker image: `docker-compose -f docker/docker-compose.production.yml build`
2. Test locally: `docker-compose -f docker/docker-compose.production.yml up`
3. Verify health check: `docker-compose exec autoclaw crew health`
4. Deploy to production

---

## Summary

This implementation guide provides detailed step-by-step instructions for implementing all features in the AutoClaw roadmap. Each task includes:

1. Clear objectives
2. Step-by-step code implementation
3. Testing procedures
4. Expected outcomes

Follow these instructions in order to successfully implement the complete AutoClaw system from 40% to 100% completion.
