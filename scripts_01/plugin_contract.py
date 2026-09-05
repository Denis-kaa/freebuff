#!/usr/bin/env python3
"""
plugin_contract.py — Plugin Contract Specification (правило 9, промт 37).

Программный валидатор границ «плагин ↔ ядро». Проверяет:
  - manifest.json (обязательные поля, name, version, events_subscribed, python_version)
  - экземпляр (BasePlugin, наличие lifecycle-методов)

Спецификация: docs_10/plugin/PLUGIN_CONTRACT_SPECIFICATION.md
Использование:
    from scripts_01.plugin_contract import validate_manifest, validate_plugin_entry

    violations = validate_manifest(manifest)
    violations = validate_plugin_entry(entry)
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# Константы контракта
# ═══════════════════════════════════════════════════════════════

#: Допустимое имя плагина: только нижний регистр, цифры, подчёркивание.
NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")
#: SemVer: X.Y.Z (без pre-release/build — контракт строгий).
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
#: Шаблон события: domain.event или domain.* (нижний регистр).
EVENT_PATTERN = re.compile(r"^[a-z0-9_)+(\.[a-z0-9_*]+)+$")

#: Обязательные поля manifest.json (поле, читаемое сообщение).
REQUIRED_MANIFEST_FIELDS = {
    "name": "имя плагина",
    "version": "версия плагина",
    "description": "описание плагина",
}

#: Lifecycle-методы, которые должен предоставлять BasePlugin.
LIFECYCLE_METHODS = [
    "on_load",
    "on_enable",
    "on_disable",
    "on_unload",
    "on_event",
    "get_tools",
    "get_commands",
    "execute",
]


# ═══════════════════════════════════════════════════════════════
# Типы
# ═══════════════════════════════════════════════════════════════


class ContractSeverity(Enum):
    """Строгость нарушения контракта."""

    WARN = "warn"
    ERROR = "error"


@dataclass
class ContractViolation:
    """Одно нарушение контракта.

    Attributes:
        field: путь/имя поля (например "manifest.name", "instance").
        message: человекочитаемое описание.
        severity: WARN или ERROR.
    """

    field: str
    message: str
    severity: ContractSeverity = ContractSeverity.WARN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
        }


# ═══════════════════════════════════════════════════════════════
# Валидаторы
# ═══════════════════════════════════════════════════════════════


def _parse_python_version(spec: str) -> Optional[tuple]:
    """Парсит минимальную версию Python из spec вида '>=3.10'.

    Returns:
        (major, minor) или None, если spec не содержит ограничения.
    """
    m = re.search(r"(>=|>)?\s*(\d+)\.(\d+)", spec or "")
    if not m:
        return None
    return (int(m.group(2)), int(m.group(3)))


def validate_manifest(manifest: Any) -> List[ContractViolation]:
    """Проверяет manifest.json плагина на соответствие контракту.

    Args:
        manifest: экземпляр PluginManifest (или None).

    Returns:
        Список ContractViolation (пустой = контракт соблюдён).
    """
    violations: List[ContractViolation] = []

    if manifest is None:
        return [ContractViolation(
            field="manifest",
            message="manifest.json отсутствует (обязателен по контракту)",
            severity=ContractSeverity.ERROR,
        )]

    # Обязательные поля
    for field_name, human_name in REQUIRED_MANIFEST_FIELDS.items():
        value = getattr(manifest, field_name, None)
        if not value:
            violations.append(ContractViolation(
                field=f"manifest.{field_name}",
                message=f"{human_name} отсутствует или пусто",
                severity=ContractSeverity.ERROR,
            ))

    # Формат имени
    if manifest.name and not NAME_PATTERN.match(manifest.name):
        violations.append(ContractViolation(
            field="manifest.name",
            message=f"невалидное имя '{manifest.name}' (ожидается ^[a-z0-9_]+$)",
            severity=ContractSeverity.ERROR,
        ))

    # Формат версии
    if manifest.version and not VERSION_PATTERN.match(manifest.version):
        violations.append(ContractViolation(
            field="manifest.version",
            message=f"невалидная версия '{manifest.version}' (ожидается SemVer X.Y.Z)",
            severity=ContractSeverity.ERROR,
        ))

    # Шаблоны событий
    for event in manifest.events_subscribed or []:
        if not EVENT_PATTERN.match(event):
            violations.append(ContractViolation(
                field=f"manifest.events_subscribed[{event}]",
                message=f"невалидный шаблон события '{event}' (ожидается domain.event или domain.*)",
                severity=ContractSeverity.WARN,
            ))

    # Совместимость версии Python
    min_py = _parse_python_version(manifest.python_version)
    if min_py is not None:
        current = (sys.version_info.major, sys.version_info.minor)
        if current < min_py:
            violations.append(ContractViolation(
                field="manifest.python_version",
                message=f"требуется Python {min_py[0]}.{min_py[1]}+, "
                        f"текущий {current[0]}.{current[1]}",
                severity=ContractSeverity.WARN,
            ))

    return violations


def validate_plugin_entry(entry: Any) -> List[ContractViolation]:
    """Проверяет PluginEntry на соответствие контракту.

    Комбинирует проверки манифеста и экземпляра.

    Args:
        entry: PluginEntry из PluginRegistry.

    Returns:
        Список ContractViolation (пустой = контракт соблюдён).
    """
    violations: List[ContractViolation] = []

    # Манифест
    violations.extend(validate_manifest(entry.manifest))

    # Экземпляр
    instance = entry.instance
    if instance is None:
        violations.append(ContractViolation(
            field="instance",
            message="плагин не имеет экземпляра (instance is None)",
            severity=ContractSeverity.ERROR,
        ))
        return violations

    from scripts_01.plugin_api import BasePlugin
    if not isinstance(instance, BasePlugin):
        violations.append(ContractViolation(
            field="instance",
            message=f"экземпляр не является BasePlugin: {type(instance).__name__}",
            severity=ContractSeverity.ERROR,
        ))
        return violations

    # Lifecycle-методы
    for method in LIFECYCLE_METHODS:
        if not hasattr(instance, method) or not callable(getattr(instance, method)):
            violations.append(ContractViolation(
                field=f"instance.{method}",
                message=f"отсутствует lifecycle-метод '{method}'",
                severity=ContractSeverity.WARN,
            ))

    return violations


def has_errors(violations: List[ContractViolation]) -> bool:
    """True, если среди нарушений есть хотя бы одно ERROR-нарушение."""
    return any(v.severity == ContractSeverity.ERROR for v in violations)


def format_violations(
    plugin_name: str,
    violations: List[ContractViolation],
) -> str:
    """Форматирует отчёт о нарушениях для CLI/логов."""
    if not violations:
        return f"✅ Contract OK — {plugin_name}"
    lines = [f"❌ Contract violations for {plugin_name} ({len(violations)}):"]
    for v in violations:
        lines.append(f"   [{v.severity.value.upper()}] {v.field}: {v.message}")
    return "\n".join(lines)
