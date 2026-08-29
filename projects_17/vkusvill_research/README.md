# vkusvill_research/ — Deep Research по ВкусВилл × AI-Автоматизация

> **Версия:** 0.1 (scaffold, 2026-08-06)
> **Parent roadmap:** [`docs_10/ROADMAP_VV_002_RESEARCH.md`***REMOVED***(../../docs_10/ROADMAP_VV_002_RESEARCH.md)
> **Source brief:** [`pompts_11/064_04_vkusvill_ai_avtomatizaciya.md`***REMOVED***(../../pompts_11/064_04_vkusvill_ai_avtomatizaciya.md)
> **Scope:** Full 33 секции per pomt 63 (user-confirmed in ask_user)
> **Integration:** Гибрид — sibling `vkusvill_demo/` (ROADMAP-VV-001) + этот research layer

## Что здесь

Это **исследовательский слой** для отклика на вакансию **ВкусВилл × "Специалист по AI-автоматизации бизнес-процессов"**.

Брат-проект [`vkusvill_demo/`***REMOVED***(../vkusvill_demo/) содержит **готовый артефакт** (модельный `.xlsx` + Teamwork 3 роли + parity-check), который доказывает навык.

Здесь лежит **понимание бизнеса**, которое превращает артефакт в осмысленный отклик, а не изолированное упражнение.

## Структура (8 файлов)

| Файл | Brief секции | Глава | Stage |
|---|---|---|---|
| [`01_business_scale.md`***REMOVED***(01_business_scale.md) | §3.1, §4, §28, §30 | масштаб, оргструктура, ТехВилл, timeline | 1 (Tier 1) |
| [`02_supply_chain_economics.md`***REMOVED***(02_supply_chain_economics.md) | §3.2, §10, §11 | бизнес-модель, экономика ошибок, KPI | 1 (Tier 1) |
| [`03_legacy_and_forecasting.md`***REMOVED***(03_legacy_and_forecasting.md) | §6, §7, §8, §9, §22 | Excel/VBA, дублирование, боли HM | 2 (Tier 2) |
| [`04_ai_role_and_stack.md`***REMOVED***(04_ai_role_and_stack.md) | §2, §5, §13, §14 | почему вакансия сейчас, vibe-coding, стек | 3 (Tier 3) |
| [`05_cases_and_competitors.md`***REMOVED***(05_cases_and_competitors.md) | §15, §16 | конкуренты, реальные кейсы | 2 (Tier 2) |
| [`06_candidate_profile.md`***REMOVED***(06_candidate_profile.md) | §12, §18, §20 | идеал, карта вакансии, 90 дней | 3 (Tier 3) |
| [`07_interview_strategy.md`***REMOVED***(07_interview_strategy.md) | §19, §21, §23, §24 | 110 вопросов, отклик, red/green | 4 (synthesis) |
| [`08_final_synthesis.md`***REMOVED***(08_final_synthesis.md) | §17, §25-§33 | методология, 10 ответов, схема | 4 (synthesis) |

Plus: [`SOURCES.md`***REMOVED***(SOURCES.md) — Tier 1/2/3 source registry с датами и надёжностью.

## Источники

[`SOURCES.md`***REMOVED***(SOURCES.md) — структурированный реестр:

```yaml
source:
  name: <publication/source>
  tier: 1|2|3
  url: <https://...>
  date: <YYYY-MM-DD or YYYY>
  reliability: высокая | средняя | низкая
  covers: <brief §section>
  extract: <что подтверждает, цитата если есть>
```

Tier-rule: Tier 3 не используем если Tier 2 закрыл вопрос (per ROADMAP_VV_002_RESEARCH §4).

## Практическая реализация

Артефактный слой отклика лежит в [`projects_17/vkusvill_demo/`***REMOVED***(../vkusvill_demo/) (ROADMAP-VV-001 v5.105.0).

Связка архитектурно:

```
ИССЛЕДОВАНИЕ          →  АРТЕФАКТ              →  ОТКЛИК
(этот каталог)              (vkusvill_demo/)          (deliverable)
```

В частности:

- Бизнес-логика 3 категорий (молоко/крупа/напиток) в `vkusvill_demo/business_logic.md` подкрепляется **контекстом ритейла** из файла `02_supply_chain_economics.md` (что значит forecast error для российской продуктовой сети).
- Tech stack модельного .xlsx (Python + openpyxl + JSON-based parity-check) сравнивается с **реальным стеком ВкусВилла** из файла `04_ai_role_and_stack.md` (Python/SQL/API восстребованы per тексту вакансии).
- «Вайб-кодинг» должность в файле `04_ai_role_and_stack.md` подтверждает **рабочий цикл** из `vkusvill_demo/STEPS.md` (specialist читает legacy Excel → формулирует требования → AI-assisted coding → тестирует vs legacy → итерация).

Этот cross-link превращает артефакт из «упражнения» в «доказательство понимания бизнеса».

## Tag Protocol (anti-hallucination per CON-55)

Каждое существенное утверждение в research-файлах начинается с одного из 6 маркеров:

- `[ФАКТ***REMOVED***` — ≥2 независимых источника или Tier 1 + URL
- `[СИЛЬНАЯ ГИПОТЕЗА***REMOVED***` — 1 Tier 1/2 + логика
- `[СЛАБАЯ ГИПОТЕЗА***REMOVED***` — Tier 3 / косвенные сигналы
- `[ПРЕДПОЛОЖЕНИЕ***REMOVED***` — допущение, явное как допущение
- `[НЕТ ДАННЫХ***REMOVED***` — пробел, NO экстраполяции

Per CON-55: маркеры применяются **инлайн к каждому утверждению**, а НЕ disclaimer в начале/конце документа.

## Status (по Stage)

| Stage | Done? |
|---|---|
| Stage 0 — scaffold (этот README + 8 файлов + SOURCES) | 🟢 |
| Stage 1 — Tier 1 baseline (company + scale + economics) | ⚪ pending |
| Stage 2 — Tier 2 sector (legacy + competitors + cases) | ⚪ pending |
| Stage 3 — Tier 3 stack + talent | ⚪ pending |
| Stage 4 — synthesis (interview + final model) | ⚪ pending |
| Stage 5 — close-out (CHANGELOG + LESSONS + .freebuff_result) | ⚪ pending |

---

## Honest disclosure

Это **модельное исследование** для подготовки к собеседованию в реальную компанию. Не маркетинговый pitch, не реклама ВкусВилла, не выдумка «как они работают». Цель per brief §33 — «дать кандидату максимально реалистичное представление о том, куда он идёт».

Если где-то не нашли данных — пишем `[НЕТ ДАННЫХ***REMOVED***` и НЕ пытаемся экстраполировать (brief §33 «не пытайся понравиться кандидату»).

---

*README создан как scaffold 2026-08-06 в рамках ROADMAP-VV-002 Stage 0.*
