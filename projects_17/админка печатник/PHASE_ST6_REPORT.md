# PHASE_ST6_REPORT.md — Этап 6: Communication Hub (роадмап v6)

> Дата: 2026-09-09 · Статус: COMPLETE · Коммит: см. git log (`stage-6: telegram inbox → inquiry → estimate`)
> Основа: РОАДМАП_v6 Этап 6, промт_4 §44 (Unified Inbox), §45 (client matching),
> §47 (Adapter Pattern), §55 (идемпотентность external_message_id), §60 (MVP-цикл).

## 1. Что сделано

- **Схема (аддитивно)**: `inbox_messages` (UNIQUE(channel, external_id) —
  идемпотентность §55; parsed_json — результат детерминированного парсера;
  сообщение — ФАКТ: текст не редактируется никогда) + `inquiries`
  (client_id, client_match none/auto/manual, summary, estimate_id, статусы
  new → estimated → archived).
- **Store**: `record_incoming_message` (дубликат возвращает существующую строку,
  created=False), `create_inquiry_from_message` (авто-matching, идемпотентно),
  `update_inquiry` (ручная привязка клиента + суть), `attach_estimate_to_inquiry`
  (new → estimated, идемпотентно), `archive_inbox_message`, списки с фильтрами.
- **Client matching (§45)**: авто-привязка по telegram-контакту с нормализацией
  (@убрать, lowercase); дубли клиентов не создаются — клиент из реестра Этапа 1.
- **TelegramAdapter (§47)**: `printcalc_web/telegram.py` — Bot API через httpx,
  long polling в daemon-потоке (стартует из `create_app`), эхо-подтверждение
  клиенту при первом сообщении. Конфиг только env: `PRINTCALC_TG_TOKEN`,
  `PRINTCALC_TG_ENABLED` (0/1), дефолт — поллер выключен (нет токена = no-op),
  приложение работает без Telegram.
- **API**: GET/POST `/api/inbox`, POST `/api/inbox/{id}/inquiry`,
  POST `/api/inbox/{id}/archive`, GET `/api/inquiries`, GET/PATCH
  `/api/inquiries/{id}` (PATCH-семантика: client_id передан явно ↔ не передан),
  POST `/api/inquiries/{id}/estimate`.
- **UI «Входящие»**: таблица сообщений (распознанные позиции + unknown),
  таблица заявок (клиент + тип matching + смета), диалог заявки
  (привязка клиента, суть, «Создать смету» → редирект в Сметы).
  Навигация: раздел «Входящие» в сайдбаре.

## 2. MVP-цикл §60 (проверен тестом `test_stage6_http_cycle`)

сообщение Telegram → inbox (парсер распознал «Баннер 440г × 2») →
заявка (авто/ручной matching) → смета привязана (new → estimated) →
далее штатный цикл Этапа 2: accept → snapshot → заказ (уже готов).

## 3. Что сознательно НЕ делалось (скоуп-дисциплина ANTI-5)

- QUESTION_FLOW-опросник в чате (§8) — следующий шаг Этапа 6, UI заявки уже
  готов его принять (summary + parsed).
- EmailAdapter (§43), MAX/VK (§41–42) — позже, контракт `record_incoming_message`
  к этому готов (channel='email' уже в закрытом словаре).
- Ответы клиенту из системы (§44 ответы) — сейчас только детерминированное эхо.

## 4. Проверки

- **195 passed** (+10: приём/идемпотентность/matching/lifecycle/HTTP-цикл/
  Telegram-parsing), mypy clean.
- Golden-паритет Riso/Tablichki/Wide не тронут (движок не менялся).
- Полные прогоны: `pytest tests/ -q` → 195 passed; mypy по 5 файлам — Success.

## 5. Деплой

- Сервис на whimco запускается с `PYTHONPATH=src` — после pull нужен рестарт
  юнита (LESSON из Этапа 5b).
- Telegram включается на сервере env-переменными (см. §1); без токена функционал
  не активен, но inbox/manual-канал и UI полностью работают.
