# ADR-007 — Delivery contract and idempotency (P7)

> **Статус:** Accepted
> **Дата:** 2026-08-23
> **Связано:** `DELIVERY.md`, `ROADMAP.md` P7, `DOMAIN_CONTRACTS.md` (Delivery port), `STORAGE.md`

## Контекст

P3 определил порт `Delivery.send(publication, decision, *, owner_scope)` и
`DeliveryAttempt`. P6 дал idempotent-хранилище `delivery_attempts` с FK на
публикацию. Для P7 нужно реализовать доставку карточек без live-credentials,
не нарушая идемпотентность и privacy.

## Решение

1. **Контракт-only слой `app/delivery/`**: `render_card()` (HTML-escape,
   никакого Markdown), `MessageTransport` (Protocol), `TelegramDelivery`
   (dry-run, idempotency, owner-гейт).
2. **Delидеальный key** `owner:item_key:p{version***REMOVED***` ⇒ повторная доставка
   того же ключа возвращает сохранённый `SENT` и не вызывает transport —
   дубль карточки невозможен на уровне приложения.
3. **Dry-run по умолчанию**: без транспорта или с `dry_run=True` попытка
   `SKIPPED`, карточка рендерится, network не происходит.
4. **Retry через storage**: `replace_failed=True` в `save_delivery_attempt`
   позволяет перезаписывать только `FAILED`-попытки (после сбоя провайдера),
   но не `SENT`/`SKIPPED`.
5. **Owner-гейт**: `owner_scope` обязан совпадать с владельцем decision;
   пустой scope запрещён. Автор публикации не является адресатом — outbound
   к авторам невозможен по контракту.
6. **Privacy в карточке**: нет полей автора; только title/summary/ссылка/
   категории/score.

## Альтернативы

- **Отправка через реальный python-telegram-bot сейчас** — требует token и
  live-режим, что противоречит P9/G2 (Telegram live остаётся policy-gated);
- **Простой try/except boolean** — теряет evidence результата
  (`provider_message_id`/`error_code`), которые требуют контракты P3;
- **FIFO-очередь + backoff** — полезно для массовой рассылки, но не нужно
  для contract-test P7; откладывается в P11.

## Последствия

- P8 (single-tenant MVP) может склеить receipt через dry-run + fixture transport;
- реализация Telegram Bot API adapter остаётся отдельным policy/credentials gate;
- `delivery_attempts` с FK требуют существующей публикации — storage сохраняет
  публикацию до доставки (инвариант проверен тестом);
- multi-tenant owner-гейт в P13 расширит проверку до row-level isolation.