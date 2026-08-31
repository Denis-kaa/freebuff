# 10_ACCEPTANCE_CRITERIA — критерии приёмки

## Parser

- [ ] parser запускается командой из README без ручных правок
- [ ] объекты извлекаются с живого источника (площадь, цена, комнаты, url, external_id)
- [ ] поля нормализуются: price → NUMERIC, area → м² (NUMERIC), rooms → NUMERIC
- [ ] неполные записи (нет price или area) отбраковываются и логируются

## Scheduler

- [ ] ежедневный прогон срабатывает по расписанию (APScheduler cron)
- [ ] ручной запуск через бота /run работает
- [ ] /stop мягко останавливает прогон

## Database

- [ ] данные записываются в PostgreSQL (upsert по natural key)
- [ ] duplicates не создаются: повторный прогон не вставляет новых строк для тех же объектов
- [ ] смена цены фиксируется событием price_changed в property_event
- [ ] restart не уничтожает state (run_log, property сохраняются)

## Bot

- [ ] /status показывает последний прогон (время, счётчики)
- [ ] /stats показывает количество объектов, новых/обновлённых
- [ ] /errors показывает последние ошибки
- [ ] бот отвечает на все команды MVP

## Errors & retry

- [ ] ошибки логируются в run_log (fetched/created/updated/removed/errors)
- [ ] retry с backoff+jitter работает (тестируется FakeScraper, без сети)
- [ ] временная ошибка сети не валит весь прогон

## Deployment

- [ ] docker-compose up поднимает parser + bot + PostgreSQL
- [ ] деплой воспроизводим с нуля по README
- [ ] секреты только через env, не в коде

## Статусы (честность)

Каждый пункт помечается: DESIGNED / IMPLEMENTED / TESTED / EXECUTED / VERIFIED / UNVERIFIED / BLOCKED.
