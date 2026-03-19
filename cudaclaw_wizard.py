#!/usr/bin/env python3
"""
CudaClaw Installation Wizard
=============================
GPU-accelerated multi-agent swarm setup for AutoClaw.

Supports:
  - vLLM local inference (NVIDIA GPU)
  - Cloud API backends (Anthropic, OpenAI, HuggingFace, etc.)
  - Multi-instance swarm configuration
  - Role-based agent assignment (Foreman, Worker, CompletionTester)
  - MCP server registration
  - OpenClaw self-install protocol

Usage (human):
    python3 cudaclaw_wizard.py

Usage (OpenClaw agent - fully automated):
    python3 cudaclaw_wizard.py --agent-mode --preset swarm_4worker \
        --api-key anthropic:$ANTHROPIC_API_KEY \
        --foreman-model claude-sonnet-4-6 \
        --worker-count 4

Machine-readable output (--json):
    python3 cudaclaw_wizard.py --verify-only --json
"""

import os
import sys
import json
import platform
import subprocess
import shutil
import textwrap
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CUDACLAW_VERSION = "1.0.0"
CONFIG_DIR = Path.home() / ".cudaclaw"
INSTANCES_DIR = CONFIG_DIR / "instances"
KEYS_FILE = CONFIG_DIR / "api_keys.json"
MCP_FILE = CONFIG_DIR / "mcp_servers.json"
SWARM_FILE = CONFIG_DIR / "swarm_config.json"

# ─────────────────────────────────────────────
# COLOUR / PRINT HELPERS
# ─────────────────────────────────────────────

RESET = "\033[0m"
BOLD  = "\033[1m"
GREEN = "\033[32m"
YELLOW= "\033[33m"
CYAN  = "\033[36m"
RED   = "\033[31m"
MAGENTA = "\033[35m"

def cprint(msg: str, color: str = RESET) -> None:
    print(f"{color}{msg}{RESET}")

def header(title: str) -> None:
    width = 64
    bar = "═" * width
    print(f"\n{CYAN}{BOLD}╔{bar}╗")
    print(f"║  {title:<{width-2}}║")
    print(f"╚{bar}╝{RESET}\n")

def step(n: int, total: int, msg: str) -> None:
    cprint(f"  [{n}/{total}] {msg}", CYAN)

def ok(msg: str) -> None:
    cprint(f"  ✅  {msg}", GREEN)

def warn(msg: str) -> None:
    cprint(f"  ⚠️   {msg}", YELLOW)

def err(msg: str) -> None:
    cprint(f"  ❌  {msg}", RED)

def ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    try:
        val = input(f"  {prompt}{hint}: ").strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        return default

def ask_yn(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        val = input(f"  {prompt} [{hint}]: ").strip().lower()
        if not val:
            return default
        return val in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return default

# ─────────────────────────────────────────────
# SYSTEM CHECKS
# ─────────────────────────────────────────────

class SystemChecker:
    """Verify prerequisites and GPU availability."""

    @staticmethod
    def python_ok() -> Tuple[bool, str]:
        v = sys.version_info
        if v < (3, 10):
            return False, f"Python {v.major}.{v.minor} found – need 3.10+"
        return True, f"Python {v.major}.{v.minor}.{v.micro}"

    @staticmethod
    def cuda_info() -> Dict:
        """Return CUDA / GPU details."""
        info = {"available": False, "device_count": 0, "devices": [], "driver_version": None}
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,compute_cap",
                 "--format=csv,noheader"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                devices = []
                for line in result.stdout.strip().split("\n"):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 3:
                        devices.append({
                            "name": parts[0],
                            "vram_mb": parts[1],
                            "compute_cap": parts[2]
                        })
                info.update({"available": True, "device_count": len(devices), "devices": devices})
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return info

    @staticmethod
    def vllm_available() -> bool:
        try:
            import importlib.util
            return importlib.util.find_spec("vllm") is not None
        except Exception:
            return False

    @staticmethod
    def disk_free_gb() -> float:
        stat = shutil.disk_usage("/")
        return stat.free / (1024 ** 3)

    @classmethod
    def full_report(cls) -> Dict:
        py_ok, py_msg = cls.python_ok()
        cuda = cls.cuda_info()
        return {
            "python": {"ok": py_ok, "msg": py_msg},
            "cuda": cuda,
            "vllm": cls.vllm_available(),
            "disk_free_gb": round(cls.disk_free_gb(), 2),
            "platform": platform.system(),
            "arch": platform.machine(),
        }


# ─────────────────────────────────────────────
# API KEY MANAGER
# ─────────────────────────────────────────────

KNOWN_PROVIDERS = {
    "anthropic":    {"env": "ANTHROPIC_API_KEY",    "url": "https://console.anthropic.com"},
    "openai":       {"env": "OPENAI_API_KEY",        "url": "https://platform.openai.com"},
    "huggingface":  {"env": "HF_TOKEN",              "url": "https://huggingface.co/settings/tokens"},
    "groq":         {"env": "GROQ_API_KEY",          "url": "https://console.groq.com"},
    "together":     {"env": "TOGETHER_API_KEY",      "url": "https://api.together.xyz"},
    "cloudflare":   {"env": "CLOUDFLARE_API_TOKEN",  "url": "https://dash.cloudflare.com/profile/api-tokens"},
    "replicate":    {"env": "REPLICATE_API_TOKEN",   "url": "https://replicate.com/account/api-tokens"},
    "mistral":      {"env": "MISTRAL_API_KEY",       "url": "https://console.mistral.ai"},
    "cohere":       {"env": "COHERE_API_KEY",        "url": "https://dashboard.cohere.com"},
    "custom":       {"env": "CUSTOM_LLM_API_KEY",    "url": ""},
}

class ApiKeyManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.keys: Dict[str, str] = {}
        if KEYS_FILE.exists():
            try:
                self.keys = json.loads(KEYS_FILE.read_text())
            except Exception:
                self.keys = {}

    def collect_interactive(self) -> None:
        header("Step 2 – API Keys")
        cprint("  Enter API keys for each provider you want to use.", YELLOW)
        cprint("  Press Enter to skip. Keys are stored in ~/.cudaclaw/api_keys.json\n")

        for provider, meta in KNOWN_PROVIDERS.items():
            env_val = os.environ.get(meta["env"], "")
            existing = self.keys.get(provider, env_val)
            masked = f"****{existing[-4:]}" if len(existing) > 4 else existing
            hint = f"  [from env: {masked}]" if existing else ""
            cprint(f"\n  {BOLD}{provider.upper()}{RESET}{CYAN} – {meta['url']}{RESET}{hint}")
            val = ask(f"  {provider} key (Enter to skip)")
            if val:
                self.keys[provider] = val
            elif existing:
                self.keys[provider] = existing

        self.save()

    def load_from_args(self, pairs: List[str]) -> None:
        """Parse provider:key pairs from CLI args."""
        for pair in pairs:
            if ":" in pair:
                provider, key = pair.split(":", 1)
                self.keys[provider.lower()] = key
        self.save()

    def save(self) -> None:
        KEYS_FILE.write_text(json.dumps(self.keys, indent=2))
        KEYS_FILE.chmod(0o600)

    def primary_backend(self) -> Optional[str]:
        """Return best available cloud provider, or None."""
        for p in ("anthropic", "openai", "groq", "together", "mistral"):
            if self.keys.get(p):
                return p
        return None


# ─────────────────────────────────────────────
# MCP SERVER CONFIG
# ─────────────────────────────────────────────

COMMON_MCP_SERVERS = {
    "filesystem":   "Allows reading/writing local files",
    "brave-search": "Web search via Brave API",
    "github":       "GitHub API access",
    "postgres":     "PostgreSQL database access",
    "slack":        "Slack workspace integration",
    "notion":       "Notion workspace integration",
    "custom":       "Custom MCP server endpoint",
}

class McpConfigurator:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.servers: Dict[str, Dict] = {}
        if MCP_FILE.exists():
            try:
                self.servers = json.loads(MCP_FILE.read_text())
            except Exception:
                self.servers = {}

    def collect_interactive(self) -> None:
        header("Step 3 – MCP Servers (optional)")
        cprint("  MCP servers extend agent capabilities. Skip if unsure.\n")
        for name, desc in COMMON_MCP_SERVERS.items():
            cprint(f"  {BOLD}{name}{RESET} – {desc}")
            if ask_yn(f"  Configure {name}?", default=False):
                endpoint = ask("    Endpoint / connection string")
                token    = ask("    Auth token (optional)")
                self.servers[name] = {"endpoint": endpoint, "token": token}
        self.save()

    def save(self) -> None:
        MCP_FILE.write_text(json.dumps(self.servers, indent=2))
        MCP_FILE.chmod(0o600)


# ─────────────────────────────────────────────
# INSTANCE ROLE DEFINITIONS
# ─────────────────────────────────────────────

ROLE_DESCRIPTIONS = {
    "foreman": {
        "desc": "Coordinates the swarm. Detects loops/recursion. Reports progress to OpenClaw.",
        "max_count": 1,
        "default_model": "claude-sonnet-4-6",
        "required": True,
    },
    "completion_tester": {
        "desc": "Validates whether a finite task list is complete. Triggers resource release.",
        "max_count": 1,
        "default_model": "claude-haiku-4-5-20251001",
        "required": False,
    },
    "researcher": {
        "desc": "GPU-accelerated web search and synthesis.",
        "max_count": 8,
        "default_model": "mistralai/Mistral-7B-Instruct-v0.3",
        "required": False,
    },
    "coder": {
        "desc": "Code generation, review, and refactoring on GPU.",
        "max_count": 8,
        "default_model": "deepseek-ai/DeepSeek-Coder-V2-Instruct",
        "required": False,
    },
    "synthesizer": {
        "desc": "Knowledge synthesis and distillation.",
        "max_count": 4,
        "default_model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "required": False,
    },
    "validator": {
        "desc": "Output validation and quality gating.",
        "max_count": 4,
        "default_model": "claude-haiku-4-5-20251001",
        "required": False,
    },
    "worker": {
        "desc": "General-purpose GPU worker (inherits task from foreman).",
        "max_count": 32,
        "default_model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "required": False,
    },
}

PRESET_SWARMS = {
    "minimal": {
        "desc": "1 foreman + 1 worker. For lightweight or testing tasks.",
        "instances": [
            {"role": "foreman", "count": 1, "backend": "cloud"},
            {"role": "worker",  "count": 1, "backend": "vllm"},
        ],
    },
    "swarm_4worker": {
        "desc": "1 foreman + 1 tester + 4 GPU workers. Default GPU swarm.",
        "instances": [
            {"role": "foreman",            "count": 1, "backend": "cloud"},
            {"role": "completion_tester",  "count": 1, "backend": "cloud"},
            {"role": "worker",             "count": 4, "backend": "vllm"},
        ],
    },
    "research_fleet": {
        "desc": "1 foreman + 1 tester + 4 researchers + 2 synthesizers.",
        "instances": [
            {"role": "foreman",           "count": 1, "backend": "cloud"},
            {"role": "completion_tester", "count": 1, "backend": "cloud"},
            {"role": "researcher",        "count": 4, "backend": "vllm"},
            {"role": "synthesizer",       "count": 2, "backend": "vllm"},
        ],
    },
    "code_squad": {
        "desc": "1 foreman + 4 coders + 2 validators + 1 tester.",
        "instances": [
            {"role": "foreman",           "count": 1, "backend": "cloud"},
            {"role": "completion_tester", "count": 1, "backend": "cloud"},
            {"role": "coder",             "count": 4, "backend": "vllm"},
            {"role": "validator",         "count": 2, "backend": "cloud"},
        ],
    },
    "cloud_only": {
        "desc": "All-cloud swarm. No GPU required.",
        "instances": [
            {"role": "foreman",           "count": 1, "backend": "cloud"},
            {"role": "completion_tester", "count": 1, "backend": "cloud"},
            {"role": "worker",            "count": 4, "backend": "cloud"},
        ],
    },
}


class SwarmConfigurator:
    def __init__(self, keys: ApiKeyManager, cuda: Dict):
        self.keys = keys
        self.cuda = cuda
        self.config: Dict = {
            "version": CUDACLAW_VERSION,
            "swarm_name": "cudaclaw-swarm",
            "instances": [],
            "foreman": {},
            "loop_detection": {
                "enabled": True,
                "max_iterations_per_task": 50,
                "stall_timeout_seconds": 300,
                "recursion_depth_limit": 10,
            },
            "progress_reporting": {
                "interval_seconds": 30,
                "openclaw_callback": True,
            },
            "resource_management": {
                "auto_release_on_completion": True,
                "idle_shutdown_seconds": 120,
            },
        }

    def choose_preset_interactive(self) -> str:
        header("Step 4 – Swarm Configuration")
        has_gpu = self.cuda.get("available", False)
        if not has_gpu:
            warn("No NVIDIA GPU detected – GPU roles will use cloud fallback.")
        cprint("\n  Available presets:\n")
        for key, preset in PRESET_SWARMS.items():
            cprint(f"  {BOLD}{key:<20}{RESET} {preset['desc']}")
        default = "swarm_4worker" if has_gpu else "cloud_only"
        chosen = ask("\n  Choose preset", default)
        return chosen if chosen in PRESET_SWARMS else default

    def build_from_preset(self, preset_key: str, foreman_model: Optional[str] = None,
                          worker_count: Optional[int] = None) -> None:
        preset = PRESET_SWARMS[preset_key]
        instances = []
        backend_key = self.keys.primary_backend() or "cloud"

        for spec in preset["instances"]:
            role_meta = ROLE_DESCRIPTIONS[spec["role"]]
            count = spec["count"]
            if spec["role"] == "worker" and worker_count is not None:
                count = worker_count

            for i in range(count):
                suffix = f"-{i+1}" if count > 1 else ""
                inst = {
                    "id": f"{spec['role']}{suffix}",
                    "role": spec["role"],
                    "backend": spec["backend"],
                    "model": foreman_model if spec["role"] == "foreman" and foreman_model
                             else role_meta["default_model"],
                    "api_provider": backend_key if spec["backend"] == "cloud" else None,
                    "vllm_endpoint": "http://localhost:8000/v1" if spec["backend"] == "vllm" else None,
                    "capabilities": _role_capabilities(spec["role"]),
                }
                instances.append(inst)

        self.config["instances"] = instances
        # Extract foreman config
        foreman = next((i for i in instances if i["role"] == "foreman"), None)
        if foreman:
            self.config["foreman"] = {
                "instance_id": foreman["id"],
                "model": foreman["model"],
                "report_to_openclaw": True,
            }

    def build_interactive(self) -> None:
        preset = self.choose_preset_interactive()
        name = ask("  Swarm name", "cudaclaw-swarm")
        self.config["swarm_name"] = name

        cprint("\n  Foreman configuration:", CYAN)
        foreman_model = ask("  Foreman model", ROLE_DESCRIPTIONS["foreman"]["default_model"])
        self.build_from_preset(preset, foreman_model=foreman_model)

        cprint("\n  Loop detection settings:", CYAN)
        max_iter = ask("  Max iterations per task", "50")
        self.config["loop_detection"]["max_iterations_per_task"] = int(max_iter)

        stall = ask("  Stall timeout (seconds)", "300")
        self.config["loop_detection"]["stall_timeout_seconds"] = int(stall)

        self.save()

    def save(self) -> None:
        INSTANCES_DIR.mkdir(parents=True, exist_ok=True)
        SWARM_FILE.write_text(json.dumps(self.config, indent=2))
        ok(f"Swarm config saved → {SWARM_FILE}")


def _role_capabilities(role: str) -> List[str]:
    caps = {
        "foreman":           ["task_distribution", "loop_detection", "progress_reporting",
                              "worker_management", "resource_release"],
        "completion_tester": ["task_validation", "completion_detection", "result_aggregation"],
        "researcher":        ["web_search", "document_retrieval", "knowledge_synthesis"],
        "coder":             ["code_generation", "code_review", "refactoring", "debugging"],
        "synthesizer":       ["knowledge_synthesis", "summarization", "distillation"],
        "validator":         ["output_validation", "quality_gating", "fact_checking"],
        "worker":            ["general_tasks", "parallel_execution", "tool_use"],
    }
    return caps.get(role, ["general_tasks"])


# ─────────────────────────────────────────────
# VLLM SETUP HELPER
# ─────────────────────────────────────────────

class VllmSetup:
    @staticmethod
    def generate_start_script(instances: List[Dict]) -> str:
        """Generate a shell script to launch vLLM servers for each worker."""
        lines = ["#!/bin/bash", "# Auto-generated by cudaclaw_wizard.py", ""]
        port = 8000
        for inst in instances:
            if inst.get("backend") == "vllm":
                lines.append(f"# {inst['id']} ({inst['role']})")
                lines.append(
                    f"python -m vllm.entrypoints.openai.api_server \\\n"
                    f"  --model {inst['model']} \\\n"
                    f"  --port {port} \\\n"
                    f"  --host 0.0.0.0 \\\n"
                    f"  --dtype auto \\\n"
                    f"  --max-model-len 8192 &"
                )
                lines.append(f"echo 'Started {inst[\"id\"]} on port {port}'")
                lines.append("")
                # Update vllm_endpoint for this instance
                inst["vllm_endpoint"] = f"http://localhost:{port}/v1"
                port += 1
        lines.append("echo 'All vLLM servers started. Check with: ps aux | grep vllm'")
        return "\n".join(lines)

    @staticmethod
    def save_script(script: str, path: Path) -> None:
        path.write_text(script)
        path.chmod(0o755)
        ok(f"vLLM launch script → {path}")


# ─────────────────────────────────────────────
# OPENCLAW AGENT MANIFEST
# ─────────────────────────────────────────────

def generate_openclaw_manifest(swarm_config: Dict, keys: ApiKeyManager, sysinfo: Dict) -> Dict:
    """
    Machine-readable manifest that OpenClaw reads to understand how to
    spin up, configure, and interact with this CudaClaw installation.
    """
    return {
        "cudaclaw_version": CUDACLAW_VERSION,
        "manifest_version": "1.0",
        "description": "CudaClaw GPU-accelerated multi-agent swarm for AutoClaw",
        "capabilities": {
            "gpu_acceleration": sysinfo["cuda"]["available"],
            "vllm_inference": sysinfo["vllm"],
            "parallel_workers": len([i for i in swarm_config.get("instances", [])
                                     if i["role"] not in ("foreman", "completion_tester")]),
            "cloud_fallback": True,
            "finite_task_completion": True,
            "loop_detection": True,
            "progress_reporting": True,
        },
        "agent_roles": {
            role: {
                "desc": meta["desc"],
                "max_instances": meta["max_count"],
                "default_model": meta["default_model"],
                "required": meta["required"],
            }
            for role, meta in ROLE_DESCRIPTIONS.items()
        },
        "swarm_presets": {
            k: {"desc": v["desc"], "instance_specs": v["instances"]}
            for k, v in PRESET_SWARMS.items()
        },
        "current_swarm": swarm_config,
        "api_providers": list(keys.keys.keys()),
        "setup_commands": {
            "launch_swarm": "python3 cudaclaw_wizard.py --launch",
            "status":       "python3 cudaclaw_wizard.py --status",
            "add_worker":   "python3 cudaclaw_wizard.py --add-worker --role worker",
            "stop_swarm":   "python3 cudaclaw_wizard.py --stop",
        },
        "openclaw_integration": {
            "spawn_swarm_for_task": {
                "description": "OpenClaw calls this to spin up a CudaClaw swarm for a job",
                "command": "python3 cudaclaw_wizard.py --agent-mode --preset {preset} --task '{task}'",
                "returns": "swarm_id, foreman_endpoint, progress_callback_url",
            },
            "query_progress": {
                "description": "Foreman reports task progress back to OpenClaw",
                "protocol": "JSON over stdout or HTTP callback",
                "format": {
                    "swarm_id": "string",
                    "task_id": "string",
                    "status": "running|complete|stalled|error",
                    "progress_pct": "0-100",
                    "completed_subtasks": "list",
                    "pending_subtasks": "list",
                    "worker_states": "dict",
                    "message": "human-readable update",
                },
            },
        },
        "gpu_info": sysinfo["cuda"],
        "system": {
            "platform": sysinfo["platform"],
            "arch": sysinfo["arch"],
            "disk_free_gb": sysinfo["disk_free_gb"],
        },
    }


# ─────────────────────────────────────────────
# MAIN WIZARD
# ─────────────────────────────────────────────

class CudaClawWizard:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.sysinfo: Dict = {}
        self.keys = ApiKeyManager()
        self.mcp = McpConfigurator()
        self.swarm: Optional[SwarmConfigurator] = None

    def run(self) -> int:
        if self.args.verify_only:
            return self._run_verify()
        if self.args.agent_mode:
            return self._run_agent_mode()
        return self._run_interactive()

    # ── Interactive (human) mode ──────────────────

    def _run_interactive(self) -> int:
        self._banner()
        self._step_syscheck()
        self._step_keys_interactive()
        self._step_mcp_interactive()
        self._step_swarm_interactive()
        self._step_finalize()
        return 0

    def _banner(self) -> None:
        print(f"""
{CYAN}{BOLD}
   ██████╗██╗   ██╗██████╗  █████╗  ██████╗██╗      █████╗ ██╗    ██╗
  ██╔════╝██║   ██║██╔══██╗██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║
  ██║     ██║   ██║██║  ██║███████║██║     ██║     ███████║██║ █╗ ██║
  ██║     ██║   ██║██║  ██║██╔══██║██║     ██║     ██╔══██║██║███╗██║
  ╚██████╗╚██████╔╝██████╔╝██║  ██║╚██████╗███████╗██║  ██║╚███╔███╔╝
   ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
{RESET}
  {BOLD}GPU-Accelerated Multi-Agent Swarm{RESET} · v{CUDACLAW_VERSION}
  Built on AutoClaw · Parallel by nature
""")

    def _step_syscheck(self) -> None:
        header("Step 1 – System Check")
        self.sysinfo = SystemChecker.full_report()

        py = self.sysinfo["python"]
        (ok if py["ok"] else err)(f"Python: {py['msg']}")

        cuda = self.sysinfo["cuda"]
        if cuda["available"]:
            ok(f"CUDA: {cuda['device_count']} GPU(s) detected")
            for d in cuda["devices"]:
                cprint(f"     → {d['name']} | {d['vram_mb']} | compute {d['compute_cap']}", GREEN)
        else:
            warn("CUDA: No GPU detected – cloud-only mode available")

        if self.sysinfo["vllm"]:
            ok("vLLM: installed")
        else:
            warn("vLLM: not installed – run `pip install vllm` for local inference")

        disk = self.sysinfo["disk_free_gb"]
        (ok if disk > 10 else warn)(f"Disk: {disk:.1f} GB free")

    def _step_keys_interactive(self) -> None:
        self.keys.collect_interactive()

    def _step_mcp_interactive(self) -> None:
        self.mcp.collect_interactive()

    def _step_swarm_interactive(self) -> None:
        self.swarm = SwarmConfigurator(self.keys, self.sysinfo["cuda"])
        self.swarm.build_interactive()

    def _step_finalize(self) -> None:
        header("Step 5 – Finalize")
        swarm_cfg = self.swarm.config if self.swarm else {}

        # Write vLLM launch script
        vllm_script = VllmSetup.generate_start_script(swarm_cfg.get("instances", []))
        vllm_path = CONFIG_DIR / "start_vllm.sh"
        VllmSetup.save_script(vllm_script, vllm_path)

        # Write OpenClaw manifest
        manifest = generate_openclaw_manifest(swarm_cfg, self.keys, self.sysinfo)
        manifest_path = CONFIG_DIR / "openclaw_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        ok(f"OpenClaw manifest → {manifest_path}")

        # Write instance configs
        for inst in swarm_cfg.get("instances", []):
            inst_path = INSTANCES_DIR / f"{inst['id']}.json"
            inst_path.write_text(json.dumps(inst, indent=2))

        cprint("\n" + "─" * 64, CYAN)
        cprint(f"""
  {GREEN}{BOLD}CudaClaw installation complete!{RESET}

  Next steps:
  {CYAN}1.{RESET} Start vLLM servers (GPU):   bash {vllm_path}
  {CYAN}2.{RESET} Launch swarm:              python3 cudaclaw_wizard.py --launch
  {CYAN}3.{RESET} Check status:              python3 cudaclaw_wizard.py --status

  OpenClaw can auto-discover this install via:
    {CYAN}python3 cudaclaw_wizard.py --json{RESET}

  Config dir: {CONFIG_DIR}
""")

    # ── Agent / non-interactive mode ──────────────

    def _run_agent_mode(self) -> int:
        self.sysinfo = SystemChecker.full_report()
        if self.args.api_key:
            self.keys.load_from_args(self.args.api_key)

        preset = getattr(self.args, "preset", "swarm_4worker")
        self.swarm = SwarmConfigurator(self.keys, self.sysinfo["cuda"])
        self.swarm.build_from_preset(
            preset,
            foreman_model=getattr(self.args, "foreman_model", None),
            worker_count=getattr(self.args, "worker_count", None),
        )
        self.swarm.save()

        # Generate vLLM script
        vllm_script = VllmSetup.generate_start_script(self.swarm.config["instances"])
        VllmSetup.save_script(vllm_script, CONFIG_DIR / "start_vllm.sh")

        manifest = generate_openclaw_manifest(self.swarm.config, self.keys, self.sysinfo)
        manifest_path = CONFIG_DIR / "openclaw_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        if self.args.json:
            print(json.dumps(manifest, indent=2))
        else:
            ok(f"CudaClaw configured: preset={preset}, "
               f"instances={len(self.swarm.config['instances'])}")
        return 0

    # ── Verify only mode ──────────────────────────

    def _run_verify(self) -> int:
        self.sysinfo = SystemChecker.full_report()
        if self.args.json:
            print(json.dumps(self.sysinfo, indent=2))
            return 0

        py = self.sysinfo["python"]
        (ok if py["ok"] else err)(f"Python: {py['msg']}")
        cuda = self.sysinfo["cuda"]
        if cuda["available"]:
            ok(f"CUDA: {cuda['device_count']} GPU(s)")
        else:
            warn("CUDA: not available")
        (ok if self.sysinfo["vllm"] else warn)("vLLM: " + ("installed" if self.sysinfo["vllm"] else "not installed"))
        return 0 if self.sysinfo["python"]["ok"] else 1


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cudaclaw_wizard",
        description="CudaClaw Installation Wizard – GPU swarm setup for AutoClaw",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python3 cudaclaw_wizard.py                            # Interactive setup
          python3 cudaclaw_wizard.py --verify-only --json       # System check (JSON out)
          python3 cudaclaw_wizard.py --agent-mode \\             # OpenClaw auto-setup
              --preset swarm_4worker \\
              --api-key anthropic:sk-ant-xxx \\
              --foreman-model claude-sonnet-4-6 \\
              --worker-count 4
        """)
    )
    p.add_argument("--verify-only",    action="store_true", help="Only run system checks")
    p.add_argument("--agent-mode",     action="store_true", help="Non-interactive mode for AI agents")
    p.add_argument("--json",           action="store_true", help="Output JSON instead of human-readable text")
    p.add_argument("--preset",         default="swarm_4worker",
                   choices=list(PRESET_SWARMS.keys()),
                   help="Swarm preset to apply in --agent-mode")
    p.add_argument("--api-key",        action="append", metavar="PROVIDER:KEY",
                   help="API key (repeatable). e.g. --api-key anthropic:sk-ant-xxx")
    p.add_argument("--foreman-model",  help="Model ID for the foreman instance")
    p.add_argument("--worker-count",   type=int, help="Override worker count in preset")
    p.add_argument("--launch",         action="store_true", help="Launch swarm after setup")
    p.add_argument("--status",         action="store_true", help="Show current swarm status")
    p.add_argument("--stop",           action="store_true", help="Stop running swarm")
    p.add_argument("--add-worker",     action="store_true", help="Add a new worker instance")
    p.add_argument("--role",           default="worker", help="Role for --add-worker")
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.status:
        if SWARM_FILE.exists():
            cfg = json.loads(SWARM_FILE.read_text())
            print(json.dumps(cfg, indent=2))
        else:
            err("No swarm config found. Run wizard first.")
        return 0

    wizard = CudaClawWizard(args)
    return wizard.run()


if __name__ == "__main__":
    sys.exit(main())
