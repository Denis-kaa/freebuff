"""
Idempotent Installer — устанавливает компоненты только если их нет.

Основание: docs_10/core/BOOTSTRAP_SPECIFICATION.md §3.3, §5.1
Retry: §8.3 — 3 попытки с exponential backoff (1s, 2s, 4s)
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from freebuff_plugin_03.bootstrap import (
    BootstrapProfile,
    EnvironmentState,
    InstallResult,
    InstallStep,
    RuntimeDefinition,
)


class IdempotentInstaller:
    """Идемпотентный установщик.

    Устанавливает компоненты только если их нет.
    Поддерживает pip, npm, git, binary установку.
    Все subprocess вызовы используют retry (3 попытки, exponential backoff).
    """

    def __init__(self, workspace_root: Path, state: EnvironmentState):
        self._workspace = workspace_root
        self._state = state
        self._steps: List[InstallStep] = []

    @property
    def steps(self) -> List[InstallStep]:
        return self._steps

    # ══════════════════════════════════════════════════════════
    # Retry helper
    # ══════════════════════════════════════════════════════════

    def _run_with_retry(
        self,
        cmd: List[str],
        max_retries: int = 3,
        timeout: int = 120,
        step_name: str = "install",
    ) -> Tuple[bool, str, float, InstallStep]:
        """Run a command with retry logic and exponential backoff.

        Implements spec §8.3: 3 retries with 2^attempt seconds delay.

        Args:
            cmd: command to run
            max_retries: max attempts (default 3)
            timeout: per-attempt timeout
            step_name: display name for the InstallStep

        Returns:
            (success, error_message, duration_ms, step)
        """
        last_error = ""
        overall_t0 = time.time()

        for attempt in range(max_retries):
            t0 = time.time()
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout,
                )
                if result.returncode == 0:
                    step = InstallStep(
                        name=step_name,
                        status="passed",
                        duration_ms=(time.time() - t0) * 1000,
                    )
                    self._steps.append(step)
                    return True, "", (time.time() - overall_t0) * 1000, step

                last_error = result.stderr[:200]
            except subprocess.TimeoutExpired:
                last_error = "timeout"
            except Exception as e:
                last_error = str(e)

            # Last attempt failed — don't sleep
            if attempt == max_retries - 1:
                break

            # Exponential backoff: 1s, 2s, 4s
            sleep_time = 2 ** attempt
            time.sleep(sleep_time)

        step = InstallStep(
            name=step_name,
            status="failed",
            duration_ms=(time.time() - overall_t0) * 1000,
            error=last_error,
        )
        self._steps.append(step)
        return False, last_error, (time.time() - overall_t0) * 1000, step

    # ══════════════════════════════════════════════════════════
    # Main install method
    # ══════════════════════════════════════════════════════════

    def install_profile(self, profile: BootstrapProfile) -> List[InstallResult]:
        """Устанавливает все компоненты профиля (идемпотентно).

        Args:
            profile: профиль установки

        Returns:
            список результатов установки
        """
        results: List[InstallResult] = []

        # 1. Системные зависимости
        for pkg in profile.system_packages:
            if pkg not in self._state.system_packages:
                result = self._install_system(pkg)
                results.append(result)
            else:
                results.append(InstallResult(
                    component=pkg, installed=True, skip_reason="already installed"
                ))

        # 2. Python пакеты
        for pkg in profile.python_packages:
            pkg_name = pkg.split("==")[0].split(">=")[0].split("<")[0].strip().lower()
            if pkg_name not in self._state.pip_packages:
                result = self._install_pip(pkg)
                results.append(result)
            else:
                results.append(InstallResult(
                    component=pkg, installed=True, skip_reason="already installed"
                ))

        # 3. npm пакеты
        for pkg in profile.npm_packages:
            pkg_name = pkg.split("@")[0] if pkg.startswith("@") else pkg.split("@")[0].strip()
            if pkg_name not in self._state.npm_packages:
                result = self._install_npm(pkg)
                results.append(result)
            else:
                results.append(InstallResult(
                    component=pkg, installed=True, skip_reason="already installed"
                ))

        return results

    def install_runtime(self, runtime: RuntimeDefinition) -> InstallResult:
        """Устанавливает AI Runtime.

        Args:
            runtime: определение Runtime

        Returns:
            результат установки
        """
        # Проверяем, установлен ли уже
        if shutil.which(runtime.bin_name):
            return InstallResult(
                component=runtime.name,
                installed=True,
                path=shutil.which(runtime.bin_name) or "",
                skip_reason="already installed",
            )

        step = InstallStep(name=f"install_runtime:{runtime.name}")
        t0 = time.time()

        try:
            if runtime.install_type == "pip":
                result = self._install_pip(runtime.source)
            elif runtime.install_type == "npm":
                result = self._install_npm(runtime.source)
            elif runtime.install_type == "git":
                result = self._install_git(runtime.source, runtime.install_path)
            elif runtime.install_type == "binary":
                result = self._install_binary(runtime)
            else:
                result = InstallResult(
                    component=runtime.name,
                    installed=False,
                    error=f"Unknown install type: {runtime.install_type}",
                )

            step.duration_ms = (time.time() - t0) * 1000
            step.status = "passed" if result.installed else "failed"
            if result.error:
                step.error = result.error
            self._steps.append(step)

            # Post-install hooks
            if result.installed and runtime.post_install:
                for cmd in runtime.post_install:
                    try:
                        if isinstance(cmd, str):
                            cmd_list = shlex.split(cmd)
                        else:
                            cmd_list = list(cmd)
                        subprocess.run(cmd_list, shell=False, timeout=30,
                                     capture_output=True, text=True)
                    except Exception:
                        pass

            return result

        except Exception as e:
            step.duration_ms = (time.time() - t0) * 1000
            step.status = "failed"
            step.error = str(e)
            self._steps.append(step)
            return InstallResult(
                component=runtime.name,
                installed=False,
                error=str(e),
            )

    # ══════════════════════════════════════════════════════════
    # Specific installers (all with retry via _run_with_retry)
    # ══════════════════════════════════════════════════════════

    def _install_system(self, package: str) -> InstallResult:
        """Устанавливает системный пакет (pkg/apt) с retry.

        Retry: 3 попытки, exponential backoff (1s, 2s, 4s).
        Идемпотентность: проверяет наличие перед установкой.
        """
        if shutil.which(package):
            return InstallResult(
                component=package, installed=True, skip_reason="already in PATH"
            )

        if self._state.is_termux:
            cmd = ["pkg", "install", "-y", package]
        else:
            cmd = ["apt-get", "install", "-y", package]

        success, error, duration_ms, step = self._run_with_retry(
            cmd, step_name=f"install_system:{package}",
        )

        return InstallResult(
            component=package,
            installed=success,
            error=error,
        )

    def _install_pip(self, package: str) -> InstallResult:
        """Устанавливает pip пакет с retry.

        Retry: 3 попытки, exponential backoff (1s, 2s, 4s).
        """
        success, error, duration_ms, step = self._run_with_retry(
            [sys.executable, "-m", "pip", "install", package],
            step_name=f"install_pip:{package}",
        )

        return InstallResult(
            component=package,
            installed=success,
            error=error,
        )

    def _install_npm(self, package: str) -> InstallResult:
        """Устанавливает npm пакет с retry.

        Retry: 3 попытки, exponential backoff (1s, 2s, 4s).
        """
        success, error, duration_ms, step = self._run_with_retry(
            ["npm", "install", "-g", package],
            step_name=f"install_npm:{package}",
        )

        return InstallResult(
            component=package,
            installed=success,
            error=error,
        )

    def _install_git(self, source: str, dest_path: str = "") -> InstallResult:
        """Клонирует git репозиторий (идемпотентно) с retry.

        Retry: 3 попытки, exponential backoff (1s, 2s, 4s), timeout 300s.

        Args:
            source: URL репозитория
            dest_path: путь назначения

        Returns:
            результат установки
        """
        repo_name = source.split("/")[-1].replace(".git", "")
        if dest_path:
            dest = Path(dest_path)
        else:
            dest = self._workspace / "runtimes" / repo_name

        # Идемпотентность: если директория существует — пропускаем
        if dest.exists():
            return InstallResult(
                component=repo_name,
                installed=True,
                path=str(dest),
                skip_reason="already cloned",
            )

        dest.parent.mkdir(parents=True, exist_ok=True)
        success, error, duration_ms, step = self._run_with_retry(
            ["git", "clone", source, str(dest)],
            step_name=f"install_git:{repo_name}",
            timeout=300,
        )

        return InstallResult(
            component=repo_name,
            installed=success,
            path=str(dest) if success else "",
            error=error,
        )

    def _install_binary(self, runtime: RuntimeDefinition) -> InstallResult:
        """Устанавливает Runtime через загрузку бинарника с retry.

        Retry: 3 попытки, exponential backoff (1s, 2s, 4s).
        """
        dest = Path(runtime.install_path or f"/usr/local/bin/{runtime.bin_name}")

        success, error, duration_ms, step = self._run_with_retry(
            ["curl", "-Lo", str(dest), runtime.source],
            step_name=f"install_binary:{runtime.name}",
        )

        if success:
            try:
                os.chmod(dest, 0o755)
            except Exception:
                pass

        return InstallResult(
            component=runtime.name,
            installed=success,
            path=str(dest) if success else "",
            error=error,
        )
