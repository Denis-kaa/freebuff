# 13_DEAD_CODE_AND_UNVERIFIED — Мёртвый код и непроверенное

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §6 (DEAD_CODE / UNVERIFIED)
> **Метод:** компонент существует, но нет реального caller/runtime path → DEAD_CODE. Недостаточно доказательств → UNVERIFIED.

---

## 1. DEAD_CODE кандидаты

| Компонент | Файл | Почему DEAD_CODE-кандидат | Вердикт |
|-----------|------|---------------------------|---------|
| `overlay_server.py` / `overlay_client.py` | scripts_01/ | runtime-путь не верифицирован в этой сессии; overlay-UI не в каноне | ⚠️ UNVERIFIED (не dead — есть скрипты запуска) |
| `stream_session.py` / `stream_bridge.py` | scripts_01/ | есть тесты, но production-путь не подтверждён | ⚠️ UNVERIFIED |
| `xlsx_builder.py` / `excel_eval.py` | core_02/ + tests | используются vkusvill_demo сценарием | ✅ НЕ dead (домен-специфичен) |
| `wizard.py` / `wizard_lib.py` | scripts_01/ + core_02/ | интерактивный wizard, runtime-путь не в CI-loop | ⚠️ UNVERIFIED (интерактив) |
| `auto_save.py`, `auto_conspect.py`, `auto_continue.sh` | scripts_01/ | вспомогательные утилиты | ✅ НЕ dead (утилиты) |

**Вывод:** явного DEAD_CODE (компонент с нулём callers) **не обнаружено**. Есть несколько UNVERIFIED (overlay/stream/wizard — интерактивные/периферийные, не в каноническом vertical slice).

## 2. UNVERIFIED компоненты

| Компонент | Причина |
|-----------|---------|
| `overlay_server/client` | интерактивный overlay, не в CI-loop, runtime не верифицирован |
| `stream_session/bridge` | стриминг, тесты есть, production-вызов не подтверждён |
| `wizard.py` | интерактивный мастер, вызывается вручную |
| `phone_control_mcp.py` | MCP-обёртка для телефона, внешняя зависимость |
| `services_08/*` | сервисный слой, отдельный от core_02/scripts_01 |

## 3. DOCUMENTED_ONLY (есть в документации, нет в коде) — сводка

| Компонент | Документация | Код | Статус |
|-----------|--------------|-----|--------|
| Scenario Engine (оркестратор) | SCENARIO_ENGINE_DESIGN §7-§9 | нет | DOCUMENTED_ONLY |
| Content Intelligence (отдельный) | content_factory/concept*.md | нет (есть generic opportunity_engine) | DOCUMENTED_ONLY |
| Concept Evolution (все элементы) | RFC_ORG_MEMORY_EVOLUTION + 09_FUTURE_GAPS | нет (grep 0) | DOCUMENTED_ONLY |
| Decision Intelligence (ARE/CAE/TDA) | RFC_DECISION_INTELLIGENCE_SYSTEM | нет | DOCUMENTED_ONLY |
| traceability_graph.py (инструмент) | TRACEABILITY_GRAPH §E.9 #3 | нет | DOCUMENTED_ONLY |
| Content Factory (движок) | content_factory/concept*.md | нет | DOCUMENTED_ONLY |

## 4. Entrypoint-gaps (реализовано, но недоступно через все каналы)

| Возможность | CLI | MCP | TG | REST |
|-------------|:---:|:---:|:--:|:----:|
| Opportunity discover/run | ✅ | ❌ | ❌ | ❌ |
| Whim capture/promote | ✅ | ❌ | ❌ | ❌ |
| Scenario select | ✅ (через propose) | ❌ | ❌ | ❌ |
| Factory select_forge | ❌ (нет CLI) | ❌ | ❌ | ❌ |
| Project pulse | ✅ | ✅ | ❌ | ✅ (metrics) |
| Forge chain | ✅ | ❌ | ❌ | ✅ (REST) |

---

_Конец 13_DEAD_CODE_AND_UNVERIFIED. Переход к 14_NEXT_VERTICAL_SLICE._
