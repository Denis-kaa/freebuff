# AUDIT_REPORT.md — Отчёт для аудита приложения «Печатник»

> **Дата:** 2026-09-23 · **Базовый коммит кода:** `3583b55` (master, origin/Denis-kaa/freebuff)
> **Назначение:** вводный документ для независимого аудита. Сопровождается промптом
> аудитора (`AUDIT_PROMPT.md`) и архивом `pechatnik_audit_2026-09-23.tar.gz`.
> Все утверждения — факты репозитория и живой верификации; ничего не приукрашено.

---

## 1. Идентификация

| Поле | Значение |
|---|---|
| Приложение | «Печатник» — операционная система типографии (кассовый каталог, детерминированные калькуляторы, конвейер производственных заданий, Communication Hub, Reports Hub) |
| Бизнес-контекст | действующая типография в Нефтеюганске (ХМАО), владелец — Денис |
| Развёртывание | сервер whimco: `/opt/printcalc` (прод-данные), `/opt/freebuff` (репозиторий платформы Workspace OS) |
| Сервисы | `printcalc-web.service` (:8300, FastAPI/uvicorn) · `reports-hub.service` (:8310, генератор отчётов) — оба systemd, enabled |
| БД | SQLite (`/opt/printcalc/data/printcalc.db`); схема — аддитивные миграции в `db.py` |
| Лицензия/приватность | внутренний контур; прайс и клиентские данные не публикуются |

## 2. Стек и окружение

- **Python 3.11+**, зависимости сознательно минимальны (`pyproject.toml`): `fastapi>=0.110`, `uvicorn>=0.27`, `jinja2>=3.1` (extras: `web`), `httpx>=0.27` (`test`/`telegram`), `PyYAML>=6` (`rules` — без него loud-ошибка по контракту S0). Runtime-deps core = `[]`.
- **Качество:** pytest (481 тест), mypy (strict-режим по проектным правилам, clean), golden-тесты калькуляторов с независимой деривацией ожиданий.
- **Фронтенд:** server-rendered Jinja2 + vanilla JS (12 модулей, без сборки), mobile-first.
- **Инфраструктура:** `deploy/*.service` шаблоны юнитов; cron-поллер автодеплоя (`scripts_01/auto_deploy.sh`, каждые 5 мин) + post-merge хук + автогенерация Reports Hub (`scripts_01/regen_reports_hub.sh`, гвард по HEAD-stamp).

## 3. Архитектура (два пакета)

```
printcalc/src/
├── printcalc/            # библиотека домена — чистая, без веба
│   ├── calculators/      # 8 портов калькуляторов: digital, wide, riso,
│   │                     #   sign, tablichki, cnc, design, cost
│   │                     #   конвейер каждого: config → spec → compute → golden
│   ├── engine/consumption/  # расход материала: рулон/лист, поворот, SHEET_NESTING
│   └── assistant/
└── printcalc_web/        # FastAPI-приложение
    ├── api.py            # 78 роутов (FastAPI router)
    ├── store.py          # вся бизнес-логика доступа к данным (SQLite)
    ├── db.py             # схема + аддитивные миграции (PRAGMA table_info-guard)
    ├── parser.py         # детерминированный парсер v2 свободного текста
    │                     #   (словари + regex, БЕЗ LLM — сознательное решение)
    ├── rules/            # Smart Order: engine.py (RuleVerdict) + packs/*.yaml
    ├── mail_poller.py    # Email-канал входящих (IMAP, зеркало telegram.py)
    ├── telegram.py       # Telegram-канал (поллер)
    ├── emailer.py / outbox.py / reply_templates.py  # исходящие + шаблоны R1/R2/R3
    ├── margin.py / pricing.py / orderbridge.py / p0_services.py / export.py
    └── templates/ + static/   # 10 экранов, mobile-first
```

**Принципы (проверяемые аудитом):**
1. **Детерминизм** — расчёты и тексты клиенту без LLM и без недетерминизма; каждое решение имеет источник (доки research/).
2. **Closed vocabulary** (ANTI-6b) — все словари закрытые: единицы (`UNIT_CATALOG`), шаблоны (`REPLY_TEMPLATES`), каналы (`INBOX_CHANNELS`), capabilities правил; неизвестный токен → loud-ошибка, не silent fallback.
3. **Contract first / additive** — миграции только добавляют; «распознать ≠ предложить»: ничего не попадает в заказ без подтверждения оператора (`auto=False`).
4. **Immutable snapshot** — сметы хранят снимок цен на момент создания.

## 4. Функциональная карта (что готово)

| Блок | Состояние | Где смотреть |
|---|---|---|
| Клиенты, материалы, сметы, заказы | ✅ этапы 1–2 | `store.py`, экраны clients/materials/estimates/orders |
| Consumption engine (рулон+лист, поворот, nesting) | ✅ этап 3–3b | `engine/consumption/`, 6 тестов |
| Производство (задания, QC-гард, чек-листы OP-01…22) | ✅ этап 4 | production.html/js |
| Склад (ledger, резерв → автосписание) | ✅ этап 5b | materials |
| Communication Hub: Telegram + Email + ответы с шаблонами R1/R2/R3 | ✅ этап 6 + 6b + 20 | telegram.py, mail_poller.py, inbox |
| Кассовые услуги P0 (CSV round-trip), подсказки R5/R10 | ✅ этапы 8–9 | price_list |
| Калькуляторы 8/8 (golden-паритет с legacy) | ✅ этапы 7,10a–10c | calculators/* |
| Smart Order S0–S6 (пак правил → нормализатор → RuleVerdict → API → UI → мост в калькулятор) | ✅ закрыт 09-16 | rules/, PHASE_RULES_R*_REPORT |
| Ценовой слой: каскад района A–E, runtime-прайс `data/wide_prices.yaml` (правка без кода) | ✅ | wide_prices.template.yaml |
| Единицы измерения сквозь заказ + размерный ввод «наклейка 20 на 30» | ✅ 09-21 | store/parser, PHASE_UNITS_REPORT |
| Reports Hub (Apple-style отчёты, diff, token-гейт :8310, автогенерация) | ✅ H1–H6 | services_08/reports_hub (вне архива, см. §8) |
| Учебник новичка (18 файлов, ~4 900 строк) + карточки материалов и машин до грейда A | ✅ текст; фотобанк 30/47 | учебник/ |
| Payment Hub (TestAdapter → TBank), приём файлов | ⏳ не начато | — |

## 5. Верификация на дату отчёта

| Проверка | Результат |
|---|---|
| `pytest tests/ -q` (printcalc) | **481 passed**, 2 warnings (SyntaxWarning из зависимостей) |
| `mypy src/printcalc_web/ --ignore-missing-imports` | Success: no issues found in 22 source files |
| Golden-паритеты (независимая деривация) | визитка 100 шт = 563.83 ₽ · буква 40 см = 539.63 ₽ · короб = 18 305.85 ₽ — живой расчёт совпал до копейки |
| Живой смоук прод-сервера | шаблоны ответов + render по message_id; кейс «наклейка 20 на 30» → позиция+размер; сервисы active |
| Объём кода | 14 944 LOC (src) + 7 940 LOC (тесты), 116 py-файлов, 78 API-роутов |

## 6. Операционные параметры

Env-переменные (имена; **значений в архиве нет** — задаются в systemd-юнитах на сервере):

```
PRINTCALC_DB              PRINTCALC_TG_TOKEN / PRINTCALC_TG_ADMIN
PRINTCALC_IMAP_HOST / _PORT / _USER / _PASSWORD / _FOLDER / _ENABLED / _POLL_SECONDS
PRINTCALC_SMTP_*          (исходящие, emailer.py)
REPORTS_HUB_TOKEN         (гейт :8310)
```

Каналы TG и IMAP — код готов, **выключены по умолчанию**: без кредов поллеры стартуют в no-op режиме (тихий выход, приложение работает).

## 7. Известные ограничения и риски (честно)

1. **Аутентификация UI** — веб-интерфейс рассчитан на внутренний контур (локальная сеть/VPN); отдельной системы логинов нет. Для публичного доступа требуется слой auth — сейчас это осознанное ограничение MVP.
2. **Секреты** — только env юнитов на сервере; в репозитории их нет (проверяемо grep). Бэкапы БД — на усмотрение владельца, автоматического бэкапа нет.
3. **Парсер** — детерминированный (словари+regex); покрытие ограничено словарями, расширение — по REGISTER-FIRST протоколу. LLM сознательно не используется.
4. **Цены части позиций** — грейды B/C (модель рынка, не локальная фиксация); правятся в Excel/CSV без кода.
5. **Приём файлов** (макеты PDF/TIFF) — не реализован; вложения писем не принимаются.
6. **Payment Hub** — не начат (TestAdapter по промту 4).
7. **site/ Reports Hub** — генерируется на диске, вне git; восстановление = регенерация.
8. **SQLite** — однозаходная БД; при многопользовательской нагрузке потребуется переезд на клиент-серверную СУБД.

## 8. Состав архива

**Включено** (≈4 МБ, tar.gz):

| Путь | Что это |
|---|---|
| `printcalc/` | весь код (src, tests, docs, scripts, pyproject, шаблон прайса) — **без** `.venv`, `__pycache__`, кэшей, `data/` (живая БД) |
| `research/` | 20 файлов полевого исследования (методология, компании, прайсы района, интенты, схема заказа, правила диалога, MVP) |
| `промт_печатник*.md` (1–10), `ПРОМПТ_..._КОНСОЛИДАЦИЯ_v3` | ТЗ-цепочка: 10 поколений спецификаций |
| `РОАДМАП_v5/v6/v7`, `RESEARCH_ADOPTION_PLAN`, `PROJECT_STATUS_REPORT` | планы и сводки этапов |
| `PHASE_*_REPORT.md` (24 файла) | отчёты каждого этапа с верификацией |
| `учебник/*.md` | текст учебника (18 файлов) — **без** `images/` (44 МБ фото; текст самодостаточен) |
| `BUSINESS_RULES`, `OPERATIONS_CATALOG`, `QUESTION_FLOW`, `SALES_SCRIPT`, `UPSELL_RULES`, `TERMS_GLOSSARY`, `MATERIAL_MODEL`, … | предметные доки |
| `AUDIT_REPORT.md`, `AUDIT_PROMPT.md` | этот отчёт + промпт аудитора |

**Исключено** (и почему): `worktree/`, `worktree_wf/`, `*.source.zip` (824 МБ — legacy-исходники, портированы в golden-тесты), `printcalc/.venv` (113 МБ), `data/` (живая БД с персональными данными клиентов — НЕ подлежит выгрузке), `учебник/images/` (44 МБ), `HTML/` (генерат), `reports_hub site/` (регенерируется).

**Не входит, но доступно отдельно:** `services_08/reports_hub` (генератор отчётов платформы) и `deploy/` юниты — по запросу; живая БД — только выгрузкой владельца на месте.

## 9. Воспроизведение верификации

```bash
cd printcalc
python3.11 -m venv .venv && .venv/bin/pip install -e '.[web,test,rules]'
.venv/bin/python -m pytest tests/ -q          # ожидание: 481 passed
.venv/bin/python -m mypy src/printcalc_web/ --ignore-missing-imports
.venv/bin/python -m uvicorn printcalc_web:app --port 8300   # без БД/кредов стартует в degraded
```

---
*Отчёт подготовлен агентом (Buffy/Freebuff); все численные утверждения воспроизводимы командами §9.*
