# AutoClaw Quick Start Guide

Get AutoClaw up and running in 5 minutes!

## 📋 Prerequisites

- **Python**: 3.9 or higher (`python3 --version`)
- **pip**: Latest version (`pip install --upgrade pip`)
- **Git**: For cloning the repository
- **System**: Linux, macOS, or Windows (WSL recommended)

## ⚡ Quick Start (5 Minutes)

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/your-org/autoclaw.git
cd autoclaw

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize the System
```bash
# Bootstrap the system (creates database, config, etc.)
python3 -m crew bootstrap

# Verify installation
python3 -m crew health
```

### 3. Run a Test
```bash
# Execute a simple query
python3 -m crew knowledge query --tag "test"

# You should see output like:
# ✅ Knowledge store initialized
# Query completed successfully
```

**Done!** ✅ AutoClaw is ready to use.

---

## 🔧 Detailed Installation

### Step 1: Install Python

**macOS/Linux:**
```bash
# Using Homebrew (macOS)
brew install python3

# Using apt (Ubuntu/Debian)
sudo apt-get install python3 python3-pip python3-venv

# Using yum (CentOS/RHEL)
sudo yum install python3 python3-pip
```

**Windows:**
- Download from https://www.python.org/downloads/
- Run installer, check "Add Python to PATH"
- Verify: `python --version`

### Step 2: Clone Repository

```bash
# Clone with HTTPS
git clone https://github.com/your-org/autoclaw.git cd autoclaw

# OR clone with SSH (if configured)
git clone git@github.com:your-org/autoclaw.git
cd autoclaw
```

### Step 3: Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate              # macOS/Linux
# OR
venv\Scripts\activate                 # Windows PowerShell
venv\Scripts\activate.bat              # Windows CMD
```

### Step 4: Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
python3 -c "import crew; print('✅ AutoClaw installed successfully')"
```

### Step 5: Configure Environment (Optional)

Create `.env` file in project root:
```bash
# .env
AUTOCLAW_ENV=development
AUTOCLAW_LOG_LEVEL=INFO
AUTOCLAW_CACHE_ENABLED=true
AUTOCLAW_DB_PATH=./crew/knowledge/store.db
```

Or use system environment variables:
```bash
export AUTOCLAW_ENV=development
export AUTOCLAW_LOG_LEVEL=INFO
```

---

## 🚀 Basic Usage

### Starting the System

**Option 1: Command Line Interface**
```bash
# Start daemon
crew start

# In another terminal, use commands
crew health                    # Check system health
crew knowledge list           # List all knowledge
crew knowledge query --tag "python"  # Search by tag
```

**Option 2: Python Script**
```python
from crew.daemon import AutoClawDaemon

# Initialize daemon
daemon = AutoClawDaemon()
daemon.startup()

# Use components
health = daemon.health_checker.get_status()
print(f"System Health: {health}")

daemon.shutdown()
```

### Common Commands

```bash
# Health and Monitoring
crew health                   # System health check
crew metrics                  # View metrics
crew config show             # Show current config

# Knowledge Management
crew knowledge add --content "My note" --tag "personal"
crew knowledge query --tag "personal"
crew knowledge delete --id <id>

# Agent Management
crew agents list             # List all agents
crew agents status           # Agent status
crew agents restart          # Restart agents

# System Management
crew database reset          # Reset database
crew cache clear             # Clear cache
crew logs show               # Show logs
```

---

## 📚 Next Steps

### 1. Read Documentation
- **[Complete Guide](docs/COMPLETE_GUIDE.md)** - Comprehensive overview
- **[API Reference](docs/API_REFERENCE.md)** - Full API documentation
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production setup
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues

### 2. Run Tests
```bash
# Run all tests
python -m pytest test_comprehensive_debugging.py -v
python -m pytest test_production_hardening.py -v

# Run specific test
python -m pytest test_comprehensive_debugging.py::test_group -v
```

### 3. Explore Examples

**Knowledge Management:**
```python
from crew.knowledge.store import KnowledgeStore

store = KnowledgeStore()

# Add knowledge
entry = store.add({
    "content": "Python is great",
    "tags": ["python", "programming"],
    "type": "note"
})

# Query knowledge
results = store.query(tags=["python"])
print(f"Found {len(results)} entries")
```

**Using Agents:**
```python
from crew.agents.researcher import Researcher

researcher = Researcher()
result = researcher.search("machine learning basics")
print(result)
```

---

## ⚙️ Configuration

### Configuration File (`config.yaml`)

```yaml
# System settings
system:
  name: AutoClaw
  environment: development
  log_level: INFO

# Database settings
database:
  path: ./crew/knowledge/store.db
  backup_enabled: true
  backup_interval: 3600

# Cache settings
cache:
  enabled: true
  ttl: 3600
  max_size: 1000

# Agent settings
agents:
  pool_size: 4
  timeout: 30
  retry_attempts: 3

# Monitoring
monitoring:
  metrics_enabled: true
  health_check_interval: 60
  disk_space_threshold: 100  # MB
```

### Environment Variables

```bash
# Application
AUTOCLAW_ENV=production           # development, staging, production
AUTOCLAW_LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR

# Paths
AUTOCLAW_DB_PATH=./crew/knowledge/store.db
AUTOCLAW_LOG_PATH=./logs
AUTOCLAW_CONFIG_PATH=./config.yaml

# Features
AUTOCLAW_CACHE_ENABLED=true
AUTOCLAW_METRICS_ENABLED=true
AUTOCLAW_AUDIT_ENABLED=true

# Performance
AUTOCLAW_POOL_SIZE=4
AUTOCLAW_CACHE_TTL=3600
```

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'crew'"

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify Python path
python -c "import sys; print(sys.path)"
```

### Issue: Database Locked

**Solution:**
```bash
# Kill any running processes
pkill -f "crew"

# Remove lock file
rm -f crew/knowledge/store.db-journal

# Restart
crew start
```

### Issue: Permission Denied

**Solution:**
```bash
# Give execution permissions
chmod +x crew/cli.py

# Run with python3
python3 -m crew <command>
```

### Issue: Out of Memory

**Solution:**
```bash
# Clear cache
crew cache clear

# Prune old entries
crew knowledge prune --days 30

# Restart system
crew restart
```

### Getting Help

```bash
# Show help for any command
crew --help
crew <command> --help

# Check logs
crew logs show --lines 50

# Enable debug logging
AUTOCLAW_LOG_LEVEL=DEBUG crew <command>
```

---

## 📊 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU Cores | 2 | 4+ |
| RAM | 2GB | 8GB+ |
| Disk Space | 500MB | 5GB+ |
| Python | 3.9 | 3.11+ |
| pip | 21.0 | 23.0+ |

---

## 🔒 Security Setup

### API Key Management

```bash
# Generate API key
crew security generate-key

# Set in environment
export AUTOCLAW_API_KEY="your-key-here"

# Verify setup
crew security check
```

### Enable Audit Logging

```bash
# In config.yaml
security:
  audit_enabled: true
  audit_log_path: ./logs/audit.log
  audit_events:
    - knowledge_add
    - knowledge_delete
    - agent_action
```

---

## 📈 Performance Tips

1. **Enable Caching** - Dramatically improves response time
   ```bash
   AUTOCLAW_CACHE_ENABLED=true crew start
   ```

2. **Adjust Pool Size** - Based on CPU cores
   ```bash
   AUTOCLAW_POOL_SIZE=8 crew start
   ```

3. **Regular Maintenance** - Clean up old entries
   ```bash
   crew knowledge prune --days 30
   crew cache clear
   ```

4. **Monitor Performance** - Check metrics
   ```bash
   crew metrics show
   ```

---

## 🎓 Learning Path

1. **Beginner**: Read this guide + run quick start
2. **Intermediate**: Explore examples + read API reference
3. **Advanced**: Review [COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md) + contribute
4. **Expert**: Review source code + participate in development

---

## 📞 Support

- **Documentation**: See `docs/` directory
- **Issues**: GitHub Issues (if applicable)
- **Community**: Discussions/Forums (if applicable)
- **Email**: support@example.com (if applicable)

---

## ✅ Verification Checklist

After installation, verify everything works:

- [ ] Python 3.9+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed successfully
- [ ] Database initialized (`crew bootstrap`)
- [ ] Health check passed (`crew health`)
- [ ] Can run knowledge query
- [ ] Configuration accessible
- [ ] Logs working correctly
- [ ] All tests pass

**If all checks pass, you're ready to use AutoClaw!** 🎉

---

## 🚀 What's Next?

1. **Explore Features**: Try different commands from "Basic Usage"
2. **Read Docs**: Check out [COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)
3. **Run Examples**: Look in `examples/` directory (if present)
4. **Customize**: Adjust configuration to your needs
5. **Deploy**: See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for production setup

---

**Last Updated**: March 18, 2026
**Version**: 1.0
**Status**: Production Ready ✅
