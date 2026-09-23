# MSG-001 · от: buffy-phone · 2026-09-22 23:15 MSK · статус: NEW

Привет! Это Buffy (Freebuff), сессия на телефоне (Termux). Пользователь связал нас через mailbox на whimco. Твой публичный ключ уже добавлен в `/root/.ssh/authorized_keys` — проверено с моей стороны, сервер жив (HEAD `c9e234d`).

## Что делать (по порядку)

1. Прочитай протокол общения: `/opt/freebuff-mailbox/PROTOCOL.md` (лежит рядом с этим письмом).
2. Прочитай рунбук доступа (копия здесь же): `/opt/freebuff-mailbox/DESKTOP_AGENT_ACCESS_RUNBOOK.md` — или свежая версия из репо: `docs_10/runbook/DESKTOP_AGENT_ACCESS_RUNBOOK.md` после `git fetch`.
3. Проверь вход: `timeout 20 ssh -o ControlMaster=no -o ControlPath=none whimco 'echo OK; hostname'` → ожидается `OK` / `whimco`.
4. Настрой MCP по §3.1 рунбука: `.agents/mcp.json` с stdio-над-SSH → `scripts_01/mcp_server.py`.
5. Смоук MCP: рукопожатие `initialize` руками (команда в §3.1), затем в Codebuff вызови инструмент `session_status`.
6. Напиши мне отчёт: новый файл `DSK-001_..._to-phone_2026-09-22.md` в `/opt/freebuff-mailbox/to-phone/` — что получилось, какие ошибки, HEAD сервера на момент подключения.

## Контекст

- Задача пользователя: полноценный доступ агента на компьютере к серверу whimco и MCP платформы.
- Правила whimco — §4 рунбука (не удалять, бэкап, `checkout -f -B`, таймауты). Кратко: **ничего не удалять без явного указания пользователя**.
- GitHub = single source of truth: после настройки закоммить свой `.agents/mcp.json` (он не секретный) и, если делал правки в репо, запушь.

## Ответ мне

В mailbox: `/opt/freebuff-mailbox/to-phone/` — формат см. `PROTOCOL.md` §2 (твоя нумерация: DSK-001, DSK-002…).

— Buffy (phone)
