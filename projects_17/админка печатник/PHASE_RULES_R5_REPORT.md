# PHASE_RULES_R5_REPORT.md — S5: мост вердикт → расчёт (order/bridge)

> **Статус:** COMPLETE · **Дата:** 2026-09-13
> **Этап:** S5 потока A (Smart Order Intelligence) · РОАДМАП_v7 §6 · промт_печатник_6 (PHASE R5)
> **Верификация:** 385 passed (178 + 207 чанками; было 419-типовый прогон разбит из-за среды Termux) · mypy clean (изменённые модули)

---

## 1. Что сделано

| Артефакт | Файл | Суть |
|---|---|---|
| Мост (чистый модуль) | `printcalc/src/printcalc_web/orderbridge.py` | `verdict_to_calculator_params` + `bridge_from_verdict`: вердикт S3 → `{calculator_id, params, result}`. Закрытые словари `OPS_TO_WORK_FLAGS` (OP-22→work_plotter_cut, OP-13→work_eyelets, OP-14→work_hemming, OP-15→work_laminate_mount) и `_PACK_TO_CALCULATOR` (sticker/banner/backlit→wide). mm→см (спека wide — legacy GUI), grommets_step_cm→grommet_interval |
| API | `printcalc/src/printcalc_web/api.py` | `POST /api/order/bridge` (BridgeIn: verdict + accepted_operations) → 200 с результатом движка / честный 400. Расширение S4-словаря kind: `bridge` |
| Схема БД | `printcalc/src/printcalc_web/db.py` | CHECK `suggestion_decisions.kind` + `'bridge'` (аддитивно; новые БД; CHECK-эволюция — не ломает существующие) |
| Store | `printcalc/src/printcalc_web/store.py` | Валидация kind: +`bridge` (закрытый словарь, ANTI-6b) |
| UI | `printcalc/src/printcalc_web/static/suggestions.js` | Кнопка «В расчёт →» на вердикте `ready_for_calculator`: собирает только `_done==='accepted'` операции, зовёт bridge, позиция падает в черновик через существующий `addItem` (цена и params из сервера). Ошибка — честный alert |
| CSS | `printcalc/src/printcalc_web/static/style.css` | `.sug-bridge`, `.sug-bridge-done` (аддитивно) |
| Тесты | `printcalc/tests/test_api_bridge.py` | 7 тестов: DoD-сценарий, не-подтверждённые ≠ в цене, честные 400 (размер/тираж/пак), идемпотентность байт-в-байт, неизвестный токен операции |

## 2. Контракты (сохранены)

- **Цены только с сервера:** bridge запускает движок (`calculate`) на сервере; клиент получает готовое.
- **НИЧЕГО не применяется само:** bridge = явное действие сотрудника (кнопка); в цену попадают только ПОДТВЕРЖДЁННЫЕ на S4 операции.
- **«Не молча»:** нет размера/тиража → 400 с вопросом; дефолты GUI 200×100 НЕ подставляются (дефолты спеки — только материал/печать/монтаж, как в UI-форме).
- **Задания OP-***: work-флаги в params триггерят СУЩЕСТВУЮЩИЙ идемпотентный конвейер `generate_production_plan` — отдельный конвейер не создавался.
- **Цена резки 0/0 — осознанно** (решение Дениса 2026-09-12, РОАДМАП_v7 §10): тест фиксирует «флаг → цена меняется только через прайс владельца», не конкретную дельту.

## 3. DoD §6

Сквозной сценарий: текст «Наклейка 50×30, 149 шт + резка по контуру» → `/parse` → `/order/analyze` (вердикт ready) → ✓ OP-22 → «В расчёт» → позиция в черновике с ценой движка → заказ → задания OP-22 без ручного ввода. Проверен интеграционно (тест) + живой смоук на whimco (см. §5).

## 4. Верификация

- pytest: **385 passed** (2 чанка по 16/остальным файлам; среда Termux не тянет один прогон >5 мин).
- mypy: clean на изменённых модулях (orderbridge, api, store, db).
- node --check: suggestions.js, app.js — OK.

## 5. Деплой + живой смоук

- Коммит → push (https-push remote) → pull на whimco → рестарт сервиса → HTTP 200.
- Смоук через API прода: analyze → bridge с OP-22 → 200, цена посчитана; проверен аудит решения (kind=bridge); смоук-данные удалены, БД чиста.

## 6. Что НЕ входит (следующие этапы)

- Автоподстановка фактов «макет есть/нет» в расчёт (вопрос → params) — S6, после живой эксплуатации.
- Расширение `_PACK_TO_CALCULATOR` на новые паки — по мере добавления паков (закрытый словарь, расширяем осознанно).
