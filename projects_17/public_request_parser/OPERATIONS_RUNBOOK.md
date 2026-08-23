# OPERATIONS_RUNBOOK — эксплуатация Public Request Parser (P11)

> **Статус:** operational draft — scheduler и backoff реализованы; live-эксплуатация
> с постоянным polling — после G7 (runbook dry-run + наблюдение оператором).
> **Дата:** 2026-08-23

## 1. Роли и режимы

| Режим | Команда | Назначение |
|---|---|---|
| Офлайн срез | `python -m app.cli --once --fixture fixtures/rss/sample_rss.xml --db parser.db` | Проверка pipeline без сети |
| Canary | `python -m app.cli --canary --source trudvsem --db parser.db --required "python" --limit 5` | Один живой срез с отчётом |
| Canary HH | `PRP_HH_APP_TOKEN=... python -m app.cli --canary --source headhunter ...` | То же, источник HH (секрет из env) |
| Scheduler | `python -m app.cli --schedule --source trudvsem --db parser.db --interval 60` | Постоянный polling-цикл (P11) |
| Maintenance | `python -m app.cli --maintenance --db parser.db` | TTL cleanup + backup `.db.bak` |

## 2. Scheduler-поведение (P11)

- каждый цикл = один срез `run_canary` (fetch → normalize → store → match → dry-run delivery);
- интервал — `--interval` (нижняя граница 5 сек);
- при сбое — экспоненциальный backoff (base=interval×0.1, factor=2, cap 300 с);
- каждый сбой алертится в stderr (`[prp-ops:warning***REMOVED***`); успешные итерации логируются;
- после успеха backoff сбрасывается.

## 3. Известные ограничения (честно)

- Delivery — dry-run (SENT не реальный): Telegram live отключён до отдельного
  policy-решения (P9/P17).
- Alerting — stderr-хук; Telegram/email-алерты — после G7.
- Polling cadence не ниже `--interval`; система не обходит rate limits источников;
  `SourcePolicy.can_poll` и статус `ALLOWED` проверяются адаптерами на каждом срезе.

## 4. Процедуры

### 4.1. Ежедневный мониторинг (оператор)

```bash
# смотреть циклы
python -m app.cli --schedule --source trudvsem --db parser.db --interval 300 --limit 10
# проверить размер БД и бэкап
ls -la parser.db* ; python -m app.cli --maintenance --db parser.db
```

### 4.2. Сбой источника

1. Ошибка в логе (`fail_streak` растёт, backoff увеличивается);
2. Проверить статус API вручную: `curl -s <endpoint>?limit=1`;
3. Если источник мёртв >1 часа — `Ctrl+C` (graceful stop), отключить источник
   через **исключение из `--source`** (конфиг), продолжить остальные;
4. Зафиксировать в STEPS (issue log).

### 4.3. Инцидент секретности

- `hh/info.md` — НЕ коммитится (в `.gitignore`); если попал в git — немедленно
  rotate Client Secret на dev.hh.ru, удалить из истории (filter-branch/BFG),
  записать урок.

### 4.4. Резервное копирование

- `--maintenance` создаёт `<db>.bak` (online sqlite backup);
- перед обновлением кода всегда делать бэкап; проверка: открыть `.bak`
  и сделать `SELECT COUNT(*) FROM publications`.

## 5. Правила безопасности

- Никаких outbound к авторам публикаций;
- контакты/адреса из API не извлекаются адаптерами (fixture-проверка);
- полный текст — только с TTL (storage `expire_full_text`);
- secrets — только env (`PRP_HH_APP_TOKEN`), не в аргументах CLI и не в коде.

## 6. Связанные документы

- `POST_MVP_GATES.md` — статусы P10–P19 и gate-критерии (G7: unattended OK);
- `STEPS.md` — журнал фактических действий;
- `STORAGE.md` — TTL, backup, идемпотентность;
- `SOURCE_POLICY_MATRIX.md` — allowed/политики источников.