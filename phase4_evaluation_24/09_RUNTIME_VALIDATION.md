# 09_RUNTIME_VALIDATION — фактическое исполнение

> Протокол pomt83 §13: command / input / output / result / artifacts / logs.
> «Не принимай "код выглядит правильно" как доказательство.»

## 9.1 VSLICE-1 — EventBus поднимается

- **command**: `python -c "from scripts_01.event_bus import get_default_event_bus; from scripts_01.event_subscribers ***REMOVED***gister_all; bus = get_default_event_bus(); register_all(bus)"`
- **result**: PASS — 40 subscribers зарегистрированы.

## 9.2 VSLICE-2 — ForgeFacade инстанцируется

- **command**: `python -c "from core_02.forge_facade import ForgeFacade; f = ForgeFacade(); print(len([m for m in dir(f) if not m.startswith('_')***REMOVED***))"`
- **result**: PASS — 10+ публичных методов.

## 9.3 VSLICE-3 — Forge chain real integration

- **command**: `python -m pytest tests_09/test_forge_chain_real_integration.py -q`
- **result**: **7 passed (78.65s)** — `forge.py chain [--resume***REMOVED*** --json` на `vkusvill_demo`,
  `interior_planner`, `vkusvill_research`; JSON schema (9 ключей) валидна; resume = subset-or-equal.

## 9.4 VSLICE-4 — Bootstrap unknown-profile graceful

- **command**: `python -m pytest tests_09/test_mcp_server.py::TestBootstrapTools -q`
- **result**: **12 passed (5.78s)** — unknown profile `nonexistent_profile_xyz` → fallback `minimal`.

## 9.5 VSLICE-5 — Anchor resolution

- **command**: `python -m core_02.anchors_resolver . --json > runtime_05/anchors_resolver_report.json`
- **result**: exit 0. 208 docs / 1098 anchors: 925 CURRENT, 85 LESSON, 3 DESIGN_ONLY,
  1 STALE, 84 UNVERIFIED (soft-namespace, advisory), hard=0.
- **artifacts**: `runtime_05/anchors_resolver_report.json` (valid JSON).

## 9.6 Артефакты прогона

- `runtime_05/anchors_resolver_report.json`
- `/tmp/pomt83_pytest.log` (полный pytest, tmux)

## 9.7 Логи

- Логи встроены в отчёты выше; traceback отсутствуют (все зелёные).
