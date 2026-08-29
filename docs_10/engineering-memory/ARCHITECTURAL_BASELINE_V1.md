# ARCHITECTURAL_BASELINE_V1.md — Канонический архитектурный baseline

> **Статус:** CANONICAL · единая точка отсчёта для будущих ADR (ADR-017+, ADR-018/019/020).
> **Источник:** сводный вывод FORENSICS_104_105_106_107 (промты 104/105/106/107), верифицирован кодом 2026-08-22.
> **Принцип:** «что уже система / что набор механизмов / что только документация / чего не хватает» (promt107 §27).
> **Режим:** FORENSIC ONLY — констатация фактов; решения и реализация — через отдельные ADR.

---

## 1. Что УЖЕ является СИСТЕМОЙ (связано сквозным контрактом)

**Buffy Forge-слой** — единственный домен, где механизмы соединены сквозным контрактом:

```
Workspace(L-1) → Project(L-2) → ForgePipeline(L-3) → ForgeRegistry(L-4) → ForgeFacade
```

- Жизненный цикл: FORGE → CHECK → BUILD → POLICY → TEST → DEPLOY → REPORT (7 стадий; `forge_pipeline.py:380`); статусы UNFORGED → DEPLOYED/FAILED; B10-валидация; chain-runner 14 ролей (LIGHT/HEAVY/CONDITIONAL).
- Тесты: test_forge_pipeline/registry/facade/chain_cli/chain_real_integration.
- **Capability-роутинг** (data-driven): `SmartRouter/ModelCatalog` (core_02/router.py) + `ModelGateway` + closed-set capability tokens.

### Execution-пути (верифицировано кодом)

| Path | Статус | Evidence |
|------|--------|----------|
| **Path A:** Project → ForgeFacade → ForgePipeline → ForgeRegistry → Artifact | **REAL** | Forge-слой, тесты |
| **Path B:** Opportunity → capability → select_forge → ForgeFacade.run_chain | **REAL** (мост СШИТ) | `scripts_01/opportunity_engine.py:949`, `core_02/factory_base.py:368`, `scripts_01/forge.py:490` (cmd_chain); forge_id адвизорный (traceability), исполнение по role_ids. *(Evidence-строки уточнены 2026-08-22 по code-verification: фактический вызов run_chain — :949/:368/:490, не :941/:361.)* |

## 2. Что является НАБОРОМ РАБОТАЮЩИХ МЕХАНИЗМОВ (не связанных между собой)

| Кластер | Механизмы | Проблема |
|---------|-----------|----------|
| **Memory/Knowledge** ×4 | memory_engine, knowledge_engine, graph_index, engineering_memory | нет единого source-of-truth |
| **Role** ×2 | Blueprint pipeline-роли (14-17) vs roles.py collab-роли (6) | оба называют себя «роли», разные слои |
| **Task** ×2 | task_manager.py (SQLite) vs orchestrator.py | два механизма управления задачами |
| **Tool** ×2 | tool_runtime.py (BaseTool×5) vs mcp_server.py (McpTool) | два tool-контракта |
| **Registry** ×6 | workspace, scenario, factory, forge, missing, tool | разные форматы/хранилища |
| **Workspace** ×2 | workspace.py (YAML) vs workspace_registry.py (SQLite) | **RESOLVED BY DESIGN: ADR-017** (SQLite = mapping/privacy, YAML = конфиг, sync-контракт) |

## 3. Что является ТОЛЬКО ДОКУМЕНТАЦИЕЙ (DOCUMENTED ONLY)

| Концепт | Реальность |
|---------|------------|
| Сквозной `Project → Scenario → Factory → Forge → Artifact` как ОДИН конвейер | опровергнут; реальны 2 независимые ветки Path A + Path B (обе REAL) |
| AGENT как класс с lifecycle | единого проектного Agent-класса с lifecycle нет; роли stateless. **ЗАКРЫТ (ADR-019):** `core_02/agent_base.py::Agent` (ABC) + `AgentLifecycle` (forward-only DAG) + `route_model`/`run_forge` сервисы. Есть `IAgent` (ABC, `interfaces.py:50`), mesh-слой `AgentNode/AgentMesh` (`distributed_agents.py:111/:249`), исполнители ролей `BaseRoleExecutor` (`role_executor.py:49`) — Agent-класс теперь является официальным интерфейсом поверх них (additive) |
| PROJECT ROLE (Owner/PM/Contributor) ≠ AGENT ROLE | roles.py смешивает |
| Integration/Connector/Adapter слой | мосты (TG/MCP/phone) вшиты в ядро. **ЗАКРЫТ (ADR-020):** `core_02/integration_base.py::IntegrationAdapter` (ABC) — единый контракт для внешних мостов: AuthSpec (none/bearer/vault/chat_id_scope/phone_scope) + intent→capability роутинг (закрытый словарь `INTENT_CAPABILITY_MAP`) + нормализованный вход/выход (AdapterRequest/Response) + call_platform → SmartRouter (§7.3). Существующие мосты (`telegram_contract.py`, `mcp_server.py`, `phone_control_mcp.py`, `sdk_bridge.py`, `bridge_layer.py`) — нетронуты (аддитивно) |
| Sandbox / tenant isolation | отсутствует (runtime-ACL нет); единая доверенная зона Termux. Есть только декларативный реестр 18 границ `core_02/boundaries_v17.py` (BState ENFORCED/PARTIAL/DOCTRINE) — спецификация, не runtime-изоляция |

## 4. Чего РЕАЛЬНО НЕ ХВАТАЕТ (приоритизация)

| Приоритет | Контракт | Статус |
|-----------|----------|--------|
| **P0** | Единая Workspace модель | ✅ **ЗАКРЫТ** (ADR-017, sync_from_config в core_02/workspace_registry.py, v5.189.83) |
| **P0** | Sandbox/tool-ACL для внешних мостов (ShellTool) | открыт |
| **P1** | Factory→Forge execution-мост | ✅ **ЗАКРЫТ** (Path B REAL, evidence выше) — контракт фиксирует ADR-018 |
| **P1** | Agent base class + lifecycle | ✅ ЗАКРЫТ (ADR-019, core_02/agent_base.py) |
| **P1** | Integration adapter boundary | ✅ **ЗАКРЫТ** (ADR-020, core_02/integration_base.py) |
| **P2** | Дубли: task ×2, tool ×2, memory ×4 | открыты |
| **P3** | Репозиторий: нумерация каталогов, смешение доменов | открыт |
| **P4** | Enhancements: семантические теги, метрики, UX | после P0-P2 |

## 5. Правила для будущих ADR

1. Новый ADR ссылается на этот файл как baseline (§1-§4) и НЕ переоткрывает факты.
2. Code-first: решение должно быть верифицируемо (CLAIM → FILE → SYMBOL, формат EVIDENCE_LEDGER).
3. Additive Architecture (CAN-16): новая сущность — аддитивный слой, не переписывание.
4. Реализация — только после утверждения ADR (promt107 §28).
5. Forensic-коррекции фиксируются в AUDIT_DELTA (для внешних аудиторов).

---

## История

- **v1.1 (2026-08-22):** правки по `BASELINE_V1_CODE_VERIFICATION.md` (7 находок): evidence-строки Path B → :949/:368/:490 (`scripts_01/forge.py`); lifecycle 6→7 стадий (добавлен POLICY); §3 AGENT — уточнение (IAgent/AgentNode/BaseRoleExecutor есть, единого проектного lifecycle нет); §3 Sandbox — упоминание `boundaries_v17.py` (декларативный реестр). Код не менялся (промт 108 §1).
- **v1.0 (2026-08-22):** создан по итогам FORENSICS_104_105_106_107 v5.189.75; включает коррекцию Path B (PARTIAL→REAL, code-verified) и ADR-017 (Workspace P0 design closed).
- **Источники:** `FORENSICS_104_105_106_107/_consolidated/UNIFIED_CONCLUSIONS.md`, `EVIDENCE_LEDGER_MERGED.md`, `AUDIT_DELTA.md`; `platform_architectural_inventory_34/CONTRACT_GRAPH.md`.
