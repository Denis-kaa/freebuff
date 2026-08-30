# Инструкция: вход на сервер whimco (для другого агента)

Проверено только что: соединение работает, сервер отвечает.

## 1. Как подключаться

Подключайся **только через SSH-алиас** `whimco` из конфига Termux. Не пиши IP и ключ вручную — конфиг уже настроен против fail2ban-бана.

```bash
ssh -F /data/data/com.termux/files/home/.ssh/config whimco '<команда>'
```

Ключевые параметры конфига (уже прописаны, повторять не нужно):

| Параметр | Значение | Зачем |
|---|---|---|
| HostName | `185.233.184.192` | IP сервера |
| User | `root` | вход под root |
| IdentityFile | `/data/data/com.termux/files/home/.ssh/id_ed25519_whimco` | ключ доступа |
| ControlMaster | auto / Persist 4h | одно соединение на всех, не дёргает fail2ban |

## 2. Обязательные флаги для каждой команды

Из скриптов и агентов всегда вызывай так — это предотвращает и зависания, и переиспользование «мертвого» мастера-соединения:

```bash
timeout 40 ssh -o ControlMaster=no -o ControlPath=none -F /data/data/com.termux/files/home/.ssh/config whimco '...'
```

- `timeout 40` (или меньше для быстрых команд) — SSH иногда виснет, таймаут обязателен.
- `ControlMaster=no -o ControlPath=none` — новое чистое соединение; старый мультиплексор может быть мёртв.
- Не передавай параметр `cwd` в tool-вызов — удалённая команда выполняется на сервере внутри кавычек, а локальный bash от `cwd` падает с ENOENT.

## 3. Что на сервере

- `/opt/freebuff` — рабочая копия репозитория (Git-репозиторий, remote `origin` = HTTPS `https://github.com/Denis-kaa/freebuff.git`; SSH-порт 22 к GitHub с сервера закрыт, работает только 443/HTTPS).
- `data_13/context.db`, `context_12/events.db`, `.env` — серверные данные, в `.gitignore`, **не трогать и не перезаписывать**.
- Резервная копия: `/opt/freebuff-server-backup-20260829T201345Z`.

## 4. Правила работы

1. **Ничего не удалять** в `/opt/freebuff` без явного указания пользователя.
2. Обновление копии — только через `git fetch origin && git checkout -f -B master origin/master` (не `pull`).
3. Перед любыми изменениями — убедиться, что свежий бэкап критичных данных существует.
4. Для долгих команд (fetch, сборка) поднимай `timeout` до 300, но не запускай без таймаута.
5. Если соединение оборвалось — просто повтори команду; ControlMaster не используется, бана не будет.

## 5. Быстрая проверка живости

```bash
timeout 20 ssh -o ControlMaster=no -o ControlPath=none -F /data/data/com.termux/files/home/.ssh/config whimco 'echo OK; hostname; git -C /opt/freebuff rev-parse --short HEAD'
```

Ожидаемый ответ: `OK`, `whimco`, текущий HEAD репозитория.
