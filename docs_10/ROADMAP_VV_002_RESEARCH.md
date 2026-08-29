# ROADMAP-VV-002 — Deep Research: ВкусВилл × AI-Автоматизация бизнес-процессов

> **Версия:** 0.1 (scaffold-stage, 2026-08-06)
> **Тип:** orchestration document (аналог ROADMAP_FORGE_RECONCILIATION.md / ROADMAP-VV-001)
> **Scope:** Full 33 секции (per user choice в ask_user)
> **Integration:** Гибрид — `projects_17/vkusvill_demo/` + sibling `projects_17/vkusvill_research/` с двунаправленной README cross-link
> **Brief:** [`pompts_11/064_04_vkusvill_ai_avtomatizaciya.md`***REMOVED***(../pompts_11/064_04_vkusvill_ai_avtomatizaciya.md) (1098 строк)

## 1. Контекст и наследие

**ROADMAP-VV-001 v5.105.0** (закрыт ранее в этой сессии) — это **артефактный слой** для отклика ВкусВилл: модельный `.xlsx` (3 категории × 12 недель × 3 листа) + Teamwork 3 роли + parity-check variant (b) pure-Python JSON. Лежит в `projects_17/vkusvill_demo/`.

**ROADMAP-VV-002** — это **исследовательский слой над тем же откликом**: вместо «артефакт демонстрирует навык» мы получаем «исследование демонстрирует понимание бизнеса → артефакт становится доказательством, а не самоцелью».

Сшивка:

```
 ВКУСВИЛЛ.COMPANY (research)
       │
       ▼
 SECTOR.CONTEXT (research)
       │
       ▼
 ВАКАНСИЯ.ROLE (research)
       │
       ▼
 КАНДИДАТ.PROFILE (research)
       │
       ▼
 АРТЕФАКТ.MODEL_XLSX (ROADMAP-VV-001)
       │
       ▼
 ОТКЛИК (deliverable)
```

Слой «артефакт» уже существует (VV-001). Слой «исследование» — это VV-002.

## 2. Scope (per brief pomt 63)

Полное покрытие 33 секций согласно pompt63 §1-§33. См. [`pompts_11/064_04_vkusvill_ai_avtomatizaciya.md`***REMOVED***(../pompts_11/064_04_vkusvill_ai_avtomatizaciya.md) для полного текста.

Иерархия секций (для traceability VV-002 → pompt63):

| VV-002 файл | Brief секции | Глава |
|---|---|---|
| `01_business_scale.md` | §3.1, §4, §28, §30 | масштаб, оргструктура, ТехВилл, timeline |
| `02_supply_chain_economics.md` | §3.2, §10, §11 | бизнес-модель, экономика ошибок, KPI |
| `03_legacy_and_forecasting.md` | §6, §7, §8, §9, §22 | Excel/VBA, дублирование, боли HM |
| `04_ai_role_and_stack.md` | §2, §5, §13, §14 | почему вакансия сейчас, vibe-coding, стек |
| `05_cases_and_competitors.md` | §15, §16 | конкуренты, реальные кейсы |
| `06_candidate_profile.md` | §12, §18, §20 | идеал, карта вакансии, 90 дней |
| `07_interview_strategy.md` | §19, §21, §23, §24 | 110 вопросов, отклик, red/green |
| `08_final_synthesis.md` | §17, §25, §26, §27, §29, §31, §32, §33 | методология, 10 ответов, схема |

`SOURCES.md` — реестр Tier 1/2/3 источников с датой/URL/надёжностью/что подтверждает.

## 3. Methodology — Anti-Hallucination Tag Protocol (CON-55)

**Каждое** существенное утверждение в research-файлах должно начинаться с маркера из 6 значений per brief §2 + §33:

| Маркер | Значение | Когда использовать |
|---|---|---|
| `[ФАКТ***REMOVED***` | подтверждённый факт | ≥2 независимых источника из разных Tier согласны, или Tier 1 + URL |
| `[СИЛЬНАЯ ГИПОТЕЗА***REMOVED***` | обоснованное предположение | 1 Tier 1/2 источник + логика |
| `[СЛАБАЯ ГИПОТЕЗА***REMOVED***` | интуиция | только Tier 3 / косвенные сигналы |
| `[ПРЕДПОЛОЖЕНИЕ***REMOVED***` | допущение | логическая цепочка, явная как допущение |
| `[НЕТ ДАННЫХ***REMOVED***` | не найдено публично | прямое признание пробела, NO экстраполяции |

Никаких предположений за факты. Никакой экстраполяции. Двух-источниковая верификация для всех чисел (выручка, кол-во магазинов, сотрудников).

Per `core_02/LESSONS.md CON-55`: тегирование должно применяться инлайн к каждому утверждению, а НЕ disclaimer в начале/конце документа.

## 4. Tier 1/2/3 Mining Strategy (thinker-with-files-gemini recommendation)

**Стратегия: 10-15 глубоких запросов в глубину, не 100 в ширину.**

Tier зависят друг от друга — если Tier 2 закрыл вопрос, Tier 3 не парсим.

### Tier 1 (Foundation, ~3-4 запроса)

1. `site:vkusvill.ru "О компании"` → масштаб, история, ключевые цифры
2. `site:vkusvill.ru/news/ "2024" OR "2023" OR "выручка" OR "открыл"` → динамика
3. `site:техвилл.рф` → структура IT-дочки, проекты, стек
4. `vkusvill.ru/team` or `/career` → оргструктура + открытые вакансии

### Tier 2 (Sector Analysis, ~3-4 запроса)

5. `site:retail.ru "ВкусВилл" (автозаказ OR распределение OR списания)` → боли отрасли
6. `site:cnews.ru OR site:tadviser.ru "ВкусВилл" (внедрение OR автоматизация OR ML)` → enterprise-проекты
7. `(site:vedomosti.ru OR site:rbc.ru) "ВкусВилл" (логистика OR IT)` → стратегические интервью
8. `интервью C-level "ВкусВилл" 2024 2025` → стратегия 2025-2026

### Tier 3 (Stack & Legacy, ~3-4 запроса)

9. `site:hh.ru "ВкусВилл" (forecasting OR "Excel" OR VBA OR "автозаказ")` → соседние вакансии = ground truth о стеке
10. `site:habr.com "ВкусВилл" (ML OR спрос OR прогноз)` → технические детали от сотрудников
11. `site:github.com "vkusvill" OR "vkusvill-tech"` → open-source следы (маловероятно, но бывает)
12. `t.me "ВкусВилл" (AI OR автоматизация OR HR)` → слухи + сигналы

**≤15 запросов** = gate для Tier expansion. Если после 15 запросов остаются лакуны — фиксируем в `[НЕТ ДАННЫХ***REMOVED***`, не продолжаем.

## 5. Anti-Hallucination Checklist (per CON-55 + brief §33)

- [ ***REMOVED*** Revenue / # stores / # employees = **dual-source verify** (Tier 1 + Tier 2)
- [ ***REMOVED*** При расхождении источников → показать ОБЕ цифры с датами (brief §26)
- [ ***REMOVED*** Если метрика не найдена → `[НЕТ ДАННЫХ***REMOVED***`, НЕ экстраполируем (brief §33)
- [ ***REMOVED*** Никаких утверждений «X% списаний» без источника
- [ ***REMOVED*** Утверждения про внутренние системы ВкусВилл (Excel/VBA) — строго по вакансиям Tier 3, не выдумываем
- [ ***REMOVED*** Утверждения про стратегию 2025-2026 — только из интервью C-level (Tier 1/2), не из общих трендов

## 6. Execution Plan

### Stage 0 — Scaffold (THIS)

✅ Main orchestration doc (этот файл)
✅ `projects_17/vkusvill_research/` directory + 8 stub files + SOURCES.md + README
✅ Cross-link `vkusvill_demo/README.md` ↔ `vkusvill_research/README.md`
✅ Registry: INDEX.md + DOCUMENT_REGISTRY.md ACTIVE bump
✅ LESSONS.md CON-55 (research methodology)

### Stage 1 — Tier 1 baseline (next)

- 3-4 web-research запроса
- Заполнить `01_business_scale.md` (ФАКТ-секция) + SOURCES.md
- Заполнить `02_supply_chain_economics.md` (ФАКТ-секция economic context)

### Stage 2 — Tier 2 sector analysis

- 3-4 запроса
- Заполнить `03_legacy_and_forecasting.md` + `05_cases_and_competitors.md`

### Stage 3 — Tier 3 stack & talent

- 3-4 запроса
- Заполнить `04_ai_role_and_stack.md` + `06_candidate_profile.md`

### Stage 4 — Interview prep (synthesis)

- Синтез из Stage 1-3
- Заполнить `07_interview_strategy.md` + `08_final_synthesis.md`

### Stage 5 — Close-out

- CHANGELOG entry + .freebuff_result
- Project-local STEPS.md final state
- Project-local LESSONS.md update с конкретными on-task findings (per user constraint не разрастаться)

## 7. Cross-link Pattern (thinker recommendation)

**Двунаправленная cross-link в существующих README. НЕ создаём `vkusvill_INDEX.md` (нарушает запрет на расширение архитектуры).**

- `vkusvill_demo/README.md` → секция `## Теоретическая база` (new) — указывает на `../vkusvill_research/README.md`
- `vkusvill_research/README.md` → секция `## Практическая реализация` — указывает на `../vkusvill_demo/README.md`

## 8. Project Boundary (per user constraint continuity)

Per pomt 62 + user directive «не расширять архитектуру платформы»:

- ❌ НЕ создаём новый Forge
- ❌ НЕ пишем в `core_02/LESSONS.md` широкие cross-cutting уроки (только CON-55 узкое)
- ❌ НЕ меняем ROADMAP_FORGE_RECONCILIATION.md (closed earlier в этой сессии)
- ❌ НЕ понятным будет: внешний `Runtime`/`Wizard`/`Forge` для research
- ✅ Project-local LESSONS.md в `vkusvill_research/` — узкое, точечное, on-task findings
- ✅ Project-local STEPS.md в `vkusvill_research/` — каждый шаг фиксируется

## 9. Status Tracker

| Stage | Status | Notes |
|---|---|---|
| Stage 0 (scaffold) | 🟢 in progress (this doc) | 11 файлов, registry bumps, CON-55 |
| Stage 1 (Tier 1) | ⚪ pending | start after scaffold close |
| Stage 2 (Tier 2) | ⚪ pending | gate: Stage 1 complete |
| Stage 3 (Tier 3) | ⚪ pending | gate: Stage 2 complete |
| Stage 4 (synthesis) | ⚪ pending | gate: Stages 1-3 done |
| Stage 5 (close-out) | ⚪ pending | gate: Stage 4 complete |

Per Stage 1-3 will run as subsequent turns with full Tier-by-Tier web research. Each Stage закрывается прежде чем следующий стартует (sequential gates per ROADMAP-VV-001 / ROADMAP-FR-001 lesson: нет parallelism между critical-path stages).

---

## 10. CAN-17 Compliance (anti-rewriting audit trail)

ROADMAP-VV-002 это **additive** слой:
- ROADMAP-VV-001 v5.105.0 НЕ переписывается (closed)
- ROADMAP_FORGE_RECONCILIATION.md НЕ модифицируется (its scope = Forge only)
- core_02/LESSONS.md получает только ADDITIVE CON-55 entry

## 11. References

- Brief: [`pompts_11/064_04_vkusvill_ai_avtomatizaciya.md`***REMOVED***(../pompts_11/064_04_vkusvill_ai_avtomatizaciya.md)
- Уже существующий артефакт: [`projects_17/vkusvill_demo/`***REMOVED***(../projects_17/vkusvill_demo/) (ROADMAP-VV-001)
- Lesson: [`core_02/LESSONS.md`***REMOVED***(../core_02/LESSONS.md) — CON-54 (Teamwork-decomposition), CON-55 (research-methodology, will be appended in Stage 0)
- Historic analogue: [`docs_10/ROADMAP_FORGE_RECONCILIATION.md`***REMOVED***(ROADMAP_FORGE_RECONCILIATION.md) (closed) — структурный template

---

*vv-002 scaffold создан 2026-08-06 — Stage 0 complete=readiness marker immediately follows.*
