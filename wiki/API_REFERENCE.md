# Socket Protocol & API Reference

Daemon socket protocol for advanced integration.

---

## 🔌 Socket Connection

**Path**: `data/crew.sock` (Unix domain socket)

**Protocol**: JSON request/response

---

## 📤 Request Format

```json
{
  "command": "add",
  "args": {
    "title": "Research task",
    "priority": 7
  }
}
```

---

## 📥 Response Format

```json
{
  "status": "ok",
  "data": {
    "task_id": 42,
    "created_at": "2026-03-19T07:00:00Z"
  }
}
```

---

## 📋 Available Commands

| Command | Purpose |
|---------|---------|
| `add` | Create task |
| `board` | Get queue |
| `show` | Get task details |
| `status` | System status |
| `metrics` | Statistics |

---

## ✅ Status Codes

| Code | Meaning |
|------|---------|
| ok | Success |
| error | Failure |
| timeout | Timeout |

---

## 🔗 See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [CLI_COMMANDS.md](CLI_COMMANDS.md) - Available commands
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration

**See also**: [HOME.md](HOME.md)
