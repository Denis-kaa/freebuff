"""ReportModel — dataclass-контракт отчёта (reports-hub-spec §4.1).

Contract First: сайт = детерминированный рендер модели; модель версионируется
(`schema_version`), JSON-сериализуемая (to_json/from_json round-trip — тест №3
спеки). Факты хранятся с указанием источника (файл+строка, §5.2 анти-галлюцинации):
нет данных → секция помечается status='missing', пустышки запрещены.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

#: Версия контракта модели (спека §4.1: модель версионируется).
SCHEMA_VERSION = 1

#: Закрытый словарь статусов секции (ANTI-6b: вне набора — ValueError).
SECTION_STATUSES: tuple[str, ...] = ("ok", "missing", "error")


@dataclass
class SourceRef:
    """Указание источника факта (файл + строка, §5.2 — числа с источником)."""

    path: str
    line: int | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "SourceRef":
        return cls(path=str(data["path"]), line=data.get("line"))


@dataclass
class Section:
    """Секция отчёта §7.1. status='missing' — источник не найден (не молча)."""

    kind: str  # закрытый словарь SECTION_KINDS
    title: str
    status: str = "ok"  # SECTION_STATUSES
    items: list[dict[str, Any]] = field(default_factory=list)
    source: SourceRef | None = None
    note: str = ""

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Section":
        status = str(data.get("status", "ok"))
        if status not in SECTION_STATUSES:
            raise ValueError(
                f"недопустимый статус секции {status!r} (допустимо: {SECTION_STATUSES})"
            )
        source = data.get("source")
        return cls(
            kind=str(data["kind"]),
            title=str(data["title"]),
            status=status,
            items=list(data.get("items", [])),
            source=SourceRef.from_json(source) if source else None,
            note=str(data.get("note", "")),
        )


@dataclass
class ProjectReport:
    """Отчёт одного проекта: метаданные + упорядоченные секции §7.1."""

    slug: str
    title: str
    generated_at: str
    sections: list[Section] = field(default_factory=list)
    has_data: bool = True  # False → карточка «нет данных» (решение №12)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "slug": self.slug,
            "title": self.title,
            "generated_at": self.generated_at,
            "has_data": self.has_data,
            "sections": [s.to_json() for s in self.sections],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ProjectReport":
        version = int(data.get("schema_version", 0))
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version {version} не поддерживается (ожидалось {SCHEMA_VERSION})"
            )
        return cls(
            slug=str(data["slug"]),
            title=str(data["title"]),
            generated_at=str(data["generated_at"]),
            has_data=bool(data.get("has_data", True)),
            sections=[Section.from_json(s) for s in data.get("sections", [])],
        )


@dataclass
class ReportModel:
    """Корневая модель генерации: главная + все проекты (спека §4.2 model.py)."""

    generated_at: str
    projects: list[ProjectReport] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": self.generated_at,
            "projects": [p.to_json() for p in self.projects],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ReportModel":
        version = int(data.get("schema_version", 0))
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version {version} не поддерживается (ожидалось {SCHEMA_VERSION})"
            )
        return cls(
            generated_at=str(data["generated_at"]),
            projects=[ProjectReport.from_json(p) for p in data.get("projects", [])],
        )

    def to_json_str(self) -> str:
        return json.dumps(self.to_json(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json_str(cls, raw: str) -> "ReportModel":
        return cls.from_json(json.loads(raw))
