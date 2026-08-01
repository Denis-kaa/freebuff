# File Registry — Freebuff Project

> **Generated:** 2026-07-29  
> **Purpose:** Inventory of project files with current location, category, and target location after restructure.  
> **Status:** Work in progress — files are being migrated incrementally to avoid breaking 1124 tests.

---

## How to read this registry

| Column | Meaning |
|--------|---------|
| **File** | Path relative to project root |
| **Category** | CODE, CONFIG, TEST, DOC-* etc. |
| **Status** | `keep`, `move`, `merge`, `archive`, `delete` |
| **Target (v5 structure)** | Where the file should live after restructure |

---

## Core / entry points

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `freebuff_cli.py` | CODE | keep | `cli_07/freebuff_cli.py` (kept at root for compatibility) | CLI entry point |
| `cli_07/__init__.py` | CODE | new | `cli_07/__init__.py` | Re-exports root CLI |
| `core_02/interfaces.py` | CODE | keep | `core_02/interfaces.py` | SmartRouter abstractions |
| `core_02/router.py` | CODE | keep | `core_02/router.py` | Capability router |
| `services_08/__init__.py` | CODE | new | `services_08/__init__.py` | Re-exports scripts_01/ modules |

---

## services_08/ — Core services (currently `scripts_01/`)

> Migration plan: move modules from `scripts_01/` to `services_08/` incrementually.
> `scripts_01/` will remain as compatibility shim until v6.

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `scripts_01/context_manager.py` | CODE | move | `services_08/context/manager.py` | Session platform |
| `scripts_01/session_utils.py` | CODE | move | `services_08/context/utils.py` | Session helpers |
| `scripts_01/stream_session.py` | CODE | move | `services_08/context/stream_session.py` | Stream sessions |
| `scripts_01/stream_bridge.py` | CODE | move | `services_08/context/stream_bridge.py` | Stream bridge |
| `scripts_01/memory_engine.py` | CODE | move | `services_08/memory/engine.py` | Memory (5 levels) |
| `scripts_01/knowledge_engine.py` | CODE | move | `services_08/knowledge/engine.py` | Knowledge / RAG |
| `scripts_01/graph_index.py` | CODE | move | `services_08/knowledge/graph.py` | Graph index |
| `scripts_01/event_bus.py` | CODE | move | `services_08/events/bus.py` | Event bus |
| `scripts_01/orchestrator.py` | CODE | move | `services_08/workflow/orchestrator.py` | Workflow engine |
| `scripts_01/tool_runtime.py` | CODE | move | `services_08/tools/runtime.py` | Tool runtime |
| `scripts_01/model_gateway.py` | CODE | move | `services_08/models/gateway.py` | Model gateway |
| `scripts_01/plugin_api.py` | CODE | move | `services_08/plugins/api.py` | Plugin API |
| `scripts_01/seed_knowledge.py` | CODE | move | `services_08/knowledge/seed.py` | Knowledge seeding |
| `scripts_01/system_monitor.py` | CODE | move | `services_08/system/monitor.py` | Health monitor |
| `scripts_01/auto_conspect.py` | CODE | move | `services_08/context/auto_conspect.py` | Auto summarization |
| `scripts_01/context_builder.py` | CODE | move | `services_08/context/builder.py` | Unified context |
| `scripts_01/bootstrap.py` | CODE | move | `services_08/session/bootstrap.py` | Session bootstrap |
| `scripts_01/mcp_server.py` | CODE | move | `services_08/mcp/server.py` | MCP server |
| `scripts_01/mcp_fastapi.py` | CODE | move | `services_08/mcp/fastapi.py` | FastAPI MCP wrapper |
| `scripts_01/telegram_bot.py` | CODE | move | `services_08/telegram/bot.py` | Telegram bot |
| `scripts_01/archive/dashboard_api.py` | CODE | move | `services_08/api/dashboard.py` | Dashboard API |

---

## freebuff_plugin_03/ — Plugin layer

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `freebuff_plugin_03/__init__.py` | CODE | keep | `freebuff_plugin_03/__init__.py` | Package init |
| `freebuff_plugin_03/wrapper.py` | CODE | keep | `freebuff_plugin_03/wrapper.py` | Plugin wrapper |
| `freebuff_plugin_03/bridge.py` | CODE | keep | `freebuff_plugin_03/bridge.py` | Context bridge |
| `freebuff_plugin_03/api.py` | CODE | keep | `freebuff_plugin_03/api.py` | Plugin API endpoints |
| `freebuff_plugin_03/router.py` | CODE | keep | `freebuff_plugin_03/router.py` | Intent router |
| `freebuff_plugin_03/mcp_server.py` | CODE | keep | `freebuff_plugin_03/mcp_server.py` | Plugin MCP server |
| `freebuff_plugin_03/config.py` | CODE | keep | `freebuff_plugin_03/config.py` | Plugin config |
| `freebuff_plugin_03/tgbot.py` | CODE | keep | `freebuff_plugin_03/tgbot.py` | Telegram bot plugin |
| `freebuff_plugin_03/scenario_engine.py` | CODE | keep | `freebuff_plugin_03/scenario_engine.py` | Scenario engine |
| `freebuff_plugin_03/bootstrap/` | CODE | keep | `freebuff_plugin_03/bootstrap/` | Bootstrap engine |
| `freebuff_plugin_03/runtime/` | CODE | keep | `freebuff_plugin_03/runtime/` | Runtime abstraction |
| `freebuff_plugin_03/event/` | CODE | keep | `freebuff_plugin_03/event/` | Event platform |
| `freebuff_plugin_03/bridge_layer.py` | CODE | keep | `freebuff_plugin_03/bridge_layer.py` | Bridge layer |
| `freebuff_plugin_03/acp_protocol.py` | CODE | keep | `freebuff_plugin_03/acp_protocol.py` | ACP protocol |
| `freebuff_plugin_03/mcp_client.py` | CODE | keep | `freebuff_plugin_03/mcp_client.py` | MCP client |
| `freebuff_plugin_03/scenarios/` | DOC | keep | `freebuff_plugin_03/scenarios/` | Scenario templates |

---

## Tests

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `tests_09/conftest.py` | TEST | keep | `tests_09/conftest.py` | pytest fixtures |
| `tests_09/test_*.py` | TEST | keep | `tests_09/test_*.py` | All test files |
| `tests_09/test_runtime_abstraction.py` | TEST | keep | `tests_09/test_runtime_abstraction.py` | Runtime tests |
| `tests_09/test_mcp_server.py` | TEST | keep | `tests_09/test_mcp_server.py` | MCP server tests |
| `tests_09/test_bootstrap_engine.py` | TEST | keep | `tests_09/test_bootstrap_engine.py` | Bootstrap tests |

---

## Documentation

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `README.md` | DOC | keep | `README.md` | Main README |
| `BUFFY.md` | DOC-AGENT | keep | `BUFFY.md` | Master agent manifest |
| `AGENTS.md` | DOC-AGENT | keep | `AGENTS.md` (single source) | Канон; ops-дубль архивирован (2026-08-01) |
| `docs_10/ops/AGENTS.md` | DOC-AGENT | archived | `trash_21/AGENTS_ops_duplicate.md` | Дубль решён (2026-08-01) → trash_21 |
| `.freebuff/AGENTS.md` | DOC-AGENT | merge | `AGENTS.md` | Duplicate — merge into root |
| `CLAUDE.md` | DOC-AGENT | keep | `CLAUDE.md` | Claude fallback |
| `CODY.md` | DOC-AGENT | keep | `CODY.md` | Cody fallback |
| `.cursorrules` | DOC-AGENT | keep | `.cursorrules` | Cursor fallback |
| `SPEC.md` | DOC-SPEC | keep | `SPEC.md` | Technical specification |
| `CHANGELOG.md` | DOC | keep | `CHANGELOG.md` | Changelog |
| `TASK.md` | DOC | keep | `TASK.md` | Current task |
| `docs_10/vision/VISION_3.0.md` | DOC-ARCH | update | `docs_10/01-architecture/VISION_3.0.md` | Update component statuses |
| `docs_10/core/ARCHITECTURE_3.0.md` | DOC-ARCH | update | `docs_10/01-architecture/ARCHITECTURE_3.0.md` | Update component statuses |
| `docs_10/vision/ROADMAP.md` | DOC-ARCH | update | `docs_10/07-roadmap/ROADMAP.md` | Update roadmap |
| `docs_10/decisions/DECISIONS.md` | DOC-ARCH | keep | `docs_10/decisions/DECISIONS.md` | Индекс ADR |
| `docs_10/engineering-memory/decisions/ADR_*.md` | DOC-ARCH | keep | — | Отдельные архитектурные решения |
| `docs_10/decisions/IDEAS.md` | DOC-ARCH | keep | `docs_10/decisions/IDEAS.md` | Ideas registry |
| `docs_10/audits/AUDIT_FULL_2026-07-29.md` | DOC-AUDIT | keep | `docs_10/03-audits/AUDIT_FULL_2026-07-29.md` | This audit |
| `docs_10/ops/SESSION_GUIDE.md` | DOC-SESSION | keep | `docs_10/06-sessions_15/SESSION_GUIDE.md` | Session guide |
| `pompts_11/*.md` | PROMPT | archive | `pompts_11/` or `prompts/` | Add `pompts_11/README.md` index |
| `pompts_11/*.bak` | OTHER | delete | — | Backup files |

---

## Configuration & data

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `.freebuff/config.json` | CONFIG | keep | `.freebuff/config.json` | Freebuff CLI config |
| `requirements.txt` | CONFIG | keep | `requirements.txt` | Python deps |
| `mypy.ini` | CONFIG | keep | `mypy.ini` | mypy config |
| `.gitignore` | CONFIG | update | `.gitignore` | Add `*.bak`, `.mypy_cache` etc. |
| `data_13/` | DATA | keep | `data_13/` | SQLite databases |
| `context_12/` | DATA | keep | `context_12/` | Session data |
| `logs_14/` | DATA | keep | `logs_14/` | Logs |

---

## External / other

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `projects_17/` | PROJECT | keep | `projects_17/` | External projects |
| `buffy-playground_19/` | PROJECT | keep | `buffy-playground_19/` | Frontend playground |
| `plugins_04/hello_world/` | PLUGIN | keep | `plugins_04/hello_world/` | Demo plugin |
| `__pycache__/`, `*.pyc` | OTHER | delete | — | Build artifacts |
| `.mypy_cache/`, `.pytest_cache/` | OTHER | delete | — | Cache artifacts |

---

## Migration rules

1. **No file is deleted until tests pass** for the new location.
2. **Backward compatibility:** old `scripts.X` and root-level imports keep working via `services_08/__init__.py` and root-level shims.
3. **Path rule:** all new code uses `Path(__file__).resolve().parent` or `Path.home()`; no absolute Android/Termux paths in source.
4. **Docs first:** update `docs_10/vision/VISION_3.0.md` and `docs_10/core/ARCHITECTURE_3.0.md` before moving files.

---

*Last updated: 2026-07-29*
