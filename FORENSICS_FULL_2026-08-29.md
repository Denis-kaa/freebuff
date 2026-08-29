# PLATFORM FORENSICS FULL REPORT — Freebuff / Workspace OS
# Дата прохода: 2026-08-29
# Метод: промт 104 (PLATFORM_ARCHITECTURAL_FORENSICS) + 103 (engineering reporter) + серверная проверка /opt/freebuff

---

## A. EXECUTIVE SUMMARY

Платформа Freebuff / Workspace OS существует в двух инстансах:

1. **Локальный (телефон, /mnt/sdcard/PROJECTS/workstation/freebuff)** — основной рабочий каталог, версия v5.189.67 (TASK.md), 109+ файлов промтов, 6527 событий в events.db, 121 сессия и 455 сообщений в context.db.
2. **Серверный (/opt/freebuff на whimco, 185.233.184.192)** — копия того же репозитория, но с самостоятельной жизнью: 111 промтов, 690 событий, context.db пуст (0 сессий/сообщений), отдельные профильные проекты (profile-site) и тестовые данные (whims, learning_events).

**Главные выводы прохода:**

- Архитектурная модель (Whim → Project → Intelligence → Scenario → Factory → Forge → Agent → Artifact) в коде **существует частично**: Forge/Factory/Scenario реализованы и тестируемы (blueprint_v3, forge_registry), Intelligence-слой представлен разрозненными модулями (opportunity_engine, whim_capture, hypothesis_ledger), единого "мозга" нет.
- **История взаимодействия живёт не в одном месте, а в шести:** events.db (события платформы), context.db (сессии/сообщения), streams/ (сырые сессии), summaries/ (конспекты), sessions_15 (логи Telegram-спавна), CHANGELOG.md (версии релизов). Единого провенанса от мысли до результата нет.
- **Синхронизация между телефоном и сервером неполная и асимметричная:** сервер не получает наши новые файлы (116.md, 117.md, отклики, исследование), потому что они не закоммичены в git; при этом на сервере есть файлы, которых нет на телефоне (profile-site, 111/112/115.md). Синхронизация git-основанная, runtime-данные исключены (runtime_data: false).
- **Проекты интегрируются через проектный контейнер** (projects_17/<имя>/) с манифестом, но внешние проекты (ai-dubber, sheet_project) привязаны только косвенно: события lisa_estimator для sheet_project есть, ai-dubber в платформенных данных отсутствует полностью.
- **Наши текущие артефакты (116.md, 117.md, otklik_kwork_ai_assistent.md, neiroslop_research.md, ai_dubber_transcript) не зарегистрированы в MissingRegistry/forge_registry** и не синхронизированы на сервер. Форенсик-промты (103-107) зарегистрированы в реестрах, но их результат (этот отчёт) пока тоже локальный.

---

## B. REPOSITORY REALITY MAP (локально)

| Слой | Директория | Что реально есть | Состояние |
|------|-----------|------------------|-----------|
| Ядро | core_02/ | router.py, blueprint_v3.py, remote_sync.py, scenario_registry, forge_facade, roles | Production (3342+ тестов) |
| Скрипты | scripts_01/ | context_manager, memory_engine, stream_session, knowledge_engine, event_bus, orchestrator | Production / каркас |
| Промты | pompts_11/ | 109+ промтов (001-117), включая форенсик 103-107 | Актив |
| Сценарии | runtime_05/scenarios/ | blueprint_v3.yaml, vkusvill_demo.yaml, 19_remote_sync/ | 2 канон + 1 тест |
| Фабрики | runtime_05/factories/ | architecture, content, research, test | Каркас |
| Документация | docs_10/ | core, engineering-memory, audits, canonical, vision | Обширная |
| Данные | data_13/ | context.db, whims.db, metrics.db, hypothesis_ledger, forge_registry.yaml, missing_registry.yaml | Актив |
| Проекты | projects_17/ | interior_planner, sheet_project, kwork, whimco и др. | Контейнеры |
| Тесты | tests_09/ | 3342+ тестов | Production |
| Состояние | context_12/ | events.db (6527 событий), streams/, summaries/, checkpoints/ | Актив |

---

## C. CURRENT SYSTEM ARCHITECTURE

Платформа реализована как модель-агностическая рабочая среда: ядро (core_02) + инструменты (scripts_01) + промты (pompts_11) + сценарии (runtime_05) + проекты (projects_17) + данные (data_13). Ключевые подтверждённые кодом цепочки:

- Сценарий (scenario) читается через ScenarioRegistry, роли извлекаются через BlueprintCorpus (blueprint_v3.py).
- Forge-пайплайн исполняется через ForgeFacade (упоминается в core_02, CHANGELOG).
- Роутинг моделей через SmartRouter (core_02/router.py) по capabilities (KNOWN_CAPABILITIES в blueprint_v3.py).
- События пишутся в events.db (event_log: 6527 строк локально, 690 на сервере).

---

## D. USER → WORKSPACE → PROJECT FLOW

FACT: context.db содержит 121 сессию, 455 сообщений, 104 чекпоинта, 71 проект, 3 workspaces, 4 workspace_projects.

ANALYSIS: Пользователь взаимодействует через Telegram-терминал (сессии tg_terminal_messenger) и через рабочий каталог. Сессии в context.db заканчиваются 5 августа (smoke/verify-тесты), реальные рабочие диалоги (наши сессии 26-29 августа) в БД не попадают.

DECISION: context.db фиксирует в основном тестовый/Telegram-скоуп, а не текущую живую работу.

---

## E. INTELLIGENCE / BRAIN ANALYSIS

FACT: Есть отдельные модули интеллекта: opportunity_engine, whim_capture (whims.db + whims.yaml), hypothesis_ledger (jsonl), learning_events (86 локально, 24 на сервере), weighted_scoring_engine, devil_advocate_pass, capability_gap_auditor.

FACT: Единого понятия "Intelligence" / "Brain" как одного компонента в коде НЕТ (по карте system_model_forensics_33/02_REPOSITORY_MAP.md: blueprint_v3 = BlueprintCorpus, но отдельного Intelligence-модуля не указано).

ANALYSIS: Intelligence-слой — это совокупность разрозненных утилит, а не единая подсистема. Гипотеза "Intelligence как мозг" пока концептуальная.

---

## F. AGENT ARCHITECTURE

FACT: Агенты представлены через роли блюпринтов (orchestrator, explainer, lisa, risk, decomposer, architect, auditor, response_writer, developer, frontend, devops, tester, fixer, acceptance, documenter, retrospective) с CAPABILITIES_OVERRIDE → SmartRouter.

FACT: На сервере /opt/freebuff/agent/skills/ и .agents/skills/ — 43+ навыков (grilling, triage, implement, code-review, research и др.).

ANALYSIS: Агентный слой двоякий: ролевой конвейер (блюпринты) + навыки (skills). Оба существуют, но между ними нет явного моста в коде (роли → скиллы не маршрутизируются автоматически).

---

## G. WORKSPACE / PROJECT MODEL

FACT: context.db: workspaces (3), workspace_projects (4), projects (71). Проекты имеют name/path/category/status/last_scanned.

FACT: projects_17/ — контейнеры проектов (interior_planner_app, sheet_project, kwork, whimco и др.) по конвенции PROJECT_RULES.md: проект = контейнер контекста (MANIFEST, LESSONS, decisions, ROADMAP, STEPS, RUNNABLE).

ANALYSIS: Модель проекта реализована как файловый контейнер + запись в БД. Граница проекта (B1 Workspace↔Project) — файловая директория, не runtime-изоляция.

---

## H. SCENARIO ARCHITECTURE

FACT: runtime_05/scenarios/: blueprint_v3.yaml (Kwork Arbitr v3, root /storage/emulated/0/PROJECTS/workstation/blueprints_v3), vkusvill_demo.yaml, 19_remote_sync/.

FACT: BlueprintCorpus читает registry.yaml из канонического корпуса (вне репозитория, /storage/emulated/0/PROJECTS/workstation/blueprints_v3) с 17+ ролями.

ANALYSIS: Scenario-слой — рабочий, с реестром и валидацией (validate_all через ScenarioRegistry). Это самый зрелый слой из всей гипотетической модели.

---

## I. FACTORY ANALYSIS

FACT: runtime_05/factories/: architecture, content, research, test — четыре фабрики (каркас).

FACT: В forge_registry.yaml есть записи о прогонах (started_at, duration_s) до 23 августа.

ANALYSIS: Factory-абстракция существует как каталог фабрик, но без единого FactoryRegistry-интерфейса (в коде не найден отдельный класс Factory). Частично реализовано, концептуально описано.

---

## J. FORGE ANALYSIS

FACT: core_02 содержит forge-компоненты (ForgeFacade, forge_pipeline, forge_registry в data_13). По карте system_model: Forge — исполнительный мост (см. CLAIM/evidence в предыдущих форенсик-проходах FORENSICS_104_105_106_107).

FACT: Версии релизов (PHASE4-PHASE13) подтверждают: Forge/Factory вертикальные срезы реализованы и упакованы в архивы.

ANALYSIS: Forge — реально существующий исполнительный слой. Он исполняет цепочки ролей (пример: workflow.completed в events.db, step.started/completed).

---

## K. AGENT / SKILL / TOOL ARCHITECTURE

FACT: Роли (блюпринты) → capabilities → SmartRouter. Skills на сервере (43 шт). Tools: CLI-инструменты, MCP (mcp_server.py, mcp.json), плагины (plugins_04: wrapper.py, acp_protocol.py, bridge_layer.py, mcp_client.py).

FACT: CAPABILITIES_OVERRIDE валидируется против KNOWN_CAPABILITIES (ValueError при drift) — защита ANTI-6b/CON-8.

ANALYSIS: Цепочка Factory → Forge → Agent → Skill → Tool существует, но переходы в основном через конвенции и реестры, не через runtime-граф.

---

## L. ARTIFACT ARCHITECTURE

FACT: Артефакты = файлы: отчёты, коды, архивы (PHASE*.tar.gz, FORENSICS_*.tar.gz), документы. Есть промт 108 (artifact_contract).

ANALYSIS: Понятие Artifact реализовано как файл + (частично) метаданные, но единой системы артефактов с lineage/provenance (Artifact ID → Project → Agent) нет.

---

## M. MEMORY / KNOWLEDGE / CONTEXT

FACT: context_12/: checkpoints (104), streams/ (36), summaries/ (12288 байт каталог), unified_context.md, events.db.

FACT: data_13/context.db: sessions/messages/checkpoints/projects/workspaces + knowledge_* таблицы (0 строк) + learning_events (86) + experience_analytics (0).

FACT: Streams локально заканчиваются 1 августа; summaries — 5 августа; events.db — 23 августа.

ANALYSIS: Память реально существует (5 уровней: working/project/knowledge/personal/archive описаны в BUFFY_PROJECT.md), но knowledge-таблицы пусты, а текущая живая история (26-29 авг) в БД не пишется. Streams/checkpoints не обновляются после 1-5 августа. **Разрыв провенанса: наши текущие сессии не оставляют следов в платформенной памяти.**

---

## N. EVENT / ORCHESTRATION / RUNTIME

FACT: events.db (локально 6527 событий): memory.stored, mcp.server.initialized, workflow.*, step.*, lisa_estimator.completed. Max timestamp локально 2026-08-23T07:24.

FACT: На сервере events.db: 690 событий, max 2026-08-27T05:44 (lisa_estimator, workflow).

ANALYSIS: Event bus работает, но локальный инстанс не получает событий после 23 авг, а серверный — после 27 авг. Живая работа (28-29 авг) не логируется.

---

## O. PLUGIN / MCP / EXTERNAL INTEGRATION

FACT: .freebuff/mcp.json, plugins_04/ (wrapper, acp_protocol, bridge_layer, mcp_client), runtime_05/plugins/. Сервер: plugins_04 свежие (26-27 авг).

FACT: remote_sync (ADR-010, Telegram Relay) реализован: RemoteSyncCoordinatorImpl, e2e_remote_sync.py, 26+14 тестов.

ANALYSIS: Плагины/MCP существуют; remote_sync — самая продвинутая внешняя интеграция.

---

## P. FEEDBACK / LEARNING LOOP

FACT: learning_events (86 локально, 24 на сервере): trigger_id (lisa_estimator), outcome success, lesson_id None.

FACT: lesson_id = None во всех видимых записях.

ANALYSIS: Петля обратной связи есть механически (событие → learning_event), но уроки не извлекаются (lesson_id пуст). Плато: система записывает, но не учится на событиях.

---

## Q. CURRENT EXECUTION PATHS

1. Пользователь → Telegram/CLI → сессия (context.db) → (исторически)
2. Проект → LISA-оценка → events.db (lisa_estimator.completed) → learning_events
3. Сценарий → ScenarioRegistry → роли → SmartRouter → Forge-цепочка → workflow/step события
4. Whim → whims.db/whims.yaml → (статусы NEW→PROMOTED, но локально whims пуст, на сервере 2 тестовые)

---

## R. ARCHITECTURE HYPOTHESIS VALIDATION

Модель: Whim → Workspace OS → Workspace → Project → Intelligence → Scenario → Factory → Forge → Agent/Skill/Tool → Artifact → Project State → Intelligence.

| Элемент | Статус |
|---------|--------|
| Whim | Реализовано частично (whims.db пуст локально, 2 записи на сервере) |
| Workspace OS | Реализовано (платформа существует) |
| Workspace | Реализовано (3 записи в БД) |
| Project | Реализовано (71 запись + projects_17) |
| Intelligence | **Концептуально, нет единого модуля** |
| Scenario | Реализовано и зрело (blueprint_v3, registry) |
| Factory | Частично (каталог фабрик, нет FactoryRegistry) |
| Forge | Реализовано (исполнение цепочек, событий) |
| Agent/Skill/Tool | Реализовано (роли + 43 скилла + MCP/плагины) |
| Artifact | Файлы + частичные метаданные, нет lineage |
| Project State | Через manifest/TASK/CHANGELOG, не через runtime |
| Intelligence (обратно) | Нет петли обучения (lesson_id пуст) |

**Соответствие модели реальности: ~60-65%.** Ядро (Scenario/Forge/Agent) существует; края модели (Whim, Intelligence, Artifact lineage, Feedback loop) — частично или концептуально.

---

## S. MISSING / PARTIAL / CONCEPTUAL COMPONENTS

| Компонент | Статус | Доказательство |
|-----------|--------|----------------|
| Единый Intelligence/Brain | MISSING | Нет модуля, есть разрозненные утилиты |
| FactoryRegistry | PARTIAL | Каталог фабрик есть, интерфейса нет |
| Artifact lineage/provenance | MISSING | Нет ID/родословной артефактов |
| Feedback loop (уроки) | PARTIAL | learning_events есть, lesson_id пуст |
| Knowledge-база | MISSING (пустые таблицы) | knowledge_objects: 0 |
| Плагин для наших новых промтов | MISSING | 116/117 не в forge_registry |
| Remote Sync реальный | PARTIAL | Реализован, ожидает реальный TG-прогон |

---

## T. ARCHITECTURAL BLIND SPOTS

1. **История текущих сессий не пишется в платформенную память.** Streams (до 1 авг), summaries (до 5 авг), events (до 23 авг), context.db (до 5 авг). Мы работаем вне платформенной памяти.
2. **Синхронизация асимметрична и неполна.** Сервер не получает наши новые файлы (нет 116/117), телефон не имеет серверных (нет profile-site). git auto_push настроен, но коммиты не делаются вручную.
3. **MissingRegistry не видит новые промты** (116/117) — они не пройдены через register-first lifecycle.
4. **Дублирование источников правды:** история в 6 местах без единого провенанса.

---

## U. CONTRADICTIONS

1. sync.yaml говорит `remote.ssh_alias: wimp`, а реальный алиас в SSH-конфиге `whimco`. Поле не обновлено после фактического подключения.
2. TASK.md заявляет версию v5.189.67, но git-история содержит v5.189.84 (FBM integration) — версии разошлись между манифестом и git-логами.
3. events.db max timestamp (23 авг) ≠ конец работы (29 авг). Платформа логирует не всё, что происходит в рабочем каталоге.
4. Серверная копия называет себя тем же проектом, но данные (context.db пуст) указывают на тестовый инстанс, не на продолжение локальной истории.

---

## V. PROVENANCE / TRACEABILITY GAPS

- От мысли (whim) до результата (artifact): whims локально пусты, артефакты без lineage. Цепочка рвётся на обоих концах.
- Наши рабочие файлы (116/117/отклики/исследование) не имеют записи в реестрах платформы.
- Нет связи между сессией разговора (мы с тобой) и артефактами, которые мы создаём. Форенсик этого прохода тоже существует вне реестра платформы.

---

## W. RECOMMENDED CANONICAL ARCHITECTURE (после форенсика)

Для целевой интеграции (по твоему вопросу "как проекты интегрировать"):

1. **Проект = контейнер + манифест + запись в БД.** Все внешние проекты (ai-dubber, sheet_project, whimco) заводятся в projects_17/<имя>/ с MANIFEST.md и регистрируются в data_13 (через существующий механизм скана context.db). Это уже работает для sheet_project, но не для ai-dubber.
2. **История = единый event + session trace.** Текущие сессии должны писаться в events.db (или отдельный БД) с session_id, чтобы форенсик мог восстановить "что → почему → решение". Сейчас этого нет.
3. **New prompts через register-first.** 116.md и 117.md должны пройти mark_prompt_written в MissingRegistry, иначе они остаются вне платформы.
4. **Sync: коммит перед push.** Правило: любой новый артефакт (промт, отклик, отчёт) коммитится в git, тогда он дойдёт до сервера. Плюс синхронизация runtime-данных (runtime_data: true) если нужна история на сервере.

---

## X. ROADMAP IMPLICATIONS

1. Создать единый "Журнал сессий" (session journal), куда пишутся наши текущие диалоги и созданные артефакты (см. TARGET GAP-1).
2. Закрыть разрыв версий (TASK.md vs git): синхронизировать версию и закоммитить всё текущее.
3. Зарегистрировать 116/117 в MissingRegistry.
4. Настроить серверную синхронизацию так, чтобы новые файлы уходили (auto-commit перед push), и решить судьбу server-only файлов (profile-site, 111/112/115).

---

## Y. EVIDENCE LEDGER

| Claim | Evidence |
|-------|----------|
| events.db локально 6527 событий | context_12/events.db, COUNT(event_log) |
| max событие локально 23 авг | SELECT MAX(timestamp) event_log |
| сервер events 690, max 27 авг | /opt/freebuff/context_12/events.db |
| context.db: 121 сессия, 455 сообщений | SELECT COUNT(*) sessions/messages |
| сессии в основном тестовые TG | topic-поля (smoke/verify/напиши мне привет) |
| knowledge-таблицы пусты | SELECT COUNT(*) knowledge_objects = 0 |
| learning_events 86 локально | SELECT COUNT(*) learning_events |
| lesson_id пуст | SELECT lesson_id → None во всех |
| streams до 1 авг | ls -t context_12/streams/ |
| summaries до 5 авг | ls -t context_12/summaries/ |
| whims локально пусты | SELECT COUNT(*) whims → 0 |
| whims сервер 2 (тестовые) | SELECT * FROM whims (h_smoke, h_e2e_1) |
| 116/117 нет на сервере | ls /opt/freebuff/pompts_11/116.md → No such file |
| 111/112/115 нет локально | ls pompts_11/*.md |
| 116/117 не в forge_registry | grep 116/117 data_13/forge_registry.yaml → только совпадения duration_s |
| sync.yaml алиас wimp | .freebuff/sync.yaml remote.ssh_alias: wimp |
| SSH алиас whimco | /data/data/com.termux/files/home/.ssh/config |
| remote GitHub | git remote -v → github.com/Denis-kaa/freebuff.git |
| последний git-коммит v5.189.84 | git log --oneline (FBM integration) |
| TASK.md версия v5.189.67 | TASK.md header |
| форенсик-промты зарегистрированы | missing_registry.yaml (084, 103-107 упоминания) |

---

## Z. FINAL VERDICT

Платформа Freebuff / Workspace OS — реальная, рабочая система с сильным ядром (Scenario/Forge/Agent/роутер, 3342+ тестов) и зрелой моделью проектов-контейнеров. Модель "Intelligence → Factory → Forge" соответствует реальности примерно на 60-65%: середина модели реализована, края (Whim, Intelligence-мозг, Artifact lineage, Feedback loop) — частично или концептуально.

**Три практических разрыва, которые стоит закрыть в первую очередь:**

1. **История не пишется.** Наши текущие сессии и артефакты не попадают в память платформы (streams/events/context остановлены 1-23 августа). Без этого форенсик невозможен по определению.
2. **Синхронизация неполна.** Новые файлы не коммитятся → не доходят до сервера. Плюс расхождение версий (TASK v5.189.67 vs git v5.189.84).
3. **Новые промты вне реестров.** 116.md и 117.md (включая этот отчёт) не прошли register-first, не отражены в forge_registry/missing_registry.

Эти три пункта и есть "точки интеграции", о которых ты спрашивал: интеграция проектов идёт через projects_17 + scan, интеграция промтов через MissingRegistry, интеграция истории через event/session trace, интеграция между устройствами через git-коммиты.
