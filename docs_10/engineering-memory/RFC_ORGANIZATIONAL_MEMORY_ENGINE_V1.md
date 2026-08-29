# RFC: Organizational Memory Engine v1

**Статус:** 📋 RFC (ожидает утверждения)
**Автор:** Buffy (promt51 → 051_14_organizational_memory_engine)
**Дата:** 2026-08-05
**Основание:** [pompts_11/051_14_organizational_memory_engine.md***REMOVED***(../../pompts_11/051_14_organizational_memory_engine.md) — user directive
**Предшественник:** [IDEAS.md §14 — Lessons Memory Engine***REMOVED***(../../docs_10/decisions/IDEAS.md) (💡 Idea, отклонено в пользу данного RFC)

---

## 1. Architectural Fit Check (AFC)

### 1.1 Что уже существует

| Компонент | Расположение | API/Схема | Статус |
|-----------|-------------|-----------|--------|
| **Knowledge Engine** | `scripts_01/knowledge_engine.py` (851 стр.) | `FtsIndex`, `TfidfIndex`, `SemanticIndex` (SVD/LSA), `KnowledgeEngine` (unified API: `search(capabilities)`, `index_document`, `rebuild_index`, `graph_search`) | ✅ Production |
| **Graph Index** | `scripts_01/graph_index.py` (400+ стр.) | `GraphIndex`: nodes (`graph_nodes`), edges (`graph_edges`), 7 типов связей, BFS shortest_path, subgraph, traverse, auto_discover | ✅ Production |
| **FTS5 индекс** | `context_12/knowledge/index.db::docs_fts` | BM25 через SQLite FTS5, таблица `doc_meta` (doc_id, title, source, doc_type, char_count) | ✅ Production |
| **TF-IDF векторы** | `context_12/knowledge/vectors.npy` + `vocab.json` | numpy float32, косинусная близость | ✅ Production |
| **SVD/LSA слой** | `context_12/knowledge/svd_*.npy` + `svd_meta.json` | torch/numpy SVD, n_components=100, document embeddings | ✅ Production |
| **arch_decisions** | `data_13/context.db::arch_decisions` | id, session_id, title, context, decision, alternatives, rationale, consequences, status (default 'accepted'), created_at, updated_at | ✅ Готов (0 записей) |
| **event_log** | `context_12/events.db::event_log` | event_id, event_type, source, data_json, timestamp, delivered_to | ✅ Production |
| **event_store** | `context_12/events.db::event_store` | + correlation_id, session_id, project, user_id, metadata_json | ✅ Production |
| **event_fts** | `context_12/events.db::event_fts` | FTS5 поверх event_type + data_json | ✅ Production |
| **LESSONS.md** | `core_02/LESSONS.md` (782 стр.) | ~46 уроков: CON-* (подтверждённые), CAN-* (кандидаты), ANTI-* (антипаттерны) — markdown | ✅ Production (ручной) |
| **Memory Engine** | `scripts_01/memory_engine.py` | `MemoryEngine`: working/project/knowledge/personal/archive уровни | ✅ Production |
| **Промт-диспетчер** | `scripts_01/prompt_dispatcher.py` | очередь задач, pgrep pre-check, backoff, dispatch_all | ✅ Production |
| **Event Bus** | `scripts_01/event_bus.py` | publish/subscribe, используется knowledge_engine | ✅ Production |

### 1.2 Что необходимо расширить

| Потребность | Текущее состояние | Что нужно |
|------------|-------------------|-----------|
| Единая модель знаний | ADR → arch_decisions, уроки → markdown, документы → FTS | Универсальная таблица `knowledge_objects` |
| Типизация знаний | Неявная (CON-/ADR/...) | Поле `kind` с enum типов |
| Жизненный цикл | Нет (статусы только у arch_decisions) | `status` + `lifecycle_stage` |
| Метрики опыта | Нет | `confidence_score`, `usage_count`, `success/failure_count` |
| Learning Loop | Нет | Механизм обратной связи |
| Experience Analytics | Нет | Аналитические запросы |
| Связи между знаниями | Только graph_index (между doc_id) | Прямые связи knowledge_object↔knowledge_object |
| Событийная лента знаний | event_log (сырые события) | Связка event→observation→candidate→knowledge |

### 1.3 Что нельзя ломать

- ❌ **`knowledge_engine.py` API** — используется другими компонентами (prompt_dispatcher, router)
- ❌ **`graph_index.py` API** — `add_edge`, `get_related`, `shortest_path`, `subgraph`, `traverse`
- ❌ **`data_13/context.db`** — 10+ таблиц (sessions, messages, workspaces, invariants, ...)
- ❌ **`context_12/events.db`** — логирование платформы
- ❌ **`core_02/LESSONS.md`** — должен оставаться читаемым до миграции, после миграции — read-only архив
- ❌ **Структура `context_12/knowledge/`** — FTS5, TF-IDF, SVD должны продолжать работать

### 1.4 Какие компоненты становятся частью Organizational Memory

```
Organizational Memory Engine
├── Memory Store          ← data_13/context.db (новая таблица knowledge_objects + связи)
├── Knowledge Objects     ← универсальная модель (CON-, ADR, Pattern, Rule, ...)
├── Knowledge Graph       ← scripts_01/graph_index.py (GraphIndex)
├── Semantic Layer        ← scripts_01/knowledge_engine.py (FTS5 + TF-IDF + SVD)
├── Event Pipeline        ← context_12/events.db (event_log → observation → candidate)
├── Learning Loop         ← новый компонент (feedback → confidence → update)
└── Experience Analytics  ← новый компонент (SQL-запросы + отчёты)
```

---

## 2. Общая архитектура

### 2.1 Принципы

1. **Память организации, не уроки.** Центральная сущность — `Knowledge Object`, а не `Lesson`. Урок — лишь один из типов.
2. **Эволюция, не революция.** Все изменения — ADDITIVE. Не удаляем, не переписываем существующие таблицы/API. CAN-16 anti-rewriting.
3. **Единая БД.** Всё в `data_13/context.db` — рядом с arch_decisions, sessions, workspaces.
4. **Семантический слой — существующий.** Knowledge Engine уже умеет keyword/semantic/hybrid — расширяем индексацию, не переписываем движок.
5. **Миграция без даунтайма.** Фазы миграции независимы; платформа работает между фазами.

### 2.2 Слои архитектуры

```
┌─────────────────────────────────────────────────────────┐
│                  EXPERIENCE ANALYTICS                    │
│   usage_stats, contradiction_detection, decay_monitor   │
├─────────────────────────────────────────────────────────┤
│                     LEARNING LOOP                        │
│   feedback → confidence_update → validation → re-review  │
├─────────────────────────────────────────────────────────┤
│                    SEMANTIC LAYER                        │
│   FTS5 (keyword) + TF-IDF (vector) + SVD/LSA (semantic) │
│   KnowledgeEngine.search(knowledge_objects, ...)        │
├─────────────────────────────────────────────────────────┤
│                    KNOWLEDGE GRAPH                       │
│   GraphIndex: supports, contradicts, supersedes, ...    │
│   Новые rel_types + knowledge_object узлы                │
├─────────────────────────────────────────────────────────┤
│                    MEMORY STORE                          │
│   knowledge_objects + knowledge_tags + knowledge_links   │
│   + knowledge_events (в data_13/context.db)              │
├─────────────────────────────────────────────────────────┤
│                  EVENT PIPELINE                          │
│   event_log → Observation → Candidate → Knowledge Object │
└─────────────────────────────────────────────────────────┘
```

### 2.3 Потоки данных

```
СЫРОЕ СОБЫТИЕ (event_log/event_store)
    │
    ▼
OBSERVATION (автоматически: кластеризация повторяющихся событий)
    │
    ▼
CANDIDATE (полуавтоматически: требует review человеком)
    │
    ▼
KNOWLEDGE OBJECT (подтверждён, индексирован, активен)
    │
    ▼
FEEDBACK (автоматически: usage_count, success/failure)
    │
    ▼
VALIDATION (периодически: confidence drop → re-review)
```

---

## 3. Универсальная модель Knowledge Object

### 3.1 Типы Knowledge Objects (поле `kind`)

| Kind | Описание | Пример | Откуда берётся |
|------|---------|--------|---------------|
| `adr` | Architecture Decision Record | «Router вынесен в отдельный модуль» | Миграция arch_decisions |
| `lesson` | Подтверждённый урок/опыт | CON-36: «node_modules не восстанавливать вслепую» | Миграция LESSONS.md |
| `pattern` | Повторяющийся паттерн взаимодействия | «После pgrep pre-check всегда двойная проверка» | Event clustering |
| `rule` | Правило/политика | «Без --no-tg не диспатчить ночью» | Человек |
| `observation` | Зафиксированное наблюдение | «Диск заполняется на 100% при npm install» | Event pipeline |
| `candidate` | Кандидат на подтверждение | CAN-16: «не переписывать resolved-историю» | Pipeline + человек |
| `checklist` | Чек-лист | «Перед деплоем: drift_check, consistency_check, test» | Человек |
| `guideline` | Руководство/гайдлайн | «Как документировать CON-уроки» | Человек |
| `faq` | Часто задаваемый вопрос | «Почему node_modules не копируется?» | Семантическая группировка |
| `workflow` | Рабочий процесс | «prompt → dispatch → verify → done» | Человек / pipeline |

**Расширяемость:** `kind` — TEXT, не ENUM. Новые типы добавляются без ALTER TABLE.

> **Важно:** `kind` (таксономический тип знания) и `lifecycle_stage` (стадия в пайплайне) — независимые измерения. KO с `kind='observation'` может иметь `lifecycle_stage='confirmed'` (наблюдение подтверждено), а KO с `kind='lesson'` может иметь `lifecycle_stage='candidate'` (урок ещё проверяется). `kind` = что это за знание, `lifecycle_stage` = на какой стадии жизненного цикла оно находится.

### 3.2 Атрибуты (единая схема)

```sql
CREATE TABLE knowledge_objects (
    id              TEXT PRIMARY KEY,          -- CON-36, ADR-001, PAT-001, RULE-001
    kind            TEXT NOT NULL DEFAULT 'lesson',  -- adr|lesson|pattern|rule|observation|candidate|checklist|guideline|faq|workflow
    status          TEXT NOT NULL DEFAULT 'active',  -- active|superseded|archived|draft|review
    title           TEXT NOT NULL DEFAULT '',
    summary         TEXT NOT NULL DEFAULT '',        -- Краткое описание (одна строка)
    content         TEXT NOT NULL DEFAULT '',        -- Полный текст (markdown)
    
    -- Жизненный цикл
    lifecycle_stage TEXT NOT NULL DEFAULT 'confirmed', -- observation|candidate|confirmed|validated|superseded|archived
    
    -- Метрики опыта
    confidence_score REAL NOT NULL DEFAULT 0.5,       -- 0.0..1.0 (автоматически обновляется)
    evidence_count  INTEGER NOT NULL DEFAULT 0,       -- Сколько раз подтверждено
    usage_count     INTEGER NOT NULL DEFAULT 0,       -- Сколько раз использовано
    success_count   INTEGER NOT NULL DEFAULT 0,       -- Сколько раз помогло
    failure_count   INTEGER NOT NULL DEFAULT 0,       -- Сколько раз не помогло
    
    -- Связи
    superseded_by   TEXT DEFAULT NULL,                -- id→knowledge_objects (если устарел)
    source_event_id TEXT DEFAULT NULL,                -- event_id источника (если из pipeline)
    
    -- Временные метки
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    last_used_at    TEXT DEFAULT NULL,
    last_validated_at TEXT DEFAULT NULL,
    
    -- Версионирование
    version         INTEGER NOT NULL DEFAULT 1,
    
    FOREIGN KEY (superseded_by) REFERENCES knowledge_objects(id)
);

-- Индексы для частых запросов
CREATE INDEX idx_ko_kind ON knowledge_objects(kind);
CREATE INDEX idx_ko_status ON knowledge_objects(status);
CREATE INDEX idx_ko_lifecycle ON knowledge_objects(lifecycle_stage);
CREATE INDEX idx_ko_confidence ON knowledge_objects(confidence_score);
CREATE INDEX idx_ko_usage ON knowledge_objects(usage_count DESC);
CREATE INDEX idx_ko_last_used ON knowledge_objects(last_used_at);
```

### 3.3 Нормализация: tags, source_files, relations

**Почему отдельные таблицы, а не JSON-поля?**
- JSON в SQLite не индексируется эффективно
- Теги и source_files — частые фильтры в аналитике
- Связи (relations) — join с graph_edges для графового поиска

```sql
-- Теги (нормализованные)
CREATE TABLE knowledge_tags (
    knowledge_id TEXT NOT NULL,
    tag          TEXT NOT NULL,
    PRIMARY KEY (knowledge_id, tag),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
);
CREATE INDEX idx_kt_tag ON knowledge_tags(tag);

-- Исходные файлы (откуда знание)
CREATE TABLE knowledge_sources (
    knowledge_id TEXT NOT NULL,
    source_file  TEXT NOT NULL,           -- путь к файлу
    source_line  INTEGER DEFAULT NULL,    -- опционально: строка
    PRIMARY KEY (knowledge_id, source_file),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
);

-- Ссылки на внешние ресурсы
CREATE TABLE knowledge_references (
    knowledge_id TEXT NOT NULL,
    ref_type     TEXT NOT NULL DEFAULT 'url',  -- url|doc|issue|commit
    ref_value    TEXT NOT NULL,
    label        TEXT DEFAULT '',
    PRIMARY KEY (knowledge_id, ref_type, ref_value),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
);
```

---

## 4. Схема Memory Store

### 4.1 Размещение

ВСЁ в `data_13/context.db` — рядом с существующими таблицами:
- `arch_decisions` (остаётся без изменений до миграции)
- `knowledge_objects` (НОВАЯ)
- `knowledge_tags` (НОВАЯ)
- `knowledge_sources` (НОВАЯ)
- `knowledge_references` (НОВАЯ)
- `knowledge_events` (НОВАЯ — связка event→knowledge)

```sql
CREATE TABLE knowledge_events (
    event_id        TEXT NOT NULL,
    knowledge_id    TEXT NOT NULL,
    relation_type   TEXT NOT NULL DEFAULT 'source',  -- source|trigger|evidence|feedback
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (event_id, knowledge_id),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
    -- NB: event_id ссылается на event_log.event_id в events.db (другая БД).
    --     Ссылка ЛОГИЧЕСКАЯ (не FOREIGN KEY — SQLite не поддерживает cross-DB FK).
    --     Целостность проверяется на уровне приложения.
);
```

### 4.2 Отношение к существующим таблицам

| Существующая таблица | Отношение | Действие |
|----------------------|-----------|---------|
| `arch_decisions` | Предок `knowledge_objects(kind=adr)` | Миграция (Phase 3), потом read-only |
| `graph_nodes` | Будет включать `knowledge_objects.id` как узлы | Добавить узлы при создании KO |
| `graph_edges` | Новые rel_types | Расширить enum |
| `doc_meta` (в index.db) | Синоним KO для FTS-поиска | Индексировать KO.content |
| `event_log` | Источник `knowledge_objects(kind=observation)` | Pipeline |
| `LESSONS.md` | Мигрирует в KO | Phase 3, потом read-only архив |

---

## 5. Knowledge Graph

### 5.1 Новые типы связей

Расширяем `REL_TYPES` в `graph_index.py`:

```python
REL_TYPES = {
    # Существующие
    "references", "parent", "child", "depends",
    "related", "tagged", "contains",
    # НОВЫЕ — для Organizational Memory
    "supports",       # KO-A подтверждает KO-B
    "contradicts",    # KO-A противоречит KO-B
    "duplicates",     # KO-A дублирует KO-B
    "supersedes",     # KO-A заменяет KO-B
    "derived_from",   # KO-A выведен из KO-B
    "caused_by",      # KO-A вызван событием KO-B
    "resolved_by",    # KO-A решён через KO-B
    "generalizes",    # KO-A обобщает KO-B
    "specializes",    # KO-A уточняет KO-B
***REMOVED***
```

### 5.2 Автоматические vs ручные vs семантические связи

| Тип связи | Как строится | Триггер |
|----------|-------------|---------|
| `supports` | Автоматически | Один KO ссылается на другой при использовании → usage_count↑ обоих |
| `contradicts` | Автоматически (семантически) | SemanticIndex находит противоположные утверждения → флаг человеку |
| `duplicates` | Автоматически (семантически) | SemanticIndex cosine ≥ 0.85 → кандидат на merge |
| `supersedes` | Человек | При обновлении KO: указать superseded_by |
| `derived_from` | Автоматически | Pipeline: observation→candidate→lesson |
| `caused_by` | Автоматически | Event clustering: KO создан на основе события |
| `resolved_by` | Человек / автоматически | Урок решает проблему — ручная связь |
| `generalizes` / `specializes` | Полуавтоматически | Семантическая близость + review |
| `related` | Автоматически (семантически) | Cosine ≥ 0.6 + общие теги |

### 5.3 Интеграция с GraphIndex

Никаких изменений в `graph_index.py` API не требуется — только расширение `REL_TYPES`. Узлы: `graph_nodes.doc_id = knowledge_objects.id`.

---

## 6. Semantic Layer

### 6.1 Использовать существующий Knowledge Engine

**Не создаём новый движок.** `KnowledgeEngine` уже умеет:
- `search(query, mode='hybrid')` — keyword + semantic
- `index_document(doc_id, content, metadata)`
- `fit_semantic(n_components=100)` — SVD/LSA
- `graph_search(doc_id, mode='related')`

### 6.2 Что индексируется

При создании/обновлении Knowledge Object:

```python
ke = KnowledgeEngine()

# Индексация KO в существующий FTS5 + TF-IDF
ke.index_document(
    doc_id=f"ko:{ko.id***REMOVED***",
    content=f"{ko.title***REMOVED***\n{ko.summary***REMOVED***\n{ko.content***REMOVED***",
    metadata={
        "title": ko.title,
        "source": f"knowledge_objects/{ko.kind***REMOVED***/{ko.id***REMOVED***",
        "doc_type": f"ko_{ko.kind***REMOVED***",
        "created_at": ko.created_at,
    ***REMOVED***
)
```

**Индексируемые поля:**
- `title` + `summary` + `content` (все вместе)
- `tags` (через `knowledge_tags`) — добавляются как keywords в metadata

### 6.3 Что передаётся в RAG

При поиске контекста для новой задачи:

```
Context = KnowledgeEngine.search(query, mode='hybrid', top_k=5)
        + GraphIndex.get_related(top_result.id, max_depth=1)
        → Формируется контекстный блок для LLM
```

### 6.4 Периодическая реиндексация

После каждого `fit_semantic()` (вызывается при batch-обновлениях) перестраивается SVD-проекция. Частота: после каждых ~10 новых KO или раз в день.

---

## 7. Learning Loop

### 7.1 Модель обратной связи

```
Knowledge Object использован
    │
    ▼
Результат: success | failure | neutral
    │
    ▼
Обновление метрик:
    usage_count += 1
    success_count += 1 (если success)
    failure_count += 1 (если failure)
    last_used_at = now()
    │
    ▼
Пересчёт confidence_score:
    total = success_count + failure_count
    confidence = 0.5 + (success_count / max(total, 1)) * 0.5
    │
    ▼
Проверка порогов:
    confidence < 0.3 → статус 'review'
    confidence > 0.9 + evidence_count ≥ 5 → lifecycle 'validated'
    last_used_at > 90 дней → decay (confidence *= 0.95)
```

### 7.2 Механизм обратной связи

Два источника:

**A. Автоматический** (из диспетчера):
```python
# В prompt_dispatcher.py, при применении урока:
if lesson_applied_successfully:
    mem.update_confidence(knowledge_id, outcome='success')
else:
    mem.update_confidence(knowledge_id, outcome='failure')
```

**B. Ручной** (человек):
```
/buffy lesson CON-36 success   # помогло
/buffy lesson CON-36 failure   # не помогло
/buffy lesson CON-36 supersede CON-42  # заменить
```

### 7.3 Замыкание цикла

```
Observation (сырое событие)
    → Candidate (кластеризация N похожих событий)
    → Knowledge Object (подтверждён человеком)
    → Usage (применяется в задачах)
    → Feedback (success/failure)
    → Confidence Update (автоматически)
    → Re-validation (confidence < порог → review)
    → Superseded / Updated (человек или автоматически)
```

---

## 8. Experience Analytics

### 8.1 Аналитические запросы

Реализуются как SQL-вьюхи и Python-методы в новом модуле `scripts_01/experience_analytics.py`.

**Какие знания используются чаще всего?**
```sql
SELECT id, title, kind, usage_count, confidence_score
FROM knowledge_objects
WHERE status = 'active'
ORDER BY usage_count DESC
LIMIT 20;
```

**Какие знания перестали быть актуальными?**
```sql
SELECT id, title, kind, last_used_at, confidence_score
FROM knowledge_objects
WHERE status = 'active'
  AND (last_used_at < datetime('now', '-90 days') OR last_used_at IS NULL)
  AND usage_count > 0
ORDER BY last_used_at ASC;
```

**Какие знания противоречат друг другу?**
```sql
SELECT e.source_id, e.target_id, s.title, t.title
FROM graph_edges e
JOIN knowledge_objects s ON e.source_id = s.id
JOIN knowledge_objects t ON e.target_id = t.id
WHERE e.rel_type = 'contradicts';
```

**Какие Observation чаще всего становятся Lessons?**
```sql
SELECT COUNT(*) AS total_observations,
       COUNT(CASE WHEN lifecycle_stage IN ('confirmed','validated') THEN 1 END) AS promoted
FROM knowledge_objects
WHERE kind = 'observation';
```

**Какие Lessons никогда не используются?**
```sql
SELECT id, title, created_at
FROM knowledge_objects
WHERE kind = 'lesson' AND usage_count = 0 AND status = 'active';
```

**Какие проблемы повторяются чаще всего?**
```sql
SELECT e.event_type, COUNT(*) AS freq
FROM event_log e
JOIN knowledge_events ke ON e.event_id = ke.event_id
WHERE ke.relation_type = 'trigger'
GROUP BY e.event_type
ORDER BY freq DESC
LIMIT 10;
```

**Какие решения наиболее успешны?**
```sql
SELECT id, title, kind, success_count, failure_count,
       ROUND(CAST(success_count AS REAL) / MAX(success_count + failure_count, 1), 2) AS success_rate
FROM knowledge_objects
WHERE success_count + failure_count > 0
ORDER BY success_rate DESC, success_count DESC
LIMIT 10;
```

### 8.2 Периодические отчёты

- **Daily:** `decay_monitor` — проверка confidence < 0.3
- **Weekly:** `contradiction_report` — новые противоречия за неделю
- **Monthly:** `experience_summary` — топ-10 KO, decayed KO, unused KO

---

## 9. Mapping старой архитектуры → новой

| Старая сущность | → | Новая сущность | Примечание |
|-----------------|---|---------------|-----------|
| `LESSONS.md::CON-*` | → | `knowledge_objects(kind=lesson, lifecycle_stage=confirmed)` | Миграция: парсинг markdown → SQL |
| `LESSONS.md::CAN-*` | → | `knowledge_objects(kind=candidate)` | Миграция с сохранением номера |
| `LESSONS.md::ANTI-*` | → | `knowledge_objects(kind=lesson, title_prefix='ANTI-')` | Антипаттерны — подтип уроков |
| `arch_decisions` | → | `knowledge_objects(kind=adr)` | Миграция: копирование строк |
| `event_log::event_type` | → | `knowledge_objects(kind=observation, source_event_id=event_id)` | Pipeline кластеризации |
| `knowledge_engine::FtsIndex` | → | **Без изменений** — просто индексирует KO | |
| `knowledge_engine::TfidfIndex` | → | **Без изменений** | |
| `knowledge_engine::SemanticIndex` | → | **Без изменений** — SVD на KO | |
| `graph_index::GraphIndex` | → | **Расширение REL_TYPES** (9 новых) | Без изменения API |
| `doc_meta` (в index.db) | → | **Без изменений** — doc_id = `ko:{id***REMOVED***` | |
| `core_02/LESSONS.md` | → | **Read-only архив** после миграции | CAN-16: не удалять |

### Компоненты без изменений

- `context_12/events.db` — все таблицы
- `data_13/context.db::sessions`, `messages`, `workspaces`, `projects`, `invariants`, `checkpoints`, `action_verifications`
- `scripts_01/knowledge_engine.py` — полный API
- `scripts_01/graph_index.py` — API (только `REL_TYPES` расширяется)
- `scripts_01/memory_engine.py`
- `scripts_01/prompt_dispatcher.py` — добавится вызов feedback

---

## 10. План миграции

### Phase 1: Organizational Memory RFC (сейчас)
- ✅ Написать этот RFC
- ⬜ Утверждение RFC пользователем
- ⬜ Регистрация RFC в INDEX.md, DOCUMENT_REGISTRY.md, CHANGELOG.md

### Phase 2: Memory Store + Knowledge Objects
- ⬜ Создать таблицы `knowledge_objects`, `knowledge_tags`, `knowledge_sources`, `knowledge_references`, `knowledge_events` в `data_13/context.db`
- ⬜ Написать `scripts_01/organizational_memory.py` — Python API (CRUD + search + feedback)
- ⬜ Написать тесты (`tests_09/test_organizational_memory.py`)
- ⬜ Интегрировать индексацию через `KnowledgeEngine`
- ⬜ Расширить `REL_TYPES` в `graph_index.py`

### Phase 3: Миграция данных
- ⬜ Парсер `LESSONS.md` → `knowledge_objects` (CON-* → lesson, CAN-* → candidate, ANTI-* → lesson)
- ⬜ Парсер `arch_decisions` → `knowledge_objects(kind=adr)` (если появятся записи)
- ⬜ Верификация: все ~46 уроков перенесены
- ⬜ `LESSONS.md` → read-only (переименовать в `core_02/LESSONS.md.archive` или оставить с пометкой)

### Phase 4: Event Pipeline + Learning Loop
- ⬜ `scripts_01/experience_pipeline.py` — кластеризация событий → observation → candidate
- ⬜ `scripts_01/learning_loop.py` — feedback, confidence, decay
- ⬜ Интеграция в `prompt_dispatcher.py` — автоматический feedback при применении уроков

### Phase 5: Experience Analytics
- ⬜ `scripts_01/experience_analytics.py` — SQL-запросы, отчёты
- ⬜ CLI: `python scripts_01/experience_analytics.py report --type weekly`
- ⬜ Интеграция в `status_report.sh`

### Phase 6: Graph Auto-Discovery + Semantic Contradictions
- ⬜ Авто-детект связей (duplicates, contradictions, supports) через `SemanticIndex`
- ⬜ Периодические задачи (cron / диспетчер)

После каждой фазы:
- `drift_check.py` — без регрессий
- `consistency_check.py` — без новых расхождений
- Полная работоспособность платформы

---

## 11. Риски

| Риск | Вероятность | Влияние | Митигация |
|------|-----------|---------|----------|
| **Переусложнение** — Knowledge Object модель окажется слишком общей для реальных нужд | Средняя | Высокое | Начать с 3 типов (lesson, adr, observation), добавлять по необходимости |
| **Семантический дрейф** — урок устарел, но confidence высокий из-за старых usage | Высокая | Среднее | Поле `status` + `last_validated_at` + decay (90 дней) + периодический re-review |
| **Дублирование с arch_decisions** — ADR и lesson пересекаются по содержанию | Средняя | Низкое | Явная граница: ADR = архитектурные решения (формальные), lesson = проверенный опыт (практический) |
| **On-device ограничения** — SVD/LSA на CPU при 1000+ KO | Низкая (пока) | Среднее | SVD уже работает; при масштабировании — инкрементальный SVD или переход на FAISS |
| **Миграция LESSONS.md** — парсер может потерять контекст | Средняя | Среднее | Верификация: ручное сравнение каждого CON-/CAN-/ANTI-; LESSONS.md остаётся read-only |
| **Event pipeline latency** — кластеризация событий может отставать | Низкая | Низкое | Пакетная обработка (раз в N событий); не блокирует диспетчер |
| **Графовая связность** — при удалении KO рвутся связи | Низкая | Низкое | `ON DELETE SET NULL` для superseded_by; мягкое удаление (status=archived) предпочтительнее |

---

## 12. Альтернативы (рассмотрены и отклонены)

### 12.1 Отдельная векторная БД (Chroma, Qdrant, LanceDB)
**Отклонено.** Нарушает ограничение «не создавать новую векторную БД». Существующий SVD/LSA + TF-IDF достаточен для текущего масштаба (~100-1000 документов). При росте → FAISS как опциональный бэкенд для SemanticIndex.

### 12.2 Только FTS-поиск без семантики (grep-like)
**Отклонено.** Не выполняет требование «семантически смотреть на решения». FTS5 = keyword matching, не видит синонимы/контекст. TF-IDF + SVD уже реализованы и работают.

### 12.3 Отдельная БД для Organizational Memory (новый `memory.db`)
**Отклонено.** Противоречит принципу «единая БД». `data_13/context.db` уже содержит `arch_decisions`; `knowledge_objects` — естественное расширение.

### 12.4 LLM-эмбеддинги вместо SVD
**Отклонено (пока).** Требует API-ключей, сетевых вызовов, стоимости. SVD/LSA работает on-device бесплатно. В будущем — опциональный плагин embedding-модели.

### 12.5 Lesson-центричная модель (исходная идея IDEAS.md §14)
**Отклонено (осознанно).** Урок — лишь один тип знаний. Платформе нужна память организации, не «база уроков». Данный RFC заменяет IDEAS.md §14.

---

## 13. Рекомендации

1. **Утвердить RFC** — переход от идеи к реализации.
2. **Начать с Phase 2** (Memory Store + Knowledge Objects) — самая маленькая независимая единица, даёт immediate value (CRUD для любых знаний).
3. **Мигрировать LESSONS.md в Phase 3** — даст первый реальный набор данных, проверит модель на практике.
4. **Не спешить с Learning Loop** — фазы 4-6 могут идти параллельно с эксплуатацией фаз 2-3.
5. **CON-37** (новый урок) — зафиксировать в LESSONS.md урок о том, почему Lesson-центричная модель была заменена на Organizational Memory.
6. **Не удалять IDEAS.md §14** — оставить как историческую запись с пометкой «заменено RFC Organizational Memory Engine v1» (CAN-16 compliance).

---

## Приложение A: Сравнение «Lessons Memory Engine» vs «Organizational Memory Engine»

| Аспект | Lessons Memory Engine (IDEAS.md §14) | Organizational Memory Engine (данный RFC) |
|--------|--------------------------------------|------------------------------------------|
| Центральная сущность | `lessons` таблица | `knowledge_objects` — множество типов |
| Типы знаний | Только уроки (CON-/ANTI-/CAND-) | 10+ типов: adr, lesson, pattern, rule, observation, candidate, checklist, guideline, faq, workflow |
| Расширяемость | Новая таблица на каждый тип | `kind` TEXT — без ALTER TABLE |
| Жизненный цикл | Только статус | `lifecycle_stage` (6 стадий) + `status` + метрики |
| Метрики опыта | Нет | confidence_score, evidence/usage/success/failure count |
| Learning Loop | Нет | Полный цикл: observation→candidate→KO→feedback→confidence |
| Analytics | Нет | 7+ аналитических запросов |
| Граф связей | Только graph_index | 9 новых rel_types + авто-детект |
| Место в архитектуре | Подсистема lessons | Центральный слой памяти платформы |

---

## Приложение B: Сигнатура Python API (проект)

```python
# scripts_01/organizational_memory.py

class OrganizationalMemory:
    """Unified API for Organizational Memory Engine."""
    
    def __init__(self, workspace_root: Path, event_bus=None): ...
    
    # CRUD
    def create(self, kind: str, title: str, content: str, **kwargs) -> str: ...
    def get(self, ko_id: str) -> KnowledgeObject: ...
    def update(self, ko_id: str, **fields) -> None: ...
    def archive(self, ko_id: str, reason: str = '') -> None: ...
    def supersede(self, old_id: str, new_id: str) -> None: ...
    
    # Search
    def search(self, query: str, kind: str = None, top_k: int = 10,
               mode: str = 'hybrid') -> List[SearchResult***REMOVED***: ...
    def find_related(self, ko_id: str, depth: int = 2) -> List[KnowledgeObject***REMOVED***: ...
    def find_contradictions(self) -> List[Tuple[str, str***REMOVED******REMOVED***: ...
    def find_similar(self, ko_id: str, threshold: float = 0.7) -> List[str***REMOVED***: ...
    
    # Learning Loop
    def record_usage(self, ko_id: str, outcome: str) -> None: ...
    def update_confidence(self, ko_id: str) -> float: ...
    def decay_check(self) -> List[str***REMOVED***: ...  # возвращает KO для re-review
    
    # Analytics
    def top_used(self, limit: int = 10) -> List[KnowledgeObject***REMOVED***: ...
    def unused_since(self, days: int = 90) -> List[KnowledgeObject***REMOVED***: ...
    def stats(self) -> Dict[str, Any***REMOVED***: ...
    
    # Pipeline
    def create_observation(self, event_id: str, summary: str) -> str: ...
    def promote_to_candidate(self, obs_id: str) -> str: ...
    def confirm(self, candidate_id: str) -> str: ...
    
    # Migration
    def migrate_lessons_md(self, path: Path) -> int: ...
    def migrate_arch_decisions(self) -> int: ...
```

---

**Статус RFC:** Ожидает утверждения пользователем.

**Следующий шаг после утверждения:** Phase 2 — создание таблиц + `organizational_memory.py`.
