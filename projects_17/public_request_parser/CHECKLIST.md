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

## Telegram adapter gate

- [ ***REMOVED*** Технические fixtures проходят parser contract.
- [ ***REMOVED*** Policy/legal basis зафиксирован отдельно.
- [ ***REMOVED*** Live-доступ разрешён явно, а не по умолчанию.
- [ ***REMOVED*** Нет private-chat access, outbound к авторам или обхода ограничений.
- [ ***REMOVED*** Нет передачи собранного контента в AI/ML pipeline.
