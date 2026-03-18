# AutoClaw Installation Guide

Complete installation instructions for all operating systems.

## Quick Install (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/your-org/autoclaw.git
cd autoclaw

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python3 -m crew health
```

Done! 🎉

---

## System Requirements

| Requirement | Minimum | Recommended |
|------------|---------|------------|
| Python | 3.9 | 3.11+ |
| pip | 21.0 | 23.0+ |
| RAM | 2GB | 8GB |
| Disk | 500MB | 5GB |
| OS | Linux/macOS/Windows | Linux/macOS |

---

## Platform-Specific Installation

### macOS

```bash
# Install Homebrew (if needed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python3

# Install Git (if needed)
brew install git

# Clone and setup
git clone https://github.com/your-org/autoclaw.git
cd autoclaw
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Ubuntu/Debian (Linux)

```bash
# Update packages
sudo apt-get update
sudo apt-get upgrade

# Install dependencies
sudo apt-get install python3 python3-pip python3-venv git

# Clone and setup
git clone https://github.com/your-org/autoclaw.git
cd autoclaw
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### CentOS/RHEL (Linux)

```bash
# Install dependencies
sudo yum install python3 python3-pip git

# Clone and setup
git clone https://github.com/your-org/autoclaw.git
cd autoclaw
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
# Install Python from https://www.python.org/downloads/
# Make sure to check "Add Python to PATH"

# Clone repository
git clone https://github.com/your-org/autoclaw.git
cd autoclaw

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

**If Activation script error**: Run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows (Command Prompt)

```cmd
# Clone repository
git clone https://github.com/your-org/autoclaw.git
cd autoclaw

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

---

## Docker Installation (Optional)

### Using Docker

```bash
# Build Docker image
docker build -t autoclaw .

# Run container
docker run -it -v $(pwd)/data:/app/data autoclaw

# Inside container
crew health
```

### Using Docker Compose

```bash
# Start with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Verification

After installation, verify everything works:

```bash
# Check Python
python3 --version      # Should be 3.9+

# Check pip
pip --version          # Should be 21.0+

# Check dependencies
python3 -c "import crew; print('✅ AutoClaw installed')"

# Start system
crew health            # Should show "✅ System Healthy"
```

If all pass, **you're ready to go!** 🚀

---

## Troubleshooting Installation

### Error: "python3: command not found"

**Cause**: Python not installed
**Solution**: Install Python for your OS (see Platform-Specific above)

### Error: "pip: command not found"

**Cause**: pip not installed or not in PATH
**Solution**:
```bash
python3 -m pip install --upgrade pip
```

### Error: "ModuleNotFoundError: No module named 'crew'"

**Cause**: Virtual environment not activated or dependencies not installed
**Solution**:
```bash
# Check activation
which python  # Should show venv path

# Activate if needed
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall
pip install -r requirements.txt
```

### Error: "Permission denied"

**Cause**: Insufficient permissions
**Solution**:
```bash
# macOS/Linux
chmod +x crew/cli.py

# Then use python to run
python3 -m crew <command>
```

### Error: "No such file or directory: requirements.txt"

**Cause**: Not in the right directory
**Solution**:
```bash
# Make sure you're in autoclaw folder
ls requirements.txt  # Should exist

# If not, go to right folder
cd /path/to/autoclaw
```

### Slow Installation

**Cause**: Downloading from PyPI can be slow
**Solution**: Use a faster mirror
```bash
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

### Running with errors/warnings

Usually OK! Most warnings can be ignored. If you see errors:
```bash
# Check logs
crew logs show

# Get more detail
AUTOCLAW_LOG_LEVEL=DEBUG crew health
```

---

## Advanced Installation

### Install from Requirements (Custom)

```bash
# Create custom requirements.txt
pip freeze > requirements.txt

# Install from custom file
pip install -r requirements.txt
```

### Install Development Mode

```bash
# Install in development mode
pip install -e .

# This allows editing source code directly
```

### Install with Optional Dependencies

```bash
# Full installation with all extras
pip install -r requirements-dev.txt
pip install -r requirements-extras.txt

# Specific extras
pip install crew[web]      # Web interface
pip install crew[postgres] # PostgreSQL support
```

---

## Uninstallation

### Complete Uninstall

```bash
# Remove installation
rm -rf autoclaw/
rm -rf ~/venv/              # If venv in home directory

# Or just deactivate
deactivate  # Leave virtual environment
```

### Clean Up

```bash
# Clear pip cache
pip cache purge

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

---

## Getting Help

If installation fails:

1. **Check prerequisites**: Python 3.9+, git, pip installed
2. **Check platform**: Follow platform-specific instructions above
3. **Check logs**: Run `crew logs show`
4. **Check internet**: Ensure you can download packages
5. **Try again**: Sometimes a retry fixes it
6. **Check docs**: Read [QUICKSTART.md](QUICKSTART.md)
7. **Get support**: Check error details, search issues, ask for help

---

## Next Steps

After successful installation:

1. **Read**: [ONBOARDING.md](ONBOARDING.md) - Beginner guide
2. **Learn**: [QUICKSTART.md](QUICKSTART.md) - Quick start guide
3. **Explore**: [docs/COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md) - Full documentation
4. **Code**: Review `crew/` directory for source code

---

## Installation Tips

1. **Use virtual environment** - Always use venv to avoid conflicts
2. **Use latest pip** - Run `pip install --upgrade pip` first
3. **Check Python version** - Must be 3.9+
4. **Trust the process** - Let pip resolve dependencies
5. **Don't sudo pip** - Virtual environment handles permissions
6. **Use `python3` not `python`** - Avoid system Python
7. **Check internet** - Slow/missing connection causes failures

---

## Common Patterns

### Install and Run Tests

```bash
# Setup
git clone https://github.com/your-org/autoclaw.git
cd autoclaw
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python -m pytest test_comprehensive_debugging.py -v
python -m pytest test_production_hardening.py -v
```

### Fresh Install (Reset Everything)

```bash
# Remove old installation
rm -rf venv crew/knowledge/store.db

# Start fresh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m crew bootstrap
```

### Install Specific Version

```bash
# Install specific release
pip install autoclaw==1.0.0

# Or from source
git clone -b v1.0.0 https://github.com/your-org/autoclaw.git
```

---

## Support

- **Issues**: GitHub Issues
- **Docs**: See `docs/` directory
- **Email**: support@example.com
- **Discord**: Link if available

---

**Status**: Production Ready ✅
**Last Updated**: March 18, 2026
