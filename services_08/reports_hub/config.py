"""Профили проектов и автообход projects_17/ (спека §4.3).

Owner-файл проекта: ``projects_17/<slug>/reports_hub.yaml``.
Нет файла — default-профиль по сигнатурам отчётности.
Нет сигнатур — карточка «нет данных» (серая, с причиной).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


#: Сигнатуры отчётной документации (спека §4.3, автообход).
REPORT_SIGNATURES: tuple[str, ...] = (
    "PROJECT_STATUS_REPORT.md",
    "PHASE_*_REPORT.md",
    "ROADMAP*.md",
    "РОАДМАП*.md",
    "FINAL_REPORT.md",
    "MANIFEST.md",
)

#: Служебные каталоги, исключаемые из автообхода (спека §4.3).
EXCLUDED_DIRS: tuple[str, ...] = (
    ".freezer",
    "trash_21",
    "__pycache__",
    ".git",
    ".venv",
    "node_modules",
)


@dataclass(frozen=True)
class ProjectProfile:
    """Профиль отчёта одного проекта."""

    slug: str
    path: Path
    title: str
    accent: str = ""
    logo: str = ""
    docs: tuple[str, ...] = ()
    timeline_sources: tuple[str, ...] = ()
    loc_paths: tuple[str, ...] = ()
    roadmap: str = ""
    blockers: str = ""
    excluded: bool = False
    has_report_docs: bool = False
    invalid_reason: str = ""

    def to_json(self) -> dict[str, Any]:
        """Сериализовать профиль в JSON-совместимый словарь."""
        payload = {
            "slug": self.slug,
            "path": str(self.path),
            "title": self.title,
            "accent": self.accent,
            "logo": self.logo,
            "docs": list(self.docs),
            "timeline_sources": list(self.timeline_sources),
            "loc_paths": list(self.loc_paths),
            "roadmap": self.roadmap,
            "blockers": self.blockers,
            "excluded": self.excluded,
            "has_report_docs": self.has_report_docs,
            "invalid_reason": self.invalid_reason,
        }
        return payload


def _strip_quotes(value: str) -> str:
    """Снять одну пару совпадающих кавычек (одинарные/двойные)."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("\"", "'"):
        return value[1:-1]
    return value


def _parse_owner_text(text: str, project_name: str) -> dict[str, Any]:
    """Минимальный парсер reports_hub.yaml без внешних зависимостей.

    Подмножество YAML, достаточное для профиля (§4.3 спеки): скаляры
    (title/accent/logo/roadmap/blockers/exclude), списки (docs,
    timeline_sources, metrics.loc_paths). Вложенность — только
    ``metrics:`` → ``loc_paths:``. Комментарии ``#`` и пустые строки
    игнорируются.

    Raises:
        ValueError: битый файл (табы, незакрытая кавычка, мусор) — проект
            помечается невалидным (спека §11), обход не падает.
    """
    data: dict[str, Any] = {}
    current_list_key: str | None = None
    in_metrics = False
    loc_paths: list[str] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        if "\t" in raw_line:
            raise ValueError(
                f"битый reports_hub.yaml в {project_name}: таб в строке {line_no}"
            )
        stripped = raw_line.split("#", 1)[0].rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        content = stripped.strip()
        if indent == 0:
            in_metrics = False
            current_list_key = None
            if content.startswith("- "):
                raise ValueError(
                    f"битый reports_hub.yaml в {project_name}: "
                    f"элемент списка без ключа (строка {line_no})"
                )
            if ":" not in content:
                raise ValueError(
                    f"битый reports_hub.yaml в {project_name}: "
                    f"нет ':' (строка {line_no})"
                )
            key, _, value = content.partition(":")
            key = key.strip()
            value = value.strip()
            if key == "metrics":
                if value:
                    raise ValueError(
                        f"битый reports_hub.yaml в {project_name}: "
                        f"metrics должен быть mapping (строка {line_no})"
                    )
                in_metrics = True
                continue
            if key in ("docs", "timeline_sources"):
                if value:
                    raise ValueError(
                        f"битый reports_hub.yaml в {project_name}: "
                        f"{key} должен быть списком (строка {line_no})"
                    )
                data[key] = []
                current_list_key = key
                continue
            if value.startswith("[") and not value.endswith("]"):
                raise ValueError(
                    f"битый reports_hub.yaml в {project_name}: "
                    f"незакрытая скобка (строка {line_no})"
                )
            if value.count('"') % 2 != 0 or value.count("'") % 2 != 0:
                raise ValueError(
                    f"битый reports_hub.yaml в {project_name}: "
                    f"незакрытая кавычка (строка {line_no})"
                )
            if key == "exclude":
                data[key] = value.lower() in ("true", "yes", "1")
            else:
                data[key] = _strip_quotes(value)
            continue
        # Вложенная строка: элемент списка или metrics.loc_paths.
        if not content.startswith("- "):
            if in_metrics and indent == 2 and content.startswith("loc_paths:"):
                _, _, value = content.partition(":")
                value = value.strip()
                if value:
                    raise ValueError(
                        f"битый reports_hub.yaml в {project_name}: "
                        f"loc_paths должен быть списком (строка {line_no})"
                    )
                current_list_key = "__loc_paths__"
                continue
            raise ValueError(
                f"битый reports_hub.yaml в {project_name}: "
                f"неожиданная вложенная строка {line_no}"
            )
        item = _strip_quotes(content[2:].strip())
        if current_list_key == "__loc_paths__":
            loc_paths.append(item)
        elif current_list_key in ("docs", "timeline_sources"):
            data[current_list_key].append(item)
        else:
            raise ValueError(
                f"битый reports_hub.yaml в {project_name}: "
                f"элемент списка без ключа (строка {line_no})"
            )
    if loc_paths:
        data["metrics"] = {"loc_paths": loc_paths}
    return data


def _read_owner_file(project_dir: Path) -> dict[str, Any]:
    """Прочитать reports_hub.yaml проекта (пусто при отсутствии).

    Raises:
        ValueError: если YAML битый (спека §11: проект помечается невалидным).
    """
    owner = project_dir / "reports_hub.yaml"
    if not owner.exists():
        return {}
    try:
        text = owner.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"не читается reports_hub.yaml в {project_dir.name}: {exc}") from exc
    data = _parse_owner_text(text, project_dir.name)
    if not isinstance(data, dict):
        raise ValueError(f"reports_hub.yaml в {project_dir.name}: корень должен быть mapping")
    return data


def _has_report_docs(project_dir: Path) -> bool:
    """Проверить сигнатуры отчётности в каталоге проекта."""
    for signature in REPORT_SIGNATURES:
        if "*" in signature:
            if list(project_dir.glob(signature)):
                return True
        elif (project_dir / signature).exists():
            return True
    return False


def build_profile(slug: str, project_dir: Path) -> ProjectProfile:
    """Построить профиль проекта (owner-файл или default).

    Битый YAML не роняет обход: профиль помечается invalid_reason
    (спека §11 — сайт генерится без него, ошибка видна в диагностике).
    """
    try:
        owner = _read_owner_file(project_dir)
    except ValueError as exc:
        return ProjectProfile(
            slug=slug,
            path=project_dir,
            title=slug,
            invalid_reason=str(exc),
        )
    if owner.get("exclude") is True:
        return ProjectProfile(slug=slug, path=project_dir, title=slug, excluded=True)
    has_docs = _has_report_docs(project_dir)
    docs = tuple(str(x) for x in owner.get("docs", []))
    timeline_sources = tuple(str(x) for x in owner.get("timeline_sources", []))
    metrics = owner.get("metrics", {}) if isinstance(owner.get("metrics"), dict) else {}
    loc_paths = tuple(str(x) for x in metrics.get("loc_paths", []))
    return ProjectProfile(
        slug=slug,
        path=project_dir,
        title=str(owner.get("title", slug)),
        accent=str(owner.get("accent", "")),
        logo=str(owner.get("logo", "")),
        docs=docs,
        timeline_sources=timeline_sources,
        loc_paths=loc_paths,
        roadmap=str(owner.get("roadmap", "")),
        blockers=str(owner.get("blockers", "")),
        has_report_docs=has_docs,
    )


def discover_projects(projects_root: Path) -> list[ProjectProfile]:
    """Автообход projects_17/ (спека §4.3).

    Args:
        projects_root: каталог ``projects_17`` (проверяется существование).

    Returns:
        Список профилей, отсортированный по slug. Служебные каталоги пропущены.
    """
    profiles: list[ProjectProfile] = []
    if not projects_root.exists():
        return profiles
    try:
        entries = sorted(os.listdir(projects_root))
    except OSError:
        return profiles
    for name in entries:
        if name in EXCLUDED_DIRS or name.startswith("."):
            continue
        project_dir = projects_root / name
        if not project_dir.is_dir():
            continue
        profiles.append(build_profile(slug=name, project_dir=project_dir))
    return profiles
