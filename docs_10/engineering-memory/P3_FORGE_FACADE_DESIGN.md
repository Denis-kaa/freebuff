# P3 — ForgeFacade: Дизайн (Задача 1) + Реализация (Задача 2)

> **Статус:** DESIGN + IMPLEMENTED (промт 70, Миссия 2)
> **Основание:** `P3_BLUEPRINT_FORGE_FACADE_RESEARCH.md` (Задача 0: 15/17 ролей — производственные стадии)
> **Дата:** 2026-08-10

---

## 0. Explain-first

Задача 0 показала: цепочка из 15 ролей **декларативна, но не исполняется** (15/17 — классификация Задачи 0, включая presale-трек response_writer; Facade-scope = 14; `resolve_pipeline()` вызывается только из тестов; `wizard.py` выбирает одну роль; grep `forge` в scenario/wizard → 0). Значит, Facade должен:

1. **СОХРАНИТЬ §7.3 boundary** — Scenario/роли НЕ получают прямой доступ к `ForgePipeline` (это требование-инвариант, не рекомендация).
2. **Дать явный, опциональный переход** — после завершения роли (например, `developer` в цепочке) Facade может ИНИЦИИРОВАТЬ Forge-прогон **по явному запросу** (не автоматически, не молча).
3. **Сохранить UNFORGED-семантику** — Facade не меняет, что значит UNFORGED; только даёт путь его изменить через явный вызов.
4. **Быть узким** — только для 14 pipeline-ролей (12 ядро + frontend + devops), не для 17; справочные (orchestrator, context_keeper) не трогаем; response_writer (presale-трек) — вне основного scope. *(Задача 0 классифицировала 15/17 производственных стадий С УЧЁТОМ response_writer; из Facade-scope он исключён → 14.)*

## 1. Архитектура Facade

```
Blueprint v3 роль (developer, tester, ...)  ── явный запрос ──►  ForgeFacade
                                                                     │
                                     ┌───────────────────────────────┤
                                     │ 1. can_initiate(role_id)      │  ← gate: только pipeline-роли
                                     │ 2. register_project()         │
                                     │ 3. ForgePipeline.run()        │  ← ЕДИНСТВЕННАЯ точка входа
                                     │ 4. forge_registry.record_run()│  ← фиксация результата
                                     └───────────────────────────────┘
                                                                     │
                                                     forge_registry.yaml (status)
```

**Ключевое:** `ForgePipeline` инстанцируется ТОЛЬКО внутри `ForgeFacade`. Scenario/роли/`wizard_lib` по-прежнему не импортируют `core_02.forge_pipeline` (grep-инвариант §7.3 сохраняется).

## 2. API (core_02/forge_facade.py)

```python
PIPELINE_ROLES: frozenset[str***REMOVED*** = frozenset({
    # 14 стадий цепочки (12 ядро + frontend + devops; Задача 0: 15/17 — с response_writer).
    # НЕ включает orchestrator/context_keeper/response_writer.
    "explainer", "lisa", "risk", "decomposer", "architect", "auditor",
    "developer", "frontend", "devops", "tester", "fixer",
    "acceptance", "documenter", "retrospective",
***REMOVED***)

@dataclass(frozen=True)
class ForgeFacadeResult:
    project_id: str
    requested_by_role: str
    status_before: str          # обычно UNFORGED
    status_after: str           # DEPLOYED / FAILED (из record_run)
    overall: str                # ok / failed
    stages: tuple[dict, ...***REMOVED***    # сводка стадий
    initiated_explicitly: bool  # всегда True — фиксация «не молча»

class ForgeFacade:
    def __init__(self, registry: ForgeRegistry | None = None,
                 dry_run: bool = False, workspace_steps_policy: str = "optional"): ...

    def can_initiate(self, role_id: str) -> bool:
        """Gate: только pipeline-роли могут инициировать Forge-прогон."""
        return role_id in PIPELINE_ROLES

    def initiate_forge(self, project: Project, requested_by_role: str,
                       hooks: dict | None = None,
                       skip: set[str***REMOVED*** | None = None) -> ForgeFacadeResult:
        """ЯВНЫЙ запрос на Forge-прогон от завершившей артефакт роли.

        - Не вызывается автоматически; вызывающий обязан передать роль.
        - Справочные роли (orchestrator/context_keeper) → ValueError (gate).
        - Фиксирует результат через forge_registry.record_run().
        """
```

## 3. Подтверждение соблюдения границ (промт 70 Задача 1 п.1-3)

| Требование | Как соблюдено |
|------------|---------------|
| §7.3: Direct Forge call из Scenario — НЕТ | `ForgePipeline` импортируется только в `forge_facade.py`; scenario/wizard_lib не трогаются (0 новых импортов) |
| Явный, опциональный переход (не автоматически, не молча) | `initiate_forge()` — единственный метод; требует `requested_by_role`; результат содержит `initiated_explicitly=True` + полную сводку |
| UNFORGED-семантика сохраняется | Facade НЕ переопределяет статусы; `record_run()` сам вычисляет DEPLOYED/FAILED из overall — та же логика, что в `scripts_01/forge.py:151` |
| Пропорционально находке (Задача 2) | `PIPELINE_ROLES` = ровно 14 стадий (12 ядро + frontend + devops); справочные роли и response_writer вне |
| Additive Architecture | Новый файл `core_02/forge_facade.py`; существующие модули не изменены |

## 4. Задача 2 — Реализация

Файл: `core_02/forge_facade.py` (~120 строк). Тесты: `tests_09/test_forge_facade.py`.

Покрытие тестами:
- `can_initiate`: pipeline-роль True, справочная False.
- `initiate_forge` с ролью `developer` → результат DEPLOYED/FAILED, `initiated_explicitly=True`, `status_before=UNFORGED`.
- `initiate_forge` со справочной ролью (`orchestrator`) → `ValueError` (gate сработал).
- `dry_run=True` → стадии skipped, но flow (register → record_run) выполняется.
- **Инвариант §7.3:** grep `forge` в `scenario_registry.py`/`wizard_lib.py` остаётся 0 (регрессия).

## 5. Cross-links

- `P3_BLUEPRINT_FORGE_FACADE_RESEARCH.md` (Задача 0 — классификация 15/17)
- `P3_IDEA_EXPLORER_RUN_FORGE_FACADE.md` (pre-flight гейт W-14: IDEA EXPLORER v2.0 на идее ForgeFacade-фабрики → chain-runner v1, эксперимент H1)
- `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §7.3 (§7.3 boundary), §7.6 gap 2
- `core_02/forge_pipeline.py` · `core_02/forge_registry.py` · `scripts_01/forge.py:151`
- `pompts_11/071_02_prompt_architect_1_7.md` Миссия 2

---

## 6. Chain-Runner (Шаг 3 ROADMAP §18, v5.157.0)

> **Статус:** IMPLEMENTED 2026-08-10 (additive к §2 API; CAN-16 сохраняет §1–§5 без изменений).
> **Forward-action source:** `P3_IDEA_EXPLORER_RUN_FORGE_FACADE.md` §18 SELECTED CONCEPT = chain-runner v1 (реализован; OPEN QUESTION закрыт).
> **Cross-link target:** `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §34 (Implementation Roadmap UPDATE) + §36 (forward-reference v0.1 sub-block).

### 6.1 Назначение

`ForgeFacade.run_chain(project, role_ids)` — выполнение полной (или partial) цепочки из 14 pipeline-ролей в порядке `PIPELINE_CHAIN` (linear, из Задачи 0). Каждая роль обрабатывается в одном из 3 режимов в зависимости от её класса:

- **LIGHT (8 ролей; analysis + documentation):** `mode="check_only"` — через `RoleArtifactValidator.validate(role_id)` (шаг 2 ROADMAP, v5.156.0). Только проверка наличия файлов-артефактов; `initiate_forge` (full Forge-чикл) НЕ вызывается, поскольку артефакты генерируются ролью, не Forge'ом.
- **HEAVY (4 роли; code + test):** `mode="full_cycle"` — через `initiate_forge(... , project_read_only=True)`. Полный чикл ForgePipeline FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT. `project_read_only=True` enforce B2 R-124 (Forge не мутирует артефакты Project) — критично для chain.
- **CONDITIONAL (2 роли; frontend + devops):**
  - `frontend`: `mode="conditional_skip"` если `project.type != "web"` (status="skipped", details содержит project.type); иначе `mode="full_cycle"`.
  - `devops`: всегда `mode="full_cycle"` (condition: always в blueprints_v3/registry.yaml).

### 6.2 API (additive к §2)

```python
LIGHT_ROLES: frozenset[str***REMOVED*** = frozenset({
    "explainer", "lisa", "risk", "decomposer",
    "architect", "auditor", "documenter", "retrospective",
***REMOVED***)  # 8 ролей: аналитические/документационные

HEAVY_ROLES: frozenset[str***REMOVED*** = frozenset({
    "developer", "tester", "fixer", "acceptance",
***REMOVED***)  # 4 роли: code/test

@dataclass(frozen=True)
class ChainStage:
    role_id: str
    mode: str            # "check_only" | "full_cycle" | "conditional_skip"
    status: str          # "ok" | "partial" | "missing" | "run_ok" | "run_failed"
                         # | "init_error" | "skipped"
    details: str
    duration_s: float = 0.0

@dataclass(frozen=True)
class ChainRun:
    project_id: str
    project_root: str
    stage_count: int
    chain: Tuple[ChainStage, ...***REMOVED***
    overall: str         # "ok" | "partial" | "failed" | "degraded"
    started_at: str
    finished_at: str
    validation_registry_status: str  # "loaded" | "missing" | "unreadable" | "not_run"
    validation_summary: Optional[ValidationSummary***REMOVED*** = None

class ForgeFacade:
    # additive к §2:
    def run_chain(self, project: Project,
                  role_ids: Optional[Tuple[str, ...***REMOVED******REMOVED*** = None,
                  *,
                  registry_path: Optional[Path***REMOVED*** = None,
                  compose_artifact_check: bool = True,
                  project_read_only: bool = True,
                  skip_full_cycle_stages: Optional[Set[str***REMOVED******REMOVED*** = None
                 ) -> ChainRun: ...
```

### 6.3 Контрактные гарантии (ВАЖНО для архитектуры)

| Констрейнт | Где enforce | Чего нет |
|------------|-------------|----------|
| §7.3 (Scenario не видит ForgePipeline) | run_chain → `self.initiate_forge(...)` (единственный мост) — НЕ прямой `ForgePipeline(...)` | прямого импорта |
| UNFORGED через record_run | `initiate_forge(...)` → `pipe.run(...)` → `registry.record_run(...)` | pre-проверки статуса |
| B2 R-124 (Forge не мутирует Project) | `initiate_forge(... project_read_only=True)` default в run_chain | mutations RUNNABLE.md между chain stages |
| ADDITIVE | только `core_02/forge_facade.py` расширен | модификации workspace.py/forge_pipeline.py/forge_registry.py |
| Graceful degradation | registry missing → `overall="degraded"` (НЕ "failed") | hard fail |
| Chain-soft-failure | try/except в full_cycle (ValueError + Exception → `status="init_error"`) | catastrophic abort |

### 6.4 Status decision tree (overall)

Decision tree для `ChainRun.overall` (последовательно проверяется):

1. **"failed"** — `len(stages) == 0` ИЛИ все full_cycle стадии `status="init_error"` (chain прерван на каждой тяжёлой роли).
2. **"degraded"** — `validation_registry_status ∈ {"missing", "unreadable"***REMOVED***` И хоть что-то отработало. Реестр недоступен, но chain продолжил через fallback (`DEFAULT_ROLE_OUTPUTS`).
3. **"partial"** — есть `imperfect statuses = {partial, missing, run_failed, init_error***REMOVED***` И не все full_cycle "init_error".
4. **"ok"** — все статусы ∈ `{ok, run_ok, skipped***REMOVED***` И registry loaded.

### 6.5 H4 (FORGE-pending статус): REFUTED — новые STATUSES не нужны

Гипотеза из `P3_IDEA_EXPLORER_RUN_FORGE_FACADE.md` §18 OPEN QUESTIONS:
> «расширять ли STATUSES (role_done/forge_pending — H4)»

**Вердикт (2026-08-10, v5.158.0 docs-only):** H4 REFUTED. `forge_registry.STATUSES` остаются 6-ю значениями (`UNFORGED`, `CHECKING`, `BUILDING`, `TESTING`, `DEPLOYED`, `FAILED`). Per-role прогресс хранится в `ChainRun.chain` (frozen dataclass) и сохраняется в `ForgeStatus.last_pipeline` через `record_run` → `initiate_forge`. H4 use-case «узнать курсор chain для resume» закрывается существующим `last_pipeline["chain"***REMOVED***` (additive forward к chain-resume в CLI).

Три аргумента:
- **SRP (SOLID):** `forge_registry` отвечает за глобальное состояние проекта (артефакты на FS), а не за per-role прогресс оркестратора.
- **B10/R-127 invariant сохранён (v5.153.0):** UNFORGED ≠ UNTESTED; промежуточный «CHAIN_PARTIAL» / «ROLE_DONE» сломал бы machine-checkable schema.
- **KISS / overlap:** `ChainStage.status` уже фиксирует per-role прогресс в `ChainRun`. Расширение STATUSES дублирует информацию (overlap risk, drafting drift риск).

**Forward-path для resume (рекомендация):** реализовать в CLI `scripts_01/forge.py forge chain --resume` через парсинг `registry.get_project_status(pid).last_pipeline["chain"***REMOVED***` (последний `ok`/`run_ok` индекс + `role_ids[that_idx+1:***REMOVED***`). Кодирование — отдельная итерация v5.158+.

### 6.6 Cross-references (additive updates)

- `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §34 (First Vertical Slice, Phase 4) — UPDATE-блок: chain-runner реализован поверх C3 (Forge Pipeline+Evolution). См. §34.4 Implementation Roadmap → STATUS UPDATE.
- `WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` §36 (Финальный вердикт) — sub-block §36.x: chain-runner готов как forward-action для v0.1.
- `P3_IDEA_EXPLORER_RUN_FORGE_FACADE.md` §16/§18 SELECTED CONCEPT (реализовано; H4 REFUTED §6.5).
- `core_02/forge_facade.py` — имплементация (`run_chain`, `ChainStage`, `ChainRun`, `LIGHT_ROLES`, `HEAVY_ROLES`).
- `tests_09/test_run_chain.py` — 26 тестов в 6 классах (additive).
- ADR-013 (ForgeFacade Blueprint v3 Bridge) — §7.3 boundary сохраняется.
- `CHANGELOG.md` v5.157.0 — release notes (chain-runner SHIPPED); v5.158.0 — H4 docs-only.

### 6.7 Forward (следующие итерации)

- CLI `forge chain --resume` через `last_pipeline["chain"***REMOVED***` (v5.158+).
- `forge chain --dry-run` — preview + cost estimate через `RoleArtifactValidator`.
- Monkeypatch тесты для chain-soft-failure (`init_error` path verify).
- Реальная интеграция: `run_chain` на `vkusvill_demo` + `interior_planner` (фиксация реальной стоимости вызова).

---

## 7. Cross-link-манифест (v5.158.0 update)

Этот additendum CPS §6 добавляет следующие cross-link ссылки (CAN-16 ADDITIVE):

- `docs_10/engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md`:
  - §34 UPDATE-блок (Implementation Roadmap phases 4.1–4.5 все CLOSED; cross-reference к chain-runner в RESEARCH §34).
  - §36 sub-block §36.x (forward-reference v0.1; chain-runner + H4 REFUTED).
