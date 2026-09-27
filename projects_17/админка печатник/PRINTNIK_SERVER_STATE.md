# PRINTNIK SERVER STATE

> **Снимок фактического состояния проекта «Печатник»** для агента, продолжающего разработку.
> Дата: 2026-09-27 · Метод: только чтение (read-only), БД открыта в `mode=ro`, сервисы не тронуты.
> Классификация утверждений: `[FACT]` проверено командой/запросом · `[CODE]` видно в коде ·
> `[DOC]` только в документации · `[TEST]` подтверждено прогоном · `[INFERENCE]` вывод · `[UNKNOWN]`.

---

## 1. Server / Repository

- `[FACT]` Проект живёт **внутри монорепо платформы**: `/opt/freebuff` (git-репозиторий), проект в `/opt/freebuff/projects_17/админка печатник/`, приложение — `printcalc/`.
- `[FACT]` Прод-данные: `/opt/printcalc/data/printcalc.db` (SQLite, WAL). Прод-venv: `/opt/printcalc-venv`.
- `[FACT]` Отдельного git-репо у printcalc НЕТ — он часть `/opt/freebuff`.

## 2. Git

- `[FACT]` Ветка: `master` · HEAD: `b14846e` «docs(audit): AUDIT_REPORT…» (2026-09-25).
- `[FACT]` Remote: `origin = https://github.com/Denis-kaa/freebuff.git`.
- `[FACT]` Незакоммиченных изменений в скоупе проекта НЕТ (untracked-файлы только вне скоупа: `.share_tmp/`, `fix_*.py` и пр.).
- `[FACT]` Последние 20 коммитов: аудит-доки (b14846e), tunnel-фиксы, mailbox-агент (не «Печатник»), **Hub v2** (`5ce4122`, `3583b55`), **PHASE_UNITS** (`c9e234d`), авто-регенерация Reports Hub (`64a139b`), статус-отчёты, учебник (карточки производителей). В работе сейчас: ничего незавершённого в скоупе.

## 3. Tech Stack

- `[FACT]` Python **3.12.3** (`/opt/printcalc-venv`).
- `[FACT]` FastAPI 0.141.1, Starlette 1.6.0, Uvicorn 0.52.4, Jinja2 3.1.6, Pydantic 2.13.5, PyYAML 6.0.3, httpx 0.28.1, pytest 9.1.1.
- `[FACT]` **НЕТ**: SQLAlchemy, Alembic, Redis, PostgreSQL, React, TypeScript, Vite/Next.js, Docker, node_modules. Фронтенд — server-rendered Jinja2 + vanilla JS (12 модулей, без сборки).
- `[CODE]` Зависимости ядро = `[]` (pyproject); extras: web/test/telegram/rules — сознательный минимализм.
- `[FACT]` Миграции — собственный механизм `db.py` (`PRAGMA table_info`-guard + ADD COLUMN), НЕ Alembic.
- `[FACT]` mypy используется (clean на 22 файлах), линтеры в CI не сконфигурированы (`[UNKNOWN]` CI как таковой — см. §17).

## 4. Deployment

- `[FACT]` `printcalc-web.service`: active (running) с 2026-09-26, enabled; WorkingDirectory `/opt/freebuff/projects_17/админка печатник/printcalc`; ExecStart `/opt/printcalc-venv/bin/python -m printcalc_web --host 0.0.0.0 --port 8300`; env: `PRINTCALC_WEB_DB=/opt/printcalc/data/printcalc.db`, `PYTHONPATH=src`; Restart=on-failure.
- `[FACT]` `reports-hub.service`: active, :8310, `python -m services_08.reports_hub serve`, WorkingDirectory `/opt/freebuff`, токен через `EnvironmentFile=/etc/default/reports-hub` (права 600 root — `SECRET_PRESENT = true`, значение не выводилось).
- `[FACT]` Cron (root): автодеплой каждые 5 мин (`auto_deploy.sh pull`), регенерация Reports Hub каждые 5 мин (`regen_reports_hub.sh`, HEAD-stamp guard), nightly-audit — **другого проекта** (TeenFreelance).
- `[FACT]` Telegram/IMAP-поллеры в коде активны, но БЕЗ кредов → no-op (каналы выключены).

## 5. Database

`[FACT]` 20 таблиц (sqlite_master). Ключевые (имя · строки · поля · связи):

| Таблица | Строк | Ключевые поля | Связи |
|---|---|---|---|
| `clients` | 0 | id, name, kind, note, archived, created_at, updated_at | ← contacts, orders, estimates |
| `contacts` | 0 | client_id, channel, value | → clients |
| `orders` | 0 | status, payment_method, total, wishes, client_id, estimate_id | → clients, estimates |
| `order_items` | 0 | kind(price/calculator/manual), name, price, qty, calculator_id, params_json, price_list_item_id, consumption_json, segment_id, **unit** | → orders, price_list_items |
| `materials` | 11 | aliases_json, consumption_mode, base/purchase/price_unit, purchase_cost, roll_width/length, sheet_w/h, min_stock, supplier, active, pack_size | ← stock_movements |
| `estimates` | 0 | status, total, client_id, valid_until | → clients |
| `estimate_items` | 1* | kind, price, qty, calculator_id, params_json | → estimates |
| `calc_snapshots` | 0 | engine_version, registry_checksum, catalog_checksum, policy_version, details_json | → estimates |
| `operations` | 13 | code (OP-xx), name, steps_json, **checklist_json**, equipment, minutes, role, trigger, enabled | ← production_tasks |
| `production_tasks` | 0 | order_id, operation_id, status, sequence, checklist_result, started/completed_at | → orders, operations |
| `stock_movements` | 0 | material_id, order_id, kind, quantity | → materials, orders |
| `inbox_messages` | 1 | channel, external_id, chat_id, sender_handle, text, status, parsed_json, inquiry_id | → inquiries |
| `price_list_items` | 42 | name, price, **unit**, category, synonyms, usage_count, unverified, archived | ← order/estimate_items |
| `settings` | 0 | key, value | — |

Также: `inquiries`, `outbox_messages`, `suggestion_decisions`, `ui_sections`, `order_section_values`.
`[FACT]` Статусы: заказы/сметы — строковые статусы через закрытые кортежи (`ORDER_STATUSES`, статусные переходы см. store.py); production_tasks: `pending|in_progress|done|blocked` (`[CODE]` TASK_STATUSES).
`[FACT]` *1 строка estimate_items при 0 estimates — остаток смоук-теста (сирота; чистить НЕ буду по условию).
`[FACT]` Производственных данных НЕТ: 0 клиентов, 0 заказов — система задеплоена и исправна, реальный ввод данных владельцем ещё не начат.

## 6. API

`[FACT]` 78 эндпоинтов / 65 путей (живой OpenAPI :8300/openapi.json). Префикс `/api/...` (НЕ `/api/v1`). Группы:

- **clients (7):** GET/POST /api/clients, GET /api/clients/lookup, GET/PATCH /{id}, POST /{id}/contacts, DELETE /{id}/contacts/{cid}
- **materials (6):** CRUD + lookup + POST /{id}/purchase
- **orders (12):** CRUD + PATCH /{id}/client + GET /export.txt + materials/reserve|release|consume + production/generate + GET /production + GET /sections
- **estimates (7):** CRUD + accept + /order (конвертация) + status
- **production (4):** tasks list + start/complete/block
- **stock (4):** /stock, /adjust, /movements, /purchase-plan
- **price-list (9):** CRUD + export.csv + import + import-template + template.csv + similar + /{id}/synonyms
- **inbox (4) + inquiries (5):** inbox list/manual/archive/inquiry; inquiries + estimate + reply
- **replies/reply-templates (3):** GET /replies, GET /reply-templates, POST /{template_id}/render
- **parse/analyze/bridge (3):** POST /api/parse, POST /api/order/analyze, POST /api/order/bridge (Smart Order)
- **calculators (2):** GET /api/calculators, POST /api/calculate
- **consumption (1):** POST /api/consumption/calculate
- **operations (1)** · **margin (1):** GET /api/margin/report · **report (1):** off-catalog · **sections (4)** · **settings (2)**: payment-methods · **suggestions (2)**
- **Аутентификации НЕТ** — ни одного auth-эндпоинта `[FACT]`; защита = внутренний контур/VPN + tunnel-доступ `[INFERENCE]`.

## 7. Clients / Contacts

- `[CODE]` Таблицы clients+contacts, FK, lookup-эндпоинт, PATCH, привязка клиента к заказу (`PATCH /orders/{id}/client`).
- `[FACT]` История клиента: эндпоинта /clients/{id}/history нет; клиентская история — через GET /orders фильтр `[UNKNOWN]` (не проверял параметр).
- `[FACT]` Реальных клиентов 0 — автозаполнение/matching на живых данных не проявлялись; matching по sender_handle реализован в store (inbox→client) `[CODE]`.

## 8. Materials

- `[FACT]` 11 материалов: `aliases_json` (синонимы есть), consumption_mode (roll/sheet), base/purchase/price units, purchase_cost, roll_width/length, sheet dims, min_stock, supplier, active, pack_size.
- `[CODE]` API: CRUD + purchase; склад: stock_movements + purchase-plan.
- `[FACT]` Seed-данные сидируются при старте; примеры канонических имён в materials — без секретов (цены не выводил по требованию §21/этика — по запросу).
- `[CODE]` Runtime-прайс широкоформатных работ: `data/wide_prices.yaml` (шаблон `wide_prices.template.yaml` в репо) — правится владельцем без кода.

## 9. Orders

- `[CODE]` Модель: orders(status, payment_method, total, wishes, client_id, estimate_id) + order_items(kind: price|calculator|manual, params_json, consumption_json, segment_id, unit).
- `[CODE]` Статусная машина: ORDER_STATUSES в store.py (закрытый кортеж, loud при недопустимом статусе).
- `[CODE]` Связки: смета → заказ (`POST /estimates/{id}/order`), заказ → производство (`POST /orders/{id}/production/generate`), резерв/списание материалов на заказ (3 эндпоинта), экспорт задания в .txt.
- `[FACT]` Полей files/responsible/deadlines/payment_status в схеме НЕТ (payment_method есть; оплаты как процесса нет — Payment Hub не начат `[DOC]`).
- `[FACT]` 0 живых заказов; контур протестирован (469/481 тестов incl. units roundtrip).

## 10. Estimates

- `[CODE]` estimates + estimate_items + calc_snapshots; статусы через закрытый кортеж; accept-эндпоинт; конвертация в заказ.
- `[CODE]` Immutable snapshot: `calc_snapshots` хранит engine_version, registry_checksum, catalog_checksum, policy_version, details_json — снимок версий при создании.
- `[FACT]` Отдельных material_version/pricing_version/consumption_policy_version полей нет — они внутри policy_version/checksum'ов `[INFERENCE]`. Живых смет 0.

## 11. Calculators

`[FACT]` Живой реестр (`GET /api/calculators`) — **8/8, все зарегистрированы и отвечают**:

| Калькулятор | id | Код | Golden-тесты | Статус |
|---|---|---|---|---|
| Цифровая печать | digital | calculators/digital | test_digital_golden | РЕАЛИЗОВАН |
| Широкоформат | wide | calculators/wide (+ runtime-прайс) | test_wide_golden | РЕАЛИЗОВАН |
| Ризография | riso | calculators/riso | test_riso_golden | РЕАЛИЗОВАН |
| Вывески | sign | calculators/sign | test_sign_golden | РЕАЛИЗОВАН |
| Таблички | tablichki | calculators/tablichki | test_tablichki_golden | РЕАЛИЗОВАН |
| ЧПУ (лазер/фрезер) | cnc | calculators/cnc | test_cnc_golden | РЕАЛИЗОВАН |
| Дизайн | design | calculators/design | test_design_golden | РЕАЛИЗОВАН |
| Себестоимость | cost | calculators/cost | test_cost_golden | РЕАЛИЗОВАН |

- `[CODE]` Регистрация — явная в `printcalc_web/calculators.py` (`register_*` + `registry.register`); wide — с ценами доп. работ из runtime-файла владельца.
- `[CODE]` Конвейер каждого порта: config → spec → compute; вход/выход — typed dataclasses; `POST /api/calculate` единая точка.
- `[TEST]` 8 golden-сьютов с независимой деривацией ожиданий (пример: ЧПУ деривации в docstring test_cnc_golden; визитка 100 шт = 563.83 ₽ совпала с живым сервером).
- `[FACT]` «Только документация»/«не найдено» — таких НЕТ из списка §7.

## 12. Consumption Engine

- `[CODE]` Расположение: `src/printcalc/engine/consumption/` — engine.py, models.py, roll.py, adapters.py, normalize.py, units.py, rounding.py, errors.py.
- `[CODE]` Возможности (по grep, ~100 упоминаний): roll nesting, sheet nesting (SHEET_NESTING), orientation/rotate, bleed/gap, minimum billing, remnants-политика (gaps с ПРИЧИНОЙ в margin.py).
- `[CODE]` API: `POST /api/consumption/calculate`; привязка к заказам: `consumption_json` в order_items + `/orders/{id}/materials/reserve|release|consume` → stock_movements.
- `[TEST]` test_consumption*: nesting, manual width override (шире/уже), does_not_fit_either_way, unknown_material, order-integration (item gets consumption), price-from-calculator.
- `[FACT]` **Реально используется**: расчёт вызывается при создании позиций-калькуляторов (consumption_json пишется в order_items), резерв→автосписание ведёт склад. Интеграция подтверждена кодом и тестами.

## 13. Production

- `[FACT]` `operations`: 13 строк с code OP-xx, steps_json, **checklist_json** (чек-листы приёмки на каждой операции), equipment, minutes, role, trigger.
- `[CODE]` Цепочка: заказ → `production/generate` → production_tasks (sequence по операциям) → start/complete/block; QC-гард: block/complete с checklist_result; чек-листы OP-01…22 — в store.py seed (13 в БД; каталог §2 описывает 22 — часть операций ещё не сидирована `[INFERENCE]`).
- `[FACT]` production_tasks пуст — конвейер готов, но вживую не гонялся.
- `[CODE]` Shop-floor UI: production.html/production.js (экран «Производство»).

## 14. Documents

- `[FACT]` Генератора договоров/DOCX/PDF НЕТ: ни библиотек (python-docx/reportlab/fpdf/weasyprint отсутствуют в venv), ни кода. Единственный экспорт — `GET /orders/{id}/export.txt` (текстовое производственное задание) и CSV прайса.
- `[DOC]` ТЗ на договоры существует: `промт_печатник_6_договоры.md` — **DOC_ONLY**, не реализовано.

## 15. Free Text / Assistant

- `[CODE]` Детерминированный парсер v2: `printcalc_web/parser.py` (335 строк, словари+regex, БЕЗ LLM). Возможности: словарные алиасы+синонимы каталога (price_list_items.synonyms), извлечение размеров («20 на 30», «20×30», «0,5» — частично баг, см. ниже), слова-тиражи («6 штук», «2 штуки»), мультизаказ-сегменты (segment_id), поле sizes, needs_operator-эскалация.
- `[CODE]` **Smart Order (S0–S6, завершён)**: нормализатор OrderDraft (rules/normalize) → движок правил RuleVerdict (rules/engine) на YAML-паках (rules/packs: sticker 5, banner 4, backlit 3 = 12 правил) → API (/api/order/analyze, /api/order/bridge) → UI-подсказки → мост в калькулятор. Правила: контурная резка→плоттерная (OP-22), поштучно→плоттерная поштучно, люверсы+шаг, монтаж (только ПРЕДЛОЖИТЬ, auto=True запрещён ValueError'ом).
- `[CODE]` Контекст-наследование сегментов мультизаказа — есть (segment_id в order_items).
- `[CODE]` Question engine: `require`/`suggest` в паках + suggestion_decisions (учёт решений оператора). Шаблоны ответов R1/R2/R3 (reply_templates.py). AI fallback: НЕТ (сознательно).
- `[FACT]` Проба 7 запросов §15 (тест на временной БД, seed каталога):

| Запрос | Результат парсера | Разрыв |
|---|---|---|
| Наклейка 50×30, 149 шт, резка по контуру | наклейка ✅, размер ✅, 149 шт ✅; «резка по контуру» → matched **ЧПУ** (не то) + unknown «по/контуру» | факт `cutting_mode=contour` извлекает НЕ парсер, а нормализатор S1 → RuleVerdict предложит OP-22. Цепочка существует, но fact-extraction «резка по контуру» в parsed_json отсутствует — разрыв слоя |
| Баннер 3×6 + люверсы через 30 | баннер ✅ + люверс ✅ (оба price), размер ✅; «через 30» → unknown | шаг люверсов не извлекается парсером; правило пакета banner знает шаг — но факт в parsed не попадает |
| Бэклит 80×60, 1440 dpi, контур | **бэклит → unknown** (нет позиции каталога!), matched только ЧПУ от «резки» | нет позиции «Бэклит» в price_list; dpi не извлекается. Пак backlit.yaml есть — но парсер не может выбрать продукт |
| Наклейка плоттерная, монтажная, 40 шт, поштучно | наклейка ✅, 40 шт ✅, размер ✅; «плоттерная/монтажной» unknown | finishing-факты — зона нормализатора S1; в parsed_json их нет |
| Табличка ПВХ 4 мм 80×35 | табличка ✅, размер ✅; «пвх», «мм» unknown; «4» потерян | толщина не извлекается — у tablichki-калькулятора есть параметры, но парсер их не заполняет |
| Фото на паспорт 6 штук | matched «Фото на документы (4 шт)» | **семантический конфликт**: позиция = пакет 4 шт, запрос = 6 фото; нужна политика пересчёта (6 фото = 1.5 пакета? 2 пакета? отдельная позиция «за 1 фото») |
| Мультизапрос (фото+табличка 0,5×0,5+баннер 2×2 и 3×12) | 3 продукта сегментированы ✅ | **баг**: «0,5 на 0,5» → sizes=`5 на 0` (десятичная запятая ломает токенизацию размера) |

- `[INFERENCE]` Итог: сущности (OrderDraft, RuleVerdict, паки, facts-схема) **способны представить** все 7 запросов; разрывы — в extraction-слое (finishing/dpi/толщина/шаг не извлекаются из текста), отсутствии позиции «Бэклит», семантике фото-пакетов и баге десятичных размеров.

## 16. Production Rules

- `[CODE]` 12 правил в 3 YAML-паках (`rules/packs/`): резка по контуру→плоттерная (OP-22, «новый код, OP-15 зарезервирован»), поштучно→режим резки, контур→требование макета с контуром (layout_with_cut_contour), люверсы→шаг-подтверждение, монтаж→upsell-предложение, улица→материал, витрина (vitrine), бэклит→подсветка. Каждый suggest несёт `reason` с источником. Валидатор схемы — closed vocabulary, drift → `PackValidationError` `[TEST]` (негативная проба OP-99 → ValueError).
- `[FACT]` Правила существуют в коде и покрыты тестами (rules-сьюты 12/12 hub_v2 + rules_normalize).

## 17. Tests

- `[TEST]` Прогон из **распакованного архива** (не рабочей копии): **481 passed**, mypy clean (22 файла) — воспроизводимо: `pip install -e 'printcalc[web,test,rules]'` + pytest.
- `[FACT]` Сьюты: 8 golden-калькуляторов, consumption (8+), units (33), hub_v2 (12), rules_normalize, inbox, api_estimates, p0_services, parser…
- `[FACT]` CI-системы НЕТ (GitHub Actions не сконфигурирован `[UNKNOWN]` в remote — workflows не обнаружены); тесты гоняются вручную/агентом; cron nightly-audit относится к другому проекту.
- `[CODE]` Тесты не трогают прод-БД (фикстуры создают временные); запуск безопасен.

## 18. Documentation vs Code

| Область | Документация говорит | Код показывает | Статус |
|---|---|---|---|
| Калькуляторы 8/8 | «матрица закрыта» | 8 в реестре, 8 golden | **MATCH** |
| Consumption Engine | «подключён к Orders» | consumption_json + reserve/consume + тесты | **MATCH** |
| Smart Order S0–S6 | «поток A закрыт» | packs+engine+bridge+UI | **MATCH** |
| Units/размерный ввод | «размер ≠ тираж» | parser sizes + unit в order_items | **MATCH** |
| Hub v2 (Email+ответы) | «закрыт 09-21» | mail_poller+templates+API+UI | **MATCH** (канал выключен до кредов) |
| Договоры | промт_6_договоры | генератора нет | **DOC_ONLY** |
| Чек-листы OP-01…22 | «22 операции» | 13 в БД | **PARTIAL** |
| Payment Hub | «этап 7» | отсутствует | **DOC_ONLY** |
| Приём файлов | «Блок E» | отсутствует | **DOC_ONLY** |
| TG-бот | «код готов, ждёт токен» | telegram.py + no-op без кредов | **MATCH** (не активирован) |
| Audit report §9 install | `pip install -e '.[web,test,rules]'` + pytest | pytest не входит в extras | **OUTDATED** (находка MEDIUM) |
| Данные | «система в проде» | 0 клиентов/заказов | **PARTIAL** (деплой есть, ввода нет) |

## 19. Recent Changes

- `[FACT]` Последняя кодовая волна: **Hub v2** (Email-канал + шаблоны R1/R2/R3, 09-21→09-23, `5ce4122`/`3583b55`) и **PHASE_UNITS** (единицы + размерный ввод, `c9e234d`); затем доки аудита (`b14846e`). Параллельно в монорепо — mailbox-агент и tunnel (не «Печатник»).
- `[FACT]` Незавершённой работы в скоупе нет (чистый статус).

## 20. Current Roadmap Status

- `[DOC]` РОАДМАП_v7: поток A (Smart Order) S0–S6 — **закрыт**; поток B (Reports Hub) H1–H6 — **закрыт** (сервис :8310 активен).
- `[DOC]` Следующие этапы по PROJECT_STATUS_REPORT §4: Payment Hub (TestAdapter→TBank), приём файлов (files[]+DPI-валидатор), активация TG/IMAP (ждут креды владельца), ценовые решения в Excel (визитки 2 ₽, мин. заказ, шаг люверсов, монтаж).

## 21. Architecture Risks

1. `[FACT]` **Нет аутентификации** на :8300 (78 эндпоинтов открыты); компенсация — внутренний контур/VPN/tunnel. Для любого внешнего доступа — блокер.
2. `[FACT]` **Нет бэкапов БД** (ни cron, ни скрипта) при том, что БД — единственное хранилище.
3. `[FACT]` **Нет CI** — тесты гоняются вручную; регрессии ловит только дисциплина агента.
4. `[FACT]` SQLite — однозаходная БД (WAL смягчает чтение, но запись одна); при росте нагрузки — переезд на PostgreSQL.
5. `[TEST]` Баг парсера: десятичные размеры «0,5 на 0,5» → `5 на 0` (потеря запятой) — влияет на метры.
6. `[TEST]` Семантическая ловушка «Фото на паспорт 6 штук» vs позиция-«пакет 4 шт» — нужна политика пересчёта.
7. `[FACT]` `pip install -e 'printcalc[...]'` не ставит pytest/mypy (extras test неполон) — воспроизведение верификации ломается.

## 22. Recommended Next Step

`[INFERENCE]` Наименьший риск × наибольшая ценность: **(1) закрыть гигиену** — cron-бэкап SQLite (sqlite3 .backup + ротация, ~10 строк) и дополнить extras `test = ["pytest", "httpx"]`; **(2) парсер** — фикс десятичных размеров + extraction finishing-фактов (резка по контуру/поштучно/монтажная) в parsed_json, чтобы Smart Order-цепочка заработала на 7/7 запросов §15; **(3) у владельца** — креды TG/IMAP и решения по ценам (не код).
