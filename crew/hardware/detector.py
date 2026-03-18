"""Hardware detection and profile selection.

Detects available hardware at startup and selects the appropriate profile.
Profile determines: agent count, model size, inference backend, CF strategy.

Detection order:
  1. Check for Jetson (embedded ARM device)
  2. Check CUDA + VRAM
  3. Check multi-GPU
  4. Check RAM and CPU
  5. Select profile

Result is cached in data/crew/hardware.yaml.
Override with: hardware.force_profile in config.yaml
"""

import os
import logging
import platform
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

logger = logging.getLogger(__name__)

HARDWARE_CACHE = Path("data/crew/hardware.yaml")


# ============================================================================
# Profile Specifications
# ============================================================================

PROFILES: Dict[str, Dict[str, Any]] = {
    "nano": {
        "display_name": "Jetson Nano 8GB",
        "cuda": True,
        "unified_memory": True,
        "inference_backend": "llama.cpp",
        "quantization": "Q4_K_M",
        "max_model_params": "3B",
        "max_agents": 2,
        "cf_strategy": "heavy",
        "hot_cache_entries": 200,
        "warm_db_mb": 256,
    },
    "jetson_orin": {
        "display_name": "Jetson Orin 32/64GB",
        "cuda": True,
        "unified_memory": True,
        "inference_backend": "llama.cpp",
        "quantization": "Q5_K_M",
        "max_model_params": "13B",
        "max_agents": 4,
        "cf_strategy": "balanced",
        "hot_cache_entries": 500,
        "warm_db_mb": 1024,
    },
    "laptop_gpu": {
        "display_name": "Laptop GPU (RTX 4050/4060)",
        "cuda": True,
        "unified_memory": False,
        "inference_backend": "llama.cpp",
        "quantization": "Q5_K_M",
        "max_model_params": "13B",
        "max_agents": 4,
        "cf_strategy": "balanced",
        "hot_cache_entries": 1000,
        "warm_db_mb": 2048,
    },
    "workstation": {
        "display_name": "Workstation GPU (RTX 4080/4090)",
        "cuda": True,
        "unified_memory": False,
        "inference_backend": "vllm",
        "quantization": "fp16",
        "max_model_params": "70B",
        "max_agents": 8,
        "cf_strategy": "light",
        "hot_cache_entries": 5000,
        "warm_db_mb": 8192,
    },
    "multi_gpu": {
        "display_name": "Multi-GPU Workstation",
        "cuda": True,
        "unified_memory": False,
        "inference_backend": "vllm",
        "quantization": "fp16",
        "max_model_params": "405B",
        "max_agents": 16,
        "cf_strategy": "minimal",
        "hot_cache_entries": 20000,
        "warm_db_mb": 32768,
    },
    "cloud": {
        "display_name": "Cloud / API-only",
        "cuda": False,
        "unified_memory": False,
        "inference_backend": "api",
        "quantization": None,
        "max_model_params": None,
        "max_agents": 32,
        "cf_strategy": "heavy",
        "hot_cache_entries": 10000,
        "warm_db_mb": 16384,
    },
    "cpu_only": {
        "display_name": "CPU Only",
        "cuda": False,
        "unified_memory": False,
        "inference_backend": "llama.cpp",
        "quantization": "Q4_K_M",
        "max_model_params": "3B",
        "max_agents": 2,
        "cf_strategy": "heavy",
        "hot_cache_entries": 200,
        "warm_db_mb": 512,
    },
}


class HardwareDetector:
    """Detects hardware and selects runtime profile.

    Usage:
        detector = HardwareDetector(config)
        profile_name, profile_info = detector.detect()

        # Then use profile_info to configure agents, backends, etc.
        max_agents = profile_info["max_agents"]
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize detector.

        Args:
            config: Hardware config section (may contain force_profile)
        """
        self.config = config or {}

    def detect(self, force: bool = False) -> tuple[str, Dict[str, Any]]:
        """Detect hardware and return (profile_name, profile_info).

        Results are cached. Set force=True to re-detect.

        Args:
            force: Ignore cache and re-detect

        Returns: (profile_name, profile_dict)
        """
        # Check for forced profile override
        forced = self.config.get("force_profile")
        if forced and forced in PROFILES:
            logger.info(f"Using forced hardware profile: {forced}")
            info = {**PROFILES[forced], "forced": True}
            return forced, info

        # Check cache
        if not force and HARDWARE_CACHE.exists():
            try:
                cached = yaml.safe_load(HARDWARE_CACHE.read_text())
                if cached and "profile" in cached:
                    logger.info(f"Using cached hardware profile: {cached['profile']}")
                    profile_name = cached["profile"]
                    return profile_name, {**PROFILES.get(profile_name, {}), **cached}
            except Exception:
                pass

        # Run detection
        hw_info = self._gather_hardware_info()
        profile_name = self._select_profile(hw_info)
        result = {**PROFILES[profile_name], **hw_info}

        # Cache result
        self._save_cache(profile_name, result)

        logger.info(
            f"Detected hardware profile: {profile_name} "
            f"({PROFILES[profile_name]['display_name']})"
        )

        return profile_name, result

    def _gather_hardware_info(self) -> Dict[str, Any]:
        """Gather all hardware information."""
        info: Dict[str, Any] = {
            "platform": platform.machine(),
            "cpu_cores": os.cpu_count() or 1,
            "architecture": platform.machine(),
        }

        # Check Jetson
        info["is_jetson"] = self._check_jetson()
        info["jetson_model"] = self._get_jetson_model() if info["is_jetson"] else None

        # Check CUDA
        cuda_info = self._check_cuda()
        info.update(cuda_info)

        # Check RAM
        info["ram_gb"] = self._get_ram_gb()

        return info

    def _check_jetson(self) -> bool:
        """Check if running on Jetson hardware."""
        # Check device tree
        device_tree = Path("/proc/device-tree/model")
        if device_tree.exists():
            try:
                model = device_tree.read_bytes().decode(errors="ignore").lower()
                if "jetson" in model or "tegra" in model:
                    return True
            except Exception:
                pass

        # Check NVIDIA Tegra release
        tegra_release = Path("/etc/nv_tegra_release")
        if tegra_release.exists():
            return True

        # Check for ARM + NVIDIA combination
        if platform.machine().startswith("aarch64"):
            # Could be Jetson or Raspberry Pi
            # Check for CUDA on ARM
            if Path("/usr/local/cuda").exists():
                return True

        return False

    def _get_jetson_model(self) -> Optional[str]:
        """Get Jetson model name if on Jetson."""
        device_tree = Path("/proc/device-tree/model")
        if device_tree.exists():
            try:
                return device_tree.read_bytes().decode(errors="ignore").strip("\x00")
            except Exception:
                pass
        return "Unknown Jetson"

    def _check_cuda(self) -> Dict[str, Any]:
        """Check CUDA availability and GPU info."""
        info = {
            "cuda_available": False,
            "vram_gb": 0.0,
            "gpu_count": 0,
            "gpu_names": [],
        }

        try:
            import torch
            if torch.cuda.is_available():
                info["cuda_available"] = True
                info["gpu_count"] = torch.cuda.device_count()
                info["gpu_names"] = []

                total_vram = 0.0
                for i in range(info["gpu_count"]):
                    props = torch.cuda.get_device_properties(i)
                    vram = props.total_memory / (1024**3)
                    total_vram += vram
                    info["gpu_names"].append(props.name)

                # Report per-GPU VRAM (first GPU or average)
                info["vram_gb"] = total_vram / info["gpu_count"] if info["gpu_count"] > 0 else 0.0
                info["total_vram_gb"] = total_vram

        except ImportError:
            # torch not available — try subprocess
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    info["cuda_available"] = True
                    info["gpu_count"] = len(lines)
                    vroms = []
                    for line in lines:
                        parts = line.split(",")
                        if len(parts) >= 2:
                            try:
                                mb = float(parts[0].strip())
                                vroms.append(mb / 1024)
                                info["gpu_names"].append(parts[1].strip())
                            except ValueError:
                                pass
                    if vroms:
                        info["vram_gb"] = sum(vroms) / len(vroms)
                        info["total_vram_gb"] = sum(vroms)
            except Exception:
                pass

        return info

    def _get_ram_gb(self) -> float:
        """Get total system RAM in GB."""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except ImportError:
            # Read from /proc/meminfo
            try:
                meminfo = Path("/proc/meminfo").read_text()
                for line in meminfo.split("\n"):
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb / (1024**2)
            except Exception:
                pass
        return 8.0  # Assume 8GB if can't detect

    def _select_profile(self, hw: Dict[str, Any]) -> str:
        """Select profile based on hardware info."""
        is_jetson = hw.get("is_jetson", False)
        cuda = hw.get("cuda_available", False)
        vram = hw.get("vram_gb", 0.0)
        gpu_count = hw.get("gpu_count", 0)
        jetson_model = (hw.get("jetson_model") or "").lower()

        # Jetson detection
        if is_jetson:
            if "orin" in jetson_model and vram >= 16:
                return "jetson_orin"
            return "nano"

        # Multi-GPU (regardless of per-GPU VRAM)
        if gpu_count >= 2:
            return "multi_gpu"

        # Single GPU tiers
        if cuda:
            if vram >= 48:
                return "workstation"  # High-end single GPU
            elif vram >= 12:
                return "workstation"
            elif vram >= 4:
                return "laptop_gpu"
            else:
                # GPU detected but too small
                return "cpu_only"

        # No GPU
        # Check if we're likely in cloud (no display, many cores)
        cpu_count = hw.get("cpu_cores", 1)
        if cpu_count >= 16 and not Path("/proc/device-tree").exists():
            return "cloud"

        return "cpu_only"

    def _save_cache(self, profile_name: str, info: Dict[str, Any]):
        """Save detection results to cache."""
        HARDWARE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "profile": profile_name,
            "detected_at": __import__("datetime").datetime.now().isoformat(),
            **{
                k: v for k, v in info.items()
                if k in [
                    "is_jetson", "jetson_model", "cuda_available",
                    "vram_gb", "gpu_count", "gpu_names",
                    "ram_gb", "cpu_cores", "architecture",
                ]
            },
        }
        try:
            HARDWARE_CACHE.write_text(yaml.dump(cache_data, default_flow_style=False))
        except Exception as e:
            logger.debug(f"Could not save hardware cache: {e}")


def detect_hardware(config: Optional[Dict[str, Any]] = None) -> tuple[str, Dict[str, Any]]:
    """Convenience function to detect hardware.

    Args:
        config: Hardware config section (optional)

    Returns: (profile_name, profile_info)
    """
    detector = HardwareDetector(config)
    return detector.detect()
