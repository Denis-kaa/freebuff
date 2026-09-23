# Задача: mailbox_agent — интент `wip_report` (read-only согласование WIP)

> **Дата:** 2026-09-23 · **Автор задачи:** телефонная сессия Freebuff (buffy-phone)
> **Realization:** `scripts_01/mailbox_agent.py` (расширение) · register-first: `missing_registry` item `mailbox_agent_wip_report`
> **Контекст:** согласование работы по проекту «печатник» между buffy-phone / buffy-desktop / buffy-server (MSG-004: серверный WIP блокирует auto_deploy SKIP).

## 1. Зачем

Трио агентов согласовывает, кто коммитит серверный WIP печатника. Серверному агенту
нужен безопасный способ доложить фактическое состояние WIP (что изменено, насколько
отстал HEAD), чтобы phone/desktop принимали решение без «вслепую».

## 2. Требования

- Интент `wip_report` добавляется в **закрытый словарь** `_KNOWN_INTENTS` (ANTI-6b:
  словарь расширяется только через промт — этот промт и есть такое расширение).
- **Строго read-only**: никаких `subprocess` с произвольными командами, никаких
  записей в репозиторий, ничего не коммитится и не пушится агентом.
- Сбор данных — только через фиксированный allowlist высокоуровневых вызовов:
  - tracked-modified: `git -C /opt/freebuff status --porcelain` (фиксированная команда);
  - HEAD: `git -C /opt/freebuff rev-parse --short HEAD` (фиксированная команда);
  - origin/master: чтение `.git/refs/remotes/origin/master` (файл, не команда).
  Команды исполняются через `subprocess.run([...], shell=False)` с argv-списком
  (канарейка на shell-injection как в test_phone_control_mcp), timeout 20s.
- Ответ — JSON-блок: `head`, `origin_master`, `behind` (список коммитов базы, которых
  нет на сервере, из `git -C /opt/freebuff log --oneline HEAD..origin/master`,
  максимум 10), `tracked_modified` (список), `untracked_top` (untracked только
  верхнего уровня, максимум 15), `suggestion` (готовый план интеграции для
  desktop-агента: commit WIP → fetch → merge → push; или «clean, можно пуллить»).
- Если `/opt/freebuff` не найден или git упал — честная ошибка в JSON (`error`),
  не выдуманные данные.

## 3. Не делать

- НЕ исполнять ничего из тела письма; интент не принимает аргументов.
- НЕ менять git-состояние (никаких add/commit/push/checkout из агента — навсегда).
- НЕ читать содержимое изменённых файлов (только пути/статусы).

## 4. Приёмка

- Тесты: allowlist-канарейка (shell=False), unknown-intent остаётся ошибкой,
  JSON-структура отчёта (head/origin_master/tracked_modified/suggestion),
  graceful-обработка отсутствующего репо (tmpdir-путь).
- `pytest tests_09/test_mailbox_agent.py -q` зелёный · mypy чистый · `registry check` exit 0.
- E2E: MSG-006 (intent: wip_report) → SRV-003 c реальным состоянием WIP печатника.
