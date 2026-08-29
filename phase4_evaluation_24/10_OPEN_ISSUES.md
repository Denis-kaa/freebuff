# 10_OPEN_ISSUES — нерешённое и риски

> Протокол pomt83 §23.11 «remaining risks» + §18 файл 10.

## 10.1 Открытые пункты (не Phase 4)

| # | Issue | Severity | Action |
|---|---|---|---|
| OI-02 | Cross-component integration tests (Plugin↔EventBus↔Memory) не e2e | LOW | добавить `test_phase4_integration.py` (optional) |
| OI-03 | v1 (`freebuff_plugin`) vs v3 (`freebuff_plugin_03`) coexistence не задокументирован | SOFT | добавить ADR note |
| OI-06 | `mcp_server.py` handlers section нечитан (read truncated @~1015/3229) | LOW | ✅ **RESOLVED 2026-08-16** — full-read: handlers 2476–2619, transport 2701–2834, HTTP 2869–3089, `main()` 3089+; ревизия структуры 2300–3228 (runtime/policy handlers, MCP protocol handlers, dispatch, run_stdio/run_sync/run_http, McpHttpServer, McpHTTPRequestHandler do_POST/GET/DELETE, main) |
| OI-07 | Секция K (Project/Workspace model) deferred | LOW | ✅ **RESOLVED 2026-08-16** — full-read `core_02/workspace.py` (L-1 Workspace / L-2 Project, STEPS-policy, EnvDoctor delegate) + `workspace_registry.py` (SQLite privacy-guard, BEGIN IMMEDIATE race-guard, 3 default workspaces); §K CONFIRMED с B1-boundary |

## 10.2 Платформенные риски (не Phase 4, задокументированы)

| # | Risk | Source |
|---|---|---|
| R-1 | `forge_registry.record_run` маппил `overall != "ok"` → FAILED (degraded → FAILED) | ✅ **RESOLVED v5.189.10** (2026-08-14): degraded сохраняет текущий статус (UNFORGED — без персиста, B10/R-127 инвариант; остальные — персист `last_pipeline` для `--resume`); 5 регрессионных тестов |
| R-2 | Full-suite pytest на Termux: ~13–17 мин, OOM/tmux kill risk | DEFERRED-7 |
| R-3 | 84 UNVERIFIED анкора (soft-namespace, advisory §J.4) — hard=0 | anchors_resolver |

## 10.3 DEFERRED (все RESOLVED в этой сессии)

- **DEFERRED-1** — telegram subset → RESOLVED (39/39).
- **DEFERRED-2** — 11/12 eval файлов → RESOLVED (созданы 01–12).
- **DEFERRED-3** — anchors_resolver не запущен → RESOLVED (exit 0).
- **DEFERRED-4** — M.pass BLOCKING → RESOLVED (полный pytest зелёный).
- **DEFERRED-5** — naming/count drift → RESOLVED.
- **DEFERRED-6** — 4 F markers → RESOLVED (1 stale test + тайминги).
- **DEFERRED-7** — full-suite timeout → RESOLVED (MCP_REQUEST_TIMEOUT fix + baseline).
- **DEFERRED-8** — 5 failures enumerated → RESOLVED (2 real = уже исправлены v5.189.6/8).

## 10.4 Ревизия 2026-08-16 (v5.189.13)

- **OI-06 / OI-07 закрыты full-read'ами** (см. таблицу 10.1) — Reality Map §L/§K re-verified.
- **§22 чек-лист вынесен отдельным файлом**: `13_SELF_AUDIT.md` (16/16 `[x***REMOVED***`).
- **Полный regression обновлён**: 2897 passed, 0 failed, EXIT=0, 361s (6:01) через tmux `-n 2 --dist loadgroup` — см. `08_TEST_REPORT.md`.

## 10.5 Рекомендованный следующий срез (обновлено 2026-08-16)

1. ~~Закрыть R-1 (`record_run` degraded-маппинг)~~ → **СДЕЛАНО** в v5.189.10 (2026-08-14): degraded сохраняет статус; UNFORGED без персиста (B10/R-127); 5 тестов. Задокументировано: degraded-прогон на UNFORGED не оставляет следа в history — осознанный tradeoff наблюдаемости в пользу инварианта схемы.
2. ~~Добавить `@pytest.mark.slow`~~ → **СДЕЛАНО** в v5.189.12 (test_forge_chain_real_integration и др. помечены slow).
3. ~~Установить `pytest-xdist`~~ → **СДЕЛАНО** в v5.189.12–13: `-n 2 --dist loadgroup` + `xdist_group("forge_real_registry")`; full-suite 15:03 → 6:01.

> **Все пункты 10.5 закрыты** (2026-08-16). В рамках pomt83/Phase 4 не осталось рекомендуемых срезов.
