---
category: automation
complexity: средняя
description: Telegram бот для мониторинга здоровья серверов, процессов и сервисов с алертами и дашбордом
tags:
  - telegram
  - monitoring
  - bot
  - healthcheck
  - alerting
---

# Сценарий: Telegram Health Monitor

## Описание задачи

Telegram бот для мониторинга здоровья серверов, процессов и сервисов. 
Бот отслеживает системные метрики (CPU, RAM, Disk), проверяет доступность HTTP/HTTPS эндпоинтов,
следит за процессами и отправляет алерты при превышении порогов.

## Технические требования

```yaml
стек:
  python: 3.11+
  библиотеки:
    - python-telegram-bot 20.x
    - psutil  # системные метрики
    - httpx/aiohttp  # HTTP healthchecks
    - aiosqlite  # хранение состояния
    - pydantic  # модели данных
  хранение: sqlite (через aiosqlite)
  запуск: systemd / tmux / Termux (termux-services)
  алерты: Telegram (inline buttons: /silence, /ack, /escalate)
```

## Промт для freebuff

```
Разработай Telegram Health Monitor бота.

### Функционал

1. **Системный мониторинг:**
   - CPU: загрузка, температура (если доступно)
   - RAM: использовано/всего, процент
   - Disk: использовано/всего по смонтированным разделам
   - Network: активные соединения, трафик
   - Uptime: время работы системы
   - Load Average: 1/5/15 минут

2. **Healthchecks:**
   - HTTP(S) эндпоинты — код ответа, время ответа, SSL expiry
   - TCP порты — открыт/закрыт
   - Процессы — запущен/остановлен, потребление ресурсов
   - Docker контейнеры — статус, перезапуски
   - Ping — потеря пакетов, latency

3. **Алерты (пороговые значения):**
   - CPU > 80% — WARNING, > 95% — CRITICAL
   - RAM > 85% — WARNING, > 95% — CRITICAL
   - Disk > 85% — WARNING, > 95% — CRITICAL
   - HTTP 5xx — CRITICAL, HTTP 4xx — WARNING
   - Процесс упал — CRITICAL
   - SSL < 7 дней — WARNING, < 1 день — CRITICAL

4. **Команды бота:**
   /start — приветствие, меню
   /status — сводка по всем системам (CPU/RAM/Disk)
   /health — проверка всех настроенных healthchecks
   /processes — список отслеживаемых процессов
   /alerts — история алертов
   /silence <minutes> — отключить алерты на N минут
   /add_check <type> <target> — добавить healthcheck
   /remove_check <id> — удалить healthcheck
   /config — текущая конфигурация мониторинга

5. **Inline режим:**
   - Нажатие на алерт: /ack — подтвердить, /silence 60 — заглушить
   - Кнопки: "Обновить", "Подробнее", "Заглушить на 1ч"

### Требования к реализации:
1. Асинхронная архитектура (asyncio + python-telegram-bot)
2. Шедулер для периодических проверок (JobQueue из python-telegram-bot — primary; apscheduler или asyncio.create_task — fallback)
3. Graceful degradation: если метрика недоступна — пропустить, не падать
4. Логирование через structlog или стандартный logging
5. Конфигурация через config.py + .env (TGBOT_TOKEN, CHECK_INTERVAL, THRESHOLDS)
6. Экспорт метрик для Prometheus (опционально, /metrics на localhost)
7. Graceful shutdown: сохранить состояние, завершить задачи

### Структура проекта:
```
tg_health_monitor/
├── main.py                  # точка входа, asyncio.run
├── bot/
│   ├── __init__.py
│   ├── app.py               # Application, handlers registration
│   ├── handlers.py          # команды /start, /status, /health
│   └── keyboards.py         # inline клавиатуры
├── monitor/
│   ├── __init__.py
│   ├── system.py            # psutil метрики (CPU/RAM/Disk)
│   ├── http_check.py        # HTTP/TCP healthchecks
│   ├── process_watch.py     # мониторинг процессов
│   └── scheduler.py         # периодические проверки
├── models.py                # Pydantic модели (Alert, Check, Config)
├── database.py              # aiosqlite — хранение чеков, алертов, настроек
├── config.py                # настройки + .env
├── requirements.txt
└── Dockerfile (опционально)
```

Напиши полный код всех файлов с обработкой ошибок, логированием и graceful shutdown.
```

## Варианты

| Тип монитора | Особенности | Сложность |
|-------------|-----------|-----------|
| **Одиночный сервер** | psutil + healthchecks | низкая |
| **Несколько серверов** | SSH + агентская модель | высокая |
| **Kubernetes кластер** | K8s API + поды/ноды | высокая |
| **Docker compose** | Docker SDK + контейнеры | средняя |
| **Внешние сервисы** | HTTP checks + SSL + Ping | низкая |
| **Гибридный** | Сервер + Внешние + Docker | средняя |

## Расширения

| Фича | Описание | Приоритет |
|------|----------|-----------|
| **Prometheus экспортёр** | /metrics для Grafana | P2 |
| **SLA статистика** | Uptime % за день/неделю/месяц | P2 |
| **Webhook интеграция** | Отправка в PagerDuty/OpsGenie | P2 |
| **Дашборд в Grafana** | Через Prometheus | P3 |
| **Агент для удалённых серверов** | Легковесный агент + шифрованный канал | P3 |
