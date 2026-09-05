"""Environment Checker — проверка окружения (спека §2.1, жизненный цикл §2.3 шаг 1)."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from plugins_04.bootstrap.types import EnvironmentState


def _detect_node_version() -> str:
    """Версия Node.js (опциональный компонент, >= 18 по спеке)."""
    if shutil.which("node") is None:
        return ""
    try:
        r = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=10,
        )
        if getattr(r, "returncode", 1) == 0:
            raw = str(getattr(r, "stdout", "") or "").strip()
            if re.match(r"^v?\d+", raw):
                return raw
    except Exception:
        pass
    return ""


def _read_mem_info() -> "tuple[int, int]":
    """(total_mb, available_mb) из /proc/meminfo; (0, 0) если недоступно."""
    try:
        info: dict = {}
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    value = parts[1].strip().split()[0]
                    info[parts[0].strip()] = int(value) // 1024  # kB → MB
        return info.get("MemTotal", 0), info.get("MemAvailable", 0)
    except Exception:
        return 0, 0


class EnvironmentChecker:
    """Проверяет окружение: OS/Termux/Python/Node/Git/Disk/RAM."""

    def __init__(self, workspace_path: str = ".") -> None:
        self.workspace_path = workspace_path

    # ── быстрый чек (без обращения к workspace) ────────────

    def check_quick(self) -> EnvironmentState:
        state = EnvironmentState()

        # OS detection
        system = (platform.system() or "").lower()
        is_termux = os.environ.get("TERMUX_VERSION") is not None
        if is_termux:
            state.os_type = "android"
            state.is_termux = True
        elif system == "darwin":
            state.os_type = "mac"
        elif system == "linux":
            state.os_type = "linux"
        elif system == "windows":
            state.os_type = "windows"

        # Python / Node
        state.python_version = platform.python_version()
        state.node_version = _detect_node_version()

        # Git в PATH
        state.git_available = shutil.which("git") is not None

        # Disk
        state.disk_free_gb = self._disk_free_gb()

        # RAM
        total, available = _read_mem_info()
        state.ram_total_mb = total
        state.ram_available_mb = available

        # PATH (guard: под глобальным патчем environ.get может вернуть None)
        path_env = os.environ.get("PATH") or ""
        state.path_dirs = [p for p in path_env.split(os.pathsep) if p]

        state.workspace = str(self.workspace_path)
        return state

    # ── полный чек (+ workspace) ───────────────────────────

    def check(self) -> EnvironmentState:
        state = self.check_quick()
        ws = Path(self.workspace_path)
        state.has_git = (ws / ".git").exists()
        state.has_env_file = (ws / ".env").exists()
        return state

    def _disk_free_gb(self) -> float:
        target = Path(self.workspace_path)
        try:
            if not target.exists():
                target = Path.cwd()
            usage = shutil.disk_usage(str(target))
            return round(usage.free / (1024 ** 3), 2)
        except Exception:
            return 0.0
