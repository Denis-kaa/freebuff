# ВкусВилл demo — разбор модельной Excel/VBA логики

**⚠️ МОДЕЛЬНЫЙ пример** — этот проект демонстрирует подход к разбору legacy Excel/VBA инструментов прогноза/заказа в ритейле. **НЕ привязан к реальным данным ВкусВилла или иного ритейлера.** Все цифры — модельные на основе общепринятых принципов (см. [business_logic.md***REMOVED***(business_logic.md) §4 sources).

## Контекст

Демо-артефакт для отклика на вакансию «Специалист по AI-автоматизации бизнес-процессов» (ВкусВилл). Задача вакансии: анализ текущей логики прогноза/заказа (включая Excel/VBA-инструменты) и воспроизведение в новых, более гибких решениях.

Чтобы продемонстрировать подход, мы построили:
1. Минимальный **xlsx-skill** (`core_02/xlsx_builder.py`) — платформенная возможность для генерации `.xlsx`;
2. **Модельный .xlsx** с 3 категориями, 12 неделями истории, реальными Excel-формулами (AVERAGE/STDEV.P/IF/SQRT), 2 неочевидными элементами legacy-стиля;
3. **Teamwork-разбор через 3 роли** (analyst / developer / reviewer) с parity-check между pre-saved Excel-значениями и Python recompute (variant b per Q1).

## Что внутри

| Файл | Teamwork-role | Описание |
|------|---------------|----------|
| `build_model_xlsx.py` | — | Конструирует `model_forecast.xlsx` через xlsx-skill |
| `model_forecast.xlsx` | — | Модельный .xlsx (3 листа: history / forecast / order) |
| `business_logic.md` | analyst | 4 принципа + 2 неочевидных + sources |
| `forecast.py` | developer | Python-recompute (mirrors build_model formulas) |
| `parity_check.py` + `parity_report.md` | reviewer | Variant (b) Python-only parity, NO LibreOffice |
| `model_snapshot.json` | — | Side-car JSON (pre-computed values для snapshot) |
| `forecast_python.json` | — | forecast.py output |
| `STEPS.md` | — | Step-by-step log выполнения |
| `LESSONS.md` | — | Project-local narrow lessons (per user constraint) |
| `README.md` | — | Этот файл |
| `short_report.md` | — | Краткий итоговый отчёт |
| `../../runtime_05/scenarios/vkusvill_demo.yaml` | (registry) | Teamwork-сценарий 3 роли |

## Как запустить

```bash
cd /path/to/freebuff

# 1. Построить модельный .xlsx + side-car JSON
python3 projects_17/vkusvill_demo/build_model_xlsx.py

# 2. Python-recompute forecast (named constants only, NO Excel)
python3 projects_17/vkusvill_demo/forecast.py

# 3. Parity-check (variant b, NO LibreOffice, NO Excel engine)
python3 projects_17/vkusvill_demo/parity_check.py
# OK: projects_17/vkusvill_demo/parity_report.md written
# OVERALL: PASS
```

## Принципы (4 + 2 неочевидных)

См. `business_logic.md` для полного описания с источниками (Chopra, Hyndman, AbcSupplyChain, Relex).

| # | Принцип | Формула (Excel-side) | NON_OBVIOUS? |
|---|---------|----------------------|----------------|
| 1 | SMA(W=4) | `=AVERAGE('history'!D{h_end-3***REMOVED***:D{h_end***REMOVED***)` | — |
| 2 | Weekday seasonality | per-cat index из таблицы | — |
| 3 | Safety stock Z×σ×√L | `=STDEV.P(...)*1.65*SQRT(L)` | **NON_OBVIOUS_1** (Z=1.65 hardcoded без комментария) |
| 4 | Shelf-life correction | `=IF(shelf_life<L*2, 0.5, 1.0)` | — |
| 5 | Incident correction | (legacy defined name) | **NON_OBVIOUS_2** (`post_incident_2024_correction` — cell-content proxy H22=0.92) |

## Границы честности (явно задокументированы)

- ❌ **Не используем реальные данные ВкусВилла**. Все цифры модельные на общепринятых принципах.
- ❌ **Не реализуем VBA-макросы** — только формулы Excel (VBA — это бинарный артефакт в legacy; для разбора логики формул достаточно).
- ❌ **Не храним openpyxl defined names** — для NON_OBVIOUS_2 используем cell-content proxy (H22 + label в J7). Per user constraint «не предлагай новые Forge в рамках демо».
- ❌ **Не запускаем Excel/LibreOffice** — parity-check делается pure Python (variant b Q1) во избежание внешней системной зависимости.
- ❌ **Не создаём новые Forge/расширения архитектуры** в рамках этого demo (per user constraint, project-local LESSONS.md узкий).

## Теоретическая база

> **Knowing layer** (per [CON-56***REMOVED***(../../core_02/LESSONS.md) Pattern #1 — sibling research↔artifact architecture). Двунаправленный cross-link: этот файл (artifact layer) ← research layer; обратная ссылка из research → [`vkusvill_research/README.md`***REMOVED***(../vkusvill_research/README.md) «## Практическая реализация».

Связанный **research-слой** для этого артефакта: [`../vkusvill_research/`***REMOVED***(../vkusvill_research/) ([`docs_10/ROADMAP_VV_002_RESEARCH.md`***REMOVED***(../../docs_10/ROADMAP_VV_002_RESEARCH.md), промт 63).

Там лежит deep-research по ВкусВилл × AI-автоматизация (33 секции per brief `pompts_11/064_04_vkusvill_ai_avtomatizaciya.md`), Tier 1/2/3 source-mining по [CON-55***REMOVED***(../../core_02/LESSONS.md) (anti-hallucination tag protocol). **46 sources собраны** (S001–S083), 8 файлов research заполнены, Stages 1–4 закрыты (CHANGELOG v5.106.0).

**Конкретные cross-link файлы** (все 8, релевантность к этому артефакту):

| Research file | Что это | Связь с артефактом |
|---|---|---|
| [`01_business_scale.md`***REMOVED***(../vkusvill_research/01_business_scale.md) | Масштаб ВкусВилл + ТехВилл + timeline 2022-2026 | Контекст для бизнес-логики 3 категорий (молочка/крупа/напиток) |
| [`02_supply_chain_economics.md`***REMOVED***(../vkusvill_research/02_supply_chain_economics.md) | Экономика ошибок forecast + KPI ритейла | **Прямое обоснование** SMA/Z=1.65/shelf-life/INCIDENT-correction в нашем .xlsx |
| [`03_legacy_and_forecasting.md`***REMOVED***(../vkusvill_research/03_legacy_and_forecasting.md) | 10-stage pipeline reconstruction + Excel/VBA legacy | **Доказывает relevancy** нашего reverse-engineering подхода к реальному pipeline ВкусВилл |
| [`04_ai_role_and_stack.md`***REMOVED***(../vkusvill_research/04_ai_role_and_stack.md) | Реальный стек ВкусВилл (Python/SQL/API в вакансии) | Артефакт демонстрирует 3 из топ-5 требуемых навыков |
| [`05_cases_and_competitors.md`***REMOVED***(../vkusvill_research/05_cases_and_competitors.md) | Позиция среди enterprise-решений конкурентов | Показывает, что модельный .xlsx vs X5/Лента ML — честный scale-срез |
| [`06_candidate_profile.md`***REMOVED***(../vkusvill_research/06_candidate_profile.md) | Профиль идеального кандидата по 6 осям | Наш артефакт = «proving» часть кандидата из этого профиля |
| [`07_interview_strategy.md`***REMOVED***(../vkusvill_research/07_interview_strategy.md) | **110 вопросов с разбором** | Наш артефакт даёт ответ на вопросы Excel/VBA + vibe-coding категории |
| [`08_final_synthesis.md`***REMOVED***(../vkusvill_research/08_final_synthesis.md) | **8-уровневая схема + 10 AQ-ответов + cover letter** | Связывает этот демо-артефакт с реальным откликом (elevator-pitch для интервью) |

Это превращает артефакт из «упражнения» в **«доказательство понимания бизнеса»**: research даёт **knowing** (что реально происходит в ВкусВилл), артефакт даёт **proving** (что кандидат реально умеет). Двунаправленный паттерн зафиксирован в CON-56.

## Реестр

Документ зарегистрирован в `docs_10/DOCUMENT_REGISTRY.md` (ACTIVE counter +1 для VV-001, +1 для VV-002) и `docs_10/INDEX.md` под roadmap_id `ROADMAP-VV-001`.

> **⚠️ Файлы, исключаемые из отклика на вакансию** (служебные, не deliverable): [`BUFFY_GUIDANCE.md`***REMOVED***(BUFFY_GUIDANCE.md) (личные указания ассистента Buffy — не часть исследования), [`STEPS.md`***REMOVED***(STEPS.md) и [`LESSONS.md`***REMOVED***(LESSONS.md) (рабочие журналы). В отклик включаются: `model_forecast.xlsx`, `business_logic.md`, `short_report.md` + (опционально) `forecast.py`/`parity_check.py`/`parity_report.md`.

Роадмап-документ: `docs_10/ROADMAP_VKUSVILL_DEMO_062.md`.
Контракт Teamwork-сценария: `runtime_05/scenarios/vkusvill_demo.yaml`.
