"""Библиотека документов Reports Hub (спека §7.2, H3).

Карточки доков: имя, тип, статус-цитата, дата, размер, резюме.
Полный рендер документа — в `render.py` (самодостаточный HTML).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from services_08.reports_hub.extract.markdown import parse_markdown

#: Расширения, попадающие в библиотеку.
DOC_SUFFIXES: tuple[str, ...] = (".md",)

#: Служебные имена, не попадающие в библиотеку.
EXCLUDED_NAMES: tuple[str, ...] = ("README.md", "LICENSE.md", "CHANGELOG.md")

_DOC_TYPES: tuple[tuple[str, str], ...] = (
    (r"^PHASE", "phase-report"),
    (r"^PROJECT_STATUS_REPORT", "status"),
    (r"РОАДМАП|ROADMAP", "roadmap"),
    (r"AUDIT|PRICE_AUDIT|PRODUCT_AUDIT", "audit"),
    (r"^research/|RESEARCH|FINAL_REPORT", "research"),
    (r"SPEC|спека|CALCULATOR_|MATERIAL_MODEL|BUSINESS_RULES|ORDER_WORKFLOW", "spec"),
    (r"^prompts?/|промт", "prompt"),
    (r"OPEN_QUESTIONS|QUESTION_FLOW", "open-questions"),
)

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class DocEntry:
    """Документ библиотеки: карточка + путь для полного рендера."""

    filename: str
    rel_path: str
    path: Path
    doc_type: str = ""
    status_quote: str = ""
    date: str = ""
    size_bytes: int = 0
    summary: str = ""
    heavy: bool = False


def doc_type_of(rel_path: str) -> str:
    """Классифицировать документ по относительному пути (закрытый набор типов)."""
    for pattern, doc_type in _DOC_TYPES:
        if re.search(pattern, rel_path, re.IGNORECASE):
            return doc_type
    return "doc"


def _patterns_for(profile_docs: tuple[str, ...]) -> list[str]:
    """Глобы профиля; пусто — все .md проекта (default-профиль §4.3)."""
    return list(profile_docs) if profile_docs else ["*.md", "**/*.md"]


def collect_docs(project_dir: Path, profile_docs: tuple[str, ...]) -> list[DocEntry]:
    """Собрать документы проекта по глобам профиля.

    Args:
        project_dir: каталог проекта.
        profile_docs: глобы из reports_hub.yaml (пусто → все .md).

    Returns:
        Отсортированный список DocEntry (по rel_path).
    """
    seen: dict[str, DocEntry] = {}
    for pattern in _patterns_for(profile_docs):
        for path in sorted(project_dir.glob(pattern)):
            if not path.is_file() or path.suffix.lower() not in DOC_SUFFIXES:
                continue
            rel_path = path.relative_to(project_dir).as_posix()
            if rel_path.startswith(("worktree/", "worktree_wf/", ".venv/", "node_modules/")):
                continue
            if path.name in EXCLUDED_NAMES:
                continue
            if rel_path in seen:
                continue
            seen[rel_path] = _build_entry(path, rel_path)
    return [seen[key] for key in sorted(seen)]


def _build_entry(path: Path, rel_path: str) -> DocEntry:
    """Построить карточку документа (парсинг шапки + резюме-фолбэк)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return DocEntry(
            filename=path.name,
            rel_path=rel_path,
            path=path,
            doc_type=doc_type_of(rel_path),
            summary="источник не читается",
        )
    doc = parse_markdown(text, path=rel_path)
    status_quote = ""
    date = ""
    for quote in doc.top_quotes:
        if "статус" in quote.lower() and status_quote == "":
            status_quote = quote
        match = _DATE_RE.search(quote)
        if match and date == "":
            date = match.group(1)
    if date == "":
        match = _DATE_RE.search(text[:2000])
        if match:
            date = match.group(1)
    if status_quote == "":
        for section in doc.sections[:3]:
            if "статус" in section.title.lower() and section.quotes:
                status_quote = section.quotes[0]
                break
    summary = ""
    for section in doc.sections:
        if section.level == 1:
            continue
        for line in section.body_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith(("**", "|", "#", "-", ">")):
                summary = stripped[:300]
                break
        if summary:
            break
    if not summary and doc.top_quotes:
        summary = doc.top_quotes[0][:300]
    return DocEntry(
        filename=path.name,
        rel_path=rel_path,
        path=path,
        doc_type=doc_type_of(rel_path),
        status_quote=status_quote,
        date=date,
        size_bytes=path.stat().st_size if path.exists() else 0,
        summary=summary,
        heavy=path.stat().st_size > 200_000 if path.exists() else False,
    )


def read_doc_text(entry: DocEntry) -> str:
    """Прочитать текст документа (пусто при ошибке чтения)."""
    try:
        return entry.path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def doc_slug(rel_path: str) -> str:
    """URL-слаг документа с сохранением структуры подкаталогов (спека §11).

    ``PROJECT_STATUS_REPORT.md`` → ``project-status-report``;
    ``research/17_catalog_prices.md`` → ``research/17-catalog-prices``
    (имена в подкаталогах не конфликтуют между собой).
    """
    from services_08.reports_hub.report.summaries import slugify

    without_suffix = rel_path[:-3] if rel_path.lower().endswith(".md") else rel_path
    return "/".join(slugify(part) for part in without_suffix.split("/") if part)
