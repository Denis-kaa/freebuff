"""HTML-рендер Reports Hub (спека §6.4, §4.2, H3).

Все страницы — самодостаточные HTML (inline CSS/JS, только относительные
ссылки): открываются с сервера и локально по file://.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path

from services_08.reports_hub.design.tokens import build_css, theme_script
from services_08.reports_hub.extract.markdown import ParsedDocument
from services_08.reports_hub.report.doclibrary import DocEntry, doc_slug
from services_08.reports_hub.report.model import ReportModel, ReportSection
from services_08.reports_hub.report.summaries import slugify

SECTION_TITLES: dict[str, str] = {
    "roadmap": "Что дальше",
    "blockers": "Проблемы, блокеры, открытые вопросы",
}

STATUS_LABEL: dict[str, str] = {
    "done": "готово",
    "partial": "в работе",
    "todo": "не начато",
    "unknown": "",
}


@dataclass(frozen=True)
class SiteModel:
    """Модель сайта: главная-галерея + проектные страницы."""

    generated_at: str
    projects: list[ReportModel]
    no_data: tuple[tuple[str, str], ...] = ()


def esc(value: str) -> str:
    """HTML-экранирование."""
    return html.escape(value, quote=True)


def _metric_tiles(model: ReportModel) -> str:
    """Сетка плиток метрик (2 колонки на мобильном, 4 на десктопе)."""
    if not model.metrics:
        return '<p class="diag">Метрики не извлечены (источник не найден).</p>'
    tiles = []
    for tile in model.metrics:
        source = f'<div class="metric-label">{esc(tile.source)}</div>' if tile.source else ""
        tiles.append(
            f'<div class="metric"><div class="metric-label">{esc(tile.label)}</div>'
            f'<div class="metric-value">{esc(tile.value)}</div>{source}</div>'
        )
    return f'<div class="metrics">{"".join(tiles)}</div>'


def _timeline_block(model: ReportModel) -> str:
    """Хронология этапов: вертикальная линия с точками (mobile-first)."""
    if not model.timeline:
        return '<p class="diag">Хронология этапов не найдена в источниках.</p>'
    items = []
    for entry in model.timeline:
        meta = " · ".join(
            part
            for part in (
                f'<span class="commit-chip">{esc(entry.commit)}</span>' if entry.commit else "",
                esc(entry.date) if entry.date else "",
            )
            if part
        )
        result = f"<div>{esc(entry.result)}</div>" if entry.result else ""
        items.append(
            f"<li><div><strong>{esc(entry.title)}</strong></div>{result}"
            f'<div class="diag">{meta}</div></li>'
        )
    return f'<ul class="timeline">{"".join(items)}</ul>'


def _section_block(section: ReportSection) -> str:
    """Секция roadmap/blockers: чек-лист с бейджами статуса."""
    title = SECTION_TITLES.get(section.name, section.name)
    if not section.items:
        return f'<h2 class="section-title">{esc(title)}</h2><p class="diag">источник не найден</p>'
    rows = []
    for item in section.items:
        status = ""
        text = item
        if item.startswith("[") and "]" in item:
            label, _, remainder = item[1:].partition("]")
            status = label.strip()
            text = remainder.strip()
        marker = STATUS_LABEL.get(status, "")
        css = "status-done" if status == "done" else "status-open" if status == "partial" else "status-todo"
        prefix = f'<span class="{css}">{esc(marker)}</span> ' if marker else ""
        rows.append(f"<li>{prefix}{esc(text)}</li>")
    return f'<h2 class="section-title">{esc(title)}</h2><ul>{"".join(rows)}</ul>'
def _doc_grid(model: ReportModel, docs_prefix: str = "docs/") -> str:
    """Библиотека документов: карточки с резюме (клик → полный рендер)."""
    if not model.docs:
        return '<p class="diag">Документов нет.</p>'
    cards = []
    for card in model.docs:
        heavy = " · тяжёлый" if card.size_bytes > 200_000 else ""
        target = f"{docs_prefix}{doc_slug(card.filename)}.html"
        meta = " · ".join(part for part in (card.doc_type, card.date, f"{card.size_bytes} Б{heavy}") if part)
        quote = f'<p><em>{esc(card.status_quote)}</em></p>' if card.status_quote else ""
        summary = f"<p>{esc(card.summary)}</p>" if card.summary else ""
        cards.append(
            f'<a class="doc-card" href="{esc(target)}"><h3>{esc(card.filename)}</h3>'
            f'<p class="diag">{esc(meta)}</p>{quote}{summary}</a>'
        )
    return f'<div class="doc-grid">{"".join(cards)}</div>'


def _page(title: str, body: str, *, back_href: str = "", back_label: str = "") -> str:
    """Обёртка самодостаточной страницы (шапка, переключатель темы, контент)."""
    back = f'<a class="theme-btn" href="{esc(back_href)}">{esc(back_label)}</a>' if back_href else ""
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="ru"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(title)}</title><style>{build_css()}</style></head><body>"
        f'<header class="topbar"><div class="topbar-inner">{back}'
        f'<div class="topbar-title">{esc(title)}</div>'
        f'<button class="theme-btn" id="theme-btn" type="button">Авто</button>'
        f'</div></header><main class="wrap">{body}</main>'
        f"<script>{theme_script()}</script></body></html>"
    )


def render_project_page(model: ReportModel) -> str:
    """Статус-отчёт проекта (спека §7.1)."""
    body_parts = [
        f'<h1 class="large-title">{esc(model.title)}</h1>',
        '<p class="subtitle">состояние на '
        + esc(model.generated_at)
        + (f" · источник: {esc(model.exec_source)}" if model.exec_source else "")
        + "</p>",
        f'<details class="card" open><summary>Кратко</summary><p>{esc(model.exec_summary)}</p></details>',
        _metric_tiles(model),
        '<h2 class="section-title">Хронология этапов</h2>',
        _timeline_block(model),
    ]
    for section in model.sections:
        body_parts.append(_section_block(section))
    body_parts.append('<h2 class="section-title">Библиотека документов</h2>')
    body_parts.append(_doc_grid(model))
    if model.diagnostics:
        items = "".join(f"<li>{esc(item)}</li>" for item in model.diagnostics)
        body_parts.append(
            '<details class="card"><summary>Диагностика генерации</summary>'
            f'<ul class="diag">{items}</ul></details>'
        )
    return _page(model.title, "".join(body_parts), back_href="../index.html", back_label="← Все отчёты")


def render_index(site: SiteModel) -> str:
    """Главная-галерея всех отчётов (спека §6.4.1)."""
    cards = []
    for model in site.projects:
        slug = slugify(model.slug)
        numbers = " · ".join(f"{tile.label}: {tile.value}" for tile in model.metrics[:3])
        stages = f" · этапов: {len(model.timeline)}" if model.timeline else ""
        cards.append(
            f'<a class="doc-card" href="projects/{esc(slug)}/index.html"><h3>{esc(model.title)}</h3>'
            f"<p>{esc(numbers)}{esc(stages)}</p>"
            f'<p class="diag">{esc(model.exec_summary[:180])}</p></a>'
        )
    no_data = [
        f'<div class="doc-card"><h3>{esc(name)}</h3><p class="diag">нет данных: {esc(reason)}</p></div>'
        for name, reason in site.no_data
    ]
    body = [
        '<h1 class="large-title">Отчёты</h1>',
        f'<p class="subtitle">сгенерировано {esc(site.generated_at)} · проектов с отчётами: {len(site.projects)}</p>',
        f'<div class="doc-grid">{"".join(cards)}</div>',
    ]
    if no_data:
        body.append('<h2 class="section-title">Без отчётных данных</h2>')
        body.append(f'<div class="doc-grid">{"".join(no_data)}</div>')
    return _page("Отчёты", "".join(body))
def render_doc_page(entry: DocEntry, doc: ParsedDocument) -> str:
    """Полный рендер Markdown-документа (спека §7.2)."""
    parts = [f'<h1 class="large-title">{esc(entry.filename)}</h1>']
    if entry.status_quote:
        parts.append(f'<p class="subtitle">{esc(entry.status_quote)}</p>')
    for section in doc.sections:
        if section.level >= 1 and section.title:
            parts.append(f'<h2 class="section-title">{esc(section.title)}</h2>')
        for table in section.tables:
            head = "".join(f"<th>{esc(cell)}</th>" for cell in table.header)
            rows = "".join(
                "<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>" for row in table.rows
            )
            parts.append(
                f'<table class="stages"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>'
            )
        if section.body_text():
            parts.append(f'<pre class="diag">{esc(section.body_text())}</pre>')
    return _page(entry.filename, "".join(parts), back_href="../index.html", back_label="← Назад")


def write_site(site_root: Path, site: SiteModel, doc_pages: dict[str, str]) -> None:
    """Записать сайт на диск + `manifest.json` (observability, спека §4.1).

    Args:
        site_root: каталог вывода (`site/`).
        site: модель сайта.
        doc_pages: карта «<slug-проекта>/<html-слаг>.html» → содержимое страницы.
    """
    site_root.mkdir(parents=True, exist_ok=True)
    (site_root / "index.html").write_text(render_index(site), encoding="utf-8")
    for model in site.projects:
        slug = slugify(model.slug)
        project_dir = site_root / "projects" / slug
        docs_dir = project_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "index.html").write_text(render_project_page(model), encoding="utf-8")
        for rel_path, content in doc_pages.items():
            prefix = f"{slug}/"
            if not rel_path.startswith(prefix):
                continue
            target = docs_dir / rel_path[len(prefix) :]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    manifest = {
        "generated_at": site.generated_at,
        "projects": [
            {
                "slug": model.slug,
                "title": model.title,
                "metrics": len(model.metrics),
                "timeline_stages": len(model.timeline),
                "docs": len(model.docs),
                "diagnostics": len(model.diagnostics),
            }
            for model in site.projects
        ],
        "no_data": [{"slug": name, "reason": reason} for name, reason in site.no_data],
    }
    (site_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )