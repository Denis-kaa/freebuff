# ADR-022: Server-first sync triangle (телефон ↔ GitHub ↔ whimco)

- **Дата:** 2026-09-05
- **Статус:** ✅ Accepted/Implemented (проверен живой сессией 2026-09-05)
- **Связи:** PROJECT_RULES §5.1, LESSONS CON-69, `docs_10/runbook/SYNC_RUNBOOK.md`, ADR-010 (Remote Sync — TG-релей, другая плоскость), ADR-017 (Unified Workspace Model)

## Context

Платформа живёт на трёх узлах: телефон (Termux, `~/freebuff`), GitHub (`Denis-kaa/freebuff`), сервер whimco (`/opt/freebuff` + прод-копии проектов в `/opt/<project>`). До 2026-09-05 синхронизация была ad-hoc: сервер отставал от базы на десятки коммитов, серверный WIP (модули, промты, тесты) существовал только на сервере и был невидим для других узлов; мобильный gh-токен был отозван, что блокировало push с телефона. Живая сессия выявила риск: `git checkout -f -B` на сервере молча затёр бы modified-tracked-файлы и оставил бы untracked-WIP (plugins_04, whim_store + 5 тестов, 8 промтов, torrent_dl_web) невидимым.

## Options

1. **Только телефон → GitHub (телефон-centric):** сервер — чистый деплой-таргет. Отклонено: серверная работа теряется, нарушает принцип Single Source of Truth (AGENTS.md §1).
2. **RSync/unidirectional mirror:** быстро, но без истории коммитов и без bidirectional-потока; конфликты неразрешимы. Отклонено.
3. **Git-треугольник server-first (выбрано):** все проекты создаются и живут на whimco; GitHub — общая база; телефон — мобильный узел разработки. Любой WIP обязан попасть в `master` в тот же заход.

## Decision

Принять правило **Server-first** (PROJECT_RULES §5.1) с механикой:

- **GitHub = single source of truth**; узлы синхронизируются только через git (`fetch` + `checkout -f -B`, не `pull`).
- Сервер: cron-поллер `scripts_01/auto_deploy.sh` (каждые 5 мин) + post-merge hook — проверено живым pull `a402f8f → 9dbae43`.
- Телефон → сервер emergency-канал: git-bundle через SSH (scp), сервер пушит в GitHub — проверено (116M full bundle + 30K incremental).
- Прод-копии проектов (`/opt/teenfreelance`) поддерживаются в byte-parity с контейнером в базе (нормализация CRLF — 58 файлов).
- Secret-hygiene перед `git add -A` (реальный кейс: Google `client_secret` в `torrent_dl_web/credentials.json` → gitignore до коммита).

## Rationale

- Соответствует архитектурным принципам: Single Source of Truth (GitHub), Backward Compatibility (addivity через git-merge, без переписывания), Observability (история коммитов + autodeploy-лог).
- Устраняет класс потерь «WIP только в одном месте» (CON-69) и класс рассинхрона прод-копии с контейнером (CRLF-кейс TeenFreelance).
- Не требует новой инфраструктуры: используется существующий git + SSH + cron.

## Consequences

- (+) Любая работа на любом узле воспроизводима с любого другого узла из базы.
- (+) Прод-копии перестают «дрейфовать» от кода в базе.
- (−) Дисциплина: перед hard-checkout обязательна проверка WIP (иначе потери — см. CON-69 §2).
- (−) `pmos_*`/`profile-site*`-нейминг WIP-директорий теперь в базе → 18 известных naming-violations в consistency_check до их реорганизации (зарегистрировано, не маскировать).
- (→) Mobile gh-токен отозван: push с телефона работает через PAT в credential-store; интерактивный `gh auth login` — отложено (не блокирует).
