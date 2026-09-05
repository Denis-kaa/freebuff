"""IdempotentInstaller — идемпотентная установка компонентов (спека §5).

Главный принцип: повторный запуск никогда не ломает систему.
Уже установленные компоненты пропускаются (skip_reason), сетевые операции
повторяются с backoff (_run_with_retry).
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, List, Optional, Tuple

from plugins_04.bootstrap.types import (
    EnvironmentState,
    InstallResult,
    InstallStep,
    RuntimeDefinition,
)

RETRY_SLEEP_SECONDS = 1.0


class IdempotentInstaller:
    """Идемпотентный установщик: skip-if-present + retry для сетевых операций."""

    def __init__(self, workspace: Path, env_state: EnvironmentState) -> None:
        self.workspace = Path(workspace)
        self.env_state = env_state
        self.steps: List[InstallStep] = []

    # ── retry-обёртка над subprocess ────────────────────────

    def _run_with_retry(
        self,
        cmd: List[str],
        max_retries: int = 3,
        step_name: str = "",
        timeout: int = 120,
    ) -> Tuple[bool, str, float, InstallStep]:
        """Запуск команды с retry. Возвращает (success, error, duration_ms, step)."""
        step = InstallStep(name=step_name or " ".join(cmd))
        started = time.time()
        last_error = ""
        attempts = max(1, max_retries)
        for attempt in range(attempts):
            try:
                result: Any = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout,
                )
                if getattr(result, "returncode", 1) == 0:
                    last_error = ""
                    break
                last_error = (getattr(result, "stderr", "") or "").strip()
            except Exception as exc:  # noqa: BLE001 — ошибка сети/окружения = retry
                last_error = str(exc)
            if attempt < attempts - 1:
                time.sleep(RETRY_SLEEP_SECONDS)
        duration_ms = (time.time() - started) * 1000.0
        success = not last_error
        step.status = "passed" if success else "failed"
        if not success:
            step.error = last_error
        step.duration_ms = round(duration_ms, 1)
        self.steps.append(step)
        return success, last_error, duration_ms, step

    # ── pip ─────────────────────────────────────────────────

    def _install_pip(self, package: str) -> InstallResult:
        success, error, duration_ms, _step = self._run_with_retry(
            ["pip", "install", package], step_name=f"pip install {package}",
        )
        return InstallResult(
            installed=success,
            skip_reason="" if success else "",
            error=error,
            duration_ms=duration_ms,
        )

    # ── system packages ─────────────────────────────────────

    def _install_system(self, package: str) -> InstallResult:
        if shutil.which(package) is not None:
            self.steps.append(
                InstallStep(name=f"system {package}", status="skipped")
            )
            return InstallResult(installed=False, skip_reason="already in PATH")

        installer_cmd = self._system_installer_cmd()
        if installer_cmd is None:
            error = f"no system package manager found for '{package}'"
            self.steps.append(InstallStep(name=f"system {package}", status="failed", error=error))
            return InstallResult(installed=False, error=error)

        cmd = installer_cmd + [package]
        try:
            result: Any = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
            )
            ok = getattr(result, "returncode", 1) == 0
            error = "" if ok else (getattr(result, "stderr", "") or "").strip()
        except Exception as exc:  # noqa: BLE001
            ok, error = False, str(exc)
        self.steps.append(
            InstallStep(name=f"system {package}", status="passed" if ok else "failed", error=error)
        )
        return InstallResult(installed=ok, error=error)

    @staticmethod
    def _system_installer_cmd() -> Optional[List[str]]:
        for manager in ("apt-get", "pkg", "apk", "brew"):
            if shutil.which(manager) is not None:
                return [manager, "install"]
        # Fallback: менеджер не детектился (например, под тестовым патчем) —
        # используем дефолт для семейства ОС.
        system = platform.system().lower()
        if system == "darwin":
            return ["brew", "install"]
        if system == "linux":
            return ["apt-get", "install"]
        return None

    # ── git ─────────────────────────────────────────────────

    def _install_git(self, repo_url: str, dest_path: Optional[str] = None) -> InstallResult:
        repo_name = repo_url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[: -len(".git")]
        dest = Path(dest_path) if dest_path else self.workspace / "runtimes" / repo_name

        if dest.exists():
            self.steps.append(InstallStep(name=f"git clone {repo_name}", status="skipped"))
            return InstallResult(installed=False, skip_reason="already cloned")

        started = time.time()
        try:
            result: Any = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(dest)],
                capture_output=True, text=True, timeout=600,
            )
            ok = getattr(result, "returncode", 1) == 0
            error = "" if ok else (getattr(result, "stderr", "") or "").strip()
        except Exception as exc:  # noqa: BLE001
            ok, error = False, str(exc)
        duration_ms = (time.time() - started) * 1000.0
        name = f"git clone {repo_name}"
        self.steps.append(
            InstallStep(name=name, status="passed" if ok else "failed", error=error,
                        duration_ms=round(duration_ms, 1))
        )
        return InstallResult(installed=ok, error=error, duration_ms=duration_ms)

    # ── runtime ─────────────────────────────────────────────

    def install_runtime(self, runtime: RuntimeDefinition) -> InstallResult:
        bin_name = runtime.bin_name or runtime.name
        if shutil.which(bin_name) is not None:
            self.steps.append(InstallStep(name=f"runtime {runtime.name}", status="skipped"))
            return InstallResult(installed=False, skip_reason="already installed")

        if runtime.install_type == "pip":
            return self._install_pip(runtime.name)
        if runtime.install_type == "npm":
            success, error, duration_ms, _step = self._run_with_retry(
                ["npm", "install", "-g", runtime.name],
                step_name=f"npm install {runtime.name}",
            )
            return InstallResult(installed=success, error=error, duration_ms=duration_ms)
        if runtime.install_type == "git":
            if not runtime.source:
                self.steps.append(InstallStep(name=f"runtime {runtime.name}", status="failed",
                                              error="git source not specified"))
                return InstallResult(installed=False, error="git source not specified")
            return self._install_git(runtime.source)
        self.steps.append(InstallStep(name=f"runtime {runtime.name}", status="failed"))
        return InstallResult(installed=False, error=f"unknown install type: {runtime.install_type}")
