"""scripts_01/research_web.py — Web Research capability (Tool: ``research_web``).

Missing Capability #6 (FACTORY_FORGE_ARCHITECTURE_V1.md §20, pompts_11/075_04_research_web_capability.md).
Research Factory → Research Forge → Web Research Engine. Результат: Research
Report (research_report.md) — синтез веб-исследования по теме.

Безопасность: веб-запросы через ``httpx`` с таймаутами, без ``shell=True`` /
``os.system`` / curl-инжекта. Fail-safe: сбой источника → warning + continue;
нет сети → degraded-отчёт ``sources_checked: 0``, exit 0.

Usage::

    python scripts_01/research_web.py "конкуренты Workspace OS" --out research_report.md
    python scripts_01/research_web.py "тема" --json --max-sources 5 --timeout 15
    python scripts_01/research_web.py "тема" --no-save
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup


DEFAULT_OUT = "research_report.md"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "research_web/1.0 (Freebuff Workspace OS; local-first)"
)
# Ключи JSON-схемы DoD (075_04_research_web_capability §5): query, sources[], synthesis, evidence_checked, degraded
JSON_SCHEMA_KEYS = ("query", "sources", "synthesis", "evidence_checked", "degraded")


@dataclass
class Source:
    """Один найденный источник: URL + заголовок + фрагмент."""

    url: str
    title: str = ""
    snippet: str = ""
    verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "verified": self.verified,
        }


@dataclass
class ResearchReport:
    """Результат веб-исследования (Research Report)."""

    query: str
    sources: list[Source] = field(default_factory=list)
    synthesis: str = ""
    evidence_checked: int = 0
    degraded: bool = False
    warnings: list[str] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def sources_checked(self) -> int:
        return len(self.sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "sources": [s.to_dict() for s in self.sources],
            "synthesis": self.synthesis,
            "evidence_checked": self.evidence_checked,
            "degraded": self.degraded,
            "warnings": self.warnings,
            "sources_checked": self.sources_checked,
            "generated_at": self.generated_at,
        }

    def to_markdown(self) -> str:
        """Markdown-отчёт (файл research_report.md по умолчанию)."""
        lines = [
            "# Research Report",
            "",
            f"**Запрос:** {self.query}",
            f"**Сгенерирован:** {self.generated_at}",
            f"**Источников проверено:** {self.sources_checked}",
            f"**Degraded:** {'да' if self.degraded else 'нет'}",
            "",
            "## Цель исследования",
            "",
            f"Веб-исследование по запросу «{self.query}»: сбор источников, "
            "проверка evidence и синтез выводов.",
            "",
            "## Найденные источники",
            "",
        ]
        if not self.sources:
            lines.append("_Источники не найдены (нет сети или пустой результат)._")
        for s in self.sources:
            lines.append(f"- **[{s.title or s.url}]({s.url})** — {s.snippet or '(без фрагмента)'}")
            if s.verified:
                lines.append("  - ✅ подтверждён независимой загрузкой")
        lines += [
            "",
            "## Проверка evidence",
            "",
            f"Подтверждено независимой загрузкой источников: **{self.evidence_checked}**.",
            "",
            "## Синтез",
            "",
            self.synthesis or "_Синтез недоступен (нет источников)._",
            "",
            "## Ограничения / непроверенное",
            "",
        ]
        if self.warnings:
            for w in self.warnings:
                lines.append(f"- ⚠️ {w}")
        else:
            lines.append("_Нет._")
        lines.append("")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Web layer (переопределяется в тестах — модуль остаётся сеть-независимым)
# ═══════════════════════════════════════════════════════════════════


def search_web(query: str, max_sources: int = 10, timeout: float = 10.0) -> list[Source]:
    """Поиск через DuckDuckGo HTML (без API-ключа). Возвращает список источников.

    Raises:
        httpx.HTTPError: сетевая ошибка / не-2xx ответ.
    """
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": USER_AGENT}
    params = {"q": query}
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url, params=params, headers=headers)
        resp.raise_for_status()
    return _parse_ddg_results(resp.text, max_sources)


def fetch_page(url: str, timeout: float = 10.0) -> str:
    """Загрузить страницу источника. Возвращает HTML. Raises на любом сбое."""
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
    return resp.text


def _parse_ddg_results(html: str, max_sources: int) -> list[Source]:
    """Разобрать HTML-выдачу DuckDuckGo в список Source (URL + title + snippet)."""
    soup = BeautifulSoup(html, "html.parser")
    sources: list[Source] = []
    for result in soup.select(".result"):
        a = result.select_one(".result__a")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        url = _extract_ddg_url(href) or href
        if not url.startswith(("http://", "https://")):
            continue
        snippet_el = result.select_one(".result__snippet")
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
        sources.append(Source(url=url, title=a.get_text(" ", strip=True), snippet=snippet[:300]))
        if len(sources) >= max_sources:
            break
    return sources


def _extract_ddg_url(href: str) -> str:
    """DuckDuckGo оборачивает ссылки в /l/?uddg=<urlencoded> — вернуть реальный URL."""
    if "uddg=" not in href:
        return href
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(href)
    uddg = parse_qs(parsed.query).get("uddg")
    if uddg:
        return uddg[0]
    return href


def _extract_snippet(html: str, max_chars: int = 300) -> str:
    """Вытащить читаемый текстовый фрагмент из HTML страницы."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return " ".join(text.split())[:max_chars]


# ═══════════════════════════════════════════════════════════════════
# Evidence + synthesis
# ═══════════════════════════════════════════════════════════════════


def _significant_terms(text: str, min_len: int = 4) -> set[str]:
    """Значимые термы текста (нижний регистр, без стоп-слов/цифр)."""
    stop = {
        "this", "that", "with", "from", "they", "have", "were", "will", "their",
        "there", "what", "about", "into", "them", "then", "these", "those",
        "этот", "это", "для", "что", "как", "при", "его", "ее", "её", "все",
        "они", "также", "можно", "такое", "очень", "уже", "еще", "ещё", "или",
    }
    words = set()
    for w in text.lower().split():
        w = "".join(ch for ch in w if ch.isalnum())
        if len(w) >= min_len and w not in stop and not w.isdigit():
            words.add(w)
    return words


def _count_evidence(sources: list[Source], query: str) -> int:
    """Сколько источников независимо подтверждено (CON-55 anti-hallucination).

    Evidence = количество verified-источников, чей фрагмент разделяет хотя бы
    один значимый терм с другим источником (пересечение по смыслу).
    """
    if not sources:
        return 0
    term_sets = [_significant_terms(f"{s.title} {s.snippet}") for s in sources]
    counted = 0
    for i, s in enumerate(sources):
        if not s.verified:
            continue
        for j, other in enumerate(term_sets):
            if i == j:
                continue
            if term_sets[i] & other:
                counted += 1
                break
    return counted


def _synthesize(query: str, sources: list[Source], warnings: list[str]) -> str:
    """Простой детерминированный синтез по фрагментам (без LLM-вызова)."""
    if not sources:
        return (
            f"Источники по запросу «{query}» не найдены. Проверь сеть/запрос "
            "или запусти с --max-sources больше (CON-55: не делаем выводов без evidence)."
        )
    top = sources[:5]
    parts = [f"По запросу «{query}» найдено {len(sources)} источников."]
    parts.append("Ключевые материалы:")
    for s in top:
        title = s.title or s.url
        parts.append(f"- {title} — {s.snippet[:120] or '(без фрагмента)'}")
    if len(sources) > 5:
        parts.append(f"- … и ещё {len(sources) - 5}.")
    if warnings:
        parts.append(f"⚠️ Часть источников не проверена: {len(warnings)} предупреждений.")
    return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════
# Main API (075_04_research_web_capability §3.1)
# ═══════════════════════════════════════════════════════════════════


def research_web(
    query: str,
    out: str | None = None,
    max_sources: int = 10,
    timeout: float = 10.0,
    save: bool = True,
    *,
    corpus_dir: Optional[Path] = None,
    persist_corpus: bool = True,
) -> ResearchReport:
    """Выполнить веб-исследование. Возвращает ResearchReport.

    Args:
        query: тема/запрос исследования.
        out: путь файла отчёта (default research_report.md при save=True).
        max_sources: лимит источников.
        timeout: таймаут на запрос (сек).
        save: записать ли markdown-отчёт (False = dry-run/--no-save).
        corpus_dir: ROOT-каталог corpus (default ``None`` → ``DEFAULT_CORPUS_DIR``)
            — путь передаётся в ``corpus_persistence.persist(..., root=corpus_dir)``.
            Используйте ``tmp_path`` в тестах для hermetic setup.
        persist_corpus: persist-ить ли успешные fetch в corpus (default True).
            Fail-safe per ADR-016: ошибки persist → warning + continue,
            БЕЗ exception наружу.

    Fail-safe: сбой поиска/источника → warning + continue; нет сети →
    degraded-отчёт с ``sources_checked: 0``.
    """
    warnings: list[str] = []
    query = (query or "").strip()

    try:
        sources = search_web(query, max_sources=max_sources, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — fail-safe по дизайну
        warnings.append(f"поиск недоступен: {type(exc).__name__}: {exc}")
        sources = []

    # Проверка каждого источника (fail-safe на битый URL)
    for src in sources:
        try:
            html = fetch_page(src.url, timeout=timeout)
            src.verified = True
            if not src.snippet:
                src.snippet = _extract_snippet(html)
            # ── Corpus persistence (ADR-016 fail-safe: never break main flow).
            # Default ON (auto-track fetches), opt-out via persist_corpus=False.
            # Errors → warnings.append + continue, NEVER propagate as exception.
            if persist_corpus:
                try:
                    # Lazy import: avoid hard dependency on corpus_persistence module
                    # (если его нет в deployment — graceful skip).
                    from scripts_01.corpus_persistence import persist
                    persist(
                        url=src.url, source="research_web",
                        title=src.title or None,
                        metadata={"status": 200, "query": query},
                        root=corpus_dir,
                    )
                except Exception as exc:  # noqa: BLE001 — ADR-016 fail-safe
                    warnings.append(
                        f"corpus_persistence error ({src.url}): "
                        f"{type(exc).__name__}: {exc}"
                    )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"источник не подтверждён ({src.url}): {type(exc).__name__}: {exc}")

    degraded = len(sources) == 0
    evidence_checked = _count_evidence(sources, query)
    synthesis = _synthesize(query, sources, warnings)

    report = ResearchReport(
        query=query,
        sources=sources,
        synthesis=synthesis,
        evidence_checked=evidence_checked,
        degraded=degraded,
        warnings=warnings,
    )

    if save:
        target = out or DEFAULT_OUT
        _write_report(report, target)

    _emit_events(report)
    return report


def _write_report(report: ResearchReport, target: str) -> None:
    """Записать markdown-отчёт (идемпотентно, atomic-запись)."""
    

    path = Path(target)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(report.to_markdown(), encoding="utf-8")
    tmp.replace(path)


# ═══════════════════════════════════════════════════════════════════
# Observability (best-effort, никогда не валит основной поток)
# ═══════════════════════════════════════════════════════════════════


def _emit_events(report: ResearchReport) -> None:
    """Записать событие в EventBus + Learning Loop (best-effort, не блокирует)."""
    try:
        from scripts_01.event_bus import Event, EventBus

        EventBus().publish(
            Event(
                type="research_web.completed",
                data={
                    "query": report.query,
                    "sources_checked": report.sources_checked,
                    "evidence_checked": report.evidence_checked,
                    "degraded": report.degraded,
                },
                source="research_web",
            )
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        from core_02.memory_store import MemoryStore

        MemoryStore().record_learning_event(
            trigger_id="research_web",
            context_snapshot={
                "query": report.query,
                "sources_checked": report.sources_checked,
                "degraded": report.degraded,
            },
            outcome="success" if not report.degraded else "neutral",
        )
    except Exception:  # noqa: BLE001
        pass


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Web Research capability (Tool: research_web) — Research Factory"
    )
    parser.add_argument("query", help="тема/запрос исследования")
    parser.add_argument("--out", default=None, help=f"файл отчёта (default {DEFAULT_OUT})")
    parser.add_argument("--json", action="store_true", help="stdout в JSON (для Scenario Engine/API)")
    parser.add_argument("--max-sources", type=int, default=10, help="лимит источников (default 10)")
    parser.add_argument("--timeout", type=float, default=10.0, help="таймаут на запрос, сек (default 10)")
    parser.add_argument("--no-save", action="store_true", help="без записи файла (dry-run)")
    parser.add_argument(
        "--no-corpus", action="store_true",
        help="не persist-ить URLs в corpus_persistence (default: persist ON)",
    )
    parser.add_argument(
        "--corpus-dir", type=Path, default=None,
        help="override DEFAULT_CORPUS_DIR (default=data_13/corpus); полезно в скриптах и тестах",
    )
    args = parser.parse_args()

    report = research_web(
        args.query,
        out=args.out,
        max_sources=args.max_sources,
        timeout=args.timeout,
        save=not args.no_save,
        corpus_dir=args.corpus_dir,
        persist_corpus=not args.no_corpus,
    )

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(report.to_markdown())
    return 0


if __name__ == "__main__":
    sys.exit(main())
