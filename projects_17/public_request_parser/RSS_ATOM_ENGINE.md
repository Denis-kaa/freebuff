# RSS_ATOM_ENGINE — P4

> **Статус:** implemented locally, fixture-based
> **Версия:** 0.1.0
> **Ограничение:** parser не выполняет HTTP-запросы и не включает live polling.

## Назначение

P4 принимает уже загруженный RSS 2.x или Atom 1.0 XML-документ, извлекает
стабильные элементы `SourceItem`, преобразует их в доменные `Publication`,
устраняет дубли и поддерживает bounded checkpoint/resume для следующего
pipeline слоя.

Сетевой transport, conditional HTTP (`ETag`/`Last-Modified`), scheduler,
SQLite/WAL и Telegram delivery намеренно остаются в P6/P7 и не появляются
скрытой зависимостью в P4.

## API

### `RSSAtomParser`

```python
parser = RSSAtomParser("source-id", base_url="https://example.test/")
result = parser.parse(payload)
```

Поддерживаются:

- RSS 2.x: `channel/item`, `guid`, `link`, `title`, `description`, `pubDate`;
- Atom 1.0: namespace-aware `feed/entry`, `id`, `link`, `title`, `summary`,
  `content`, `published`, `updated`;
- absolute HTTP(S) canonical URL;
- RFC 2822 и ISO-8601 dates с приведением к UTC;
- category/term в технических metadata;
- controlled warnings для пропущенных URL/title и невалидных optional dates;
- `AdapterError` для повреждённого XML, неподдержанного root и отсутствующего
  обязательного RSS channel.

Неполный item не останавливает весь feed: item без URL или title пропускается
с `FeedWarning`.

### `normalize_source_item`

Преобразует `SourceItem` в `Publication`, принимает явный `fetched_at` для
детерминированных тестов и `max_text_chars` для ограничения временного полного
текста. Авторские поля не добавляются.

### `deduplicate_publications`

Сохраняет первый элемент по `source_id:item_id` и canonical URL. Поэтому
повторная загрузка одного feed не создаёт второй normalized record, а разные
источники могут использовать одинаковый локальный item ID.

### `FixtureFeedAdapter`

Реализует project-local `SourceAdapter` на bytes/string fixture:

- bounded `limit`;
- checkpoint resume после последнего подтверждённого item;
- локальный `health()` как проверка parseability;
- отсутствие сетевых вызовов;
- отказ, если передан policy со статусом `allowed`: fixture adapter не может
  незаметно стать live transport.

### `InMemoryCheckpointStore`

Hermetic async adapter для P4 tests. Он моделирует контракт `get/commit`;-
SQLite/WAL implementation и crash recovery относятся к P6/P11.

## Fixture evidence

- `fixtures/rss/sample_rss.xml` — synthetic RSS 2.0;
- `fixtures/atom/sample_atom.xml` — synthetic Atom 1.0;
- `tests/test_rss_atom.py` — 8 hermetic tests.

Fixtures не содержат реальные персональные данные и не являются разрешением
на агрегацию живого источника.

## Проверки

```bash
cd projects_17/public_request_parser
PYTHONPATH=. python -m pytest tests/test_rss_atom.py -q
python -m mypy app/rss_atom tests/test_rss_atom.py --strict
```

## Не закрыто P4

- G2 и production `allowed` source;
- HTTP fetching, rate-limit budget и conditional requests;
- SQLite checkpoint persistence;
- matching, TTL cleanup и Telegram delivery;
- Telegram web-preview live path.
