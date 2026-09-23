# DESKTOP_AGENT_ACCESS_RUNBOOK — доступ к серверу whimco для агента на компьютере

> **Статус:** ACTIVE · Runbook · создан 2026-09-22 в телефонной сессии Freebuff (handoff: агент на телефоне → агент на компьютере).
> **Целевая конфигурация:** компьютер **Linux**, агент **Codebuff (Buffy)**, доступ **SSH** + **MCP (stdio поверх SSH)**.
> **Канон:** правило Server-first (PROJECT_RULES §5.1, ADR-022, LESSONS CON-69); смежные рунбуки: `SERVER_ACCESS_WHIMCO.md` (корень, Termux-вариант), `docs_10/runbook/SYNC_RUNBOOK.md` (git-треугольник).

---

## TL;DR — 4 шага

1. Получи от пользователя SSH-доступ к серверу `root@185.233.184.192` (пароль или публичный ключ — один раз, не хранить в git).
2. Настрой SSH-алиас `whimco` в `~/.ssh/config` (см. §1) и проверь живость (см. §2).
3. Добавь MCP-сервер Freebuff в `.agents/mcp.json` рабочей копии `/opt/freebuff` — **stdio поверх SSH** (см. §3.1, основной вариант).
4. Правила работы с сервером — §4: ничего не удалять, бэкапы перед изменениями, `git fetch` + `checkout -f -B` (не `pull`).

⚠️ **Секреты (пароль/ключ сервера, токены GitHub) в репозиторий и в чат не попадают.** Ключ лежит только в `~/.ssh/` с правами `600`.

---

## 0. Контекст: что это за сервер и зачем

| Параметр | Значение |
|---|---|
| Хост | `185.233.184.192` (имя хоста: `whimco`) |
| Вход | `root` по SSH-ключу |
| Рабочая копия | `/opt/freebuff` — git-репозиторий, `origin` = `https://github.com/Denis-kaa/freebuff.git` |
| Данные (вне git, не трогать) | `data_13/context.db`, `context_12/events.db`, `.env`, `context_12/events.db` — gitignored |
| Бэкап | `/opt/freebuff-server-backup-20260829T201345Z` (исторический) |
| Роль сервера | канонический дом проектов (Server-first): проекты живут и создаются здесь; GitHub = single source of truth; телефон — мобильный узел |

Критично: **SSH-порт 22 от GitHub с сервера закрыт** — сервер ходит в GitHub только по HTTPS:443. Это влияет только на git-операции сервера, не на твой вход.

## 1. Первичная настройка SSH (один раз, руками агента на компьютере)

### 1.1 Вариант А — пользователь уже скопировал свой ключ на сервер (предпочтительно)

На компьютере сгенерируй отдельный ключ (не переиспользуй чужие):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_whimco -C "desktop-agent-$(hostname)"
```

Передай **публичный** ключ (`~/.ssh/id_ed25519_whimco.pub`) пользователю — он добавит его на сервер (или сам выполнит, если у пользователя есть рабочий доступ, например с телефона):

```bash
# выполняет тот, у кого уже есть доступ (например, телефонная сессия):
# ssh-copy-id -i <pub> root@185.233.184.192
```

### 1.2 Вариант Б — пользователь дал одноразовый пароль

```bash
ssh-copy-id -i ~/.ssh/id_ed25519_whimco.pub root@185.233.184.192
# введёшь пароль один раз; дальше — только по ключу
```

### 1.3 Конфиг-алиас (обязательно)

Создай `~/.ssh/config` (права `600`):

```sshconfig
Host whimco
    HostName 185.233.184.192
    User root
    IdentityFile ~/.ssh/id_ed25519_whimco
    IdentitiesOnly yes
    ServerAliveInterval 30
    ServerAliveCountMax 4
```

Дальше везде используй **только алиас `whimco`** — не IP и не ключ вручную. Алиас — единая точка правок, и он защищает от опечаток при смене ключа.

## 2. Проверка живости (первым делом в каждой сессии)

```bash
timeout 20 ssh -o ControlMaster=no -o ControlPath=none whimco 'echo OK; hostname; git -C /opt/freebuff rev-parse --short HEAD'
```

Ожидаемый ответ: `OK`, `whimco`, текущий HEAD репозитория.

Отличия от телефонного рунбука (`SERVER_ACCESS_WHIMCO.md`): на Linux конфиг в `~/.ssh/config`, флаг `-F` с явным путём не нужен. Флаги `-o ControlMaster=no -o ControlPath=none` и `timeout` сохранены — та же дисциплина против зависаний и мёртвых мастер-соединений.

## 3. Подключение MCP-сервера Freebuff (главная цель)

MCP-сервер платформы — `scripts_01/mcp_server.py` (чистый Python, stdlib-only, без внешних SDK):
- **Транспорт stdio** (JSON-RPC 2.0 по stdin/stdout) — то, что нужно Codebuff;
- дополнительно есть HTTP-режим (`--http --port 8765`) — запасной вариант (§3.2);
- workspace вычисляется от пути самого файла (`Path(__file__).resolve().parent.parent`), поэтому на сервере сервер автоматически работает в `/opt/freebuff` без конфигов;
- инструменты (`~52` + авто-discovery из ToolRegistry): `knowledge_search`, `memory_store`, `memory_retrieve`, `memory_list`, `session_status`, `context_resume`, `event_search`, `event_timeline`, `event_replay`, `event_audit`, `event_pulse`, `rag_search`, `rag_hybrid`, `rag_rerank`, `pulse_list`, `pulse_stats`, `pulse_scan`, `roles_*`, `presence_*`, `collab_*`, `distributed_*`, `plugins_list`, `bridge_*`, `bootstrap_*`, `runtime_*`, `policy_override`.
- полный список: `python scripts_01/mcp_server.py --tools` (на сервере).

### 3.1 Основной вариант: stdio MCP поверх SSH (рекомендуется для Codebuff)

Codebuff читает MCP-конфиг из **`.agents/mcp.json`** (формат: корневой ключ `mcpServers`, `command` + `args` + `env`; поддерживается только stdio — HTTP-эндпоинты подключать нельзя).

В рабочей копии репозитория на компьютере (после `git clone https://github.com/Denis-kaa/freebuff.git`) создай `.agents/mcp.json`:

```json
{
  "mcpServers": {
    "whimco-buffy": {
      "command": "ssh",
      "args": [
        "-o", "ControlMaster=no",
        "-o", "ControlPath=none",
        "-o", "ServerAliveInterval=30",
        "whimco",
        "cd /opt/freebuff && python3 scripts_01/mcp_server.py"
      ]
    }
  }
}
```

Как это работает: Codebuff запускает `ssh whimco '... mcp_server.py'` как subprocess → stdout процесса становится stdio-каналом MCP → JSON-RPC идёт по SSH. Никаких открытых портов, никакой публичной экспозиции, авторизация = SSH-ключ.

⚠️ Нюансы:
- Сервер пишет служебные сообщения в **stderr**, JSON-RPC — в **stdout**: чисто для stdio-транспорта. Но не запускай с `-t` (TTY) — TTY ломает бинарную чистоту stdout.
- Каждый вызов поднимает SSH-сессию (~1–3 с на установление). Если Codebuff перезапускает MCP-подключение часто — можно убрать `-o ControlMaster=no` и включить мультиплексирование (`ControlMaster auto` + `ControlPath ~/.ssh/cm-%r@%h:%p` + `ControlPersist 10m` в `~/.ssh/config`), НО помни телефонный урок: мёртвый мастер-сокет «тихо» ломает соединения. При проблемах — вернись к чистому соединению.
- Проверка руками до подключения к Codebuff (должен вернуть JSON-RPC-ответ с capabilities):

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"hand-check","version":"0"}}}' \
  | timeout 20 ssh -o ControlMaster=no -o ControlPath=none whimco 'cd /opt/freebuff && python3 scripts_01/mcp_server.py'
```

- Смоук после подключения в Codebuff: попроси агента вызвать MCP-инструмент `session_status` (без аргументов) — должен вернуть статус сервера без ошибки.

### 3.2 Запасной вариант: HTTP MCP через SSH-туннель (если stdio-over-SSH капризничает)

На сервере MCP может работать как HTTP (Streamable HTTP на `:8765`, FastAPI-обёртка — `scripts_01/mcp_fastapi.py`). Снаружи порт не открываем — тянем его локально через SSH:

```bash
# локально, в отдельном терминале (держит туннель, foreground):
ssh -N -L 8765:127.0.0.1:8765 whimco
```

На сервере убедись, что слушатель поднят:

```bash
# посмотреть, слушается ли 8765
timeout 20 ssh whimco 'ss -tlnp | grep 8765 || echo NOT_LISTENING'

# если NOT_LISTENING — поднять (nohup, лог, по правилам платформы):
timeout 30 ssh whimco 'cd /opt/freebuff && nohup python3 scripts_01/mcp_server.py --http --host 127.0.0.1 --port 8765 > /tmp/buffy_mcp_http.log 2>&1 & echo started'
```

- HTTP-вариант защищён Bearer-токеном (`FREEBUFF_MCP_TOKEN`, берётся из `/opt/freebuff/.env`; fallback — Vault через `FREEBUFF_VAULT_ADDR`/`FREEBUFF_VAULT_TOKEN`; без токена → 401). Токен узнай у пользователя/прочитай на сервере — **в чат и git не выводи**.
- Быстрый тест: `curl -s -X POST http://127.0.0.1:8765/mcp -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}'`
- Caveat: stdio-сервер и FastAPI-сервер — **разные инстансы**: knowledge/memory пишут в локальные БД сервера, поэтому оба варианта работают с одними данными, но сессии не разделяются. Для Codebuff основной путь — всё равно §3.1 (stdio).
- **Cloudflare Tunnel / открытые порты — НЕ использовать** без явного указания пользователя: сервер уже имеет публичную поверхность (web-проекты на :8020/:8300 и пр.), добавлять новую не нужно.

### 3.3 Что даёт подключение (кратко)

Через MCP агент на компьютере получает инструменты платформы: поиск по знаниям (`knowledge_search`), память (`memory_store/retrieve`), события (`event_search/timeline`), RAG, collaboration/presence, policy override. Плюс ресурсы: `buffy://manifest` (BUFFY.md), `buffy://task`, `buffy://changelog` и др.

## 4. Правила работы с сервером (не нарушать)

1. **Ничего не удалять** в `/opt/freebuff` без явного указания пользователя.
2. Бэкап `data_13/context.db`, `context_12/events.db`, `.env` перед любыми деструктивными операциями: `timeout 30 ssh whimco 'mkdir -p /opt/freebuff-server-backup-$(date +%Y%m%dT%H%M%SZ) && cp -a /opt/freebuff/data_13/context.db /opt/freebuff/context_12/events.db /opt/freebuff/.env /opt/freebuff-server-backup-<TS>/'`.
3. Обновление серверной копии — только `git fetch origin && git checkout -f -B master origin/master` (не `pull`). **Перед hard-checkout убедись, что серверный WIP закоммичен** (LESSONS CON-69): `timeout 30 ssh whimco 'cd /opt/freebuff && git status --porcelain'` — пусто или всё осознанно.
4. Долгие команды (git fetch, сборки) — `timeout` до 300, никогда без таймаута.
5. Секреты в git не попадают: перед `git add -A` проверять `credentials.json`/`.env`-подобные файлы.
6. WIP любого узла обязан попасть в базу (GitHub) в тот же заход — правило Server-first. Сервер коммитит и пушит сам: `cd /opt/freebuff && git add -A && git commit -m "wip(server): ..." && git push origin master`.
7. Соединение оборвалось — просто повтори команду; с `-o ControlMaster=no` бана не будет.

Полная механика синхронизации — `docs_10/runbook/SYNC_RUNBOOK.md` (треугольник телефон ↔ GitHub ↔ whimco, emergency git-bundle, troubleshooting).

## 5. Troubleshooting

| Симптом | Причина | Fix |
|---|---|---|
| `ssh: connect to host ... port 22: Connection timed out` (с телефона так и было 2026-09-22) | мобильная/корпоративная сеть режет исходящий 22 | с компьютера обычно ок; если нет — проверить провайдера/файрвол, VPN как обход |
| `Permission denied (publickey)` | ключ не добавлен на сервер / не тот IdentityFile | `ssh -v whimco`, проверить §1; ключ с правами `600` |
| MCP-подключение в Codebuff «висит» | TTY/binary-мусор в stdout или мёртвый мастер-сокет | убрать `-t` из ssh; `ControlMaster=no`; проверить руками §3.1 |
| MCP tools не видны | сервер упал при старте | посмотреть stderr: `timeout 20 ssh whimco 'cd /opt/freebuff && python3 scripts_01/mcp_server.py --status'` |
| `ModuleNotFoundError` на сервере при запуске mcp_server | python 3.х без нужного stdlib (редко) | серверный python: `python3 --version`; сервер чисто stdlib-only — значит, битая рабочая копия: `git -C /opt/freebuff status` |
| HTTP-вариант: 401 | нет/неверный bearer | токен из `/opt/freebuff/.env` (`FREEBUFF_MCP_TOKEN`); не копировать в git/чат |
| git push с сервера отклонён | параллельный коммит на другом узле | `git fetch` → сверить → merge/rebase по ситуации (SYNC_RUNBOOK §4) |
| CRLF-различия | Windows-происхождение файлов | `sed -i 's/\r$//'` по текстовым расширениям на обеих сторонах (SYNC_RUNBOOK §4) |

## 6. Чек-лист готовности агента на компьютере

- [ ] SSH-ключ создан, публичная часть добавлена на сервер, `~/.ssh/config` содержит алиас `whimco` (§1)
- [ ] Проверка живости отвечает `OK` + hostname + HEAD (§2)
- [ ] Локальная рабочая копия репозитория склонирована (для `.agents/mcp.json` и чтения канона)
- [ ] `.agents/mcp.json` создан по §3.1, рукопожатие MCP прошло (§3.1, проверка руками)
- [ ] В Codebuff MCP-инструменты видны, смоук `session_status` зелёный
- [ ] Прочитаны: `AGENTS.md` (правила платформы), `SERVER_ACCESS_WHIMCO.md` (телефонный вариант), `docs_10/runbook/SYNC_RUNBOOK.md` (синхронизация)
- [ ] Ноль секретов в git/чатах

## 7. Cross-links

- `SERVER_ACCESS_WHIMCO.md` — вход на сервер с телефона (Termux): оригинальный рунбук, отсюда взяты правила
- `docs_10/runbook/SYNC_RUNBOOK.md` — Server-first sync (git-треугольник), emergency bundle
- `docs_10/core/PROJECT_RULES.md` §5.1 — правило Server-first (канон)
- `docs_10/decisions/DECISIONS.md` ADR-022 — решение о топологии синхронизации
- `scripts_01/mcp_server.py` / `scripts_01/mcp_fastapi.py` — MCP-сервер (stdio/HTTP) и FastAPI-обёртка
- `docs_10/plugin/FREEBUFF_PLUGIN_API.md` — конфиги MCP для других клиентов (Claude Desktop, VS Code/Cursor, OpenClaw)
- `core_02/LESSONS.md` CON-69 — sync-before-hard-checkout

---

_Создан 2026-09-22 телефонной сессией Freebuff (handoff для десктоп-агента). Проверка живости сервера в момент создания не выполнялась (SSH с телефона: таймаут исходящего 22-го порта); все параметры взяты из `SERVER_ACCESS_WHIMCO.md` (проверен 2026-08-29) и кода репозитория._
