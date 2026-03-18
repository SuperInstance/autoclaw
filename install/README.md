# Installation & Setup

This directory contains everything needed to install AutoResearch on your system.

## 📋 What's in This Directory?

| File | Purpose |
|------|---------|
| `install.py` | Unified Python installer (main entry point) |
| `install.sh` | Linux/macOS bash installer script |
| `install.ps1` | Windows 11 PowerShell installer script |
| `config-wizard.py` | Interactive 6-stage configuration wizard |
| `INSTALLATION_GUIDE.md` | Detailed 400+ line setup guide |

## 🚀 Quick Install

Choose your platform:

### Linux/macOS
```bash
cd autoresearch
bash install/install.sh --interactive
```

### Windows 11
```powershell
cd autoresearch
.\install\install.ps1 -Mode interactive
```

### Docker (All Platforms)
```bash
cd autoresearch
docker-compose -f docker/docker-compose.yml up -d
```

## 🔍 What the Installer Does

1. **Validates Environment**
   - Checks Python 3.10+ installed
   - Verifies Git available
   - Detects GPU (NVIDIA CUDA)
   - Finds package manager (uv > pip > conda)
   - Checks available disk space

2. **Installs Dependencies**
   - Uses fastest available package manager
   - Installs PyTorch, transformers, and dependencies
   - Sets up development tools (if requested)

3. **Prepares Data**
   - Downloads training datasets
   - Trains tokenizer (BPE, 8192 vocab)
   - Creates evaluation splits
   - ~5 minutes on typical system

4. **Configuration Wizard**
   - 6 interactive stages
   - Asks about system, services, research goals
   - Generates YAML configurations
   - Creates agent profiles

5. **Baseline Test**
   - Runs single training experiment
   - Validates setup works
   - Outputs baseline metrics

## 📝 Configuration Wizard Stages

**Stage 1: System Profile**
```
- Research institution/company name
- Your name and email
- GPU settings (all, specific, or CPU)
- Cache directory location
```

**Stage 2: API Services**
```
- OpenAI (GPT-4, GPT-4-turbo)?
- Anthropic Claude?
- Chinese APIs (Deepseek, Qwen)?
- Local models (Ollama, vLLM)?
```

**Stage 3: Research Template**
```
- Technical Wiki (ML/AI knowledge base)
- Explanatory Wiki (detailed concept explanations)
- Game Dev Assets (procedural generation)
- Custom Research (your objectives)
```

**Stage 4: Deployment Targets**
```
- GitHub wiki auto-sync?
- PostgreSQL database?
- MongoDB document storage?
- S3-compatible archival?
```

**Stage 5: Multi-Agent Configuration**
```
- How many agents? (1, 2, 4, or custom)
- Specialization (yes/no)
- Collaboration protocol
```

**Stage 6: Data Retention**
```
- Hot storage duration (days)
- Warm storage duration (days)
- Cold storage duration (days)
- Archive compression settings
```

## 🛠️ Advanced Options

```bash
# Skip data preparation
python install/install.py --skip-data

# Skip baseline experiment
python install/install.py --skip-baseline

# Auto mode (no interactive prompts, use defaults)
python install/install.py --mode auto

# Verbose logging
python install/install.py --verbose

# Custom repo location
python install/install.py --repo-root /path/to/autoclaw
```

## 📋 Configuration Files Generated

After installation, these files are created:

```
config/
├── system.yaml              # Main system configuration
├── agents/
│   ├── default.yaml         # Default single agent
│   ├── hyperparameter-specialist.yaml
│   ├── architecture-explorer.yaml
│   └── synthesis-agent.yaml
└── services/
    ├── openai.yaml          # Pre-commented templates
    ├── anthropic.yaml       # Just uncomment + add key
    ├── chinese-apis.yaml
    └── local-services.yaml
```

**All service templates are pre-commented** - users just:
1. Uncomment the service they want
2. Replace `"your key here"` with actual API key
3. Run!

## 🐛 Troubleshooting

### Python Not Found
```bash
# Make sure Python 3.10+ is installed
python3 --version

# Or reinstall with "Add to PATH" option
```

### Git Not Found
```bash
# Install git first
# macOS: brew install git
# Ubuntu: sudo apt-get install git
# Windows: https://git-scm.com/download/win
```

### Insufficient Disk Space
Need ~250GB for full setup. To use less:
1. Edit `prepare.py`:
   ```python
   MAX_SEQ_LEN = 1024  # Down from 2048
   EVAL_TOKENS = 2**17  # Down from 2**20
   ```
2. Re-run installer

### CUDA/GPU Issues
The installer auto-detects GPUs. If you have issues:
```bash
# Run with CPU-only mode
ar start --agents 1 --device cpu

# Check GPU availability
nvidia-smi

# Reinstall PyTorch with correct CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## 📚 For More Information

- **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** - 400+ line detailed guide
- **[../README.md](../README.md)** - Main repo README
- **[../CONCEPTS.md](../CONCEPTS.md)** - Core concepts explained

## ✅ Verification Checklist

After installation, verify everything works:

```bash
# Check system status
ar verify

# Test with single agent
ar start --agents 1

# Monitor progress
ar status

# Chat with agent
ar chat default

# View metrics
ar metrics

# Expected output: experiments running, val_bpb improving
```

## 🎯 Next Steps

1. **Review configuration**: `cat config/system.yaml`
2. **Add API keys**: Edit `config/services/*.yaml`
3. **Understand agents**: Review `config/agents/*.yaml`
4. **Start research**: `ar start --agents 4`
5. **Read documentation**: `cat CONCEPTS.md`

---

**Need help?** See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for detailed troubleshooting
