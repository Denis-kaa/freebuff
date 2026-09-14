"""Автообход projects_17 + профили reports_hub.yaml (спека §4.3, тест №5).

Контракты:
- проект с сигнатурами отчётности → DiscoveredProject(has_data=True);
- без сигнатур → DiscoveredProject(has_data=False, reason='нет отчётной
  документации') — карточка «нет данных», не молча (решение №12);
- битый reports_hub.yaml → has_data=False, reason='профиль невалиден: …',
  ошибка видна в диагностике (§11);
- конфликт slug → DiscoveryError с перечислением (B-Rule 5, §11);
- исключаемые каталоги — закрытый список EXCLUDED_DIRS + per-project
  `exclude: true` в yaml.

Slug-правило (§11, открытый вопрос №1 v1): кириллица/пробелы → хеш-суффикс
при небезопасном имени; оригинальное имя хранится в title.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

#: Сигнатуры отчётности (спека §4.3 «Автообход»).
REPORT_SIGNATURES: tuple[str, ...] = (
    "PROJECT_STATUS_REPORT.md",
    "FINAL_REPORT.md",
    "MANIFEST.md",
)
#: Glob-сигнатуры (проверяются отдельно).
REPORT_GLOBS: tuple[str, ...] = (
    "PHASE_*_REPORT.md",
    "PHASE_*.md",
    "ROADMAP*.md",
    "РОАДМАП*.md",
    "AUDIT*.md",
    "*AUDIT*.md",
)

#: Служебные/мусорные каталоги (спека §4.3): обходится мимо всегда.
EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".freezer",
        "trash_21",
        "__pycache__",
        "node_modules",
        ".git",
        ".venv",
        "venv",
    }
)

_SLUG_UNSAFE = re.compile(r"[^a-z0-9_-]+")


class DiscoveryError(RuntimeError):
    """Ошибка обхода (например, конфликт slug — §11)."""


@dataclass
class DiscoveredProject:
    """Результат обхода одного каталога projects_17/<name>."""

    name: str  # оригинальное имя каталога
    slug: str  # URL-безопасный слаг
    path: Path
    has_data: bool
    reason: str = ""  # почему has_data=False (для карточки «нет данных»)
    profile: dict[str, Any] = field(default_factory=dict)  # reports_hub.yaml
    profile_error: str = ""  # битый yaml → текст ошибки в диагностику


def make_slug(name: str, *, taken: set[str] | None = None) -> str:
    """URL-безопасный слаг из имени каталога (§11: кириллица → хеш при коллизии).

    Простой случай (латиница/цифры/дефис) — транслит не нужен, имя уже валидно.
    Иначе — хеш-суффикс: «админка печатник» → «ad"-hash» невозможен, поэтому
    слаг = 'p' + 12 hex-символов sha256 имени (детерминированно).
    """
    base = name.strip().lower().replace(" ", "-")
    safe = _SLUG_UNSAFE.sub("-", base).strip("-")
    if safe and safe == _SLUG_UNSAFE.sub("", base) and base == safe:
        slug = safe
    else:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
        slug = f"p-{digest}"
    if taken is not None and slug in taken:
        raise DiscoveryError(
            f"конфликт slug {slug!r} для проектов: {sorted(taken)} + {name!r} (B-Rule 5)"
        )
    return slug


def _has_report_signatures(project_dir: Path) -> tuple[bool, str]:
    """Есть ли в каталоге сигнатуры отчётности (файлы или globs)."""
    for sig in REPORT_SIGNATURES:
        if (project_dir / sig).is_file():
            return True, sig
    for pattern in REPORT_GLOBS:
        if any(project_dir.glob(pattern)):
            return True, pattern
    return False, "нет отчётной документации"


def _load_profile(project_dir: Path) -> tuple[dict[str, Any], str]:
    """Читает reports_hub.yaml (опционален); битый → пусто + ошибка (не молча)."""
    profile_path = project_dir / "reports_hub.yaml"
    if not profile_path.is_file():
        return {}, ""
    try:
        data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return {}, f"профиль невалиден: {exc}"
    if data is None:
        return {}, ""
    if not isinstance(data, dict):
        return {}, f"профиль невалиден: ожидается словарь, получено {type(data).__name__}"
    if data.get("exclude") is True:
        return {}, "excluded"
    return data, ""


def discover_projects(root: Path) -> list[DiscoveredProject]:
    """Обход projects_17/<name>/ (спека §4.3): сигнатуры + профиль + слаг.

    Результат отсортирован по имени; слаги уникальны (конфликт → DiscoveryError).
    """
    if not root.is_dir():
        raise DiscoveryError(f"корень обхода не найден: {root}")

    discovered: list[DiscoveredProject] = []
    taken: set[str] = set()
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if not entry.is_dir() or entry.name in EXCLUDED_DIRS or entry.name.startswith("."):
            continue
        profile, profile_error = _load_profile(entry)
        if profile_error == "excluded":
            continue
        if profile_error:
            discovered.append(
                DiscoveredProject(
                    name=entry.name,
                    slug=make_slug(entry.name, taken=taken),
                    path=entry,
                    has_data=False,
                    reason=profile_error,
                    profile_error=profile_error,
                )
            )
            continue
        has_data, evidence = _has_report_signatures(entry)
        discovered.append(
            DiscoveredProject(
                name=entry.name,
                slug=make_slug(entry.name, taken=taken),
                path=entry,
                has_data=has_data,
                reason="" if has_data else evidence,
                profile=profile,
            )
        )
    return discovered
