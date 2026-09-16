# PHASE_H6_REPORT.md — H6: systemd-юнит + деплой + смоук

> **Статус:** COMPLETE · **Дата:** 2026-09-16
> **Этап:** H6 потока B (Reports Hub) — ФИНАЛЬНЫЙ · РОАДМАП_v7 §7 · reports-hub-spec.md §10.3
> **Верификация:** 80 passed (без изменений кода — деплой-этап) · сервис active/enabled · смоук 401/200/cookie/zip 260 файлов/404

---

## 1. Что сделано

| Артефакт | Файл | Суть |
|---|---|---|
| Юнит (в репо) | `deploy/reports-hub.service` | Шаблон `printcalc-web.service`: `WorkingDirectory=/opt/freebuff`, `ExecStart=/opt/printcalc-venv/bin/python -m services_08.reports_hub serve --host 0.0.0.0 --port 8310`, `Restart=on-failure` (3с), `EnvironmentFile=/etc/default/reports-hub`; примечания про регенерацию вручную (по расписанию — вне v1) |
| Токен (серверно-локально) | `/etc/default/reports-hub` | `REPORTS_HUB_TOKEN=<secrets.token_urlsafe(32)>`, chmod 600 — вне репо по политике секретов (как PRINTCALC_WEB_DB в юните, но значением) |
| Сайт на проде | `services_08/reports_hub/site/` | Регенерирован `generate --all --platform`: 13 проектов · 231 док; `site/` в .gitignore (H3-решение) — перегенерация на деплое |
| Юнит на хосте | `/etc/systemd/system/reports-hub.service` | Скопирован из `deploy/`, `daemon-reload`, `enable --now` (symlink multi-user.target.wants — переживает ребут) |

## 2. Живой смоук (FACT, whimco, порт 8310)

```
systemctl is-active reports-hub → active (Main PID, 11.4 MB)
401 без токена → 401
index?token=…  → 200
печатник       → 200 (projects/adminka-pechatnik/index.html)
платформа      → 200 (platform/index.html)
cookie-вход    → Set-Cookie: rh_token=… (HttpOnly)
/download/zip  → 200, 260 файлов в архиве
неизвестная    → 404
journalctl     → «Started reports-hub.service … serve: http://0.0.0.0:8310/»
```

## 3. Решения по ходу (и почему)

1. **Токен в `/etc/default/reports-hub` (EnvironmentFile), не `Environment=` в юните** — юнит коммитится в репо, секрет не должен попасть в git; файл chmod 600, серверно-локальный (та же политика, что `data_13/missing_registry.yaml` и `data/wide_prices.yaml`).
2. **Юнит хранится в `deploy/` репо** — воспроизводимость деплоя на новом хосте: cp + daemon-reload + enable; правки юнита ревьюятся в git.
3. **Регенерация сайта — не в юните** (без ExecStartPost): генерация меняет файлы под живым сервером; в v1 регенерация ручная после pull (спека §10.3), таймер — позже (open question §13.2).
4. **0.0.0.0 вместо 127.0.0.1** — юнит продовый, аналог printcalc-web (:8300); доступ защищён token-гейтом (решение №16).

## 4. Эксплуатация (кратко)

```bash
# обновить и перегенерировать:
cd /opt/freebuff && git pull
/opt/printcalc-venv/bin/python -m services_08.reports_hub generate --all --platform
systemctl restart reports-hub   # не обязателен (HTML статичен), но сбрасывает zip-кэш в памяти

# токен (ротация):
nano /etc/default/reports-hub && systemctl restart reports-hub
```

## 5. Поток B завершён

Все этапы спеки §14 выполнены: H1 каркас → H2 extract → H3 рендер → H4 diff+summaries → H5 сервер+платформа → H6 деплой. Осталось из open questions (не блокирует): регенерация по расписанию, PDF-экспорт, RSS/TG-уведомление.
