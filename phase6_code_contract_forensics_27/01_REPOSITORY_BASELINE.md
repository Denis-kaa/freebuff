# 01_REPOSITORY_BASELINE — Фиксация исходного состояния

> **Промт:** `pompts_11/087_19_phase6_code_contract_forensics.md` §2 (REPOSITORY_BASELINE)
> **Дата:** 2026-08-17 · **Версия платформы:** v5.189.22
> **Метод:** repository-first — только фактические данные (git, ls, AST, pytest), никаких предположений.

---

## 1. Git-состояние

| Параметр | Значение |
|----------|----------|
| Branch | `master` |
| HEAD commit | `5b504dd` (feat(remote-sync): Phase 5.3-E persistent listener loop, v5.67.0) |
| Working tree | много uncommitted изменений (v5.67.0 → v5.189.22 накоплены в рабочем дереве) |
| Версия (BUFFY.md) | **5.189.22** (2026-08-17; предыдущая: 5.189.21) |
| Версия (CHANGELOG top) | `[5.189.22***REMOVED*** — 2026-08-17` |

> ⚠️ **Наблюдение (baseline):** HEAD-коммит отстаёт от рабочего дерева на ~120 релизов (v5.67.0 vs v5.189.22). Это НЕ баг — рабочий процесс платформы накапливает изменения в дереве и коммитит редко. Для forensics важен **рабочее дерево** как source of truth.

## 2. Структура каталогов (top-level)

```
__pycache__/  books_out_23/  buffy-playground_19/  cli_07/  context_12/
core_02/  data_13/  docs_10/  freebuff_plugin/  freebuff_plugin_03/
frontend_18/  infa_20/  intelligence_forensics_25/  logs_14/
phase4_evaluation_24/  phase5_intelligence_loop_26/  plugins_04/
pompts_11/  projects_17/  prototype_22/  runtime_05/  screenshots_16/
scripts_01/  services_08/  sessions_15/  src_06/  tests_09/  trash_21/
```

## 3. Ключевые метрики

| Метрика | Значение | Команда |
|---------|----------|---------|
| Тест-файлов в `tests_09/` | **105** | `ls tests_09/test_*.py \| wc -l` |
| AST-счётчик тест-функций | **2933** | `count_test_functions(Path('.'))` |
| Engineering-memory документов | **57** | `ls docs_10/engineering-memory/*.md \| wc -l` |
| LOC (core_02 + scripts_01) | **52 856** | `wc -l core_02/*.py scripts_01/*.py` |
| Записей в missing_registry | **20** | `python -m core_02.missing_registry list` |
| Сценариев (runtime_05/scenarios) | **3** | `blueprint_v3.yaml`, `vkusvill_demo.yaml`, `19_remote_sync/scenario.yaml` |
| Проектов в forge_registry.yaml | **1** (interior-planner) | grep data_13/forge_registry.yaml |

## 4. Существующие forensics / evaluation пакеты (прецеденты)

| Пакет | Содержимое | Статус |
|-------|-----------|--------|
| `phase4_evaluation_24/` | 13 файлов (01_EXECUTIVE_SUMMARY … 13_SELF_AUDIT) — Phase 4 protocol forensics | CLOSED |
| `intelligence_forensics_25/` | 14 файлов (01_REPOSITORY_REALITY_MAP … 14_EVALUATION_REPORT) — Intelligence Integration Forensics (промт 084) | CLOSED |
| `phase5_intelligence_loop_26/` | 11 файлов + README + MANIFEST — Close Intelligence Loop (промт 085) | CLOSED |

**Этот пакет** `phase6_code_contract_forensics_27/` — Phase 6 Code-Contract Forensics (промт 087) — **новый**, повторно исследует платформу целиком (не только Intelligence-слой) после завершения Phase 4/5.

## 5. Тестовая инфраструктура

- `pytest.ini`: markers `slow` (real-subprocess/network, deselect `-m "not slow"`) + `xdist_group`.
- `tests_09/conftest.py`: фикстуры `context_manager`, `mesh_tmp_db`, `offline_queue_path`.
- Полный прогон: `python -m pytest tests_09/ -q --tb=line -p no:cacheprovider` (запущен в фоне, см. §22 / 16_TEST_REPORT).

## 6. Ничего не изменено

На этапе baseline НИ ОДИН файл не изменён и не создан (кроме этого отчёта). Репозиторий зафиксирован в текущем состоянии.

---

_Конец 01_REPOSITORY_BASELINE. Переход к 02_ARCHITECTURE_REALITY_MAP._
