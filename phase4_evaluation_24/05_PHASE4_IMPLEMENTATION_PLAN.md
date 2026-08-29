# 05_PHASE4_IMPLEMENTATION_PLAN — реализация (закрыта)

> Протокол pomt83 §10: «FIRST WORKING SLICE FIRST». Поскольку Phase 4 закрыта на v5.20.0,
> раздел «реализация недостающего» вырождается: реализовывать нечего — фиксируем REUSE-вердикт
> и вертикальные срезы, которыми доказана работоспособность.

## 5.1 Gap-анализ (PHASE4_GAP_ANALYSIS)

| Заявлено (док) | В коде | Gap | Вердикт |
|---|---|---|---|
| Phase 4 «в работе ~85%» (устар. ROADMAP) | Phase 4 закрыта v5.20.0 | устаревший док | REUSE — обновить док |
| Plugin API | `plugin_api.py` | нет | REUSE |
| Event Bus | `event_bus.py` | нет | REUSE |
| MCP Server | `mcp_server.py` | нет | REUSE |
| Telegram Bot | `telegram_bot.py` | нет | REUSE |
| Scenario Engine | `scenario_engine.py` + `scenario_registry.py` | нет | REUSE |
| Plugins (3) | v5.20.0 | нет | REUSE |

**Итог gap-анализа: 0 новых модулей.** Параллельная архитектура не создана (CAN-16 ADDITIVE).

## 5.2 Вертикальные срезы (доказательство работоспособности)

| Slice | GOAL | FILES | VALIDATION | DONE |
|---|---|---|---|---|
| VSLICE-1 | EventBus поднимается, 40 subscribers регистрируются | `event_bus.py` + `event_subscribers.py` | import + instantiate PASS | ✅ |
| VSLICE-2 | ForgeFacade инстанцируется (10+ методов) | `forge_facade.py` | instantiate PASS | ✅ |
| VSLICE-3 | Forge chain на demo-проектах | `forge.py chain --json` | `test_forge_chain_real_integration.py` 7 passed (78.65s) | ✅ |
| VSLICE-4 | Bootstrap unknown-profile graceful | `bootstrap/engine.py` | `TestBootstrapTools` 12/12 | ✅ |
| VSLICE-5 | Anchor resolution | `anchors_resolver.py` | 208 docs / 1098 anchors, exit 0 | ✅ |

## 5.3 Реализованные исправления (в рамках аудита)

Производственный код не менялся. Исправлены только устаревшие тесты + нейминг:

1. `tests_09/test_telegram_bot.py` — 4 surgical fixes (fixture decorator, `tg_module` import,
   2 × monkeypatch scope) → 39/39 PASS.
2. `tests_09/test_multi_turn_dispatcher.py` — 1 stale assertion (discriminated tuple) → 23/23.
3. `tests_09/test_mcp_client.py` — `MCP_REQUEST_TIMEOUT` monkeypatch/mock (~60s → 15.24s).
4. Нейминг: `promt83.md` → `083_19_pomt83_protocols.md`; `PHASE4_EVALUATION_PACKAGE/` → `phase4_evaluation_24/`; счётчик `2862` → `2864`.

## 5.4 DONE criteria

- [x***REMOVED*** Forensic-аудит завершён (02)
- [x***REMOVED*** Traceability связана с кодом (03)
- [x***REMOVED*** Runtime path реально выполнен (09)
- [x***REMOVED*** Regression пройдена (08)
- [x***REMOVED*** Evaluation Package собран (12 файлов)
- [x***REMOVED*** Архив создан и проверен
