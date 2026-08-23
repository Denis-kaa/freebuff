# CHECKLIST — public_request_parser

## Каркас проекта

- [x***REMOVED*** `MANIFEST.md` существует.
- [x***REMOVED*** `README.md` существует.
- [x***REMOVED*** `SPEC.md` указывает на canonical specification.
- [x***REMOVED*** `ROADMAP.md` существует.
- [x***REMOVED*** `STEPS.md` существует.
- [x***REMOVED*** `LESSONS.md` существует.
- [x***REMOVED*** `RUNNABLE.md` существует.
- [x***REMOVED*** `CHECKLIST.md` существует.
- [x***REMOVED*** `requirements.txt` существует.
- [x***REMOVED*** `project.yaml` существует.
- [x***REMOVED*** `decisions/DECISIONS.md` и ADR существуют.
- [x***REMOVED*** `DOMAIN_CONTRACTS.md` описывает P3 API.
- [x***REMOVED*** `MATCHING_ENGINE.md` описывает P5 API.
- [x***REMOVED*** `STORAGE.md` описывает P6 API.
- [x***REMOVED*** `DELIVERY.md` описывает P7 API.

## До начала кода

- [ ***REMOVED*** Source matrix заполнена для первого RSS/Atom feed.
- [ ***REMOVED*** Policy decision для первого live URL = `allowed`.
- [ ***REMOVED*** TTL default и maximum утверждены.
- [ ***REMOVED*** Формула `accept/pending/reject` thresholds утверждена.
- [ ***REMOVED*** Состав технических metadata утверждён.
- [ ***REMOVED*** Telegram delivery transport выбран и документирован.
- [ ***REMOVED*** Граница Parser ↔ Lead Aggregator подтверждена через contract review.

## P3 Domain contracts

- [x***REMOVED*** Typed `Publication`, `SearchProfile`, `MatchDecision` и `SourcePolicy`.
- [x***REMOVED*** `RetentionPolicy` не ослабляет source TTL.
- [x***REMOVED*** `SourceAdapter`, `CheckpointStore`, `Delivery` оформлены как Protocol.
- [x***REMOVED*** Policy gate запрещает polling для не-`allowed` источников.
- [x***REMOVED*** Contract tests проходят в hermetic режиме.

## P4 RSS/Atom engine

- [x***REMOVED*** Fixture tests для RSS и Atom.
- [x***REMOVED*** Нормализация title/content/date/guid/id.
- [x***REMOVED*** Dedup повторного запуска.
- [x***REMOVED*** Checkpoint/resume после рестарта (in-memory port; SQLite в P6).
- [x***REMOVED*** Controlled warnings для неполных и повреждённых feeds.
- [x***REMOVED*** Fixture adapter не может стать live transport.
- [ ***REMOVED*** TTL cleanup удаляет полный текст (P6).

## P5 Matching

- [x***REMOVED*** Required/optional/excluded/synonym/intent правила.
- [x***REMOVED*** Пороги accept/pending/reject и boundary tests.
- [x***REMOVED*** Explainable decision: snapshot, matched/rejected, reasons.
- [x***REMOVED*** Intent gate отличает «ищет» от «предлагает».
- [ ***REMOVED*** Калибровка порогов на размеченных данных (P10/P14).

## P6 Storage and retention

- [x***REMOVED*** SQLite WAL + foreign keys + busy_timeout.
- [x***REMOVED*** Schema v1 через `PRAGMA user_version`, миграции идемпотентны.
- [x***REMOVED*** UNIQUE dedup: item_key и canonical_url.
- [x***REMOVED*** Checkpoint persistence (upsert) + async Store порт.
- [x***REMOVED*** Decisions и delivery_attempts идемпотентны.
- [x***REMOVED*** TTL cleanup обнуляет только content; metadata/decision остаются.
- [x***REMOVED*** Cap текста и запрет текста на уровне хранилища.
- [ ***REMOVED*** Scheduler регулярного TTL-прохода (P11).
- [ ***REMOVED*** Backup/restore и crash recovery (P11).

## P7 Delivery contract

- [x***REMOVED*** HTML-карточка с escape (без Markdown, без полей автора).
- [x***REMOVED*** Идемпотентный delivery_key; повторная доставка не дублирует send.
- [x***REMOVED*** Dry-run → SKIPPED без сети.
- [x***REMOVED*** Retry после FAILED (перезапись только failed-строк).
- [x***REMOVED*** Owner-гейт: scope совпадает с владельцем decision.
- [x***REMOVED*** Статусы попыток сохраняются в storage (get_delivery_attempt).
- [ ***REMOVED*** Кнопки viewed/relevant/irrelevant/archive (P8 UX).
- [ ***REMOVED*** Живой Telegram transport + credentials gate (P9).

## Telegram adapter gate

- [x***REMOVED*** Контракт delivery реализован (dry-run, idempotent, owner-гейт).
- [x***REMOVED*** Fixture web-preview адаптер реализован; ALLOWED-policy запрещена.
- [ ***REMOVED*** Policy/legal basis для live Telegram зафиксирован отдельно.
- [ ***REMOVED*** Live-доступ разрешён явно, а не по умолчанию.
- [x***REMOVED*** Нет private-chat access, outbound к авторам или обхода ограничений (контракт).
- [ ***REMOVED*** Нет передачи собранного контента в AI/ML pipeline.

## P8–P14 реализовано (offline)

- [x***REMOVED*** Offline pipeline + CLI `--once`/`--maintenance`; checkpoint-resume идемпотентен.
- [x***REMOVED*** `backup_to()` (P11).
- [x***REMOVED*** `HttpFeedAdapter` (P12): live только для `allowed` + `can_poll`.
- [x***REMOVED*** Schema v2: owner-isolated `profiles`, `feedback` + stats, миграция v1→v2 (P13/P14).
- [x***REMOVED*** ADR-008 (P15 remain separate) и ADR-009 (P16 deferred) зафиксированы.
- [ ***REMOVED*** G2: первый production `allowed` source (P10/P17/P18).
