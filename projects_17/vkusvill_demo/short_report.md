# ВкусВилл demo — краткий отчёт (ROADMAP-VV-001)

**⚠️ МОДЕЛЬНЫЙ пример**, не реальные данные ритейлера.

## Что сделано

1. **Task 0 — xlsx-skill.** `core_02/xlsx_builder.py` минимальный API (Workbook/sheet/cell/save/load), atomic save. 10 юнит-тестов PASSED. `requirements.txt` обновлён (`openpyxl>=3.1.0`).
2. **Task 1 — модельный .xlsx.** 3 категории (молочка/крупа/напиток) × 12 недель истории. 3 листа (history/forecast/order) с реальными Excel-формулами (AVERAGE, STDEV.P, IF, SQRT). 2 неочевидных (SERVICE_LEVEL_Z=1.65 без комментария + INCIDENT_2024_CORRECTION cell-content proxy).
3. **Task 2 — Teamwork 3 роли** через `runtime_05/scenarios/vkusvill_demo.yaml`:
   - analyst → `business_logic.md` (4 принципа + 2 неочевидных + sources)
   - developer → `forecast.py` (named constants, NO Excel engine)
   - reviewer → `parity_check.py` + `parity_report.md` (variant b per Q1, NO LibreOffice)
4. **Task 3 — честный артефакт:** README + этот отчёт. Registry updates (INDEX + DOC REGISTRY + CHANGELOG v5.105.0 + LESSONS CON-54).

## Parity result

Все 3 SKU прошли parity-check. Pre-computed Excel values == Python recompute (modulo tolerance ±0.01).

**OVERALL: ✅ PASS** (3/3 SKUs × {5 forecast-полей + order_qty***REMOVED*** = 18 PASS-строк, 0 FAIL).

## 4 принципа

1. **SMA(W=4)** — простая скользящая по 4 неделям; `=AVERAGE('history'!D{end-3***REMOVED***:D{end***REMOVED***)`.
2. **Weekday index** — профиль спроса по дню недели. Напиток демо: `[0.90, 0.85, 0.85, 0.95, 1.25, 1.50, 1.30***REMOVED***` (сб пик 1.5×).
3. **Safety stock Z×σ×√L** — 95% сервис. **NON_OBVIOUS_1: Z=1.65 висит без видимого комментария** в `K5`.
4. **Shelf-life correction** — `IF(shelf_life < 2*lead_time, 0.5, 1.0)`.

## 2 неочевидных элемента (Q3)

| # | Где | Описание | Demo-реализация |
|---|-----|----------|------------------|
| 1 | `forecast!K5` = 1.65 | Жёстко прописанный множитель без комментария «что Z для 95%» | Значение висит в K5, в J5 только label |
| 2 | `forecast!H22` = 0.92 | Defined name `post_incident_2024_correction` legacy | Cell-content proxy (xlsx_builder минимальный API, per user constraint no Forge-ext) |

## Файлы (Task 1+2+3)

| Файл | Назначение |
|------|------------|
| `projects_17/vkusvill_demo/build_model_xlsx.py` | Конструктор .xlsx (named constants, one source of truth) |
| `projects_17/vkusvill_demo/model_forecast.xlsx` | Модельный артефакт (3 листа, реальные формулы + 2 NON_OBVIOUS) |
| `projects_17/vkusvill_demo/model_snapshot.json` | Side-car pre-computed values |
| `projects_17/vkusvill_demo/business_logic.md` | 4 принципа + 2 неочевидных + sources |
| `projects_17/vkusvill_demo/forecast.py` | Python-recompute (developer role, imports constants) |
| `projects_17/vkusvill_demo/forecast_python.json` | Output forecast.py |
| `projects_17/vkusvill_demo/parity_check.py` | Variant (b) parity-check (reviewer role, NO LibreOffice) |
| `projects_17/vkusvill_demo/parity_report.md` | PASS/FAIL per row + OVERALL |
| `projects_17/vkusvill_demo/README.md` | Входная точка + честный marker |
| `projects_17/vkusvill_demo/STEPS.md` | Step-by-step log (Steps 1–6) |
| `projects_17/vkusvill_demo/LESSONS.md` | Project-local narrow (3 факта + 1 open Q, per user constraint) |
| `projects_17/vkusvill_demo/short_report.md` | Этот файл |
| `runtime_05/scenarios/vkusvill_demo.yaml` | Teamwork-сценарий 3 роли |

## Boundary / honesty markers

- ✅ МОДЕЛЬНЫЙ marker в `A1` каждого листа + в README + здесь.
- ❌ NO реальные данные ВкусВилла (per Q4 + §5 business_logic.md).
- ❌ NO VBA-бинарников — только формулы Excel.
- ❌ NO LibreOffice/Excel-engine в parity (variant b Q1).
- ❌ NO Forge-extensions в этом demo (per user constraint, project-local LESSONS узкий).
- ❌ NO openpyxl defined_names (cell-content proxy H22).

## Реестр

- Roadmap: `docs_10/ROADMAP_VKUSVILL_DEMO_062.md`
- INDEX: `docs_10/INDEX.md` (VV-001 registered)
- DOC REGISTRY: `docs_10/DOCUMENT_REGISTRY.md` (ACTIVE counter +1: 82→83)
- LESSONS: `core_02/LESSONS.md` — **CON-54** (Teamwork-decomposition: роль ≠ generic, role = конкретный узкий output)
- CHANGELOG: `CHANGELOG.md` v5.105.0 (Task 0/1/2/3 все заполнены)
