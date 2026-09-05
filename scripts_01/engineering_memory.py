#!/usr/bin/env python3
"""
engineering_memory.py — Engineering Memory (EM) engine для Buffy Project.

EM сохраняет опыт проекта: почему принимались решения, какие альтернативы
рассматривались, что сломалось и чему научилась команда. Она не заменяет
код или changelog, но фиксирует контекст, который обычно теряется.

Архитектура:
  - Drafts: MemoryEngine (MemoryLevel.PROJECT)
  - Finalized documents: Markdown с YAML frontmatter в docs_10/engineering-memory/
  - Search: KnowledgeEngine (FTS5 + TF-IDF)
  - Triggers: EventBus

Использование:
    from scripts_01.engineering_memory import EMEngine

    em = EMEngine(workspace_root=".")
    draft_id = em.record_decision(
        title="Use SQLite for state",
        context="Need durable local state",
        decision="SQLite",
        rationale="Zero setup, Python stdlib",
        consequences="Simple but single-node",
        authors=["Buffy"],
    )
    path = em.finalize_draft(draft_id)
    results = em.query_experience("sqlite state")
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from scripts_01.event_bus import Event
from scripts_01.memory_engine import MemoryEngine, MemoryLevel, ContentType


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
}

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
    authors: List[str]
    tags: List[str]
    related_components: List[str]
    related_commits: List[str]
    related_tasks: List[str]
    status: str
    sections: Dict[str, str]

    @property
    def content(self) -> str:
        """Собирает Markdown body из секций."""
        lines: List[str] = []
        for heading, body in self.sections.items():
            lines.append(f"## {heading}\n")
            lines.append(body.strip())
            lines.append("\n")
        return "\n".join(lines)


class EMEngineError(Exception):
    """Базовая ошибка Engineering Memory Engine."""


class DraftNotFoundError(EMEngineError):
    """Драфт не найден в MemoryEngine."""


# ═══════════════════════════════════════════════════════════════
# Template Renderer
# ═══════════════════════════════════════════════════════════════


class TemplateRenderer:
    """Рендерит Markdown-шаблоны из docs_10/engineering-memory/templates/.

    Плейсхолдеры в шаблоне: `{title}`, `{context}`, `{date}` и т.д.
    Если значение для плейсхолдера не передано, он остаётся как есть,
    что позволяет использовать шаблон и как руководство для ручного заполнения.
    """

    _LIST_FIELDS = {"authors", "tags", "related_components", "related_commits", "related_tasks"}

    def __init__(self, templates_dir: Path | None = None):
        if templates_dir is None:
            templates_dir = DEFAULT_WORKSPACE / "docs_10" / "engineering-memory" / "templates"
        self._templates_dir = Path(templates_dir)

    def render(self, template_name: str, **values: Any) -> str:
        """Рендерит шаблон, заменяя плейсхолдеры на значения.

        Args:
            template_name: имя файла шаблона (например, "decision_journal.md")
            **values: значения для плейсхолдеров

        Returns:
            Рендеренный Markdown.
        """
        template_path = self._templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        content = template_path.read_text(encoding="utf-8")

        # Автоматически заполняем дату, если не передана
        if "date" not in values:
            values["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Простая замена плейсхолдеров
        for key, value in values.items():
            placeholder = "{" + key + "]"
            if placeholder in content:
                serialized = self._serialize_value(key, value)
                content = content.replace(placeholder, serialized)

        return content

    def _serialize_value(self, key: str, value: Any) -> str:
        """Сериализует значение для вставки в Markdown-шаблон."""
        # Автоматически нормализуем строки в списки для list-полей
        if key in self._LIST_FIELDS and isinstance(value, str):
            value = [value] if value.strip() else []

        if isinstance(value, list):
            items = [json.dumps(str(item), ensure_ascii=False) for item in value]
            return "[" + ", ".join(items) + "]"
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return ""
        return str(value)

    def list_templates(self) -> List[str]:
        """Возвращает список доступных шаблонов."""
        if not self._templates_dir.exists():
            return []
        return sorted(
            p.name for p in self._templates_dir.iterdir()
            if p.suffix == ".md" and p.is_file() and p.name.lower() != "readme.md"
        )

    def available_for(self, doc_type: str) -> bool:
        """Проверяет, есть ли шаблон для данного типа документа."""
        return (self._templates_dir / f"{doc_type}.md").exists()


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
        templates_dir: str | Path | None = None,
    ):
        """Инициализирует EMEngine.

        Args:
            workspace_root: корень workspace (по умолчанию родитель scripts_01/)
            memory_engine: готовый MemoryEngine (или None для lazy create)
            knowledge_engine: готовый KnowledgeEngine (или None для lazy create)
            event_bus: готовый EventBus (или None — используется тот же, что в MemoryEngine)
        """
        if workspace_root is None:
            workspace_root = DEFAULT_WORKSPACE
        self._root = Path(workspace_root)
        self._em_dir = self._root / "docs_10" / "engineering-memory"
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

        # TemplateRenderer: lazy init
        self._template_renderer: TemplateRenderer | None = None
        self._templates_dir_override: Path | None = Path(templates_dir) if templates_dir else None

    # ── Внутренние свойства ─────────────────────────────────

    @property
    def _knowledge_engine(self) -> Any:
        """Lazy init KnowledgeEngine."""
        if self._knowledge is None:
            from scripts_01.knowledge_engine import KnowledgeEngine
            self._knowledge = KnowledgeEngine(
                workspace_root=self._root,
                event_bus=self._event_bus,
            )
            self._knowledge_owned = True
        return self._knowledge

    @property
    def template_renderer(self) -> TemplateRenderer:
        """Lazy init TemplateRenderer."""
        if self._template_renderer is None:
            templates_dir = self._templates_dir_override or self._templates_dir
            self._template_renderer = TemplateRenderer(templates_dir)
        return self._template_renderer

    # ── Public: record_* methods ──────────────────────────────

    def record_decision(
        self,
        title: str,
        decision: str,
        rationale: str,
        context: str = "",
        alternatives: str = "",
        consequences: str = "",
        authors: List[str] | None = None,
        tags: List[str] | None = None,
        related_components: List[str] | None = None,
        related_commits: List[str] | None = None,
        related_tasks: List[str] | None = None,
    ) -> str:
        """Создаёт черновик Decision Journal.

        Returns:
            draft_id — ключ драфта в MemoryEngine.
        """
        sections = {
            "Context": context or "(не указано)",
            "Decision": decision,
            "Rationale": rationale,
        }
        if alternatives:
            sections["Alternatives Considered"] = alternatives
        if consequences:
            sections["Consequences"] = consequences

        return self._create_draft(
            type="decision_journal",
            title=title,
            sections=sections,
            authors=authors,
            tags=tags or ["decision"],
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
        authors: List[str] | None = None,
        tags: List[str] | None = None,
        related_components: List[str] | None = None,
        related_commits: List[str] | None = None,
        related_tasks: List[str] | None = None,
    ) -> str:
        """Создаёт черновик Incident Report.

        Returns:
            draft_id — ключ драфта в MemoryEngine.
        """
        sections: Dict[str, str] = {
            "Summary": summary,
            "Root Cause": root_cause,
            "Resolution": resolution,
        }
        if timeline:
            sections["Timeline"] = timeline
        if impact:
            sections["Impact"] = impact
        if prevention:
            sections["Prevention"] = prevention

        return self._create_draft(
            type="incident_report",
            title=title,
            sections=sections,
            authors=authors,
            tags=tags or ["incident"],
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
        authors: List[str] | None = None,
        tags: List[str] | None = None,
        related_components: List[str] | None = None,
        related_commits: List[str] | None = None,
        related_tasks: List[str] | None = None,
    ) -> str:
        """Создаёт черновик Lessons Learned.

        Returns:
            draft_id — ключ драфта в MemoryEngine.
        """
        sections: Dict[str, str] = {
            "Lesson": lesson,
        }
        if context:
            sections["Context"] = context
        if example:
            sections["Example"] = example

        return self._create_draft(
            type="lessons_learned",
            title=title,
            sections=sections,
            authors=authors,
            tags=tags or ["lesson"],
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
        authors: List[str] | None = None,
        tags: List[str] | None = None,
        related_components: List[str] | None = None,
        related_commits: List[str] | None = None,
        related_tasks: List[str] | None = None,
    ) -> str:
        """Создаёт черновик Task Retrospective.

        Returns:
            draft_id — ключ драфта в MemoryEngine.
        """
        sections: Dict[str, str] = {
            "Intent": intent,
            "Reality": reality,
        }
        if friction:
            sections["Friction"] = friction
        if discoveries:
            sections["Discoveries"] = discoveries
        if follow_ups:
            sections["Follow-ups"] = follow_ups

        return self._create_draft(
            type="task_retrospective",
            title=title,
            sections=sections,
            authors=authors,
            tags=tags or ["retrospective"],
            related_components=related_components,
            related_commits=related_commits,
            related_tasks=related_tasks,
        )

    # ── Public: finalize / query / list ─────────────────────

    def finalize_draft(self, draft_id: str, *, reviewer: Optional[str] = None) -> Path:
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
            raise DraftNotFoundError(f"Draft not found: {draft_id}")

        meta = entry.metadata or {}
        doc_type = meta.get("type", "record")
        title = meta.get("title", "untitled")
        date = meta.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

        # Определяем целевую директорию
        type_dir = TYPE_TO_DIR.get(doc_type, "records")
        target_dir = self._em_dir / type_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Имя файла (уникальное, чтобы не перезаписать случайно)
        slug = self._slugify(title) or "untitled"
        filename = f"{doc_type}-{slug}-{date}.md"
        target_path = target_dir / filename
        counter = 1
        while target_path.exists():
            filename = f"{doc_type}-{slug}-{date}-{counter}.md"
            target_path = target_dir / filename
            counter += 1

        # Собираем frontmatter
        frontmatter = self._build_frontmatter(
            id=f"em-{doc_type}-{slug}-{date}",
            type=doc_type,
            title=title,
            date=date,
            authors=meta.get("authors", []),
            tags=meta.get("tags", []),
            related_components=meta.get("related_components", []),
            related_commits=meta.get("related_commits", []),
            related_tasks=meta.get("related_tasks", []),
            status="final",
            reviewer=reviewer,
        )

        # Decision journals receive an canonical ADR id and update the index
        if doc_type == "decision_journal" and "adr_id" not in frontmatter:
            frontmatter["adr_id"] = self._next_adr_id()

        frontmatter_str = self._frontmatter_to_string(frontmatter)

        # Содержимое документа
        body = entry.content
        full_content = frontmatter_str + "\n" + body

        # Сохраняем файл
        target_path.write_text(full_content, encoding="utf-8")

        # Обновляем индекс ADR при финализации решения
        if doc_type == "decision_journal":
            try:
                self._regenerate_decision_index()
            except Exception as exc:
                logger.warning("Failed to regenerate ADR index: %s", exc)
                self._maybe_publish("em.index_failed", {
                    "draft_id": draft_id,
                    "path": str(self._root / "docs_10" / "decisions" / "DECISIONS.md"),
                    "error": str(exc),
                })

        # Индексируем в KnowledgeEngine
        try:
            self._knowledge_engine.index_document(
                doc_id=frontmatter["id"],
                content=full_content,
                metadata={
                    "title": title,
                    "source": str(target_path.relative_to(self._root)),
                    "doc_type": doc_type,
                    "tags": ",".join(meta.get("tags", [])),
                },
            )
        except Exception as exc:
            # KnowledgeEngine не должен блокировать EM
            self._maybe_publish("em.index_failed", {
                "draft_id": draft_id,
                "path": str(target_path),
                "error": str(exc),
            })

        # Удаляем драфт из MemoryEngine
        self._memory.delete(MemoryLevel.PROJECT, draft_id)

        # Публикуем событие финализации
        self._maybe_publish("em.document_finalized", {
            "doc_id": frontmatter["id"],
            "type": doc_type,
            "title": title,
            "path": str(target_path),
            "reviewer": reviewer,
        })

        return target_path

    def query_experience(
        self,
        query: str,
        limit: int = 5,
        mode: str = "hybrid",
    ) -> List[Dict[str, Any]]:
        """Ищет по индексированным EM-документам.

        Args:
            query: поисковый запрос
            limit: максимальное количество результатов
            mode: 'keyword', 'semantic', 'hybrid'

        Returns:
            Список результатов поиска как dict.
        """
        results = self._knowledge_engine.search(query, top_k=limit * 3, mode=mode)
        em_results = [r for r in results if r.doc_id.startswith("em-")]
        return [
            {
                "doc_id": r.doc_id,
                "score": r.score,
                "snippet": r.snippet,
                "metadata": r.metadata,
            }
            for r in em_results[:limit]
        ]

    def list_drafts(self) -> List[Dict[str, Any]]:
        """Возвращает список EM-драфтов из MemoryEngine."""
        entries = self._memory.list_entries(level=MemoryLevel.PROJECT)
        drafts = []
        for entry in entries:
            meta = entry.metadata or {}
            if meta.get("em_draft"):
                drafts.append({
                    "draft_id": entry.key,
                    "type": meta.get("type"),
                    "title": meta.get("title"),
                    "date": meta.get("date"),
                    "status": meta.get("status", "draft"),
                })
        return drafts

    def discard_draft(self, draft_id: str) -> bool:
        """Удаляет драфт без финализации.

        Returns:
            True если драфт был удалён, False если не найден.
        """
        entry = self._memory.retrieve(MemoryLevel.PROJECT, draft_id)
        if entry is None:
            return False
        meta = entry.metadata or {}
        if not meta.get("em_draft"):
            return False
        return self._memory.delete(MemoryLevel.PROJECT, draft_id)

    # ── Template rendering ───────────────────────────────────

    def render_template(self, template_name: str, **values: Any) -> str:
        """Рендерит шаблон по имени.

        Args:
            template_name: имя файла шаблона (например, "decision_journal.md")
            **values: значения для плейсхолдеров

        Returns:
            Рендеренный Markdown.
        """
        return self.template_renderer.render(template_name, **values)

    def create_draft_from_template(
        self,
        template_name: str,
        title: str,
        **values: Any,
    ) -> str:
        """Создаёт драфт EM из рендеренного шаблона.

        Args:
            template_name: имя файла шаблона
            title: название документа
            **values: значения для плейсхолдеров шаблона

        Returns:
            draft_id — ключ созданного драфта.
        """
        rendered = self.render_template(template_name, **values)
        body = self._strip_frontmatter(rendered)
        doc_type = Path(template_name).stem

        # Нормализуем list-поля: строки → список, если это возможно
        def _as_list(value: Any) -> List[str]:
            if value is None:
                return []
            if isinstance(value, list):
                return [str(v) for v in value]
            if isinstance(value, str):
                return [value] if value.strip() else []
            return [str(value)]

        return self._create_draft(
            type=doc_type,
            title=title,
            content=body,
            authors=_as_list(values.get("authors")),
            tags=_as_list(values.get("tags")),
            related_components=_as_list(values.get("related_components")),
            related_commits=_as_list(values.get("related_commits")),
            related_tasks=_as_list(values.get("related_tasks")),
        )

    def list_templates(self) -> List[str]:
        """Возвращает список доступных шаблонов EM."""
        return self.template_renderer.list_templates()

    # ── Auto-trigger helpers ───────────────────────────────

    def has_auto_trigger(self, ref: str) -> bool:
        """Проверяет, был ли уже создан авто-драфт для данного ref."""
        return self._memory.retrieve(MemoryLevel.PROJECT, f"em_auto_trigger_{ref}") is not None

    def set_auto_trigger(self, ref: str) -> None:
        """Сохраняет маркер, что авто-драфт для данного ref уже создан."""
        self._memory.store(
            level=MemoryLevel.PROJECT,
            key=f"em_auto_trigger_{ref}",
            content="auto-trigger marker",
            content_type=ContentType.TEXT,
            summary=f"EM auto-trigger marker for {ref}",
            metadata={"em_auto_trigger": True, "ref": ref},
        )

    # ── Internal helpers ────────────────────────────────────

    def _create_draft(
        self,
        type: str,
        title: str,
        sections: Dict[str, str] | None = None,
        content: str | None = None,
        authors: List[str] | None = None,
        tags: List[str] | None = None,
        related_components: List[str] | None = None,
        related_commits: List[str] | None = None,
        related_tasks: List[str] | None = None,
    ) -> str:
        """Создаёт драфт в MemoryEngine и возвращает draft_id."""
        draft_id = f"em_draft_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        date = now.strftime("%Y-%m-%d")

        if content is None:
            if sections is None:
                sections = {}
            record = EMRecord(
                id=draft_id,
                type=type,
                title=title,
                date=date,
                authors=authors or ["Buffy"],
                tags=tags or [],
                related_components=related_components or [],
                related_commits=related_commits or [],
                related_tasks=related_tasks or [],
                status="draft",
                sections=sections,
            )
            content = record.content

        self._memory.store(
            level=MemoryLevel.PROJECT,
            key=draft_id,
            content=content,
            content_type=ContentType.MARKDOWN,
            summary=f"EM draft: {type} — {title}",
            metadata={
                "em_draft": True,
                "type": type,
                "title": title,
                "date": date,
                "authors": authors or ["Buffy"],
                "tags": tags or [],
                "related_components": related_components or [],
                "related_commits": related_commits or [],
                "related_tasks": related_tasks or [],
                "status": "draft",
            },
        )

        self._maybe_publish("em.draft_created", {
            "draft_id": draft_id,
            "type": type,
            "title": title,
        })

        return draft_id

    def _build_frontmatter(self, *, reviewer: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """Собирает frontmatter в виде dict (JSON-экранированного YAML)."""
        frontmatter = dict(kwargs)
        if reviewer:
            frontmatter["reviewer"] = reviewer
        return frontmatter

    def _frontmatter_to_string(self, frontmatter: Dict[str, Any]) -> str:
        """Сериализует frontmatter dict в YAML-like блок с JSON-escaped значениями."""
        lines = ["---"]
        for key, value in frontmatter.items():
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        lines.append("---")
        return "\n".join(lines)

    def _maybe_publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Публикует событие в EventBus, если он доступен."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(type=event_type, data=data, source="engineering_memory"))
        except Exception:
            pass

    @staticmethod
    def _strip_frontmatter(markdown: str) -> str:
        """Удаляет YAML frontmatter из Markdown и возвращает body.

        Args:
            markdown: Markdown с опциональным YAML frontmatter.

        Returns:
            Markdown без frontmatter (с сохранением оригинальных пустых строк).
        """
        lines = markdown.splitlines()
        if not lines or lines[0].strip() != "---":
            return markdown
        try:
            end_index = lines[1:].index("---") + 1
        except ValueError:
            return markdown
        body_lines = lines[end_index + 1:]
        return "\n".join(body_lines).strip("\n")

    @staticmethod
    def _slugify(text: str) -> str:
        """Превращает строку в безопасный для файлов slug."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-)", "", text)
        text = re.sub(r"[\s_)+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text.strip("-")[:50]

    # ── ADR index helpers ─────────────────────────────────────

    def _next_adr_id(self) -> str:
        """Возвращает следующий свободный ADR id (например, ADR-008)."""
        decisions_dir = self._em_dir / "decisions"
        max_num = 0
        if decisions_dir.exists():
            for path in decisions_dir.glob("*.md"):
                try:
                    text = path.read_text(encoding="utf-8")
                    for match in re.finditer(r"\bADR-(\d{3,})\b", text):
                        max_num = max(max_num, int(match.group(1)))
                except Exception:
                    continue
        return f"ADR-{max_num + 1:03d}"

    @staticmethod
    def _extract_adr_metadata(path: Path) -> Optional[Dict[str, str]]:
        """Извлекает метаданные ADR из файла (ручной или EM-generated формат)."""
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return None

        # EM-generated файлы с YAML frontmatter
        if text.startswith("---"):
            try:
                lines = text.splitlines()
                end_index = lines[1:].index("---") + 1
                frontmatter: Dict[str, Any] = {}
                for line in lines[1:end_index]:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()
                        try:
                            frontmatter[key] = json.loads(value)
                        except json.JSONDecodeError:
                            frontmatter[key] = value

                title = frontmatter.get("title", "").strip()
                adr_id = str(frontmatter.get("adr_id", "")).strip()
                date = str(frontmatter.get("date", "")).strip()
                status = str(frontmatter.get("status", "")).strip()
                if title and adr_id:
                    return {
                        "id": adr_id,
                        "title": title,
                        "date": date,
                        "status": status,
                        "path": str(path),
                    }
            except Exception:
                pass

        # Ручной формат: # ADR-XXX: Title, **Дата:** ..., **Статус:** ...
        h1_match = re.search(r"^# (ADR-\d{3,}):\s*(.+)$", text, re.MULTILINE)
        if h1_match:
            adr_id = h1_match.group(1)
            title = h1_match.group(2).strip()
            date_match = re.search(r"\*\*Дата:\*\*\s*(\d{4}-\d{2]-\d{2])", text)
            date = date_match.group(1) if date_match else ""
            status_match = re.search(r"\*\*Статус:\*\*\s*(.+)", text)
            status = status_match.group(1).strip() if status_match else ""
            return {
                "id": adr_id,
                "title": title,
                "date": date,
                "status": status,
                "path": str(path),
            }

        return None

    def _regenerate_decision_index(self) -> None:
        """Перегенерирует docs_10/decisions/DECISIONS.md на основе файлов в docs_10/engineering-memory/decisions/."""
        decisions_dir = self._em_dir / "decisions"
        index_path = self._root / "docs_10" / "decisions" / "DECISIONS.md"

        adrs: List[Dict[str, str]] = []
        if decisions_dir.exists():
            for path in sorted(decisions_dir.glob("*.md")):
                meta = self._extract_adr_metadata(path)
                if meta:
                    adrs.append(meta)

        def _sort_key(adr: Dict[str, str]) -> tuple[int, int, str]:
            match = re.match(r"ADR-(\d+)", adr["id"])
            if match:
                return (0, int(match.group(1)), "")
            return (1, 0, adr["id"])

        adrs.sort(key=_sort_key)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        lines: List[str] = [
            "# Decisions — Архитектурные решения Buffy Project",
            "",
            f"> **Последнее обновление:** {today}",
            "> ",
            "> Этот файл больше не хранит ADR в одном месте. Каждое решение вынесено в отдельный журнал в [`docs_10/engineering-memory/decisions/`](../engineering-memory/decisions/).",
            "",
            "---",
            "",
            "## Индекс архитектурных решений",
            "",
            "| ID | Название | Дата | Статус | Ссылка |",
            "|----|----------|------|--------|--------|",
        ]

        for adr in adrs:
            link = f"../engineering-memory/decisions/{Path(adr['path']).name}"
            title = adr["title"].replace("|", "\\|")
            status = adr.get("status", "").replace("|", "\\|")
            date = adr.get("date", "")
            lines.append(
                f"| {adr['id']} | {title} | {date} | {status} | [{Path(adr['path']).name}]({link}) |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## Почему разделение?",
            "",
            "- **Единый источник правды:** индекс хранит ссылки, а полные ADR живут в Engineering Memory.",
            "- **Повторное использование:** шаблоны Engineering Memory (`decision_journal.md`) обеспечивают единый формат.",
            "- **Автоматизация:** drift-check и другие инструменты могут сканировать отдельные ADR без парсинга одного большого файла.",
            "",
            "---",
            "",
            "_См. также [Engineering Memory](../engineering-memory/ARCHITECTURE.md) и [Project Book](../engineering-memory/PROJECT_BOOK.md)_.",
            "",
        ])

        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Engineering Memory — сохраняй опыт проекта",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts_01/engineering_memory.py record-decision "Use SQLite" \
      --decision "SQLite" --rationale "Zero setup" --context "Need state"
  python scripts_01/engineering_memory.py finalize em_draft_1234abcd
  python scripts_01/engineering_memory.py query "sqlite decision"
  python scripts_01/engineering_memory.py list-drafts
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
    p_query.add_argument("--mode", choices=["keyword", "semantic", "hybrid"],
                         default="hybrid", help="Режим поиска")

    # list-drafts
    sub.add_parser("list-drafts", help="Список драфтов EM")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    em = EMEngine()

    def _split(value: str) -> List[str]:
        return [v.strip() for v in value.split(",") if v.strip()] if value else []

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
        print(f"📝 Decision draft: {draft_id}")

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
        print(f"📝 Incident draft: {draft_id}")

    elif args.command == "record-lesson":
        draft_id = em.record_lesson(
            title=args.title,
            lesson=args.lesson,
            context=args.context,
            example=args.example,
            authors=_split(args.authors),
            tags=_split(args.tags),
        )
        print(f"📝 Lesson draft: {draft_id}")

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
        print(f"📝 Retrospective draft: {draft_id}")

    elif args.command == "finalize":
        try:
            path = em.finalize_draft(args.draft_id, reviewer=args.reviewer)
            print(f"✅ Finalized: {path}")
        except DraftNotFoundError:
            print(f" Draft not found: {args.draft_id}")

    elif args.command == "discard":
        ok = em.discard_draft(args.draft_id)
        print(f"{'🗑 Discarded' if ok else '❌ Not found'}: {args.draft_id}")

    elif args.command == "query":
        results = em.query_experience(args.query, limit=args.limit, mode=args.mode)
        if not results:
            print("🔍 No results")
        else:
            print(f"🔍 {len(results)} results:")
            for r in results:
                print(f"  [{r['score']:.4f}] {r['doc_id']}")
                print(f"     {r['snippet'][:120]}")

    elif args.command == "list-drafts":
        drafts = em.list_drafts()
        if not drafts:
            print("📭 No drafts")
        else:
            print(f"📋 {len(drafts)} drafts:")
            for d in drafts:
                print(f"  {d['draft_id']} | {d['type']} | {d['title']}")


if __name__ == "__main__":
    main()
