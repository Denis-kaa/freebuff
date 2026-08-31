# AUTONOMY_MAP — вакансия «парсер недвижимости + Telegram-бот + деплой»

> Вакансия: ежедневный по расписанию парсер объектов недвижимости (площадь, цена, комнаты, характеристики) → БД; прокси, многопоточность/асинхронность; бот для управления; деплой на сервере.
> Разделение по промту 69 §2. Обновляется по мере работы.

## A — AGENT CAN DO (полностью самостоятельно)

| Действие | Основание |
|---|---|
| Исследование вакансии → ТЗ (USER → TECHNICAL → INFRA requirements) | анализ |
| Проектирование архитектуры (scheduler → scraper → parser → dedup → DB → bot) | существующие паттерны платформы |
| Написание кода парсера (httpx + bs4, есть в среде) | `TLSClient`/`WebScraper` паттерны уже в платформе (`projects_17/lead_aggregator`, `scripts_01/pricing_enumerator.py`) |
| Async workers + bounded concurrency (asyncio + semaphore) | httpx.AsyncClient уже async |
| Модель данных + дедупликация (natural key: source+external_id/url; hash-fallback) | `Deduplicator` + `CheckpointStore` (SQLite+WAL) уже реализованы в lead_aggregator |
| Telegram-бот управления (/status /run /stop /stats) | aiogram/telethon есть; `tg_digital_market` — готовый aiogram-скелет |
| Scheduler (APScheduler / cron / systemd timer) | systemd timer — минимально достаточный |
| Тесты (pytest, hermetic: FakeScraper DI, без сети) | паттерн `ScraperProtocol`/`FakeScraper` из `test_pricing_enumerator.py` |
| Dockerfile + docker-compose + deployment docs | стандарт |
| Retry/backoff/jitter + rate limiting | `RetryPolicy` (circuit breaker) уже реализована |
| Локальный запуск + статический анализ | среда |

## B — AGENT CAN DO, BUT NEEDS APPROVAL

| Действие | Почему |
|---|---|
| Выбор целевых сайтов-источников (какие порталы недвижимости парсить) | юридический/ToS-гейт (W-7): robots.txt, условия сайтов |
| Выбор прокси-провайдера и бюджет | платное решение, внешний аккаунт |
| Установка новых зависимостей (curl_cffi, playwright, APScheduler) | риск несовместимости с Python 3.14.6/Termux (W-2) |
| Продакшн-деплой на сервер заказчика | изменение внешней инфраструктуры |
| Схема БД финальная (PostgreSQL vs SQLite v1) | архитектурное решение под объём заказчика |

## C — HUMAN REQUIRED

| Действие | Минимальное действие человека |
|---|---|
| API keys / секреты (прокси-провайдер, TG bot token) | создать аккаунт у провайдера, выдать токен |
| Оплата прокси (residential/datacenter) | подтверждение оплаты |
| Доступ к серверу деплоя (SSH) | выдать SSH-доступ |
| Финальное утверждение списка сайтов-источников | выбрать из подготовленного списка |
| CAPTCHA-решение сервис (если понадобится) | аккаунт 2Captcha/CapMonster |

## D — EXTERNAL BLOCKERS

| Blocker | WHAT | WHY | MINIMUM HUMAN ACTION |
|---|---|---|---|
| Cloudflare-защита на порталах недвижимости | парсинг заблокирован без TLS-impersonation/headless | anti-bot на крупных порталах | купить curl_cffi-совместимый прокси или разрешить headless |
| CAPTCHA на источниках | доступ блокируется | anti-bot | аккаунт captcha-сервиса |
| Отсутствие API у SPA-источников (аналог W-16: Kwork стал SPA) | статичный HTML = скелет | JS-рендеринг | выбрать источники с SSR/API |
| Гео-блокировка источников | 403 без резидентного IP | rate-limit по гео | прокси нужной геолокации |

## Автономность (оценка)

- Research/Architecture/Code/Tests/Docs: **~95%**
- Deployment: **80%** (нужен SSH-доступ и секреты)
- Прокси/CAPTCHA: **~30%** (выбор + оплата — человек)
