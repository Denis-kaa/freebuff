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
| `freebuff_cli.py` | CODE | keep | `cli/freebuff_cli.py` (kept at root for compatibility) | CLI entry point |
| `cli/__init__.py` | CODE | new | `cli/__init__.py` | Re-exports root CLI |
| `core/interfaces.py` | CODE | keep | `core/interfaces.py` | SmartRouter abstractions |
| `core/router.py` | CODE | keep | `core/router.py` | Capability router |
| `services/__init__.py` | CODE | new | `services/__init__.py` | Re-exports scripts/ modules |

---

## services/ — Core services (currently `scripts/`)

> Migration plan: move modules from `scripts/` to `services/` incrementually.
> `scripts/` will remain as compatibility shim until v6.

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `scripts/context_manager.py` | CODE | move | `services/context/manager.py` | Session platform |
| `scripts/session_utils.py` | CODE | move | `services/context/utils.py` | Session helpers |
| `scripts/stream_session.py` | CODE | move | `services/context/stream_session.py` | Stream sessions |
| `scripts/stream_bridge.py` | CODE | move | `services/context/stream_bridge.py` | Stream bridge |
| `scripts/memory_engine.py` | CODE | move | `services/memory/engine.py` | Memory (5 levels) |
| `scripts/knowledge_engine.py` | CODE | move | `services/knowledge/engine.py` | Knowledge / RAG |
| `scripts/graph_index.py` | CODE | move | `services/knowledge/graph.py` | Graph index |
| `scripts/event_bus.py` | CODE | move | `services/events/bus.py` | Event bus |
| `scripts/orchestrator.py` | CODE | move | `services/workflow/orchestrator.py` | Workflow engine |
| `scripts/tool_runtime.py` | CODE | move | `services/tools/runtime.py` | Tool runtime |
| `scripts/model_gateway.py` | CODE | move | `services/models/gateway.py` | Model gateway |
| `scripts/plugin_api.py` | CODE | move | `services/plugins/api.py` | Plugin API |
| `scripts/seed_knowledge.py` | CODE | move | `services/knowledge/seed.py` | Knowledge seeding |
| `scripts/system_monitor.py` | CODE | move | `services/system/monitor.py` | Health monitor |
| `scripts/auto_conspect.py` | CODE | move | `services/context/auto_conspect.py` | Auto summarization |
| `scripts/context_builder.py` | CODE | move | `services/context/builder.py` | Unified context |
| `scripts/bootstrap.py` | CODE | move | `services/session/bootstrap.py` | Session bootstrap |
| `scripts/mcp_server.py` | CODE | move | `services/mcp/server.py` | MCP server |
| `scripts/mcp_fastapi.py` | CODE | move | `services/mcp/fastapi.py` | FastAPI MCP wrapper |
| `scripts/telegram_bot.py` | CODE | move | `services/telegram/bot.py` | Telegram bot |
| `scripts/archive/dashboard_api.py` | CODE | move | `services/api/dashboard.py` | Dashboard API |

---

## freebuff_plugin/ — Plugin layer

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `freebuff_plugin/__init__.py` | CODE | keep | `freebuff_plugin/__init__.py` | Package init |
| `freebuff_plugin/wrapper.py` | CODE | keep | `freebuff_plugin/wrapper.py` | Plugin wrapper |
| `freebuff_plugin/bridge.py` | CODE | keep | `freebuff_plugin/bridge.py` | Context bridge |
| `freebuff_plugin/api.py` | CODE | keep | `freebuff_plugin/api.py` | Plugin API endpoints |
| `freebuff_plugin/router.py` | CODE | keep | `freebuff_plugin/router.py` | Intent router |
| `freebuff_plugin/mcp_server.py` | CODE | keep | `freebuff_plugin/mcp_server.py` | Plugin MCP server |
| `freebuff_plugin/config.py` | CODE | keep | `freebuff_plugin/config.py` | Plugin config |
| `freebuff_plugin/tgbot.py` | CODE | keep | `freebuff_plugin/tgbot.py` | Telegram bot plugin |
| `freebuff_plugin/scenario_engine.py` | CODE | keep | `freebuff_plugin/scenario_engine.py` | Scenario engine |
| `freebuff_plugin/bootstrap/` | CODE | keep | `freebuff_plugin/bootstrap/` | Bootstrap engine |
| `freebuff_plugin/runtime/` | CODE | keep | `freebuff_plugin/runtime/` | Runtime abstraction |
| `freebuff_plugin/event/` | CODE | keep | `freebuff_plugin/event/` | Event platform |
| `freebuff_plugin/bridge_layer.py` | CODE | keep | `freebuff_plugin/bridge_layer.py` | Bridge layer |
| `freebuff_plugin/acp_protocol.py` | CODE | keep | `freebuff_plugin/acp_protocol.py` | ACP protocol |
| `freebuff_plugin/mcp_client.py` | CODE | keep | `freebuff_plugin/mcp_client.py` | MCP client |
| `freebuff_plugin/scenarios/` | DOC | keep | `freebuff_plugin/scenarios/` | Scenario templates |

---

## Tests

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `tests/conftest.py` | TEST | keep | `tests/conftest.py` | pytest fixtures |
| `tests/test_*.py` | TEST | keep | `tests/test_*.py` | All test files |
| `tests/test_runtime_abstraction.py` | TEST | keep | `tests/test_runtime_abstraction.py` | Runtime tests |
| `tests/test_mcp_server.py` | TEST | keep | `tests/test_mcp_server.py` | MCP server tests |
| `tests/test_bootstrap_engine.py` | TEST | keep | `tests/test_bootstrap_engine.py` | Bootstrap tests |

---

## Documentation

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `README.md` | DOC | keep | `README.md` | Main README |
| `BUFFY.md` | DOC-AGENT | keep | `BUFFY.md` | Master agent manifest |
| `AGENTS.md` | DOC-AGENT | merge | `AGENTS.md` (single source) | Merge docs/ops/AGENTS.md and .freebuff/AGENTS.md |
| `docs/ops/AGENTS.md` | DOC-AGENT | merge | `AGENTS.md` | Duplicate — merge into root |
| `.freebuff/AGENTS.md` | DOC-AGENT | merge | `AGENTS.md` | Duplicate — merge into root |
| `CLAUDE.md` | DOC-AGENT | keep | `CLAUDE.md` | Claude fallback |
| `CODY.md` | DOC-AGENT | keep | `CODY.md` | Cody fallback |
| `.cursorrules` | DOC-AGENT | keep | `.cursorrules` | Cursor fallback |
| `SPEC.md` | DOC-SPEC | keep | `SPEC.md` | Technical specification |
| `CHANGELOG.md` | DOC | keep | `CHANGELOG.md` | Changelog |
| `TASK.md` | DOC | keep | `TASK.md` | Current task |
| `docs/vision/VISION_3.0.md` | DOC-ARCH | update | `docs/01-architecture/VISION_3.0.md` | Update component statuses |
| `docs/core/ARCHITECTURE_3.0.md` | DOC-ARCH | update | `docs/01-architecture/ARCHITECTURE_3.0.md` | Update component statuses |
| `docs/vision/ROADMAP.md` | DOC-ARCH | update | `docs/07-roadmap/ROADMAP.md` | Update roadmap |
| `docs/decisions/DECISIONS.md` | DOC-ARCH | keep | `docs/04-decisions/DECISIONS.md` | ADRs |
| `docs/ops/IDEAS.md` | DOC-ARCH | keep | `docs/01-architecture/IDEAS.md` | Ideas registry |
| `docs/audits/AUDIT_FULL_2026-07-29.md` | DOC-AUDIT | keep | `docs/03-audits/AUDIT_FULL_2026-07-29.md` | This audit |
| `docs/ops/SESSION_GUIDE.md` | DOC-SESSION | keep | `docs/06-sessions/SESSION_GUIDE.md` | Session guide |
| `pompts/*.md` | PROMPT | archive | `pompts/` or `prompts/` | Add `pompts/README.md` index |
| `pompts/*.bak` | OTHER | delete | — | Backup files |

---

## Configuration & data

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `.freebuff/config.json` | CONFIG | keep | `.freebuff/config.json` | Freebuff CLI config |
| `requirements.txt` | CONFIG | keep | `requirements.txt` | Python deps |
| `mypy.ini` | CONFIG | keep | `mypy.ini` | mypy config |
| `.gitignore` | CONFIG | update | `.gitignore` | Add `*.bak`, `.mypy_cache` etc. |
| `data/` | DATA | keep | `data/` | SQLite databases |
| `context/` | DATA | keep | `context/` | Session data |
| `logs/` | DATA | keep | `logs/` | Logs |

---

## External / other

| File | Category | Status | Target (v5 structure) | Notes |
|------|----------|--------|-----------------------|-------|
| `projects/` | PROJECT | keep | `projects/` | External projects |
| `buffy-playground/` | PROJECT | keep | `buffy-playground/` | Frontend playground |
| `plugins/hello_world/` | PLUGIN | keep | `plugins/hello_world/` | Demo plugin |
| `__pycache__/`, `*.pyc` | OTHER | delete | — | Build artifacts |
| `.mypy_cache/`, `.pytest_cache/` | OTHER | delete | — | Cache artifacts |

---

## Migration rules

1. **No file is deleted until tests pass** for the new location.
2. **Backward compatibility:** old `scripts.X` and root-level imports keep working via `services/__init__.py` and root-level shims.
3. **Path rule:** all new code uses `Path(__file__).resolve().parent` or `Path.home()`; no absolute Android/Termux paths in source.
4. **Docs first:** update `docs/vision/VISION_3.0.md` and `docs/core/ARCHITECTURE_3.0.md` before moving files.

---

*Last updated: 2026-07-29*
