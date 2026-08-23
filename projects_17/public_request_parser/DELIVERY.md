# DELIVERY — P7

> **Статус:** implemented locally, contract-only
> **Версия:** 0.1.0
> **Ограничение:** live Telegram transport отсутствует; доставка работает в
> dry-run и через принятый `MessageTransport` протокол без реального provider.

## Назначение

P7 доставляет объяснимые карточки (`Publication + MatchDecision`) владельцу
профиля через Telegram-HTML, не создавая outbound к авторам публикации.

## API

### `render_card(publication, decision, *, score_label=None) -> DeliveryCard`

HTML-карточка:

```text
<b>Need a &lt;python&gt; backend</b>
Looking for &amp; help
🔗 <a href="https://example.test/items/1">Открыть источник</a> · score 0.90
Категории: python, web
```

- **HTML escaping обязателен** (`html.escape` с `quote=False`); Markdown не используется;
- ссылка — только `canonical_url` источника;
- полей автора/email/phone **нет** (privacy-инвариант);
- `score_label` — display-only, бизнес-логики не несёт.

### `delivery_key_for(publication, decision, *, owner_scope) -> str`

Идемпотентный ключ: `{owner_scope***REMOVED***:{item_key***REMOVED***:p{profile_version***REMOVED***`.

### `MessageTransport` (Protocol)

```python
async def send(*, chat_id: str, text: str, disable_web_page_preview: bool = True) -> str
```

Возвращает provider message id. Реальный Telegram adapter живёт отдельно и не
входит в P7 (нет live-credentials и outbound-права).

### `TelegramDelivery`

```python
delivery = TelegramDelivery(
    transport=transport,      # MessageTransport | None
    storage=storage,          # SqliteStorage | None
    default_owner_scope="operator",
    dry_run=False,
    default_chat_id="",
)
attempt = await delivery.deliver(publication, decision, owner_scope="operator")
```

Поведение:

| Ситуация | Результат |
|---|---|
| `dry_run=True` или нет транспорта | `SKIPPED`, карточка рендерится, ничего не отправляется |
| transport вернул id | `SENT` + `provider_message_id` |
| transport бросил `DeliveryTransportError` | `FAILED` + `error_code` |
| повторная доставка того же ключа | возвращает сохранённый `SENT`, send не вызывается (идемпотентность) |
| `owner_scope` не совпадает с владельцем decision | `ContractValidationError` (owner-гейт) |
| `owner_scope` пуст | `ContractValidationError` |

### Retry-семантика

`SqliteStorage.save_delivery_attempt(..., replace_failed=True)`:
- новая попытка по ключу с существующим `SENT`/`SKIPPED` игнорируется (INSERT OR IGNORE);
- существующий `FAILED` заменяется новой попыткой (retry после сбоя провайдера);
- `get_delivery_attempt(key)` возвращает сохранённое состояние.

## Проверки

```bash
cd projects_17/public_request_parser
PYTHONPATH=. python -m pytest tests/test_delivery.py -q
python -m mypy app tests --strict
```

## Не закрыто P7

- живой Telegram Bot API adapter (отдельный policy/credentials gate);
- кнопки (source / viewed / relevant / irrelevant / archive) — P8 UX;
- очередь/backoff для массовой рассылки (P11);
- multi-tenant `owner_scope` поверх decision-владельца (P13).