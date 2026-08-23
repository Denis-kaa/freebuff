# SPEC.md — Public Request Parser Bot

Полная спецификация задачи находится в canonical-файле корня:

- [`public-request-parser-spec.md`***REMOVED***(../../public-request-parser-spec.md)

Этот файл является project-local entry point и намеренно не дублирует canonical specification. При расхождении прав имеет файл корня; изменения архитектурных решений фиксируются в [`decisions/`***REMOVED***(decisions/).

## Зафиксированный scope каркаса

- RSS/Atom — первый operational adapter.
- Telegram web-preview — технический adapter/fixture contract, live-доступ выключен до policy approval.
- Single-tenant runtime сейчас, multi-tenant-ready доменные контракты.
- Read-only, без outbound к авторам и без базы авторов.
- Ссылка и технические метаданные + полный текст с настраиваемым TTL.
