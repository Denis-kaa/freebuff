# PHASE_ST5_REPORT.md — Этап 5: Склад (роадмап v6 / промт_4 §19–21)

> Дата: 2026-09-09 · Статус: COMPLETE · Коммит: см. git log (`stage-5: stock ledger, reserve/consume, purchase planner`)
> Основа: промт_печатник_4 §19–21, промт_печатник_5 §7.1 (типы движений).

## 1. Что сделано

- **Ledger-модель склада** (`stock_movements`): движение — единственный источник
  истины. Типы — закрытый словарь (ANTI-6b): `PURCHASE / RESERVE / RELEASE /
  CONSUME / ADJUST`.
- **Позиция склада** по материалу: `physical` (закупка − списание), `reserved`
  (резерв − снятие), `estimated = physical − reserved` — расчётный остаток «~».
  `ADJUST` — set-семантика инвентаризации (дельта до посчитанного).
- **Резерв/списание заказа без ручного ввода**: `production_consumption`
  берётся из `consumption_json` позиций (посчитан движком на Этапе 3).
  Резерв идемпотентен (второй раз — 400); списание конвертирует RESERVE→CONSUME;
  снятие после списания запрещено.
- **Планировщик закупок** (§21): `Need = Required − Available − Reserved`,
  округление вверх до `pack_size` (новое поле материала + миграция).
  Внешний спрос — через `required` (сумма планов производства).
- **API**: `GET /stock`, `GET /stock/movements`, `POST /stock/adjust`,
  `POST /materials/{id}/purchase`, `POST /orders/{id}/materials/reserve|release|consume`,
  `POST /stock/purchase-plan`.
- **UI**: блок «Склад» на странице «Материалы» (позиции, последние движения,
  инвентаризация/приёмка в один клик, план закупок); кнопки «Резерв на складе»
  и «Списать материалы» в карточке заказа.
- **Миграция**: `materials.pack_size REAL` — аддитивная, идемпотентная.

## 2. Инварианты (проверяются тестами)

| Инвариант | Тест |
|---|---|
| Пустая позиция = 0/0/0 | `test_empty_position_is_zero` |
| RESERVE не трогает physical (§19) | `test_reserve_does_not_touch_physical` |
| ADJUST задаёт physical напрямую, идемпотентен | `test_adjust_sets_physical_to_counted` |
| Закрытый словарь типов движений | `test_unknown_movement_kind_rejected` |
| Резерв из consumption_json, идемпотентен | `test_reserve_order_from_consumption` |
| Списание конвертирует резерв, повтор запрещён | `test_consume_converts_reserve` |
| Release после consume блокирован | `test_release_after_consume_blocked` |
| Нет расхода — резервировать нечего | `test_reserve_without_consumption_rejected` |
| Округление закупки до упаковки | `test_purchase_plan_min_stock_triggers` |
| Внешний спрос в плане | `test_purchase_plan_with_external_required` |
| Reserved уменьшает доступное | `test_purchase_plan_accounts_reserved` |
| HTTP-цикл приёмка→резерв→списание→ADJUST→план | `test_stock_http_cycle` |

## 3. Файлы

- `src/printcalc_web/db.py` — схема `stock_movements` + миграция `pack_size`
- `src/printcalc_web/store.py` — ledger, позиции, резерв/списание, план закупок
- `src/printcalc_web/api.py` — 6 эндпоинтов склада
- `src/printcalc_web/templates/materials.html`, `static/materials.js` — склад-панель
- `src/printcalc_web/templates/orders.html`, `static/orders.js` — кнопки резерва/списания
- `tests/test_stock.py` — 14 тестов (unit + HTTP)

## 4. Метрики

- Тесты: **181 passed** (было 167), mypy clean.
- Золотые тесты калькуляторов не тронуты (паритет легаси-цен сохранён).

## 5. Что НЕ входит (осознанно)

- Интеграция списания с завершением production-заданий (автосписание при
  «все задания готовы») — следующий шаг Этапа 5b.
- Себестоимость заказа из закупочных цен (COGS) — Этап 9 (аналитика).
- Ручные корректировки резерва (частичный резерв) — по потребности.
