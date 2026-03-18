# Docker & Containerization

Complete Docker setup for AutoResearch deployment on any platform.

## 📋 What's in This Directory?

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image definition |
| `docker-compose.yml` | Multi-service orchestration |
| `docker-entrypoint.sh` | Container startup script |
| `.env.example` | Environment configuration template |

## 🐳 Quick Start with Docker

### Prerequisites
- Docker Desktop installed (https://www.docker.com/products/docker-desktop)
- ~10-20GB disk space for images
- (Optional) NVIDIA Container Toolkit for GPU support

### Step 1: Setup Environment

```bash
# Copy environment template
cp docker/.env.example docker/.env

# Edit with your API keys
nano docker/.env

# Or use Visual Studio Code
code docker/.env
```

### Step 2: Start All Services

```bash
# Start all services (creates and runs containers)
docker-compose -f docker/docker-compose.yml up -d

# Wait 30-60 seconds for startup
sleep 60

# Check status
docker-compose ps

# View logs
docker-compose logs -f autoresearch
```

### Step 3: Access Services

```bash
# AutoResearch CLI
docker-compose exec autoresearch ar status

# Murmur Wiki
# Open in browser: http://localhost:3004

# Spreadsheet-Moment
# Open in browser: http://localhost:5173

# Monitor logs
docker-compose logs -f autoresearch
```

### Step 4: Stop Services

```bash
# Stop (keeps data)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop, remove containers AND delete all data
docker-compose down -v
```

## 🏗️ Docker Architecture

### Services in docker-compose.yml

```
┌─ autoresearch (main)
│  ├─ Python 3.11 + CUDA 12.1
│  ├─ PyTorch + Dependencies
│  └─ AutoResearch Engine
│
├─ postgres (knowledge storage)
│  └─ PostgreSQL 15
│
├─ redis (caching)
│  └─ Redis 7
│
├─ murmur (semantic wiki)
│  └─ Murmur Knowledge Graph
│
├─ spreadsheet-moment (dashboards)
│  └─ Data Interface
│
├─ ollama (optional local LLMs)
│  └─ Local Model Server
│
└─ prometheus (optional monitoring)
   └─ Metrics Collection
```

### Network: autoresearch-net (bridge)
All services can communicate internally by hostname (e.g., `postgres:5432`)

## 🔧 Dockerfile Overview

Multi-stage build for efficiency:

**Stage 1: base**
- Ubuntu 22.04 + CUDA 12.1
- System dependencies
- Non-root user creation

**Stage 2: builder**
- Install uv (fast Python package manager)
- Install Python dependencies
- (~300MB layer)

**Stage 3: production**
- Copy dependencies from builder
- Copy application code
- Optimized final image (~1.5GB)

**Stage 4: development** (optional)
- Extra development tools
- IPython, Jupyter, debugging
- For development/debugging

## 📝 Configuration: .env File

Key environment variables:

```bash
# AI Services
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
DEEPSEEK_API_KEY=...

# Database
POSTGRES_PASSWORD=secure_password_here!
POSTGRES_USER=autoresearch
DATABASE_URL=postgresql://autoresearch:password@postgres:5432/autoresearch_knowledge

# Redis
REDIS_URL=redis://redis:6379

# Resource Limits
AGENTS_COUNT=4
MAX_GPU_MEMORY_GB=80
MAX_API_TOKENS_PER_MIN=50000

# Integration
MURMUR_ENDPOINT=http://murmur:3004
MURMUR_AUTO_SYNC=true
```

## 🎮 Common Docker Commands

```bash
# View running containers
docker-compose ps

# View logs for all services
docker-compose logs

# View logs for specific service
docker-compose logs autoresearch

# Follow logs (tail -f)
docker-compose logs -f autoresearch

# Stop all services
docker-compose stop

# Start all services
docker-compose start

# Restart all services
docker-compose restart

# Rebuild images (if you modify Dockerfile)
docker-compose build

# Execute command in container
docker-compose exec autoresearch ar status

# Open shell in container
docker-compose exec autoresearch /bin/bash

# Remove everything (containers + volumes)
docker-compose down -v

# View resource usage
docker stats

# View container logs from 10 minutes ago
docker-compose logs --since 10m autoresearch
```

## 💾 Data Persistence

### Volumes

Data is persisted in Docker volumes:

| Volume | Contents | Keep After `down`? |
|--------|----------|-------------------|
| `postgres-data` | Knowledge graph | Yes |
| `redis-data` | Cache | No (ephemeral) |
| `murmur-data` | Wiki data | Yes |
| `ollama-data` | Downloaded models | Yes |
| `prometheus-data` | Metrics history | No |

### Backup Data

```bash
# Backup knowledge graph
docker run --rm -v postgres-data:/data -v $(pwd):/backup \
  postgres:15 pg_dump -U autoresearch autoresearch_knowledge > backup.sql

# Backup results
docker-compose exec autoresearch \
  tar czf /app/results-backup.tar.gz /app/results/
```

## 🚀 Advanced Usage

### GPU Support

**Prerequisites:**
- NVIDIA GPU
- NVIDIA Container Toolkit installed

**Installation:**
```bash
# Ubuntu
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

**Verify:**
```bash
docker run --rm --runtime=nvidia nvidia/cuda:12.1.1-base nvidia-smi
```

**Enable in docker-compose:**
Update `docker-compose.yml`:
```yaml
autoresearch:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

### Using Ollama (Local LLMs)

```bash
# Enable in docker-compose (uncomment ollama service)
docker-compose --profile with-ollama up -d ollama

# Pull models
docker-compose exec ollama ollama pull mistral

# Update config to use Ollama
# Set OLLAMA_BASE_URL=http://ollama:11434/v1 in .env
```

### Enable Monitoring (Prometheus)

```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Access Prometheus
# Open in browser: http://localhost:9090

# View metrics
# Query: container_memory_usage_bytes{name="autoresearch"}
```

### Custom Port Mapping

Edit `docker-compose.yml`:
```yaml
autoresearch:
  ports:
    - "6006:6006"  # TensorBoard
    - "8000:8000"  # Local API
    - "9999:8000"  # Expose API on different port
```

### Scale to Multiple Nodes

```bash
# Use docker swarm or Kubernetes
# See deployment/ directory for examples
```

## 🔍 Troubleshooting

### Container Won't Start

```bash
# Check error logs
docker-compose logs autoresearch

# Common issues:
# - Missing .env file: cp docker/.env.example docker/.env
# - PostgreSQL not ready: wait 30 seconds
# - Out of disk space: docker system prune -a
```

### Out of Disk Space

```bash
# See how much space Docker uses
docker system df

# Remove unused images/containers
docker system prune -a

# Remove unused volumes
docker volume prune
```

### PostgreSQL Connection Failed

```bash
# Check if postgres is running
docker-compose logs postgres

# Verify password in .env matches compose file
# Default: POSTGRES_PASSWORD=secure_password_change_me

# Restart postgres
docker-compose restart postgres
```

### GPU Not Detected

```bash
# Check if NVIDIA Container Toolkit is installed
docker run --rm --runtime=nvidia nvidia/cuda:12.1.1-base nvidia-smi

# If not working:
# 1. Install NVIDIA Container Toolkit
# 2. Restart Docker daemon
# 3. Ensure CUDA_VISIBLE_DEVICES set in .env
```

### Container Crashes on Start

```bash
# Check logs
docker-compose logs autoresearch --tail 50

# Common causes:
# - Insufficient disk space
# - GPU out of memory
# - CUDA version mismatch
# - API key missing or invalid

# Try without GPU:
# Set CUDA_VISIBLE_DEVICES="" in .env
docker-compose restart autoresearch
```

## 📊 Monitoring

### Container Resource Usage

```bash
# Real-time stats
docker stats

# For specific container
docker stats autoresearch

# Output: CPU%, memory usage, network I/O, block I/O
```

### Application Metrics

```bash
# Check agent status
docker-compose exec autoresearch ar status

# View metrics
docker-compose exec autoresearch ar metrics --last 1h

# View logs
docker-compose exec autoresearch ar logs --tail 50
```

### Database Health

```bash
# Connect to postgres
docker-compose exec postgres psql -U autoresearch -d autoresearch_knowledge

# Check tables
\dt

# Query sample data
SELECT * FROM research_findings LIMIT 5;

# Exit
\q
```

## 🔐 Security Considerations

### Change Default Passwords

```bash
# Edit docker/.env
POSTGRES_PASSWORD=your_secure_password_here

# Also update:
DATABASE_URL=postgresql://autoresearch:your_secure_password_here@postgres:5432/...
```

### Limit Network Exposure

```yaml
# In docker-compose.yml, remove public port mappings:
# Instead of:
# ports:
#   - "3004:3004"
#
# Use:
# networks:
#   - autoresearch-net
# (Only accessible from other containers)
```

### Use Secrets (Production)

```bash
# For production, use Docker secrets or .env files
# Never commit passwords to git
# Add to .gitignore:
echo "docker/.env" >> .gitignore
echo ".env" >> .gitignore
```

## 📚 Further Reading

- **Docker Docs:** https://docs.docker.com/
- **Docker Compose:** https://docs.docker.com/compose/
- **NVIDIA Container Toolkit:** https://github.com/NVIDIA/nvidia-docker
- **[../README.md](../README.md)** - Main documentation
- **[../install/INSTALLATION_GUIDE.md](../install/INSTALLATION_GUIDE.md)** - General setup

## ✅ Verification Checklist

After starting Docker:

```bash
# All services running
docker-compose ps

# No crashes in logs
docker-compose logs autoresearch | grep -i error

# Postgres responding
docker-compose exec postgres pg_isready

# Redis responding
docker-compose exec redis redis-cli ping

# AutoResearch CLI works
docker-compose exec autoresearch ar verify

# Expected: ✓ checks pass
```

---

**Ready to deploy?** Start with `docker-compose up -d` 🚀
