# AutoClaw Deployment Guide

Production deployment strategies for AutoClaw across different environments.

## Local Development

Quick setup for development and testing.

### 1. Installation

```bash
# Clone repository
git clone <repo_url>
cd autoclaw

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Create data directory
mkdir -p data

# Copy example config
cp docs/config.example.yaml data/config.yaml

# Edit as needed
nano data/config.yaml
```

### 3. Run the System

```bash
# Terminal 1: Start daemon in foreground to see logs
python -m crew.daemon --foreground --verbose

# Terminal 2: Use CLI commands
python crew/cli.py knowledge list
python crew/cli.py system health
python crew/cli.py status
```

### 4. Run Tests

```bash
# Comprehensive test suite
python test_comprehensive_debugging.py

# Expected output: 9/9 test groups PASSED
```

---

## Docker Deployment

Run AutoClaw in containers for reproducibility and scalability.

### Single Container Setup

**Dockerfile** for single-container deployment:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY crew ./crew
COPY crew/cli.py .
COPY data ./data

# Create data directory
RUN mkdir -p data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from crew.daemon_integration import get_daemon_integration; get_daemon_integration().get_stats()" || exit 1

# Run daemon
CMD ["python", "-m", "crew.daemon", "--foreground"]
```

**Build and run:**

```bash
# Build image
docker build -t autoclaw:latest .

# Run container
docker run -d \
  --name autoclaw \
  -v $(pwd)/data:/app/data \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -p 8000:8000 \
  autoclaw:latest

# Check logs
docker logs -f autoclaw

# Stop container
docker stop autoclaw
```

### Docker Compose (Multi-Service)

**docker-compose.yml** for local multi-service development:

```yaml
version: '3.8'

services:
  autoclaw:
    build: .
    container_name: autoclaw
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LOG_LEVEL=info
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "from crew.daemon_integration import get_daemon_integration; get_daemon_integration().get_stats()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    networks:
      - autoclaw-net

  # Optional: monitoring services
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - autoclaw-net

volumes:
  prometheus-data:

networks:
  autoclaw-net:
    driver: bridge
```

**Run:**

```bash
docker-compose up -d
docker-compose logs -f autoclaw
docker-compose down
```

---

## Kubernetes Deployment

Deploy to Kubernetes for high availability and scalability.

### Namespace and ConfigMap

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: autoclaw

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: autoclaw-config
  namespace: autoclaw
data:
  config.yaml: |
    crew:
      name: "AutoClaw Kubernetes"
      personality: balanced

    knowledge:
      max_entries: 500
      cleanup_days: 30

    triggers:
      enabled: true
      default_poll_minutes: 30

    adaptive:
      enabled: true
```

### Deployment with Persistent Storage

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: autoclaw
  namespace: autoclaw
spec:
  replicas: 3
  selector:
    matchLabels:
      app: autoclaw
  template:
    metadata:
      labels:
        app: autoclaw
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
    spec:
      containers:
      - name: autoclaw
        image: autoclaw:latest
        imagePullPolicy: IfNotPresent

        ports:
        - containerPort: 8000
          name: http

        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: autoclaw-secrets
              key: api-key
        - name: LOG_LEVEL
          value: "info"

        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"

        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2

        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: config
          mountPath: /app/config

      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: autoclaw-data
      - name: config
        configMap:
          name: autoclaw-config

      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - autoclaw
              topologyKey: kubernetes.io/hostname

---
# persistentvolumeclaim.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: autoclaw-data
  namespace: autoclaw
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: fast-ssd

---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: autoclaw
  namespace: autoclaw
spec:
  selector:
    app: autoclaw
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
  type: ClusterIP

---
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: autoclaw-secrets
  namespace: autoclaw
type: Opaque
stringData:
  api-key: ${ANTHROPIC_API_KEY}
```

**Deploy:**

```bash
# Create namespace
kubectl create namespace autoclaw

# Create secrets (replace with actual key)
kubectl create secret generic autoclaw-secrets \
  -n autoclaw \
  --from-literal=api-key=$ANTHROPIC_API_KEY

# Apply manifests
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml

# Check status
kubectl get pods -n autoclaw
kubectl logs -f deployment/autoclaw -n autoclaw

# Scale up
kubectl scale deployment autoclaw -n autoclaw --replicas=5

# Monitor
kubectl top pods -n autoclaw
```

---

## Systemd Service (Linux)

Run AutoClaw as a system service.

### Service File

Create `/etc/systemd/system/autoclaw.service`:

```ini
[Unit]
Description=AutoClaw Autonomous Research Crew
After=network.target

[Service]
Type=simple
User=autoclaw
WorkingDirectory=/opt/autoclaw

Environment="ANTHROPIC_API_KEY=%i"
ExecStart=/opt/autoclaw/venv/bin/python -m crew.daemon --foreground
Restart=on-failure
RestartSec=10

# Resource limits
MemoryLimit=2G
CPUQuota=80%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=autoclaw

[Install]
WantedBy=multi-user.target
```

### Setup

```bash
# Create user
sudo useradd -r -s /bin/bash autoclaw

# Create directory
sudo mkdir -p /opt/autoclaw
sudo chown autoclaw:autoclaw /opt/autoclaw
cd /opt/autoclaw

# Install AutoClaw
git clone <repo> .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy service file
sudo cp systemd/autoclaw.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable autoclaw
sudo systemctl start autoclaw

# Check status
sudo systemctl status autoclaw
sudo journalctl -u autoclaw -f
```

---

## Monitoring and Observability

### Health Checks

AutoClaw provides a health check endpoint:

```bash
# Direct check
python -c "from crew.daemon_integration import get_daemon_integration; print(get_daemon_integration().get_stats())"

# Via CLI
crew-cli system health
```

### Prometheus Metrics

Export system metrics for monitoring:

```python
# In your daemon loop
from crew.daemon_integration import get_daemon_integration
from crew.error_handling import get_error_auditor

di = get_daemon_integration()
auditor = get_error_auditor()

stats = di.get_stats()
errors = auditor.get_stats()

# Export metrics
print(f"knowledge_entries {stats['total_knowledge_entries']}")
print(f"message_queue_depth {stats['message_queue_depth']}")
print(f"total_errors {errors['total_errors']}")
```

### Logging

Configure logging in `data/config.yaml`:

```yaml
daemon:
  log_level: info
  log_file: data/logs/autoclaw.log
  log_format: json  # or text
```

### Alerting Rules

Create Prometheus alert rules:

```yaml
# prometheus-rules.yaml
groups:
  - name: autoclaw
    rules:
    - alert: HighMessageQueueDepth
      expr: message_queue_depth > 1000
      for: 5m
      annotations:
        summary: "Message queue backing up ({{ $value }} pending)"

    - alert: HighErrorRate
      expr: rate(total_errors[5m]) > 0.1
      for: 10m
      annotations:
        summary: "High error rate detected"

    - alert: DaemonDown
      expr: up{job="autoclaw"} == 0
      for: 1m
      annotations:
        summary: "AutoClaw daemon is down"
```

---

## Configuration Management

### Environment Variables

Sensitive configuration via environment variables:

```bash
export ANTHROPIC_API_KEY=sk-...
export LOG_LEVEL=info
export KNOWLEDGE_MAX_ENTRIES=500

python -m crew.daemon
```

### Secrets Management

Using Vault or similar:

```python
import hvac

client = hvac.Client(url='http://127.0.0.1:8200')

# Read secrets
secrets = client.secrets.kv.read_secret_version(path='autoclaw/config')
api_key = secrets['data']['data']['anthropic_api_key']

# Use in configuration
os.environ['ANTHROPIC_API_KEY'] = api_key
```

---

## Backup and Recovery

### Data Backup

```bash
# Backup data directory
tar -czf autoclaw-backup-$(date +%Y%m%d).tar.gz data/

# Backup knowledge database
sqlite3 data/knowledge.db ".backup data/knowledge-backup.db"

# Backup message bus database
sqlite3 data/message_bus.db ".backup data/message_bus-backup.db"
```

### Restore from Backup

```bash
# Restore data directory
tar -xzf autoclaw-backup-20240318.tar.gz

# Restore knowledge database
sqlite3 data/knowledge.db ".restore data/knowledge-backup.db"
```

### Automated Backups

Systemd timer for daily backups:

```ini
# /etc/systemd/system/autoclaw-backup.service
[Unit]
Description=Backup AutoClaw data
After=autoclaw.service

[Service]
Type=oneshot
User=autoclaw
ExecStart=/usr/local/bin/autoclaw-backup.sh

---
# /etc/systemd/system/autoclaw-backup.timer
[Unit]
Description=Daily AutoClaw backup

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

---

## Performance Tuning

### Database Optimization

```python
import sqlite3

# Enable WAL mode for better concurrency
conn = sqlite3.connect('data/knowledge.db')
conn.execute('PRAGMA journal_mode=WAL')

# Optimize queries with indices
conn.execute('CREATE INDEX idx_tags ON knowledge_entries(tags)')
conn.execute('CREATE INDEX idx_status ON knowledge_entries(status)')
```

### Memory Management

```python
# In daemon loop, periodically clean up
from crew.knowledge import get_knowledge_store

store = get_knowledge_store()

# Clean old entries
removed = store.cleanup_old_entries(days=30)
logger.info(f"Cleaned {removed} old entries")

# Compact database
import gc
gc.collect()
```

### Connection Pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Use connection pool for database access
engine = create_engine(
    'sqlite:///data/message_bus.db',
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600
)
```

---

## Scaling Strategies

### Horizontal Scaling

For multi-machine deployment:

1. **Shared Knowledge Store**: Use remote database (PostgreSQL)
2. **Shared Message Bus**: Use centralized message broker (Redis, RabbitMQ)
3. **Distributed Agents**: Agents run independently, share state via bus

### Vertical Scaling

For single-machine increase:

1. Increase `knowledge.max_entries` (default 500)
2. Increase `experiments.time_budget_seconds` (default 300)
3. Increase VM resources (memory, CPU)

---

## Troubleshooting

### Daemon won't start

```bash
# Check logs
journalctl -u autoclaw -n 100

# Check configuration
python -c "import yaml; yaml.safe_load(open('data/config.yaml'))"

# Check permissions
ls -la data/
chown autoclaw:autoclaw data/*
```

### High memory usage

```bash
# Check for leaks
python -m crew.daemon --profile

# Clean old knowledge
crew-cli knowledge stats
python -c "from crew.knowledge import get_knowledge_store; get_knowledge_store().cleanup_old_entries(days=7)"
```

### Message queue backing up

```bash
# Check queue depth
crew-cli system status

# Check for stuck agents
ps aux | grep agent

# Check for dead letters
sqlite3 data/message_bus.db "SELECT COUNT(*) FROM dead_letters"
```

---

## See Also

- [Integration Guide](INTEGRATION_GUIDE.md) - Using components together
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues
- [API Reference](API_REFERENCE.md) - API documentation
