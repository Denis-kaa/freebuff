# RFC Evolution: Organizational Memory Engine v1 → v1.1

**Статус:** 📋 Architectural Enhancement (надстройка над RFC v1)
**Основание:** [pompts_11/052_15_rfc_evolution_architectural_enhancement.md***REMOVED***(../../pompts_11/052_15_rfc_evolution_architectural_enhancement.md) — user directive
**Целевой RFC:** [RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md***REMOVED***(./RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md) (v5.92.0)
**Принцип:** Architectural Evolution, не Architectural Replacement. Все изменения ADDITIVE.
**Анализ проведён:** 2026-08-05

---

## Сводка: 8 уровней анализа → 12 Improvements

| # | Уровень | Improvement | Приоритет |
|---|---------|------------|-----------|
| I-1 | Concept | Authority Model — уровни доверия к знаниям | Critical |
| I-2 | Concept | Decision Trace — почему платформа приняла именно это решение | Critical |
| I-3 | Concept | Policy — знания-правила vs знания-советы | High |
| I-4 | Architecture | Архитектурный нейминг: Memory Engine → Intelligence System | Medium |
| I-5 | Missing | Conflict Resolver — разрешение противоречий | High |
| I-6 | Missing | Knowledge Provenance — полная цепочка происхождения | High |
| I-7 | Lifecycle | Knowledge Evolution — версионирование с историей изменений | High |
| I-8 | Lifecycle | Knowledge Revision — процесс пересмотра (не только decay) | Medium |
| I-9 | Decision | Reasoning Layer — комбинирование знаний для принятия решений | High |
| I-10 | Decision | Decision History — архив принятых решений и их исходов | Medium |
| I-11 | Conflict | Conflict Lifecycle — от обнаружения до разрешения | High |
| I-12 | Evolution | Long-term Scalability — подготовка к 1000+ KO через 5 лет | Medium |

---

## Improvement I-1: Authority Model

### Что обнаружено
В RFC v1 все Knowledge Objects равны: `confidence_score` измеряет опыт использования, но не учитывает **источник** знания. Урок, импортированный из markdown-файла, урок от code-reviewer, и правило от пользователя имеют одинаковый вес при поиске.

### Почему это проблема
- Сгенерированное знание (LLM) не должно иметь тот же вес, что и проверенное человеком.
- При конфликте двух KO платформа не может определить, какому доверять.
- Через 2 года платформа будет содержать знания от 5+ источников — без authority-модели «шум» заглушит «сигнал».

### Предлагаемое решение

**Новое поле `authority` в `knowledge_objects`:**

```sql
ALTER TABLE knowledge_objects ADD COLUMN authority TEXT NOT NULL DEFAULT 'imported';
-- Значения: system | reviewed | candidate | generated | user | imported
-- system:     встроенное правило платформы (Policy, invariant)
-- reviewed:   подтверждено code-review или человеком
-- candidate:  промежуточный уровень (сгенерировано, ожидает подтверждения)
-- generated:  сгенерировано LLM/алгоритмом
-- user:       создано пользователем вручную
-- imported:   импортировано из внешнего источника (LESSONS.md, docs)
```

**Новая таблица `knowledge_authority_log` — аудит изменений authority:**

```sql
CREATE TABLE knowledge_authority_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id    TEXT NOT NULL,
    old_authority   TEXT NOT NULL,
    new_authority   TEXT NOT NULL,
    reason          TEXT DEFAULT '',
    changed_by      TEXT DEFAULT 'system',  -- system | user | reviewer
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
);
```

**Правила повышения authority:**
- `imported` → `reviewed`: после миграции и ручной верификации
- `generated` → `candidate`: после кластеризации событий
- `candidate` → `reviewed`: после подтверждения человеком
- `reviewed` → `system`: после N успешных применений + confidence > 0.9

### Как интегрировать
- **RFC §3.2** — добавить поле `authority` в схему `knowledge_objects`
- **RFC §7 (Learning Loop)** — добавить правила повышения authority
- **Новая таблица** `knowledge_authority_log` в `data_13/context.db`
- **Повторно использовать:** `confidence_score` (уже есть), `event_log` (для аудита)

### Совместимость
✅ ADDITIVE: ALTER TABLE + новая таблица. Существующие KO получают `authority='imported'`. Confidence продолжает работать независимо.

### Приоритет: **Critical**

---

## Improvement I-2: Decision Trace

### Что обнаружено
RFC v1 описывает «поиск знаний → использование», но не фиксирует **почему платформа выбрала именно этот KO для конкретной задачи**. Без Decision Trace невозможно ответить: «какие знания реально повлияли на решение X?».

### Почему это проблема
- Невозможно отладить неправильное решение: «почему Buffy использовал урок А, а не урок Б?»
- Learning Loop не имеет данных для обратной связи с конкретными решениями.
- Analytics не может связать success/failure с конкретным контекстом использования.

### Предлагаемое решение

**Новая таблица `decision_trace`:**

```sql
CREATE TABLE decision_trace (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL DEFAULT '',
    task_id         TEXT NOT NULL DEFAULT '',
    knowledge_id    TEXT NOT NULL,
    query_context   TEXT NOT NULL DEFAULT '',    -- контекст запроса (ситуация)
    search_mode     TEXT NOT NULL DEFAULT 'hybrid', -- keyword|semantic|hybrid|graph
    rank_position   INTEGER NOT NULL DEFAULT 0,  -- позиция в выдаче (0-based)
    relevance_score REAL NOT NULL DEFAULT 0.0,    -- score от KnowledgeEngine
    was_used        INTEGER NOT NULL DEFAULT 1,   -- реально ли применён
    outcome         TEXT DEFAULT NULL,             -- success|failure|neutral (заполняется позже)
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
);

CREATE INDEX idx_dt_session ON decision_trace(session_id);
CREATE INDEX idx_dt_knowledge ON decision_trace(knowledge_id);
CREATE INDEX idx_dt_outcome ON decision_trace(outcome);
```

**Интеграция в Learning Loop (RFC §7):**
```python
# При поиске знаний для задачи:
results = ke.search(query, mode='hybrid', top_k=5)
for i, result in enumerate(results):
    om.record_decision_trace(
        session_id=task_id,
        knowledge_id=result.doc_id,
        query_context=query,
        rank_position=i,
        relevance_score=result.score,
        was_used=(i == 0),  # использован top-1
    )
```

### Как интегрировать
- **Новый раздел RFC:** §6.5 «Decision Trace — объяснимость решений»
- **Новая таблица** `decision_trace` в `data_13/context.db`
- **Расширение `organizational_memory.py` API:** `record_decision_trace()`, `get_decision_history()`
- **Повторно использовать:** `KnowledgeEngine.search()` (уже возвращает score), `event_log` (контекст задачи)

### Совместимость
✅ ADDITIVE: новая таблица, новый метод API. Существующий `search()` не меняется.

### Приоритет: **Critical**

---

## Improvement I-3: Policy — знания-правила vs знания-советы

### Что обнаружено
RFC v1 различает `kind` (adr, lesson, rule, ...), но не различает **нормативную силу** знания. Правило «без --no-tg не диспатчить ночью» и урок «node_modules не восстанавливать вслепую» — оба хранятся одинаково, но первое должно **блокировать** действие, а второе — **советовать**.

### Почему это проблема
- Платформа не может обеспечить compliance: нет механизма «это правило нарушено → действие заблокировано».
- При росте числа правил ручная проверка невозможна.
- Policy violation должно генерировать событие, а не просто низкий search score.

### Предлагаемое решение

**Добавить `enforcement` в `knowledge_objects`:**

```sql
ALTER TABLE knowledge_objects ADD COLUMN enforcement TEXT NOT NULL DEFAULT 'advisory';
-- advisory:  совет (можно проигнорировать)
-- mandatory: правило (нарушение → warn)
-- blocking:  жёсткое правило (нарушение → abort)
-- passive:   информационное (не требует действия)
```

**Новый компонент: `scripts_01/policy_checker.py` — Policy Enforcement Point**

```python
class PolicyChecker:
    """Проверяет compliance с mandatory/blocking правилами перед действием."""
    
    def check(self, action_context: dict) -> List[PolicyViolation***REMOVED***:
        """Возвращает список нарушений (mandatory → warn, blocking → abort)."""
        mandatory = om.search(kind='rule', enforcement='mandatory', ...)
        blocking = om.search(kind='rule', enforcement='blocking', ...)
        violations = [***REMOVED***
        for rule in blocking:
            if self._violates(rule, action_context):
                violations.append(PolicyViolation(rule, severity='blocking'))
        ...
        return violations
```

### Как интегрировать
- **RFC §3.2** — добавить поле `enforcement` в схему
- **Новый раздел RFC:** §14 «Policy Enforcement — от советов к правилам»
- **Новый модуль:** `scripts_01/policy_checker.py`
- **Повторно использовать:** `KnowledgeEngine.search()`, `event_log` (policy violation events)

### Совместимость
✅ ADDITIVE: ALTER TABLE + новый модуль. Все существующие KO — `enforcement='advisory'`.

### Приоритет: **High**

---

## Improvement I-4: Архитектурный нейминг

### Что обнаружено
RFC называется «Organizational Memory Engine», но его содержание выходит далеко за пределы «памяти». Он включает Learning Loop, Experience Analytics, Knowledge Graph, Semantic Search. Это не Engine (один компонент), а архитектурный слой. Это не только Memory (хранение), но и Reasoning (принятие решений).

### Почему это проблема
- Название «Memory Engine» ограничивает восприятие: команда думает «это база данных для уроков», а не «центральный интеллектуальный слой платформы».
- При расширении (I-1–I-3, I-5–I-12) название «Engine» всё меньше соответствует содержанию.
- Внешние читатели (ADR, vision docs) недооценивают стратегическую важность компонента.

### Предлагаемое решение

**Эволюция нейминга (не переименование — признание роста):**

```
Organizational Memory Engine (v1)
    ↓ эволюция
Organizational Intelligence Layer (v1.1+)
```

В RFC добавить примечание:
> **Архитектурная эволюция (v1.1):** содержание RFC переросло первоначальное название «Memory Engine». Платформа не просто хранит знания — она принимает решения на их основе, объясняет их, разрешает конфликты и самообучается. Рекомендуемое название для внешних ссылок: **Organizational Intelligence Layer**. Внутреннее кодовое имя (таблицы, модули) остаётся `organizational_memory` для обратной совместимости.

### Как интегрировать
- **RFC §0** — добавить блок «Эволюция нейминга» перед §1
- **Рекомендация:** внешние ссылки (INDEX.md, PLATFORM.md) → «Organizational Intelligence Layer»
- **Код:** имена таблиц/модулей не менять (`organizational_memory.py`, `knowledge_objects`)

### Совместимость
✅ ADDITIVE: только документация. Код не меняется.

### Приоритет: **Medium**

---

## Improvement I-5: Conflict Resolver

### Что обнаружено
RFC v1 §5.2 описывает `contradicts`-связи в Knowledge Graph и §8.1 — SQL-запрос для обнаружения противоречий. Но механизм **разрешения** противоречий отсутствует. Платформа знает, что KO-A противоречит KO-B, но не знает, что с этим делать.

### Почему это проблема
- Противоречивые знания накапливаются без разрешения → платформа даёт противоречивые советы.
- Без resolver противоречия — это «шум» в semantic search: оба KO возвращаются с похожими scores.
- Через год платформа будет иметь десятки unresolved contradictions.

### Предлагаемое решение

**Новая таблица `conflict_resolutions`:**

```sql
CREATE TABLE conflict_resolutions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id           TEXT NOT NULL,     -- KO-A
    target_id           TEXT NOT NULL,     -- KO-B
    conflict_type       TEXT NOT NULL DEFAULT 'contradiction',  -- contradiction|duplicate|overlap
    resolution_strategy TEXT NOT NULL DEFAULT 'manual',         -- manual|newest_wins|highest_confidence|authority_wins|merge
    resolved_by         TEXT DEFAULT NULL,  -- кто разрешил (system|user|reviewer)
    resolution_note     TEXT DEFAULT '',
    winner_id           TEXT DEFAULT NULL,  -- какой KO «победил» (NULL = оба невалидны)
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (source_id) REFERENCES knowledge_objects(id),
    FOREIGN KEY (target_id) REFERENCES knowledge_objects(id),
    FOREIGN KEY (winner_id) REFERENCES knowledge_objects(id)
);
```

**Стратегии разрешения:**
| Стратегия | Когда применять | Автоматически? |
|-----------|----------------|----------------|
| `newest_wins` | Оба KO одного типа, один явно устарел | ✅ Авто (если difference > 30 дней) |
| `highest_confidence` | Оба KO одного authority-уровня | ✅ Авто |
| `authority_wins` | Разные authority-уровни (system > reviewed > ...) | ✅ Авто |
| `merge` | KO-A и KO-B дополняют друг друга | ❌ Ручное |
| `manual` | Всё остальное | ❌ Ручное |

### Как интегрировать
- **Новый раздел RFC:** §5.4 «Conflict Resolution — от обнаружения к разрешению»
- **Новая таблица** `conflict_resolutions` в `data_13/context.db`
- **Новый метод API:** `om.resolve_conflict(source_id, target_id, strategy)`
- **Повторно использовать:** `graph_index` (contradicts-рёбра), authority (I-1), confidence_score

### Совместимость
✅ ADDITIVE: новая таблица, новый метод. Существующий `contradicts` detection не меняется.

### Приоритет: **High**

---

## Improvement I-6: Knowledge Provenance

### Что обнаружено
RFC v1 имеет `source_event_id` (ссылка на породившее событие) и `knowledge_sources` (файлы), но нет **полной цепочки происхождения**. Нельзя ответить: «откуда взялся KO-42, через какие трансформации он прошёл, кто его подтвердил?»

### Почему это проблема
- Без provenance невозможно аудировать качество знаний.
- При миграции LESSONS.md → KO теряется связь с исходным markdown.
- При ошибке в KO невозможно traced back к исходному событию/наблюдению.

### Предлагаемое решение

**Расширить `knowledge_objects` полем `provenance_chain`:**

```sql
ALTER TABLE knowledge_objects ADD COLUMN provenance_chain TEXT DEFAULT '[***REMOVED***';
-- JSON-массив: [{"stage":"event","id":"evt_123"***REMOVED***,{"stage":"observation","id":"OBS-1"***REMOVED***,...***REMOVED***
```

**Новая таблица `knowledge_provenance` (детальная):**

```sql
CREATE TABLE knowledge_provenance (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id    TEXT NOT NULL,
    stage           TEXT NOT NULL,    -- event|observation|candidate|confirmation|revision|supersession
    source_id       TEXT DEFAULT NULL, -- event_id / observation_id / previous KO id
    actor           TEXT NOT NULL DEFAULT 'system', -- system|user|reviewer|pipeline
    transformation  TEXT NOT NULL DEFAULT 'created', -- created|promoted|revised|superseded|merged
    note            TEXT DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
);

CREATE INDEX idx_kp_knowledge ON knowledge_provenance(knowledge_id);
CREATE INDEX idx_kp_stage ON knowledge_provenance(stage);
```

### Как интегрировать
- **RFC §4.1** — добавить `provenance_chain` в схему
- **Новая таблица** `knowledge_provenance` в `data_13/context.db`
- **Расширение API:** `om.get_provenance(ko_id) → List[ProvenanceStep***REMOVED***`
- **Повторно использовать:** `event_log`, `knowledge_events`

### Совместимость
✅ ADDITIVE: ALTER TABLE + новая таблица. Существующие KO: `provenance_chain='[***REMOVED***'`.

### Приоритет: **High**

---

## Improvement I-7: Knowledge Evolution — версионирование с историей

### Что обнаружено
RFC v1 имеет поле `version INTEGER DEFAULT 1` и `superseded_by`, но нет **истории изменений** Knowledge Object. Нельзя посмотреть: «как выглядел CON-36 в версии 1, что изменилось в версии 2, почему?»

### Почему это проблема
- Без истории изменений невозможно понять эволюцию знания.
- При ошибке в новой версии нельзя откатиться к предыдущей.
- Аналитика не может измерить «скорость изменений знаний» (быстро устаревающие домены).

### Предлагаемое решение

**Новая таблица `knowledge_object_versions`:**

```sql
CREATE TABLE knowledge_object_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id    TEXT NOT NULL,
    version         INTEGER NOT NULL,
    title           TEXT NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',
    change_summary  TEXT NOT NULL DEFAULT '',   -- что изменилось относительно предыдущей
    change_type     TEXT NOT NULL DEFAULT 'update', -- update|correction|supersession|merge
    changed_by      TEXT NOT NULL DEFAULT 'system',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_objects(id)
);

CREATE INDEX idx_kov_knowledge ON knowledge_object_versions(knowledge_id, version);
```

**API:**
```python
om.revise_knowledge(ko_id, new_content, change_summary)  # → version++
om.get_version_history(ko_id)  # → List[version snapshots***REMOVED***
om.rollback(ko_id, target_version)  # → восстанавливает указанную версию
```

### Как интегрировать
- **Новый раздел RFC:** §3.4 «Knowledge Evolution — версионирование и история изменений»
- **Новая таблица** `knowledge_object_versions`
- **Расширение API:** `revise_knowledge()`, `get_version_history()`, `rollback()`
- **Повторно использовать:** `version` (уже есть), `superseded_by` (уже есть)

### Совместимость
✅ ADDITIVE: новая таблица, новые методы. Поле `version` уже существует.

### Приоритет: **High**

---

## Improvement I-8: Knowledge Revision — процесс пересмотра

### Что обнаружено
RFC v1 §7 (Learning Loop) описывает decay (confidence *= 0.95 после 90 дней) и проверку порогов (confidence < 0.3 → review), но нет **процесса пересмотра**. Что значит «review»? Кто ревьюит? Как долго? Что происходит после?

### Почему это проблема
- «Review» без процесса — это мёртвый статус. KO застревает в review навсегда.
- Нет SLA для устаревающих знаний.
- Нет уведомлений/эскалации для forgotten reviews.

### Предлагаемое решение

**Расширить lifecycle_stage:**

```sql
-- Добавить значение 'under_review' в lifecycle_stage
-- Новые поля:
ALTER TABLE knowledge_objects ADD COLUMN review_due_by TEXT DEFAULT NULL;
ALTER TABLE knowledge_objects ADD COLUMN review_assignee TEXT DEFAULT NULL;
```

**Процесс пересмотра:**
```
confidence < 0.3 OR last_validated > 180 дней
    → lifecycle_stage = 'under_review'
    → review_due_by = now() + 30 дней
    → уведомление (event_log + TG)
    │
    ├─ Ревью завершено (подтверждено) → lifecycle = 'validated', confidence = 0.8
    ├─ Ревью завершено (устарело) → lifecycle = 'superseded', search weight = 0
    └─ Ревью просрочено (>30 дней) → эскалация, confidence ещё ниже
```

### Как интегрировать
- **RFC §7.1** — дополнить модель decay процессом revision
- **RFC §7** — новый подраздел «Revision Workflow»
- **Новый скрипт:** `scripts_01/revision_monitor.py` (cron job для просроченных review)
- **Повторно использовать:** `event_log`, `confidence_score`, `telegram_contract`

### Совместимость
✅ ADDITIVE: ALTER TABLE + новый скрипт. Существующий decay не меняется.

### Приоритет: **Medium**

---

## Improvement I-9: Reasoning Layer

### Что обнаружено
RFC v1 описывает **поиск** знаний (semantic search → top-5 KO), но не описывает **комбинирование** множества KO для принятия решения. Платформа находит 5 релевантных KO — и что дальше? Как из 5 противоречивых советов выбрать действие?

### Почему это проблема
- Semantic search возвращает список, но не synthesises решение.
- При конфликте KO (один говорит «делай X», другой — «не делай X») платформа не знает, как выбрать.
- Через год в базе будет 500+ KO — top-5 будет содержать противоречия почти всегда.

### Предлагаемое решение

**Новый компонент: Reasoning Layer (над Semantic Layer):**

```python
class ReasoningEngine:
    """Комбинирует множество KO в одно решение."""
    
    def reason(self, query: str, context: dict) -> ReasoningResult:
        """
        1. Semantic search → top-10 KO
        2. Фильтрация: отбросить superseded, archived
        3. Группировка: supports / contradicts
        4. Ранжирование: authority + confidence + relevance
        5. Разрешение конфликтов: strategy-based (I-5)
        6. Синтез: form final recommendation
        """
        kos = om.search(query, top_k=10)
        active = [ko for ko in kos if ko.status == 'active'***REMOVED***
        groups = self._group_by_stance(active)  # supporting vs contradicting
        resolved = self._resolve_conflicts(groups)
        recommendation = self._synthesize(resolved, context)
        return ReasoningResult(
            recommendation=recommendation,
            supporting_ko=[...***REMOVED***,
            contradicting_ko=[...***REMOVED***,
            confidence=...,
            reasoning_chain=[...***REMOVED***,  # для Decision Trace (I-2)
        )
```

**Новая таблица `reasoning_sessions`:**

```sql
CREATE TABLE reasoning_sessions (
    id              TEXT PRIMARY KEY,
    query           TEXT NOT NULL,
    context_json    TEXT NOT NULL DEFAULT '{***REMOVED***',
    recommendation  TEXT NOT NULL DEFAULT '',
    confidence      REAL NOT NULL DEFAULT 0.0,
    ko_ids_used     TEXT NOT NULL DEFAULT '[***REMOVED***',  -- JSON-массив ID использованных KO
    conflicts_found INTEGER NOT NULL DEFAULT 0,
    conflicts_resolved INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Как интегрировать
- **Новый раздел RFC:** §6.6 «Reasoning Layer — от поиска к решению»
- **Новый модуль:** `scripts_01/reasoning_engine.py`
- **Новая таблица** `reasoning_sessions`
- **Повторно использовать:** `KnowledgeEngine.search()`, `GraphIndex`, authority (I-1), conflict resolution (I-5), decision trace (I-2)

### Совместимость
✅ ADDITIVE: новый модуль над существующим Semantic Layer. `KnowledgeEngine.search()` не меняется.

### Приоритет: **High**

---

## Improvement I-10: Decision History

### Что обнаружено
Decision Trace (I-2) фиксирует факт использования KO. Но нет **истории принятых решений и их исходов**. Нельзя ответить: «какие решения платформа приняла за последнюю неделю? Какие из них были успешны?»

### Почему это проблема
- Learning Loop (RFC §7) получает feedback, но не привязан к конкретным решениям.
- Невозможно измерить «качество решений платформы» агрегированно.
- При росте автономности платформы (cron dispatch, авто-фиксы) аудит решений становится критичным.

### Предлагаемое решение

**Расширить `decision_trace` (I-2) полем `decision_id` и добавить агрегирующую таблицу:**

```sql
CREATE TABLE decisions (
    id              TEXT PRIMARY KEY,          -- UUID
    session_id      TEXT NOT NULL DEFAULT '',
    task_id         TEXT NOT NULL DEFAULT '',
    decision_type   TEXT NOT NULL DEFAULT 'recommendation',  -- recommendation|action|policy_check
    summary         TEXT NOT NULL DEFAULT '',
    ko_ids_used     TEXT NOT NULL DEFAULT '[***REMOVED***',  -- JSON-массив
    outcome         TEXT DEFAULT NULL,            -- success|failure|neutral (заполняется позже)
    outcome_note    TEXT DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at     TEXT DEFAULT NULL
);

CREATE INDEX idx_decisions_outcome ON decisions(outcome);
CREATE INDEX idx_decisions_created ON decisions(created_at);
```

### Как интегрировать
- **Новый раздел RFC:** §8.3 «Decision History — аудит принятых решений»
- **Новая таблица** `decisions`
- **Расширение `decision_trace`** — добавить `decision_id` FOREIGN KEY
- **Повторно использовать:** `decision_trace` (I-2), `reasoning_sessions` (I-9), `event_log`

### Совместимость
✅ ADDITIVE: новая таблица, расширение существующей. Decision Trace (I-2) не ломается.

### Приоритет: **Medium**

---

## Improvement I-11: Conflict Lifecycle

### Что обнаружено
RFC v1 §5.2 описывает автоматическое обнаружение `contradicts`-связей, а I-5 добавляет `conflict_resolutions`. Но нет **жизненного цикла конфликта**: обнаружен → проанализирован → разрешён → задокументирован → проверен.

### Почему это проблема
- Без lifecycle конфликты либо игнорируются, либо разрешаются ad-hoc.
- Нельзя измерить «время жизни конфликта» (от обнаружения до разрешения).
- Нет гарантии, что resolution действительно решает проблему (может создать новый конфликт).

### Предлагаемое решение

**Расширить lifecycle конфликта:**

```
DETECTED (автоматически: SemanticIndex cosine > threshold + opposite stance)
    │
    ▼
TRIAGED (автоматически: классификация — contradiction|duplicate|overlap)
    │
    ▼
ANALYZED (полуавтоматически: сравнение authority, confidence, evidence)
    │
    ├─ AUTO-RESOLVABLE → RESOLVED (strategy-based: I-5)
    └─ NEEDS-HUMAN → PENDING_REVIEW (уведомление)
    │
    ▼
RESOLVED (стратегия применена, winner_id установлен, loser → superseded)
    │
    ▼
VERIFIED (опционально: через N дней проверка, что конфликт не возник снова)
```

**Расширить `conflict_resolutions` полем `lifecycle_stage`:**

```sql
ALTER TABLE conflict_resolutions ADD COLUMN lifecycle_stage TEXT NOT NULL DEFAULT 'detected';
-- detected|triaged|analyzed|pending_review|resolved|verified
ALTER TABLE conflict_resolutions ADD COLUMN verified_at TEXT DEFAULT NULL;
-- NB: ALTER TABLE ... DEFAULT применяется только к НОВЫМ строкам.
--     Существующие строки (созданные в I-5 до I-11) получат NULL в lifecycle_stage.
--     Необходим backfill: UPDATE conflict_resolutions SET lifecycle_stage='resolved' WHERE lifecycle_stage IS NULL;
```

### Как интегрировать
- **RFC §5.4 (I-5)** — добавить lifecycle stages
- **Новый скрипт:** `scripts_01/conflict_monitor.py` (cron: авто-триаж + эскалация)
- **Повторно использовать:** `conflict_resolutions` (I-5), `event_log`, authority (I-1)

### Совместимость
✅ ADDITIVE: ALTER TABLE + новый скрипт. I-5 не ломается.

### Приоритет: **High**

---

## Improvement I-12: Long-term Scalability

### Что обнаружено
RFC v1 рассчитан на текущий масштаб (~100 KO). Через 5 лет платформа может иметь 1000+ KO от 5+ источников. Текущая архитектура неявно предполагает:
- SVD/LSA на CPU при 1000+ документах — приемлемо, но нужен мониторинг
- Knowledge Graph с 1000+ узлами — BFS subgraph может стать медленным
- Полный rescan событий для observation clustering — не масштабируется
- Semantic search возвращает все KO данного kind — без сегментации

### Почему это проблема
- Не сейчас. Но архитектура должна быть готова к росту без переписывания.
- Проблемы масштабирования, заложенные сейчас, станут блокерами через 2-3 года.

### Предлагаемое решение

**1. Инкрементальная индексация (а не полный `fit_semantic`):**
```python
# Добавить в SemanticIndex:
def fit_incremental(self, new_vectors, new_doc_ids):
    """Частичное обновление SVD без полного пересчёта."""
```

**2. Сегментация Knowledge Graph:**
```sql
-- Добавить поле domain в graph_nodes для шардирования графа
ALTER TABLE graph_nodes ADD COLUMN domain TEXT DEFAULT 'general';
-- domain: platform|interior|tg|security|general
```

**3. Пагинация и курсоры для аналитики:**
```python
# Все аналитические запросы должны поддерживать limit/offset/cursor
om.top_used(limit=20, offset=0)
om.search(query, top_k=10, cursor=last_id)  # для sequential scan
```

**4. TTL для observation-записей:**
```sql
ALTER TABLE knowledge_objects ADD COLUMN ttl_days INTEGER DEFAULT NULL;
-- NULL = бессрочно. Для observation: 90 дней (авто-архивация).
```

**5. Budget-aware SVD:**
```python
# Мониторинг времени fit_semantic, авто-reduce n_components при превышении
if fit_time > 30:  # секунд
    n_components = max(50, n_components // 2)
```

### Как интегрировать
- **Новый раздел RFC:** §15 «Scalability — подготовка к 1000+ Knowledge Objects»
- **Расширение:** `SemanticIndex.fit_incremental()`, `graph_nodes.domain`, `knowledge_objects.ttl_days`
- **Повторно использовать:** существующий `SemanticIndex`, `GraphIndex`, `KnowledgeEngine`

### Совместимость
✅ ADDITIVE: ALTER TABLE + новые методы. Существующий `fit_semantic` остаётся как fallback.

### Приоритет: **Medium**

---

## Сводная таблица изменений RFC

| Раздел RFC | Изменение | Improvement |
|-----------|----------|------------|
| §0 | Блок «Эволюция нейминга» | I-4 |
| §3.2 | Поля `authority`, `enforcement`, `provenance_chain` | I-1, I-3, I-6 |
| §3.4 (NEW) | Knowledge Evolution — версионирование | I-7 |
| §4.1 | Таблицы `knowledge_authority_log`, `knowledge_provenance`, `knowledge_object_versions`, `decision_trace`, `decisions`, `conflict_resolutions`, `reasoning_sessions` | I-1, I-2, I-5, I-6, I-7, I-10 |
| §5.4 (NEW) | Conflict Resolution + Lifecycle | I-5, I-11 |
| §6.5 (NEW) | Decision Trace | I-2 |
| §6.6 (NEW) | Reasoning Layer | I-9 |
| §7.1 | Revision Workflow | I-8 |
| §8.3 (NEW) | Decision History | I-10 |
| §14 (NEW) | Policy Enforcement | I-3 |
| §15 (NEW) | Scalability | I-12 |

---

## Приоритеты внедрения (рекомендуемый порядок)

| Фаза | Improvements | Обоснование |
|------|-------------|------------|
| **Фаза A** (сейчас) | I-1 (Authority), I-2 (Decision Trace) | Без authority нельзя доверять поиску; без decision trace нельзя отлаживать. |
| **Фаза B** | I-5 (Conflict Resolver), I-6 (Provenance), I-7 (Versioning) | Конфликты будут сразу после миграции LESSONS.md; provenance нужен для аудита. |
| **Фаза C** | I-3 (Policy), I-9 (Reasoning), I-11 (Conflict Lifecycle) | Policy и reasoning — поверх authority + conflict resolver. |
| **Фаза D** | I-4 (Naming), I-8 (Revision), I-10 (Decision History) | Документация + процессы. |
| **Фаза E** | I-12 (Scalability) | Не срочно, но заложить поля (domain, ttl_days) в Phase 2 для forward-compat. |

---

**Рекомендация:** включить improvements I-1 и I-2 в Phase 2 RFC (создание таблиц) как forward-compatible поля — они требуют ALTER TABLE, но не требуют немедленной реализации API. Остальные — в соответствующие фазы RFC.

**Принцип архитектурной эволюции соблюдён:**
- ✅ Все 12 improvements — ADDITIVE (ALTER TABLE, новые таблицы, новые модули)
- ✅ Ни один раздел RFC не переписан — только расширен
- ✅ Совместимость с существующей архитектурой сохранена
- ✅ Каждый improvement использует существующие компоненты (KnowledgeEngine, GraphIndex, event_log)
