# PHASE_HUB_V2_REPORT.md — Communication Hub v2: Email-канал + ответы из «Входящих»

> **Статус:** COMPLETE · **Дата:** 2026-09-21
> **Этап:** Communication Hub v2 (код, §4 п.1) · промт_печатник_4 §43/§45 · RESEARCH_ADOPTION_PLAN §5-Б п.11
> **Верификация:** 481 passed (было 469 → +12 новых, `test_hub_v2.py`) · mypy clean (22 файла) · живой смоук после деплоя

---

## 1. Что сделано

| Артефакт | Файл | Суть |
|---|---|---|
| Email-приём | `src/printcalc_web/mail_poller.py` (новый, 224 строки) | `ImapAdapter` — единственное место, знающее imaplib (Adapter Pattern §47). Poll-loop в daemon-потоке при старте приложения. Без кредов — тихий no-op: канал «не включён», приложение работает |
| Шаблоны ответов | `src/printcalc_web/reply_templates.py` (новый, 127 строк) | Закрытый словарь (ANTI-6b): `R1_GROUPED_QUESTION` / `R2_PACKAGE_EXPLAIN` / `R3_HOW_TO_ORDER` из research/14. Детерминированная подстановка распознанных фактов парсера; нет факта → placeholder «…» (не выдумка, §37) |
| API | `src/printcalc_web/api.py` | `GET /api/reply-templates` (список) + `POST /api/reply-templates/{id}/render` (подстановка фактов заявки на сервере — источник истины в одном месте) |
| Ответ по email | `src/printcalc_web/store.py` | `_reply_recipient`: если сообщение пришло по email (или email в контактах клиента) → отправка письма через существующий `emailer.dispatch` (SMTP-слой уже был) |
| UI | `templates/inbox.html` + `static/inbox.js` | Селектор «Шаблон ответа» в диалоге заявки + кнопка «Вставить»: fetch render-эндпоинта с parsed-фактами заявки → текст в поле ответа, оператор правит перед отправкой |
| Подключение | `src/printcalc_web/__init__.py` | `start_mail_poller()` рядом с TG-поллером при создании приложения |

## 2. Ключевые решения

| Решение | Основание |
|---|---|
| Зеркало `telegram.py` вместо нового фреймворка | Adapter Pattern §47; один и тот же контракт `record_incoming_message` |
| Идемпотентность по Message-ID = `external_id` | §55: `store.record_incoming_message` уже дедуплицирует по `(channel, external_id)`; дубликат письма не создаёт строку и не помечается seen |
| Incoming → существующие таблицы | §43: mailbox = IMAP-ящик (один), conversation = клиент/заявка, message = `inbox_messages`. Отдельной CRM-сущности НЕТ — архитектура не раздувается |
| Подстановка фактов на сервере, не в JS | §37: текст клиенту детерминированный; одна реализация — один источник истины |
| Email-fallback в `_reply_recipient` | Приоритет адресата: telegram → email-отправитель → email из контактов клиента |
| `sizes` из parsed_json + fallback на текст запроса | «наклейка 20 на 30» → «20×30» в R1-вопросе; двухместные размеры приоритетнее одиночных чисел (тираж) |

## 3. Конфигурация (env, CODE_QUALITY 4.7)

```
PRINTCALC_IMAP_HOST        # хост IMAP (пусто → канал выключен, no-op)
PRINTCALC_IMAP_PORT        # default 993 (SSL)
PRINTCALC_IMAP_USER        # логин ящика
PRINTCALC_IMAP_PASSWORD    # пароль
PRINTCALC_IMAP_FOLDER      # default INBOX
PRINTCALC_IMAP_ENABLED     # «0» выключает даже с кредами (default 1)
PRINTCALC_IMAP_POLL_SECONDS  # default 60
```

SMTP-параметры ответов — уже существующие переменные `emailer.py` (`PRINTCALC_SMTP_*`).

## 4. Тесты (+12, `tests/test_hub_v2.py`)

| Группа | Тесты |
|---|---|
| ImapAdapter | `test_to_payload_extracts_fields` (заголовки/From/текст), `test_process_message_records_and_marks_seen` (запись+seen), `test_process_message_duplicate_not_marked` (дедуп) |
| Шаблоны | `test_templates_closed_vocabulary` (ANTI-6b), `test_render_unknown_template_raises` (loud), R1 с размерами / без фактов («…»), R2 (состав пакета), R3 (процедура, не цены) |
| Ответ | `test_reply_recipient_email_message` (email-сообщение → outbox), `test_reply_recipient_email_via_client_contact` (fallback на контакты) |
| API | `test_api_reply_templates_endpoints` |

## 5. Границы этапа (честно)

- **Реальный IMAP-ящик не подключён** — нужен адрес/пароль от владельца (как TG-токен). Код проверен тестами на фейковом адаптере; при появлении кредов канал включается env-переменными без правок кода.
- Отправка ответов — через существующий SMTP (`emailer.py`); если SMTP-кредов нет, ответ попадает в outbox с ошибкой отправки (виден в UI, ретрай кнопкой).
- Вложения писем (макеты PDF/TIFF) — не в этом этапе: приём файлов отдельная задача §4.

---

*Верификация: `/opt/printcalc-venv/bin/python -m pytest tests/ -q` → 481 passed; mypy → Success: no issues found in 22 source files.*
