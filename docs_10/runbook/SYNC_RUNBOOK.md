# SYNC_RUNBOOK — Server-first sync (phone ↔ GitHub ↔ whimco)

> **Статус:** ACTIVE · операционный manual правила «Server-first» (PROJECT_RULES §5.1, LESSONS CON-69, ADR-005).
> **Дата:** 2026-09-05 · проверен живой сессией (полный треугольник поднял `c60bac5` → `a402f8f` → `9dbae43`).

---

## 0. Правило одной строкой

**Все проекты живут и создаются на сервере whimco (`/opt/freebuff`). Ресёрч/разовые задачи можно вести на телефоне, но результат обязан попасть в общую базу (git master) в тот же заход. WIP, существующий только в одном месте, — нарушение правила.**

Инфраструктура: три узла образуют git-треугольник.

| Узел | Путь | Роль |
|---|---|---|
| Телефон (Termux) | `~/freebuff` (project root сессии) | мобильная разработка, аудиты, ресёрч |
| GitHub | `github.com/Denis-kaa/freebuff` (branch `master`) | общая база (single source of truth) |
| Сервер whimco | `/opt/freebuff` (+ соседние `/opt/<project>` для деплоев) | канонический дом проектов, runtime |

Аутентификация:
- **Телефон → whimco:** SSH-алиас `whimco` (конфиг Termux `~/.ssh/config`; ключ `id_ed25519_whimco`). Всегда: `timeout N ssh -o ControlMaster=no -o ControlPath=none -F /data/data/com.termux/files/home/.ssh/config whimco '...'`.
- **GitHub push:** работает с телефона (`credential.helper store`, `/root/.git-credentials`; локальный override в `.git/config`: пустой helper + `store` — см. §4 Troubleshooting) и с сервера (`/root/.git-credentials`, `git config --global credential.helper store`).
- **Сервер → GitHub fetch:** только HTTPS:443 (порт 22 к GitHub закрыт).

---

## 1. Нормальный цикл (телефон → база → сервер)

```bash
# 1. На телефоне: коммит + пуш
git add <scoped paths> && git commit -m "..." && git push origin-https master

# 2. На сервере: подтянуть (cron делает это сам каждые 5 мин; вручную — так)
ssh whimco 'cd /opt/freebuff && bash scripts_01/auto_deploy.sh pull'
```

`scripts_01/auto_deploy.sh` (уже установлен, cron-маркер `# freebuff-autodeploy`, лог `/var/log/freebuff-autodeploy.log`):
- cron-поллер каждые 5 минут: `git fetch` + fast-forward `master`;
- post-merge hook выполняет deploy-шаги (`DEPLOY_CMD`, по умолчанию пуст);
- `.env`, `data_13/context.db`, `context_12/events.db` — gitignored, pull их не трогает.

## 2. Нормальный цикл (сервер → база → телефон)

Серверный WIP (новые модули, промты, фиксы) коммитится **на сервере** и пушится; телефон стягивает:

```bash
# На сервере
cd /opt/freebuff && git add -A && git commit -m "wip(server): ..." && git push origin master

# На телефоне
git fetch origin-https && git checkout -f -B master origin-https/master
```

## 3. Emergency: телефон не может push/pull (нет сети/токена)

Канонический путь из сессии 2026-09-05 — **bundle через SSH**:

```bash
# 1. Полный bundle локально (если сервер не имеет базы коммита) или инкрементальный
git bundle create /tmp/sync.bundle --all                # полный (~116M)
git bundle create /tmp/sync.bundle <base>..master       # инкремент (~30K)

# 2. Передача + импорт на сервере
scp /tmp/sync.bundle.gz whimco:/tmp/
ssh whimco 'cd /opt/freebuff && git bundle verify /tmp/sync.bundle && \
  git fetch /tmp/sync.bundle refs/heads/master:refs/heads/from-phone && \
  git checkout -f -B master from-phone && git branch -D from-phone && \
  git push origin master'                                # сервер затем пушит в GitHub

# 3. Телефон после восстановления сети: git fetch origin-https && git checkout -f -B master origin-https/master
```

⚠️ `git checkout -f -B` на сервере **перезаписывает modified-tracked-файлы**. Перед hard-checkout убедиться, что серверный WIP закоммичен/застэшен. Правило бэкапа перед изменениями — `SERVER_ACCESS_WHIMCO.md` §3/§4 (не удалять ничего, бэкап `context.db`/`events.db`/`.env` перед операциями).

## 4. Troubleshooting

| Симптом | Причина | Fix |
|---|---|---|
| `remote: Invalid username or token` с телефона | мёртвый gh-токен перехватывает credential-chain (`gh auth git-credential` стоит раньше `store`) | `git config --local credential.https://github.com.helper ""` + `--add ... store`; живой токен — в `/root/.git-credentials` сервера |
| `could not read Username for 'https://github.com'` на сервере | нет `/root/.git-credentials` | записать `https://USER:TOKEN@github.com` (chmod 600), `git config --global credential.helper store` |
| `gh auth status` → token invalid (телефон и сервер) | токены 2026-07 отозваны | не критично: git-push идёт через PAT в `.git-credentials`; `gh auth login` — только интерактивно, отложить |
| SSH виснет | мёртвый ControlMaster | всегда `-o ControlMaster=no -o ControlPath=none` + `timeout` |
| push отклонён (non-fast-forward) | параллельный коммит на другом узле | `git fetch` → `checkout -f -B master origin[-https]/master` только БЕЗ локальных незакоммиченных нужных изменений; иначе merge/rebase |
| CRLF-«различия» между /opt/<project> и контейнером в базе | Windows-происхождение исходников | `sed -i 's/\r$//'` по текстовым расширениям на ОБЕИХ сторонах (см. сессию 2026-09-05: TeenFreelance, 58 файлов) |

## 5. Инварианты

1. **Ничего не удалять** в `/opt/freebuff` без явного указания пользователя (SERVER_ACCESS_WHIMCO.md §4.1).
2. Бэкап `data_13/context.db`, `context_12/events.db`, `.env` перед любыми деструктивными операциями (`/opt/freebuff-server-backup-<TS>/`).
3. Обновление серверной копии — только `git fetch` + `checkout -f -B` (не `pull`).
4. Секреты в git не попадают: перед `git add -A` на сервере проверять `credentials.json`/`.env`-подобные файлы (кейс 2026-09-05: Google `client_secret` в `torrent_dl_web` — добавлен в `.gitignore` ДО коммита).
5. WIP любого узла обязан попасть в базу в тот же заход (CON-69) — «потерять серверный WIP hard-checkout'ом» = нарушение правила, а не сбой.

## 6. Cross-links

- `docs_10/core/PROJECT_RULES.md` §5.1 — правило Server-first (канон)
- `core_02/LESSONS.md` CON-69 — урок «sync-before-hard-checkout»
- `docs_10/decisions/DECISIONS.md` ADR-022 — решение о топологии синхронизации
- `SERVER_ACCESS_WHIMCO.md` (Termux FS, вне репо) — доступ к серверу
- `scripts_01/auto_deploy.sh` — серверный pull-механизм
