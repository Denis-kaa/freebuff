# PHASE_RULES_R4_REPORT.md — S4: UI-поверхность подсказок

> **Статус:** COMPLETE · **Дата:** 2026-09-13
> **Этап:** S4 потока A (Smart Order Intelligence) · РОАДМАП_v7 §5 · промт_печатник_6 (PHASE R4)
> **Верификация:** 419 passed (было 371 → +7 S4-тестов и +41 от параллельной работы) · mypy clean (70 файлов)

---

## 1. Что сделано

| Артефакт | Файл | Суть |
|---|---|---|
| Таблица аудита | `printcalc/src/printcalc_web/db.py` | `suggestion_decisions`: inquiry_id (FK), decision (closed set), kind, token, field, source_text, payload (JSON), operator, created_at — CREATE IF NOT EXISTS, идемпотентно |
| Store | `printcalc/src/printcalc_web/store.py` | `record_suggestion_decision` (валидация закрытых словарей → StoreError), `list_suggestion_decisions` (новые сверху, фильтр по заявке) |
| API | `printcalc/src/printcalc_web/api.py` | `POST /api/suggestions/decision` (201; только ЛОГИРУЕТ решение), `GET /api/suggestions/decisions?inquiry_id=` |
| Frontend | `printcalc/src/printcalc_web/static/suggestions.js` (новый) | Рендер вердикта: «Распознано» → «Предложения» (✓/Изменить) → «Не хватает данных» (Да/Нет) → «Нужно уточнить» (опции + Уточнить позже); каждое решение → аудит-API |
| Интеграция | `printcalc/src/printcalc_web/static/app.js` | После «Разобрать» — вызов `/api/order/analyze` с parse_result; ошибка анализа НЕ ломает обычный разбор |
| Разметка | `printcalc/src/printcalc_web/templates/index.html` | `#suggest-box` в панели «Быстрый ввод» + подключение suggestions.js |
| Стиль | `printcalc/src/printcalc_web/static/style.css` | `.suggest-box` + строки/вопросы; mobile-first (колонка ≤640px), палитра приложения |
| Реестр | `data_13/missing_registry.yaml` | REGISTER-FIRST: `suggestions_ui` (registered → prompt_written → implemented), `order_rules_engine` дооформлен как implemented |

## 2. Контракты поведения (анти-правила §6 промт_6 — соблюдены)

1. **Ничего не применяется само:** сервер только логирует решение; позиция
   в заказ попадает действием сотрудника (`✓` → `addItem` с `needs_calc`,
   цена 0 — цена появится на S5, клиент цену не считает).
2. **Три разных статуса:** факт («Распознано») / предложение (✓/Изменить) /
   подтверждённое (журнал) — визуально и по данным разделены.
3. **Closed vocabulary:** decision ∈ {accepted, changed, rejected, deferred},
   kind ∈ {operation, question, ''} — на уровне pydantic (422) И store
   (StoreError → 400). Двойная защита, ANTI-6b.
4. **Контекстные вопросы:** показываются только вердиктные suggestions/missing
   (§4.5), не весь список.
5. **Правил во frontend нет:** JS рендерит готовый вердикт сервера.

## 3. DoD §5 — сценарий «порезать поштучно»

`Наклейка 20×30, 40 шт, с монтажной, порезать поштучно` →
pack=sticker, qty=40, size 200×300 мм, предложения OP-22 «Плоттерная резка» +
OP-15 «Накатка на основу» (auto=false у обоих), вопросы: контур макета
(layout) и накатка плёнки. Оператор: ✓ на OP-22 → позиция в черновике,
ответ «Да, контуры есть» → обе записи в журнале решений с operator+created_at.
Терминология не нужна. Закреплено тестом `test_dod_piecewise_scenario_walk`.

## 4. Тесты (+7)

`tests/test_api_suggestions.py`: аудит ✓ (кто/когда/что), закрытые словари
(422), deferred/rejected + порядок журнала, фильтр по заявке (через НАСТОЯЩИЕ
заявки — FK включён, никаких выдуманных id), DoD-проход, идемпотентность
вердикта (S3-контракт не сломан), HTML-страница содержит `#suggest-box` и
suggestions.js.

Полный прогон: **419 passed** (2:29), mypy: **no issues in 70 files**.
Из тестового клиента ASGI найден нюанс: query-параметры — только через
`params=` (строка запроса в path не парсится) — зафиксировано в тесте.

## 5. Деплой и живой смоук

- push → pull на whimco → рестарт `printcalc-web` → active, HTTP 200.
- Смоук на проде: `POST /api/order/analyze` (DoD-фраза) → вердикт ОК;
  `POST /api/suggestions/decision` (accepted, OP-22) → 201;
  `GET /api/suggestions/decisions` → запись присутствует; тестовая запись
  удалена из БД (смоук не оставляет данных).

## 6. Открытые вопросы

1. **operator=«Денис» захардкожен** — учёт сотрудников/ролей не входит в S4
   (RBAC появится позже); поле готово, подстановка — одна строка.
2. **Изменить** — сейчас логирует intent и возвращает фокус на ✓; содержимое
   правки (какая именно альтернатива) — предмет S5 (связка с калькулятором).
3. payload ответов на вопросы хранится как JSON-слепок — аналитика по
   ответам (какой вариант выбирают чаще) — Поток B (Reports Hub).

## 7. Что дальше

- **S5** — `ready_for_calculator=true` → авто-переход в расчёт без повторного
  ввода; подтверждённые операции → конвейер заданий (идемпотентно).
- После S5 поток A закрыт → Поток B (Reports Hub H1–H6).
