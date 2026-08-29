# BASELINE_V1_CODE_VERIFICATION.md — Верификация ARCHITECTURAL_BASELINE_V1 против кода

> **Статус:** ANALYTICAL (forensic-only, промт 108 §1: код не изменялся, только аналитический документ).
> **Дата:** 2026-08-22
> **Цель:** перепроверить claims `ARCHITECTURAL_BASELINE_V1.md` §1–§4 против фактического кода
> (Path A/B REAL, evidence-строки) и зафиксировать расхождения.
> **Метод:** CLAIM → FILE:LINE → VERDICT (формат EVIDENCE_LEDGER, промт 108 §25).
> **Принцип:** код — источник истины; документация — гипотеза (промт 108, критическое правило).

---

## 1. Path B — evidence-строки baseline (СВЕРКА)

Baseline §1: `opportunity_engine.py:941`, `factory_base.py:361`, `forge.py:490`.

| Claim (baseline) | Фактический код | VERDICT |
|------------------|-----------------|---------|
| `forge.py:490` | Файла `core_02/forge.py` **НЕТ**. Существует `scripts_01/forge.py:490` (`cmd_chain` → `run = facade.run_chain(`) | **PATH DIVERGENCE** — baseline неоднозначен: без префикса читается как core-модуль, которого нет. Корректный путь — `scripts_01/forge.py:490` (так в ADR-018). Сам вызов на :490 подтверждён. |
| `opportunity_engine.py:941` | Функция `execute()` (scripts_01/opportunity_engine.py:~856–1019). **Строка 941 = `_emit_event(`**; фактический вызов `facade.run_chain(project, role_ids=role_ids)` — на **:949** | **LINE DRIFT** (−8) — ссылка внутри той же функции, но не на сам вызов. Семантика (execute → select_forge → run_chain) подтверждена. |
| `factory_base.py:361` | **Строка 361 = `return {`** (ветка «project unresolved»); фактический вызов `facade.run_chain(project, role_ids=request.role_ids, project_read_only=True)` — на **:368** | **LINE DRIFT** (−7) — ссылка внутри `execute()`, но не на сам вызов. Семантика подтверждена. |
| Мост СШИТ в 3 точках | `opportunity_engine.py:949` (execute), `factory_base.py:368` (BaseFactory.execute), `scripts_01/forge.py:490` (cmd_chain) | **CONFIRMED** — Path B REAL. |

**Итог по evidence-строкам:** мост существует и работает (CONFIRMED), но 2 из 3 номеров строк в baseline
смещены, а путь `forge.py` неоднозначен. Кандидаты на правку baseline: `opportunity_engine.py:949`,
`factory_base.py:368`, `scripts_01/forge.py:490`.

---

## 2. Path A — подтверждение

| Claim | Фактический код | VERDICT |
|-------|-----------------|---------|
| ForgeFacade → ForgePipeline → ForgeRegistry | `forge_facade.py:26` `from core_02.forge_pipeline import ForgePipeline`; `:27` `ForgeRegistry`; `:321 initiate_forge`; `:361 pipe = ForgePipeline(...)`; `:370 status_after = self.registry.record_run(...)` | **CONFIRMED** |
| ForgePipeline инстанцируется только здесь | Комментарий `forge_facade.py:7` «ForgePipeline инстанцируется ТОЛЬКО здесь» + `:300` «Scenario/роли НЕ вызывают ForgePipeline напрямую» (промт 108 §8, §7.3) | **CONFIRMED** (grep-инвариант) |
| Жизненный цикл FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT, UNFORGED | `forge_pipeline.py:4,79,380` (7-stage: FORGE→CHECK→BUILD→POLICY→TEST→DEPLOY→REPORT), `:353-354` rollback → UNFORGED; `forge_facade.py:356` `status_before = UNFORGED` | **CONFIRMED** (уточнение: 7 стадий, не 6 — добавлен POLICY) |
| 14 pipeline-ролей, LIGHT/HEAVY/CONDITIONAL | `forge_facade.py:64` PIPELINE_ROLES (14 имён); `:83` PIPELINE_CHAIN (14); `:46-51` LIGHT_ROLES/HEAVY_ROLES; CONDITIONAL inline (frontend/devops) | **CONFIRMED** |
| B10-валидация | `forge_facade.py:58` (R-127/B10 machine-readable invariant) | **CONFIRMED** |
| Тесты test_forge_* | `test_forge_pipeline.py`, `test_forge_registry.py`, `test_forge_facade.py`, `test_forge_chain_cli.py`, `test_forge_chain_real_integration.py` — все существуют | **CONFIRMED** |

---

## 3. §2 «Набор механизмов» — сверка

| Claim | Фактический код | VERDICT |
|-------|-----------------|---------|
| Memory/Knowledge ×4 | `scripts_01/memory_engine.py`, `scripts_01/knowledge_engine.py`, `scripts_01/graph_index.py` + `docs_10/engineering-memory/` | **CONFIRMED** (уточнение: в `scripts_01/`, не `core_02/` — baseline путей не давал) |
| Role ×2: pipeline-роли vs collab-роли (6) | `scripts_01/roles.py:54` STANDARD_ROLES — ровно 6 (developer, reviewer, documenter, researcher, archiver, orchestrator) | **CONFIRMED** |
| Task ×2 | `scripts_01/task_manager.py`, `scripts_01/orchestrator.py` | **CONFIRMED** |
| Tool ×2 | `scripts_01/tool_runtime.py` (ToolRegistry :616), `scripts_01/mcp_server.py` | **CONFIRMED** |
| Registry ×6 | workspace_registry, scenario_registry, factory_registry, forge_registry, missing_registry (core_02/) + ToolRegistry (scripts_01/tool_runtime.py:616) | **CONFIRMED** (tool-реестр живёт в scripts_01, не в core_02) |
| Workspace ×2 (ADR-017) | `core_02/workspace.py`, `core_02/workspace_registry.py` | **CONFIRMED** |

---

## 4. §3 «DOCUMENTED ONLY» — сверка

| Claim | Фактический код | VERDICT |
|-------|-----------------|---------|
| «AGENT как класс с lifecycle — класса нет; роли stateless» | `core_02/interfaces.py:50` **`class IAgent(ABC)`** (run/ok/err/warn); `scripts_01/distributed_agents.py:111` **`class AgentNode`** + `:77 AgentNodeStatus` (PENDING/CONNECTING/ONLINE/BUSY/ERROR/OFFLINE) + `:249 AgentMesh` | **OVERSTATEMENT** — классы агентов ЕСТЬ (IAgent ABC, AgentNode dataclass, AgentMesh). Точнее: «единого **проектного** Agent-класса с lifecycle CREATED→ACTIVE→PAUSED→DONE/FAILED нет; есть IAgent-интерфейс (LEVIATHAN-паттерн) и mesh-слой AgentNode/AgentMesh». Формулировку baseline стоит уточнить. |
| «PROJECT ROLE ≠ AGENT ROLE — roles.py смешивает» | `scripts_01/roles.py:395 get_collab_role` — маппинг project→collab (orchestrator→owner, developer/reviewer→editor, остальные→viewer); STANDARD_ROLES — функциональные роли | **CONFIRMED** — роли функциональные, маппинг на collab-роли явный; смешение слоёв есть |
| «Integration/Connector/Adapter слой — мосты вшиты в ядро» | Мосты: `core_02/telegram_contract.py`, `scripts_01/mcp_server.py`, `scripts_01/phone_control_mcp.py`, `scripts_01/sdk_bridge.py::SmartRouterAdapter` (:31) | **CONFIRMED** — единого Integration layer нет; адаптеры разрознены |
| «Sandbox / tenant isolation — отсутствует» | `core_02/boundaries_v17.py` — **декларативный реестр** 18 границ (B1–B14+B15–B17+B-GUI, BState ENFORCED/PARTIAL/DOCTRINE); owner'ы ссылаются на `core_02/exec_layer`, `core_02/collab_layer`, `core_02/dis_engine` — **каталогов exec_layer/collab_layer НЕТ**, есть `dis_engine.py` | **CONFIRMED с уточнением** — sandbox-изоляции нет; boundaries_v17 — спецификация, не runtime-ACL |

---

## 5. Прочее (уточнения к §1)

| Claim | Фактический код | VERDICT |
|-------|-----------------|---------|
| «SmartRouter/ModelCatalog (core_02/router.py) + closed-set capability tokens» | `core_02/router.py:82 ModelCatalog`, `:239 SmartRouter`; но **KNOWN_CAPABILITIES живёт в `core_02/blueprint_v3.py:159`** (closed-set, ANTI-6b) | **CONFIRMED с уточнением** — closed-set определён в blueprint_v3.py, не router.py |
| Capability-роутинг data-driven | `factory_registry.py:272 select_forge` (status-priority production>material>design + tie-break); `resolve_by_policy` | **CONFIRMED** |

---

## 6. СВОДКА РАСХОЖДЕНИЙ (для AUDIT_DELTA / правки baseline)

| # | Severity | Расхождение | Правка в baseline |
|---|----------|-------------|-------------------|
| 1 | **MEDIUM** | `forge.py:490` — путь неоднозначен; файла `core_02/forge.py` нет | → `scripts_01/forge.py:490` |
| 2 | **LOW** | `opportunity_engine.py:941` — фактический вызов run_chain на :949 | → `opportunity_engine.py:949` |
| 3 | **LOW** | `factory_base.py:361` — фактический вызов run_chain на :368 | → `factory_base.py:368` |
| 4 | **MEDIUM** | §3 «AGENT — класса нет» — переоценка: есть IAgent (ABC), AgentNode, AgentMesh | переформулировать: «нет единого проектного Agent-класса с lifecycle; есть IAgent-интерфейс + mesh-слой» |
| 5 | **LOW** | §3 «Sandbox отсутствует» — верно, но стоит упомянуть boundaries_v17 (декларативный реестр 18 границ, не runtime-ACL) | добавить упоминание boundaries_v17 |
| 6 | **LOW** | §2 «Memory/Knowledge ×4», «Task ×2», «Tool ×2» — фактически в `scripts_01/`, не `core_02/` | уточнить пути (baseline их не указывал — опционально) |
| 7 | **LOW** | §1 lifecycle — в коде 7 стадий (FORGE→CHECK→BUILD→**POLICY**→TEST→DEPLOY→REPORT), baseline пишет 6 | уточнить: 7 стадий |

**Что подтверждено без изменений:** Path A REAL, Path B REAL (мост сшит), 14 ролей + LIGHT/HEAVY/CONDITIONAL,
B10/R-127, тесты test_forge_*, §2 наборы механизмов, §4 приоритеты P0–P1, ADR-017/018 семантика
(forge_id адвизорный, role_ids — единственный управляющий вход).

---

## 7. История

- **v1.0 (2026-08-22):** создан по запросу «Проверь ARCHITECTURAL_BASELINE_V1 против реального кода
  (Path A/B REAL: opportunity_engine.py:941, factory_base.py:361, forge.py:490)». Код НЕ изменялся (промт 108 §1).
- **Источники:** `ARCHITECTURAL_BASELINE_V1.md`, `ADR_018_Factory_Forge_Execution_Bridge.md`, фактический код
  `scripts_01/opportunity_engine.py`, `core_02/factory_base.py`, `core_02/forge_facade.py`,
  `core_02/forge_pipeline.py`, `scripts_01/forge.py`, `core_02/factory_registry.py`, `core_02/router.py`,
  `core_02/blueprint_v3.py`, `scripts_01/roles.py`, `scripts_01/distributed_agents.py`, `core_02/interfaces.py`,
  `core_02/boundaries_v17.py`.
