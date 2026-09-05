"""Bootstrap types — восстановлено v5.189.89 по контракту тестов
tests_09/test_bootstrap_engine.py и спецификации docs_10/core/BOOTSTRAP_SPECIFICATION.md.

Bootstrap Engine — не установщик, а менеджер состояния среды (идемпотентный).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EnvironmentState:
    """Текущее состояние окружения (спека §2.2)."""

    os_type: str = "unknown"           # linux | android (termux) | mac | windows
    is_termux: bool = False
    python_version: str = ""
    node_version: str = ""
    git_available: bool = False
    disk_free_gb: float = 0.0
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    pip_packages: Dict[str, str] = field(default_factory=dict)
    system_packages: List[str] = field(default_factory=list)
    path_dirs: List[str] = field(default_factory=list)
    has_git: bool = False              # workspace является git-репозиторием
    has_env_file: bool = False         # workspace/.env существует
    workspace: str = ""


@dataclass
class InstallStep:
    """Один шаг установки (идемпотентный)."""

    name: str = ""
    status: str = "pending"            # pending | passed | failed | skipped
    duration_ms: float = 0.0
    error: str = ""


@dataclass
class InstallResult:
    """Результат одной операции установки."""

    installed: bool = False
    skip_reason: str = ""
    error: str = ""
    duration_ms: float = 0.0

    @property
    def ok(self) -> bool:
        """Успех = установлен ИЛИ корректно пропущен (идемпотентность)."""
        return self.installed or bool(self.skip_reason)


@dataclass
class RuntimeDefinition:
    """Определение Runtime: имя, источник, версия."""

    name: str
    version: str = "latest"
    install_type: str = "pip"          # pip | npm | git
    source: str = ""                   # для install_type=git
    bin_name: str = ""                 # если пусто — используется name


@dataclass
class BootstrapProfile:
    """Профиль установки (Minimal, Developer, Offline, ...)."""

    name: str = "minimal"
    description: str = ""
    offline_mode: bool = False
    pip_packages: List[str] = field(default_factory=list)
    system_packages: List[str] = field(default_factory=list)
    runtimes: Dict[str, RuntimeDefinition] = field(default_factory=dict)


@dataclass
class DiagnosticReport:
    """Результат диагностики Runtime Doctor."""

    health_score: float = 0.0
    path_issues: List[str] = field(default_factory=list)
    runtime_issues: List[str] = field(default_factory=list)
    dependency_issues: List[str] = field(default_factory=list)
    key_issues: List[str] = field(default_factory=list)


@dataclass
class BootstrapReport:
    """Результат полного цикла bootstrap."""

    success: bool = False
    profile: str = ""
    duration_ms: float = 0.0
    steps: List[InstallStep] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    environment: Optional[EnvironmentState] = None
    diagnosis: Optional[DiagnosticReport] = None

    def summary(self) -> str:
        icon = "✅" if self.success else "❌"
        lines = [
            f"{icon} Bootstrap '{self.profile}' — "
            f"{'success' if self.success else 'failed'} ({self.duration_ms:.0f} ms)"
        ]
        for s in self.steps:
            mark = {"passed": "✓", "failed": "✗", "skipped": "↷"}.get(s.status, "·")
            lines.append(f"  {mark} {s.name} [{s.status}]"
                         + (f" — {s.error}" if s.error else ""))
        for w in self.warnings:
            lines.append(f"  ⚠️ {w}")
        for e in self.errors:
            lines.append(f"  ✗ {e}")
        return "\n".join(lines)

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def has_errors(self) -> bool:
        return len(self.errors) > 0


@dataclass
class BootstrapEvent:
    """Событие для EventBus (контракт: атрибуты .type / .data)."""

    type: str
    data: Dict[str, Any] = field(default_factory=dict)
