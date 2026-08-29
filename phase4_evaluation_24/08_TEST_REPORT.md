# 08_TEST_REPORT — Phase 4 (pomt83)

> Протокол pomt83 §12/§13/§14: UNIT + INTEGRATION + VERTICAL SLICE + REGRESSION.

## 8.1 Результаты этой сессии (2026-08-14)

| Suite | Результат | Время |
|---|---|---|
| `tests_09/test_mcp_server.py::TestBootstrapTools` | **12 passed** | 5.78s |
| `tests_09/test_forge_chain_real_integration.py` | **7 passed** | 78.65s |
| `python -m core_02.anchors_resolver .` | exit 0 (208 docs / 1098 anchors) | — |
| `pytest tests_09/ -q` (full, tmux) | см. 8.3 | ~13–17 мин |

## 8.2 Ранее закрытые subset-прогоны (в рамках аудита)

| Suite | Результат |
|---|---|
| `test_telegram_bot.py` | 39/39 PASS (было 30/39) |
| `test_multi_turn_dispatcher.py` | 23/23 PASS (было 22/23, stale assertion) |
| `test_mcp_client.py` | 70 passed (было ~60s+ из-за MCP_REQUEST_TIMEOUT) |
| `test_consistency_check.py` + `test_prompts_naming.py` | 101 passed |

## 8.3 Полный regression (`pytest tests_09/ -q`)

- **Ревизия 2026-08-16 (v5.189.13, tmux, `-n 2 --dist loadgroup`)**: **2897 passed, 0 failed, EXIT=0, 361s (6:01)**.
  Done-marker `EXIT=0` — сьюит дошёл до конца без фейлов; ускорение 12:42 → 6:01 (2.1×).
- **Сессия 2026-08-14 (v5.189.11, tmux detached)**: **2893 passed, 0 failed, 130 warnings (12:42)**.
  Done-marker `POMT83_PYTEST_DONE_EXIT=0` — сьюит дошёл до конца без фейлов.
- **Baseline v5.189.9** (CHANGELOG): 2873 passed, 0 errors (13:11).
- **xdist-инфраструктура (v5.189.12–13)**: `pytest-xdist` установлен, `--dist loadgroup` + `xdist_group("forge_real_registry")`
  закрывают гонку за реальный `data_13/forge_registry.yaml`; `-n 2` — память-безопасно на Termux.
  Скрипт: `run_tests_fast.sh`.

## 8.4 Тестовая методология

- **UNIT** — per-module тесты (`test_*_engine.py`, `test_plugin_api.py`, …).
- **INTEGRATION** — cross-component (`test_event_subscribers.py` auto-index chain).
- **VERTICAL SLICE** — `test_forge_chain_real_integration.py` (real subprocess на 3 demo-проектах).
- **REGRESSION** — полный `pytest tests_09/ -q`.

## 8.5 Ограничения окружения

- Termux/Android: полный прогон ~13–17 мин, чувствителен к OOM/tmux kill (ранее падал на ~52%).
- `pytest-xdist` не установлен — параллелизм недоступен без `pip install` (нужно согласие).
