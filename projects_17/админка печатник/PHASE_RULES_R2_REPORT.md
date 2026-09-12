# PHASE_RULES_R2_REPORT.md — S2: движок правил ProductionRule → RuleVerdict

> **Статус:** COMPLETE · **Дата:** 2026-09-12
> **Этап:** S2 потока A (Smart Order Intelligence) · РОАДМАП_v7 §3 · промт_печатник_6 (PHASE R2)
> **Верификация:** 371 passed (printcalc, было 349 → +22 новых S2-тестов) · mypy clean (67 файлов, py3.12)

---

## 1. Что сделано

| Артефакт | Файл | Суть |
|---|---|---|
| Движок правил | `printcalc/src/printcalc_web/rules/engine.py` | `evaluate_order`/`evaluate_text`: OrderDraft + паки → `RuleVerdict` (proposed_operations / missing / suggestions / fired_rules / ready_for_calculator) + `to_json` для S3 |
| Классы вердикта | там же | `OperationProposal` (auto=False **константа** — `__post_init__` запрещает True), `MissingItem` (валидация field по закрытому набору), `Suggestion` (rule_id — источник для UI), `RuleVerdict` |
| Сид OP-22 | `store.py` (DEFAULT_OPERATIONS) | «Плоттерная резка», trigger=`work_plotter_cut` (S0-долг закрыт); чек-лист: контур замкнут / рез по контуру / плёнка не порвана |
| Работа wide | `wide/config.py` + `wide/spec.py` | `WorkPrice("Плоттерная резка", unit="шт", 0/0)` + slug `plotter_cut`: флаг `work_plotter_cut` — валидный вход wide и триггер задания |
| Тесты | `tests/test_rules_engine.py` | 22 теста: golden-вердикты §4.1–4.4 (включая DoD «бэклит без количества → False»), семантика отсутствия фактов, дубль-missing, неизвестный продукт, идемпотентность, JSON-контракт, OP-22 в плане производства |

## 2. Ключевые решения S2

1. **Пак матчится по `product_label`** черновика (не по product=wide): уникальность label
   гарантирована load_packs с S0. Внутри пака — equality-матчинг `when_facts`
   (OrderDraft.fact, bool → "true"/"false"); отсутствие факта = «не матч», не «ложь» (§3.8).
2. **blocking-missing — только из фактов черновика**: quantity/size_mm (числовая основа
   любого калькулятора, CALCULATOR_MATRIX п.4). `require` правил даёт **unblocking**
   missing («макет с контуром?» — производство, расчёт не блокирует) с source=rule_id;
   дубль с blocking исключён (require: quantity не порождает второй «Количество?»).
3. **ready_for_calculator = нет blocking-missing**. Golden: бэклит 80×60 без qty → False
   (DoD §3); с «3 шт» → True; баннер 3×6 без qty → False; наклейка 50×30/149 шт → True.
4. **auto=True невозможен по контракту** — dataclass падает на __post_init__: тест
   фиксирует, что «распознать ≠ предложить» не обходится из кода (анти-правило 1).
5. **OP-22 seed через триггер-флаг доп-работы** (`work_plotter_cut`): соответствует
   механике каталога (§3 OPERATIONS_CATALOG — операция попадает в план, если trigger
   в наборе триггеров заказа) и решению Дениса «цена — WORK_PRICES на ревью S2»
   (РОАДМАП_v7 §10): запись работы с ценой 0/0 существует, цена проставляется владельцем.

## 3. Честная фиксация: work-флаг валидируется схемой wide

Первая попытка теста «подтверждённая резка → задание OP-22» упала:
`create_order` прогоняет params через `calculate()` → `validate_inputs` по FieldSpec,
и `work_plotter_cut` был «неизвестным полем входа». Причина: work-флаги wide
генерируются из `WideConfig.works` (канон WORK_PRICES), а не из сида операций.
Следствие: для триггера OP-22 нужна запись в WORK_PRICES — добавлена с ценой 0/0
(см. §2.5). Тест `test_op22_enters_plan_on_confirmed_flag` теперь проходит
полный конвейер: create_order → generate_production_plan → OP-22 в заданиях.

## 4. DoD РОАДМАП_v7 §3

- ✅ `engine.py`: ProductionRule → RuleVerdict (proposed/missing/suggestions) —
  правила из YAML-паков S0, факты из нормализатора S1.
- ✅ Идемпотентность: повторный evaluate — байт-в-байт тот же вердикт (и JSON).
- ✅ Анти-тест auto-применения: OperationProposal(auto=True) → ValueError.
- ✅ `ready_for_calculator` корректен на всех golden-примерах
  (в т.ч. §4.4 бэклит без количества → False).
- ✅ OP-22 посеян в каталог операций (долг S0 закрыт).

## 5. Открытые вопросы (не блокируют S3)

1. **Цена «Плоттерной резки»** — 0/0 в WORK_PRICES до ревью с вами (решение §10).
2. **Имя операции для UI** — OPERATION_LABELS v1 покрывает только операции паков
   (OP-22/15/13/14/04); на S5 имя берётся из БД каталога (точное, живое).
3. **Баннер: обязателен ли qty?** — сейчас «Баннер 3×6» без тиража даёт blocking
   «Количество?» (тираж нужен для сметы). Если для баннера допустима продажа
   «за м² без тиража» — это правка BLOCKING_FIELDS (отдельное решение).
