# ADR-017: Единая Workspace модель — SQLite registry (mapping) + YAML (конфиг) + аддитивный sync-контракт

> **Статус:** Accepted (реализован в core_02/workspace_registry.py::sync_from_config, v5.189.83)
> **Дата:** 2026-08-22
> **Связанные:** ADR-013 (ForgeFacade Blueprint v3 bridge), promt107 §N (Workspace ×2), CON-19 (single-source-of-truth), CON-14 (fail-loud), CON-21 (anti-fragility), B1 (Workspace↔Project boundary).

## Context

Forensic-проходы (promt104 §N, promt107 §N) выявили **две конкурирующие модели Workspace** — два source-of-truth об одном домене:

| | A: `core_02/workspace.py` (YAML) | B: `core_02/workspace_registry.py` (SQLite) |
|---|---|---|
| Хранилище | `workspace.yaml` / `project.yaml` | `data_13/context.db` (таблицы `workspaces`, `workspace_projects`) |
| Сущности | `Workspace` (L-1) + `Project` (L-2) dataclass | `Workspace` + `Project` dataclass (свои) |
| Содержит | `steps_policy`, `default_environment`, `type/stack/roles/contracts/requirements.steps`, список проектов | `path → workspace_slug` mapping, `owner_chat_id`, `status`, `description`, `created_at` |
| Кто читает | Forge-слой: `forge_pipeline.py`, `forge_facade.py`, `forge.py`, `opportunity_engine.py`, `factory_base.py`, `capability_gap_auditor.py`, `role_executor.py` | Runtime/интеграции: `telegram_bot.py`, `scan_projects.py`, `forge.py register`, `work_area_view.py`, `mcp_fastapi.py` |
| Инвариант | — | **Privacy:** `workspace_projects.path` = PRIMARY KEY → путь принадлежит максимум ОДНОЙ workspace; `assert_path_privacy` поднимает `PrivacyViolationError` (schema-level enforcement) |
| Загрузка | per-invocation (перечитывает YAML) | персистентный, queryable (SQL) |

**Проблема:** домены пересекаются («workspace + projects»), но каждая модель знает только свою часть правды: YAML не знает владельца/приватности, SQLite не знает `steps_policy`/конфига проекта. Drift неизбежен (например, проект объявлен в `workspace.yaml`, но не зарегистрирован в registry → privacy-guard не видит его владельца; и наоборот — TG-бот регистрирует workspace, которой нет в YAML). Это P0-блокер из UNIFIED_CONCLUSIONS §4.

## Decision

Ввести **двухслойную модель с явной границей ответственности** и **аддитивным sync-контрактом** (CAN-16: ни одна из существующих моделей не переписывается):

### 1. Разделение ответственности (что является source-of-truth)

| Слой | Source-of-truth | Вопросы, на которые отвечает |
|---|---|---|
| **SQLite registry** (`workspace_registry.py`) | **Операционное состояние: `path → workspace` mapping, владение, статус, приватность** | «Какой workspace владеет этим путём?», «Можно ли этому агенту доступ к пути?», «Какие workspace существуют?» |
| **YAML** (`workspace.yaml` / `project.yaml`) | **Декларативная конфигурация (интент)** | «Какая `steps_policy`?», «Какой `default_environment`?», «Какой stack/roles/contracts у проекта?», «Какие проекты объявлены?» |

Правило: **`workspace_registry` НЕ хранит конфиг (steps_policy и пр.), `workspace.py` НЕ хранит владение (owner/status/privacy).** Каждое поле имеет ровно одного владельца (CON-19).

### 2. Аддитивный sync-контракт (YAML → SQLite, one-way)

Новый аддитивный метод `WorkspaceRegistry.sync_from_config(workspace_root)` (реализуется в отдельном заходе, НЕ в рамках этого ADR):

```python
def sync_from_config(self, workspace_root: Path) -> SyncReport:
    """YAML (workspace.yaml/project.yaml) → SQLite (workspaces/workspace_projects).

    One-way, idempotent, additive:
      - workspace не существует → INSERT (slug = _slugify_name(name), как в registry)
      - workspace существует → skip (не перезаписывать name/owner/status)
      - path (abs, resolved) не привязан → INSERT в workspace_projects
      - path уже привязан к ДРУГОЙ workspace → warn + skip (privacy invariant)
      - УДАЛЕНИЙ нет: отсутствие проекта в YAML НЕ удаляет строку registry
    Возвращает SyncReport(created_ws, created_projects, skipped, conflicts).
    """
```

**Инварианты контракта:**
1. **One-way:** синхронизация идёт только YAML → SQLite. SQLite никогда не пишет в YAML (владелец/статус — runtime-состояние, не декларатив).
2. **Idempotent:** повторный запуск не меняет состояние (все created=0, skipped=прежние).
3. **Additive (CAN-16):** только INSERT/SKIP, никогда DELETE/UPDATE чужого поля. Удаление проекта из YAML — намеренное действие, отдельный будущий `--prune` (вне scope).
4. **Privacy-инвариант сохраняется:** конфликт «path уже в другой workspace» → warn + skip (CON-21 anti-fragility, как `seed_defaults`), никогда не краш.
5. **Slug-алгоритм единый:** `_slugify_name` из `workspace_registry.py` — единственный источник истины (CON-19).
6. **Path-канонизация:** registry хранит абсолютный resolved path; YAML — относительные пути под `workspace_root` (как `DEFAULT_WORKSPACES` в seed).
7. **Observability:** результат синхронизации возвращается отчётом (`SyncReport`) и логируется (created/skipped/conflicts) — для оператора и дрейф-детекта.

### 3. Порядок резолва вопросов у потребителей

- «Где проекты/какая политика?» → **YAML** (`Workspace.load`/`Project.load` — как сейчас, без изменений).
- «Кто владелец/какой workspace для пути? Есть ли privacy-нарушение?» → **SQLite** (`find_workspace_for_project`, `assert_path_privacy` — как сейчас, без изменений).
- «Вновь объявленный в YAML проект должен быть виден registry» → **sync_contract** (`sync_from_config` — новый аддитивный вызов; точки входа: `scan_projects.py`, `forge.py register`, TG-бот batch).

## Alternatives

- **(а) SQLite — единый source-of-truth для ВСЕГО (включая конфиг)** — отвергнуто: `steps_policy`/конфиг читаются per-invocation Forge-слоем из YAML; перенос в SQLite добавил бы read-зависимость от БД в каждый forge-прогон и разорвал `Project.load`-путь (forge_pipeline/forge_facade/forge.py) без выгоды.
- **(б) YAML — единый source-of-truth для ВСЕГО (включая владение)** — отвергнуто: нет queryable-состояния и schema-level privacy-инварианта; `owner_chat_id`/`status` — runtime-состояние, не декларативный конфиг; TG-бот и scan_projects работают через SQLite.
- **(в) Полное слияние моделей в одну (Workspace = YAML + SQLite внутри)** — отвергнуто для текущего этапа: потребует переписывания всех потребителей (forge_pipeline, forge_facade, forge.py, telegram_bot, opportunity_engine, work_area_view, mcp_fastapi), нарушает Additive Architecture и promt107 §28 (код — только после утверждения ADR). Зафиксировано как будущий кандидат.
- **(г) Двухслойная модель + аддитивный sync-контракт** — **ВЫБРАНО**: явная граница «конфиг (YAML) vs состояние (SQLite)», минимум изменений (только новый аддитивный метод), privacy-инвариант остаётся на уровне схемы, дрейф становится детектируемым через `SyncReport`.

## Trade-offs

- **Выигрываем:** устранён P0-блокер «Workspace ×2 source-of-truth» (UNIFIED_CONCLUSIONS §4); явный ответ «что где источник правды»; privacy-инвариант сохраняется schema-level; дрейф YAML↔registry детектируем (SyncReport + тесты); аддитивность — ноль переписанных потребителей.
- **Теряем:** две системы остаются (YAML + SQLite) и требуют синхронизации (митигировано: idempotent-контракт + тесты + observable-отчёт); проект, объявленный в YAML, до первого sync невидим registry (митигировано: sync вызывается из существующих точек регистрации).
- **Сознательно вне scope:** удаление строк registry при удалении проекта из YAML (`--prune` — будущий заход); объединение моделей в одну (альтернатива (в) — будущий кандидат).

## Consequences

- **Реализация (отдельный заход, после утверждения):** аддитивный `WorkspaceRegistry.sync_from_config(workspace_root) -> SyncReport` + вызовы из `scan_projects.py` / `forge.py register` / TG-бот batch (без изменения существующих методов).
- **Тесты:** idempotency (двойной sync → created=0), conflict-skip (path в другой workspace → warn+skip, PrivacyViolationError НЕ поднимается), privacy-инвариант сохранён, slug-стабильность (transliteration), one-way (SQLite→YAML записи нет).
- **Документация:** `CONTRACT_GRAPH.md` (promt107) — строка `Workspace ↔ Project: REAL + DUPLICATED (2 модели)` помечается `RESOLVED BY DESIGN (ADR-017)`; `UNIFIED_CONCLUSIONS.md` §4 P0-блокер «единая Workspace модель» — «design зафиксирован (ADR-017), реализация отдельным заходом».
- **Backward compatibility:** обе модели продолжают работать как сейчас; существующие тесты (`test_workspace.py`, `test_workspace_registry.py`) не затрагиваются.
- **Реестры:** строка в `DECISIONS.md` + запись в `DOCUMENT_REGISTRY.md`.
