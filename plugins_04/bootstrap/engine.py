"""BootstrapEngine — идемпотентное развёртывание AI-среды (спека §2.3).

Жизненный цикл: SYSTEM CHECK → CONFIG LOAD → INSTALL → DIAGNOSE → REPORT.
События EventBus: bootstrap.started / checked / profile_loaded / completed | failed.
"""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import yaml

from plugins_04.bootstrap.checker import EnvironmentChecker
from plugins_04.bootstrap.doctor import RuntimeDoctor
from plugins_04.bootstrap.installer import IdempotentInstaller
from plugins_04.bootstrap.state import BootstrapState
from plugins_04.bootstrap.types import (
    BootstrapEvent,
    BootstrapProfile,
    BootstrapReport,
    EnvironmentState,
    InstallResult,
    InstallStep,
    RuntimeDefinition,
)

# Модульный атрибут: патчится в тестах (fallback-сценарий).
DEFAULT_PROFILES_PATH = Path(__file__).parent / "profiles.yaml"

# Встроенный fallback, если profiles.yaml отсутствует/повреждён.
BUILTIN_MINIMAL_PROFILE = BootstrapProfile(
    name="minimal",
    description="Fallback builtin profile",
    pip_packages=["requests"],
)


def _profile_from_yaml(name: str, raw: Dict[str, Any]) -> BootstrapProfile:
    runtimes_raw = raw.get("runtimes", {}) or {}
    runtimes = {
        rt_name: RuntimeDefinition(
            name=rt_name,
            version=str(cfg.get("version", "latest")),
            install_type=str(cfg.get("install_type", "pip")),
            source=str(cfg.get("source", "")),
            bin_name=str(cfg.get("bin_name", "")),
        )
        for rt_name, cfg in runtimes_raw.items()
    }
    return BootstrapProfile(
        name=name,
        description=str(raw.get("description", "")),
        offline_mode=bool(raw.get("offline_mode", False)),
        pip_packages=list(raw.get("pip_packages", []) or []),
        system_packages=list(raw.get("system_packages", []) or []),
        runtimes=runtimes,
    )


class BootstrapEngine:
    """Менеджер состояния среды (не установщик): check → load → install → diagnose."""

    def __init__(
        self,
        workspace_root: str = ".",
        profile: str = "minimal",
        event_bus: Any = None,
    ) -> None:
        self.workspace = Path(workspace_root)
        self._profile_name = profile
        self.event_bus = event_bus
        self._checker = EnvironmentChecker(str(self.workspace))
        self._state = BootstrapState(self.workspace)
        self._last_report: Optional[BootstrapReport] = None

    # ── EventBus (failures never break bootstrap) ───────────

    def _emit(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        if self.event_bus is None:
            return
        try:
            self.event_bus.publish(BootstrapEvent(type=event_type, data=data or {}))
        except Exception:  # noqa: BLE001 — ошибка шины не ломает bootstrap
            pass

    # ── проверка окружения ──────────────────────────────────

    def check(self) -> EnvironmentState:
        return self._checker.check()

    # ── профили ─────────────────────────────────────────────

    def _load_profile(self) -> BootstrapProfile:
        """Загрузка профиля из profiles.yaml; fallback → builtin minimal."""
        try:
            with open(DEFAULT_PROFILES_PATH, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            profiles = data.get("profiles", {})
            if self._profile_name in profiles:
                return _profile_from_yaml(self._profile_name, profiles[self._profile_name])
        except Exception:
            pass
        return BootstrapProfile(
            name=BUILTIN_MINIMAL_PROFILE.name,
            description=BUILTIN_MINIMAL_PROFILE.description,
            pip_packages=list(BUILTIN_MINIMAL_PROFILE.pip_packages),
        )

    def list_profiles(self) -> List[Dict[str, Any]]:
        try:
            with open(DEFAULT_PROFILES_PATH, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            profiles = data.get("profiles", {})
            return [
                {
                    "name": name,
                    "description": cfg.get("description", ""),
                    "offline_mode": bool(cfg.get("offline_mode", False)),
                    "runtimes": sorted((cfg.get("runtimes", {}) or {}).keys()),
                }
                for name, cfg in profiles.items()
            ]
        except Exception:
            return [
                {"name": BUILTIN_MINIMAL_PROFILE.name,
                 "description": BUILTIN_MINIMAL_PROFILE.description,
                 "offline_mode": False, "runtimes": []}
            ]

    # ── статус ──────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        data = self._state.load()
        if not data:
            return {"status": "never_run"}
        return {
            "status": data.get("status", "unknown"),
            "profile": data.get("profile", ""),
            "timestamp": data.get("timestamp", ""),
            "warnings": data.get("warnings", []),
            "errors": data.get("errors", []),
        }

    # ── полный цикл ─────────────────────────────────────────

    def run(self) -> BootstrapReport:
        t0 = time.time()
        warnings: List[str] = []
        errors: List[str] = []
        steps: List[InstallStep] = []

        self._emit("bootstrap.started", {"profile": self._profile_name})

        # 1. SYSTEM CHECK
        env = self.check()
        self._emit("bootstrap.checked", {"os": env.os_type, "python": env.python_version})

        # 2. CONFIG LOAD (fallback → minimal при неизвестном профиле)
        profile = self._load_profile()
        if profile.name != self._profile_name:
            warnings.append(
                f"profile '{self._profile_name}' not found, fell back to '{profile.name}'"
            )
        self._emit("bootstrap.profile_loaded", {"loaded": profile.name})

        # 3. INSTALL (идемпотентно)
        installer = IdempotentInstaller(self.workspace, env)

        for pkg in profile.pip_packages:
            result = installer._install_pip(pkg)
            if result.error:
                errors.append(f"{pkg}: {result.error}")

        for pkg in profile.system_packages:
            result = installer._install_system(pkg)
            if result.error:
                errors.append(f"{pkg}: {result.error}")

        for rt_name in sorted(profile.runtimes):
            result = installer.install_runtime(profile.runtimes[rt_name])
            if result.error:
                errors.append(f"{rt_name}: {result.error}")

        steps.extend(installer.steps)

        # 4. DIAGNOSE
        diagnosis = RuntimeDoctor(env, self.workspace).diagnose()

        success = not errors
        duration_ms = (time.time() - t0) * 1000.0

        # 5. REPORT + state persist
        self._state.save(
            self._state.to_report_dict(env, steps, warnings, errors, self._profile_name)
        )

        report = BootstrapReport(
            success=success,
            profile=self._profile_name,
            duration_ms=round(duration_ms, 1),
            steps=steps,
            warnings=warnings,
            errors=errors,
            environment=env,
            diagnosis=diagnosis,
        )
        self._last_report = report

        if success:
            self._emit("bootstrap.completed", {"duration_ms": round(duration_ms, 1)})
        else:
            self._emit("bootstrap.failed", {"error": "; ".join(errors)})
        return report
