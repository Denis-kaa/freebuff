# Архитектура подсистемы Engineering Memory

**Версия:** 1.0.0-draft  
**Дата:** 2026-07-31  
**Авторы:** Коллективная память сессий Buffy  
**Статус:** рабочий черновик, дополняется  
**Принцип:** Reuse First — новые сущности создаём только если существующие не подходят.

---

## 1. Зачем нужна Engineering Memory

Engineering Memory (EM) — это подсистема коллективной памяти проекта. Она не заменяет код, тесты, changelog или архитектурную документацию. Она сохраняет то, что обычно теряется: *почему* решения принимались, *какие альтернативы* рассматривались, *что сломалось* и *чему научилась* команда.

### Проблемы, которые решает EM

- **Потеря контекста между сессиями.** AI-агенты и люди забывают детали, когда сессия прерывается.
- **Онбординг новых участников.** Человек должен понять историю проекта за часы, а не за недели чтения кода.
- **Повторяющиеся ошибки.** Без фиксации инцидентов и уроков одни и те же проблемы возвращаются.
- **Архитектурный дрейф.** Решения принимаются, но причины забываются, и система медленно разъезжается.
- **Разрыв между документацией и реальностью.** Доки описывают текущее состояние, но не историю его появления.

### Что EM не делает

- EM **не хранит код** — для этого есть git.
- EM **не заменяет changelog** — changelog фиксирует *что* изменилось, EM фиксирует *почему*.
- EM **не генерирует новые архитектурные решения** — она фиксирует уже принятые.

---

## 2. Принципы

### Reuse First

Engineering Memory не создаёт нового движка хранения. Она использует:

- **EventBus** для триггеров и интеграции.
- **MemoryEngine** для временных драфтов и сеансовой памяти.
- **KnowledgeEngine** для индексации и семантического поиска.
- **ContextManager** для связи с сессиями и чекпоинтами.
- **Файловую систему + Markdown** для долгосрочного хранения.

### Опыт важнее кода

Каждый документ EM отвечает прежде всего на вопросы:

- почему принято решение;
- какие альтернативы рассматривались;
- что оказалось ошибкой;
- чему научилась команда.

### Читаемость человеком + поискаемость ИИ

Документы EM должны быть:

- понятными человеку без дополнительных инструментов;
- индексируемыми KnowledgeEngine для RAG и семантического поиска;
- связанными между собой через теги, компоненты и timeline.

### Минимум бюрократии

EM помогает разработчику, а не добавляет работы:

- агенты генерируют черновики автоматически;
- разработчик даёт только недостающие 10% контекста;
- документы появляются как побочный эффект работы, а не как отдельная задача.

---

## 3. Архитектурный обзор

```
──────────────────────────────────────────────────────────────────────┐
│                         Engineering Memory                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Triggers   │  │   Drafts      │  │   Experience Records     │  │
│  │  (EventBus)  │  │  (MemoryEng) │  │   (Markdown + YAML)        │  │
│  └──────┬───────┘  └──────┬─────┘  └────────────┬───────────────┘  │
│         │                 │                     │                    │
│         ▼                 ▼                     ▼                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    EM Orchestrator                           │   │
│  │   (scripts/engineering_memory.py + subscribers)            │   │
│  └────────────────────────┬─────────────────────────────────────┘   │
│                           │                                         │
│         ┌─────────────────┼─────────────────┐                       │
│                          ▼                 ▼                       │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐              │
│  │ Knowledge  │    │  Project   │    │   MCP/CLI  │              │
│  │ Engine     │    │  Pulse     │    │   Tools    │              │
│  └────────────┘    └────────────┘    └────────────┘              │
└──────────────────────────────────────────────────────────────────────┘
```

### Поток данных

1. **Триггер.** EventBus фиксирует событие (`task.completed`, `system.error`, `git.commit` и др.).
2. **Черновик.** EM Orchestrator собирает контекст и создаёт драфт в `MemoryEngine(WORKING)`.
3. **Рецензия.** AI или человек дополняет недостающие детали.
4. **Сохранение.** Документ записывается в `docs/engineering-memory/` как Markdown с YAML frontmatter.
5. **Индексация.** `KnowledgeEngine` индексирует документы для поиска.
6. **Получение.** Во время новой задачи контекст из EM подаётся в промпт через `ContextManager`.

---

## 4. Сущности

### ExperienceRecord

Базовая сущность — файл Markdown с YAML frontmatter.

**Frontmatter:**

```yaml
---
id: "em-decision-router-2026-07-31"
type: "decision_journal"
title: "Выбор capability-based routing для SmartRouter"
date: "2026-07-28"
authors: ["Buffy"***REMOVED***
tags: ["architecture", "routing", "capability", "decision"***REMOVED***
related_components: ["core/router.py", "freebuff_plugin/runtime/registry.py"***REMOVED***
related_commits: ["4f5d063"***REMOVED***
related_tasks: ["TASK-001"***REMOVED***
status: "final"
---
```

**Поля:**

- `id` — уникальный идентификатор (type + slug + date).
- `type` — вид документа.
- `title` — человекочитаемое название.
- `date` — дата события/решения.
- `authors` — кто создал документ.
- `tags` — тематические теги.
- `related_components` — связанные файлы/модули.
- `related_commits` — связанные git-коммиты.
- `related_tasks` — связанные задачи.
- `status` — `draft` / `review` / `final`.

### Chronicle

Составная сущность — скомпилированный документ, основанный на наборе `ExperienceRecord`. Пример: `PROJECT_BOOK.md` собирает ключевые записи в единую историю.

### EMTrigger

Внутренняя сущность, описывающая условие автоматического создания документа.

```python
@dataclass
class EMTrigger:
    event_type: str          # например, "task.completed"
    condition: str         # "loc_changed > 500"
    document_type: str       # "task_retrospective"
    priority: str            # "low" | "medium" | "high"
```

---

## 5. Интеграция с существующими системами

### EventBus

EM подписывается на события:

- `task.completed` — потенциальный Task Retrospective.
- `task.failed` / `system.error` — потенциальный Incident Report.
- `git.commit` / `git.merge` — обновление Project Pulse и Milestone Chronicle.
- `decision.logged` (из ContextManager) — создание Decision Journal.
- `memory.stored` — связь между Memory и EM.

### MemoryEngine

Используется только для **сеансовых драфтов**. Пока агент собирает контекст, драфт живёт в `MemoryLevel.WORKING` или `MemoryLevel.PROJECT`. После финализации он перемещается в файл Markdown и удаляется из Memory.

### KnowledgeEngine

Индексирует `docs/engineering-memory/**/*.md`:

- YAML frontmatter используется для фильтрации по `type`, `tags`, `related_components`.
- Markdown body индексируется для FTS и семантического поиска.
- Связи между документами строются через общие `tags` и `related_components`.

### ContextManager

EM предоставляет `ContextManager` контекст для активной сессии:

- при старте сессии подгружаются ExperienceRecords, связанные с текущей задачей;
- в промпт добавляется краткая сводка: "Ранее мы уже пытались X, см. `em-incident-x.md`".

### Project Pulse

EM документы являются источником событий высокого уровня для Project Pulse:

- `em.document_created`;
- `em.lesson_learned`;
- `em.decision_recorded`.

### MCP / CLI

Добавляются инструменты:

- `record_decision(component, decision, why, alternatives)`;
- `record_incident(title, summary, root_cause, prevention)`;
- `record_lesson(lesson, context)`;
- `query_experience(query, limit=5)`;
- `summarize_project_timeline(since, until)`.

---

## 6. Виды документов и их жизненный цикл

### 1. Decision Journal

**Когда:** после принятия значимого архитектурного решения.  
**Структура:**

- Context — что привело к необходимости решения.
- Options Considered — рассмотренные альтернативы.
- Decision — что выбрано.
- Rationale — почему.
- Consequences — последствия и риски.

**Статус:** `draft` → `final`.

### 2. Incident Report

**Когда:** после критической ошибки, security-инцидента или крупного отказа.  
**Структура:**

- Summary — краткое описание.
- Timeline — хронология.
- Root Cause — корневая причина.
- Impact — последствия.
- Resolution — как починили.
- Lessons Learned — выводы.
- Prevention — как избежать повторения.

### 3. Task Retrospective

**Когда:** после завершения сложной задачи.  
**Структура:**

- Intent — что планировалось.
- Reality — что произошло.
- Friction — что замедлило.
- Discoveries — неожиданные находки.
- Follow-ups — что осталось.

### 4. Feature Story

**Когда:** фича эволюционирует в несколько итераций.  
**Структура:** начальная идея → итерации → текущее состояние → открытые вопросы.

### 5. Milestone Chronicle

**Когда:** завершён крупный этап/версия.  
**Структура:** цели → что сделано → ключевые решения → метрики → уроки.

### 6. Lessons Learned

**Когда:** возникает короткий, но важный вывод.  
**Структура:** утверждение + контекст + пример + последствия.

### 7. Architecture Evolution

**Когда:** доменная модель или архитектура меняется.  
**Структура:** до → причины изменения → после → влияние на другие компоненты.

### 8. Project Chronicle

**Когда:** накапливается критическая масса записей.  
**Структура:** связное повествование, собранное из отдельных ExperienceRecords.  
**Пример:** `docs/engineering-memory/PROJECT_BOOK.md`.

### Жизненный цикл документа

```
Trigger
   │
   ▼
Draft (MemoryEngine)
   │
   ▼
Review (AI/human)
   │
   ▼
Final (Markdown in docs/engineering-memory/)
   │
   ▼
Index (KnowledgeEngine)
   │
   ▼
Retrieve (ContextManager / MCP / CLI)
```

---

## 7. Архитектура хранения

### Директории

```
docs/engineering-memory/
├── ARCHITECTURE.md              # Этот документ
├── PROJECT_BOOK.md              # Сккомпилированная история проекта
├── decisions/                   # Decision Journals
├── incidents/                   # Incident Reports
├── retrospectives/              # Task Retrospectives
├── features/                    # Feature Stories
├── milestones/                  # Milestone Chronicles
├── lessons/                     # Lessons Learned
├── architecture-evolution/    # Architecture Evolution
└── templates/                   # Markdown-шаблоны для каждого типа
    ├── decision_journal.md
    ├── incident_report.md
    ├── task_retrospective.md
    └── ...
```

### Именование файлов

Формат: `{type***REMOVED***-{short-title***REMOVED***-{YYYY-MM-DD***REMOVED***.md`

Примеры:

- `decision-router-capability-2026-07-28.md`
- `incident-metrics-pyc-loss-2026-07-31.md`
- `retrospective-mcp-auth-2026-07-31.md`

### Индексация и поиск

- **KnowledgeEngine** индексирует все `.md` файлы в `docs/engineering-memory/`.
- **FTS5** обеспечивает быстрый полнотекстовый поиск.
- **TF-IDF/Vector** даёт семантический поиск.
- **YAML frontmatter** индексируется как метаданные для фильтрации.

### Теги и timeline

- Теги — в YAML frontmatter.
- Timeline — implicit из `date` поля frontmatter.
- Связи — через `related_components`, `related_commits`, `related_tasks`.

### Навигация

- `docs/INDEX.md` обновляется со ссылками на EM разделы.
- `PROJECT_BOOK.md` служит входной точкой.
- Автоматически генерируемый `docs/engineering-memory/TIMELINE.md` может отображать записи по датам.

---

## 8. Автоматическое ведение памяти

### Триггеры (EventBus)

| Событие | Условие | Создаваемый документ |
|---|---|---|
| `task.completed` | LOC изменений > 500 или duration > 1h | Task Retrospective |
| `task.failed` | 3+ повторных ошибок | Incident Report |
| `git.merge` | в `main`/`master` | Milestone Chronicle / Project Pulse |
| `decision.logged` | — | Decision Journal |
| `system.error` | severity ≥ high | Incident Report |
| `security.audit_completed` | — | Lessons Learned |

### Автоматически собираемые данные

- git diff и commit messages;
- EventBus логи сессии;
- stdout/stderr выполненных команд;
- результаты тестов;
- время выполнения задачи;
- stack trace и сообщения об ошибках;
- связанные файлы и модуификации.

### Что добавляет разработчик

- одно-два предложения о причине решения;
- ответы на уточняющие вопросы агента;
- проверка фактов.

### Предотвращение потери знаний

- **Не позволять untracked-файлам.** EM-регистратор может проверять git status и напоминать о незакоммиченных файлах.
- **Сессионные чекпоинты.** `AGENTS.md` + EM работают вместе: AGENTS.md хранит контекст сессии, EM — долгосрочную память.
- **Автоматическая индексация.** Каждый созданный документ сразу попадает в KnowledgeEngine.

---

## 9. Встраивание в процесс разработки

### Невидимые черновики

Агент ведёт EM-драфт параллельно работе. При завершении задачи он либо сохраняет его, либо отбрасывает, если событие незначительное.

### Chat-based capture

Разработчик может произнести: «Запомни, что мы выбрали X, потому что Y падал на больших данных». Агент использует `record_lesson` и создаёт или обновляет `Lessons Learned`.

### Разделение ролей

Черновики EM **генерируются агентом на основе сессии**. Человек **проверяет, дополняет и утверждает**. Ручное написание с нуля допускается только для личных заметок или уникального контекста, недоступного агенту. Агент помогает:

- избежать устаревания документов;
- сохранить единый стиль;
- не пропустить важные контекстные детали.

### Регулярный пересмотр

Раз в неделю (или по триггеру) агент:

1. Проверяет драфты в MemoryEngine.
2. Предлагает финализировать или удалить их.
3. Обновляет `PROJECT_BOOK.md` на основе новых ExperienceRecords.

---

## 10. План MVP

### Фаза 1. Хранение и шаблоны

- Создать `docs/engineering-memory/` и структуру подкаталогов.
- Создать Markdown-шаблоны для Decision Journal, Incident Report, Task Retrospective, Lessons Learned.
- Зафиксировать `PROJECT_BOOK.md` и `ARCHITECTURE.md`.

### Фаза 2. EventBus интеграция

- Создать `scripts/engineering_memory.py` с `EMEngine` и `EMOrchestrator`.
- Добавить подписчика в `scripts/event_subscribers.py`: `on_task_completed`, `on_system_error`, `on_decision_logged`.
- Реализовать создание драфтов в MemoryEngine.

### Фаза 3. MCP / CLI инструменты

- `record_decision`
- `record_incident`
- `record_lesson`
- `query_experience`

### Фаза 4. Индексация и поиск

- Настроить `KnowledgeEngine` для индексации `docs/engineering-memory/**/*.md`.
- Извлекать YAML frontmatter как метаданные.
- Добавить RAG-поиск по EM.

### Фаза 5. Интеграция с ContextManager

- При старте сессии подгружать релевантные ExperienceRecords.
- Добавлять краткую сводку в системный промпт.

---

## 11. Схема данных (YAML frontmatter)

```yaml
---
id: "em-<type>-<slug>-<YYYY-MM-DD>"
type: "decision_journal"  # или incident_report, task_retrospective и т.д.
title: "Краткое название"
date: "2026-07-31"
authors: ["Buffy"***REMOVED***
tags: ["architecture", "security", "decision"***REMOVED***
related_components:
  - "scripts/verifier.py"
  - "scripts/mcp_fastapi.py"
related_commits:
  - "c51ce49"
  - "b4c52fc"
related_tasks:
  - "TASK_SECURE_MCP_ACCESS"
status: "final"
---
```

---

## 12. Пример интеграции с кодом

```python
# scripts/engineering_memory.py (draft)
import json
from dataclasses import dataclass
***REMOVED***
from typing import Dict, List, Optional

from scripts.memory_engine import MemoryEngine, MemoryLevel


# Маппинг типа документа на поддиректорию для хранения
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


@dataclass
class ExperienceRecord:
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
        lines = [***REMOVED***
        for heading, body in self.sections.items():
            lines.append(f"## {heading***REMOVED***\n")
            lines.append(body.strip())
            lines.append("\n")
        return "\n".join(lines)


class EngineeringMemoryEngine:
    """Minimal EM engine: drafts in MemoryEngine, persists as Markdown."""

    def __init__(self, workspace_root: Path, memory_engine: MemoryEngine):
        self._root = Path(workspace_root)
        self._em_dir = self._root / "docs" / "engineering-memory"
        self._memory = memory_engine

    def create_draft(self, record: ExperienceRecord) -> str:
        draft_key = f"em_draft_{record.id***REMOVED***"
        self._memory.store(
            MemoryLevel.PROJECT,
            draft_key,
            content=record.content,
            metadata={
                "type": record.type,
                "title": record.title,
                "date": record.date,
                "authors": record.authors,
                "tags": record.tags,
                "related_components": record.related_components,
                "related_commits": record.related_commits,
                "related_tasks": record.related_tasks,
                "status": record.status,
            ***REMOVED***,
        )
        return draft_key

    def finalize(self, draft_key: str, *, reviewer: Optional[str***REMOVED*** = None) -> Path:
        """Сохраняет драфт в Markdown-файл.

        Args:
            draft_key: ключ драфта в MemoryEngine.
            reviewer: идентификатор человека, утвердившего документ.
        """
        entry = self._memory.retrieve(MemoryLevel.PROJECT, draft_key)
        if entry is None:
            raise FileNotFoundError(f"Draft not found: {draft_key***REMOVED***")

        doc_type = entry.metadata.get("type", "record")
        type_dir = TYPE_TO_DIR.get(doc_type, "records")

        target_dir = self._em_dir / type_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{doc_type***REMOVED***-{entry.key***REMOVED***.md"
        target_path = target_dir / filename

        # Обновляем статус и reviewer перед финализацией
        entry.metadata["status"***REMOVED*** = "final"
        if reviewer:
            entry.metadata["reviewer"***REMOVED*** = reviewer

        frontmatter = self._build_frontmatter(entry)
        target_path.write_text(frontmatter + entry.content, encoding="utf-8")

        # Удаляем драфт из Memory после сохранения
        self._memory.delete(MemoryLevel.PROJECT, draft_key)
        return target_path

    def _build_frontmatter(self, entry) -> str:
        meta = entry.metadata
        lines = ["---"***REMOVED***
        # json.dumps гарантирует корректную YAML-экранировку строк и списков
        lines.append(f"id: {json.dumps(entry.key)***REMOVED***")
        lines.append(f"type: {json.dumps(meta.get('type', ''))***REMOVED***")
        lines.append(f"title: {json.dumps(meta.get('title', ''))***REMOVED***")
        lines.append(f"date: {json.dumps(meta.get('date', ''))***REMOVED***")
        lines.append(f"authors: {json.dumps(meta.get('authors', [***REMOVED***))***REMOVED***")
        lines.append(f"tags: {json.dumps(meta.get('tags', [***REMOVED***))***REMOVED***")
        lines.append(f"related_components: {json.dumps(meta.get('related_components', [***REMOVED***))***REMOVED***")
        lines.append(f"related_commits: {json.dumps(meta.get('related_commits', [***REMOVED***))***REMOVED***")
        lines.append(f"related_tasks: {json.dumps(meta.get('related_tasks', [***REMOVED***))***REMOVED***")
        lines.append(f"status: {json.dumps(meta.get('status', 'final'))***REMOVED***")
        if "reviewer" in meta:
            lines.append(f"reviewer: {json.dumps(meta['reviewer'***REMOVED***)***REMOVED***")
        lines.append("---\n")
        return "\n".join(lines)
```

---

## 13. Связь с доменной моделью Workspace OS

Engineering Memory вписывается в доменную модель как мета-слой:

- **Memory** — хранит факты и сообщения.
- **Knowledge** — хранит знания и индексирует их.
- **Project Pulse** — отслеживает изменения проекта в реальном времени.
- **Engineering Memory** — сохраняет *опыт*, связанный с этими изменениями.

EM не требует новых доменных сущностей типа `Workspace` или `Process`. Она работает поверх существующих: Memory, Knowledge, EventBus, ContextManager.

---

## 14. Известные ограничения и риски

- **Overhead.** Автоматическое создание документов может порождать шум. Нужны фильтры по значимости.
- **Качество черновиков.** AI может не знать всех причин решения. Требуется человеческая проверка.
- **Дублирование с changelog.** EM должна фокусироваться на «почему», а не на «что изменилось».
- **Конфиденциальность.** EM документы могут содержать чувствительные данные. Нужно уважать `.gitignore` и секреты.

---

## 15. Ссылки

- `docs/engineering-memory/PROJECT_BOOK.md` — пример Project Chronicle.
- `pompts/promt25.md` — принципы Reuse First.
- `pompts/promt26.md` — миссия Engineering Memory.
- `scripts/memory_engine.py` — Memory Engine.
- `scripts/knowledge_engine.py` — Knowledge Engine.
- `scripts/event_bus.py` — Event Bus.
- `scripts/context_manager.py` — Context Manager.

---

*«Код говорит, что сделано. Engineering Memory говорит, почему.»*
