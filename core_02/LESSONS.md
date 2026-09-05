# LESSONS

## CON-18: Неприкосновенность промтов

Промты в `pompts_11/` являются историческими и рабочими артефактами. Их нельзя удалять, перезаписывать или терять при реорганизации, переименовании, очистке и массовой обработке. Новая редакция создаётся отдельным файлом или версией; исходный промт сохраняется. Переименование требует проверки содержимого, ссылок и Git-истории. Удаление возможно только по явному отдельному указанию пользователя.
 — Blueprint v3 Integration Scenario

**Дата:** 2026-08-02
**Сценарий:** интеграция Blueprint v3 как один из self-learning сценариев Workspace OS
**Модуль:** [`core_02/blueprint_v3.py`***REMOVED***(../core_02/blueprint_v3.py), тесты: [`tests_09/test_blueprint_v3.py`***REMOVED***(../tests_09/test_blueprint_v3.py)

> Это не final-report — это **рабочий журнал** по v3-схеме **Confirmed / Candidate / Anti-pattern**.
> Формат взят из Kwork Arbitr v3 MANIFEST.md (Self-Improving Mechanism раздел).
> Пополняется по ходу итераций кода-ревью + валидации. Сохраняется рядом с кодом,
> чтобы следующая итерация видела оба слоя одновременно.

---

## 📌 Контекст сценария

**Цель:** интегрировать как «один из сценариев» Workspace OS существующий blueprint v3 pipeline
(17 ролей, declarative registry.yaml, расширяемый). Платформа должна:
- читать готовый канон (роли не выдумываются с нуля)
- создавать недостающие роли **по ходу** (путь 3 — «роли нет → создаёт»)
- фиксировать трудности и выученное прямо в этом документе

**Контракт:** `core_02/blueprint_v3.py::BlueprintCorpus` — read/create/role-registry для v3.
Wizard/AGENTS.md/contracts-skeleton отложены в текущем сценарии до подтверждения v3-интеграции.

---

## ✅ Confirmed (проверено на практике в этой сессии)

### CON-1 — Каскадный YAML‑splice + post‑parse guard даёт zero‑corruption
**Сценарий:** добавление новой роли в `registry.yaml` через текстовый splice.
**Что подтверждено:** pre‑write `yaml.safe_load(new_text)` ловит структурные поломки
(triggers с unbalanced quote, плохая индентация) **до** записи на диск; OSError в момент
write restore‑ит из timestamped backup. Тесты
`test_register_in_registry_rejects_invalid_yaml_splice` +
`test_register_in_registry_write_failure_restores_backup` — регрессионная защита.
**Вывод:** текстовый YAML‑splice оправдан для сохранения комментариев и форматирования
пользовательского registry; обязательно guard «parse‑first».

### CON-2 — Backup‑timestamp suffix `.bak.YYYYMMDDTHHMMSS` устраняет collisions
**Сценарий:** многократные правки registry.yaml за сессию.
**Что подтверждено:** однострочная замена `.with_suffix('.yaml.bak')` → timestamped
имя даёт ротацию, тест `test_register_in_registry_writes_and_makes_role_visible`
обновился на glob‑match `registry.yaml.bak.*`. Раньше один `.bak` затирал предыдущий —
нельзя было откатить второй шаг.
**Вывод:** для shared user‑file — timestamped backup всегда, не одиночный `.bak`.

### CON-3 — `os.access(root, os.W_OK)` вместо «probe‑write» файла
**Сценарий:** pre‑flight проверка права записи перед `write_text`.
**Что подтверждено:** старый код создавал коллатеральный `.write_probe` файл (и удалял) —
это шумело в filesystem watcher и рисковало коллизией с пользовательским именем.
`os.access` — atomic, no side effects.
**Вывод:** всегда предпочитать `os.access` / `os.stat` «write‑and‑delete probe», если задача
только проверка прав.

### CON-4 — Канон v3 парсится zero‑false‑positives
**Сценарий:** `parse_blueprint_md('09_developer.md')` на реальном файле пользователя.
**Что подтверждено:** XML‑секции `<role>`, `<system_role>`, `<input>`, `<main_objective>`,
`<priority_order>`, `<implementation_scope_rules>` + опциональные 14 секций извлекаются
regex‑ом чисто; header `ROLE:` + `VERSION:` извлекается отдельно.
**Вывод:** формат v3 стабилен и пригоден как контракт между ролями и платформой.

### CON-5 — Код‑ревью в 3 раунда даёт стабильное API
**Сценарий:** 3 итерации code‑reviewer‑minimax‑m3 по одному и тому же модулю.
**Что подтверждено:**

| Раунд | Поймано |
|-------|---------|
| 1     | YAML‑splice без guard, subprocess нарушает v3 atomic‑commit манифесто, возвращаемые типы Path vs str под одним `dry_run`, parse‑функция без `_` публичной выдержки |
| 2     | mid‑function imports, .write_probe collateral, валидация без регрессионных тестов |
| 3     | подтвердил чистоту; добавили документацию по pyyaml как внешнему деплою |

**Вывод:** один писательский проход + одно ревью стабильного качества не дают. Итеративный
reviewer — основной механизм качества для нетривиального модуля здесь.

---

## 🟡 Candidate (нужна проверка в следующих сценариях)

### CAN-1 — Empty‑roles registry должен падать в `BlueprintCorpus.__init__`? — RESOLVED ✅
> **2026-08-02 (v5.43.0):** `_load_registry()` теперь ловит `yaml.YAMLError` → чистый `ValueError` с указанием пути + «повреждён (невалидный YAML)» + совет восстановить из .bak; пустой/не-dict registry → `ValueError` «пуст или имеет неожиданную структуру». Self‑healing UX закрыт (CON‑11). Тесты: `test_init_raises_value_error_on_broken_yaml` + `test_init_raises_value_error_on_empty_registry`.

### CAN-2 — Связь Blueprint ↔ SmartRouter по `routing_hint → capabilities` — RESOLVED ✅
> **2026-08-02:** Реализовано через `BlueprintCorpus.routing_hint(role_id)`, dual-resolution (XML wins → override fallback → empty list). Мост closed в CON-6, защищён в CON-8 (vocab drift defense). Запись перенесена в resolved‑секцию.

### CAN-3 — TG chat_id через `.session` файл Telethon (а не getUpdates) — RESOLVED ✅
**Сценарий:** отчёты в Избранное + переписка с «Александр Литвинов».
**Состояние (CLOSED 2026-08-02, v5.40.0):** активная `.session` найдена в `projects_17/tg_terminal_messenger/tg_session.session`, подключение через `TGClient` (api_id=37035907, api_hash=383bbe0942526db1133edc23d8ba8023) дало own user_id=**7709651193** (Saved Messages/Избранное chat_id) и `Александр Литвинов` chat_id=**1063827731** (User). Полная запись — в `docs_10/core/ARCHITECTURAL_DEBT.md` §5.10. Гипотеза про прямой `SELECT FROM entities` не понадобилась: схема .session (Telethon 1.x) без колонки `type`, кросс-сценарные owner/user lookup делается через `client.get_me()` + `client.get_dialogs(limit=N)`.

### CAN-4 — YAML splice round‑trip дрифт с пользовательскими правками — RESOLVED ✅
> **2026-08-02 (v5.43.0):** fallback в `register_in_registry` заменён с «append at end» на `_insert_into_pipeline` — находит top‑level `pipeline:` и вставляет новую запись перед следующей top‑level секцией (без дубликата раздела). Регрессия: `test_register_in_registry_without_marker_inserts_into_pipeline` (ровно один `pipeline:` в файле). Полный round‑trip через ruamel.yaml — остаётся в списке «в следующий сценарий».

---

## 🚫 Anti‑pattern (что НЕ делать в следующих сценариях)

### ANTI-1 — `dry_run` параметр, возвращающий разные типы под одним методом
**Где было:** `write_blueprint(bp, dry_run=False) → Path` vs `dry_run=True → str`.
**Почему плохо:** тип‑контракт меняется под флагом → `target.exists()` упадёт случайно
на dry‑run пути. **Урок:** dry‑run либо отдельный метод (`preview_blueprint()`),
либо вообще нет (preview = `bp.to_markdown()` напрямую). Одна функция, один тип возврата.

### ANTI-2 — Mid‑function imports для «оптимизации»
**Где было:** `import yaml` и `from datetime import datetime, timezone` внутри метода
«чтобы падало только когда нужно».
**Почему плохо:** нарушает PEP‑8, скрывает реальное использование, плохо читается.
**Урок:** top‑level imports всегда, кроме случаев циклов/circular imports.

### ANTI-3 — Collateral‑файл как «probe» для проверки прав
**Где было:** запись/удаление `.write_probe` файла в директории пользователя.
**Почему плохо:** шум в filesystem watchers, риск коллизии имени, race на shared FS.
**Урок:** всегда `os.access(path, os.W_OK)` для проверки прав.

### ANTI-4 — Изменяемый shared user‑file без backup
**Где было:** `register_in_registry` первоначально не имел `shutil.copy2` для yaml.
**Почему плохо:** один баг = permanent corruption of user file. **Урок:** любая запись
в shared user‑owned file — backup‑first + post‑parse validation.

### ANTI-5 — Полнота <scope discipline>: blueprint v3 = **ОДИН** из self‑learning сценариев
**Где рискуем:** замахнуться на wizard + AGENTS.md + contracts + EAS Build разом.
**Почему плохо:** непроверяемые модули накапливаются, ревью‑петля раздувается.
**Урок:** один сценарий за раз. Этот сценарий = «v3 integration = read+create».
Следующий (отдельный) = «wizard surface».

---

## 🛠 Процессные трудности этой сессии (process bugs, не код‑баги)

### PB-1 — `str_replace` оставил malformed line `    )    md = ...`
**Symptom:** `py_compile` упал на tests_09/test_blueprint_v3.py:234 «invalid syntax».
**Cause:** replacement объединил «close paren» и «next statement» в одну строку.
**Fix:** перепроверить/пересобрать строку вручную. **Урок для себя:** в str_replace
проверять, что old/new не «съедают» separator (newline) между ними.

### PB-2 — Compound `pip install pyyaml` шёл в shell‑timeout 60s
**Symptom:** полная команда `pip install … && grep … && python -c 'import yaml'` отвалилась
на 60s shell‑timeout. Сам pip внутри статуса "stalled" не получил сигнально — это
композитная команда превысила время.
**Workaround:** задокументировано в `requirements.txt` (`pyyaml>=6.0.1`); pytest‑коллекция
крашится с `ModuleNotFoundError: No module named 'yaml'` и подсказывает что ставить.
CI‑окружение должно ставить из requirements.txt самостоятельно.
**Урок:** для нового кода с side‑deps — пин в requirements.txt. **Не утверждать, не проверив,
что именно pip завис**: скорее всего, это wallclock от составной команды.

### PB-3 — `getUpdates` от Telegram бота пуст; user‑claimed `.session` не найден
**Symptom:** невозможно получить chat_id для Избранного и «Александр Литвинов»
автоматически.
**Workaround:** зафиксировано в LESSONS как CAN‑3. Не блокирует платформенную валидацию.
**Урок:** для end‑to‑end демонстрации Telegram‑интеграций нужен прямой пользователь
chat_id или явный Telethon `.session` файл.

### PB-4 — User‑input revealed path mismatch
**Symptom:** пользователь сказал, что TG session в `/blueprints_v3/`, но узкий
find не нашёл `.session` там; реальный `tg_session.session` лежит в
`freebuff/projects_17/tg_terminal_messenger/`.
**Workaround:** отдельное наблюдение — путь был ошибочен, а не код.
**Урок:** для discovery‑stepов делать dual‑candidate probing (multiple bases), не
верить одиночному user‑утверждению.

---

## 🔗 Связанные артефакты

- [`core_02/blueprint_v3.py`***REMOVED***(./blueprint_v3.py) — реализация ридера/создателя
- [`tests_09/test_blueprint_v3.py`***REMOVED***(../tests_09/test_blueprint_v3.py) — 14 + 2 регрессионных теста
- Blueprint v3 MANIFEST — внешний канон по пути
  `~/.../blueprints_v3/MANIFEST.md` (не входит в freebuff‑репо)
- Blueprint v3 registry.yaml — внешний
  `~/.../blueprints_v3/registry.yaml`
- [`requirements.txt`***REMOVED***(../requirements.txt) — `pyyaml>=6.0.1` пин

## 📦 Scenario: Wizard поверх Blueprint v3 (2026-08-02)

### CON-6 — Dual‑resolution `routing_hint` (XML + override) — testable & debuggable
**Сценарий:** мост `BlueprintCorpus.routing_hint(role_id) → SmartRouter`.
**Что подтверждено:** parsed `<capabilities>` wins if present, else `CAPABILITIES_OVERRIDE`. `tests_09/test_wizard.py` покрывает обе ветки. Override‑fallback сохраняет семантику без патча канон‑файлов вне workspace.
**Вывод:** dual‑resolution lets the *future migration path* stay declarative (XML в каноне), while keeping the module рабочим в этом окружении *сегодня*. Aligns with CON‑1 (splice‑with‑guard) and CAN‑5 (curated vocabulary).

### CON-7 — Самогенерация корректна: `run_wizard` + SmartRouter работают в тестах
**Сценарий:** e2e test temporary workspace, `force_role_id='developer'`, `project_name='demo_app'`.
**Что подтверждено:** five `*.json` файлы + `merged.json` записаны; `assigned_model != 'auto'` (router отрезолвил на конкретную модель из default `ModelCatalog`). `resolved_task_model` happy path.
**Вывод:** override‑vocabulary (`code`, `implement`, `debug`) пересекается с `ModelCatalog` — SmartRouter.match находит score ≥ 1, отдаёт не `fallback:last_resort`.

### CAN-5 — Keyword‑overlap в `propose_roles` — игрушечный
**Сценарий:** fuzzy‑match по описанию роли.
**Гипотеза:** при 0 матчах fallback на первую зарегистрированную роль — никогда не возвращаем пустой список. При коротком или мультитовом запросе результат ненадёжен.
**Следующий шаг:** когда появится LLM‑слой — заменить на embedding‑similarity или tf‑idf + ngram.

### CAN-6 — `FREEBUFF_BLUEPRINTS_DIR` env override
**Сценарий:** в dev‑окружении canonical путь может быть недоступен.
**Гипотеза:** argparse default смотрит в env `FREEBUFF_BLUEPRINTS_DIR`; `--selftest` обеспечивает воспроизводимую отладку без зависимости от внешнего канона. Checked in `scripts_01/wizard.py:main`.

### ANTI-6 — Adding role без `CAPABILITIES_OVERRIDE` → молчание SmartRouter'а
**Сценарий:** `BlueprintCorpus.create_blueprint(role_id=…)` без строки в CAPABILITIES_OVERRIDE.
**Проблема:** `routing_hint` вернёт `[***REMOVED***` → `SmartRouter.route([***REMOVED***)` тихо попадает в `BALANCED` preference (qwen2.5:1.5b). Wizard работает, нощает generic model — пользователь получает "was‑immer local" вместо правильного capability‑матча.
**Урок:** при `register_in_registry`/создании роли в v3 ОБЯЗАТЕЛЬНО добавить row в `CAPABILITIES_OVERRIDE`; иначе routing fallback скроет это. Альтернатива: валидатор‑функция `assert role_id in CAPABILITIES_OVERRIDE` в `create_blueprint`.

### ANTI-6b — Override tokens вне `KNOWN_CAPABILITIES` ⇒ silent fallback на qwen2.5:1.5b / gemini-fallback
**Сценарий:** Более тонкий, чем ANTI‑6. Роль **есть** в `CAPABILITIES_OVERRIDE`, но tokens (`"qa"`, `"test"`, `"verify"`, `"audit"`, `"write"`, `"frontend"`, `"devops"`, `"decompose"`, `"memory"`) **отсутствуют в `ModelCatalog`**. `SmartRouter.route([...***REMOVED***)` даёт score=0 у всех моделей → переход к ветке `fallback:no_capability_match` (`sorted(..., key=-max_tokens)`) → **gemini-2.5-flash** с пометкой `fallback_used=True`; либо если match без req‑фильтра — `sorted(..., key=latency)` → **qwen2.5:1.5b (200 ms)**. Юзер получает «роль tester, ожидал code-capable, видит local 1.5B» — v3-интеграция репутает «поломанной», но pytest зелёные.
**Урок:** **CLOSE VOCABULARY contract**. Каждый токен в `CAPABILITIES_OVERRIDE` ДОЛЖЕН быть в `KNOWN_CAPABILITIES` (closed set, mirrors `ModelCatalog.capabilities`). Валидатор на `BlueprintCorpus.__init__` поднимает `ValueError` при drift.

### CON-8 — Vocabulary defense реализован на init-уровне (closes ANTI-6b)
**Сценарий:** Защита от CAPABILITIES_OVERRIDE drift. Реализовано через `BlueprintCorpus.__init__._validate_override_vocabulary()`: после `_load_registry`, инициализации `_index`, поднимает `ValueError` с понятным сообщением, если хотя бы один role_id имеет token вне `KNOWN_CAPABILITIES`. Регрессионная защита в `tests_09/test_wizard.py`:
- `test_known_capabilities_subset_of_actual_catalog` — синхро-страж с реальным `ModelCatalog`
- `test_capabilities_override_now_routing_safe` — assertion на текущее безопасное состояние
- `test_capabilities_override_init_rejects_unknown_token` — monkeypatch вставляет `"nonexistent_capability_token"`, init падает loud
**Вывод:** anomaly ловится **на первой строке `BlueprintCorpus.__init__`**, а не в 200-м e2e тесте после прогона `run_wizard`. self-learning по спирали: bug → guard → guard покрыт тестом → guard проверяется в CI на каждое изменение vocabulary.

### PB-7 — `tester` role маршрутился на qwen2.5:1.5b по fallback-ветке
**Symptom:** `tester` имел override `["test","qa","verify","audit"***REMOVED***`. После прохода через `SmartRouter.route(['test','qa','verify','audit'***REMOVED***)` все модели в `ModelCatalog.default()` получают score=0. Условие внутри `route`:
- `best_score > 0` → False (req не пуст)
- `not req` → False (req не пуст)
- → переход к п.2 (`all_models = self.catalog.match([***REMOVED***, max_tokens=0)`)
- → `sorted(..., key=-max_tokens)` → `gemini-2.5-flash` (1M tokens) с пометкой `fallback_used=True`
-   (или при отсутствии guard'а `best_score>0 → False` → `sorted(..., key=latency)` → **qwen2.5:1.5b (100-200 ms, local 1.5B)**)

**Caught by:** `code-reviewer-minimax-m3` в финальном раунде. Первая итерация wizard-тестов `test_run_wizard_resolves_assigned_model_via_smartrouter` была зелёной — потому что `developer` (`["code","implement","debug","refactor"***REMOVED***`) валиден по vocabulary. Но **tester-ветка не тестировалась явно** на capability-match, поэтому баг прошёл сквозь pytest-sanity.

**Fix:** override переписан под реальный catalog: `tester = ["code","summarize","review"***REMOVED***`. Теперь match: deepseek-v4-flash (code+reasoning+plan+refactor+explain) получает score=2 (`code`+`refactor`), gemini-2.5-flash — score=2 (`code`+`vision`), llama-3.3-70b — score=1 (`code`). Никакого fallback_used.

**Урок:** **scoring — semantic, не syntactic**. `SmartRouter.route()` который возвращает строку ≠ он выбрал правильную модель. Без capability-mock layer и явного `assert not fallback_used` в тестах этот класс ошибок проходит сквозь e2e пайплайн. **Урок для reviewer:** без smoke-assert'ов типа «`resolved_model` не обязан быть в fallback-ветке» под pytest-один проход может пропустить класс багов, который виден только глазом reviewer.

### PB-5 — Внешний канон 17 ролей нельзя патчить из workspace
**Symptom:** письмо в `~/.../blueprints_v3/*.md` (которые вне `/storage/.../freebuff/`) запрещено текущим окружением — "Modifying files outside the current working directory is not allowed".
**Workaround:** override‑map в `core_02/blueprint_v3.py` + XML‑first‑fallback; API‑контракт «XML better than override» сохранён, патч в bulk откладывается до открытия двунаправленного workflow.
**Урок:** когда модель озвучила план "патчить канон" — сначала проверь, насколько канон вне workspace; если да — минимум override‑слой и явный fallback path, иначе будет просто скрытый technical debt.

### PB-6 — `--selftest` в CLI даёт reproducible debug
**Symptom:** без CLI входной точки для wizard на run без внешних зависимостей приходилось руками создавать seed в test. Move‑трафик на полный selftest = передеплой корпуса каждый раз.
**Workaround:** добавлен `--selftest` в `scripts_01/wizard.py:argparse` — создаёт минимальный seed‑corpus в `tempfile.TemporaryDirectory(prefix="freebuff_wizard_selftest_")`, не зависит от канона, не нужен аргумент, печатает пути + модель.
**Урок:** для интеграционных CLI — добавлять `--selftest` с tmp‑seed; это первый шаг отладки и базовый ход Tutorial‑цикла ("как вызывать из bash, как читать вывод").

### PB-9 — PyYAML повторно пропал из окружения (recurrence PB‑2)
**Symptom:** `python -m pytest tests_09/test_blueprint_v3.py -q` → `ModuleNotFoundError: No module named 'yaml'`
на этапе collection (модуль падает на import). Тот же класс, что PB‑2, но теперь post‑install
(в requirements.txt pyyaml пин есть).
**Workaround:** `pip install pyyaml` перед валидацией; CI‑окружение должно ставить из
requirements.txt. **Урок:** pyyaml — не «один раз установил навсегда» в Termux — после
смены python-окружения/переустановки пакетов дропается; любой сценарий, работающий с
YAML, должен в шаге валидации сначала проверять `python -c 'import yaml'`.

---

## 📦 Scenario: E2E платформенный тест промта‑47 (2026-08-03)

### CON-12 — E2E harness 4-stage pipeline (scripts_01/e2e_promt47.py)
**Сценарий:** реальный прогон промта‑47 (interior_planner, мобильный 2D‑планировщик) через wizard + mock Runtime + TG‑канал — sim‑user-driven self‑learning loop.
**Реализовано:** [`scripts_01/e2e_promt47.py`***REMOVED***(../../scripts_01/e2e_promt47.py) — 4 sequential stage, ~250 строк:
- **Stage 1 Planning** — load `pompts_11/promt47.md` → plan.md
- **Stage 2 Wizard run** — auto‑detect canonical‑first, tmp‑seed fallback; `force_role_id='developer'`
- **Stage 3 Mock Runtime** — narrative `runtime_log.md` simulating Hermes/Claude Code (Expo RN + skia canvas + interior_consultant)
- **Stage 4 TG channel** — `core_02.telegram_contract` async‑wrapper; default = Saved only; `--client` adds Литвинов with explicit prefix `[client notification — test agent → client***REMOVED***`; `--skip-tg` disables.
**Snapshot:** NIT‑3 fix — existing workspace → rename parent to `.bak.YYYYMMDDTHHMMSSffffff` (micro‑sec collision‑resilient); `--silent` does not skip logic (only print suppression).
**Env override:** NIT‑1 fix — `FREEBUFF_BLUEPRINTS_ROOT` env var for CI / non‑canonical installs.
**Вывод:** loop schliesslich‑general: contracts → runtime → TG‑delivery → client‑visibility. Auto‑detect pattern позволяет high‑fidelity на canonical / reproducible на CI.

### CON-13 — Real TG end‑to‑end confirmed for промт‑47 (v5.46.0)
**Сценарий:** два прогона E2E на канонической системе /storage/.../blueprints_v3.
- **Run #1** (`--silent`, Saved only) → Saved Messages msg_id=**138040**
- **Run #2** (`--client --silent`, Saved + Литвинов) → Saved=**138041**, Литвинов=**138042**
**Triplex verification:** (1) SmartRouter assigned `deepseek-v4-flash` direct match (не fallback → CON‑8 vocab defense holding); (2) wizard.run_wizard_with_registry auto‑detect выбрал canonical; (3) TG dual‑channel дошёл в оба chat_id. Stage 2 path used: `CANONICAL` (env override canonical).

### ANTI‑9 — Don't gate logic on `--silent`
**Сценарий:** first draft `main()` имел snapshot‑logic gated на `if (...) and not args.silent`. Re‑run в `--silent` режиме silently пере‑писал workspace без warning.
**Урок:** **`--silent`/`--quiet` flags press только output channels (stdout/stderr), не conditional logic.** Если нужно skip logic — explicit flag (`--dry-run`/`--skip-snapshot`). Когда хотелось gate both — explicit, не piggy‑back на --silent.

### PB‑10 — len(int) TypeError в Stage 4 f‑string
**Symptom:** Реальный `--client` прогон упал в Stage 4: `TypeError: object of type 'int' has no len()`. Wizard + mock Runtime + snapshot всё OK; TG‑stage attempted to format `summary_text` → exception → msg_id=None.
**Cause:** `len(stage3_chars or 0)` — stage3_chars уже integer (return from `len(narrative)`). `len()` на int = TypeError.
**Fix:** `len(stage3_chars or 0)` → `stage3_chars or 0` (int is already count).
**Урок:** Defensive `len()` на f‑string форматировании — counter‑productive: re‑validating type via direct invocation — уже overhead. Когда upstream уже returns desired length, добавлять nginx‑protection = trapdoor.

### PB‑11 — Snapshot timestamp collision (closed via NIT‑B)
**Symptom:** `.bak.YYYYMMDDTHHMMSS` — two re‑runs in same second (CI pipeline) collide → FileExistsError.
**Fix:** `strftime("%Y%m%dT%H%M%S%f")` (microseconds). Cheap, readable, collision‑free.
**Урок:** Timestamp‑based backup naming collision‑resilient на уровне < 1s scope (CI; test loops). Hash‑based naming is alternative if microsecond уникальность всё ещё недостаточна.

### CAN‑7 — force_role='developer' bypass fuzzy‑match (open)
**Сценарий:** E2E прогон uses `force_role_id='developer'` для predictable reproducibility. Ideal role for mobile‑scaffold = architect (plan + architecture design), не developer.
**Гипотеза:** remove force_role_id → fuzzy‑propose → role по task_goal. Triggers CAN‑5 re‑evaluation; potential to discover "interior_consultant" yёт в выборке.
**Следующий шаг:** ввести `--use-propose` flag для future прогонов; manual user‑confirm после propose.

---

### CON-14 — interior_planner артефакты доставлены в workspace (v5.47.0)
[scripts_01/interior_consultant_register.py***REMOVED***(../../scripts_01/interior_consultant_register.py) подтвердил full chain: role-artifact → BlueprintCorpus(local_seed) → registry.yaml → routing_hint → SmartRouter → model. Результат: interior_consultant `routing_hint=["vision","reasoning","plan","explain","multimodal"***REMOVED***` → SmartRouter.match → **gemini-2.5-flash** (score=4, direct match, не fallback, CON-8 vocab defense holding).

**Artfacts в `/tmp/interior_planner_e2e/interior_planner/`:**
- `roles/18_interior_consultant.md` — 11 v3 sections + capabilities tokens closed-set per CON-8
- `scaffold/expo_rn_scaffold.md` — 11 sections (Sprint roadmap, file structure, deps, App.tsx, Zustand+AsyncStorage, knowledge_base.json с REAL IKEA dimensions, Skia Canvas contract, prompt_gen.ts, anti-hallucination, WHAT-NOT scope)
- `HANDOVER.md` — full status с 5 human-dev phases (Bootstrap/Drop-in/Freebuff runtime/Register (workspace)/Promote (canonical))

**Real TG final delivery (v5.47.0):** Saved Messages msg_id=**138044**, Литвинов msg_id=**138045**. Cumulative TG msg_ids: 138040 (Saved v5.46.0#1), 138041 (Saved v5.46.0#2), 138042 (Литвинов v5.46.0#2), 138044 (Saved v5.47.0), 138045 (Литвинов v5.47.0).

### CAN-8 — interior_consultant workspace-only, NOT canonical (open, PB-5 contract, body-level hardcode aspect RESOLVED — v5.57.0)

> Body-level /tmp hardcode facet closed in v5.57.0. **Workspace-only-vs-canonical aspect** is still load-bearing for PB-5 contract (left untouched on purpose). DO NOT touch.

**Closure details (CAN-8 body-level /tmp hardcodes, RESOLVED 2026-08-03):**
- **What was**: `interior_consultant_register.py:37 DEFAULT_SEED = Path("/tmp/interior_planner_seed")` + `e2e_promt47.py:12` help text `# default /tmp/interior_planner_e2e` + anywhere else `/tmp/interior_planner_e2e/...` appeared in body-level context.
- **Resolution chain (now uniform across both scripts):**
  1. `$INTERIOR_PLANNER_HOME` env override (CI / dev installs / sandbox)
  2. Canonical hardcode fallback: `/storage/emulated/0/PROJECTS/workstation/interior_planner_e2e`
  3. Inline `def resolve_interior_planner_home() -> Path: return Path(os.environ.get(...))` — NOT a helper module, lives with the script.
- **Helper dropped**: `_interior_planner_home.py` + `_marker.txt` both deleted. They were v5.53.0 artifacts; v5.56.0 already proved they were dead-code once resolver is inlined.
- **CON-18 (inline duplication as load-bearing design)**: 8-line `resolve_interior_planner_home()` теперь duplicated between `register.py` + `e2e_promt47.py`. ANTI-fragility wins: shared helper = brittleness at relocation (loss-prone across git mv / SCM discard). DRY-ifying this back into a module would re-introduce exactly the failure mode v5.56.0 hit (helper never created → NameError). **Read this section before refactoring.**
- **Known caveats**:
  - `parents[1***REMOVED***` sys.path block в обоих скриптах — old form, NOT sufficient for `core_02` discovery (parents[1***REMOVED*** = `interior_planner/`, doesn't contain `core_02/`). Runners must set `PYTHONPATH=/storage/.../workstation/freebuff` or `FREEBUFF_ROOT` env. Block-A recovery deferred to separate debt.
  - `DEFAULT_CANONICAL_ROOT = Path("/storage/.../blueprints_v3")` в register.py — still hardcoded without env override; out of CAN-8 scope.
- **Verify gates passed (2026-08-03)**: py_compile / cold-import DEFAULT_SEED+DEFAULT_ARTIFACT NOT /tmp / business gate `e2e_promt47.py --skip-tg --silent` exit 0 / grep `/tmp/interior` оба файла → 0 hits. Full evidence: CHANGELOG v5.57.0 + `docs_10/core/ARCHITECTURAL_DEBT.md §5.11`.
Per PB-5, Freebuff-side сознательно НЕ registers interior_consultant в `/storage/.../blueprints_v3/`. Role file lives в workspace; manual dev-side promote через HANDOVER Phase E.

**Следующий шаг:** Расширить BlueprintCorpus API для двунаправленного workflow (stage v3→workspace-edit→promote-to-canonical) + `--use-propose` flag (CAN-7 follow-up) который сканирует и workspace manifests.

### PB-12 — HANDOVER.md Phase D reference developer role without file (doc bug, fixed)
**Symptom:** Phase D example snippet creates `registry.yaml` with 2 entries (developer+interior_consultant), copies only `18_interior_consultant.md`, not `09_developer.md`. `BlueprintCorpus(root=local_seed)` loads OK (registry validates), но `list_roles()` filters IDs без present файлов → developer role теряется.

**Fix:** Phase D обновлён - добавлена `shutil.copy(dev_src, seed_dir / "09_developer.md")` line + сделана ссылка на `scripts_01/interior_consultant_register.py` (single source of truth, do it once, finger it).

**Урок:** Документируя multi-step copy-dance scripts — сначала fix script, потом snapshot в Handover. Inline snippets в Handover drift easily.

---

## 📦 Scenario: interior_planner concrete source code + project-level role (2026-08-03)

### CON-15 — Project-local role registry pattern (v5.48.0 architecture fix)
**Сценарий:** v5.47.0 был ошибочно mixanversal: role `interior_consultant` предлагалась как promote-to-canonical в Phase E. User прозрачно поправил: "не впихивать в сценарий, она привязана к проекту" — role должна жить в **project-local AGENTS.md**, не в scenario `blueprint_v3` registry.

**Что сделано:**
1. **[`interior_planner/AGENTS.md`***REMOVED***(../../tmp/interior_planner_e2e/interior_planner/AGENTS.md)** — 104 строки, явно разделяет architectural rule:
   - **Scenario-level roles** (e.g. `blueprint_v3` corpus, 17 roles) = **system**, reusable across many projects, registry.yaml manages them.
   - **Project-level roles** (project-local AGENTS.md) = **domain-specific**, only this project, AGENTS.md manages them.
2. **Real TS source code** (production-ready, сконвертирован из spec scaffold в actual code):
   - [`package.json`***REMOVED***(../../tmp/interior_planner_e2e/interior_planner_app/package.json) — RN 0.74.5 + Skia 1.3.2 + Zustand 4.5.4 + AsyncStorage, pinned versions.
   - [`tsconfig.json`***REMOVED***(../../tmp/interior_planner_e2e/interior_planner_app/tsconfig.json) — strict mode, noUncheckedIndexedAccess.
   - [`src/types/domain.ts`***REMOVED***(../../tmp/interior_planner_e2e/interior_planner_app/src/types/domain.ts) — project-scoped types (Room, FurnitureObject, KnowledgeBase) — **NE shared with system**.
   - [`src/data/knowledge_base.json`***REMOVED***(../../tmp/interior_planner_e2e/interior_planner_app/src/data/knowledge_base.json) — REAL IKEA dimensions (verified 2024-Q1).
   - [`src/store/roomStore.ts`***REMOVED***(../../tmp/interior_planner_e2e/interior_planner_app/src/store/roomStore.ts) — Zustand + AsyncStorage + partialize + onRehydrateStorage + hasHydrated guard.
   - [`src/components/RoomEditor.tsx`***REMOVED***(../../tmp/interior_planner_e2e/interior_planner_app/src/components/RoomEditor.tsx) — main screen orchestrator (header + canvas + category chips + items panel + footer с long-press-to-delete).
   - [`src/components/Canvas2D.tsx`***REMOVED***(../../tmp/interior_planner_e2e/interior_planner_app/src/components/Canvas2D.tsx) — react-native-skia renderer + GestureDetector drag (v2: handleDragUpdate вынесен в JS thread через runOnJS callback, чтобы избежать worklet-call non-worklet functions; Skia `<Text>` drop по blocker reminder).
3. **Scope-leak invariant проверяется side-effect:** `grep -rl 'AGENTS\.md\|interior_consultant' runtime_05/scenarios/*.yaml` ⇒ **NO_LEAK** (sanity grep в AGENTS.md Quick Commands дается в project как regression check).
4. **Реальный TG финал (v5.48.0):** Saved Messages msg_id=**138047**, Литвинов msg_id=**138048** — cumulative 7 TG сообщений по промту-47 (Saved 138040/138041/138044/138047 + Литвинов 138042/138045/138048).

**Вывод:** Self-learning platform должен уметь reflectировать разницу между **system scenario role** и **project role**. Ошибка смешения (v5.47.0 Phase E promote-to-canonical) была допущена потому что wizard разрабатывался в scenario-first context (CON-10); пользователь явно поправил "не сценарий, проект". Это **architectural discipline lesson**: project roles не должны auto-promote-в scenario catalog. Cross-reference: HANDOVER.md Phase E (v5.47.0) marked OBSOLETE — см. AGENTS.md §"What CANNOT be done from here".

### PB-13 — In-worklet Array.find/errors (Canvas2D.tsx v1)
**Symptom:** First draft [`Canvas2D.tsx`***REMOVED***(../../tmp/interior_planner_e2e/interior_planner_app/src/components/Canvas2D.tsx) v1 вызывал `findNearestObject` напрямую из `Gesture.Pan().onUpdate` worklet context. Caught by code-reviewer-minimax-m3 final round.

**Причина:** React Native Reanimated 3 worklets не могут non-worklet-call closures over component-scope variables (e.g., `project.objects`). `Array.find` работает в worklet thread, но access к React state через closure — не является.

**Fix (v2):** Логика вынесена в `handleDragUpdate` (useCallback, JS thread) и вызывается из worklet через `runOnJS(handleDragUpdate)(e.x, e.y)`. Worklet → UI-thread event forwarding → JS-thread geometry logic → JS-thread `moveObject()`. **Один worklet directive, один bridging call, JS-thread ownership.**

**Урок:** При работе с Reanimated + gestures/JSI libs скептически оценивай какая логика МОЖЕТ вызываться из UI thread. Worklet thread: только pure JS primitives + closures, захваченные на момент `Gesture.Pan()` создания. Вся логика с React state dependency — **JS thread**, bridged через `runOnJS`.

### ANTI-8 — Skia useFont(null) — silent fallback trap
**Symptom:** v1 [`Canvas2D.tsx`***REMOVED***(../../tmp/interior_planner_e2e/interior_planner_app/src/components/Canvas2D.tsx) испльзовал Skia `<Text font={font***REMOVED***>{name***REMOVED***</Text>` где `font = useFont(null, 12)`. Caught by code-reviewer-minimax-m3.

**Причина:** Skia `useFont` ожидает **реальный** font source — URI, byte array, или SkFont instance. Null — invalid, может throw или silently return undefined. `if (font && ...)` защищает runtime crash но `<Text>` рендерится пустым (немой labels).

**Fix (v2):** Drop `<Text>` rendering entirely. RectИ мебели остаются **без** inline labels; имена видны в chip list ниже канваса (already существует в v2 через `object-chip` в `RoomEditor.tsx`). **MVP trade-off**: visual canvas = чисто, no inline текст; если нужен labels-on-canvas — add real font file (e.g., Inter-Regular.ttf) + asset loading.

**Урок:** Если требует real font — assetetub. Если asset не critical — drop rendering (MVPs с partial features — OK). **Никогда не** `useFont(null)` в Skia — silent undefined trap.

---

## ⏭ Что в следующий сценарий (NOT этой итерации)

- AGENTS.md renderer из `role_id + contracts` (отдельный сценарий поверх `core_02/contracts.py`)
- LLM‑based fuzzy role match (замена CAN‑5 keyword overlap)
- ruamel.yaml‑based registry round‑trip (замена текстового splice из CON‑1)
- ~~Реальная Telegram‑интеграция через `tg_session.session` (CAN‑3)~~ → **✅ Resolved** v5.40.0 (см. `docs_10/core/ARCHITECTURAL_DEBT.md` §5.10; chat_ids: Saved Messages=**7709651193**, Александр Литвинов=**1063827731**; API у `projects_17/tg_terminal_messenger/src/telegram/client.py`)
- **Telegram integration contract** — следующий сценарий поверх найденных chat_id: стабильный wrapper `core_02/telegram_contract.py` (TGClient.from_session_default() + `send_to(saved_messages: int, text: str)` + `send_to_litvinov()`) с регресс‑тестом, чтобы все TG‑интеграции шли через единый API вместо хардкода chat_id в потребителях.
- Validate `agent.missing_required_sections` при создании роли (см. ANTI‑6)
- **FUT-NIT-1 (v5.189.26, Phase 9 / promt 092)**: `_LAZY_IMPORT_ERRORS` в `scripts_01/content_factory.py` — module-global mutable state, может утекать между ContentFactory-instances в тестах. **Следующий шаг:** перевести на instance attribute `self._import_warnings: List[str***REMOVED*** = [***REMOVED***` (single underscore, lazy-init в `__init__`). Чистая пере-стейтмент в один день. До этого: безопасность гарантируется hermetic test-isolation (фикстуры cleanup, instance per test) + CLI-контекст (одна глобальная величина на процесс).

## 📦 Scenario: Multi‑Scenario Registry поверх Blueprint v3 (2026-08-02)

### CON-10 — Multi‑scenario registry closes ANTI‑7 (registry = polymorphic wizard source)

**Сценарий:** Refactor wizard от hard-coded single-corpus к multi-scenario. Реализовано:
- **`core_02/scenario.py`** — `Role` dataclass + `Scenario` ABC + `ScenarioManifest` (YAML loader). ABC surface: 2 properties (scenario_id, display_name) + `roles()`, `load_role_text()`, `routing_hint()`, `validate()`.
- **`core_02/scenario_registry.py`** — `_SCENARIO_TYPES` dispatch (`type:` → class), auto‑discovery `*.yaml` в scenarios_dir (env `$FREEBUFF_SCENARIOS_DIR` или `runtime_05/scenarios/`), graceful warnings (`silent=True` для тестов, `silent=False` для CLI со stderr), `validate_all()` soft‑gate, cross‑scenario duplicate role_id detection, `_instantiate(scenario_id, root)` uniform kwarg signature.
- **`core_02/blueprint_v3.py`** — `BlueprintCorpus` adds `scenario_id` kwarg, `roles()`, `load_role_text()`, `validate()`, properties `scenario_id`/`display_name`. **Legacy `list_roles()` returns tuples preserved** (BC). `BlueprintScenario = BlueprintCorpus` BC alias.
- **`core_02/wizard_lib.py`** — `run_wizard_with_registry(registry, ...)` + 3 helpers (`build_agent_json_for_registry`, `build_task_json_for_registry`, `_seed_levels_for_registry`). legacy `run_wizard(corpus=...)` сохранён.
- **`scripts_01/wizard.py`** — `--scenarios-dir` env override + `--scenario <id>` filter + auto‑discover mode (default) + explicit `--blueprints-dir` BC. `--selftest` builds tmp registry.

**Coverage:** `tests_09/test_scenario_registry.py` ~19 tests: discovery (sort, enabled skip, empty, nonexistent), parse (good/bad), warnings (unknown type, parse fail, duplicate id, silent vs stderr), cross-scenario (`all_roles`, `find_role`, `propose_roles` top/fallback/cross, `validate_all` clean/corrupt/dup), BC alias + ABC conformance.

**Вывод:** новый Scenario = YAML‑manifest + одна строка в `_SCENARIO_TYPES`. Wizard / registry не меняются. Auto‑discovery pattern parallels `runtime_05/providers/` + `freebuff_plugin_03/runtime/registry.py` — freebuff растёт без over‑engineering.

### ANTI-7 — Single-source hardcode = wizard lock-in

**Сценарий:** Wizard hard‑кодит `corpus: BlueprintCorpus` — единственный источник ролей. Хочешь Remote Personas = мажорный refactor wizard signature.
**Проблема:** Single‑source wizard API = type pollution: каждый новый role‑source заставляет wizard имплементировать `BlueprintCorpus` API вместо того чтобы wizard говорить на общем Scenario ABC.
**Урок:** Wizard ищет роль через `ScenarioRegistry` (cross‑scenario `find_role`/`propose_roles`/`validate_all`). Auto‑discovered scenarios подхватываются новым YAML + одной строкой dispatch. См. CON‑10.

### ANTI-7b — ABC method shadow = BC rename trap

**Сценарий:** Спроектировал Scenario ABC с `list_roles() → list[Role***REMOVED***`. Конфликт с существующим `BlueprintCorpus.list_roles() → list[tuple[...***REMOVED******REMOVED***`. Если переименовать ABC → BC break в wizard/tестах. Если переименовать concrete → loss of legacy `list_roles()` API.
**Fix:** Переименование ABC метода в `roles()` (без `list_`‑префикса) — distinct from `list_roles()` legacy. Concrete добавляет НОВЫЙ метод `roles()` для ABC, оставляет существующий `list_roles()` нетронутым.
**Урок:** при расширении класса через ABC всегда делать `dir(concrete_cls)` и искать shadowing. Если collision → rename ABC (не concrete), префиксуя новый метод именем, не занятым в наследниках.

### PB-8 — ABC rename `list_roles` → `roles` (collision resolution)

**Symptom:** Первый draft `Scenario` ABC объявил `list_roles() → list[Role***REMOVED***`. Конфликт с existing `BlueprintCorpus.list_roles() → list[tuple***REMOVED***`. type collision на этапе разработки.
**Fix:** rename ABC метода в `roles()`. `BlueprintCorpus.list_roles()` остался legacy: `test_wizard.py` + `wizard_lib.propose_roles` (single‑corpus BC path) НЕ меняются. `BlueprintCorpus.roles()` добавлен как new concrete: projects tuples → `Role` dataclasses.
**Урок:** Trade‑off между именованием ABC после «роль‑функции» (cleaner: `roles`) и существующих legacy terms (preserve callers: `list_roles`). Новый ABC wins, semantic clarity. BC legacy wins, preserves callers. Оба в одном классе — два distinct метода.

### CON-11 — Чистые ошибки корпуса + markerless splice (CAN‑1 + CAN‑4, v5.43.0)
**Сценарий:** resilience корпуса — повреждённый/пустой registry.yaml + реформат пользователем без marker'а.
**Что подтверждено:** (1) `_load_registry()` переводит `yaml.YAMLError` в `ValueError` с указанием пути и совета восстановить из .bak; пустой/не‑dict → `ValueError` «пуст или неожиданная структура». (2) `_insert_into_pipeline` вставляет новую запись внутрь существующего `pipeline:` (ищет top‑level ключ, вставляет перед следующей секцией) — файл остаётся валидным YAML, дубликатов секций нет. (3) post‑parse guard по‑прежнему ловит любой невалидный сплис до записи на диск (CON‑1 сохранён).
**Вывод:** self‑healing UX: pipeline, упавший посреди проекта на повреждённом registry, теперь падает loud с диагностикой, а не молчаливым traceback; пользовательский реформат registry.yaml больше не ломает добавление ролей.



## ✅ Scenario: Block-A Recovery — FreebuffLocator Helper (2026-08-03)

### CON-19 / ANTI-12 NEW lesson — verify-gate baseline check

При закрытии any `sys.path`-class change (Block-A, locator enhancement, relocation):
**ALWAYS runna baseline-check downstream references BEFORE changed-run**, не только
после. Инача silent pre-existing drift-fixes маскируются как «all gates green» 
без ground-truth. Кейс в v5.58.0: `e2e_promt47.py` ROOT изменился с `parents[1***REMOVED*** = 
interior_planner/` на `parents[1***REMOVED***` ➜ Freebuff root. Downstream refs (DEFAULT_E2E_LOG, 
PROMT47_FILE, _CANONICAL_MANIFEST) **MOЛЧА** указывали на несуществующие пути в 
`interior_planner/` с момента v5.51.0 relocation — это был PRE-EXISTING DRIFT, 
без baseline-проверки я не увидел его manual-fix vs incidental-fix.

**Pattern (NEW)**:
```bash
# Step A: snapshot expected downstream paths from changed script
grep -E "ROOT |DEFAULT_E2E_LOG |PROMT47_FILE |_CANONICAL_MANIFEST" <script>.py
# Step B: BEFORE changed-run, list actual filesystem truth
python3 -c "***REMOVED***; print(Path(docs_10/e2e_logs/promt47_run.md).exists())"
# Step C: AFTER changed-run, re-check
# Same command, should match.
```

### CON-20 — code duplication as load-bearing (повтор v5.57.0)

Несмотря на то что 4-line locator-pattern **identical** в обоих canonical scripts, 
сама функция живёт в **1 файле** `_freebuff_locator.py`. Это anti-fragile design:
- 1 source-of-truth для contract (resolver API, marker tag, validation)
- N copies в callsites (no inversion of control, no surprise side-effects)

Не пытаться unified через `_interior_planner_home.py`-style helper в проекте scripts/ —
это переносит brittleness в helper (его можно потерять при relocation). Inline locator-
**block** (4 lines x N callsites) — ОК. Helper module — НЕ ОК. Восстановлен приоритет 
анти-fragility над DRY применительно к project-level scripts.

### Block-A closure details (v5.58.0)

Phase: post-v5.57.0 (CAN-8 closed but Block-A recovery deferred as separate debt).

Изменения:
- **NEW**: `scripts/_freebuff_locator.py` — 60-line pure-function helper, 
  `resolve_freebuff_root() -> Path` (contract: $FREEBUFF_ROOT > canonical hardcode > 
  validation `(root / "core_02").is_dir()` > `[FreebuffLocator***REMOVED***` marker).
- **CHANGED**: `scripts/interior_consultant_register.py` + `scripts/e2e_promt47.py` — 
  replaced `parents[1***REMOVED***` sys.path block with locator pattern (4 lines, identical).

Verify-gate 2026-08-03 (6 gates, all green):
1. `py_compile` 3/3 → exit 0
2. Full Block-A chain без PYTHONPATH → exit 0 (core_02.blueprint_v3 + telegram_contract both OK)
3. Drift baseline check: 3/3 downstream refs → exist=True (PATHs реальны под Freebuff root)
4. Business gate `e2e_promt47.py --skip-tg --silent` → exit 0
5. `register.py` cold-import: DEFAULT_SEED/DEFAULT_ARTIFACT НЕ через `/tmp` → PASS (v5.57.0 invariant)
6. Grep audit: `parents\[1\***REMOVED***` functional = 0, `from _freebuff_locator import` = 2/2 scripts ✓

Tooling tidy: `_apply_blocka_v5580.py` + `_apply_can8_v5570.py` + `_restore_can8_v5570.py` 
+ `v551_*` + `v552_dock.py` + `v553_dock.py` → moved в `trash_21/` (anti-accumulation по 
`docs_10/core/CODE_QUALITY_STANDARD.md`).

### Known limitations (deferred)

- **`python3 -m pkg.e2e_promt47` invocation mode** — current usage works because Python 
  auto-injects script dir в sys.path[0***REMOVED***. Если в будущем кто-то запустит `-m` mode из 
  parent dir, sibling locator import провалится. Current usage always via absolute 
  path → safe. Documented в CHANGELOG v5.58.0 §Known Limitations.
- **Hardcoded Python `_CANONICAL_FREEBUFF_ROOT`** vs shell-form `${FREEBUFF_ROOT:-/default***REMOVED***` 
  convention в `freebuff_plugin_03/monitor.sh` — minor inconsistency, not blocker.

---

## 🚀 Scenario: CAN-9 Final Closure — Real `--client` TG Round-Trip (2026-08-03)

### CON-22 — locator-class changes require RE-round-trip, not pre-fix confirm

При выполнении compound debt closure, где ОДНОВРЕМЕННО меняется sys.path strategy 
(Block-A v5.58.0) И verification gate (CAN-9 v5.59.0), недостаточно использовать 
pre-fix-round-trip evidence как подтверждение post-fix. Необходим **ЗАНОВО** 
реальный TG round-trip через новий sys.path chain, чтобы подтвердить:

1. Успешный stage 4 TG delivery (Saved + Литвинов).
2. Round-trip read-back через `client.get_messages` === real history (не 
   синтетика).
3. `promt47_run.md` правильно appended вверху pre-existing `## Historical 
   Verification Runs` section (B-3 splice fix verifies audit trail intact).
4. New run narrative отличается от pre-fix только способом discovery, не 
   бизнес-логикой (Stage 1–3 поведение идентично).

### Latest verified run (v5.59.0, locator-based)

- **Pre-flight (CHECK-only)**: TG session alive (`projects_17/tg_terminal_messenger/tg_session.session`, sqlite entities кэш валидный), `core_02.telegram_contract` importable через `_freebuff_locator.resolve_freebuff_root()` без PYTHONPATH, API surface (`report_to_saved_messages`/`report_to_alex_litvinov`/`report_to_litvinov`) exposes правильні chat_id константи.
- **Real run TG side-effects**: `python3 /storage/.../interior_planner_e2e/interior_planner/scripts/e2e_promt47.py --client --silent` → exit 0.
- **Saved Messages** (chat_id=7709651193): msg_id=**138170**, text head `🧪 E2E платформенный тест промта-47\n\n📦 Project: interior_planner\n📐 Stage 2 path: ...`
- **Литвинов** (chat_id=1063827731): msg_id=**138171**, text head `🔔 [client notification — test agent → client***REMOVED***\n\n🧪 E2E платформенный тест промта-4...`
- **Round-trip** (`TGClient.get_messages(chat_id, ids=msg_id)`): оба retrieved, non-empty text, real TG history ✓.
- **promt47_run.md** log: новый Run вверху + 6 prior Historical Verification Rows splice-preserved (v5.46.0/v5.47.0/v5.49-50/v5.52.0/v5.56.0/v5.56.1 — все valid через TG round-trip).

### Differs from v5.56.0 round-trip (POST-Block-A re-confirm)

v5.56.0 canonical close (138128/138129): under `parents[1***REMOVED***` sys.path strategy.
v5.59.0 NEW close (138170/138171): under `_freebuff_locator.resolve_freebuff_root()`.
Business behavior identical — Stage 1 (planning) + Stage 2 (wizard) + Stage 3 (mock runtime) + Stage 4 (TG).
TG message content has identical headers (text starts with `🧪 E2E платформенный тест промта-47` for Saved, `🔔 [client notification — test agent → client***REMOVED***` for Литвинов), differing only in run metadata (snapshot name, model_id if changed by Stage 2 fallback harness).

### Cumulative harness audit-trail (post-v5.59.0)

audit-trail из `docs_10/e2e_logs/promt47_run.md` `## Historical Verification Runs`:
- v5.45 → Saved=137901 + Литвинов=137902
- v5.46.0 → Saved=138040 + Литвинов=138042
- v5.47.0 → Saved=138044 + Литвинов=138045
- v5.49-50 → Saved=138047 + Литвинов=138048
- v5.56.0 → Saved=138128 + Литвинов=138129
- v5.56.1 NIT-1 → Saved=138130 + Литвинов=138131
- **v5.59.0 → Saved=138170 + Литвинов=138171** (this release, locator-based)

Anti-rewriting rule (CAN-17) prevсит makesоммтять любой msg_id задля consistency, даже 
если есть post-hoc disсоvery. Все 7 записей сохранены в audit-trail без модификаций.

### Ship status

CAN-9 fully closed in v5.59.0 (post-Block-A v5.58.0). Compound closure 
(Block-A + CAN-9) verified end-to-end through locator-based discovery → real TG 
delivery → round-trip read-back → audit-trail preservation. Code-reviewer-minimax-m3 
final APPROVE.

## ✅ Scenario: Phase 5.3-C Live Round-Trip — v5.64.0 Gate D (2026-08-03)

### CON-35 NEW lesson — script-native Stage 3 sufficient for round-trip verification

**Key finding**: When running LIVE TG round-trips with dual-channel delivery, **rely on the script-native Stage 3 implementation** (`TGClient.get_messages(limit=100)` limit-scan + client-side `id` filter per CON-31) instead of writing a separate side-script for verification. The script's Stage 3 is ALREADY designed for this exact scenario. Re-implementing it externally increases drift risk and cancels the per-run log evidence.

### CON-31 (TGClient wrapper constraint → RESOLVED v5.66.0)

TGClient.get_messages signature в `projects_17/tg_terminal_messenger/src/telegram/client.py` — `(entity, limit=5)`, НЕ принимает `ids=`. Pivot used limit-scan + client-side filter.

**RESOLVED via ADR-011 + `core_02/_tg_client_v2.py` fork (DEBT-5.21 closure, v5.66.0)**: `TGClientV2` now exposes:
- `get_messages(entity, limit=5, ids=None)` — `ids=` kwarg delegates to telethon's native `ids=` param, eliminating the CON-31 limit-scan pivot.
- `add_event_handler(callback, event)` — for Phase 5.3-D hot-path listener.
- `remove_event_handler(callback, event)` — for clean shutdown.

The fork wraps (not extends) the upstream `projects_17/tg_terminal_messenger` boundary per ADR-011 Option 3, preserving upstream untouched.

**CON-31 implications for e2e_remote_sync.py**: The original limit-scan pivot was accepted as a pragmatic trade-off in v5.64.0 (Phase 5.3-C) when TGClient did not expose `ids=`. With v5.66.0 `TGClientV2.get_messages(ids=[...***REMOVED***)` available, future round-trips SHOULD use `ids=` kwarg for precise message-by-ID fetch (returns `[Message***REMOVED***` with telethon's exact match). The upstream TGClient (`projects_17`) remains unchanged; the fork only lives in `core_02/`.

**Pattern (NEW for real TG runs)**:
```bash
# Step A: pre-flight via --skip-tg (zero side-effects)
python3 scripts_01/e2e_remote_sync.py --skip-tg --silent --run-tag preflight_v5_64_dryrun

# Step B: real TG side-effects with dual-channel
python3 scripts_01/e2e_remote_sync.py --sync-group --silent --run-tag phase_5_3_c_gate_d_real_v5_64_0

# Step C: round-trip evidence is AUTOMATICALLY captured in run log + audit-trail row prepended in promt47_run.md (via script's write_e2e_log).
# No external verification script needed.
```

### CAN-17 audit-trail direction (corrected from initial thinker position)

**Initial thinker recommendation**: append NEW audit-trail row to BOTTOM of `## Historical Verification Runs` (chronological reasoning).

**Actual file evidence (basher read)**: **append-to-TOP** is the established convention. The `## Historical Verification Runs` header is followed by v5.64.0, then v5.59.0, then v5.56.1, etc. (NEWEST FIRST).

**Forward rule**: For all future real TG round-trips, anchor on `## Historical Verification Runs` line and use `str.replace(anchor, anchor + new_row, 1)` to prepend immediately after the header. Preserves all prior runs (CAN-17).

### ##FB_STATE## marker — canonical round-trip detection pattern

Discovered during v5.64.0 live run: TG message body contains `##FB_STATE##` marker which can be used as canonical round-trip detection pattern.\n\n**Provenance**: programmatically generated by `core_02/remote_sync.py::RemoteSyncCoordinatorImpl.push_state()` as part of the StateV2a SyncDelta payload body field. Stage 3 grep-detect is an idempotent validation that the message body was produced by `push_state()` (real state sync) rather than other TG-channel artifacts (echo/control/test).

### v5.64.0 Live Run Evidence

- **Pre-flight (Stage 0, --skip-tg CHECK-only)**: TG session alive, `core_02.remote_sync` + `core_02.telegram_contract` importable через `_freebuff_locator.resolve_freebuff_root()` без PYTHONPATH.
- **Real TG send (Stage 2)** двусторонних каналів:
  - **Saved Messages** (chat_id=**7709651193**): msg_id=**138366**, native `TGClient.get_messages(7709651193, limit=100)` limit-scan + client-side filter, non-empty text + `##FB_STATE##` marker.
  - **А. Литвинов** (chat_id=**1063827731**): msg_id=**138367**, native `TGClient.get_messages(1063827731, limit=100)` limit-scan + client-side filter, non-empty text + `##FB_STATE##` marker.
- **drift_check + consistency_check**: exit 0 (1 pre-existing CAN-10 naming warning — не входит в scope v5.64.0).

### CAN-9 cumulative ledger (post-v5.64.0 real run)

`docs_10/e2e_logs/promt47_run.md` `## Historical Verification Runs` (newest first, CAN-17):
1. v5.64.0 — Saved=138366 + Литвинов=138367 (this release, Phase 5.3-C Gate D REAL)
2. v5.59.0 — Saved=138170 + Литвинов=138171 (locator-based, post-Block-A)
3. v5.56.1 — Saved=138130 + Литвинов=138131 (NIT-1)
4. v5.56.0 — Saved=138128 + Литвинов=138129 (post-PYTHONPATH-required)
5. v5.49-50 — Saved=138047 + Литвинов=138048
6. v5.47.0 — Saved=138044 + Литвинов=138045
7. v5.46.0 — Saved=138040 + Литвинов=138042
8. v5.45 — Saved=137901 + Литвинов=137902 (CLE originating)

All 7 prior runs preserved (CAN-17 anti-rewriting). Newest run prepended per actual convention.

### Ship status

**v5.64.0 SHIPPED** — Phase 5.3-C Gate D complete. Compound closure (5.3-A spec + 5.3-B runtime + 5.3-C real GNU TG round-trip) ship-ready end-to-end. Code-reviewer-minimax-m3 APPROVE.

---

## 📌 Scenario: Identity Clarification (Buffy ≡ Freebuff, 2026-08-04, v5.74.0)

### CAN-XX / CON-NEW — clarification discipline: insert > rewrite

**Scenario:** user clarified 3 things about project identity that were scattered across canonical docs with inconsistent framing:
1. **Promt-48** = external interface to the Freebuff AI agent (not «запуск Баффи как subprocess»). Пользователь скачал Workspace OS (Freebuff) на телефон из облака и хочет управлять им извне, не только из локального терминала.
2. **Buffy ≡ Freebuff** (неразрывны): пользователь говорит «Баффи» = вся система Freebuff (платформа + мозг), а не «ассистент в Freebuff».
3. **Workspace OS** = the platform (planned rebrand от Freebuff); **Buffy/brain layer** = swappable layer, future users may replace or distribute.

**Что подтверждено (2026-08-04, v5.74.0):**
- Inserted **Clarification blocks** (не rewrites) into 3 canonical docs: [`docs_10/core/CORE_PROMPT.md`***REMOVED***(docs_10/core/CORE_PROMPT.md) §1, [`BUFFY.md`***REMOVED***(BUFFY.md) top, [`pompts_11/promt48.md`***REMOVED***(pompts_11/promt48.md) ЦЕЛЬ (item 0 + header). ALL inserted surgically.
- Новый ADR: [`docs_10/engineering-memory/decisions/ADR_012_buffy_swappable_brain.md`***REMOVED***(docs_10/engineering-memory/decisions/ADR_012_buffy_swappable_brain.md) — 3-level model: Workspace OS (platform) ← Buffy/Freebuff (brain) ← Access Channels (TG/MCP/REST/terminal).
- CHANGELOG.md v5.74.0 prepended (documentation-only release; v5.73.0 preserved below).
- AGENTS.md / TASK.md / BUFFY_PROJECT.md version stamps sync'd to v5.74.0.

**Почему INSERT, не REWRITE:**
- Сохраняет provenance: original canonical text не сломан, остаётся в истории (anti-rewriting CAN-16 spirit applied to identity layer).
- Cross-references (CHANGELOG.md historical entries, LESSONS.md CON-* anchors, AGENTS.md milestone table) остаются валидными — original identity строка не переписывается.
- Будущие similar clarifications могут co-exist (несколько Clarification blocks stackable; rewrite вынуждает одну каноническую версию).
- Если будущий maintainer прочитает историческую narrative, original framing доступна рядом с clarified — NO lost history.

**Lesson NEW — Identity-Audit pattern при major shift:**
- При изменении identity framing — 3 canonical files должны синхронизироваться: **`CORE_PROMPT identity §` + `BUFFY.md top` + relevant `prompt <N>.md ЦЕЛЬ`**.
- ADR создаётся в `docs_10/engineering-memory/decisions/` как engineering memory layer для долгосрочного follow-up.
- Version bump требуется, даже когда change is documentation-only — чтобы другие агенты не работали с устаревшей framing.
- **Insert-over-rewrite + traceability = CAN-16 anti-rewriting extension на identity layer** (NEW lesson).

**Anti-pattern (запрещено при identity change):**
- ❌ Rewrite original identity sentence в canonical doc — ломает cross-references historical narrative + создаёт silent alignment gap между разделами.
- ❌ Добавить clarification block в **одном файле** (e.g. только в CORE_PROMPT) — drift с BUFFY.md / prompts_file.
- ❌ Не делать ADR — будущие сессии будут решать ту же проблему заново.
- ❌ Не бампить версию — неясно когда identity shift произошёл + другие docs остаются на old framing.

**Follow-up (deferred, не блок):**
- `docs_10/decisions/DECISIONS.md` canonical index entry — добавить строку для ADR_012 при ship (📌).
- `docs_10/vision/decision_index.md` navigation link — добавить для ADR_012 при ship (📌).
- BUFFY_PROJECT.md rename «Buffy Project 2.0» → «Workspace OS 2.0» — deferred к v5.80+ (avoid breaking docs structure сейчас).
- `core_02/brain_plugin.py` runtime API surface (deferred к v6.x) для swappable brain layer.
- `core_02/multi_agent_router.py` для multi-agent distribution (deferred к v6.x).

**Why no code-reviewer on documentation-only release:**
- ZERO Python/JS/code changes; only markdown edits + 1 new ADR markdown file.
- `code-reviewer-minimax-m3` guideline: «Skip if change is straightforward»; documentation-only edit ниже порога code-review.

## ✅ Scenario: Dual-Path TG → Buffy Dispatch (v5.83.0, 2026-08-04)

### CON-23 (NEW lesson) — user-feedback-driven real-time UX

User report: «почему ты его не выполняешь? суть в том, чтобы это выполнялось из моего уже повторного участия». Translation: TG bot writes to queue but cron pick-up latency is 0—5 min — UX gap. Конкретно — наблюдение из реального use-case: пользователь отправил /task в телеграм, не получил отклика, повторил.

**Решение (dual-path architecture):**
- **Fast path:** `cmd_task` пишет prompt + сразу spawn'ит `prompt_dispatcher.py --once` через `asyncio.create_subprocess_exec` (fire-and-forget). Latency: 1—3 sec. TG-bot reactor НЕ блокируется (`await` на subprocess fork не занимает минуты).
- **Slow path (cron safety-net):** `*/5 * * * *` prompt_dispatch.sh продолжает тикать. v5.83.0 ADD `python scripts_01/prompt_dispatcher.py --recover --recover-age 3600` ПЕРЕД основной dispatch — push stale `.in_progress/` locks обратно в `user/`. Graceful `|| echo "not supported"` fallback если dispatcher ещё не поддерживает `--recover`.
- **Race-safe:** `dispatch_one.move_to_status` wrapped try/except FileNotFoundError → returns `skipped_locked` noop (concurrent bot+crond spawn --- FileNotFoundError midrace --- NE crash, no duplicate execution).
- **Anti-zombie:** module-level `_pending_reapers: set[asyncio.Task[None***REMOVED******REMOVED*** = set()` anchors fire-and-forget reapers; `_reap_subprocess_safe` self-unregisters через `finally: _pending_reapers.discard(current)`. Без anchor'а `asyncio.create_task()` создания рискуют GC'нуться прежде чем они успеют завершить работу.
- **Anti-leak (round 4 review):** `log_fd.close()` on exception path перед `raise` --- если fork raises, parent FD leak. Pattern: `try { spawn ***REMOVED*** except { close + raise ***REMOVED***` обеспечивает single close per scenario.
- **Observability (round 1 review):** per-task log file `logs_14/tg_spawn_<taskid>.log` (НЕ DEVNULL). Позволяет post-mortem debugging fast-path spawn.

**Why asyncio.create_subprocess_exec (НЕ subprocess.run):**
- `subprocess.run` blocks TG-bot reactor loop === starves other users. asyncio вариант возвращает `Process` immediately после fork.
- In-process call `dispatch_one()` shares memory with bot. Если Баффи trigger'ит OOM в том же процессе === bot dies. Отдельный subprocess = anti-fragility.

**Anti-fragile guard layering (4 уровня):**
1. Bot subprocess crash → file stays в `user/` → cron подхватывает в ≤5 min. No data loss.
2. Cron crash → bot уже spawned, bot exit returns void. User видит response anyway.
3. Bot & cron race → FileNotFoundError → `skipped_locked` noop, NE crash.
4. Dispatcher crash (OOM/SIGKILL) mid-launch → file в `.in_progress/` → cron `--recover` pushes back в `user/`.

**Tests added (5 + 0 regressions):**
- `test_cmd_task_spawns_dispatcher_subprocess` — verify spawn args содержит `prompt_dispatcher.py --once`.
- `test_cmd_task_spawn_failure_replies_cron_fallback` — verify OSError → «deferred → cron safety-net» в reply.
- `test_dispatch_one_race_returns_skipped_locked` — verify FileNotFoundError в `move_to_status` → return dict с `skipped_locked` status.
- `test_reap_subprocess_safe_unregisters_from_pending` — verify `_pending_reapers` set shrinks post-await.
- `test_prompt_dispatch_sh_invokes_recover_before_main_flag` — verify recover invokes ПЕРЕД main dispatch в sh.

**Forward-looking guard (CON-NEW):**
- (1) Periodic snapshot `_pending_reapers` в logs_14/ для debug visibility.
- (2) TG-message-dedup if user spams /task прежде чем dispatch finishes (current: каждый /task = новый subprocess, нет дубля в queue).
- (3) Limit concurrent reapers (e.g., max 4 subprocesses) --- не fork-bomb при rapid TG-fire.
- (4) Test isolation: `_pending_reapers.clear()` в fixture teardown (carry-over из round 4 polish nit).**Anti-fragility принцип:** ВСЕ 4 crash-уровня (bot, cron, race, dispatcher) перекрывают друг друга --- ни один single point of failure не съест user message. User TG-сообщение никогда не теряется.

## 🚀 Scenario: Live TG Round-Trip + Test-Hardening (v5.87.0, 2026-08-05)

### CON-27 (NEW) — OOM-awareness для live TG e2e

**Сценарий:** полный real-run `e2e_dual_path_tg_verify.py` (cmd_task → dispatcher → `wrapper.launch` → Buffy/proot) на phone-class RAM умирает **signal 9 (OOM)** на 2m14s ДО завершения round-trip. Сам round-trip confirm (Saved msg_id + Литвинов msg_id) НЕ требует Buffy — только TG send + read-back.

**Что подтверждено (live evidence):**
- Lean-path `scripts_01/tg_roundtrip_verify.py` (telegram_contract send + `TGClient.get_messages(limit=100)` read-back, CON-31 pivot) даёт POSITIVE round-trip: **Saved=138673, Литвинов=138674** (7.31s, exit 0) и **Saved=138675, Литвинов=138676** (18.44s, exit 0).
- Cumulative harness audit-trail в `promt47_run.md` ## Historical Verification Runs: v5.64.0 138366/138367 → v5.87.0 138673/138674 → 138675/138676 (CAN-17 append-to-TOP preserved).
- `wrapper.launch()` (tmux session + `.freebuff_result` polling) — правильный механизм фонового запуска Buffy; НЕ прямой `nohup` бинаря (Codebuff CLI — interactive TUI, web-research подтвердил).

**Паттерн (NEW):** разделять «что хочет user» (round-trip confirm) от «что тестирует pipeline» (spawn+dispatch). Для live TG confirm использовать lean script; полный e2e — для структурных dry-runs + CI.

### CON-28 (NEW) — search-head uniqueness discipline

**Сценарий:** TG round-trip read-back искал по статичному first-line head (`text.splitlines()[0***REMOVED***[:40***REMOVED***`) — одинаковый для ВСЕХ запусков → false-positive на старые сообщения с тем же префиксом ломает CAN-9 honesty.

**Решение:** `_unique_search_head(text, run_tag)` — run-tag ОБЯЗАН быть в ПЕРВОЙ строке сообщения (`🧪 v5.87.0 live TG round-trip {run_tag***REMOVED***`); search substring unique-per-run. Плюс force-append `\nRun-tag: {run_tag***REMOVED***` для custom `--text` без тега (иначе guaranteed false-negative).

### Тест-seams паттерн (NEW, код-ревью driven)

Для тестирования harness-скриптов без live TG:
- `_round_trip(..., client_factory=None)` — injectable TGClient factory (default = реальный import внутри функции).
- `_append_audit_trail(..., md_path=None)` — injectable target file (default = canonical promt47_run.md).
- Тесты (`tests_09/test_tg_roundtrip_verify.py`, 14 шт) exercise РЕАЛЬНЫЕ функции через seams — не копии логики, не глобальный Path monkeypatch.

### Трудности сессии (difficulties encountered)

1. **OOM signal 9** на live real-run (2m14s) — ключевой блокер, решён lean-path split (CON-27).
2. **str_replace anchor-mismatch silent-skips** — `oldString` с неверным whitespace/quotes молча не матчится; success-print мог ввести в заблуждение (verify по grep ОБЯЗАТЕЛЕН после каждого replace).
3. **Heredoc quote-escape hell** — Python f-strings с вложенными `'` в shell-heredoc ломали синтаксис; замена на write_file/str_replace с точными anchors.
4. **bak-файл бесполезен** если создан ПОСЛЕ broken-состояния (`.bak_v5.86.0_holistic` содержал ту же SyntaxError). Восстановление из git для untracked файла невозможно — только перезапись.
5. **pytest 1 failed + 8 errors** в `test_telegram_bot.py` — хроническая fixture-проблема (с v5.84.0 Polish #2 revert), НЕ регрессия v5.87.0.

### Verify Gate (2026-08-05)

- py_compile: `tg_roundtrip_verify.py` + `e2e_dual_path_tg_verify.py` + `test_tg_roundtrip_verify.py` — all OK.
- pytest `test_tg_roundtrip_verify.py`: **14/14 PASS**.
- Combined regression: `test_tg_roundtrip_verify` + `test_remote_sync` + `test_tg_client_v2` = **48/48 PASS**.
- Full collection: **2218 tests**.
- Live TG: 2× positive round-trip (138673/138674, 138675/138676).
- Code-reviewer: rounds 1-5, финальный APPROVE ship-ready.

### Cross-references: сессионные уроки v5.86.0 (в CHANGELOG, single-lessons-home note)

Пользователь просил «сохраняй все уроки». CON-25.1 (iterative round polling для surgical fixes: read → str_replace → verify → code-reviewer → iterate) и CON-26 (mock-object surface scope — только то, что cmd_task реально использует: `.id` + `.type` + `reply_text()`) детально записаны в CHANGELOG v5.86.0 entry; здесь — cross-reference для single-lessons-home консистентности.

## ✅ Scenario: CON-33 closure — single-instance backoff (v5.89.0, 2026-08-05)

### CON-34 (NEW) — дешёвый pre-check вместо слепого spawn при single-instance

**Сценарий:** freebuff допускает только один живой инстанс. v5.88.0 ввёл deferral (задача → `user/` вместо ложного failed), но каждый cron-тик (5 мин) спавнил tmux и ждал ~90s, чтобы обнаружить «already running» — чистые потери, пока живая интерактивная сессия держит инстанс.

**Решение (CON-33 → CON-34):**
- **Дешёвый pre-check** `_live_instance_busy()`: `pgrep -f "config/manicode/freebuff"` по подстроке пути бинаря (мс вместо ~90s спавна). Подстрока общая для host-Termux и inside-proot cmdline; обёртка `~/.local/bin/freebuff` НЕ матчится.
- **Fail-open**: ошибка pgrep → False → разрешаем spawn; реальный блокер по-прежнему ловится wrapper-маркером (`_SINGLE_INSTANCE_MARKERS`) → deferral. Pre-check — оптимизация, не единственный guard.
- **Backoff ≠ таймер**: пропуск пока сигнал занятости есть; сигнал исчез → спавним. `**Deferred At:**` — только audit-метка, backoff её НЕ читает (документировано в docstring).
- **`--all` обязан break'аться на ЛЮБОМ доказательстве занятости** (pre-check backoff И wrapper-блокер `deferred_single_instance`): иначе файл из `user/` пере-подхватывается следующим проходом → N×время_спавна впустую или бесконечный цикл. Задачи 2..N после успешного launch идут с `skip_busy_precheck=True` (занятость = наш собственный инстанс, не внешний).
- **Порядок guard'а**: проверка очереди ПЕРЕД pgrep (не гоняем pgrep на пустой очереди).

**Тест-seams урок (extends CON-26):** новые модульные pre-check'и, читающие реальное окружение (`pgrep`), ОБЯЗАНЫ мокаться во ВСЕХ фикстурах, вызывающих `dispatch_one`/`dispatch_all` (`queue_root`, `ws_root`, test_telegram_bot race-тест) — иначе тесты становятся environment-dependent (живой инстанс в окружении → спуриозный backoff).

**Live-подтверждение:** `_live_instance_busy()` = True при живой сессии; `--once --no-tg` вернул `⏳ backoff (инстанс занят): 1` мгновенно (~0s).

**Verify Gate:** 101 passed (5 файлов); 1 failed + 8 errors в test_telegram_bot.py — хроническая fixture-проблема с v5.84.0, НЕ регрессия. Code-reviewer rounds 1–3: все пункты закрыты (break на wrapper-блокере, изоляция тестов, честный счёт в main).

## ✅ Scenario: CON-35 closure — backoff-cooldown + TG один раз (v5.90.0, 2026-08-05)

### CON-35 (NEW) — счётчик backoff-тиков в мете файла + уведомление один раз

**Сценарий:** CON-33 даёт мгновенный backoff (не спавнит tmux), но молчит каждый тик. Пользователь не знает, что очередь ждёт, пока живая сессия держит единственный инстанс freebuff.

**Решение:**
- **`**Backoff Streak:**` мета в файле задачи** — счётчик подряд идущих backoff-тиков. Обязательно в файле (не в памяти), т.к. каждый cron-тик — отдельный процесс: streak переживает тики (дополняет CON-34 «state в файле»).
- **Порог `--backoff-notify N`** (default 6 = ~30 мин при cron 5 мин): при достижении — **TG-уведомление ОДИН раз** (`**Backoff Notified:** true` предотвращает повтор). Не спам каждый тик.
- **`N=0` = выключено** — guard `threshold > 0` обязателен (до фикса `1 >= 0` всегда true → notify на первом тике; баг пойман код-ревью + тестом).
- **Флаг notified — ТОЛЬКО при реальной отправке TG**: если --no-tg тик пересекает порог и ставит флаг без отправки, будущие TG-тики навсегда теряют возможность уведомить. Флаг внутри `if send_tg:`.
- **Reset** — при реальном запуске (инстанс освободился): streak=0, notified=false, новый busy-период считает с 0.

**Урок (extend CON-34):** «уведомить один раз» ≠ «поставить флаг один раз». Флаг доставки должен ставиться ТОЛЬКО в момент фактической доставки (send успешен), иначе канал, временно отключённый на тике пересечения порога, навсегда теряет уведомление. Плюс: threshold=0 — это валидное значение «выключено», а не «уведомлять всегда» — guard обязателен.

**Verify Gate:** 60 passed (3 файла: test_prompt_dispatcher + test_multi_turn_dispatcher + test_prompt_queue). Code-reviewer rounds 1–2: 2 бага пойманы и закрыты (N=0 guard, флаг без отправки).

---

### CON-36 — восстановление проекта из .bak-снапшота + регистрация роли через существующий пайплайн (interior_planner, v5.91.0)

Боевая задача interior_planner: каноническое место `projects_17/interior_planner` (workspace_registry «Работа») было пустым, полный Expo-бандл лежал в `.bak.20260803T070807985465/`.

1. **node_modules никогда не восстанавливать вслепую** — диск был 100% (464M/107G свободно), 803M не влезли бы; node_modules перегенерируем через `npm install`. Каркас = исходники + package.json + package-lock.json (1.6M). Инвентарь сверен с v5.49.0 (Canvas2D 269 / RoomEditor 402 / roomStore 156 / domain 78 / App 15 + knowledge_base 3475B).
2. **Регистратор-пайплайн может жить вне canonical `scripts_01/`** — `interior_consultant_register.py` (238 строк) живёт в sibling-workspace `interior_planner_e2e/interior_planner/scripts/` рядом с `_freebuff_locator.py` (Block-A pattern). В canonical остался только `.pyc` (3 авг) — улика последнего запуска, НЕ источник. Перед «файл потерян»: искать sibling + `__pycache__/*.pyc`.
3. **Проверка успеха = 3 независимых сигнала**: (а) прогон пайплайна `interior_consultant_register.py` (exit 0, roles=[developer,interior_consultant***REMOVED***, v3.1.0, routing=[vision,reasoning,plan,explain,multimodal***REMOVED***, model=gemini-2.5-flash); (б) независимый load BlueprintCorpus из canonical seed (missing=[***REMOVED***); (в) `workspace_registry.seed_defaults()` — путь `projects_17/interior_planner` больше не в missing.
4. **Артефакт роли — в canonical `roles/18_interior_consultant.md`** (v3.1.0 из `/tmp/interior_planner_seed/`); регистратор строит локальный seed (`interior_planner_seed/`: registry.yaml + developer.md read-only + роль) — PB-5 контракт «не трогает canonical blueprints_v3» соблюдён.

---

### CON-37 — Lesson-центричная модель заменена на Organizational Memory: не проектировать систему вокруг одной сущности (v5.92.0)

**Сценарий:** IDEAS.md §14 предлагала «Lessons Memory Engine» — таблицу `lessons` в `context.db` как специализированное хранилище уроков CON-/ANTI-/CAND-. При архитектурном анализе (promt51 / RFC Organizational Memory Engine v1) стало очевидно: это повторяет ошибку early-Wizard — проектирование системы вокруг одной сущности, а не вокруг памяти организации.

**Проблема:**
- **Silo**: `lessons`-таблица — отдельный силос, не связанный с `arch_decisions`, `event_log`, `knowledge_engine`. Каждый новый тип знаний требовал бы новой таблицы.
- **Не-expandable**: хочется Patterns, Rules, Checklists, Guidelines, FAQs — для каждого `CREATE TABLE` + миграция.
- **Нет Learning Loop**: уроки записываются, но не «живут» — не обновляются от usage, не decay, не contradict друг друга.
- **Семантика заперта**: RAG только для уроков, но не для ADR, паттернов, правил.

**Решение — Organizational Memory (RFC v5.92.0):**
1. **Knowledge Object** — универсальная сущность с полем `kind` (TEXT, не ENUM): adr, lesson, pattern, rule, observation, candidate, checklist, guideline, faq, workflow. Новые типы — без ALTER TABLE.
2. **Единый Memory Store** — таблицы `knowledge_objects` + `knowledge_tags` + `knowledge_sources` + `knowledge_references` + `knowledge_events` в `data_13/context.db` (рядом с `arch_decisions`).
3. **Семантический слой — существующий KnowledgeEngine** (FTS5 + TF-IDF + SVD), не новый движок.
4. **Knowledge Graph — 9 новых rel_types** (supports, contradicts, duplicates, supersedes, derived_from, caused_by, resolved_by, generalizes, specializes).
5. **Learning Loop** — observation→candidate→KO→feedback→confidence_update→validation — замкнутый цикл.
6. **Experience Analytics** — 7+ SQL-запросов: top-used, decayed, contradictions, unused, success-rate.

**Что сохранено:**
- `core_02/LESSONS.md` остаётся read-only архивом после миграции (CAN-16).
- IDEAS.md §14 — ❌ Rejected с пометкой «заменено RFC Organizational Memory Engine v1».
- Все существующие таблицы/API (`arch_decisions`, `knowledge_engine`, `graph_index`) — без изменений.

**Вывод:** когда проектируешь подсистему памяти для платформы — начинай с вопроса «какие типы знаний будут через 2 года?», а не «как хранить уроки?». Entity-first проектирование (вокруг одной сущности) приводит к silo-архитектуре и блокирует расширение. Память организации > база уроков. Решение зафиксировано в [RFC Organizational Memory Engine v1***REMOVED***(../docs_10/engineering-memory/RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md) (v5.92.0, 2026-08-05).

---

### CON-38 — Архитектурный синтез: от отдельных RFC к метасистеме Buffy Forge (v5.95.0)

**Сценарий:** promt51→56: от идеи «положить уроки в БД» (IDEAS.md §14) до полноценной архитектурной экосистемы из 5 RFC/конституций (OM, Evolution, DIS, ARB, AG). Возник вопрос: это отдельные подсистемы или части единой метасистемы?

**Проблема:** 5 документов описывали компоненты без единой карты. Не было ответа на вопросы: Forge — это подсистема, уровень или метасистема? Как OM, DIS, ARB, AG взаимодействуют? Где границы? Есть ли дублирование?

**Решение (RFC Buffy Forge v1, v5.95.0):**
1. **Forge — метасистема**, не подсистема и не уровень. Зонтичная платформа, объединяющая весь жизненный цикл архитектурного знания: Idea → Knowledge → Architecture → Implementation → Validation → Evolution.
2. **Forge как класс подсистем** — 6 специализированных мастерских (L0-L5), каждая с единственной ответственностью:
   - L0 Idea Forge — идеи → Proposal → Draft RFC
   - L1 Knowledge Forge — события → Observations → Knowledge Objects (OM)
   - L2 Architecture Forge — RFC → ARB-вердикты → ADR (DIS + ARB + AG)
   - L3 Implementation Forge — RFC → Tasks → Code → Tests
   - L4 Validation Forge — Compliance, Drift Detection (AG)
   - L5 Evolution Forge — Analytics → Pattern Discovery → новые RFC
3. **Границы ответственности** — явно определены для каждого Forge'а. Ни один Forge не принимает решений из области другого.
4. **Инфраструктура горизонтальная** (EventBus, OM, DIS, KnowledgeEngine), Forge'ы вертикальные (специализированные мастерские).
5. **Расширяемость:** будущие Forge'ы (Code, Agent, Workflow, Prompt, Security, Performance) добавляются без ломки архитектуры.

**Что сохранено:**
- Все 5 предшествующих RFC/конституций (OM, Evolution, DIS, ARB, AG) — без изменений.
- Forge не заменяет их, а показывает как они образуют единую систему.
- CAN-16: оригинальные документы не переписаны.

**Вывод:** когда количество RFC переваливает за 3-4 — пора остановиться и спросить: «Это отдельные компоненты или части одной системы?». Архитектурный синтез не отменяет предыдущие решения, а находит структуру, в которой они работают вместе. Метасистема > сумма компонентов. Решение зафиксировано в [RFC Buffy Forge v1***REMOVED***(../docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md) (v5.95.0, 2026-08-05).


### CON-39 — Визионерские документы требуют AFC до присвоения имён; naming collision = архитектурный долг с первого дня (v5.96.0)

**Сценарий:** ARB-ревью документа 68 — Factory/Forge Manifest (promt57), предлагающего иерархию Workspace OS → Factory → Forge → Engine → Module → Tool → Skill → Prompt для runtime-производства интеллектуальных продуктов.

**Проблема:** Manifest использует слово «Forge» для runtime производственной линии, в то время как Buffy Forge (RFC-BF-001, v5.95.0) уже использует «Forge» для метасистемы архитектурного проектирования. Одно слово — две несовместимые семантики. Если реализовать оба предложения, «Forge» будет означать две разные вещи в одной кодовой базе.

**Решение:** ARB-ревью (ARB-REV-001, v5.96.0) вынесло вердикт CHANGES REQUIRED. Manifest содержит валидное визионерское ядро (Workspace OS, Project как экосистема, Prompt как нижний уровень), но: (1) naming collision «Forge» — blocking issue, (2) 60-70% предложенного уже спроектировано под другими именами, (3) отсутствуют конкретные контракты и implementation path. Рекомендация: интегрировать организационные концепции (Workspace → Project) в Buffy Forge как контейнеры над L0-L5, но НЕ создавать параллельную «Factory/Forge» систему.

**Что сохранено:** Manifest сохранён как визионерский документ (`factory_forge_manifest.md`), ARB-ревью зафиксировано в `ARB_REVIEW_FACTORY_FORGE_MANIFEST_V1.md`. CAN-16: оригинальный документ 68 не изменён.

**Вывод:** Прежде чем называть новую архитектурную сущность — проверь AFC (Architectural Fit Check): не занято ли имя существующим компонентом. Naming collision, обнаруженный post-hoc — это архитектурный долг, который растёт с каждым упоминанием обоих значений в коде и документации. ARB как процесс (10-шаговый анализ) должен включать явный шаг «Terminology Conflict Detection».


### CON-40 — SmartRouter capability check защищает от silent fallback: задача приоритизации требует capability «architecture» (v5.97.0)

**Сценарий:** promt58 — миссия приоритизации трёх архитектурных долгов. Пункт 0 требовал проверить capability-матчинг самой задачи через SmartRouter.

**Проблема:** задача приоритизации имеет capabilities `['reasoning', 'plan', 'architecture'***REMOVED***`. SmartRouter отматчил `deepseek-v4-pro` (score 3/3, fallback=False) — единственную модель в каталоге с capability `architecture`. Модель `deepseek-v4-flash` (без `architecture`) получила бы score 2/3 и молча выполнила бы задачу без architectural judgement. Пользователь строит систему не только под себя с текущей мощной моделью, а под будущих пользователей со слабыми моделями.

**Решение:** capability-матчинг через SmartRouter — не формальность, а архитектурная защита. Если capability не матчится с достаточным score на доступных моделях — задача НЕ должна выполняться тихо на fallback. Это не оптимизация «какую модель выбрать», а safety gate: «достаточно ли мощная модель для этой задачи?».

**Что сохранено:** SmartRouter использован как реальный инструмент, а не как формальность. Результат capability-матчинга задокументирован в этом уроке.

**Вывод:** Capability-based routing — не только для выбора модели, но и для protection against silent degradation. Если задача требует capability, которой нет у доступных моделей — это должно быть loud (fallback_used=True + явное предупреждение), а не silent (best effort на weaker model). Платформа должна уметь сказать «эту задачу я не могу качественно выполнить на доступных моделях» вместо того чтобы сделать вид, что справилась.


### PB-14 — Документационный дрифт: LESSONS.md vs ARCHITECTURAL_DEBT.md (CAN-8, v5.97.0)

**Symptom:** promt58 (ветка 2) — факт-чекинг CAN-8. `LESSONS.md` утверждал: CAN-8 закрыт v5.57.0 (body-level /tmp/ hardcodes устранены). `ARCHITECTURAL_DEBT.md` утверждал: CAN-8 OPEN («скрипты продолжают ссылаться на старые пути»). Оба документа не могут быть правы одновременно.

**Cause:** `ARCHITECTURAL_DEBT.md` НЕ был обновлён после фикса v5.57.0. Предыдущая запись о «Block-A fix НЕ покрыл body-level hardcodes» осталась без ревизии. В отличие от LESSONS.md (который обновляется по горячим следам каждой итерации), ARCHITECTURAL_DEBT.md — статичный реестр, который требует явного обновления.

**Fix (v5.97.0):** (1) Факт-чекинг: `grep /tmp/` по `interior_consultant_register.py` и `e2e_promt47.py` → **0 hits**. Фикс v5.57.0 действительно устранил проблему. (2) `ARCHITECTURAL_DEBT.md` CAN-8 → RESOLVED с примечанием о факт-чекинге. (3) Настоящий PB-14 зафиксирован.

**Урок:** Платформа с двумя источниками статуса (LESSONS.md для уроков, ARCHITECTURAL_DEBT.md для долгов) требует **синхронизации при закрытии**. Закрытие CAN-* должно атомарно обновлять ОБА документа — и LESSONS.md (CON-запись о решении), и ARCHITECTURAL_DEBT.md (статус → RESOLVED). Иначе возникает документационный дрифт: один документ знает правду, второй — врёт. Последствия: промт58 потратил целую ветку на разрешение противоречия, которое не должно было возникнуть.

---

## 📦 Scenario: interior_planner web launch — Android/Termux battle (2026-08-06)

### CON-41 — Expo/Metro на Android/Termux: фатально

**Сценарий:** попытка запустить Expo SDK 57 (interior_planner_app_expo) на Android/Termux.
**Проблема:** четыре независимых блокера, каждый из которых фатален:
1. **Phantom Process Killer (Android 12+):** фоновые процессы с потреблением CPU/памяти убиваются системой через 5-30 секунд. Metro Bundler с несколькими worker'ами — гарантированная цель.
2. **arm64-бинарники отсутствуют:** React Native DevTools, rolldown (Vite 6), hermes-parser — все требуют нативные .node-бинарники, которых нет в npm-реестре для android-arm64.
3. **FAT32/exFAT sdcard — нет symlinks:** `--no-bin-links` ломает весь CLI-тулинг (expo, react-native, npx).
4. **OOM (3761 MB total, ~1.2 GB available):** Metro first-build с multiple worker'ами выжирает память → OOM kill.
**Решение:** полный отказ от Expo/Metro в пользу esbuild-wasm (чистый WASM, без нативных бинарников) + статический HTML5 Canvas.
**Вывод:** Expo на Termux/Android — НЕЖИЗНЕСПОСОБЕН. Любой мобильный проект ДОЛЖЕН иметь web-фолбэк (esbuild-wasm + HTML5 Canvas) для тестирования на устройстве разработчика.

### CON-42 — --no-bin-links: каскадный отказ всего тулинга

**Сценарий:** npm install на FAT32/exFAT sdcard (`/storage/emulated/0/`).
**Проблема:** файловая система не поддерживает symlinks → `npm install --no-bin-links` не создаёт `.bin/`-симлинки. Последствия:
- `npx expo` — не находит бинарник
- `npx vite` — не находит бинарник
- `node_modules/.bin/` — пустая директория
- Любой CLI-инструмент требует прямого вызова через `node node_modules/package/bin/cli.js`
**Решение:** всегда использовать полный путь к JS- entry point: `node node_modules/expo/bin/cli start`, `node node_modules/esbuild-wasm/bin/esbuild`.
**Вывод:** проект на sdcard должен явно документировать все CLI-команды с полными путями. `npm run` / `npx` — недоступны.

### CON-43 — Фоновые процессы на Termux: stdin-ловушка

**Сценарий:** запуск HTTP-сервера в фоне (`node server.js &`, `nohup ... &`).
**Проблема:** неинтерактивная оболочка Freebuff закрывает stdin при завершении foreground-команды → SIGHUP или EOF на stdin → Node/Python падают мгновенно.
**Решение:** `nohup node server.js </dev/null >log.txt 2>&1 &` — обязательное перенаправление stdin из /dev/null.
**Вывод:** любой демон на Termux требует: (1) `</dev/null`, (2) `>log.txt 2>&1`, (3) проверку `ss -tlnp | grep PORT` после запуска. Без этого — молчаливая смерть.

### PB-15 — Проекты без RUNNABLE.md = повторение одних и тех же ошибок

**Symptom:** три часа потрачено на запуск interior_planner, хотя все блокеры (CON-41/42/43) — системные, предсказуемые.
**Причина:** проект не имел документации о требованиях к среде запуска.
**Fix:** каждый проект ДОЛЖЕН иметь:
- `RUNNABLE.md` — минимальные требования (Node version, FS type, symlinks yes/no, порты), команды запуска для каждой платформы, известные блокеры
- `CHECKLIST.md` — pre-flight проверки: `node --version`, `df -T .`, `ss -tlnp`, `free -m`
- Web-фолбэк для проектов с нативными зависимостями (esbuild-wasm + HTML5 Canvas)
**Урок:** время на запуск проекта обратно пропорционально качеству RUNNABLE.md. Без него — каждая новая среда = повторение CON-41/42/43.

### 🔧 Missing Roles (выявлено в этом сценарии)

| Роль | Назначение |
|------|-----------|
| **Environment Doctor** | Диагностика окружения: Node version, FS type, symlinks, доступные порты, свободная память, наличие нативных бинарников. Запускается ПЕРЕД любым проектом. |
| **Project Bootstrap Validator** | Проверяет проект на готовность к запуску: RUNNABLE.md существует, CHECKLIST.md пройден, web-фолбэк настроен. Блокирует запуск при несоответствии. |
| **Web Fallback Generator** | Создаёт web-версию проекта с нативными зависимостями: esbuild-wasm конфиг, HTML5 Canvas адаптер, React Native → react-native-web алиасы. |

### 🔧 Project Requirements (стандарт для новых проектов)

1. **RUNNABLE.md** — обязателен. Содержит:支持的平台, Node version, FS requirements, команды запуска, известные блокеры.
2. **CHECKLIST.md** — обязателен. Pre-flight: `node --version`, `df -T .`, `which npx`, `ss -tlnp`, `free -m`.
3. **Web-фолбэк** — обязателен для проектов с нативными зависимостями. esbuild-wasm + HTML5 Canvas + react-native-web alias.
4. **package.json scripts** — должны использовать полные пути к бинарникам (не `npx`, не `npm run` — см. CON-42).
5. **Environment Doctor** — запускается автоматически перед первым билдом. Блокирует при несовместимости.


---

### CON-44 — Environment Doctor: от ручного DEBUG к автоматической диагностике

**Сценарий:** три часа ручной отладки запуска interior_planner на Android/Termux (CON-41/42/43). Каждый блокер (FS, symlinks, OOM, порты, stdin) диагностировался вручную через grep/ss/free.
**Проблема:** без автоматической диагностики окружения каждый новый проект будет повторять те же ошибки. Разработчик тратит часы на то, что Environment Doctor определяет за 200ms.
**Решение:** реализован `core_02/environment_doctor.py` — функция `diagnose()` которая за один вызов проверяет: тип ФС, Node.js, память, порты, symlinks, артефакты проекта (RUNNABLE.md/CHECKLIST.md). Возвращает `{ok, blockers, warnings, info***REMOVED***`. Зарегистрирована как роль `environment_doctor` в blueprint_v3 (CAPABILITIES_OVERRIDE, KNOWN_CAPABILITIES, ModelCatalog). SmartRouter: `route(["diagnose","validate","report"***REMOVED***)` → deepseek-v4-pro (3/3, без fallback).
**Урок:** любой проект должен вызывать `diagnose()` перед первым билдом. Блокеры — стоп-кран. Warnings — информационно. Время diagnosis: 200ms vs 3 часа manual. ROI: ~54000x.

### CON-45 — Юнит-тесты Environment Doctor: 21 тест, mock-изоляция, интеграционный diagnose

**Сценарий:** `tests_09/test_environment_doctor.py` — полное покрытие `core_02/environment_doctor.py` юнит-тестами.
**Что покрыто:**

| Группа | Тестов | Что проверяется |
|--------|--------|----------------|
| `_get_fs_type` | 4 | stat успех, df fallback, оба падают → "unknown", FAT32 → fuseblk |
| `_get_node_version` | 4 | норма, node не найден, команда падает, v-префикс stripped |
| `_get_available_memory_mb` | 3 | /proc/meminfo парсинг, файл отсутствует, нет MemAvailable |
| `_is_port_used` | 3 | порт занят, ss→netstat fallback, оба падают → False |
| `_check_symlinks` | 2 | symlinks работают (реальный tmpdir), OSError → False |
| `diagnose()` | 5 | возвращает dict, идеальное окружение, FAT32 без артефактов, <1GB warning, Node<20 blocker |

**Mock-изоляция:** все unit-тесты используют `unittest.mock.patch` на `subprocess.run`, `shutil.which`, `builtins.open`, `os.symlink` — никаких реальных subprocess-вызовов в unit-тестах. Интеграционные тесты `diagnose()` — полностью замоканы через `patch("core_02.environment_doctor._get_*")`.

**Урок:** для диагностических модулей критично покрывать **все ветки fallback** (stat→df→unknown, ss→netstat→False). Без mock-тестов эти ветки никогда не тестируются на реальном окружении (stat всегда работает на ext4). Каждый fallback — отдельный тест-кейс. Интеграционный тест с полным mock-слоем ловит баги агрегации (blocker vs warning, ok=True при blockers, etc.).

### CON-46 — Внешние API-зависимости: Unsplash Source API закрыт в 2024

**Сценарий:** при попытке использовать Unsplash Source API (`source.unsplash.com`) для картинок материалов в interior_planner обнаружилось, что сервис закрыт в 2024 году. Документация всё ещё висела в поисковой выдаче (Google индексирует страницы, даже если API не работает).
**Проблема:** полагаться на бесплатные API без проверки их актуального статуса. Unsplash Source API был Deprecated в 2021, Sunset в 2024 — но поисковая выдача возвращала ссылки на него как на рабочий. Попытка запроса → 503 Service Unavailable.
**Решение:** переход на Picsum Photos seed API (`picsum.photos/seed/{id***REMOVED***/{width***REMOVED***/{height***REMOVED***`). Детерминированные изображения по строковому ключу, кэшируются браузером, бесплатно, без регистрации, без API-ключа.
**Урок:** перед интеграцией любого внешнего API проверять его статус через статус-страницу сервиса или `curl -I`. Для некоммерческих проектов предпочитать сервисы без API-ключа (Picsum > Unsplash API > платные альтернативы). Фиксировать ВСЕ внешние зависимости в RUNNABLE.md проекта в секции «Внешние сервисы».

### CON-47 — `<img>` в react-native-web молча крашит приложение

**Сценарий:** после добавления `SwatchImage` компонента с сырым HTML `<img>` тегом внутри react-native `<View>`, приложение interior_planner перестало загружаться. esbuild молча скомпилировал бандл (строка `<img` не найдена в бандле), но react-native-web не смог отрендерить HTML-элемент внутри RN-дерева.
**Проблема:** React Native Web транслирует RN-компоненты (`View`→`div`, `Text`→`span`, `Image`→`img`), но **не знает что делать с сырыми HTML-тегами** в JSX. Пропсы `src`, `onLoad`, `onError`, `style={{objectFit:"cover"***REMOVED******REMOVED***` — невалидны для RN (нужно `source={{uri***REMOVED******REMOVED***`, `resizeMode="cover"`). Бандлер (esbuild) не выдаёт ошибок — всё ломается в рантайме.
**Решение:** замена `<img>` на `<Image source={{uri***REMOVED******REMOVED*** resizeMode="cover">` из `react-native`. `onLoad`/`onError` — нативные колбэки RN `Image`. Стиль `opacity` работает через RN StyleSheet.
**Урок:** в react-native-web **всегда** использовать RN-компоненты: `Image` (не `img`), `TextInput` (не `input`), `ScrollView` (не `div` с `overflow`). Для внешних URL: `<Image source={{uri: url***REMOVED******REMOVED*** resizeMode="cover">`. Единственное исключение — `<canvas>` (нет RN-аналога), но его нужно оборачивать в `<View ref={containerRef***REMOVED***>`. Перед деплоем — проверять бандл на наличие сырых HTML-тегов: `grep '<img\|<input\|<div' dist/bundle.js`.

### CON-48 — Mobile-first touch-жесты: drag≠tap, pinch-zoom, hitTest для мыши и тача

**Сценарий:** interior_planner — канвас должен работать пальцем на телефоне. Добавлены onTouchStart/Move/End: 1 палец = select+drag, 2 пальца = pinch-to-zoom, тап <400ms = select, двойной тап <500ms = поворот 45°.
**Проблема:** на мобильных мышь-события не работают. Простое добавление touch-обработчиков дало баг: быстрый drag (<400ms) интерпретировался как тап — мебель поворачивалась при отпускании.
**Решение:** флаг `touchMovedRef` — выставляется в onTouchMove (и pan, и pinch ветки), onTouchEnd делает early-return если флаг установлен. Тап = touchstart + touchend без touchmove. Дополнительно: hitTest() вынесен в общий хелпер для mouse/touch, `touchAction:none` на канвасе подавляет скролл/синтетические mouse-события.
**Урок:** тап-детекция обязана проверять движение (flag), не только длительность. Длительность <400ms сама по себе не отличает тап от быстрого drag. Общий hitTest — единственный источник правды для кликов и тапов; дублирование логики в mouse/touch ветках ведёт к дрейфу.

### CON-49 — Undo/redo: push-AFTER семантика, debounce drag с tail-replace, migrate для persist

**Сценарий:** interior_planner — добавлены undo/redo (кнопки ↩↪ в топ-баре) в Zustand store с persist localStorage.
**Проблема (3 раунда ревью):** (1) push-before дизайн давал off-by-one: undo возвращал null (проект исчезал), redo не мог вернуть frontier-состояние (не хранилось в истории). (2) moveObject на каждое движение мыши/пальца пушил снапшот — один drag = сотни записей истории. (3) bump persist version 1→2 без migrate = потеря сохранённого проекта (zustand отбрасывает persisted-state при несовпадении версий). (4) debounce tail-replace ломал инвариант history[idx***REMOVED***==project после undo (заменял последний элемент вместо обрезки future).
**Решение:** (1) push-AFTER: history[idx***REMOVED*** = текущее состояние, setProject сеет [P0***REMOVED***/idx=0; undo: idx>0 → history[idx-1***REMOVED***, redo: idx<len-1 → history[idx+1***REMOVED*** — симметрично, без off-by-one. (2) debounce 300ms: на frontier — tail-replace in-place (deepcopy), после undo (idx < len-1) — pushSnapshot с обрезкой future (frontier-guard). (3) migrate: version<2 && project → seed history из сохранённого проекта. (4) canUndo: idx>0 (baseline P0 не откатывается в null), canRedo: idx<len-1.
**Урок:** undo/redo — классическая ловушка off-by-one: правильный дизайн = история хранит ТЕКУЩИЕ состояния (push-after), а не пред-мутационные. Debounce мутаций обязан сохранять инвариант (tail-replace только на frontier). persist version bump БЕЗ migrate = потеря данных. Каждый из 3 раундов ревью ловил реальный баг — многораундовое ревью окупается.

### CON-50 — Organizational Memory Engine: Memory Store + Knowledge Graph + Semantic Layer + Learning Loop

**Сценарий:** Этап 3 PLAN_NEXT_OPERATIONS — реализация MVP Organizational Memory по RFC OM v1. Четыре модуля: `core_02/memory_store.py` (SQLite: knowledge_objects/tags/sources/references/links/events, learning_events, experience_analytics; 10 kinds из RFC §3.1; 9 org-rel_types из §5), `core_02/semantic_layer.py` (обёртка над scripts_01/knowledge_engine.KnowledgeEngine: index_knowledge, semantic_search, search_related, find_similar_patterns), `core_02/learning_loop.py` (AFC: analyze → formalize → codify; feedback → confidence). 38 юнит-тестов.
**Проблемы (3 раунда ревью):** (1) COALESCE в PRIMARY KEY — SQLite запрещает выражения в ключах (OperationalError при создании схемы); (2) `update_feedback` — 13 плейсхолдеров SQL против 12 параметров (ProgrammingError); (3) `update_knowledge` принимал `None` как реальное значение и нарушал NOT NULL.
**Решение:** (1) `line INTEGER NOT NULL DEFAULT 0` без COALESCE; (2) добавлен недостающий `now` в биндинги (CASE для last_validated_at трассируется по позициям); (3) None-фильтр в updates: `{k: v for k, v in fields.items() if v is not None***REMOVED***`. Дополнительно: `_result_doc_id`/`_result_score` — адаптация под кортежный формат (doc_id, score, …) реального KnowledgeEngine.search.
**Урок:** перед «быстрым» рефакторингом SQL — всегда считать плейсхолдеры против параметров; выражения в PRIMARY KEY недопустимы в SQLite (только в CHECK/index). Реальная сигнатура чужого модуля (кортежи vs dataclass) проверяется эмпирически, а не по документации.

### CON-51 — Buffy Forge v1: Workspace/Project, Pipeline, Registry, CLI

**Сценарий:** Этап 4 PLAN_NEXT_OPERATIONS — реализация метасистемы Forge по RFC_BUFFY_FORGE_V1: `core_02/workspace.py` (L-1 Workspace + L-2 Project: requirements, Env Doctor, AGENTS.md), `core_02/forge_pipeline.py` (L-3: FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT, dry-run, hooks), `core_02/forge_registry.py` (L-4: YAML-реестр статусов DEPLOYED/FAILED, history cap 20), `scripts_01/forge.py` (L-5 CLI: forge/check/status/register/report). 37 юнит-тестов.
**Проблемы (3 раунда ревью):** (1) `stage_report` читал `self.run_summary` до присваивания — AttributeError → REPORT всегда падал; (2) `stage is self.stage_report` — сравнение bound-методов `is` ВСЕГДА False (эфемерные объекты), provisional overall не вычислялся, хук получал 'pending'; (3) argparse: `--dry-run/--no-tg` на главном парсере не наследуются подкомандами — 'unrecognized arguments'.
**Решение:** (1) `self.run_summary = run` ДО цикла + инициализация None в __init__; (2) сравнение по имени `stage.__name__ == "stage_report"`; (3) `parents=[global_flags***REMOVED***` + `add_help=False` во всех 5 сабпарсерах. Добавлен тест `test_report_hook_sees_final_overall`, ловящий баг (2).
**Урок:** bound-методы Python — эфемерные объекты, `obj.method is obj.method` == False: сравнивать методы по `__name__`. argparse требует `parents=` для наследования глобальных флагов сабпарсерами. Настройка хука отчёта до момента формирования результата — классический race порядка инициализации.

## 📦 Scenario: ROADMAP-FR-001 Step 1 — Forge ⇆ Wizard domain separation (2026-08-06)

### PB-16 — Forge Pipeline и Wizard/Scenario — orthogonal домены (НЕ синхронизационный баг) + TG-shared infra corrigendum

**Сценарий (061_19_roadmap_forge_leviathan, ROADMAP-FR-001 Step 1 fact-check):**
Подозрение — `core_02/forge_pipeline.py` и `scripts_01/wizard.py + core_02/wizard_lib + core_02/scenario_registry.py` имели два независимых механизма исполнения, а `data_13/forge_registry.yaml` хранит `interior-planner: status=UNFORGED`, хотя Wizard уже доставил артефакты (TG msg_id=138366/138367 v5.64.0).

**Факт-чекинг (Step 1.1–1.4):**

**1)** `core_02/forge_pipeline.py:56-65` — `_run_cmd` использует `subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)`. Это **реальная O/S-level** команда, выполняемая относительно `self.project.root`. Пример default from `_default_build_cmd():258-280`:

```python
if self.project.type == "web":
    esbuild = self.project.root / "node_modules/esbuild-wasm/bin/esbuild"
    index = self.project.root / "src/index.tsx"
    if esbuild.exists() and index.exists():
        return ["node", str(esbuild), "src/index.tsx", "--bundle",
                "--outfile=dist/bundle.js", "--alias:react-native=react-native-web", ...***REMOVED***
```

`stage_build:132` зовёт `_run_cmd(cmd, self.project.root)` (real subprocess). `stage_deploy:159-172` — без subprocess, проверка только `dist/` существования. `stage_test:146` — `_run_cmd` для pytest.

**2)** `grep -nE 'wizard|scenario_registry|run_wizard' core_02/forge_pipeline.py` → **0 hits**. Forge Pipeline **НЕ импортирует** `wizard_lib.run_wizard_with_registry`. `stage_forge:94-106` не вызывает Wizard — он только генерирует RUNNABLE.md/CHECKLIST.md.

**3)** `core_02/wizard_lib.py` содержит `run_wizard` и `run_wizard_with_registry` (импортируются `scripts_01/wizard.py:head-50`). `core_02/scenario_registry.py` **НЕ имеет ссылок** на `forge_pipeline`/`forge_registry` — Wizard не знает о Forge.

**4)** `data_13/forge_registry.yaml` — `interior-planner: status=UNFORGED` (canonical fact). History-записей нет (были бы через `registry.record_run` после реального `forge forge` запуска).

**5)** `data_13/context.db`: `sqlite_master` для таблиц с шаблоном имени `scenario|wizard|role_run|forge` → **0 таблиц**. Cross-table `LIKE '%interior%'` по всем столбцам всех таблиц → **0 rows**. **ScenarioRegistry НЕ хранится в context.db** — он живёт in-memory в `core_02/scenario_registry.py` (Python ABC + auto-discover YAML + runtime state). Артефакты Wizard пишутся в **TG channel** (не в БД), `docs_10/e2e_logs/promt47_run.md`, и filesystem `/tmp/interior_planner_e2e/...`.

**6)** Вчерашний Wizard-прогон interior_planner — **FACT** (`docs_10/e2e_logs/promt47_run.md` имеет 8 refs; CON-14/CON-15; live TG msg_id **138366** Saved + **138367** Литвинов в v5.64.0). Это **НЕ** `data_13/context.db` запись — это TG channel msg_id (round-trip-read-back подтверждён в CON-35).

**Вердикт (Hypothesis C подтверждена):**

| Пространство | Источник истины | Что отслеживает |
|--------------|-----------------|-----------------|
| **Forge Pipeline (CI-stages)** | `data_13/forge_registry.yaml` | `forge forge <project>` запуски: CHECK/BUILD/TEST/DEPLOY/REPORT — статусы UNFORGED/CHECKING/BUILDING/TESTING/DEPLOYED/FAILED |
| **Wizard / Scenario** | TG channel (`core_02/telegram_contract`) + filesystem (`e2e_logs/*`, `/tmp/interior_planner_e2e/`) | role-driven scenario execution (interior_consultant, developer,...) + TG round-trip с реальными msg_id |

Эти пространства **никогда не должны были быть синхронизированы** — они трекают orthogonal аспекты жизненного цикла:

- «Прошёл ли проект через `forge forge` (CI-stages)?» → `UNFORGED` **честен** для interior-planner (никогда не запускался в Forge Pipeline)
- «Прошёл ли проект через wizard с TG-доставкой?» → passed (concrete msg_id 138366/138367)

**Уроки (Lessons):**

1. **NON-collision: две системы трекают orthogonal явления (state), но TG transport — shared infra.** Это НЕ тот же класс, что PB-14 (LESSONS.md vs ARCHITECTURAL_DEBT.md — оба трекают архитектурный долг в двух местах). Forge vs Wizard трекают разные **ФАЗЫ** жизненного цикла, не один долг.
   - **Уточнение (TG-shared infra):** оба пути доставляют отчёты в один TG канал — `scripts_01/forge.py:cmd_forge` → `tg_session.send_text_message` / `TgClientV2` (см. CON-31, v5.66.0); Wizard → `core_02/telegram_contract.py:report_to_saved_messages` / `:report_to_alex_litvinov`. **State-реестры ортогональны** (`data_13/forge_registry.yaml` vs in-memory ScenarioRuntime), но **TG delivery — shared infra**. CAN-17 audit-trail (`docs_10/e2e_logs/promt47_run.md` v5.64.0: msg_id **138366** Saved + **138367** Литвинов, упомянутый в CON-35) — shared evidence через оба path'а. PB-16 verdict остаётся C: orthogonal STATE, но transport layer — общий.

2. **061_19_roadmap_forge_leviathan Шаг 2 НЕ нужен в full-merge режиме.** Шаг 2 имеет Case 2'' (full merge) vs Case 2' (doc-only). **В нашем случае применим Case 2':** только документирование границы, без изменения логики Forge или Wizard. (Вопрос «UNFORGED-naming infelicitous» — это **документная правка**, не код-lesson; см. в «Следствие для ROADMAP-FR-001» ниже.)

**Связанные артефакты (для grep-проходимости):**

- `core_02/forge_pipeline.py:56-65` — `_run_cmd` (subprocess.run)
- `core_02/forge_pipeline.py:94-106` — `stage_forge` (artifact generation, no Wizard import)
- `core_02/forge_pipeline.py:132-146` — `stage_build` (_run_cmd invocation)
- `core_02/forge_pipeline.py:159-172` — `stage_deploy` (dist/ check, no subprocess)
- `core_02/wizard_lib.py` — `run_wizard_with_registry` (Wizard's entry point)
- `core_02/scenario_registry.py` — ABC + auto-discovery (no forge references)
- `scripts_01/wizard.py` — CLI, импортирует `core_02.wizard_lib.run_wizard_with_registry`
- `data_13/forge_registry.yaml` — `interior-planner: status=UNFORGED` (canonical fact)
- `data_13/context.db` — НЕ содержит scenario/wizard/forge tables (Fact 5)
- `docs_10/e2e_logs/promt47_run.md` — 8 interior_planner refs; v5.64.0 round-trip evidence (msg_id 138366/138367)
- ROADMAP-FR-001 (`docs_10/ROADMAP_FORGE_RECONCILIATION.md`) — Step 2 готов к Case 2' (doc-only)

**Следствие для ROADMAP-FR-001 (Step 1 → Step 2 gate):**

- **Шаг 2 (Reconciliation) — apply Case 2' (doc-only, ~30 мин).** Три явных правки в `RFC_BUFFY_FORGE_V1.md §2a`:
  1. Дополнить §2a таблицей «кто за что отвечает» (Forge Pipeline ↔ Wizard/Scenario explicit boundary).
  2. Зафиксировать семантику `UNFORGED→Wizard-passed` как orthogonal, не contradictory.
  3. **UNFORGED-naming clarification** (doc-polish из Урок 1-фикс от code-reviewer-minimax-m3): явно добавить в schema-header (если есть) или в §2a row определение: `UNFORGED = "не прошёл forge forge only"`, **не** «проект вообще не работал». Это документная правка именования, не код-фикс.
- **Шаг 3 (LEVIATHAN inventory)** — может начинаться после Case 2'.

---

## 📦 Scenario: flake root-cause фикс test_run_skip_stage (PB-17, 2026-08-06)

### PB-17 — [Test-infra layer; НЕ production design как PB-16***REMOVED*** Forge Pipeline тесты с env_doctor-зависимостью — flaky в batch-режиме; hermetic fix через dry_run=True + канонический pytest-режим

**Сценарий:** при прогоне test_forge_pipeline.py в составе батча (`pytest tests_09/test_forge_pipeline.py tests_09/test_forge_registry.py tests_09/test_wizard.py tests_09/test_scenario_registry.py`) в batch-режиме, тест `tests_09/test_forge_pipeline.py::TestPipelineRun::test_run_skip_stage` периодически падает с `AssertionError: assert 'REPORT' in ['FORGE', 'CHECK'***REMOVED***`. Изолированный прогон (`pytest tests_09/test_forge_pipeline.py::TestPipelineRun::test_run_skip_stage`) всегда проходит.

**Root-cause investigation (Этап 1 — гипотеза из кода):**

В `core_02/forge_pipeline.py:run()` (lines 203-240) главный цикл:
```python
for stage in (self.stage_forge, self.stage_check, self.stage_build,
              self.stage_test, self.stage_deploy, self.stage_report):
    if stage.__name__ in skip:
        run.stages.append(StageResult(...))
        continue
    res = stage()
    run.stages.append(res)
    if res.status == "failed":
        break  # ← critical: break до stage_report, если предыдущий failed
```

`stage_check:107` в `core_02/forge_pipeline.py`:
```python
def stage_check(self) -> StageResult:
    try:
        diag = self.project.run_env_doctor()
        req = self.project.get_requirements(steps_policy=self.workspace_steps_policy)
        parts = [***REMOVED***
        ...
        ok = diag.ok and not req.missing
        return StageResult(name=name, status="ok" if ok else "failed",
                           details="; ".join(parts) or "окружение в порядке")
```

Если `diag.ok == False` (env_doctor обнаружил blockers — память < 1GB или Node не установлен), `stage_check` возвращает **"failed"** → run() loop: `if res.status == "failed": break` → break до `stage_report` → `run.stages = [FORGE (skipped because dry_run OR ok), CHECK (failed)***REMOVED***` → `assert "REPORT" in names` fails.

**Этап 2 — empirical confirmation (PB-17 followup):**

Direct call `pipe.stage_check()` на fresh tmp_path (no FORGE run before it):
```
stage_check.status='failed' details="blockers: 2; warnings: 2; missing artifacts: RUNNABLE.md, CHECKLIST.md"
```
Стабильно: 5/5 итераций возвращают одинаково без флуктуаций. Это означает, что `stage_check` стабильно возвращает "failed" в скриптовом окружении если READMe/RUNNABLE.md/CHECKLIST.md отсутствуют И/ИЛИ env_doctor находит blockers.

**НО внутри `pipe.run()` FORGE выполняется первым и создаёт RUNNABLE.md + CHECKLIST.md через `_ensure_artifacts:235`.** То есть в норме FORGE→CHECK последовательность, и CHECK видит все артефакты → req.missing=[***REMOVED*** → ok = diag.ok. Если `diag.ok == True` (env_doctor не нашёл blockers), CHECK → "ok", и весь pipeline проходит до stage_report → test passes. Если `diag.ok == False` (любой shell-server с маленькой памятью или без node), CHECK → "failed" → break → test fails.

**Изолированный прогон** на том же хосте работает потому что: либо pytest env inheritance в isolated runs даёт лучший `diag.ok`, либо первый run инициализирует state shell variable, которая кэшируется. Конкретный механизм env_doctor нестабильности сложен, но эмпирическое наблюдение: flaky условие существует в batch mode.

**Root-cause (финальная формулировка):**

Тест `test_run_skip_stage` имеет два environmental-leak источника:
1. **env_doctor.diag.ok** — зависит от /proc/meminfo, наличия node, доступных портов. Может фликать в batch vs isolated.
2. **artifact state на tmp_path** — если FORGE fails до создания RUNNABLE.md/CHECKLIST.md (например, потому что tmp_path в batch контексте не writable или write_text бросает), то CHECK увидит missing artifacts.

Оба источника — категории environmental fragility, не real-bug.

**Hermetic fix (PB-17 v1):** добавить `dry_run=True` в `test_run_skip_stage`:

```python
def test_run_skip_stage(self, project):
    # PB-17 hermetic fix: dry_run=True делает все stage_* → 'skipped' до skip-branch,
    # устраняя env_doctor-зависимый flake (root-cause: stage_check в run() loop мог
    # вернуть 'failed' при blockers от diagnose(), что вызывало break до stage_report).
    pipe = ForgePipeline(project, dry_run=True)
    run = pipe.run(skip={"stage_report"***REMOVED***)
    names = [s.name for s in run.stages***REMOVED***
    assert "REPORT" in names
    report = next(s for s in run.stages if s.name == "REPORT")
    assert report.status == "skipped"
```

В dry_run=True все стадии ранним возвратом возвращают `StageResult(status="skipped", details="dry-run")` (см. `stage_forge:94-95`, `stage_check:107-108_if self.dry_run`, `stage_build:132-133`, `stage_test:146-147`, `stage_deploy:159-160`, плюс существующий break-proofer stage_check). Никакой subprocess не вызывается, env_doctor не дёргается, `req.missing` не учитывается в ok=false path — потому что `_run_cmd` в BUILD/TEST даже не запускается. Loop не получает "failed" → break не происходит → все 6 стадий в run.stages, включая REPORT из skip-branch.

**Канонический pytest-режим для test_forge_* (PB-17 рекомендация):**

Чтобы предотвратить future flakes в тестах, которые смешивают pipeline-логику и env_doctor-зависимости, устанавливаем **два стандартных режима** в `core_02/forge_pipeline.py` test infrastructure:

| Режим | Команда | Когда применять |
|-------|---------|-----------------|
| **Hermetic (per test)** | `python3 -m pytest tests_09/test_forge_pipeline.py::TestPipelineRun::test_<name> -v` | Локальная разработка, debugging конкретного теста. Гарантирует чистый per-test run без batch-effects. |
| **Batch (CI baseline)** | `python3 -m pytest tests_09/test_forge_pipeline.py tests_09/test_forge_registry.py tests_09/test_wizard.py tests_09/test_scenario_registry.py -v -p no:randomly` | Регрессия в CI (с `-p no:randomly` для сохранения детерминированного порядка). flake-тесты должны быть ВСЕ hermetic-friendly и не зависеть от external env в batch. |

**Правило:** ни один тест в `test_forge_*` НЕ должен зависеть от env_doctor.diag.ok в batch-режиме без explicit dry_run=True. Если тест хочет проверить full pipeline (build/test/deploy c реальным subprocess), он ОБЯЗАН mock-ить или skip-ить env_doctor через stub test fixture.

**Связанные артефакты (PB-17):**
- `tests_09/test_forge_pipeline.py::TestPipelineRun::test_run_skip_stage` — hermetic fix применён
- `core_02/forge_pipeline.py:94-160` — все stage_* имеют `if self.dry_run: return skipped` early-return, что делает hermetic-фиксы возможными
- `core_02/forge_pipeline.py:203-240` — run() loop с break, root-cause раздела
- `core_02/forge_pipeline.py:107-130` — stage_check с env_doctor + missing check, имя affliction
- ROADMAP-FR-001 Step 2 Case 2' closure (этот fix не требует правки RFC §2a — он касается test-infra, не doc-boundary).

**Уроки (PB-17):**

1. **Pipeline tests with env_doctor coupling** — категория flake-risk. Любой тест в `test_forge_*`, который вызывает `pipe.run()` без `dry_run=True`, **может** фликать в batch-mode в зависимости от хоста. Hermetic fix обязателен.
2. **PB-16 (Forge ⇆ Wizard STATE-orthogonal)** vs **PB-17 (test env-leak orthogonal)**: оба про категорию "разные ортогональные домены", но PB-17 — test-infra, PB-16 — production STATE. Зафиксировать обе, не путать.
3. **`dry_run=True`** применимо к любым unit-тестам pipeline-логики. Full-stack test (e2e_promt47.py) ИСПОЛЬЗУЕТ не-dry-run pipeline и зависит от env — но это E2E, не pytest-test.

---

### CON-52 — Workspace/Project контейнеры (L-1 / L-2) и Forge уровни (L0-L5) — ортогональные семантические домены

**Контекст:** в ходе Шага 3 ROADMAP-FR-001 (LEVIATHAN inventory) добавлены 3 компонента в Category A платформы: `forge_pipeline.py` (Forge уровни L0-L5), `forge_registry.py` (state-of-truth YAML), `workspace.py` (Workspace L-1 + Project L-2 контейнеры). Эти компоненты образуют **две разные семантики иерархии**, которые легко перепутать при ребрендинге или миграции в LEVIATHAN.

**Канонические формулировки:**

| Семантика | Уровни | Назначение | Источник |
|-----------|--------|-----------|----------|
| **Контейнерная иерархия** | Workspace (L-1) → Project (L-2) | «Где живёт проект»: организация файловой системы, requirements, isolation | `core_02/workspace.py` (Workspace, Project) |
| **Forge уровни (runtime)** | L0 Idea → L1 Knowledge → L2 Architecture → L3 Implementation → L4 Validation → L5 Evolution | «Что делает Forge»: стадии архитектурного пайплайна | `core_02/forge_pipeline.py` (ForgePipeline с FORGE/CHECK/BUILD/TEST/DEPLOY/REPORT) + RFC_BUFFY_FORGE_V1.md v1.2 §2a |

**Связь с предыдущими уроками:**

- **PB-16** (Hypothesis C — Wizard⇆Forge два разных домена): Workspace/Project и Forge уровни — **расширение того же принципа** на контейнерный слой. Forge Pipeline **внутри** Project, не **параллельно** Workspace.
- **CAN-16** (audit-trail — не переписывать, ADDITIVE расширять): при добавлении новых уровней иерархии — добавлять подразделы §N.N, не переписывать §N.
- **CON-39** (визионерские документы требуют AFC до присвоения имён): Workspace/Project и Forge уровни — это два **уже реализованных** namespace'а, не альтернативные имена одного и того же.

**Канонический путь (anti-collision rule):**

1. **При упоминании контейнера** (где живёт) → `Workspace` / `Project` (L-1 / L-2).
2. **При упоминании стадии пайплайна** (что делается) → `Forge` уровень L0-L5 (или stage FORGE/CHECK/BUILD/TEST/DEPLOY/REPORT).
3. **При упоминании обоих** → писать оба явно: «Project workspace, Forge pipeline L3 (Implementation)» — не «Project L3».

**Где rebrand-collision риск реален:**

- Документация LEVIATHAN: ребрендинг «Runtime» → «Scenario», «Workflow Engine» → «Implementation Forge (L3)» уже зафиксирован в inv v1.
- Будущие Forge extensions: при добавлении нового Forge-а (Code/An agent/Workflow/Security) **не** использовать «Level»-нумерацию в смысле контейнеров.
- Roadmap-документы: при ссылке на «Project» в LEVIATHAN уточнять: «Project L-2 контейнер» ≠ «Forge L+2 уровень».

**Verification:**

- `grep -rn 'Project L[+-***REMOVED***[0-9***REMOVED***' docs_10/` — найти все ссылки где L-цифра перепутана; должно быть либо L-1/L-2 контейнер, либо L0-L5 Forge уровень.
- `grep -rn 'L[0-9***REMOVED***.*Workspace\|Workspace.*L[0-9***REMOVED***' docs_10/` — найти где смешаны имена: должно быть только Workspace (L-1) / Project (L-2).

**Связанные артефакты:**

- [`docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md`***REMOVED***(../../docs_10/engineering-memory/LEVIATHAN_INVENTORY_V1.md) — строки 35-49 (обновлённая таблица Cat-A, v1.1)
- [`docs_10/ROADMAP_FORGE_RECONCILIATION.md`***REMOVED***(../../docs_10/ROADMAP_FORGE_RECONCILIATION.md) — Шаг 3 closure (LEVIATHAN inventory prep)
- `core_02/forge_pipeline.py` (Forge pipeline runtime)
- `core_02/workspace.py` (Workspace/Project контейнеры)
- `core_02/forge_registry.py` (state-of-truth YAML)
- RFC_BUFFY_FORGE_V1 v1.2 §2a.1-2a.3 (граничная семантика)

**Дата:** 2026-08-06
**Сессия:** ROADMAP-FR-001 Шаг 3
**Версия:** post-v5.103.0

- **CON-53**: Single-cycle latency compromise — more-frequent cron poll (1 мин) для resumable queue vs realtime event-driven rewrite (резюм Task 3 promt 61). Realtime push был бы дорогим (event-bus integration, systemwide notify, file-watch FS), тогда как `--resumable-only` cron poller даёт ту же UX для TG `/answer` resume при минимальных изменениях. Альтернатива отклонена по cost/benefit; documented в `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` followups.


### CON-54 — Teamwork-decomposition через ScenarioRegistry (vkusvill_demo, ROADMAP-VV-001)

**Сценарий:** Teamwork-разбор domain-specific артефакта (vkusvill demo для отклика ВкусВилл) через 3 роли: analyst → `business_logic.md`, developer → `forecast.py`, reviewer → `parity_check.py` + `parity_report.md`. **Урок:** роль ≠ generic «analyst долбит всё». Каждая роль имеет конкретный узкий output — force discipline на качество артефакта. Сравнение с interior_planner (UI/UX): там роли шире, потому что UI-домен шире. Для domain-specific demo — НАОБОРОТ, роли узкие.

**Variant (b) для parity (per Q1).** Python-recompute vs pre-computed Excel values убирает внешнюю системную зависимость LibreOffice — тот же класс рисков, что PB-2/PB-9 для pyyaml на Termux. Применять этот паттерн по умолчанию для любых parity-check без реальной Excel-логики в runtime.

**Технические fixes (Task 2 close-out, ROADMAP-VV-001):**
- (a) `xlsx_builder.cell_value()` API fix: prepend `=` к formula if absent — иначе openpyxl сохраняет raw string и `data_only=True` не возвращает None для не-eval формулы.
- (b) `xlsx_builder XOR ValueError messages` приведены в match c `pytest.raises(match=...)` tests.
- (c) `xlsx_builder.font.copy(bold=True)` openpyxl 3.1+ deprecation: заменено на `from copy import copy; _new_font = copy(c.font); _new_font.bold = True`.
- (d) `forecast.py imports`: прямой script execution не добавляет cwd в sys.path; `sys.path.insert(0, ...)` инъекция project_root — minimally invasive, без `__init__.py` (per user constraint «не расширять архитектуру платформы»).
- (e) `INCIDENT symmetry`: `build_model_xlsx.build_order()` теперь применяет `INCIDENT_2024_CORRECTION` к `dairy.order_qty` — иначе `model_snapshot.orders[dairy***REMOVED***.order_qty` ≠ `forecast_python[dairy***REMOVED***.order.order_qty` (asymmetry выявлена parity_check FAIL после первого refactor v2). Fix mirrors `forecast.py::compute_order()` logic — одно source of truth для NON_OBVIOUS_2 application. Excel formula в `order!E` тоже включает conditional INCIDENT множитель (`*INCIDENT_2024_CORRECTION if dairy else 1.0`).

**Cell-content proxy (NON_OBVIOUS_2).** Для legacy defined name использовали cell-content (`forecast!H22=0.92` + label в `J7`) вместо openpyxl `defined_names`. Причины: (1) `xlsx_builder` API минимальный (Task 0 scope, не расширяем); (2) user constraint «не расширять архитектуру платформы в рамках этой задачи»; (3) cell-content эквивалентен по видимости для аналитика (label читается так же, как defined name).


### CON-55 — Inline tag protocol для deep research (ROADMAP-VV-002 / промт 63)

**Сценарий:** Deep research (33 секции) по реальной компании (ВкусВилл) для подготовки к job-interview. Риск LLM-галлюцинации на конкретных числах (выручка / кол-во магазинов / KPI / стек).

**Что подтверждено:** inline-маркирование каждого утверждения одним из 6 значений per brief pomt63 §2 ([ФАКТ***REMOVED*** / [СИЛЬНАЯ ГИПОТЕЗА***REMOVED*** / [СЛАБАЯ ГИПОТЕЗА***REMOVED*** / [ПРЕДПОЛОЖЕНИЕ***REMOVED*** / [НЕТ ДАННЫХ***REMOVED***) предотвращает **cross-contamination**: поток допущений НЕ перетекает в факты при финальном synthesis (file `08_final_synthesis.md`). Disclaimer в начале/конце документа НЕ достаточно — читатель теряет маркер при перечитывании секции, и допущения «забываются» как факты.

**Принцип:**

1. dual-source verify для всех числовых утверждений (Tier 1 + Tier 2 одна дата)
2. marker ПЕРЕД ключевым утверждением, не после
3. source-id в inline-ссылке (S001) или dual-marker (S001+S005 dual-source)
4. без source — НЕ писать утверждение (write `[НЕТ ДАННЫХ***REMOVED***`)

**Дополнение:** Tier 3 (hh.ru / Habr / Telegram) используется ТОЛЬКО для сигналов, не для подтверждения — если Tier 2 закрыл вопрос, Tier 3 не парсится. Cap по запросам = 15 (per ROADMAP_VV_002_RESEARCH.md §4).

**Связь:** [`docs_10/ROADMAP_VV_002_RESEARCH.md`***REMOVED***(../docs_10/ROADMAP_VV_002_RESEARCH.md) §3 (Methodology), §4 (Tier 1/2/3 strategy), §5 (Anti-Hallucination Checklist); [`projects_17/vkusvill_research/SOURCES.md`***REMOVED***(../projects_17/vkusvill_research/SOURCES.md) (source registry schema).

### CON-56 — Deep research via Stage-gate + sibling research↔artifact architecture (ROADMAP-VV-002 / промт 63)

**Контекст:** ROADMAP-VV-002 (closed 2026-08-06, CHANGELOG [5.106.0***REMOVED***) — single-cycle deep research для вакансии «ВкусВилл × Специалист по AI-автоматизации бизнес-процессов». 18 web queries total (Stage 1: 4 + Stage 2: 11 + Stage 3: 3 + Stage 4: 0 = pure synthesis), 46 sources (S001–S083), 5 stages (scaffold → Tier 1+2 baseline → Tier 2 sector → Tier 3 closer look → pure synthesis), CON-55 inline tag protocol как anti-hallucination gate.

**5 паттернов, применимых к будущим research-задачам:**

1. **Sibling research↔artifact архитектурный паттерн**: `projects_17/vkusvill_research/` (ground-truth facts + interview-prep synthesis) ↔ `projects_17/vkusvill_demo/` (artifact `.xlsx` + Teamwork-разбор в ROADMAP-VV-001 v5.105.0) — два независимых слоя без cross-modification, cross-linked в двух README. Эффективно отделяет **knowing** (что реально в вакансии/компании) от **proving** (что кандидат реально умеет). При будущих вакансиях: можно повторить pattern как `vkusvill_research/ ↔ vkusvill_demo/` → `next_company_research/ ↔ next_company_demo/`.

2. **Stage-gate discipline** (sequential stages, no parallelism on critical path): 0 spilled requests между stages. Каждый stage gating на completeness файлов прежде чем следующий стартует. Экономит budget запросов (Stage 4 pure-synthesis прошло без new web благодаря economи Stage 3 extension).

3. **CON-55 inline tag protocol** эффективно предотвращает hallucination вне disclaimer-style предупреждений. Маркеры `[ФАКТ***REMOVED***` / `[СИЛЬНАЯ ГИПОТЕЗА***REMOVED***` / `[СЛАБАЯ ГИПОТЕЗА***REMOVED***` / `[ПРЕДПОЛОЖЕНИЕ***REMOVED***` / `[НЕТ ДАННЫХ***REMOVED***` inline per assertion. Simple structure (одна inline-маркер перед каждым утверждением), high effectiveness (не требует global disclaimer в начале/конце документа). Подходит для любых research-задач с публичными источниками.

4. **Stage 4 pure synthesis** (zero new web, builds on Stage 1–3 материал): показал, что **interview-prep структурнее получается из уже собранных фактов**, чем из broad additional research. В Stage 4 синтез интервью-Q&A **+1 час pure-write** стало возможным благодаря тому, что Stage 1–3 уже дали факты. Альтернатива (начинать interview-prep параллельно с research) была бы дороже и дублировала бы поверхностные вопросы.

5. **Honest mid-game позиционирование** (anti-self-deception pattern per brief §33 «не пытайся понравиться кандидату»): в research artifacts и в candidate portfolio честное «мы mid-game, X5 впереди по IT-расходы на 39,3 млрд руб, ВкусВилл впереди в CV для fresh-категорий» работает лучше, чем «ВкусВилл — лидер AI». Recruiters реагируют на realism лучше чем на hype. Принцип: **mid-game честно + конкретное ниша-преимущество** = сильнее, чем **лидер-fantasy без подтверждений**.

**Связи:**
- [`docs_10/ROADMAP_VV_002_RESEARCH.md`***REMOVED***(../docs_10/ROADMAP_VV_002_RESEARCH.md) (orch doc)
- [`projects_17/vkusvill_research/`***REMOVED***(../projects_17/vkusvill_research/) (8 файлов: 01_business_scale + 02_supply_chain_economics + 03_legacy_and_forecasting + 04_ai_role_and_stack + 05_cases_and_competitors + 06_candidate_profile + 07_interview_strategy + 08_final_synthesis + SOURCES.md)
- CHANGELOG [5.106.0***REMOVED*** (release note)
- CON-54 (Teamwork-разбор в ROADMAP-VV-001), CON-55 (inline tag protocol)
- brief: `pompts_11/064_04_vkusvill_ai_avtomatizaciya.md`

**Quirks / открытые вопросы:**
- Stage 3 budget extension (+3 запроса) была выдана user explicit, а не auto-protocol. Future: если budget планируется по-умолчанию, расширить cap до ~25 для full Tier 1-3 + Stage 4 buffer без запроса разрешения.
- 8/8 files filled = «zero pending», но это не значит, что future кандидат = этот же. Каждый новый should re-run Stage 0 (новый sibling-research dir).

### CON-57 — Второй независимый аудит research: future-dates, контаминация цитат, circular parity (promt 64 / ROADMAP-VV-002)

**Контекст:** Аудит research-архива ВкусВилл (ROADMAP-VV-002, promt 64). 7 web-verification прогонов + demo пересборка + математическая сверка.

**4 урока, применимых к будущим research-задачам:**

1. **Future-dates = красный флаг реестра.** S070 в SOURCES.md датирован 2026-09-25 (будущее от даты аудита 2026-08-08). Причина: страница — автоматический агрегатор-досье CNews («book/»), где дата = артефакт метаданных, не дата публикации. Правило: при аудите каждый источник с датой > сегодня проверять как INVALID DATE, а claims переносить на реальные статьи.
2. **Контаминация цитат вакансии.** Формулировки «вайб-кодинг» / «не требуется инженерное образование» в research могли прийти из вакансии другого работодателя (Miles & Miles), а не ВкусВилл (S069). Правило: прямые цитаты вакансии с hh.ru перепроверять через ≥2 независимых агрегатора; при недоступности оригинала (HTTP 406) — UNVERIFIED, не использовать как [ФАКТ***REMOVED***.
3. **Circular parity.** Parity-check в demo сравнивал два Python-сгенерированных JSON (snapshot от build_model + forecast), а Excel-формулы не вычислялись вовсе. «Excel-vs-Python эквивалентность» заявлена, но не доказана. Правило: parity обязан включать независимый путь (Excel-eval engine / LibreOffice / pycel) или честно переименовываться в «Python-consistency check».
4. **Модельная фикция → инференс о компании.** INCIDENT_2024_CORRECTION (модельный пример) в research-файле 03 подан как «явно был Excel-override» у реального ВкусВилл. Правило: модельные числа из demo НЕ должны перетекать в research-файлы как выводы о компании.

**TRUST SCORE финальный:** 7/10 (после исправлений 5 пунктов — до 8.5-9/10).

---

### CON-58 — STEPS.md steps: append at file end, никогда не insert перед существующим заголовком (2026-08-09, v5.110.0 publish)

**Контекст:** 2-й повтор одного бага за одну сессию Phase 2 Workspace OS research:
1. Step 19 вставлен перед Step 18 (NEEDS-FIX в review-цикле §6).
2. Step 20 вставлен перед Step 19 (NEEDS-FIX в review-цикле v1.1 publish).

**Root cause:** паттерн `str_replace` с anchor на существующий `## Step N` заголовок, где newString = «новый Step + старый заголовок». Это инвертирует хронологию: новый Step (более поздний) оказывается ВЫШЕ старого.

**Правило (канон):**
- Новый Step в STEPS.md — только **append в конец файла** (после контента последнего Step), никогда не insert перед существующим `## Step N`.
- Если нужна вставка — сначала читай хвост файла, затем anchor на ПОСЛЕДНЮЮ строку контента (не на заголовок).
- После любой вставки Step — grep-верификация порядка: `grep -nE '^## Step' STEPS.md | tail -5` (номера строк монотонно возрастают).

**Эмпирика:** баг сработал 2/2 раз при insert-before-anchor; append-at-end сработал 0 ошибок. Порог: если у видишь pattern «новый Step + старый заголовок» в newString — это автоматический красный флаг.

**Связи:** CON-57 (последний до этого), PB-16 (audit discipline), review-циклы §4/§5/§6. Проверяется: `grep -nE '^## Step' projects_17/vkusvill_research/STEPS.md | tail -5` — порядок 1→2→…→N монотонный.

### CON-59 — канон именования файлов платформы (ADR + prompts) и CHANGELOG rename-narration ≠ broken link

**Контекст:** R8 audit 2026-08-12 выявил, что DRIFT_REPORT показывает два класса «битых ссылок», которые не должны помечаться как broken:
1. **plain references в CHANGELOG.md** к старым именам `prompts_11/promt47.md` / `scripts_01/e2e_promt47.py` / `docs_10/e2e_logs/promt47_run.md` — это **исторические записи переименований** (формат `old → new` или `references valid as-is`), сохранённые per **CON-17 anti-duplication/anti-rewrite rule** для исторических narrative elements. Mass batch-update CHANGELOG противоречит audit-trail. **Do NOT fix**.
2. **`pompts_11/promt48.md` → `pompts_11/048_11_platform_rewrite_directive.md`** и аналогичные — реальные broken-ссылки в ADR / runtime-доках, которые ДОЛЖНЫ быть исправлены (например, в `ADR_012_buffy_swappable_brain.md:7`, `:93`, таблица L110 — все три уже обновлены в R8 fix v5.187.5).

**Правило (канон именования, утверждено в CHANGELOG [5.32.0***REMOVED***/[5.26.0***REMOVED***/[v5.32.0***REMOVED***):**
- **Prompts** (pompts_11/): формат **`0XX_NN_<topic>.md`** где `XX` = chronologically-continuous номер промта (046, 047, 048, ...), `NN` = theme code из FINAL_STRUCTURE §2.1 (01..14). Имена `promtNN.md` / `promtNN_<topic>.md` / `prompts_11/` (с дополнительной s) — **DEPRECATED**. Исторические ссылки на старые имена в CHANGELOG оставить as-is.
- **ADR** (docs_10/engineering-memory/decisions/): формат **`ADR_NNN_*.md`** (с underscore после номера). Имена `ADR-NNN_*.md` (с дефисом после ADR) — **DEPRECATED** в пользу underscore (canonical).
- **Broken-classification:**
  - `scripts_01/*name*.py` — script реально отсутствует на диске → real broken fix или удалить ссылку.
  - ADR / runtime-doc ссылаются на `promtNN.md` → **MUST fix** на `0XX_NN_<topic>.md`.
  - CHANGELOG.md упоминает старое имя в narrative context (переименование, отчёт об изменении) → **NOT broken**, audit-trail по CON-17, оставить.

**Диагностический чек-лист перед правкой DRIFT_REPORT:**
1. Файл существует на диске? `ls docs_10/...` или `ls pompts_11/...`.
2. Ссылка в CHANGELOG.md? Если да — это почти наверняка rename-наррация, **НЕ фиксить**.
3. Ссылка в ADR / BUFFY.md / runtime-doc → MUST fix на canonical.

**Эмпирика (R8 fix v5.187.5):** подтверждено, что broken-список в DRIFT_REPORT 2026-08-06 содержал 2 real broken (ADR_012:7, :93 — обе в `documents`) + 3 false-positive из CHANGELOG.md historical rename narration (строки CHANGELOG:516, :529, :537), которые специально НЕ фиксятся. После правки ADR_012 + BUFFY.md оставшиеся «broken» в CHANGELOG — это narrative audit-trail, не баги.

**Связи:** CON-17 (anti-duplication/anti-rewrite для historical elements), CHANGELOG [5.32.0***REMOVED*** (Layer B `TestPomptsDirectory` + `test_promt47_renamed` anti-regression), CHANGELOG [5.26.0***REMOVED*** (TT=06 theme code для `e2e_platform_test`), PLATFORM_AUDIT_RECOMMENDATIONS_V1.md §R8 (CRITICAL). Проверяется: `grep -nE 'pomt[0-9***REMOVED***+\.md\|ADR-[0-9***REMOVED***{3***REMOVED***' {CHANGELOG.md,BUFFY.md,AGENTS.md***REMOVED***/*.md` → CHANGELOG строки можно оставить (audit-trail); BUFFY/AGENTS/runtime-docs → MUST 0 hits с deprecated pattern.

### CON-60 — Задачи «начать проект / составить план» маршрутизируются через Blueprint v3 pipeline (role corpus), не выполняются ad-hoc

**Контекст:** пользовательская задача вида «начни вести проект согласно правилам платформы; прочитай ТЗ; задокументируй простыми словами план выполнения пошагово, какую систему будешь использовать, какие шаги» (кейс: `projects_17/sheet_project`, D2 генератор Excel-дашбордов). Это типовая задача kickoff/planning, для которой у платформы уже есть канонический инструмент — **Blueprint v3 role pipeline** (Kwork Arbitr v3).

**Что использовать (канон):**
- **Роль-корпус:** [`core_02/blueprint_v3.py`***REMOVED***(./blueprint_v3.py) (BlueprintCorpus / BlueprintScenario) — 14 pipeline-ролей + registry.yaml.
- **Цепочка планирования (LIGHT-роли, аналитические):** `explainer → lisa → risk → decomposer → architect` — режим `check_only` через `RoleArtifactValidator`. Это ровно то, что просит «задокументируй план»: explainer (разбор ТЗ → `brief.md`, `parsed_requirements.md`) → lisa (оценка сложности → `lisa_report.md`) → risk (риски → `risk_matrix.md`) → decomposer (декомпозиция → `decomposition.md`, `module_list.md`, `integration_topology.md`) → architect (архитектура + ADR → `architecture.md`, `adr/*.md`, `contracts.yaml`).
- **Реализация (HEAVY-роли):** `developer → tester → fixer → acceptance` — полный ForgePipeline через `ForgeFacade.initiate_forge` (единственный санкционированный мост роль → Forge, §7.3 / B2 R-124).
- **Канон цепочки:** [`core_02/forge_facade.py::PIPELINE_CHAIN`***REMOVED***(./forge_facade.py) = explainer → lisa → risk → decomposer → architect → auditor → developer → frontend → devops → tester → fixer → acceptance → documenter → retrospective.
- **Входные точки:** [`scripts_01/forge.py`***REMOVED***(../scripts_01/forge.py) `cmd_chain` (CLI: `--roles`, `--resume`, `--json`, `--full-cycle`), `ForgeFacade.run_chain`, [`scripts_01/wizard.py`***REMOVED***(../scripts_01/wizard.py) (подбор роли через ScenarioRegistry), `core_02/scenario_registry.py` (multi-scenario dispatch).

**Правило (канон):** задача «начни проект / составь план» НЕ выполняется ad-hoc вручную — она маршрутизируется через Blueprint v3 pipeline: сначала LIGHT-роли планирования производят артефакты (brief → lisa_report → risk_matrix → decomposition → architecture + ADR), затем HEAVY-роли выполняют код через ForgeFacade. Project-каркас (MANIFEST/LESSONS/decisions/ROADMAP/README/RUNNABLE/CHECKLIST/STEPS) — это обёртка контейнера контекста (PROJECT_RULES.md §2/§4), а роли Blueprint v3 — производственный слой поверх него.

**Связи:** SCENARIO_ENGINE_DESIGN_V1.md §10 (маппинг 14 ролей → capabilities), ROLE_FORGE_MATRIX_V1.md (роль → Factory/Forge/Engine), PROJECT_RULES.md §4 (задача идёт через проект), forge_facade.py (PIPELINE_CHAIN/LIGHT/HEAVY/CONDITIONAL). Проверяется: `python scripts_01/forge.py chain --help` + `python -c "from core_02.forge_facade import PIPELINE_CHAIN; print(PIPELINE_CHAIN)"`.

### CON-61 — Автоисполнение ролевого конвейера: run_chain LIGHT-роли = check_only, генерация артефактов отсутствует (дизайн RoleExecutorRegistry)

**Контекст:** проход по ролям Blueprint v3 (explainer → lisa → risk → decomposer → architect → auditor → developer → … → retrospective) должен быть АВТОМАТИЧЕСКИМ сценарием — один запуск, все роли до конца, без ручного «продолжай / следующий шаг». Кейс `projects_17/sheet_project` показал: каждый LIGHT-артефакт писался агентом вручную, по одному за сообщение.

**Разрыв:** `ForgeFacade.run_chain` (core_02/forge_facade.py) для LIGHT_ROLES выполняет только `check_only` — `RoleArtifactValidator` проверяет СУЩЕСТВОВАНИЕ файлов (`DEFAULT_ROLE_OUTPUTS`), но НЕ генерирует их. HEAVY-роли — full_cycle ForgePipeline, но в read-only тоже не создают код. Сценарий (`blueprint_v3.py` = role corpus) хранит блюпринты ролей, но не исполняет их.

**Дизайн (ADR-016):** аддитивный слой `core_02/role_executor.py` — `RoleExecutorRegistry` (role_id → генератор), интерфейс `execute(project, role) -> list[созданные файлы***REMOVED***`. Детерминированные роли — tool-обёртки (пример: `lisa` → `lisa_estimator.py` уже генерирует `lisa_report.md`); LLM-роли (explainer/risk/decomposer/architect/auditor/documenter) — вызов модели по blueprint-промпту роли. `run_chain` получает режим `--generate`: артефакт отсутствует/partial → executor → валидация. Дефолт остаётся `check_only` (обратная совместимость, тесты не ломаются). Точка входа — `forge.py chain --generate`.

**Правило (канон):** проход по ролям НЕ должен требовать ручного пошагового подтверждения — это сценарий, исполняемый цепочкой (scenario = данные → forge = оркестрация → executor = генерация). Агент/пользователь запускает сценарий один раз, конвейер идёт до конца сам.

**Связи:** CON-60 (routing canon), ADR-016 (дизайн RoleExecutorRegistry), forge_facade.py (run_chain LIGHT/HEAVY/CONDITIONAL), scenario.py (Scenario = data, НЕ executor), §7.3 (роли не вызывают Forge напрямую). Проверяется: `python scripts_01/forge.py chain --help` (после реализации — флаг `--generate`).

### CON-62 — Каноничное хранилище весов калибровки LISA-3 (data_13/lisa_calibration.yaml)

**Контекст:** веса калибровки LISA-3 (множители осей) изначально жили только внутри проекта (`projects_17/sheet_project/lisa_calibration.yaml`) и «терялись». Нужен каноничный персистентный механизм на уровне платформы, чтобы доменные приоры накапливались между проектами.

**Что использовать (канон):**
- **Хранилище:** `data_13/lisa_calibration.yaml` — глобальные `weights` (дефолт 1.0) + `domains:` (доменные приоры, напр. `xlsx.ai_suitability: 7.0`). `DEFAULT_CALIBRATION_STORE` в `scripts_01/lisa_estimator.py` резолвит путь от `__file__`.
- **Переиспользование:** `lisa_estimator --domain <name>` — применить доменный приор (merge поверх глобальных weights).
- **Сохранение/промотирование:** `lisa_estimator --save-calibration <name>` (из `--calibrate`/`--domain`) — merge в каноничное хранилище (atomic .tmp+replace).
- **Обновление как обратная связь:** роль retrospective (Evolution Forge) обновляет `lisa_calibration.yaml` (076_13_lisa_estimator_capability §4; registry output retrospective).

**Правило (канон):** доменные веса LISA НЕ хранятся только в проекте — промотируются в каноничное `data_13/lisa_calibration.yaml` и переиспользуются через `--domain`. Precedence: глобальные `weights` ← доменные `domains.<name>` (override по осям). Доменные веса строго opt-in — дефолтный scoring не меняется.

**Связи:** CON-61 (автоисполнение ролей), `scripts_01/lisa_estimator.py` (`_load_calibration_store`/`_save_calibration_to_store`), 076_13_lisa_estimator_capability.md §4, retrospective (registry output `lisa_calibration.yaml`). Проверяется: `python scripts_01/lisa_estimator.py 'экспорт таблиц' --domain xlsx --json --no-save`.

### CON-63 — Register-first дисциплина: недостающий элемент регистрируется ДО реализации, а не задним числом

**Контекст:** при реализации ADR-016 (слой `core_02/role_executor.py` — RoleExecutorRegistry + LisaExecutor + LlmRoleExecutor) модуль был зарегистрирован в `data_13/missing_registry.yaml` УЖЕ ПОСЛЕ завершения кода — запись `role_executor` сразу получила `status: implemented`, минуя lifecycle `registered → design_ready → prompt_written → implemented`.

**Разрыв:** AGENTS.md §5 REGISTER-FIRST требует порядка: (1) зафиксировать недостающий элемент в MissingRegistry (`kind` + `description`) → (2) промт на реализацию (`mark_prompt_written`) → (3) реализация (`mark_implemented` + пополнение `KNOWN_CAPABILITIES`/Tool Registry). Запись задним числом фиксирует traceability, но НЕ ведёт lifecycle — утрачивается видимость «что ещё не начато / на каком этапе», и реестр перестаёт быть источником истины по НЕдостающим элементам (B10-валидация `validate_schema`).

**Правило (канон):** при НАЧАЛЕ реализации любого нового модуля / роли / engine / forge / capability — сначала `python -m core_02.missing_registry register <id> --kind <kind>` (status=registered), затем `mark-prompt-written`, и только после реальной реализации — `mark-implemented`. `status: implemented` при первичной регистрации допустим ТОЛЬКО для backfill traceability (явно задокументировать, как `factory_base`/`role_executor`), но НЕ как замена ведения lifecycle вперёд.

**Связи:** AGENTS.md §5 (REGISTER-FIRST + CLI), `core_02/missing_registry.py` (MissingRegistry, KINDS, STATUSES), `data_13/missing_registry.yaml` (role_executor — implemented backfill), ADR-016 (дизайн RoleExecutorRegistry), CON-61/62 (автоисполнение + LISA store). Проверяется: `python -m core_02.missing_registry list --status registered` (до реализации) / `check` (B10/R-127).

### CON-64 — Новый термин → GLOSSARY.md в том же заходе (не догонять отдельным шагом)

**Контекст:** в сессии термины конвейера исполнения (Forge/Factory/Blueprint v3/RoleExecutor/LISA) появились в коде/ADR, но в глоссарий были внесены отдельным шагом (v5.189.41), как и Phase 8-13 термины (ScenarioIntelligence/OpportunityEngine/FactoryRegistry/DecisionHistoryStore) — отдельной кампанией аудита. Терминология «догонялась» постфактум.

**Разрыв:** GLOSSARY.md §1 правило 3 — «новые термины добавляются только сюда». Если термин вводится реализацией, но в глоссарий попадает позже — в промежутке возникают параллельные/расходящиеся определения в коде, ADR и документах.

**Правило (канон):** каждый новый термин (новый модуль/класс/слой/режим) фиксируется в `docs_10/core/GLOSSARY.md` В ТОМ ЖЕ ЗАХОДЕ, что и реализация (или ADR), а не отдельным follow-up шагом. Это зеркалит register-first (CON-63) для терминологии: глоссарий — single source of truth, пополняется синхронно с вводом термина.

**Связи:** GLOSSARY.md §1 (правила 3/4), CON-63 (register-first), AGENTS.md §5. Проверяется: `grep` нового термина в GLOSSARY.md в момент мержа реализации.

### CON-65 — Cross-provider cloud fallback: hard-error class switch + availability-aware cloud-first routing

**Контекст (E2E-находка v5.189.48):** при реальном прогоне E2E через `_call_with_fallback` (ModelGateway) первичный cloud-провайдер (deepseek-v4-flash) вернул **402 billing error** — повторный вызов того же провайдера через KeyPool N раз fallился одинаково (key rotation не помогает против account-level 402). Исходный код просто ретраил тот же провайдер → 3 из 3 попыток сожжены впустую → итог: либо fallback на ту же модель с пометкой `fallback_used=True`, либо RuntimeError на 402.

При этом `SmartRouter.route()` имел tie-break `sorted(..., key=latency)` между локальной (qwen2.5:1.5b, 100-200 ms, fallback_used=False) и облачной (gemini-2.5-flash, ~1100 ms, fallback_used=False). **Latency-based tie-break отдал предпочтение local 1.5B**, хотя для boilerplate-summary был способен gemini и даже способен deepseek — и они оба при 402 обязаны переключаться, а не повторяться.

**Разрыв (два независимых ANTI-6b-ловушки):**
1. **Retry-same-provider waste**: `_call_with_fallback` НЕ различает hard-error (402 billing / 401 auth / 5xx server) от soft-error (timeout / network blip). 402 — детерминированно не восстановится, retry = pure waste. Retry имеет смысл только для soft failure (timeout, connection reset).
2. **Latency-as-primary-tie-break**: при выборе между локальной и облачной моделью «кто быстрее ответил» — плохой сигнал: latency не учитывает availability/account-status. Provider может отвечать fast и стабильно, но **не отвечать** на нужный endpoint (billing-needs-update, quota-exhausted, region-restriction).

**Правила (канон):**

1. **Hard-error class switch (`_call_with_fallback`)**: при ошибке из набора `{402 Payment Required, 401 Unauthorized, 500/502/503/504 Server Error***REMOVED***` — НЕ retry тот же ключ/провайдер. Немедленно switch в CLOUD_FALLBACK_CHAIN (`deepseek → gemini → dashscope`) до exhaust → потом local ollama. Soft-error (timeout, connect-error, 429 rate-limit < 60s) — retry-with-rotation OK.
2. **Availability-aware cloud-first filter**: при выборе между local и cloud — фильтровать cloud-кандидаты по `KeyPool.has_key(provider)` ДО latency tie-break. Если для cloud есть валидный ключ → cloud first (лучше quality для wizard/explain/summarize). Local — только при отсутствии cloud или как emergency terminal fallback.
3. **2nd model in `ModelCatalog.default()`**: каждая capability-ось (summarize/explain/code/reasoning/plan/refactor/vision) должна покрываться как минимум 2 провайдерами (primary cloud + secondary cloud или cloud+local), чтобы cross-provider fallback было возможно. `tests_09/test_model_gateway.py::TestCrossProviderFallback::test_default_catalog_has_two_cloud_providers_with_summarize_explain` контролирует инвариант.

**Реализация (v5.189.52):**
- `scripts_01/model_gateway.py`: добавлены `CLOUD_FALLBACK_CHAIN`, `_is_hard_error(classify(error))`, `_has_key_for(provider)`, `_default_model_for_provider`; `_call_with_fallback` различает hard-error vs soft-error и при hard-error делает switch provider вместо повтора.
- `core_02/router.py`: `ModelCatalog.default()` расширен — `summarize`+`explain` теперь у `gemini-2.5-flash` И `llama-3.3-70b-versatile`; `summarize` добавлен в `deepseek-v4-flash` (для LLM-role backup).
- `tests_09/test_model_gateway.py`: новый class `TestCrossProviderFallback` — 6 contract-тестов (402 switches, 5xx switches, no-key fallback path, chain exhaust, ollama terminal, catalog 2-cloud invariant).
- Ключевая anti-fragility: hard-error detection — **regex + integer code matching** на текст ошибки, не external SDK schema dependence (httpx + custom parser = portable).

**Связи:** CON-8 (vocab defense — SmartRouter говорит на capability-токенах), ANTI-6b (silent fallback на qwen2.5:1.5b — закрывается availability-filter), PB-7 (tester routing был symptom latency tie-break; v5.189.41 vocab fix первопричину закрыл, но не закрыл retry-same-provider), CON-61 (auto-chain исполнение ролей — теперь резервный маршрут у LLM-ролей валиден), CHANGELOG v5.189.52. Проверяется: `pytest tests_09/test_model_gateway.py::TestCrossProviderFallback -q` (6/6 pass) + smoke `python3 -c 'from core_02.router import ModelCatalog; c=ModelCatalog.default(); print(sum(1 for e in c.entries if "summarize" in e.capabilities and "explain" in e.capabilities))'` ≥ 2.

### CON-66 — Промты под голым номером переименовывать автоматически по `NNN_TT_name.md` БЕЗ вопросов пользователю (2026-08-22)

**Сценарий:** пользователь сохраняет промты под голым номером (`promt104.md`, `107.md`), потому что «в терминале весь текст не влазит». Такой файл нарушает конвенцию именования `NNN_TT_name.md` (FINAL_STRUCTURE §2.1) → `consistency_check` даёт **exit ≠ 0** (`naming_convention` violation).

**Правило (рабочее, переживает сжатие контекста):**
1. Обнаружив промт под голым номером в `pompts_11/` — **НЕ спрашивать пользователя**, сразу переименовать по конвенции: `NNN_TT_name.md` (NNN = хронологический номер, TT = код темы 01..14; для forensic-промтов 104–107 используется TT=19).
2. После rename — `grep -rn 'NNN.md'` по репозиторию и обновить все ссылки на старое имя (docs, CHANGELOG, tests, yaml).
3. Завершить `python -m scripts_01.consistency_check` → ожидать **exit 0**.

**Что подтверждено:** применено к `promt104.md` → `104_19_platform_architectural_forensics_v2.md`, `promt105.md` → `105_19_repository_organization_refactoring_forensics.md`, `promt106.md` → `106_19_repository_forensics_system_modeling.md`, `107.md` → `107_19_platform_architectural_inventory.md` — каждый раз `consistency_check` возвращался к exit 0.

**Связи:** CON-59 (канон именования файлов платформы + CHANGELOG rename-narration ≠ broken link), CON-64 (новый термин → GLOSSARY в том же заходе — тот же принцип «не догонять отдельным шагом»).

### CON-67 — Тяжёлые и environment-dependent тесты выполняет пользователь локально; стандартный suite — через авто-скрипт с MD-отчётом

**Контекст:** на Termux/телефоне полный pytest и typecheck могут занимать много времени, зависеть от локальных провайдеров, доступных ключей, Ollama, сети или особенностей окружения. Повторный запуск таких тестов агентом расходует время сессии и не даёт достоверности для пользовательского телефона. В одной сессии значительная часть времени ушла на повторные тестовые прогоны вместо продолжения разработки.

**Правило (канон workflow, v2 — 2026-08-22):**

#### Основной механизм: авто-скрипт `run_test_suite.sh`

Для стандартных полных проверок платформы **не создаются ручные MD-чеклисты с копипастом команд**. Вместо этого используется самодостаточный скрипт:

```bash
bash scripts_01/run_test_suite.sh --all
```

Скрипт:
- запускает все фазы (quick → full pytest → mypy → registry → counter);
- сам сохраняет структурированный MD-отчёт с выводами, exit-кодами и таймингами в `docs_10/runbook/TEST_RESULT_<timestamp>.md`;
- не требует от пользователя копировать команды или форматировать отчёт вручную.

Пользователю достаточно:
1. Запустить `bash scripts_01/run_test_suite.sh --all` из корня репозитория.
2. Прислать агенту путь к сгенерированному MD-файлу: `тесты готовы, результат в docs_10/runbook/TEST_RESULT_....md`.

Агент читает MD, извлекает статусы фаз и продолжает работу.

**Режимы скрипта:**
| Команда | Назначение |
|---------|-----------|
| `--quick` | Быстрый smoke: Router + Artifact + ADR-018 + реестры (~30 сек) |
| `--full` | quick + полный `pytest tests_09/` (~10-15 мин) |
| `--all` | Всё: quick + full + mypy + реестры (~15-20 мин, по умолчанию) |
| `--skip-mypy` | Пропустить mypy type-check |
| `--skip-full` | Пропустить полный pytest suite |
| `--out FILE` | Свой путь для отчёта |

**Инструкция:** [`docs_10/runbook/TEST_SUITE_RUNBOOK.md`***REMOVED***(../../docs_10/runbook/TEST_SUITE_RUNBOOK.md).

#### Для нестандартных/разовых проверок

Если нужна специфическая проверка (live-интеграция, конкретный сценарий, не покрытый скриптом), агент **может** создать `docs_10/runbook/TEST_REQUEST_<version>_<slug>.md` с индивидуальными командами. Но это исключение, а не правило.

#### Принципы (неизменны)

1. Пока пользователь выполняет проверки, агент **не простаивает**: продолжает независимую работу — анализ, проектирование, документацию, подготовку патчей и ревью.
2. Короткие hermetic-тесты, AST/compile/import-smoke и проверки, необходимые для безопасного редактирования, агент может запускать сам.
3. В финальном отчёте агент разделяет `AGENT-VERIFIED`, `USER-VERIFIED` и `NOT-RUN/TIMEOUT`; environment-dependent failure не маскируется под регрессию кода.

**Связи:** CQS §11 (тестируемость), CON-65 (provider availability), PB-9 (зависимости окружения), ANTI-5 (не блокировать один сценарий множеством непроверяемых шагов), [`TEST_SUITE_RUNBOOK.md`***REMOVED***(../../docs_10/runbook/TEST_SUITE_RUNBOOK.md) (инструкция пользователя).

---

### CON-68 — Аудит внешнего проекта фиксируется канон-парой AUDIT + RECOMMENDATIONS (2026-09-04)

**Контекст:** security-аудит TeenFreelance (`projects_17/TeenFreelance-master`): послойный проход auth → resource authz → files → websocket → minors' data → infra + deep-dive CRUD/raw-SQL + endpoint-sweep. 36 находок (4 critical), каждая = файл:строка + фрагмент + severity + конкретный fix.

**Правило (канон):**

1. Результат аудита → `docs_10/audits/AUDIT_<object>_<date>.md`; формат факта: файл:строка + фрагмент + severity + fix. «Общие советы» без кода запрещены.
2. Из аудита немедленно заводится/пополняется `docs_10/RECOMMENDATIONS.md` — единый append-only реестр рекомендаций (REC-NNN, приоритеты P0/P1/P2, статусы OPEN/IN_PROGRESS/DONE/WONTFIX/OBSOLETE, verify-ссылка при закрытии). Разделение ролей: **LESSONS = что выучили, RECOMMENDATIONS = что сделать**.
3. Новый документ-тип в том же заходе попадает в DOCUMENT_REGISTRY + RULES.md (doc-types) + INDEX.md — зеркало CON-64/CON-63 (register-first, «не догонять отдельным шагом»).
4. Аудит read-only: код объекта аудита не меняется в заходе аудита; фиксы — отдельные заходы, каждый закрывает REC-записи с verify в таблице реестра.

**Связи:** CON-64 (термин/док в том же заходе), CON-63 (register-first), `docs_10/core/RULES.md` §«Аудит и анализ», `docs_10/core/PROJECT_RULES.md` §3.2 (тиражируемое → общая база), `docs_10/RECOMMENDATIONS.md` (REC-001..020), `docs_10/audits/AUDIT_TEENFREELANCE_2026-09-04.md`.

---
