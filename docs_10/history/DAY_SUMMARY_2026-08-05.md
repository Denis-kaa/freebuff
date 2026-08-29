# Day Summary — 2026-08-05

**Project:** Freebuff v5.91.0
**Сессий за день:** 1 (автономная сборка пайплайна + боевая задача interior_planner)
**Автор:** Buffy (AI assistant)

> **TL;DR (читается за 90 секунд):**
> 1. **v5.89.0** — CON-33: single-instance backoff (дешёвый pgrep pre-check вместо слепого спавна tmux ~90s на cron-тик) + вычистка очереди (recover running/, requeue failed/ → 6 задач в user/) + watcher `wait_and_dispatch_all.sh` (мост «закрыл сессию → сразу прогнал очередь»).
> 2. **v5.90.0** — CON-35: backoff-cooldown поверх pgrep (счётчик подряд идущих занятых тиков в мете файла + TG-уведомление ОДИН раз при пороге, не каждый тик).
> 3. **v5.91.0** — боевая задача **interior_planner**: восстановлен Expo-каркас из .bak-снапшота в каноническое `projects_17/interior_planner/` (node_modules не копировался — диск 100%; sha256 10/10 байт-идентичность) + роль `interior_consultant` v3.1.0 зарегистрирована через пайплайн (`interior_consultant_register.py`, exit 0, model=gemini-2.5-flash).

---

## ✅ Выполненные задачи (список)

| # | Задача | Краткое описание | Релиз |
|---|--------|------------------|-------|
| 1 | **CON-33 — single-instance backoff** | `_live_instance_busy()` — дешёвый pgrep pre-check (мс) вместо слепого спавна tmux+wait ~90s каждый cron-тик; backoff-пропуск задачи (не двигается/не теряется/не фейлится), `**Deferred At:**` аудит-метка, `dispatch_all` прерывается на занятости, `main()` честная сводка | v5.89.0 |
| 2 | **Вычистка очереди** | Зависшая `running/` (libc-ошибка pre-v5.88.0) → recovered в `user/`; 3 задачи из `failed/` → requeued как pending. Итог: user/ = 6, running/ = 0, failed/ = 0 | v5.89.0 |
| 3 | **Watcher `wait_and_dispatch_all.sh`** | Отвязанный `setsid nohup`-процесс: опрашивает pgrep каждые 10s, после 3 стабильных free-проверок запускает `--all --no-tg`; heartbeat 600s; race-safety-net = CON-33 pre-check в самом диспетчере | v5.89.0 |
| 4 | **CON-35 — backoff-cooldown + TG один раз** | `**Backoff Streak:**` в мете файла (переживает cron-процессы) + `_bump_backoff_streak()` + порог `--backoff-notify N` (default 6 ≈ 30 мин) → TG-уведомление ОДИН раз (`**Backoff Notified:** true`); `N=0` = выключено; флаг notified ставится ТОЛЬКО при реальной отправке TG; `_reset_backoff_streak()` при освобождении | v5.90.0 |
| 5 | **interior_planner: восстановление Expo-каркаса** | `rsync -a --exclude node_modules` из `.bak.20260803T070807985465/` → `projects_17/interior_planner/interior_planner_app_expo/` (каноническое место по workspace_registry «Работа»); инвентарь совпал с v5.49.0 (Canvas2D 269 / RoomEditor 402 / roomStore 156 / domain 78 / App 15 + knowledge_base 3475B); **sha256 10/10 байт-идентичность**; вложенный `.git` + транзиентные логи удалены (иначе gitlink в родительском репо) | v5.91.0 |
| 6 | **interior_planner: регистрация роли через пайплайн** | Роль `18_interior_consultant.md` v3.1.0 → canonical `projects_17/interior_planner/roles/`; прогон `interior_consultant_register.py` (sibling-workspace, locator-based) → exit 0: roles `['developer','interior_consultant'***REMOVED***`, routing `[vision,reasoning,plan,explain,multimodal***REMOVED***`, missing `[***REMOVED***`, SmartRouter → `gemini-2.5-flash` | v5.91.0 |
| 7 | **Верификация workspace_registry** | `seed_defaults()`: путь `projects_17/interior_planner` больше не в missing (missing только buffy-playground_19, как и было); drift §5.22 — историческое свидетельство, не переписывалось (CAN-16) | v5.91.0 |
| 8 | **Синхронизация версий** | TASK.md / BUFFY_PROJECT.md / CHANGELOG.md согласованы на v5.91.0 (BUFFY_PROJECT был дрифт v5.88.0 → v5.91.0); `M BUFFY.md` — pre-existing v5.74.0 Clarification, не правка сессии | v5.91.0 |

---

## 📚 Новые уроки (CON)

| Урок | Суть |
|------|------|
| **CON-34** | Дешёвый pre-check (pgrep, мс) вместо слепого спавна при single-instance; backoff ≠ таймер, а дешёвый сигнал занятости; `--all` обязан break'аться на занятости |
| **CON-35** | «Уведомить один раз» ≠ «поставить флаг один раз» — флаг ТОЛЬКО при реальной отправке; `threshold=0` = валидное «выключено» (guard обязателен); streak в мете файла, а не в памяти процесса |
| **CON-36** | Восстановление из .bak: node_modules не восстанавливать вслепую (диск 100%, перегенерируем `npm install`); регистратор-пайплайн может жить в sibling-workspace (`.pyc` в `__pycache__` = улика, не источник); проверка успеха = 3 независимых сигнала (прогон пайплайна + BlueprintCorpus load + seed_defaults) |

---

## 🔬 Verify Gate (2026-08-05)

- **Тесты:** test_prompt_dispatcher + test_multi_turn_dispatcher + test_prompt_queue = **60 passed** (CON-35); 101 passed с telegram_bot (1 failed + 8 errors — документированная хроническая fixture-проблема с v5.84.0, НЕ регрессия).
- **Live-verify CON-33:** `_live_instance_busy()` = True при живой сессии; `--once --no-tg` → мгновенный backoff (~0s вместо ~90s спавна).
- **BlueprintCorpus (canonical seed):** roles `['developer','interior_consultant'***REMOVED***`, missing `[***REMOVED***`.
- **SHA256-сверка:** 10/10 файлов байт-идентичны .bak (App.tsx + 5 src + package.json + app.json + tsconfig.json + package-lock.json).
- **drift_check / consistency_check:** только pre-existing замечания (CAN-12 deferral, test-counter расхождение), не регрессии.
- **Код-ревью:** 3 набора × 2-3 раунда — все SHIP.

---

## 📊 Итог дня

**Progress:** 🔥 HIGH — 3 релиза (v5.89.0 → v5.91.0), 3 новых урока (CON-34/35/36), боевая задача interior_planner восстановлена + роль зарегистрирована через пайплайн, очередь чистая (6 задач ждут освобождения инстанса).

**Open work:** watcher `wait_and_dispatch_all.sh` (PID 780) ждёт закрытия живой сессии → 6 задач из `user/` выполнятся `--all --no-tg`; `npm install` + `npx tsc` для Expo-каркаса (ждёт места на диске — 100% заполнен); promotion роли в canonical blueprints_v3 (HANDOVER Phase E — вне скоупа Freebuff-стороны).

**Health:** verify-gates соблюдены; queue: pending=6, running=0, failed=0, done=0.
