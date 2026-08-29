# 07_ENTRYPOINT_TRACEABILITY — Карта точек входа

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §9 (ENTRYPOINT FORENSICS)
> **Метод:** USER ACTION → CLI/API/TG/MCP → HANDLER → FUNCTION → ENGINE → EVENT → STORAGE → RESULT.

---

## 1. CLI entrypoints

### 1.1 `scripts_01/forge.py` (Forge CLI)

| Команда | Handler | Engine | Storage |
|---------|---------|--------|---------|
| `forge` | `cmd_forge` | ForgeFacade.initiate_forge | forge_registry.yaml |
| `check` | `cmd_check` | EnvDoctor + requirements | — |
| `status` | `cmd_status` | ForgeRegistry list | forge_registry.yaml |
| `register` | `cmd_register` | register_project_with_profile | forge_registry.yaml |
| `report` | `cmd_report` | TG notify | — |
| `step` | `cmd_step` | step-команда | — |
| `chain` | `cmd_chain` | ForgeFacade.run_chain (14 ролей) | forge_registry.yaml + artifacts |

### 1.2 `scripts_01/opportunity_engine.py` (Opportunity CLI)

| Команда | Handler | Engine | Storage |
|---------|---------|--------|---------|
| `discover [--rank***REMOVED***` | `_cli_discover` | discover_candidates (4 источника) | opportunities.yaml |
| `propose <id>` | `_cli_propose` | propose (ScenarioRegistry) | opportunities.yaml |
| `run <id> [--dry-run***REMOVED***` | `_cli_run` | execute → ForgeFacade.run_chain | opportunities.yaml + MemoryStore |
| `status <id>` | `_cli_status` | OpportunityStore.get | opportunities.yaml |
| `list [--status***REMOVED***` | `_cli_list` | OpportunityStore.by_status | opportunities.yaml |
| `rank` | `_cli_rank` | rank_candidates (read-only) | — |

### 1.3 `scripts_01/whim_capture.py` (Whim CLI)

| Команда | Handler | Engine | Storage |
|---------|---------|--------|---------|
| `capture` | `_cli_capture` | capture | whims.yaml |
| `list` | `_cli_list` | WhimStore.all | whims.yaml |
| `status` | `_cli_status` | WhimStore.get | whims.yaml |
| `triage` | `_cli_triage` | triage | whims.yaml |
| `promote` | `_cli_promote` | promote (→ Opportunity) | whims.yaml + opportunities.yaml |
| `defer` | `_cli_defer` | defer | whims.yaml |

### 1.4 Прочие CLI (scripts_01/)

`project_pulse.py` (list/stats/scan/watch), `graph_index.py` (main), `knowledge_engine.py` (main), `event_bus.py` (main), `plugin_api.py` (main), `memory_engine.py`, `research_web.py`, `lisa_estimator.py`, `forge_api.py` (server), `telegram_bot.py` (server).

## 2. REST API entrypoints (`scripts_01/forge_api.py`, FastAPI :8765)

| Endpoint | Handler | Engine |
|----------|---------|--------|
| `GET /` | `root` | content-negotiation (Accept:text/html → prototype/index.html; */* → JSON) |
| `GET /health` | health | — |
| `GET /api/v1/projects` | projects list | Workspace/ForgeRegistry |
| `GET /api/v1/projects/{slug***REMOVED***` | project detail | ForgeRegistry |
| `GET /api/v1/projects/{slug***REMOVED***/chain` | chain | ForgeFacade.run_chain |
| `GET /api/v1/metrics` | metrics | metrics engine |
| `GET /prototype` | prototype | static Lilac Dark dashboard |

## 3. MCP entrypoints (`scripts_01/mcp_server.py` — 40+ tools)

| Домен | Tools |
|-------|-------|
| roles | roles_list/get/assign/unassign/stats |
| presence | presence_list/get/history |
| collab | collab_create/list/get/join/leave/send/history/status |
| distributed | distributed_list/spawn/run/status/broadcast |
| rag | rag_search/hybrid/rerank |
| pulse | pulse_list/stats/scan |
| event | event_search/timeline/replay |

## 4. Telegram entrypoints (`scripts_01/telegram_bot.py`)

| Command | Handler | Engine |
|---------|---------|--------|
| `/notify` | `cmd_notify` | notification |
| `/notify_client` | `cmd_notify_client` | client notify |
| `/answer` | `cmd_answer` | answer |
| `/task <text>` | `cmd_task` | task dispatch (prompt queue) |
| `/workspace` | `cmd_workspace` | workspace |
| `/queue` | `cmd_queue` | prompt queue |
| (plain message) | `_handle_message` | intent → handler |

## 5. USER ACTION → RESULT карта (vertical slice)

```
"создать opportunity" →
  CLI: opportunity_engine discover --project-id X
    → discover_candidates → 4 источника → rank → upsert → opportunities.yaml
  MCP: (нет opportunity-инструмента в mcp_server.py!) → ❌ GAP
  TG: (нет opportunity-команды) → ❌ GAP

"выполнить opportunity" →
  CLI: opportunity_engine run <id>
    → propose → execute → run_chain → advance → accumulate → MemoryStore
  MCP: ❌ GAP
  TG: ❌ GAP
```

**GAP:** Opportunity/Whim НЕ доступны через MCP и Telegram (только CLI). Это entrypoint-gap, зафиксирован в 13_DEAD_CODE_AND_UNVERIFIED / 12_ARCHITECTURAL_CONFLICTS.

---

_Конец 07_ENTRYPOINT_TRACEABILITY. Переход к 08_GRAPH_RELATIONSHIP_MAP._
