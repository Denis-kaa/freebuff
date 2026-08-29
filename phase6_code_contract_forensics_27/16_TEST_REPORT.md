# 16_TEST_REPORT — Результаты тест-верификации (§22)

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §22 (TEST VERIFICATION)
> **Команда:** `python -m pytest tests_09/ -q --tb=line -p no:cacheprovider`
> **Дата:** 2026-08-17 · **Версия:** v5.189.22

---

## 1. Результаты

| Метрика | Значение |
|---------|----------|
| **Passed** | **2953** |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Warnings | 130 (все DeprecationWarning/SyntaxWarning, не блокеры) |
| Duration | **826.59s (13:46)** |
| Exit code | **0** |
| Environment | Termux/Android (linux), Python 3.x, pytest |

## 2. Примечание: 2953 passed vs AST-счётчик 2933

- AST-счётчик (`count_test_functions`) = **2933** — считает `def test_*` по AST.
- pytest-коллекция = **2953** — включает параметризованные варианты (pytest разворачивает параметры в отдельные тест-кейсы).
- Расхождение (+20) — нормальное (параметризация), НЕ регрессия.

## 3. Ключевые тест-файлы forensics-домена (все зелёные)

| Тест-файл | Покрывает |
|-----------|-----------|
| `test_opportunity_engine.py` + `test_opportunity_ranking.py` | Opportunity DISCOVER/RANK/EXECUTE/ACCUMULATE |
| `test_whim_capture.py` | Whim lifecycle |
| `test_intelligence_loop_phase5.py` | полный Intelligence-цикл |
| `test_scenario_registry.py` | Scenario SELECT |
| `test_factory_registry.py` + `test_factory_passport.py` | Factory select_forge/capability |
| `test_forge_facade.py` + `test_forge_chain_cli.py` | Forge EXECUTE |
| `test_event_bus.py` | EventBus publish/subscribe |
| `test_memory_store.py` + `test_learning_loop.py` + `test_semantic_layer.py` | Memory/Learning/Semantic |
| `test_consistency_check.py` + `test_doc_code_verify.py` + `test_anchors_resolver.py` | traceability/anchors |

## 4. Вывод

Полный прогон **зелёный** (2953 passed, EXIT=0). Это подтверждает: все 21 CONFIRMED компонент из 02_ARCHITECTURE_REALITY_MAP имеют работающие тесты. Forensics-пакет построен на стабильной базе.

---

_Конец 16_TEST_REPORT._
