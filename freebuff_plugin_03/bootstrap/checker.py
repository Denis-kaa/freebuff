"""
Environment Checker — проверяет текущее состояние окружения.

Основание: docs_10/core/BOOTSTRAP_SPECIFICATION.md §3.2
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
}
from typing import Any, Dict, List, Optional, Tuple

from freebuff_plugin_03.bootstrap import EnvironmentState


class EnvironmentChecker:
    """Проверяет текущее состояние окружения.

    Использование:
        checker = EnvironmentChecker()
        state = checker.check()
        print(state.python_version)
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self._workspace = Path(workspace_root or os.getcwd())

    def check(self) -> EnvironmentState:
        """Выполняет полную проверку окружения."""
        state = EnvironmentState(workspace=str(self._workspace))
        self._check_os(state)
        self._check_python(state)
        self._check_node(state)
        self._check_git(state)
        self._check_disk(state)
        self._check_ram(state)
        self._check_pip_packages(state)
        self._check_path(state)
        self._check_env_file(state)
        self._check_workspace_git(state)
        return state

    def check_quick(self) -> EnvironmentState:
        """Быстрая проверка (только основные параметры)."""
        state = EnvironmentState(workspace=str(self._workspace))
        self._check_os(state)
        self._check_python(state)
        self._check_git(state)
        self._check_disk(state)
        return state

    # ── Private checks ──────────────────────────────────────

    def _check_os(self, state: EnvironmentState) -> None:
        """Определяет ОС и наличие Termux."""
        system = platform.system().lower()
        if system == "linux":
            # Проверяем Termux
            if os.environ.get("TERMUX_VERSION"):
                state.os_type = "android"
                state.is_termux = True
                state.has_proot = shutil.which("proot") is not None
            else:
                state.os_type = "linux"
                state.is_termux = False
        elif system == "darwin":
            state.os_type = "mac"
        elif system == "windows":
            state.os_type = "windows"
        else:
            state.os_type = system

        # System packages (через pkg list-installed в Termux)
        if state.is_termux:
            try:
                result = subprocess.run(
                    ["pkg", "list-installed"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    state.system_packages = [
                        line.split("/")[0].strip()
                        for line in result.stdout.split("\n")
                        if line.strip() and "/" in line
                    ]
            except Exception:
                pass

    def _check_python(self, state: EnvironmentState) -> None:
        """Проверяет версию и путь Python."""
        state.python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        state.python_path = sys.executable

    def _check_node(self, state: EnvironmentState) -> None:
        """Проверяет Node.js."""
        node_path = shutil.which("node")
        if node_path:
            try:
                result = subprocess.run(
                    ["node", "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    state.node_version = result.stdout.strip()
            except Exception:
                pass

    def _check_git(self, state: EnvironmentState) -> None:
        """Проверяет Git."""
        git_path = shutil.which("git")
        if git_path:
            state.git_available = True

    def _check_disk(self, state: EnvironmentState) -> None:
        """Проверяет свободное место на диске."""
        try:
            usage = shutil.disk_usage(self._workspace)
            state.disk_free_gb = round(usage.free / (1024 ** 3), 2)
        except Exception:
            state.disk_free_gb = 0.0

    def _check_ram(self, state: EnvironmentState) -> None:
        """Проверяет доступную RAM."""
        try:
            if state.is_termux or sys.platform == "linux":
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            state.ram_total_mb = int(line.split()[1]) // 1024
                        elif line.startswith("MemAvailable:"):
                            state.ram_available_mb = int(line.split()[1]) // 1024
        except Exception:
            pass

        if state.ram_total_mb == 0:
            # Fallback через sysinfo
            try:
                import ctypes
                from ctypes import c_ulong, c_void_p, Structure, sizeof

                class SysInfo(Structure):
                    _fields_ = [
                        ("uptime", c_ulong),
                        ("loads", c_ulong * 3),
                        ("totalram", c_ulong),
                        ("freeram", c_ulong),
                        ("sharedram", c_ulong),
                        ("bufferram", c_ulong),
                        ("totalswap", c_ulong),
                        ("freeswap", c_ulong),
                        ("procs", c_ushort),
                        ("totalhigh", c_ulong),
                        ("freehigh", c_ulong),
                        ("mem_unit", c_uint),
                    ]

                si = SysInfo()
                libc = ctypes.CDLL("libc.so.6")
                libc.sysinfo(ctypes.byref(si))
                state.ram_total_mb = si.totalram * si.mem_unit // (1024 * 1024)
                state.ram_available_mb = si.freeram * si.mem_unit // (1024 * 1024)
            except Exception:
                pass

    def _check_pip_packages(self, state: EnvironmentState) -> None:
        """Проверяет установленные pip пакеты."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=columns"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n")[2:]:  # Пропускаем заголовок
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        state.pip_packages[parts[0].lower()] = parts[1]
        except Exception:
            pass

    def _check_path(self, state: EnvironmentState) -> None:
        """Проверяет PATH."""
        state.path_dirs = os.environ.get("PATH", "").split(":")
        state.env_vars["PATH"] = os.environ.get("PATH", "")
        state.env_vars["HOME"] = os.environ.get("HOME", "")
        if state.is_termux:
            state.env_vars["PREFIX"] = os.environ.get("PREFIX", "")
            state.env_vars["TERMUX_VERSION"] = os.environ.get("TERMUX_VERSION", "")

    def _check_env_file(self, state: EnvironmentState) -> None:
        """Проверяет существование .env файла."""
        env_file = self._workspace / ".env"
        state.has_env_file = env_file.exists()

    def _check_workspace_git(self, state: EnvironmentState) -> None:
        """Проверяет git-статус workspace."""
        git_dir = self._workspace / ".git"
        state.has_git = git_dir.exists()
        if state.has_git:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                    cwd=str(self._workspace),
                )
                if result.returncode == 0:
                    state.git_branch = result.stdout.strip()
            except Exception:
                pass
