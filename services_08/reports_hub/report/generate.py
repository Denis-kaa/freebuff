"""Оркестрация генерации сайта Reports Hub (спека §14.3–14.4, H3).

Собирает модели по профилям проектов, рендерит страницы и пишет сайт.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from services_08.reports_hub.config import ProjectProfile, discover_projects
from services_08.reports_hub.extract.markdown import parse_markdown
from services_08.reports_hub.report.doclibrary import DocEntry, collect_docs, doc_slug
from services_08.reports_hub.report.model import ReportModel
from services_08.reports_hub.report.project_report import build_project_report
from services_08.reports_hub.report.render import SiteModel, render_doc_page, write_site
from services_08.reports_hub.report.summaries import DeterministicProvider, OverrideProvider, SummaryProvider, slugify


@dataclass
class GenerateResult:
    """Результат генерации: что записано + диагностика."""

    site_root: Path
    projects: int
    no_data: int
    docs_rendered: int
    diagnostics: list[str]
    orphans: list[str]


def _now_iso() -> str:
    """Текущее время в ISO-формате (UTC, секунды)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _provider(summaries_path: Path | None) -> tuple[SummaryProvider, OverrideProvider | None]:
    """Провайдер резюме: override (если файл есть) поверх детерминированного."""
    if summaries_path is None:
        return DeterministicProvider(), None
    override = OverrideProvider.from_file(summaries_path)
    return override, override


def _doc_pages(profile: ProjectProfile, slug: str) -> tuple[dict[str, str], list[str]]:
    """Собрать карту страниц документов проекта: ключ — «<slug>/<doc>.html»."""
    pages: dict[str, str] = {}
    diagnostics: list[str] = []
    for entry in collect_docs(profile.path, profile.docs):
        try:
            text = entry.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            diagnostics.append(f"источник не читается: {entry.rel_path}")
            continue
        doc = parse_markdown(text, path=entry.rel_path)
        key = f"{slug}/{doc_slug(entry.rel_path)}.html"
        pages[key] = render_doc_page(entry, doc)
    return pages, diagnostics


def generate_site(
    projects_root: Path,
    site_root: Path,
    *,
    project_slug: str | None = None,
    include_platform: bool = False,
    summaries_path: Path | None = None,
) -> GenerateResult:
    """Сгенерировать сайт отчётов (спека §14.3).

    Args:
        projects_root: каталог `projects_17/`.
        site_root: каталог вывода `site/`.
        project_slug: конкретный проект; None → все с отчётностью.
        include_platform: отчёт платформы (H5; в H3 игнорируется с диагностикой).
        summaries_path: путь к `summaries.json` (override-резюме).

    Returns:
        GenerateResult с количеством проектов/страниц и диагностикой.
    """
    provider, override = _provider(summaries_path)
    diagnostics: list[str] = []
    if include_platform:
        diagnostics.append("отчёт платформы — этап H5 (в H3 не генерируется)")

    profiles = discover_projects(projects_root)
    if project_slug is not None:
        profiles = [p for p in profiles if p.slug == project_slug]
        if not profiles:
            diagnostics.append(f"проект не найден: {project_slug}")

    models: list[ReportModel] = []
    no_data: list[tuple[str, str]] = []
    doc_pages: dict[str, str] = {}
    for profile in profiles:
        if profile.excluded:
            continue
        if profile.invalid_reason:
            no_data.append((profile.slug, f"профиль невалиден: {profile.invalid_reason}"))
            continue
        if not profile.has_report_docs:
            no_data.append((profile.slug, "нет отчётной документации"))
            continue
        model = build_project_report(profile, generated_at=_now_iso(), summaries=provider)
        models.append(model)
        slug = slugify(profile.slug)
        pages, page_diagnostics = _doc_pages(profile, slug)
        doc_pages.update(pages)
        diagnostics.extend(page_diagnostics)

    site = SiteModel(generated_at=_now_iso(), projects=models, no_data=tuple(no_data))
    write_site(site_root, site, doc_pages)
    orphans = override.orphans() if override else []
    if orphans:
        diagnostics.append(f"осиротевшие ключи summaries: {', '.join(orphans)}")
    return GenerateResult(
        site_root=site_root,
        projects=len(models),
        no_data=len(no_data),
        docs_rendered=len(doc_pages),
        diagnostics=diagnostics,
        orphans=orphans,
    )