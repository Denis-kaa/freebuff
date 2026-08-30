"""
Bootstrap Engine — идемпотентное развёртывание AI-среды.

Спецификация: docs_10/core/BOOTSTRAP_SPECIFICATION.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# Environment State
# ═══════════════════════════════════════════════════════════════


@dataclass
class EnvironmentState:
    """Текущее состояние окружения."""
    os_type: str = "unknown"             # android, linux, mac, unknown
    is_termux: bool = False
    python_version: str = ""
    python_path: str = ""
    node_version: Optional[str] = None
    git_available: bool = False
    has_proot: bool = False
    disk_free_gb: float = 0.0
    ram_available_mb: int = 0
    ram_total_mb: int = 0
    pip_packages: Dict[str, str] = field(default_factory=dict)
    npm_packages: Dict[str, str] = field(default_factory=dict)
    system_packages: List[str] = field(default_factory=list)
    runtimes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    path_dirs: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    has_env_file: bool = False
    workspace: str = ""
    has_git: bool = False
    git_branch: str = ""
    git_remote: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# Bootstrap Profile
# ═══════════════════════════════════════════════════════════════


@dataclass
class BootstrapProfile:
    """Профиль установки."""
    name: str = "minimal"
    description: str = ""
    runtimes: List[str] = field(default_factory=list)
    extensions: List[str] = field(default_factory=list)
    labs: List[str] = field(default_factory=list)
    system_packages: List[str] = field(default_factory=list)
    python_packages: List[str] = field(default_factory=list)
    npm_packages: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    aliases: Dict[str, str] = field(default_factory=dict)
    default_runtime: str = ""
    default_provider: str = ""
    default_model: str = ""
    offline_mode: bool = False
    auto_update: bool = True


# ═══════════════════════════════════════════════════════════════
# Install Step / Result
# ═══════════════════════════════════════════════════════════════


@dataclass
class InstallStep:
    """Один шаг установки."""
    name: str = ""
    status: str = "pending"  # pending, running, passed, skipped, failed
    duration_ms: float = 0.0
    error: str = ""
    skip_reason: str = ""


@dataclass
class InstallResult:
    """Результат установки компонента."""
    component: str = ""
    installed: bool = False
    version: str = ""
    path: str = ""
    error: str = ""
    skip_reason: str = ""


@dataclass
class RuntimeDefinition:
    """Определение AI Runtime."""
    name: str = ""
    display_name: str = ""
    source: str = ""
    version: str = "latest"
    install_type: str = "pip"       # pip, npm, git, binary, mcp
    install_path: str = ""
    bin_name: str = ""
    post_install: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Reports
# ═══════════════════════════════════════════════════════════════


@dataclass
class DiagnosticReport:
    """Результат диагностики."""
    path_issues: List[str] = field(default_factory=list)
    runtime_issues: List[str] = field(default_factory=list)
    dependency_issues: List[str] = field(default_factory=list)
    key_issues: List[str] = field(default_factory=list)
    health_score: float = 1.0  # 0.0 - 1.0


@dataclass
class BootstrapReport:
    """Результат bootstrap."""
    success: bool = True
    timestamp: str = ""
    profile: str = ""
    duration_ms: float = 0.0
    environment: Optional[EnvironmentState] = None
    steps: List[InstallStep] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    diagnosis: Optional[DiagnosticReport] = None

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def summary(self) -> str:
        lines = [
            f"Bootstrap: {'✅' if self.success else '❌'}",
            f"Profile: {self.profile}",
            f"Duration: {self.duration_ms:.0f}ms",
            f"Steps: {len(self.steps)}",
        ]
        if self.warnings:
            lines.append(f"Warnings: {len(self.warnings)}")
        if self.errors:
            lines.append(f"Errors: {len(self.errors)}")
        return "\n".join(lines)


__all__ = [
    "EnvironmentState",
    "BootstrapProfile",
    "InstallStep",
    "InstallResult",
    "RuntimeDefinition",
    "DiagnosticReport",
    "BootstrapReport",
]
