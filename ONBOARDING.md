# AutoClaw Onboarding Guide

Welcome to AutoClaw! This guide will help you get started in just a few minutes.

## 🎯 What is AutoClaw?

AutoClaw is an intelligent agent system that helps you:
- **Organize knowledge** - Store, search, and retrieve information
- **Automate tasks** - Run agents that perform work for you
- **Stay productive** - Build custom workflows and automations

## ⏱️ 5-Minute Setup

### 1️⃣ Prerequisites Check

Before starting, make sure you have:
- **Python 3.9+** - Check: `python3 --version`
- **pip** - Check: `python3 -m pip --version`
- **git** - Check: `git --version`

Don't have these? See [Detailed Setup](#detailed-setup) below.

### 2️⃣ Get the Code

```bash
# Copy and paste these lines into your terminal:
git clone https://github.com/your-org/autoclaw.git
cd autoclaw
```

### 3️⃣ Install

```bash
# Create isolated environment
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# Install everything
pip install -r requirements.txt
```

### 4️⃣ Verify

```bash
# This should print a checkmark
python3 -m crew health
```

**Done!** 🎉 You now have AutoClaw installed.

---

## 🚀 Your First Commands

Try these right now:

```bash
# 1. List everything in your knowledge store
crew knowledge list

# 2. Add your first note
crew knowledge add --content "Hello AutoClaw!" --tag "intro"

# 3. Search for it
crew knowledge query --tag "intro"

# 4. Check system status
crew health
```

What should happen:
- ✅ System starts
- ✅ Commands execute successfully
- ✅ You see output/results
- ✅ No errors (warnings are OK)

---

## 📚 Detailed Setup

Don't have Python? Here's how to get it:

### macOS

```bash
# Install Homebrew (if you don't have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python3

# Verify
python3 --version
```

### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt-get update

# Install Python and pip
sudo apt-get install python3 python3-pip python3-venv

# Verify
python3 --version
```

### Windows

1. Go to https://www.python.org/downloads/
2. Download Python 3.11+ for Windows
3. Run installer
4. **Important**: Check "Add Python to PATH" during installation
5. Click "Install Now"

Verify in Command Prompt:
```cmd
python --version
pip --version
```

---

## ❓ Common Questions

### Q: "command not found: python3"
**A:** Python isn't installed. Follow the install steps above for your OS.

### Q: "No such file or directory"
**A:** Make sure you're in the `autoclaw` directory:
```bash
cd autoclaw
ls  # You should see crew/, docs/, QUICKSTART.md, etc.
```

### Q: "ModuleNotFoundError"
**A:** Your virtual environment isn't activated:
```bash
source venv/bin/activate    # macOS/Linux
# OR
venv\Scripts\activate       # Windows
```

### Q: Nothing happens when I type a command
**A:** Try adding `python3 -m` before it:
```bash
python3 -m crew health
```

### Q: How do I stop the system?
**A:** Press `Ctrl+C` in the terminal.

---

## 🧠 Understanding AutoClaw

Think of AutoClaw as a **smart assistant** with three main parts:

### 1. **Knowledge Store** 📚
Your personal information database. Store anything:
```bash
crew knowledge add --content "Buy groceries" --tag "todo"
crew knowledge add --content "Python tutorial link" --tag "learning"
```

### 2. **Agents** 🤖
Workers that do tasks for you. They:
- Search the web
- Answer questions
- Organize information
- Automate workflows

### 3. **Message Bus** 📨
How everything communicates. It ensures:
- Tasks run in order
- Nothing breaks
- Everything stays organized

---

## 🎓 Learning Paths

### Path 1: Explorer (Just Looking Around)
- Read this file
- Try the 5-minute setup
- Run a few commands
- Explore with `crew --help`

**Time**: 15 minutes
**Goal**: Understand what AutoClaw does

### Path 2: User (Daily Productivity)
- Complete Path 1
- Read [QUICKSTART.md](QUICKSTART.md)
- Customize your config
- Build your first workflow

**Time**: 1-2 hours
**Goal**: Use AutoClaw for your work

### Path 3: Developer (Building Extensions)
- Complete Path 2
- Read [COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)
- Review source code
- Create custom agents

**Time**: 4-8 hours
**Goal**: Extend AutoClaw for special needs

---

## 💡 Tips & Tricks

### Tip 1: Use Tags for Organization
Tags help you find things later:
```bash
# Tag everything with categories
crew knowledge add --content "Meeting notes" --tag "work,meetings,2026"
crew knowledge query --tag "meetings"  # Find all meetings
```

### Tip 2: Check Status Before Complaining
99% of issues show up here:
```bash
crew health
```

### Tip 3: View Logs When Confused
Logs show what's happening:
```bash
crew logs show --lines 20
```

### Tip 4: Clear Cache if Slow
Frees up memory:
```bash
crew cache clear
```

### Tip 5: Read the Help
Every command has help:
```bash
crew health --help
crew knowledge --help
crew knowledge add --help
```

---

## 🐛 When Things Go Wrong

### Step 1: Take a breath 😌
Problems are fixable!

### Step 2: Check these things

```bash
# Is Python installed?
python3 --version

# Are we in the right folder?
ls crew/  # Should show files like agents/, knowledge/, etc.

# Is the environment activated?
which python  # Should show venv path

# Is the system healthy?
crew health

# What does the log say?
crew logs show --lines 50
```

### Step 3: Try fixing common issues

```bash
# Restart system
crew restart

# Clear cache
crew cache clear

# Reset database
crew database reset  # ⚠️ This deletes everything in knowledge store!

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Step 4: Get help

- Check [QUICKSTART.md](QUICKSTART.md) for detailed info
- Read [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- Check logs with `crew logs show`
- Ask for help (support contact if available)

---

## 🎯 Your First Workflow

Try building a simple workflow:

```bash
# 1. Add some knowledge
crew knowledge add --content "Learn Python basics" --tag "learning,todo"
crew knowledge add --content "Check weather" --tag "daily,todo"
crew knowledge add --content "Call mom" --tag "personal,todo"

# 2. See what you added
crew knowledge list

# 3. Find all todos
crew knowledge query --tag "todo"

# 4. Organize by category
crew knowledge query --tag "learning"
crew knowledge query --tag "daily"
crew knowledge query --tag "personal"

# 5. Check system
crew health
```

**Congratulations!** You just created your first AutoClaw workflow! 🎉

---

## 📖 Next Steps

1. **Quick Reference**: Read [QUICKSTART.md](QUICKSTART.md)
2. **Deep Dive**: Read [docs/COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)
3. **API Details**: Read [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
4. **Production**: Read [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## ✨ Features Awaiting You

AutoClaw includes:
- ✅ **30+ CLI commands** - Control everything from terminal
- ✅ **Python API** - Integrate into your code
- ✅ **Web interface** (optional) - GUI access
- ✅ **Plugins** - Extend functionality
- ✅ **Agents** - Automate work
- ✅ **Scheduling** - Run tasks on schedule
- ✅ **Monitoring** - Watch what's happening
- ✅ **Security** - API keys, audit logs, rate limiting

---

## 🎊 You're Ready!

You now know:
- ✅ What AutoClaw is
- ✅ How to install it
- ✅ How to use basic commands
- ✅ Where to go for help

**Go build something amazing!** 🚀

---

## Quick Reference Card

```
╔════════════════════════════════════════════════╗
║         AUTOCLAW QUICK COMMANDS                ║
╠════════════════════════════════════════════════╣
║ crew health              Show system status    ║
║ crew knowledge list      List all entries      ║
║ crew knowledge add       Create new entry      ║
║ crew knowledge query     Search entries        ║
║ crew start               Start daemon          ║
║ crew stop                Stop daemon           ║
║ crew logs show           View logs             ║
║ crew --help              Show all commands     ║
║ crew <cmd> --help        Show command help     ║
╚════════════════════════════════════════════════╝

Need help?
→ crew --help
→ crew logs show
→ Check QUICKSTART.md
```

---

**Welcome aboard!** 🛸 Happy coding!

**Last Updated**: March 18, 2026
**Version**: 1.0
**Status**: Production Ready ✅
