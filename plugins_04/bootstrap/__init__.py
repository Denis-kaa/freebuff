"""Bootstrap Engine — environment bootstrap (восстановлено v5.189.89).

По контракту тестов tests_09/test_bootstrap_engine.py и спецификации
docs_10/core/BOOTSTRAP_SPECIFICATION.md.

Важно: это НЕ тот же bootstrap, что scripts_01/bootstrap.py (сессионный).
"""

from plugins_04.bootstrap.checker import EnvironmentChecker
from plugins_04.bootstrap.doctor import RuntimeDoctor
from plugins_04.bootstrap.engine import BootstrapEngine
from plugins_04.bootstrap.installer import IdempotentInstaller
from plugins_04.bootstrap.state import BootstrapState
from plugins_04.bootstrap.types import (
    BootstrapEvent,
    BootstrapProfile,
    BootstrapReport,
    DiagnosticReport,
    EnvironmentState,
    InstallResult,
    InstallStep,
    RuntimeDefinition,
)

__all__ = [
    "BootstrapEngine",
    "BootstrapEvent",
    "BootstrapProfile",
    "BootstrapReport",
    "BootstrapState",
    "DiagnosticReport",
    "EnvironmentChecker",
    "EnvironmentState",
    "IdempotentInstaller",
    "InstallResult",
    "InstallStep",
    "RuntimeDefinition",
    "RuntimeDoctor",
]
