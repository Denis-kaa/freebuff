"""
Bootstrap Engine — главный класс, выполняет полный цикл bootstrap.

Основание: docs_10/core/BOOTSTRAP_SPECIFICATION.md §3.1
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
}
from typing import Any, Dict, List, Optional, TYPE_CHECKING

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None  # type: ignore

from freebuff_plugin_03.bootstrap import (
    BootstrapProfile,
    BootstrapReport,
    EnvironmentState,
    InstallStep,
    RuntimeDefinition,
    DiagnosticReport,
)
from freebuff_plugin_03.bootstrap.checker import EnvironmentChecker
from freebuff_plugin_03.bootstrap.state import BootstrapState
from freebuff_plugin_03.bootstrap.installer import IdempotentInstaller

if TYPE_CHECKING:
    EventBus = Any  # type: ignore


DEFAULT_PROFILES_PATH = Path(__file__).resolve().parent / "profiles.yaml"

# Default runtime definitions
DEFAULT_RUNTIMES: Dict[str, RuntimeDefinition] = {
    "freebuff": RuntimeDefinition(
        name="freebuff",
        display_name="Freebuff CLI",
        source="",
        version="latest",
        install_type="pip",
        bin_name="freebuff",
        post_install=[],
        requires=["python>=3.11"],
    ),
    "claude-code": RuntimeDefinition(
        name="claude-code",
        display_name="Claude Code",
        source="@anthropic/claude-code",
        version="latest",
        install_type="npm",
        bin_name="claude",
        post_install=[],
        requires=["node>=18"],
    ),
}

# Hardcoded profiles for fallback when pyyaml is not installed
_HARDCODED_PROFILES: Dict[str, BootstrapProfile] = {
    "minimal": BootstrapProfile(
        name="minimal",
        description="Fast start -- Core only",
        runtimes=["freebuff"],
        system_packages=["curl", "git"],
        default_runtime="freebuff",
    ),
    "developer": BootstrapProfile(
        name="developer",
        description="Daily development -- Core + Extensions",
        runtimes=["freebuff", "claude-code"],
        extensions=["mcp_server", "scenario_engine", "bridge_layer"],
        system_packages=["curl", "git", "wget"],
        default_runtime="freebuff",
        default_provider="anthropic",
        default_model="claude-3.5-sonnet",
    ),
    "offline": BootstrapProfile(
        name="offline",
        description="Offline work -- local models",
        runtimes=["freebuff"],
        extensions=["knowledge_engine"],
        offline_mode=True,
        auto_update=False,
    ),
    "cloud": BootstrapProfile(
        name="cloud",
        description="Cloud models via API",
        runtimes=["freebuff", "claude-code"],
        extensions=["mcp_server", "policy_engine"],
        default_runtime="claude-code",
        default_provider="anthropic",
    ),
    "android": BootstrapProfile(
        name="android",
        description="Native phone use (Termux)",
        runtimes=["freebuff"],
        extensions=["telegram_bot", "oom_protection"],
        default_provider="openrouter",
        auto_update=True,
    ),
}


class BootstrapEngine:
    """Main Bootstrap Engine class.

    Performs idempotent AI environment deployment.

    Usage:
        engine = BootstrapEngine(workspace_root="/path")
        report = engine.run()
        print(report.summary())
    """

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        profile: str = "minimal",
        event_bus: Optional[EventBus] = None,
    ):
        self._workspace = Path(workspace_root or os.getcwd())
        self._profile_name = profile
        self._profile: Optional[BootstrapProfile] = None
        self._state_mgr = BootstrapState(self._workspace)
        self._checker = EnvironmentChecker(str(self._workspace))
        self._installer: Optional[IdempotentInstaller] = None
        self._event_bus = event_bus

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit bootstrap event to EventBus (if configured)."""
        if self._event_bus is None:
            return
        try:
            from freebuff_plugin_03.bridge import create_event
            self._event_bus.publish(
                create_event(
                    event_type=f"bootstrap.{event_type}",
                    source="bootstrap_engine",
                    data={"profile": self._profile_name, **data},
                )
            )
        except Exception:
            pass  # EventBus failure should not break bootstrap

    def run(self) -> BootstrapReport:
        """Run full bootstrap: check -> load -> install -> diagnose -> report."""
        report = BootstrapReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            profile=self._profile_name,
        )
        t0 = time.time()

        self._emit("started", {"timestamp": report.timestamp})

        try:
            env = self.check()
            report.environment = env
            self._emit("checked", self._env_summary(env))

            profile = self._load_profile()
            if profile is None:
                report.success = False
                report.errors.append(f"Profile not found: {self._profile_name}")
                report.duration_ms = (time.time() - t0) * 1000
                self._emit("failed", {"error": f"Profile not found: {self._profile_name}"})
                return report
            self._profile = profile
            self._emit("profile_loaded", {"profile": profile.name})

            self._installer = IdempotentInstaller(self._workspace, env)
            self._state_mgr.mark_incomplete()

            install_results = self._installer.install_profile(profile)
            report.steps = self._installer.steps

            for rt_name in profile.runtimes:
                rt_def = DEFAULT_RUNTIMES.get(rt_name)
                if rt_def:
                    rt_result = self._installer.install_runtime(rt_def)
                    install_results.append(rt_result)

            for ir in install_results:
                if not ir.installed and ir.error:
                    report.errors.append(f"{ir.component}: {ir.error}")
                elif ir.error:
                    report.warnings.append(f"{ir.component}: {ir.error}")

            report.diagnosis = self._diagnose(env)
            if report.diagnosis.path_issues:
                report.warnings.extend(report.diagnosis.path_issues[:3])
            if report.diagnosis.key_issues:
                report.warnings.extend(report.diagnosis.key_issues[:2])

            state_data = self._state_mgr.to_report_dict(
                env, report.steps, report.warnings, report.errors, self._profile_name,
            )
            self._state_mgr.save(state_data)
            report.success = len(report.errors) == 0

            event_suffix = "completed" if report.success else "failed"
            self._emit(event_suffix, {
                "success": report.success,
                "duration_ms": (time.time() - t0) * 1000,
                "steps": len(report.steps),
                "error": report.errors[0] if report.errors else "",
                "errors_count": len(report.errors),
                "warnings_count": len(report.warnings),
            ])
        except Exception as e:
            report.success = False
            report.errors.append(f"Bootstrap failed: {e}")
            self._state_mgr.mark_incomplete()
            self._emit("failed", {"error": str(e)})

        report.duration_ms = (time.time() - t0) * 1000
        return report

    def check(self) -> EnvironmentState:
        return self._checker.check()

    def _env_summary(self, env: EnvironmentState) -> Dict[str, Any]:
        """Environment summary dict for events."""
        return {
            "os": env.os_type,
            "python": env.python_version,
            "git": env.git_available,
            "ram_mb": env.ram_available_mb,
            "disk_gb": env.disk_free_gb,
        }

    def _load_profile(self) -> Optional[BootstrapProfile]:
        """Load profile from YAML, then fall back to hardcoded profiles.

        Falls back to the hardcoded ``minimal`` profile when pyyaml is missing,
        profiles.yaml is missing/unreadable, OR the requested profile name is not
        found in profiles.yaml (graceful degrade — an unknown profile must not
        hard-fail, per BOOTSTRAP_SPECIFICATION §3.1 profiles enum).
        """
        if HAS_YAML and DEFAULT_PROFILES_PATH.exists():
            try:
                with open(DEFAULT_PROFILES_PATH, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                profiles = data.get("profiles", [])
                for p in profiles:
                    if p.get("name") == self._profile_name:
                        return BootstrapProfile(
                            name=p.get("name", "minimal"),
                            description=p.get("description", ""),
                            runtimes=p.get("runtimes", []),
                            extensions=p.get("extensions", []),
                            labs=p.get("labs", []),
                            system_packages=p.get("system_packages", []),
                            python_packages=p.get("python_packages", []),
                            npm_packages=p.get("npm_packages", []),
                            env_vars=p.get("env_vars", {}),
                            aliases=p.get("aliases", {}),
                            default_runtime=p.get("default_runtime", ""),
                            default_provider=p.get("default_provider", ""),
                            default_model=p.get("default_model", ""),
                            offline_mode=p.get("offline_mode", False),
                            auto_update=p.get("auto_update", True),
                        )
            except Exception:
                pass

        # Fallback to hardcoded profiles
        return _HARDCODED_PROFILES.get(self._profile_name, _HARDCODED_PROFILES["minimal"])

    def _diagnose(self, env: EnvironmentState) -> DiagnosticReport:
        from freebuff_plugin_03.bootstrap.doctor import RuntimeDoctor
        doctor = RuntimeDoctor(env, self._workspace)
        result = doctor.diagnose()
        return result

    def list_profiles(self) -> List[Dict[str, str]]:
        """List available profiles from YAML or hardcoded fallback."""
        if HAS_YAML and DEFAULT_PROFILES_PATH.exists():
            try:
                with open(DEFAULT_PROFILES_PATH, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                return [
                    {"name": p.get("name", ""), "description": p.get("description", "")}
                    for p in data.get("profiles", [])
                ]
            except Exception:
                pass
        return [
            {"name": k, "description": v.description}
            for k, v in _HARDCODED_PROFILES.items()
        ]

    def get_status(self) -> Dict[str, Any]:
        data = self._state_mgr.load()
        if not data:
            return {"status": "never_run", "message": "Bootstrap never ran"}
        return {
            "status": data.get("status", "unknown"),
            "profile": data.get("profile", ""),
            "timestamp": data.get("timestamp", ""),
            "warnings": data.get("warnings", 0),
            "errors": data.get("errors", 0),
        }

    @property
    def profile(self) -> Optional[BootstrapProfile]:
        return self._profile
