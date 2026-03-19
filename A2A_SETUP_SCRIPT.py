#!/usr/bin/env python3
"""
AutoClaw Agent-to-Agent (A2A) Setup Automation Script

For: Claude Code, AI Agents, Autonomous Systems
Purpose: Fully automated setup of AutoClaw for end users

Usage:
    python3 A2A_SETUP_SCRIPT.py [--verify-only] [--debug]

Agent Integration:
    agents can import this and call: setup_autoclaw(verify_only=False)
"""

import os
import sys
import subprocess
import json
import platform
from pathlib import Path
from typing import Dict, List, Tuple

# ============================================================================
# SYSTEM VERIFICATION
# ============================================================================

class SystemVerifier:
    """Verify system prerequisites before setup."""

    @staticmethod
    def check_python() -> Tuple[bool, str]:
        """Verify Python 3.9+ installed."""
        try:
            version = sys.version_info
            if version.major < 3 or (version.major == 3 and version.minor < 9):
                return False, f"Python {version.major}.{version.minor} found, need 3.9+"
            return True, f"Python {version.major}.{version.minor}.{version.micro} ✓"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def check_pip() -> Tuple[bool, str]:
        """Verify pip available."""
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "--version"],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True, f"pip available ✓"
            return False, "pip not working"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def check_git() -> Tuple[bool, str]:
        """Verify git installed."""
        try:
            result = subprocess.run(["git", "--version"],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True, f"git available ✓"
            return False, "git not found"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def check_disk_space() -> Tuple[bool, str]:
        """Verify sufficient disk space (500MB)."""
        try:
            import shutil
            stat = shutil.disk_usage("/")
            free_gb = stat.free / (1024**3)
            if stat.free > 500 * (1024**2):  # 500MB
                return True, f"{free_gb:.1f}GB available ✓"
            return False, f"Only {free_gb:.1f}GB available, need 0.5GB+"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def verify_all() -> Dict[str, Tuple[bool, str]]:
        """Run all checks."""
        return {
            "Python 3.9+": SystemVerifier.check_python(),
            "pip": SystemVerifier.check_pip(),
            "git": SystemVerifier.check_git(),
            "Disk Space (500MB+)": SystemVerifier.check_disk_space(),
        }


# ============================================================================
# SETUP AUTOMATION
# ============================================================================

class AutoClawSetup:
    """Automated AutoClaw setup for agents."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.repo_root = Path(__file__).parent
        self.venv_path = self.repo_root / "venv"
        self.errors = []
        self.warnings = []

    def log(self, msg: str, level: str = "INFO"):
        """Log message to console."""
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DEBUG": "🔍"
        }.get(level, "•")

        if level == "DEBUG" and not self.debug:
            return

        print(f"{prefix} {msg}")

        if level == "ERROR":
            self.errors.append(msg)
        elif level == "WARNING":
            self.warnings.append(msg)

    def run(self, cmd: List[str], description: str = None) -> Tuple[bool, str]:
        """Run shell command safely."""
        if description:
            self.log(description)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=300)  # 5 min timeout
            if result.returncode == 0:
                self.log(f"Success", "SUCCESS")
                return True, result.stdout
            else:
                error_msg = result.stderr or result.stdout
                self.log(f"Failed: {error_msg[:100]}", "ERROR")
                return False, error_msg
        except subprocess.TimeoutExpired:
            self.log("Command timeout (5min)", "ERROR")
            return False, "Timeout"
        except Exception as e:
            self.log(f"Exception: {str(e)[:100]}", "ERROR")
            return False, str(e)

    def step_1_verify_prerequisites(self) -> bool:
        """Step 1: Verify system prerequisites."""
        self.log("\n" + "="*60)
        self.log("STEP 1: Verifying Prerequisites")
        self.log("="*60)

        checks = SystemVerifier.verify_all()
        all_ok = True

        for check_name, (ok, msg) in checks.items():
            if ok:
                self.log(f"{check_name}: {msg}", "SUCCESS")
            else:
                self.log(f"{check_name}: {msg}", "ERROR")
                all_ok = False

        return all_ok

    def step_2_create_venv(self) -> bool:
        """Step 2: Create virtual environment."""
        self.log("\n" + "="*60)
        self.log("STEP 2: Creating Virtual Environment")
        self.log("="*60)

        if self.venv_path.exists():
            self.log(f"Virtual environment already exists: {self.venv_path}", "WARNING")
            return True

        ok, msg = self.run([sys.executable, "-m", "venv", str(self.venv_path)],
                          f"Creating venv at {self.venv_path}")
        return ok

    def step_3_install_dependencies(self) -> bool:
        """Step 3: Install Python dependencies."""
        self.log("\n" + "="*60)
        self.log("STEP 3: Installing Dependencies")
        self.log("="*60)

        # Get pip executable in venv
        if platform.system() == "Windows":
            pip_exe = self.venv_path / "Scripts" / "pip.exe"
        else:
            pip_exe = self.venv_path / "bin" / "pip"

        # Upgrade pip
        ok, _ = self.run([str(pip_exe), "install", "--upgrade", "pip"],
                        "Upgrading pip")
        if not ok:
            return False

        # Install requirements
        req_file = self.repo_root / "requirements.txt"
        if not req_file.exists():
            self.log(f"requirements.txt not found at {req_file}", "ERROR")
            return False

        ok, msg = self.run([str(pip_exe), "install", "-r", str(req_file)],
                          f"Installing requirements from {req_file}")
        return ok

    def step_4_bootstrap_system(self) -> bool:
        """Step 4: Bootstrap system (create DB, config, etc)."""
        self.log("\n" + "="*60)
        self.log("STEP 4: Bootstrapping System")
        self.log("="*60)

        # Get python executable in venv
        if platform.system() == "Windows":
            python_exe = self.venv_path / "Scripts" / "python.exe"
        else:
            python_exe = self.venv_path / "bin" / "python"

        ok, msg = self.run([str(python_exe), "-m", "crew", "bootstrap"],
                          "Running crew bootstrap")
        return ok

    def step_5_verify_installation(self) -> bool:
        """Step 5: Verify installation with health check."""
        self.log("\n" + "="*60)
        self.log("STEP 5: Verifying Installation")
        self.log("="*60)

        # Get python executable in venv
        if platform.system() == "Windows":
            python_exe = self.venv_path / "Scripts" / "python.exe"
        else:
            python_exe = self.venv_path / "bin" / "python"

        ok, msg = self.run([str(python_exe), "-m", "crew", "health"],
                          "Running health check")

        if ok:
            self.log("Installation verified ✓", "SUCCESS")
            return True
        else:
            self.log("Health check failed - review errors above", "ERROR")
            return False

    def step_6_run_tests(self) -> bool:
        """Step 6: Run test suite (optional but recommended)."""
        self.log("\n" + "="*60)
        self.log("STEP 6: Running Test Suite")
        self.log("="*60)

        # Get python executable in venv
        if platform.system() == "Windows":
            python_exe = self.venv_path / "Scripts" / "python.exe"
        else:
            python_exe = self.venv_path / "bin" / "python"

        # Try to run tests
        test_file = self.repo_root / "test_comprehensive_debugging.py"
        if test_file.exists():
            ok, msg = self.run([str(python_exe), "-m", "pytest", str(test_file),
                              "-v", "--tb=short"],
                              "Running tests (this may take a few minutes)")
            if ok:
                self.log("Tests passed ✓", "SUCCESS")
            else:
                self.log("Some tests failed (check logs for details)", "WARNING")
            return ok
        else:
            self.log("Test file not found, skipping", "WARNING")
            return True

    def run_full_setup(self) -> bool:
        """Run complete setup sequence."""
        steps = [
            ("Prerequisites", self.step_1_verify_prerequisites),
            ("Virtual Environment", self.step_2_create_venv),
            ("Dependencies", self.step_3_install_dependencies),
            ("Bootstrap", self.step_4_bootstrap_system),
            ("Verification", self.step_5_verify_installation),
            ("Tests", self.step_6_run_tests),
        ]

        results = {}
        for step_name, step_func in steps:
            try:
                results[step_name] = step_func()
                if not results[step_name]:
                    self.log(f"\n⚠️ Setup incomplete at step: {step_name}", "ERROR")
                    break
            except Exception as e:
                self.log(f"\n❌ Exception in {step_name}: {str(e)}", "ERROR")
                results[step_name] = False
                break

        return all(results.values())

    def print_summary(self):
        """Print setup summary."""
        self.log("\n" + "="*60)
        self.log("SETUP SUMMARY")
        self.log("="*60)

        if not self.errors:
            self.log("✅ Setup completed successfully!", "SUCCESS")
            self.log("\nNext steps:")
            self.log("1. Start the daemon: crew start")
            self.log("2. Try a command: crew health")
            self.log("3. Add knowledge: crew knowledge add --content 'test' --tag 'demo'")
            self.log("4. Read docs: ONBOARDING.md or QUICKSTART.md")
        else:
            self.log("❌ Setup failed with errors:", "ERROR")
            for error in self.errors:
                self.log(f"  • {error}", "ERROR")

        if self.warnings:
            self.log("\n⚠️ Warnings:", "WARNING")
            for warning in self.warnings:
                self.log(f"  • {warning}", "WARNING")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def setup_autoclaw(verify_only: bool = False, debug: bool = False) -> bool:
    """
    Main setup function - can be called by agents.

    Args:
        verify_only: Only verify, don't install
        debug: Enable debug logging

    Returns:
        True if setup successful, False otherwise
    """
    setup = AutoClawSetup(debug=debug)

    if verify_only:
        # Only verify prerequisites
        all_ok = setup.step_1_verify_prerequisites()
        setup.print_summary()
        return all_ok
    else:
        # Full setup
        success = setup.run_full_setup()
        setup.print_summary()
        return success


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="AutoClaw Agent-to-Agent Setup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 A2A_SETUP_SCRIPT.py              # Full setup
  python3 A2A_SETUP_SCRIPT.py --verify-only  # Just check prerequisites
  python3 A2A_SETUP_SCRIPT.py --debug      # Verbose output
        """
    )

    parser.add_argument("--verify-only", action="store_true",
                       help="Only verify prerequisites, don't install")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")

    args = parser.parse_args()

    success = setup_autoclaw(verify_only=args.verify_only, debug=args.debug)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
