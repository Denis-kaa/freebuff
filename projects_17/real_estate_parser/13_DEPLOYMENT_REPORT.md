# 13_DEPLOYMENT_REPORT — статус деплоя

## Статус: BLOCKED (нет доступа к серверу и секретам — категория C/D)

## Что спроектировано (UNVERIFIED — не запускалось)

| Компонент | Конфиг | Статус |
|---|---|---|
| Dockerfile + docker-compose | parser + bot + PostgreSQL, один `docker-compose up` | DESIGNED |
| systemd timer (альтернатива Docker) | ежедневный cron-запуск + `restart` | DESIGNED |
| Секреты | только env (`.env` в `.gitignore`), не в коде | DESIGNED |
| run_log | каждая запись прогона логируется в БД для /stats | DESIGNED |

## Что нужно от человека

1. SSH-доступ к серверу (host, user, key).
2. Строка подключения к PostgreSQL (или согласие на контейнерный Postgres).
3. TG bot token (BotFather).
4. Прокси-провайдер: выбор, оплата, URL/ключ.

## Acceptance (когда деплой станет возможен)

- `docker-compose up -d` поднимает всё с нуля на чистом сервере.
- Ручной /run из бота запускает прогон; cron срабатывает по расписанию.
- Restart контейнера не теряет state (property + run_log персистентны).
- Повторный прогон не создаёт дублей.
