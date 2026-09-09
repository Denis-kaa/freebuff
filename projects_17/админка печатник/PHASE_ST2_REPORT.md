# PHASE_ST2_REPORT.md — Stage 2: Estimate + Snapshot (роадмап v6 / промт_5)

> Дата: 2026-09-09 · Статус: COMPLETE · Правило: «Preserve existing contracts. Extend, don't rewrite» — ни один существующий контракт не изменён ломающим образом.
> Основа: промт_печатник_4 (§22 смета, §24 статусы, §49 snapshot, §9 без ручного переноса), промт_печатник_5 (Stage 2 ТЗ + MVP-вердикт + отчёт §22).

## 1. Что сделано

- **Estimate** как первоклассная сущность: позиции резолвятся тем же серверным
  механизмом, что и заказы (`_resolve_item`) — цены приходят только с сервера
  (каталог/движок), клиентская цена доверия не имеет.
- **Статусы §24** закрытым словарём + таблица разрешённых переходов
  (`ESTIMATE_TRANSITIONS`): draft→sent→viewed→accepted, терминальные
  rejected/expired; недопустимые переходы запрещены на уровне store (ANTI-6b).
- **Immutable snapshot §49** (`calc_snapshots`): при accept фиксируются
  engine_version (printcalc.__version__), registry_checksum (sha256 спек всех
  калькуляторов), catalog_checksum (sha256 активного прайса), policy_version,
  details (total + позиции). Повторный accept идемпотентен (ровно один snapshot
  на смету — UNIQUE). Правка сметы после accept запрещена.
- **Заказ из сметы §9**: `create_order_from_estimate` переносит позиции,
  сумму, клиента, ссылки без ручного ввода; цены берутся из сохранённых позиций
  сметы БЕЗ пересчёта (изменение прайса задним числом не влияет); одна смета —
  один заказ; только из accepted.
- **Архитектурное уточнение промт_5**: snapshot хранит результат consumption,
  «если он был рассчитан» — `details_json` открыт для Stage 3 (Consumption →
  Orders) без переделки схемы Estimate.
- **UI «Сметы»**: список с фильтром статусов, создание с позициями (из прайса /
  вручную), карточка со статусными кнопками и строкой snapshot, заказ из сметы
  (оператор выбирает только способ оплаты).

## 2. Какие файлы изменены

- `src/printcalc_web/db.py` — схема estimates/estimate_items/calc_snapshots,
  индексы, миграция `orders.estimate_id` (аддитивно, идемпотентно).
- `src/printcalc_web/store.py` — раздел «сметы»: ESTIMATE_STATUSES,
  ESTIMATE_TRANSITIONS, create/get/list/update/transition/accept_estimate,
  create_order_from_estimate, _catalog_checksum, _registry_checksum;
  `orders`-словари теперь отдают estimate_id.
- `src/printcalc_web/api.py` — модели EstimateItemIn/EstimateIn/EstimatePatch/
  EstimateStatusPatch/OrderFromEstimateIn; PATCH использует exclude_unset
  (патч note не сбрасывает клиента).
- `src/printcalc_web/views.py` — страница `/estimates`.
- `src/printcalc_web/templates/_shell_top.html` — пункт «Сметы» в сайдбаре.
- `src/printcalc_web/static/style.css` — аддитивный блок: pill-бейджи статусов,
  modal-actions, plain-item, est-* классы.

## 3. Какие файлы созданы

- `src/printcalc_web/templates/estimates.html`
- `src/printcalc_web/static/estimates.js`
- `tests/test_estimates.py` (11 unit)
- `tests/test_api_estimates.py` (4 интеграционных)
- `PHASE_ST2_REPORT.md` (этот файл)

## 4. Какие API добавлены

- `GET  /api/estimates?status=&client_id=` — список с фильтрами
- `POST /api/estimates` — создание (201), валидация позиций/клиента/даты
- `GET  /api/estimates/{id}` — смета + snapshot
- `PATCH /api/estimates/{id}` — note/valid_until/client_id до accept (400 после)
- `POST /api/estimates/{id}/status` — перевод по §24 (400 при запрещённом)
- `POST /api/estimates/{id}/accept` — snapshot §49 (идемпотентно)
- `POST /api/estimates/{id}/order` — заказ из принятой сметы (201; 400 повторно)

Префикс оставлен `/api` (существующий контракт); миграция на `/api/v1/` —
отдельное решение, не в этой фазе (§15 промт_5: breaking changes только через
новую версию).

## 5. Какие модели добавлены

- `estimates` (id, status, total, client_id, note, valid_until, created_at, updated_at)
- `estimate_items` (id, estimate_id→CASCADE, kind CHECK, name, price, qty,
  calculator_id, params_json, price_list_item_id, position)
- `calc_snapshots` (id, estimate_id UNIQUE→estimates, engine_version,
  registry_checksum, catalog_checksum, policy_version, details_json, created_at)
- `orders.estimate_id` (nullable, REFERENCES estimates)

## 6. Какие миграции добавлены

- `CREATE TABLE IF NOT EXISTS estimates / estimate_items / calc_snapshots`
- `ALTER TABLE orders ADD COLUMN estimate_id` (идемпотентно по PRAGMA table_info)
- Применяются при `connect()` на старте приложения — на сервере схема
  обновится автоматически при рестарте сервиса (проверено в живой проверке).

## 7. Какие тесты добавлены

- `test_estimates.py`: резолв и сумма позиций; валидация (пустые items, чужой
  клиент, плохая дата); цена из каталога; гварды переходов; правка до/после
  accept; snapshot создаётся ровно один раз и содержит checksums; checksum
  каталога реагирует на изменение цен и стабилен; замороженные цены выживают
  после правки прайса; заказ переносит всё (клиент, сумма, estimate_id, manual
  остаётся manual); заказ только из accepted и единожды; фильтры списка.
- `test_api_estimates.py`: полный цикл HTTP (создать→sent→accept→заказ→повтор
  400→orders/{id}.estimate_id); правила переходов по HTTP; идемпотентный
  accept; валидация (422 пустые items, 400 чужой клиент, 404→400 несуществующая).

## 8. Результат тестов

- `pytest tests -q`: **144 passed** (было 129; +11 unit +4 интеграционных)
- `mypy src/ --ignore-missing-imports`: **Success: no issues found in 38 files**
- Живая проверка на сервере: см. раздел 12.

## 9. Что осталось

- Stage 3: Consumption → Orders (`POST /api/consumption/calculate`, расход в
  карточке заказа/сметы, Tablichki→SHEET, Digital→рулонная длина).
- Inquiry (§22 промт_5) — появится в Этапе 6 (Communication Hub); поле
  `inquiry_id` в Estimate осознанно не создавалось заранее (YAGNI, аддитивно
  добавится миграцией).
- Cost/Pricing как отдельные движки (§4.1–4.2 промт_5) — сейчас цены считает
  калькулятор (legacy-паритет); разделение через ADR при переходе.
- `/api/v1/` версионирование и единый error contract (§16) — перед Stage 6.

## 10. Известные ограничения

- Snapshot фиксирует checksums + total/позиции; полные input/calculation_result
  для calculator-позиций лежат в `estimate_items.params_json` (уже достаточно
  для воспроизведения), агрегация в snapshot.details — с Stage 3.
- `valid_until` не автопереводится в expired (нет планировщика); перевод
  вручную через status-эндпоинт.
- Смета не знает про налог отдельно (total как в заказе; налог внутри каль-
  куляторов — legacy-паритет сохранён по §24 промт_5).

## 11. UNKNOWN

- Точный формат «material_version» для snapshot (реестр материалов ещё не
  версионируется) — появится вместе со Stage 5 (Stock).
- Поведение при удалении клиента, на которого ссылается accepted-смета
  (сейчас FK без CASCADE, клиент архивируется, а не удаляется).

## 12. Риски следующего этапа

- Consumption → Orders затрагивает карточку заказа (главный экран) — риск
  регрессии приёма заказа; митигируется: сначала API + тесты, UI последним.
- Проверка legacy-vs-engine для Tablichki SHEET-режима может вскрыть расхождения
  с формулой Табличек — правило §24 промт_5: паритет, при расхождении ADR.

## DoD §21 промт_5

[x] код написан [x] миграции готовы [x] API готовы [x] тесты готовы
[x] ошибки обработаны (StoreError→400, guard-переходы) [x] документация
(этот отчёт) [x] существующий функционал не сломан (144 зелёные, в т.ч. все
старые) [x] integration test проходит [x] acceptance scenarios проходят
(cycle-тест) [x] git diff проверен [x] нет debug print [x] нет hardcoded
secrets [x] нет TODO вместо реализации
