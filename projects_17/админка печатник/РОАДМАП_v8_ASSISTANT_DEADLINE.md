# РОАДМАП_v8 — Local Operator Assistant v2 + Deadline Engine

> **Статус:** ACTIVE · **Дата:** 2026-09-27 · **Источник:** prompts/2.md (ТЗ владельца, 2 части)
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

### B1. Аудит существующего (ТЗ §33)
- Order/OrderStatus, production_tasks, API orders, orders.html/js (фильтры/сортировки),
  settings, notification-механизмы (outbox/inbox), audit log — найти аналоги ДО создания.

### B2. БД (аддитивно)
- orders: + customer_deadline TEXT (ISO timestamp), + internal_deadline TEXT.
- deadline_notifications: order_id + deadline_type + threshold (уникальная комбинация,
  idempotency ТЗ §10); настройки порогов — существующая settings-таблица.

### B3. Urgency-статус (ТЗ §4–6)
- Вычисляемый DeadlineStatus: NORMAL/WARNING/URGENT/CRITICAL/VERY_CRITICAL/OVERDUE
  (пороги из настроек, не хардкод); remaining_time динамический (не в БД);
  финальные статусы (completed/delivered/cancelled) не тревожат.
- Отдельное измерение: не смешивать с OrderStatus/Production/Payment (ТЗ §11 ч.2).
- Валидация internal_deadline <= customer_deadline (ТЗ §20); timezone-aware (ТЗ §21).

### B4. API + UI
- PATCH orders deadline (audit-история изменений ТЗ §30); список: сортировки
  (дата/дедлайн/срочность/направление/ID), фильтры (все/активные/просроченные/сегодня/
  завтра/неделя/без дедлайна/направление/статус); карточка: блок ДЕДЛАЙН;
  компактный индикатор в списке (цвет + текст + remaining — accessibility ТЗ §5);
  dashboard-счётчики если есть widget system (ТЗ §24).

### B5. Напоминания
- Threshold-based, один раз на порог (idempotency), через существующий outbox/notification
  слой; при смене дедлайна — пересчёт пройденных порогов без спама (ТЗ §31).

### B6. Тесты + отчёт
- ТЗ §32: расчёт времени (8 кейсов), статусы (6), финальные (3), фильтрация, сортировка,
  уведомления (idempotency), timezone. DEADLINE_ENGINE_IMPLEMENTATION_REPORT.md
  + коммит/деплой/смоук.

---

## Правила дисциплины (обе части ТЗ)

1. **Никаких вторых систем**: parser/rules/questions/suggestions/calculator/catalog/
   materials/notifications/settings/audit — только расширение существующих.
2. **Никакого LLM** в том, что умеет детерминированный парсер; AI fallback — не в v1.
3. **Никаких выдуманных цен/фактов**: «Никогда не превращать предположение в факт».
4. **Правка тестов** — только с классификацией: баг-фикс / бизнес-правило / контракт.
5. Каждое окно работы: код → pytest → mypy → отчёт → коммит/деплой по каденции.
