#!/usr/bin/env python3
"""
engineering_memory.py — Engineering Memory (EM) engine для Buffy Project.

EM сохраняет опыт проекта: почему принимались решения, какие альтернативы
рассматривались, что сломалось и чему научилась команда. Она не заменяет
код или changelog, но фиксирует контекст, который обычно теряется.

Архитектура:
  - Drafts: MemoryEngine (MemoryLevel.PROJECT)
  - Finalized documents: Markdown с YAML frontmatter в docs/engineering-memory/
  - Search: KnowledgeEngine (FTS5 + TF-IDF)
  - Triggers: EventBus

Использование:
    from scripts.engineering_memory import EMEngine

    em = EMEngine(workspace_root=".")
    draft_id = em.record_decision(
        title="Use SQLite for state",
        context="Need durable local state",
        decision="SQLite",
        rationale="Zero setup, Python stdlib",
        consequences="Simple but single-node",
        authors=["Buffy"***REMOVED***,
    )
    path = em.finalize_draft(draft_id)
    results = em.query_experience("sqlite state")
"""

from __future__ import annotations

import json
***REMOVED***
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
***REMOVED***
from typing import Any, Dict, List, Optional

from scripts.event_bus import Event
from scripts.memory_engine import MemoryEngine, MemoryLevel, ContentType


# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

DEFAULT_WORKSPACE = Path(__file__).resolve().parent.parent

TYPE_TO_DIR = {
    "decision_journal": "decisions",
    "incident_report": "incidents",
    "task_retrospective": "retrospectives",
    "feature_story": "features",
    "milestone_chronicle": "milestones",
    "lessons_learned": "lessons",
    "architecture_evolution": "architecture-evolution",
    "project_chronicle": ".",
***REMOVED***

# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════


@dataclass
class EMRecord:
    """Базовая сущность Engineering Memory."""
    id: str
    type: str
    title: str
    date: str
    authors: List[str***REMOVED***
    tags: List[str***REMOVED***
    related_components: List[str***REMOVED***
    related_commits: List[str***REMOVED***
    related_tasks: List[str***REMOVED***
    status: str
    sections: Dict[str, str***REMOVED***

    @property
    def content(self) -> str:
        """Собирает Markdown body из секций."""
        lines: List[str***REMOVED*** = [***REMOVED***
        for heading, body in self.sections.items():
            lines.append(f"## {heading***REMOVED***\n")
            lines.append(body.strip())
            lines.append("\n")
        return "\n".join(lines)


class EMEngineError(Exception):
    """Базовая ошибка Engineering Memory Engine."""


class DraftNotFoundError(EMEngineError):
    """Драфт не найден в MemoryEngine."""


# ═══════════════════════════════════════════════════════════════
# Engineering Memory Engine
# ═══════════════════════════════════════════════════════════════


class EMEngine:
    """Engineering Memory Engine — сохраняет опыт проекта.

    Публичный API:
      - record_decision(title, context, decision, rationale, consequences, authors, ...)
      - record_incident(title, summary, root_cause, resolution, prevention, authors, ...)
      - record_lesson(title, lesson, context, authors, ...)
      - finalize_draft(draft_id, reviewer=None)
      - query_experience(query, limit=5)
      - list_drafts()
      - discard_draft(draft_id)
    """

    def __init__(
        self,
        workspace_root: str | Path | None = None,
        memory_engine: MemoryEngine | None = None,
        knowledge_engine: Any | None = None,
        event_bus: Any | None = None,
    ):
        """Инициализирует EMEngine.

        Args:
            workspace_root: корень workspace (по умолчанию родитель scripts/)
            memory_engine: готовый MemoryEngine (или None для lazy create)
            knowledge_engine: готовый KnowledgeEngine (или None для lazy create)
            event_bus: готовый EventBus (или None — используется тот же, что в MemoryEngine)
        """
        if workspace_root is None:
            workspace_root = DEFAULT_WORKSPACE
        self._root = Path(workspace_root)
        self._em_dir = self._root / "docs" / "engineering-memory"
        self._templates_dir = self._em_dir / "templates"

        # MemoryEngine: reuse or lazy create
        if memory_engine is not None:
            self._memory = memory_engine
            self._memory_owned = False
        else:
            self._memory = MemoryEngine(workspace_root=self._root, event_bus=event_bus)
            self._memory_owned = True

        # EventBus: reuse from memory_engine if not provided
        self._event_bus = event_bus
        if self._event_bus is None:
            self._event_bus = getattr(self._memory, "_event_bus", None)

        # KnowledgeEngine: reuse or lazy create
        self._knowledge: Any | None = knowledge_engine
        self._knowledge_owned = False

    # ── Внутренние свойства ─────────────────────────────────

    @property
    def _knowledge_engine(self) -> Any:
        """Lazy init KnowledgeEngine."""
        if self._knowledge is None:
            from scripts.knowledge_engine import KnowledgeEngine
            self._knowledge = KnowledgeEngine(
                workspace_root=self._root,
                event_bus=self._event_bus,
            )
            self._knowledge_owned = True
        return self._knowledge

    # ── Public: record_* methods ──────────────────────────────

    def record_decision(
        self,
        title: str,
        decision: str,
        rationale: str,
        context: str = "",
        alternatives: str = "",
        consequences: str = "",
        authors: List[str***REMOVED*** | None = None,
        tags: List[str***REMOVED*** | None = None,
        related_components: List[str***REMOVED*** | None = None,
        related_commits: List[str***REMOVED*** | None = None,
        related_tasks: List[str***REMOVED*** | None = None,
    ) -> str:
        """Создаёт черновик Decision Journal.

        Returns:
            draft_id — ключ драфта в MemoryEngine.
        """
        sections = {
            "Context": context or "(не указано)",
            "Decision": decision,
            "Rationale": rationale,
        ***REMOVED***
        if alternatives:
            sections["Alternatives Considered"***REMOVED*** = alternatives
        if consequences:
            sections["Consequences"***REMOVED*** = consequences

        return self._create_draft(
            type="decision_journal",
            title=title,
            sections=sections,
            authors=authors,
            tags=tags or ["decision"***REMOVED***,
            related_components=related_components,
            related_commits=related_commits,
            related_tasks=related_tasks,
        )

    def record_incident(
        self,
        title: str,
        summary: str,
        root_cause: str,
        resolution: str,
        prevention: str = "",
        timeline: str = "",
        impact: str = "",
        authors: List[str***REMOVED*** | None = None,
        tags: List[str***REMOVED*** | None = None,
        related_components: List[str***REMOVED*** | None = None,
        related_commits: List[str***REMOVED*** | None = None,
        related_tasks: List[str***REMOVED*** | None = None,
    ) -> str:
        """Создаёт черновик Incident Report.

        Returns:
            draft_id — ключ драфта в MemoryEngine.
        """
        sections: Dict[str, str***REMOVED*** = {
            "Summary": summary,
            "Root Cause": root_cause,
            "Resolution": resolution,
        ***REMOVED***
        if timeline:
            sections["Timeline"***REMOVED*** = timeline
        if impact:
            sections["Impact"***REMOVED*** = impact
        if prevention:
            sections["Prevention"***REMOVED*** = prevention

        return self._create_draft(
            type="incident_report",
            title=title,
            sections=sections,
            authors=authors,
            tags=tags or ["incident"***REMOVED***,
            related_components=related_components,
            related_commits=related_commits,
            related_tasks=related_tasks,
        )

    def record_lesson(
        self,
        title: str,
        lesson: str,
        context: str = "",
        example: str = "",
        authors: List[str***REMOVED*** | None = None,
        tags: List[str***REMOVED*** | None = None,
        related_components: List[str***REMOVED*** | None = None,
        related_commits: List[str***REMOVED*** | None = None,
        related_tasks: List[str***REMOVED*** | None = None,
    ) -> str:
        """Создаёт черновик Lessons Learned.

        Returns:
            draft_id — ключ драфта в MemoryEngine.
        """
        sections: Dict[str, str***REMOVED*** = {
            "Lesson": lesson,
        ***REMOVED***
        if context:
            sections["Context"***REMOVED*** = context
        if example:
            sections["Example"***REMOVED*** = example

        return self._create_draft(
            type="lessons_learned",
            title=title,
            sections=sections,
            authors=authors,
            tags=tags or ["lesson"***REMOVED***,
            related_components=related_components,
            related_commits=related_commits,
            related_tasks=related_tasks,
        )

    def record_task_retrospective(
        self,
        title: str,
        intent: str,
        reality: str,
        friction: str = "",
        discoveries: str = "",
        follow_ups: str = "",
        authors: List[str***REMOVED*** | None = None,
        tags: List[str***REMOVED*** | None = None,
        related_components: List[str***REMOVED*** | None = None,
        related_commits: List[str***REMOVED*** | None = None,
        related_tasks: List[str***REMOVED*** | None = None,
    ) -> str:
        """Создаёт черновик Task Retrospective.

        Returns:
            draft_id — ключ драфта в MemoryEngine.
        """
        sections: Dict[str, str***REMOVED*** = {
            "Intent": intent,
            "Reality": reality,
        ***REMOVED***
        if friction:
            sections["Friction"***REMOVED*** = friction
        if discoveries:
            sections["Discoveries"***REMOVED*** = discoveries
        if follow_ups:
            sections["Follow-ups"***REMOVED*** = follow_ups

        return self._create_draft(
            type="task_retrospective",
            title=title,
            sections=sections,
            authors=authors,
            tags=tags or ["retrospective"***REMOVED***,
            related_components=related_components,
            related_commits=related_commits,
            related_tasks=related_tasks,
        )

    # ── Public: finalize / query / list ─────────────────────

    def finalize_draft(self, draft_id: str, *, reviewer: Optional[str***REMOVED*** = None) -> Path:
        """Сохраняет драфт в Markdown-файл и индексирует его.

        Args:
            draft_id: ключ драфта в MemoryEngine.
            reviewer: идентификатор человека, утвердившего документ.

        Returns:
            Path к сохранённому Markdown-файлу.

        Raises:
            DraftNotFoundError: если драфт не найден.
        """
        entry = self._memory.retrieve(MemoryLevel.PROJECT, draft_id)
        if entry is None:
            raise DraftNotFoundError(f"Draft not found: {draft_id***REMOVED***")

        meta = entry.metadata or {***REMOVED***
        doc_type = meta.get("type", "record")
        title = meta.get("title", "untitled")
        date = meta.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

        # Определяем целевую директорию
        type_dir = TYPE_TO_DIR.get(doc_type, "records")
        target_dir = self._em_dir / type_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Имя файла (уникальное, чтобы не перезаписать случайно)
        slug = self._slugify(title) or "untitled"
        filename = f"{doc_type***REMOVED***-{slug***REMOVED***-{date***REMOVED***.md"
        target_path = target_dir / filename
        counter = 1
        while target_path.exists():
            filename = f"{doc_type***REMOVED***-{slug***REMOVED***-{date***REMOVED***-{counter***REMOVED***.md"
            target_path = target_dir / filename
            counter += 1

        # Собираем frontmatter
        frontmatter = self._build_frontmatter(
            id=f"em-{doc_type***REMOVED***-{slug***REMOVED***-{date***REMOVED***",
            type=doc_type,
            title=title,
            date=date,
            authors=meta.get("authors", [***REMOVED***),
            tags=meta.get("tags", [***REMOVED***),
            related_components=meta.get("related_components", [***REMOVED***),
            related_commits=meta.get("related_commits", [***REMOVED***),
            related_tasks=meta.get("related_tasks", [***REMOVED***),
            status="final",
            reviewer=reviewer,
        )
        frontmatter_str = self._frontmatter_to_string(frontmatter)

        # Содержимое документа
        body = entry.content
        full_content = frontmatter_str + "\n" + body

        # Сохраняем файл
        target_path.write_text(full_content, encoding="utf-8")

        # Индексируем в KnowledgeEngine
        try:
            self._knowledge_engine.index_document(
                doc_id=frontmatter["id"***REMOVED***,
                content=full_content,
                metadata={
                    "title": title,
                    "source": str(target_path.relative_to(self._root)),
                    "doc_type": doc_type,
                    "tags": ",".join(meta.get("tags", [***REMOVED***)),
                ***REMOVED***,
            )
        except Exception as exc:
            # KnowledgeEngine не должен блокировать EM
            self._maybe_publish("em.index_failed", {
                "draft_id": draft_id,
                "path": str(target_path),
                "error": str(exc),
            ***REMOVED***)

        # Удаляем драфт из MemoryEngine
        self._memory.delete(MemoryLevel.PROJECT, draft_id)

        # Публикуем событие финализации
        self._maybe_publish("em.document_finalized", {
            "doc_id": frontmatter["id"***REMOVED***,
            "type": doc_type,
            "title": title,
            "path": str(target_path),
            "reviewer": reviewer,
        ***REMOVED***)

        return target_path

    def query_experience(
        self,
        query: str,
        limit: int = 5,
        mode: str = "hybrid",
    ) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Ищет по индексированным EM-документам.

        Args:
            query: поисковый запрос
            limit: максимальное количество результатов
            mode: 'keyword', 'semantic', 'hybrid'

        Returns:
            Список результатов поиска как dict.
        """
        results = self._knowledge_engine.search(query, top_k=limit * 3, mode=mode)
        em_results = [r for r in results if r.doc_id.startswith("em-")***REMOVED***
        return [
            {
                "doc_id": r.doc_id,
                "score": r.score,
                "snippet": r.snippet,
                "metadata": r.metadata,
            ***REMOVED***
            for r in em_results[:limit***REMOVED***
        ***REMOVED***

    def list_drafts(self) -> List[Dict[str, Any***REMOVED******REMOVED***:
        """Возвращает список EM-драфтов из MemoryEngine."""
        entries = self._memory.list_entries(level=MemoryLevel.PROJECT)
        drafts = [***REMOVED***
        for entry in entries:
            meta = entry.metadata or {***REMOVED***
            if meta.get("em_draft"):
                drafts.append({
                    "draft_id": entry.key,
                    "type": meta.get("type"),
                    "title": meta.get("title"),
                    "date": meta.get("date"),
                    "status": meta.get("status", "draft"),
                ***REMOVED***)
        return drafts

    def discard_draft(self, draft_id: str) -> bool:
        """Удаляет драфт без финализации.

        Returns:
            True если драфт был удалён, False если не найден.
        """
        entry = self._memory.retrieve(MemoryLevel.PROJECT, draft_id)
        if entry is None:
            return False
        meta = entry.metadata or {***REMOVED***
        if not meta.get("em_draft"):
            return False
        return self._memory.delete(MemoryLevel.PROJECT, draft_id)

    # ── Internal helpers ────────────────────────────────────

    def _create_draft(
        self,
        type: str,
        title: str,
        sections: Dict[str, str***REMOVED***,
        authors: List[str***REMOVED*** | None = None,
        tags: List[str***REMOVED*** | None = None,
        related_components: List[str***REMOVED*** | None = None,
        related_commits: List[str***REMOVED*** | None = None,
        related_tasks: List[str***REMOVED*** | None = None,
    ) -> str:
        """Создаёт драфт в MemoryEngine и возвращает draft_id."""
        draft_id = f"em_draft_{uuid.uuid4().hex[:8***REMOVED******REMOVED***"
        now = datetime.now(timezone.utc)
        date = now.strftime("%Y-%m-%d")

        record = EMRecord(
            id=draft_id,
            type=type,
            title=title,
            date=date,
            authors=authors or ["Buffy"***REMOVED***,
            tags=tags or [***REMOVED***,
            related_components=related_components or [***REMOVED***,
            related_commits=related_commits or [***REMOVED***,
            related_tasks=related_tasks or [***REMOVED***,
            status="draft",
            sections=sections,
        )

        self._memory.store(
            level=MemoryLevel.PROJECT,
            key=draft_id,
            content=record.content,
            content_type=ContentType.MARKDOWN,
            summary=f"EM draft: {type***REMOVED*** — {title***REMOVED***",
            metadata={
                "em_draft": True,
                "type": type,
                "title": title,
                "date": date,
                "authors": record.authors,
                "tags": record.tags,
                "related_components": record.related_components,
                "related_commits": record.related_commits,
                "related_tasks": record.related_tasks,
                "status": "draft",
            ***REMOVED***,
        )

        self._maybe_publish("em.draft_created", {
            "draft_id": draft_id,
            "type": type,
            "title": title,
        ***REMOVED***)

        return draft_id

    def _build_frontmatter(self, *, reviewer: Optional[str***REMOVED*** = None, **kwargs: Any) -> Dict[str, Any***REMOVED***:
        """Собирает frontmatter в виде dict (JSON-экранированного YAML)."""
        frontmatter = dict(kwargs)
        if reviewer:
            frontmatter["reviewer"***REMOVED*** = reviewer
        return frontmatter

    def _frontmatter_to_string(self, frontmatter: Dict[str, Any***REMOVED***) -> str:
        """Сериализует frontmatter dict в YAML-like блок с JSON-escaped значениями."""
        lines = ["---"***REMOVED***
        for key, value in frontmatter.items():
            lines.append(f"{key***REMOVED***: {json.dumps(value, ensure_ascii=False)***REMOVED***")
        lines.append("---")
        return "\n".join(lines)

    def _maybe_publish(self, event_type: str, data: Dict[str, Any***REMOVED***) -> None:
        """Публикует событие в EventBus, если он доступен."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(type=event_type, data=data, source="engineering_memory"))
        except Exception:
            pass

    @staticmethod
    def _slugify(text: str) -> str:
        """Превращает строку в безопасный для файлов slug."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-***REMOVED***", "", text)
        text = re.sub(r"[\s_***REMOVED***+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text.strip("-")[:50***REMOVED***


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Engineering Memory — сохраняй опыт проекта",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts/engineering_memory.py record-decision "Use SQLite" \
      --decision "SQLite" --rationale "Zero setup" --context "Need state"
  python scripts/engineering_memory.py finalize em_draft_1234abcd
  python scripts/engineering_memory.py query "sqlite decision"
  python scripts/engineering_memory.py list-drafts
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # record-decision
    p_dec = sub.add_parser("record-decision", help="Создать Decision Journal draft")
    p_dec.add_argument("title", help="Название решения")
    p_dec.add_argument("--decision", required=True, help="Что решено")
    p_dec.add_argument("--rationale", required=True, help="Почему")
    p_dec.add_argument("--context", default="", help="Контекст")
    p_dec.add_argument("--alternatives", default="", help="Рассмотренные альтернативы")
    p_dec.add_argument("--consequences", default="", help="Последствия")
    p_dec.add_argument("--authors", default="Buffy", help="Авторы через запятую")
    p_dec.add_argument("--tags", default="", help="Теги через запятую")

    # record-incident
    p_inc = sub.add_parser("record-incident", help="Создать Incident Report draft")
    p_inc.add_argument("title", help="Название инцидента")
    p_inc.add_argument("--summary", required=True, help="Краткое описание")
    p_inc.add_argument("--root-cause", required=True, help="Корневая причина")
    p_inc.add_argument("--resolution", required=True, help="Как починили")
    p_inc.add_argument("--prevention", default="", help="Как избежать повторения")
    p_inc.add_argument("--timeline", default="", help="Хронология")
    p_inc.add_argument("--impact", default="", help="Последствия")
    p_inc.add_argument("--authors", default="Buffy", help="Авторы через запятую")
    p_inc.add_argument("--tags", default="", help="Теги через запятую")

    # record-lesson
    p_less = sub.add_parser("record-lesson", help="Создать Lessons Learned draft")
    p_less.add_argument("title", help="Название урока")
    p_less.add_argument("--lesson", required=True, help="Суть урока")
    p_less.add_argument("--context", default="", help="Контекст")
    p_less.add_argument("--example", default="", help="Пример")
    p_less.add_argument("--authors", default="Buffy", help="Авторы через запятую")
    p_less.add_argument("--tags", default="", help="Теги через запятую")

    # record-retrospective
    p_ret = sub.add_parser("record-retrospective", help="Создать Task Retrospective draft")
    p_ret.add_argument("title", help="Название задачи")
    p_ret.add_argument("--intent", required=True, help="Что планировалось")
    p_ret.add_argument("--reality", required=True, help="Что произошло")
    p_ret.add_argument("--friction", default="", help="Что замедлило")
    p_ret.add_argument("--discoveries", default="", help="Неожиданные находки")
    p_ret.add_argument("--follow-ups", default="", help="Что осталось")
    p_ret.add_argument("--authors", default="Buffy", help="Авторы через запятую")
    p_ret.add_argument("--tags", default="", help="Теги через запятую")

    # finalize
    p_fin = sub.add_parser("finalize", help="Сохранить драфт в Markdown")
    p_fin.add_argument("draft_id", help="ID драфта")
    p_fin.add_argument("--reviewer", default=None, help="Утвердивший человек")

    # discard
    p_disc = sub.add_parser("discard", help="Удалить драфт без сохранения")
    p_disc.add_argument("draft_id", help="ID драфта")

    # query
    p_query = sub.add_parser("query", help="Искать по Engineering Memory")
    p_query.add_argument("query", help="Поисковый запрос")
    p_query.add_argument("--limit", type=int, default=5, help="Количество результатов")
    p_query.add_argument("--mode", choices=["keyword", "semantic", "hybrid"***REMOVED***,
                         default="hybrid", help="Режим поиска")

    # list-drafts
    sub.add_parser("list-drafts", help="Список драфтов EM")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    em = EMEngine()

    def _split(value: str) -> List[str***REMOVED***:
        return [v.strip() for v in value.split(",") if v.strip()***REMOVED*** if value else [***REMOVED***

    if args.command == "record-decision":
        draft_id = em.record_decision(
            title=args.title,
            decision=args.decision,
            rationale=args.rationale,
            context=args.context,
            alternatives=args.alternatives,
            consequences=args.consequences,
            authors=_split(args.authors),
            tags=_split(args.tags),
        )
        print(f"📝 Decision draft: {draft_id***REMOVED***")

    elif args.command == "record-incident":
        draft_id = em.record_incident(
            title=args.title,
            summary=args.summary,
            root_cause=args.root_cause,
            resolution=args.resolution,
            prevention=args.prevention,
            timeline=args.timeline,
            impact=args.impact,
            authors=_split(args.authors),
            tags=_split(args.tags),
        )
        print(f"📝 Incident draft: {draft_id***REMOVED***")

    elif args.command == "record-lesson":
        draft_id = em.record_lesson(
            title=args.title,
            lesson=args.lesson,
            context=args.context,
            example=args.example,
            authors=_split(args.authors),
            tags=_split(args.tags),
        )
        print(f"📝 Lesson draft: {draft_id***REMOVED***")

    elif args.command == "record-retrospective":
        draft_id = em.record_task_retrospective(
            title=args.title,
            intent=args.intent,
            reality=args.reality,
            friction=args.friction,
            discoveries=args.discoveries,
            follow_ups=args.follow_ups,
            authors=_split(args.authors),
            tags=_split(args.tags),
        )
        print(f"📝 Retrospective draft: {draft_id***REMOVED***")

    elif args.command == "finalize":
        try:
            path = em.finalize_draft(args.draft_id, reviewer=args.reviewer)
            print(f"✅ Finalized: {path***REMOVED***")
        except DraftNotFoundError:
            print(f" Draft not found: {args.draft_id***REMOVED***")

    elif args.command == "discard":
        ok = em.discard_draft(args.draft_id)
        print(f"{'🗑 Discarded' if ok else '❌ Not found'***REMOVED***: {args.draft_id***REMOVED***")

    elif args.command == "query":
        results = em.query_experience(args.query, limit=args.limit, mode=args.mode)
        if not results:
            print("🔍 No results")
        else:
            print(f"🔍 {len(results)***REMOVED*** results:")
            for r in results:
                print(f"  [{r['score'***REMOVED***:.4f***REMOVED******REMOVED*** {r['doc_id'***REMOVED******REMOVED***")
                print(f"     {r['snippet'***REMOVED***[:120***REMOVED******REMOVED***")

    elif args.command == "list-drafts":
        drafts = em.list_drafts()
        if not drafts:
            print("📭 No drafts")
        else:
            print(f"📋 {len(drafts)***REMOVED*** drafts:")
            for d in drafts:
                print(f"  {d['draft_id'***REMOVED******REMOVED*** | {d['type'***REMOVED******REMOVED*** | {d['title'***REMOVED******REMOVED***")


if __name__ == "__main__":
    main()
