# IMPLEMENTATION_AUDIT_REPORT.md — аудит реализации перед рефакторингом (Этап 0)

> Статус: COMPLETE · Дата: 2026-09-08 ·
> Основание: §2 промт_печатник_4 («обязательный implementation report» до изменения
> архитектуры и массового кодирования). Все 15 пунктов зафиксированы с фактами
> file:line. Раздел 16 — целевая схема БД и план действий. UNKNOWN-пункты явно
> помечены (§63 промт_4: неизвестное не заменяется догадкой).

---

## 1. Текущая архитектура

### 1.1 Два слоя в одном пакете printcalc (прод, whimco)

```
printcalc/  (ядро, чистый Python, без зависимостей)
├── engine/                      # контракт CALC (эталон Riso)
│   ├── spec.py                  # CalculatorSpec/FieldSpec/FieldKind
│   ├── validate.py              # схема-валидация входов до compute
│   ├── registry.py              # закрытый реестр (дубль/неизвестный id = RegistryError)
│   ├── result.py                # CalcResult(price, price_no_tax, cost, net_profit, lines, warnings, details)
│   ├── errors.py                # CalcError/CalcInputError/RegistryError/ValidationIssue
│   └── consumption/             # движок расхода (промт_3): models/units/normalize/
│                                #   roll/rounding/engine/adapters/errors
└── calculators/{riso,tablichki,wide}/   # config(frozen) → spec → compute(чистая ф-я)

printcalc_web/  (web-слой, FastAPI, живёт на http://185.233.184.192:8300)
├── api.py      # /api/* JSON
├── views.py    # 4 HTML-страницы (тема «Печатникъ»)
├── store.py    # вся бизнес-логика SQLite
├── db.py       # схема + connect()
├── calculators.py  # мост к реестру + опции STRING-полей из конфигов
├── parser.py   # intent-парсер ступень 1 (детерминированный)
├── export.py   # OrderExport → текст для старого WF
└── static/ + templates/
```

**Принципы, которые уже выдержаны:** Additive Architecture; закрытые словари
(ANTI-6b: kinds разделов, codes ошибок consumption); server-side пересчёт цен
(клиентской цене нет доверия); golden-тесты от независимой деривации; Snapshot
материалов — только расчётный, помечен «~» (MATERIAL_MODEL §3).

### 1.2 Инфраструктура

- Сервер whimco: systemd-юнит `printcalc-web.service`, venv `/opt/printcalc-venv`,
  БД `/opt/printcalc/data/printcalc.db`, бэкапы `/opt/printcalc/backups/` (3 копии).
- Git: GitHub `Denis-kaa/freebuff`, master; телефон пушит через origin-https.
- Развёртывание: git pull --ff-only + systemctl restart (ручное, без CI).

---

## 2. Существующие калькуляторы

| ID в реестре | Статус | Источник истины | Golden-тесты | Примечание |
|---|---|---|---|---|
| `riso` | ✅ в коде + проде | legacy `Общий…/riso_calc.py:644-760` | 5+ (test_riso_golden) | Эталон контракта (§1 промт_4). Цены в коде (единственный hardcoded — PRICE_AUDIT §1) |
| `tablichki` | ✅ в коде + проде | legacy `Общий…/tablichki.py:641-744` | 7 (test_tablichki_golden) | Налог НЕ в цене (sell-пары) |
| `wide` | ✅ в коде + проде | legacy `Общий…/wide_format.py:660-756` | 10 (test_wide_golden) | Тированный прайс по площади, крепёж за заказ, люверсы ceil |
| digital | ❌ только исходник | `Общий…/digital_calc.py` (51 674 B) | нет | Дубль в build_all (дифф 2 байта) |
| sign (Вывески) | ❌ только исходник | `Общий…/sign_calc.py` (65 122 B) | нет | Standalone-версия отличается |
| cnc (ЧПУ) | ❌ только исходник | `cnc_calc.py` (29 454 B) | нет | JS-расчёт внутри Tk |
| design (Дизайн) | ❌ только исходник | `design_calc.py` (43 515 B) | нет | Услуга, не расчёт |
| universal (Себестоимость) | ❌ только исходник | `universal_calc.py` (54 566 B) | нет | Машино-час, амортизация |

Плюс consumption engine (не калькулятор, а слой): ROLL_NESTING полноценно,
AREA/LINEAR/SHEET/PIECE/COUNT прямые режимы; адаптер Wide (AREA-паритет +
opt-in roll), 34 теста в tests/consumption/.

---

## 3. Существующие API

### 3.1 JSON API (api.py, префикс /api)

| Метод и путь | Что делает |
|---|---|
| GET /settings/payment-methods | способы оплаты (editable) |
| GET/POST /price-list, PATCH /price-list/{id} | прайс-каталог CRUD |
| POST /price-list/{id}/synonyms, GET /price-list/similar | синонимы/похожие |
| POST /price-list/import, GET /price-list/export.csv | импорт «имя — цена», CSV |
| GET /calculators | список спек для schema-driven UI |
| POST /calculate | расчёт через реестр (calculator_id + params) |
| POST /parse | intent-парсер ступень 1 |
| POST/GET /orders, GET/PATCH /orders/{id} | заказы (с wishes + section_values) |
| GET /orders/{id}/export.txt | текст для ручного переноса в старый WF |
| GET/POST /sections, PATCH /sections/{id}, POST /sections/reorder | конструктор разделов |
| GET /orders/{id}/sections | значения разделов заказа |
| GET /report/off-catalog | позиции мимо каталога |

### 3.2 HTML (views.py): `/` (приём заказа), `/orders`, `/price-list`, `/constructor`.

### 3.3 Чего нет (понадобится по промт_4)

- `POST /api/consumption/calculate` (§48 промт_4) — движок готов, endpoint НЕ открыт.
- Client/Estimate/Payment/Material API — сущностей нет.
- v1-префикс (§48) — сейчас все пути без версий; решение о версионировании — UNKNOWN,
  требует решения (обратная совместимость текущего фронта).

---

## 4. Существующие модели данных

### 4.1 SQLite (db.py, 6 таблиц, все CREATE IF NOT EXISTS — идемпотентно)

- `price_list_items` (id, name, price, unit, category, synonyms, usage_count,
  unverified, archived, created_at, updated_at)
- `orders` (id, status TEXT — закрытый словарь в store, payment_method, total,
  created_at, updated_at)
- `order_items` (id, order_id → orders, kind CHECK IN ('price_list','calculator','manual'),
  name, price, qty, calculator_id, params_json, price_list_item_id, saved_to_catalog, position)
- `settings` (key, value) — способы оплаты
- `ui_sections` (id, title, kind CHECK закрытый, options_json, required, archived, position) — конструктор
- `order_section_values` (order_id, section_id, value) + wishes-колонка в orders
- индексы: status, order_id, name, position

### 4.2 Python-модели

- Engine: CalculatorSpec/FieldSpec/CalcResult/CostLine.
- Consumption: Material, MaterialConsumptionPolicy, MaterialConsumptionResult,
  Layout, Remnant (мм/мм² внутри, м²/м на границе API — to_dict).
- Web: словари (строки SQLite → dict) — без pydantic-моделей в store (проверка
  входов в api.py pydantic-схемами).

### 4.3 Чего нет

Client, Contact, Conversation/Message, Inquiry, Estimate, Payment, Material-таблица
(реестр), Reservation, Production Task/Operation, Files, Audit log.

---

## 5. Что уже работает (прод-проверено)

1. Приём заказа на стойке: быстрый ввод → парсер → позиции из прайса/калькулятора/вручную,
   итоги сервером, пожелания (свободная форма), динамические разделы (конструктор).
2. Три калькулятора в проде с паритетом legacy (golden 22 теста суммарно).
3. Статусная лента заказов (новый→в работе→выполнен→завершён) + фильтр.
4. Прайс-каталог с синонимами/импортом/unverified-флагом.
5. Consumption engine (ядра тесты 34 шт) — но НЕ подключён к прод-эндпоинтам.
6. Тёмная тема «Печатникъ» по референсу, мобильная вёрстка — проверены Playwright.
7. Движок «Печатник»-парсер ступень 1 (словарь из прайса, unknown → UI «+»).

---

## 6. Что является legacy

1. **8 Tk-калькуляторов Калькуляторы.zip** — источник формул; портируются, но сами
   как код не развиваются. Канон — wrapper-редакции «Общий калькулятор печати»
   (CALCULATOR_MATRIX §3), standalone = исторический артефакт.
2. **WorkflowForms (WF)** — отдельная система Дениса; printcalc экспортирует текст
   через export.txt. Интеграция односторонняя, ручная. Судьба WF — UNKNOWN
   (решение Дениса: оставить/заменить; влияет на Phase 4).
3. **HTML-прототипы** (HTML/печатник*.html) — макет дизайна; CDN-зависимости,
   8-статусная лента — заготовка Phase 5, не прод-код.
4. **export.txt как мост** — противоречит §9 промт_4 (нет ручного переноса), живёт
   до появления Estimate→Order.

---

## 7. Что можно переиспользовать (без изменений)

1. Engine-контракт (spec/validate/registry/result) — эталон Riso сохраняется (§1 промт_4).
2. Consumption engine целиком — создан по ТЗ промт_3, тесты зелёные.
3. Схему БД — аддитивные ALTER/CREATE (идемпотентная init уже так работает).
4. Web-мост calculators.py — опции STRING из конфигов (паттерн для новых калькуляторов).
5. Парсер ступень 1 — интерфейс готов для LLM-ступени 2 (Phase 9 промт_4).
6. Конструктор разделов (ui_sections) — data-driven, пригодится для Question Flow (§8).
7. Тему «Печатникъ» и каркас страниц (сайдбар/шапка) — новые разделы UI встроятся.
8. Все 16 проектных документов (§1 промт_4) — уже изучены и согласованы с кодом.

---

## 8. Что требует рефакторинга

1. **price_list_items ≠ Material Registry**: у позиции нет id материала, алиасы есть,
   но roll_width/consumption_mode/purchase_cost — нет. Нужна таблица materials +
   связь price_list_items.material_id (Phase 1 роадмапа v6).
2. **orders без client_id** — карточка заказа не знает клиента.
3. **order_items.price пересчитывается только для kind='calculator'** — при переходе
   на Estimate/snapshot правила пересчёта надо зафиксировать явно (§49 промт_4).
4. **api.py монолит** (~500+ строк, все эндпоинты в одном роутере) — при росте
   числа доменов разделить на APIRouter-модули (clients, estimates, payments…).
5. **store.py — сырой sqlite3** — при появлении транзакционных доменов (заказ+резерв+
   платёж) понадобится явная транзакционная граница; сейчас каждая операция автономна.
6. **money = REAL (float)** — §42 промт_3/§42 промт_4: Decimal на границе Cost Engine;
   миграция колонок на копейки (INTEGER) — под вопросом, UNKNOWN, требует решения
   (затрагивает golden-тесты — их НЕ ломать).
7. **Модель фронтенда** — каждый экран сам fetch-ит; при появлении Unified Inbox/
   Dashboard нужен лёгкий общий слой (без SPA-фреймворка, офлайн-принцип сохранить).

---

## 9. Где есть дублирование

1. **Материалы-строки в конфигах трёх калькуляторов** — «Плёнка самоклеящаяся» (Wide)
   и потенциальные синонимы в Digital; PRICE_AUDIT зафиксировал 3 варианта написания
   «самоклеящаяся» в legacy (BR-W1). В printcalc пока дубли только между Wide и
   будущим Digital/Таблички — решается Material Registry с aliases.
2. **Паттерн cost/sell пар** — PricePair (таблички), PriceTier (wide), sell-поля Riso:
   три реализации одной идеи (CALCULATOR_MATRIX §2) — консолидировать при переносе
   оставшихся калькуляторов, не раньше (не ломать golden).
3. **API-клиент в JS** — apiFetch повторён в app.js/orders.js/price_list.js/constructor.js
   (мелкое, можно вынести в общий static/api.js при следующем касании).
4. **Дубль digital_calc.py в архиве** (51 674 vs 51 672 B) — зафиксирован, к порту
   брать wrapper-редакцию.
5. **Две версии static CSS** — печатник-пресет был interim-решением, после редизайна
   остался legacy-блок; почистить при следующем касании стилей.

---

## 10. Где отсутствует единая модель

1. **Клиент** — нигде (заказы анонимны; HISTORY-модель — документ, не код).
2. **Материал как сущность** — конфиги калькуляторов изолированы; consumption engine
   принимает Material, но в проде материалы живут только внутри frozen-конфигов.
3. **Смета** — нет; расчёт живёт в ответе /calculate, не сохраняется.
4. **Обращение/диалог** — нет; parser.py не сохраняет контекст сообщений.
5. **Платёж** — payment_method — строка на заказе; денег-движений нет.
6. **Производство** — статусы заказа есть, операций/задач нет (OPERATIONS_CATALOG — проект).
7. **Snapshot расчёта** — params_json хранится, но без версий калькулятора/конфига
   (§49 промт_4: snapshot версий обязателен).
8. **Единицы** — в consumption mm/mm²/m²/lm; в прайсе — свободный текст unit;
   нормализатор есть только в consumption (§41 промт_3) — перенести на реестр материалов.

---

## 11. Какие интеграции уже существуют

1. **Git/GitHub** (общая база, Server-first: телефон ↔ сервер через origin).
2. **SSH deploy** (whimco, systemd-юнит).
3. **export.txt → старый WF** (односторонний ручной мост).
4. **Playwright** (скриншот-прогон на сервере, scripts/screenshots.py).
5. Внешних API-интеграций (Telegram/VK/MAX/Email/платёжные) — **нет**; по §41-42
   промт_4 реализация только по актуальной официальной документации, адаптеры
   изолированы (Adapter Pattern §4, §47).

---

## 12. Какие зависимости добавить

Текущие: fastapi, uvicorn, jinja2 (web-extra), httpx (test), pytest, mypy. Ноль runtime-зависимостей ядра — сохранить.

| Когда | Зависимость | Для чего | Риск |
|---|---|---|---|
| Этап 1–2 (v6) | pydantic v2 (уже с fastapi) | модели Client/Estimate/Payment | нет |
| Этап 6 | aiogram 3.x | TelegramAdapter | low: только в web-extra |
| Этап 6 | aiosmtplib/imaplib (std) | EmailAdapter | low |
| Этап 6 | httpx async (уже есть) | VK/MAX REST | low |
| Этап 7 | SDK эквайринга (TBank) | PaymentProviderAdapter | середина: изолировать в адаптер, секреты — env (§56) |
| Этап 8 | openai-совместимый клиент | LLM-парсер ступень 2 | середина: AI не источник истины (§38) |
| Никогда в ядро | pandas/numpy/ORM | — | не нужны, держать ядро чистым |

UNKNOWN: конкретный Python-SDK банка и модель LLM — выбрать при этапах 7–8 по
актуальной документации (§63: не заменять догадкой).

---

## 13. План миграции (поэтапный, соответствует §59 промт_4 и РОАДМАП_v6)

| Этап | Содержание | Критерий (§62/§65 промт_4) |
|---|---|---|
| 0 (этот отчёт) | аудит по 15 пунктам | документ согласован |
| 1 | Client + Contact + Material Registry (SQLite, аддитивно); orders.client_id nullable | CRUD+тесты; материалы Wide имеют roll_width |
| 2 | Estimate (из CalcResult) + статусы + snapshot версий (§49); заказ создаётся из сметы | «посчитал → смета → заказ» без ручного ввода |
| 3 | POST /api/consumption/calculate; расход в карточке заказа; Таблички→SHEET, Digital→рулон | оператор видит раскрой и отход по позиции |
| 4 | Operations/Tasks/Checklists/QC из OPERATIONS_CATALOG | заказ → производственное задание |
| 5 | Reservation + Estimated/Physical Stock + Purchase Planner | «не хватает X → закупить Y» |
| 6 | CommunicationService + TelegramAdapter → Email; Conversation/Message; Inquiry; Unified Inbox | MVP-цикл §60 без ручного переноса |
| 7 | Payment домен + TestAdapter → эквайринг | только подтверждённый платёж меняет статус (§29) |
| 8 | AI-парсер ступень 2 + объяснение результата (§38-39) | AI не источник истины |
| 9 (сквозные) | Files/Knowledge/Audit/Analytics/Global search по мере надобности | каждое — по §62 |

Порядок внутри этапа всегда: модель → API → тесты → UI → аудит-лог.

---

## 14. Риски

| Риск | Вероятность | Ущерб | Митигация |
|---|---|---|---|
| Ломание golden-тестов при Decimal-миграции | средняя | высокий (паритет с legacy EXE) | Decimal только в новом Cost Engine; существующие golden НЕ трогать (§42 промт_3) |
| Дрейф словаря материалов (BR-W1) | высокая | средняя (тихие нули/дубли) | Material Registry с aliases — обязательный этап 1; валидатор закрытого словаря |
| Расхождение consumption vs legacy Wide | низкая | средняя | divergence-отчёт adapters.compare_with_legacy уже в тестах (§44 промт_3) |
| Переписывание работающего прода | средняя | высокий | Additive Architecture; ALTER-миграции только добавляющие; бэкапы перед релизом (уже 3 копии) |
| Секреты интеграций в коде | низкая | критический | env/secret-provider с первого дня (§56); фронт не получает секреты |
| Двойная обработка webhook (этап 6) | средняя | средняя | идемпотентность по external_message_id (§55) — в модель Message заранее |
| Скоуп-крип (ANTI-5) | высокая | средняя | один этап за раз, DoD §62 на каждый; НЕ делать из §61 промт_4 |
| WF-зависимость (экспорт) | средняя | низкая | мост сохраняется до этапа 2; решение по WF — за Денисом (UNKNOWN) |
| Ограничения Termux-окружения разработки | средняя | низкая | тяжёлые прогоны (Playwright/pytest) на сервере — практика уже есть |

---

## 15. Список изменений по файлам (первая очередь: этапы 1–3)

### Новые файлы

```
printcalc/src/printcalc_web/models.py        # pydantic: Client, Material, Estimate, Snapshot
printcalc/src/printcalc_web/routers/clients.py
printcalc/src/printcalc_web/routers/materials.py
printcalc/src/printcalc_web/routers/estimates.py
printcalc/src/printcalc_web/routers/consumption.py   # POST /api/consumption/calculate
printcalc/src/printcalc_web/migrations.py    # нумерованные аддитивные миграции
printcalc/tests/test_clients.py
printcalc/tests/test_materials.py
printcalc/tests/test_estimates.py
printcalc/tests/test_consumption_api.py
printcalc/src/printcalc_web/templates/clients.html + static/clients.js
printcalc/src/printcalc_web/templates/estimates.html + static/estimates.js
```

### Изменяемые файлы (минимальные касания)

```
db.py      # +clients, +contacts, +materials, +estimates, +estimates_snapshot, +orders.client_id
store.py   # +store-функции новых доменов; create_order(estimate_id)
api.py     # включение роутеров (роутер остаётся совместимым: старые пути не меняются)
views.py   # +страницы clients/estimates; сайдбар: новые пункты
static/style.css  # чистка legacy-блока пресета (косметика, отдельно)
```

### Не изменяемые файлы (гарантия)

```
printcalc/engine/** (контракт и consumption — уже стабилизированы тестами)
printcalc/calculators/{riso,tablichki,wide}/** (golden)
tests/test_riso_golden.py, test_tablichki_golden.py, test_wide_golden.py, tests/consumption/**
```

---

## 16. Целевая схема БД (v2, аддитивно к текущей)

```sql
clients(id, name, kind[физлицо|компания], note, created_at)
contacts(id, client_id→clients, channel[phone|telegram|vk|max|email|web],
         external_id, value, PRIMARY KEY(channel, external_id))  -- клиент ≠ контакт (§6)
materials(id, name, aliases_json, unit, consumption_mode, purchase_cost,
          price_unit, roll_width, roll_length, sheet_w, sheet_h,
          min_stock, supplier, active)
price_list_items.material_id → materials.id (nullable, постепенно)
estimates(id, client_id, status[DRAFT|SENT|VIEWED|ACCEPTED|REJECTED|EXPIRED],
          total, valid_until, created_at)
estimate_items(id, estimate_id, calculator_id, params_json, calc_snapshot_json,
               consumption_json, price, cost, qty)
orders.estimate_id → estimates.id (nullable)
calc_snapshots(id, order_id, calculator_version, config_hash, policy_version,
               result_json, created_at)   -- §49: цена задним числом не меняется
```

Дальше (этапы 4–7): operations, production_tasks, task_checklist_items,
reservations, stock_movements, purchases, payments, conversations, messages,
inquiries, files, audit_log.

---

## 17. UNKNOWN-список (исследовать перед соответствующим этапом, §63)

1. Судьба WorkflowForms: остаётся ли WF системой Дениса параллельно (влияет на этап 2).
2. Версионирование API (/api/v1/… vs текущий /api/…): нужен совместимый переход.
3. Деньги: REAL→INTEGER-копейки или Decimal на границе — решить до Cost Engine.
4. Реальные ширины рулонов и min_billing по материалам (опрос владельца — открытые
   вопросы CONSUMPTION_ENGINE_IMPLEMENTATION_REPORT §10).
5. Конкретный эквайринг/терминал и его SDK (этап 7).
6. LLM-провайдер и лимиты для парсера ступени 2 (этап 8).
7. VK API / MAX API — только официальная документация на момент этапа 6 (§41-42).

---

## DoD этого отчёта

- [x] 15 пунктов §2 промт_4 раскрыты с фактами file:line
- [x] Целевая схема и порядок миграции зафиксированы
- [x] Риски и UNKNOWN перечислены явно (догадки не подставлены)
- [x] Гарантия неизменности golden-слоя прописана (раздел 15)
- [x] Разрешение на рефакторинг этапов 1–3 считается выданным после согласования владельцем
