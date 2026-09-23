"""Сборка отчёта по проекту (спека §7.1, H3).

Факты берутся из исходных доков через extract-слой; модель — единый
контракт `ReportModel`. Нет данных → диагностика, а не пустышка.
"""

from __future__ import annotations

from pathlib import Path

from services_08.reports_hub.config import ProjectProfile
from services_08.reports_hub.extract.gitstats import collect_git_history
from services_08.reports_hub.extract.markdown import ParsedDocument, first_paragraph, parse_markdown
from services_08.reports_hub.extract.metrics import extract_metrics, summarize_metrics
from services_08.reports_hub.report.doclibrary import DocEntry, collect_docs
from services_08.reports_hub.report.model import DocCard, MetricTile, ReportModel, ReportSection, TimelineEntry
from services_08.reports_hub.report.summaries import SummaryProvider, slugify

#: Секции, считающиеся «что дальше» (спека §5.1.4).
ROADMAP_SECTION_KEYWORDS: tuple[str, ...] = (
    "дальнейшие шаги",
    "следующие шаги",
    "что дальше",
    "roadmap",
    "порядок реализации",
    "этап",
    "поток",
)

#: Секции проблем/блокеров (спека §5.1.5).
BLOCKER_SECTION_KEYWORDS: tuple[str, ...] = (
    "открытые вопросы",
    "open question",
    "блокер",
    "blocker",
    "требует ответа",
    "проблемы",
    "риск",
)

#: Закрытый набор статусов по эмодзи (спека §5.1.3).
_STATUS_MAP: tuple[tuple[str, str], ...] = (
    ("✅", "done"),
    ("🟢", "done"),
    ("🟡", "partial"),
    ("🟠", "partial"),
    ("🔴", "todo"),
    ("🔲", "todo"),
)

_TIMELINE_HEADER_HINTS: tuple[str, ...] = ("этап", "шаг", "stage")


def _loc_count(project_dir: Path, patterns: tuple[str, ...]) -> tuple[int, int]:
    """Строки Python по глобам профиля: (non-test, тесты)."""
    if not patterns:
        return 0, 0
    files: set[Path] = set()
    for pattern in patterns:
        for path in project_dir.glob(pattern):
            if path.is_file() and path.suffix == ".py":
                files.add(path)
    total = 0
    tests = 0
    for path in files:
        try:
            with path.open(encoding="utf-8", errors="ignore") as handle:
                count = sum(1 for _ in handle)
        except OSError:
            continue
        if "test" in path.name or "/tests/" in path.as_posix():
            tests += count
        else:
            total += count
    return total, tests


def _docs_by_rel(entries: list[DocEntry]) -> dict[str, DocEntry]:
    """Индекс документов по относительному пути."""
    return {entry.rel_path: entry for entry in entries}


def _pick_doc(entries: list[DocEntry], patterns: tuple[str, ...]) -> DocEntry | None:
    """Первый документ, подходящий под имя/глоб из настроек профиля."""
    for pattern in patterns:
        for entry in entries:
            if entry.rel_path == pattern or entry.filename == pattern:
                return entry
            if any(ch in pattern for ch in "*?") and entry.path.match(pattern):
                return entry
    return None


def extract_timeline(doc: ParsedDocument) -> list[TimelineEntry]:
    """Извлечь хронологию этапов из таблицы «этап/коммит/дата/результат»."""
    for section in doc.sections:
        for table in section.tables:
            header_lower = [cell.lower() for cell in table.header]
            if not any(any(hint in cell for hint in _TIMELINE_HEADER_HINTS) for cell in header_lower):
                continue
            index: dict[str, int] = {}
            for position, cell in enumerate(header_lower):
                for key in ("этап", "коммит", "дата", "результат", "суть", "что"):
                    if key in cell and key not in index:
                        index[key] = position
            entries: list[TimelineEntry] = []
            for row in table.rows:
                stage_pos = index.get("этап")
                if stage_pos is None or stage_pos >= len(row):
                    continue
                title = row[stage_pos].strip()
                if not title:
                    continue
                result_pos, commit_pos, date_pos = index.get("результат"), index.get("коммит"), index.get("дата")
                result = row[result_pos].strip() if result_pos is not None and result_pos < len(row) else ""
                commit = row[commit_pos].strip() if commit_pos is not None and commit_pos < len(row) else ""
                date = row[date_pos].strip() if date_pos is not None and date_pos < len(row) else ""
                entries.append(
                    TimelineEntry(
                        title=title.strip("`"),
                        result=result.strip("`"),
                        commit=commit.strip("`"),
                        date=date,
                    )
                )
            if entries:
                return entries
    return []


def _status_of(text: str) -> str:
    """Статус пункта по эмодзи (закрытый набор)."""
    for emoji, status in _STATUS_MAP:
        if emoji in text:
            return status
    return "unknown"

def extract_roadmap(doc: ParsedDocument) -> list[str]:
    """Собрать чек-лист «что дальше» из роадмапа (чекбоксы + строки с эмодзи)."""
    items: list[str] = []
    for section in doc.sections:
        if not any(keyword in section.title.lower() for keyword in ROADMAP_SECTION_KEYWORDS):
            continue
        for line in section.body_lines:
            stripped = line.strip()
            if stripped.startswith(("- [ ]", "- [x]", "- [X]")):
                status = "done" if stripped.startswith(("- [x]", "- [X]")) else "todo"
                items.append(f"[{status}] {stripped[5:].strip()}")
            elif stripped.startswith("|") and any(emoji in stripped for emoji, _ in _STATUS_MAP):
                cells = [cell.strip() for cell in stripped.strip("|").split("|")]
                if len(cells) >= 2 and cells[0] and not set(cells[0]) <= set("-: "):
                    items.append(f"[{_status_of(stripped)}] {cells[0]} — {' · '.join(cells[1:])}")
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def extract_blockers(docs: list[ParsedDocument]) -> list[str]:
    """Собрать открытые вопросы/блокеры из доков (текст + источник)."""
    items: list[str] = []
    for doc in docs:
        for section in doc.sections:
            if not any(keyword in section.title.lower() for keyword in BLOCKER_SECTION_KEYWORDS):
                continue
            for line in section.body_lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped[0] in "-*":
                    text = stripped.lstrip("-*0123456789. ").strip()
                    if len(text) > 3:
                        items.append(f"{text} ({doc.path} → {section.title})")
                elif stripped.startswith("**") and stripped.endswith("**") and len(stripped) < 120:
                    items.append(f"{stripped.strip('*')} ({doc.path} → {section.title})")
    return items[:40]


def _metrics_source(docs: list[DocEntry]) -> str:
    """Имя дока-источника метрик (статус-отчёт, иначе первый)."""
    for entry in docs:
        if entry.doc_type == "status":
            return entry.rel_path
    return docs[0].rel_path if docs else ""


def _exec_fallback(parsed: dict[str, ParsedDocument]) -> str:
    """Детерминированное executive summary (шапка + суть статус-дока)."""
    role = next((doc for doc in parsed.values() if doc.path.endswith("PROJECT_STATUS_REPORT.md")), None)
    if role is None:
        role = next(iter(parsed.values()), None)
    if role is None:
        return ""
    parts: list[str] = []
    for quote in role.top_quotes[:2]:
        parts.append(quote)
    for section in role.sections:
        if section.level < 2:
            continue
        text = first_paragraph(section)
        if text:
            parts.append(text)
            break
    return " ".join(parts).strip()[:600]


def doc_card_for(entry: DocEntry) -> DocCard:
    """Карточка документа из entry (используется в тестах и рендере)."""
    return DocCard(
        filename=entry.rel_path,
        doc_type=entry.doc_type,
        status_quote=entry.status_quote,
        date=entry.date,
        size_bytes=entry.size_bytes,
        summary=entry.summary,
    )


def slug_for(profile: ProjectProfile) -> str:
    """URL-слаг проекта (транслитерация кириллицы, спека §11)."""
    return slugify(profile.slug)
def build_project_report(
    profile: ProjectProfile,
    generated_at: str,
    summaries: SummaryProvider | None = None,
) -> ReportModel:
    """Собрать ReportModel проекта (спека §7.1).

    Args:
        profile: профиль проекта (``config.py``).
        generated_at: метка времени генерации (ISO).
        summaries: провайдер резюме (override/LLM); None → детерминированные.

    Returns:
        ReportModel со всеми секциями; отсутствующие источники попадают
        в ``diagnostics`` («не молча», спека §5.2).
    """
    diagnostics: list[str] = []
    docs = collect_docs(profile.path, profile.docs)
    if not docs:
        diagnostics.append("нет отчётной документации (библиотека пуста)")
    by_rel = _docs_by_rel(docs)
    parsed: dict[str, ParsedDocument] = {}
    for entry in docs:
        try:
            text = entry.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            diagnostics.append(f"источник не читается: {entry.rel_path}")
            continue
        parsed[entry.rel_path] = parse_markdown(text, path=entry.rel_path)

    metrics: list[MetricTile] = []
    if docs:
        # Метрики объявленных чисел: канонический источник — статус-отчёт
        # (спека §7.1.2); если его нет — первый доступный док.
        source_entry = next((entry for entry in docs if entry.doc_type == "status"), docs[0])
        try:
            metrics_text = source_entry.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            metrics_text = ""
            diagnostics.append(f"метрики: источник не читается ({source_entry.rel_path})")
        hits = summarize_metrics(extract_metrics(metrics_text, path=source_entry.rel_path))
        if "tests_passed" in hits:
            hit = hits["tests_passed"]
            metrics.append(MetricTile(label="тесты", value=f"{hit.value} passed", source=hit.source))
        if "mypy_clean" in hits:
            hit = hits["mypy_clean"]
            metrics.append(MetricTile(label="mypy", value=hit.value, source=hit.source))
    else:
        diagnostics.append("метрики не извлечены (нет доков-источников)")
    loc_total, loc_tests = _loc_count(profile.path, profile.loc_paths)
    if profile.loc_paths:
        source = ", ".join(profile.loc_paths)
        metrics.append(MetricTile(label="строк кода (без тестов)", value=str(loc_total), source=source))
        metrics.append(MetricTile(label="строк кода (тесты)", value=str(loc_tests), source=source))
    commits = collect_git_history(profile.path, limit=200)
    if commits:
        metrics.append(MetricTile(label="коммитов в каталоге проекта", value=str(len(commits)), source="git log"))
    else:
        diagnostics.append("git-история недоступна (commit-метрики скрыты)")

    timeline: list[TimelineEntry] = []
    sources = profile.timeline_sources or tuple(entry.rel_path for entry in docs)
    for source_name in sources:
        timeline_entry = by_rel.get(source_name) or _pick_doc(docs, (source_name,))
        if timeline_entry is None:
            diagnostics.append(f"источник хронологии не найден: {source_name}")
            continue
        doc = parsed.get(timeline_entry.rel_path)
        if doc is None:
            continue
        timeline = extract_timeline(doc)
        if timeline:
            break
    if not timeline:
        diagnostics.append("хронология этапов не найдена (нет таблицы «этап/коммит»)")

    sections: list[ReportSection] = []
    if profile.roadmap:
        roadmap_entry = by_rel.get(profile.roadmap) or _pick_doc(docs, (profile.roadmap,))
        roadmap_doc = parsed.get(roadmap_entry.rel_path) if roadmap_entry else None
        items = extract_roadmap(roadmap_doc) if roadmap_doc else []
        if not items:
            diagnostics.append(f"roadmap пуст/не найден: {profile.roadmap}")
            items = ["источник не найден или пуст"]
        sections.append(ReportSection(name="roadmap", items=items))
    if profile.blockers:
        blocker_docs: list[ParsedDocument] = []
        blocker_entry = by_rel.get(profile.blockers) or _pick_doc(docs, (profile.blockers,))
        blocker_doc = parsed.get(blocker_entry.rel_path) if blocker_entry else None
        if blocker_doc is not None:
            blocker_docs.append(blocker_doc)
        # Плюс профильные доки открытых вопросов (спека §7.1.6).
        for rel_path, doc in parsed.items():
            if rel_path != (blocker_entry.rel_path if blocker_entry else "") and "OPEN_QUESTIONS" in rel_path:
                blocker_docs.append(doc)
        items = extract_blockers(blocker_docs)
        sections.append(ReportSection(name="blockers", items=items or ["источник не найден или пуст"]))

    doc_cards: list[DocCard] = []
    for entry in docs:
        key = f"project:{profile.slug}:doc:{entry.rel_path}"
        summary = summaries.doc_summary(key, entry.summary) if summaries else entry.summary
        doc_cards.append(
            DocCard(
                filename=entry.rel_path,
                doc_type=entry.doc_type,
                status_quote=entry.status_quote,
                date=entry.date,
                size_bytes=entry.size_bytes,
                summary=summary,
            )
        )

    exec_fallback = _exec_fallback(parsed)
    exec_key = f"project:{profile.slug}:exec"
    exec_summary = summaries.exec_summary(exec_key, exec_fallback) if summaries else exec_fallback
    if not exec_summary:
        diagnostics.append("executive summary: нет данных")
        exec_summary = "Резюме недоступно: нет отчётной документации."

    role = next((entry for entry in docs if entry.doc_type == "status"), docs[0] if docs else None)
    return ReportModel(
        slug=profile.slug,
        title=profile.title,
        generated_at=generated_at,
        exec_summary=exec_summary,
        exec_source=role.rel_path if role else "",
        metrics=metrics,
        timeline=timeline,
        sections=sections,
        docs=doc_cards,
        diagnostics=diagnostics,
    )