# Задача: mailbox_agent — живой агент buffy-server на whimco

> **Дата:** 2026-09-22 · **Автор задачи:** телефонная сессия Freebuff (buffy-phone)
> **Realization:** `scripts_01/mailbox_agent.py` · register-first: `missing_registry` item `mailbox_agent` (capability)

## 1. Зачем

Три агента платформы общаются через файловый mailbox на сервере whimco
(`/opt/freebuff-mailbox/`, протокол v1.1 — `mailbox/PROTOCOL.md`):
- `buffy-phone` (телефон, Freebuff-сессия),
- `buffy-desktop` (компьютер, Codebuff),
- `buffy-server` — **этот агент**: живёт прямо на whimco, mailbox для него локальная ФС.

Нужен минимальный самостоятельный процесс-агент, который:
1. циклически сканирует `/opt/freebuff-mailbox/to-server/`;
2. обрабатывает письма по **закрытому словарю интентов** (дух ANTI-6b: неизвестный интент — не выдумывать, а отчётить ошибку);
3. пишет отчёты/ответы `SRV-NNN` в папки получателей (`to-phone/`, `to-desktop/`);
4. при онбординге подтверждает готовность первым письмом `SRV-001`.

## 2. Требования (CODE_QUALITY_STANDARD v2.0)

- stdlib-only (сервер не должен тянуть зависимости ради агента);
- type hints, module docstring, Google-style docstrings, комментарии на русском;
- атомарная запись писем (`.tmp` + `os.replace` — как в whim_capture);
- идемпотентность: повторная обработка того же письма не даёт дубликата ответа
  (файл после обработки перемещается в `archive/`, не удаляется);
- daemon-friendly: один проход за итерацию, sleep между итерациями, SIGTERM-обработка;
- CLI: `--once` (один проход, для тестов/cron), `--loop [SECONDS]` (демон), `--status` (JSON);
- конфиг через env: `FREEBUFF_MAILBOX_DIR` (default `/opt/freebuff-mailbox`),
  `FREEBUFF_MAILBOX_AGENT_ID` (default `buffy-server`), `FREEBUFF_MAILBOX_INTERVAL_S` (default 300).

## 3. Закрытый словарь интентов (INTENT_HANDLERS)

| Интент (в шапке письма, строка `интент:` или `intent:`) | Действие |
|---|---|
| `ping` | ответ `pong` + статус агента (в папку отправителя) |
| `status` | JSON-отчёт: uptime, head, mailbox-счётчики (в папку отправителя) |
| `hello` (онбординг) | `SRV-001`: приветствие + готовность + список известных интентов |
| отсутствует/неизвестен | письмо-ошибка отправителю: интент не в словаре; само письмо всё равно архивируется |

Письмо без интента → обработка как unknown (не падать).

## 4. Не делать (границы)

- НЕ запускать shell-команды из писем (нет интента `exec` — и не появится без нового промта);
- НЕ трогать `/opt/freebuff` git-состояние из агента (git — только через человека/сессии агентов);
- НЕ удалять письма (только `archive/`);
- НЕ хранить секреты.

## 5. Приёмка

- `tests_09/test_mailbox_agent.py`: парсинг шапки, закрытый словарь (ping/hello/unknown), идемпотентность, атомарность, CLI `--once`/`--status` — все зелёные;
- `python -m pytest tests_09/test_mailbox_agent.py -q` + `python -m mypy scripts_01/mailbox_agent.py --ignore-missing-imports`;
- `python -m core_02.missing_registry check` → exit 0;
- E2E на сервере: MSG-003 (`intent: hello`) в `to-server/` → `SRV-001` появился в `to-phone/`.
