# РОАДМАП_v8 — Local Operator Assistant v2 + Deadline Engine

> **Статус:** ACTIVE · **Дата:** 2026-09-27 · **Источник:** prompts/2.md (ТЗ владельца, 2 части)
> **Прогресс:** Поток A — ГОТОВ (коммит ecd10e5, 507 тестов, отчёт §39); поток B — ГОТОВ (коммит 7be6d09, 539 тестов) + B7 связь с помощником и B8 thread-фикс/живой смоук (2026-09-30, 556 тестов).
> **Принцип ТЗ:** Preserve existing contracts. Extend, don't rewrite. Чат = интерфейс,
> Smart Order = бизнес-логика. Никаких параллельных parser/rules/settings/notification систем.
> **Основа фактов:** PRINTNIK_SERVER_STATE.md (снимок 09-27) — проба 7 запросов уже выявила
> разрывы, совпадающие с §7–15 ТЗ.

---

## Два потока, порядок A → B

| Поток | Суть | Почему вторым Deadline |
|---|---|---|
| **A. Local Operator Assistant** | Пробелы парсера + чат-интерфейс над существующим Smart Order | ТЗ §40 Этап 3 требует исправить parser ДО UI; Assistant в §32 сам ссылается на «Deadline API, когда будет доступен» |
| **B. Deadline Engine** | Дедлайны клиента/производства + urgency + напоминания + сортировки/фильтры | Зависит от того, что Assistant уже подключён (§26 «Связь с помощником»); самостоятельная ценность |

---

## Поток A — Local Operator Assistant v2.0

### A0. Аудит существующего (ТЗ §40 Этап 1) — НЕ ПЕРЕПИСЫВАТЬ
- `parser.py` (335 строк), `rules/normalize.py` (OrderDraft), `rules/engine.py` (RuleVerdict),
  `orderbridge.py` (мост), `suggestion_decisions` (store), API: /api/parse, /api/order/analyze,
  /api/order/bridge; frontend: index.html + app.js (черновик).
- Фиксация: что уже умеет КАЖДЫЙ слой — чтобы менять только минимально необходимое место.

### A1. Gap-анализ 7 проблем (ТЗ §40 Этап 2)
| # | Проблема (ТЗ) | Статус по аудиту 09-27 |
|---|---|---|
| 1 | contour → plotter (не ЧПУ) | «резка по контуру» матчит ЧПУ + parsed_json не содержит cutting_mode |
| 2 | grommet step («через 30») | шаг в unknown; правило banner ждёт факт |
| 3 | backlit alias | «бэклит» → unknown (нет позиции каталога) |
| 4 | print_quality («1440 dpi») | dpi → unknown; 1440 может съесться тиражом |
| 5 | finishing normalization (плоттерная/монтажная/поштучно) | finishing-факты не извлекаются |
| 6 | quantity policy для фото («6 штук» vs пакет 4) | matched «(4 шт)» без вопроса о политике |
| 7 | decimal comma («0,5 на 0,5») | sizes = «5 на 0» (баг токенизации) |

### A2. Минимальные фиксы parser/normalize (ТЗ Этап 3)
- Десятичная запятая/точка в размерах; единое внутреннее представление мм.
- dpi → print_quality (не quantity); слова-тиражи не съедают dpi.
- «люверсы через 30 / 30 см / с шагом 30» → grommets=true + grommet_step=300mm.
- «резка по контуру» → cutting_mode=contour (факт), НЕ маршрут в ЧПУ.
- «плоттерная / с монтажной / поштучно» → technology/cutting_mode/mounting_film.
- «ПВХ 4 мм» → material/thickness (из существующего Material Registry).
- Наследование типа изделия на вторую размерную пару («баннер 2×2 и 3×12»);
  НЕ наследовать материал/количество/люверсы.

### A3. Каталог: «Бэклит» (ТЗ §9)
- Сид позиции + aliases в существующий price_list (источник цены — исследование 17/18,
  REGISTER-FIRST); без новых сущностей.

### A4. Qty-политика фото (ТЗ §14)
- package_quantity (из названия позиции) vs requested_quantity → вопрос оператору
  «6 фото при пакете 4 — считать индивидуально?». Никакой тихой конверсии.

### A5. Локальный чат (ТЗ §5/§33, Этап 4)
- Страница/панель «Помощник»: свободный текст → POST /api/order/analyze → карточки
  РАСПОЗНАНО / ПРЕДЛАГАЕТСЯ / НУЖНО УТОЧНИТЬ / МОЖНО ПРЕДЛОЖИТЬ → кнопки
  [Добавить в заказ] → существующий suggestion_decisions + bridge.
- Никаких новых API бизнес-логики; возможно расширение ответа analyze (ТЗ §35 —
  только если существующий контракт не покрывает).

### A6. Режимы ответа (ТЗ §18–26, Этап 5)
- 8 режимов (Быстрый/Рабочий/Подробный/Обучение/Только уточнения/Производство/Продажа/
  Проверка), default Рабочий. Презентационный слой поверх RuleVerdict — без логики.

### A7. Тесты + регрессия (ТЗ §37/§38)
- 7 фраз ТЗ: intent/items/dimensions/qty/material/thickness/dpi/operations/step/cutting/
  inheritance/questions/suggestions/не-ЧПУ/decimal/не-выдуманная-цена.
- Регрессия: 481 не ухудшается; изменения существующих тестов — с обоснованием (баг/правило/контракт).

### A8. Отчёт + деплой
- LOCAL_OPERATOR_ASSISTANT_IMPLEMENTATION_REPORT.md (12 пунктов ТЗ §39) +
  обновление PROJECT_STATUS_REPORT; коммит/деплой/живая проверка 7 фраз на проде.

**Критерий готовности A (ТЗ §41):** 7 фраз дают верные items/размеры/qty/факты,
подсказки приходят из существующих правил, подтверждение через suggestion_decisions,
bridge ведёт в калькулятор. 0,5×0,5 не ломается. Цены нет без калькулятора.

---

## Поток B — Deadline Engine + напоминания + управление заказами

### B1. Аудит существующего (ТЗ §33) — ВЫПОЛНЕН 2026-09-29

| Элемент ТЗ | Что есть в printcalc | Вердикт |
|---|---|---|
| Order model | таблица `orders`: id, status, payment_method, total, created_at, updated_at + миграции wishes/client_id/estimate_id | **deadline-полей НЕТ** — добавить аддитивно |
| OrderStatus | `ORDER_STATUSES = ("новый","в работе","выполнен","завершён")` (store.py:32) | «отменён» отсутствует → **решение владельца 09-29: добавить**; финальные = выполнен/завершён/отменён |
| ProductionStatus | `TASK_STATUSES = ("pending","in_progress","done","blocked")` (production_tasks) | отдельное измерение, Deadline Engine его НЕ меняет (ТЗ §25) |
| Deadline fields | нет ни в схеме, ни в миграциях | B2 |
| API orders | POST/GET/PATCH /api/orders, /orders/{id}/production | PATCH расширить, список — sort/filter параметрами |
| Frontend orders | orders.html: фильтр-сегменты по статусу; orders.js: loadOrders ?status= | сортировок и дедлайн-колонки нет → B4 |
| Notifications | outbox_messages (письма по заявкам) + emailer.dispatch; **вешать дедлайны на письма нельзя** — другой домен | **решение владельца 09-29: журнал + UI-лента**, без email в MVP |
| Settings | таблица settings (key/value), используется payment_methods | пороги дедлайна туда же — не новая система (ТЗ §29) |
| Audit log | постоянного audit-log нет; есть suggestion_decisions (домен подсказок) | создать `deadline_events` — он и журнал напоминаний, и история изменений (ТЗ §30-31) |
| Dashboard | analytics.html — своя страница, widget system отсутствует | счётчики добавить в шапку списка заказов (не новый фреймворк, ТЗ §24) |
| Timezone | `utc_now()` — datetime.now(timezone.utc).isoformat (store.py:54); наивных дат нет | хранить ISO UTC с офсетом; отдавать remaining вычисленным (ТЗ §21) |
| Assignee | модель ответственного сотрудника отсутствует | уведомление «в ленту всем операторам» (единый журнал), без адресации (ТЗ §27 мин.) |

### B2. БД (аддитивно)
- orders: + customer_deadline TEXT (ISO UTC с офсетом, NULL = не установлен),
  + internal_deadline TEXT.
- `deadline_events`: order_id + deadline_type + threshold UNIQUE — идемпотентность
  напоминаний (ТЗ §10) и журнал изменений (порог "changed"/"set"/"cleared", payload
  со старым/новым значением — ТЗ §30).
- «отменён» → ORDER_STATUSES (миграция не нужна — строковый статус; обновить
  валидацию create/update и STATUS_STYLE в orders.js).

### B3. DeadlineService (rules->deadline.py, детерминированный)
- Вычисляемый DeadlineStatus: NORMAL/WARNING/URGENT/CRITICAL/VERY_CRITICAL/OVERDUE
  (пороги из settings, не хардкод); remaining_time динамический (не в БД);
  финальные статусы (выполнен/завершён/отменён) не тревожат (ТЗ §8).
- Отдельное измерение: не смешивать с OrderStatus/Production/Payment (ТЗ §11 ч.2).
- Валидация internal_deadline <= customer_deadline (ТЗ §20); timezone-aware (ТЗ §21);
  «Без дедлайна» — None, не «просрочен» (ТЗ §18).

### B4. API + UI
- PUT /api/orders/{id}/deadline (set/clear, внутренняя валидация, запись в
  deadline_events — audit ТЗ §30); GET /api/orders: sort=(created\|deadline\|urgency\
  \|direction\|id), order=(asc\|desc), filter=(all\|active\|overdue\|today\|tomorrow\
  \|week\|no_deadline), direction-фильтр по calculator_id позиций (существующий
  справочник wide/digital/riso/sign/cnc/design — не второй, ТЗ §14);
  GET /api/deadline/summary — счётчики шапки.
- UI: колонка «Дедлайн» с ⚪/🟢/🟡/🟠/🔴/⛔ + текст remaining (не только цвет — §5);
  селекты сортировки/фильтра; блок ДЕДЛАЙН в диалоге заказа; лента событий в шапке
  (колокольчик + счётчик непрочитанных) — обновление раз в 60 c (§7, не каждую секунду).

### B5. Напоминания
- Threshold-based: пороги 3д/24ч/12ч/2ч/overdue из настроек; событие пишется ОДИН раз
  (UNIQUE constraint), повторный sweep не дублирует (ТЗ §10).
- Sweep = при GET /api/orders (лениво, детерминированно) — отдельный демон не нужен.
- При смене дедлайна: пересчёт пройденных порогов, старые события типа остаются
  в истории, новые пороги срабатывают заново без спама (ТЗ §31).

### B6. Тесты + отчёт
- ТЗ §32: расчёт времени (8 кейсов), статусы (6), финальные (3), фильтрация, сортировка,
  уведомления (idempotency), timezone. DEADLINE_ENGINE_IMPLEMENTATION_REPORT.md
  + коммит/деплой/смоук.

### B7. Связь с помощником (ТЗ §26 второй части) — ВЫПОЛНЕН 2026-09-30
- deadline.py: `DEADLINE_QUERY_INTENTS` — закрытый словарь интентов (ANTI-6b):
  просрочено/горит/сегодня/завтра/на этой неделе/без дедлайна/активные →
  существующие фильтры deadline_filter_matches; `match_deadline_query` (нормализация
  фразы: lowercase, ё→е, пунктуация) + `execute_deadline_query` — отчёт из СУЩЕСТВУЮЩЕГО
  вычисляемого слоя (urgency_for_order, тот же расчёт, что у списка /orders; «не создавать
  отдельный источник данных»).
- POST /api/deadline/query: отчёт по фразе или 404 «не дедлайн-вопрос».
- assistant.js: перехват дедлайн-фраз ДО /order/analyze; 404 → обычный поток;
  рендер отчёта (title, счётчики, строки с 🟢🟡🟠🔴⛔ + remaining).
- Сознательно НЕ распознаётся «до 18:00» (время суток вне закрытого словаря — честное
  отсутствие вместо ложного ответа; кандидат в следующий этап).
- Тесты: test_deadline_query.py (17) — интенты, отчёт, финальные, API-контракт.

### B8. Живая проверка /orders и thread-фикс — ВЫПОЛНЕН 2026-09-30
- Живой смоук выявил прод-баг: GET /orders?sort=urgency ~50-70% ошибок 500 под
  параллельной нагрузкой (sqlite3 ProgrammingError: sync-dependency и sync-endpoint
  FastAPI выполняет в разных потоках anyio-threadpool).
- Фикс: db.connect() → check_same_thread=False; api.get_conn() → fresh-conn-per-request
  с rollback в finally. Репро 120 параллельных GET → все 200.
- read_order(): вычисляемый urgency в детальном ответе (§22 — без него диалог показывал
  неверный статус; поймано UI-смоуком).
- scripts/deadline_ui_smoke.js (+ static-копия, ?deadline_smoke=1): живой UI-смоук —
  data-deadline-smoke="ok".

---

## Правила дисциплины (обе части ТЗ)

1. **Никаких вторых систем**: parser/rules/questions/suggestions/calculator/catalog/
   materials/notifications/settings/audit — только расширение существующих.
2. **Никакого LLM** в том, что умеет детерминированный парсер; AI fallback — не в v1.
3. **Никаких выдуманных цен/фактов**: «Никогда не превращать предположение в факт».
4. **Правка тестов** — только с классификацией: баг-фикс / бизнес-правило / контракт.
5. Каждое окно работы: код → pytest → mypy → отчёт → коммит/деплой по каденции.
