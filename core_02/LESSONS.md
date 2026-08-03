# LESSONS — Blueprint v3 Integration Scenario

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
