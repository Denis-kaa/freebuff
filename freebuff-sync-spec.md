# Freebuff Sync — Спецификация двустороннего зеркала

> **Файл:** `freebuff-sync-spec.md`
> **Статус:** Draft, подготовлено по итогам интервью
> **Дата:** 2026-08-23
> **Область:** синхронизация полного Freebuff workspace между телефоном (Termux) и сервером по SSH-алиасу `wimp`
> **Реализация:** не выполнена; этот документ фиксирует требования к будущей реализации

## 1. Цель

Создать переносимый Termux-совместимый CLI `freebuff-sync`, который поддерживает двустороннее Git-зеркало рабочего пространства Freebuff:

- телефон остаётся полноценной рабочей копией Freebuff;
- сервер `wimp` получает рабочую копию того же Freebuff workspace;
- изменения, сделанные на телефоне, доходят до сервера;
- изменения, сделанные на сервере, возвращаются на телефон;
- Git используется как единственный механизм передачи, истории и слияния;
- сервер не засоряется файлами, не относящимися к платформе, секретами, кэшами и техническими артефактами;
- операции синхронизации журналируются и могут быть диагностированы через `status`.

Синхронизируется **не отдельная папка пользовательских проектов** и не только `projects_17/`. Объект синхронизации — корень репозитория Freebuff целиком, с фильтрацией состава зеркала.

## 2. Контекст текущего workspace

Исходный workspace находится в корне текущего репозитория Freebuff. По существующей структуре в него входят, в частности:

- `core_02/` — контракты и ядро;
- `scripts_01/` — CLI, серверы, утилиты и runtime-скрипты;
- `freebuff_plugin_03/`, `plugins_04/`, `runtime_05/`, `src_06/`, `cli_07/`, `services_08/`;
- `tests_09/`;
- `docs_10/`;
- `pompts_11/`, `context_12/`, `data_13/`, `logs_14/`, `sessions_15/`;
- `projects_17/` и входящие в него проекты;
- `frontend_18/`, `buffy-playground_19/`, `infa_20/`, `prototype_22/`;
- корневые документы `AGENTS.md`, `BUFFY.md`, `README.md`, `SPEC.md`, `TASK.md`, `CHANGELOG.md`, `requirements.txt` и прочие файлы репозитория.

Фактический список каталогов и файлов должен определяться скриптом через Git и файловую систему при запуске. Спецификация не разрешает переносить весь Android/Termux home-каталог: область ограничена корнем Freebuff.

## 3. Цели и нецели

### 3.1. Входит в задачу

- обнаружение и проверка SSH-доступа `ssh wimp`;
- поиск/валидация серверного корня Freebuff;
- конфигурация путей через YAML;
- создание или безопасное подключение bare Git-репозитория на сервере;
- создание серверной рабочей копии;
- настройка server-side hooks;
- режимы `push`, `pull`, `sync`, `watch`, `status`;
- двусторонний Git merge;
- обработка конфликтов, удалений и грязных рабочих деревьев;
- lock-файлы на телефоне и сервере;
- журналирование операций и diff-отчётов;
- дополнительный `.gitignore` для мусора и секретов;
- безопасный bootstrap уже существующей серверной папки;
- Termux-совместимый запуск без Docker и без обязательных сторонних Python-библиотек, кроме уже принятых проектом зависимостей.

### 3.2. Не входит в задачу

- перенос всего домашнего каталога телефона;
- синхронизация нерелевантных проектов, документов и архивов вне Freebuff;
- публикация Freebuff в интернет;
- автоматический деплой или перезапуск production-сервисов после каждого push;
- резервное копирование всего телефона;
- синхронизация секретов между устройствами;
- замена Git другим транспортом, включая rsync как основной механизм;
- автоматическое разрешение текстовых конфликтов с потерей одной из сторон.

## 4. Принятые решения

| Область | Решение |
|---|---|
| Источник | Текущая рабочая копия Freebuff на телефоне |
| Сервер | SSH alias `wimp` |
| Объект | Весь Freebuff workspace, а не только `projects_17/` |
| Транспорт | Git через SSH |
| Серверная схема | Bare repo + отдельная рабочая копия |
| Ветка | Текущая ветка телефона, без принудительного переименования в `main` |
| Bootstrap | Безопасный bootstrap существующей серверной папки с резервированием |
| Конфигурация | YAML в workspace |
| Конфликты | Обычный Git merge; неразрешённый конфликт останавливает операцию |
| Удаления | Git-удаления зеркалируются после подтверждённого/успешного merge |
| Watch | `inotifywait` при наличии, polling как fallback |
| Watch action | Автоматический commit + push после настраиваемых проверок |
| Проверки watch | Конфигурируемые; по умолчанию лёгкий режим |
| Lock | Lock-файл на телефоне и сервере |
| Логи | Локальный audit log вне Git + итоговые отчёты внутри отдельного tracked-каталога |
| Статус | Локальный и серверный status через SSH |
| Успех | Обе стороны имеют clean working tree и одинаковый HEAD |
| Секреты | Не копируются; подозрительные файлы показываются и требуют явного решения |
| SQLite | Согласованный backup через SQLite backup API перед синхронизацией |

## 5. Состав зеркала

### 5.1. Базовое правило

В зеркало попадают исходники, документация, конфигурация и рабочие данные, которые относятся к платформе Freebuff и нужны для продолжения работы на сервере.

Скрипт не должен blindly копировать всё содержимое корня. Состав строится в три слоя:

1. обычный `.gitignore`;
2. обязательный denylist безопасности и технического мусора;
3. отчёт классификации для неизвестных или подозрительных файлов.

### 5.2. Точный allowlist: входит по умолчанию

Allowlist основан на фактическом дереве workspace и текущем Git-индексе. По умолчанию в зеркало входят следующие корневые файлы и каталоги:

```text
.cursorrules
.freebuff/**
.github/**
.gitignore
AGENTS.md
BUFFY.md
BUFFY_PROJECT.md
CHANGELOG.md
CLAUDE.md
CODY.md
README.md
SPEC.md
TASK.md
__init__.py
freebuff_cli.py
generate_project_dump.sh
mypy.ini
pytest.ini
requirements.txt
run_checks.py
run_tests.sh
run_tests_fast.sh
setup_canonical.sh
smart_test_runner.sh
smart_test_runner_fixed.sh
status_report.sh
verify_archive.sh
freebuff-sync-spec.md

buffy-playground_19/**
cli_07/**
core_02/**
docs_10/**
freebuff_plugin/**
freebuff_plugin_03/**
frontend_18/**
infa_20/**
plugins_04/**
pompts_11/**
prototype_22/**
runtime_05/**
scripts_01/**
services_08/**
src_06/**
tests_09/**
projects_17/**
```

Для этих путей применяются дополнительные deny-паттерны ниже. Allowlist означает «кандидат на зеркало», а не разрешение секретов или бинарных runtime-файлов.

Корневые файлы, не перечисленные выше, не переносятся автоматически. В частности, текущие `tank.html`, `steps.md`, `nohup.out`, `qwen-table-1785806850126.csv`, `status_report_20260801_205122.txt`, `.sha256` и `verify_archive_marker.txt` получают статус `unknown`/`suspicious`. `freebuff-sync-spec.md` уже входит в allowlist как каноническая спецификация этой функции; после реализации `.freebuff/sync.yaml`, `scripts_01/freebuff_sync*.py` и соответствующие тесты также должны быть добавлены в allowlist.

### 5.3. Точный denylist: никогда не переносить автоматически

Следующие пути и типы файлов запрещены независимо от `.gitignore`, Git tracking и режима запуска:

```text
.git/**
.keys/**
.freezer/**
__pycache__/**
.mypy_cache/**
.pytest_cache/**
.test_logs/**
.test_temp/**
.freebuff_original_agents
.freebuff_result
core/**
screenshots_16/**
status_report_20260801_205122.txt
verify_archive_marker.txt

.env
.env.*
**/.env
**/.env.*
**/*.session
**/*.session-journal
**/*token*
**/*secret*
**/*credential*
**/*private_key*
**/*.pem
**/*.key
**/*.crt
**/*.log
**/*.pid
**/*.lock
**/*.tmp
**/*.bak
**/*.bak-*
**/*.orig
**/*~
**/*.pyc
**/*.pyo
**/*.db-wal
**/*.db-shm
**/node_modules/**
**/dist/**
**/build/**
**/.vite/**
```

Также по фактическому дереву целиком исключаются следующие каталоги и архивные наборы:

```text
books_out_23/**
trash_21/**
screenshots_16/**
architecture_forensics_v2/**
intelligence_forensics_25/**
phase4_evaluation_24/**
phase5_intelligence_loop_26/**
phase6_code_contract_forensics_27/**
phase7_evaluation_28/**
phase8_evaluation_29/**
phase9_evaluation_30/**
phase9_implementation_continuation_31/**
platform_architectural_inventory_34/**
repository_organization_forensics_32/**
system_model_forensics_33/**
FORENSICS_104_105_106_107/**
```

В корне и внутри проектов запрещаются архивы и checksum-артефакты:

```text
**/*.tar
**/*.tar.gz
**/*.tgz
**/*.zip
**/*.7z
**/*.rar
**/*.sha256
**/*.md5
```

Это исключает, среди прочего, фактически обнаруженные `freebuff.zip`, `freebuff.tar.gz`, `projects_17/vkusvill_demo.tar.gz`, `projects_17/kwork/доработка сайта.tar.gz`, forensic-архивы и резервные копии. Архив не переносится даже если рядом находится относящийся к платформе документ; исходные документы переносятся отдельно.

Путь `data_13/.pulse_snapshot.json` также запрещён как generated snapshot. Файлы `data_13/.drift_last_run` и `docs_10/DRIFT_REPORT.md` запрещены как результаты конкретного локального запуска.

### 5.4. Opt-in allowlist: рабочее состояние

Текущие `.gitignore` правила исключают runtime-данные целыми каталогами, поэтому они не должны внезапно попасть на сервер только потому, что пользователь выбрал «весь workspace». Для них нужен явный `runtime_data: true` в YAML и отдельная проверка.

#### Декларативные данные, разрешаемые после явного включения

```text
data_13/forge_registry.yaml
data_13/missing_registry.yaml
data_13/opportunities.yaml
data_13/whims.yaml
data_13/scenario_decisions.yaml
data_13/lisa_calibration.yaml
data_13/hypothesis_ledger/**
context_12/unified_context.md
context_12/session_todos.md
context_12/checkpoints/**
context_12/summaries/**
context_12/memory/**
context_12/knowledge/**
context_12/exports/**
sessions_15/README.md
sessions_15/.gitkeep
```

Файлы в этом списке всё равно проходят secret scan и denylist. Содержимое `context_12/` может включать персональные данные или токены в тексте; при срабатывании secret scan файл переводится в `suspicious` и не отправляется.

#### SQLite allowlist

В текущем `data_13/` обнаружены следующие базы, которые можно синхронизировать только через SQLite backup API:

```text
data_13/context.db
data_13/metrics.db
data_13/presence.db
data_13/project_pulse.db
data_13/roles.db
data_13/collaboration.db
data_13/verifier.db
context_12/events.db
projects_17/diet_platform/diet_platform.db
projects_17/tg_terminal_messenger/tg_cache.db
```

Для SQLite разрешены только согласованные backup-копии. Исходные `*.db-wal` и `*.db-shm` никогда не синхронизируются. `projects_17/tg_terminal_messenger/tg_cache.db` содержит Telegram-кэш и по умолчанию должен оставаться выключенным; его включение требует отдельного YAML allowlist. `diet_platform.db` также включается только если на сервере действительно нужен рабочий state этого проекта.

Алгоритм SQLite backup:

1. получить список баз из `sqlite.allowlist`;
2. создать временную backup-копию вне Git;
3. выполнить `sqlite3.Connection.backup()` в согласованную рабочую копию;
4. проверить открытие backup в read-only режиме и integrity check;
5. атомарно заменить целевой snapshot;
6. удалить временный файл после успешного commit;
7. записать в отчёт путь, размер, integrity result и timestamp;
8. при активном/заблокированном состоянии остановить операцию, не копируя исходный файл напрямую.

### 5.5. Проекты внутри `projects_17`

`projects_17/**` входит в основной allowlist, потому что это часть Freebuff workspace. Фильтры внутри него точнее:

- исходники, `README.md`, `MANIFEST.md`, `SPEC.md`, `ROADMAP.md`, `STEPS.md`, `CHECKLIST.md`, `RUNNABLE.md`, ADR/decisions, `.yaml`, `.yml`, `.json`, `.toml`, `.py`, `.js`, `.ts`, `.tsx`, `.css`, `.html`, `.sh`, `.sql`, `.xlsx` и относящиеся к проекту markdown-файлы входят, если не попали в denylist;
- `.env.example` разрешён, а `.env`, `.env.bak*` и любые реальные credentials запрещены;
- `*.db` входит только через SQLite allowlist;
- изображения и прочие бинарные assets входят только если находятся внутри проекта и имеют размер не больше `25 MiB`; больший файл требует `filters.large_file_allowlist`;
- проектные архивы, backup-файлы и `*.bak` запрещены даже внутри активного проекта;
- отдельная папка/проект не исключается только из-за отсутствия `MANIFEST.md`: например `content_factory`, `python_tutor`, `research`, `vocal` и `kwork` сначала классифицируются по содержимому, а не молча удаляются;
- несвязанные документы внутри проекта получают `suspicious` и требуют явного allowlist, особенно если это экспорт, клиентский материал или архив.

Фактически обнаруженные примеры:

```text
include: projects_17/kwork_site/*.md и код/конфиги проекта
include: projects_17/vkusvill_demo/*.py, *.md, *.json, *.xlsx, project.yaml
exclude: projects_17/vkusvill_demo.tar.gz
exclude: projects_17/kwork/доработка сайта.tar.gz
exclude: projects_17/diet_platform/.env, .env.bak-*, *.db-wal, *.db-shm
exclude: projects_17/tg_terminal_messenger/tg_session.session, *.db-wal, *.db-shm
exclude: projects_17/research/promt1.md.bak
exclude: projects_17/sheet_project/*.bak
```

### 5.6. Классификация и приоритет правил

Приоритет обработки пути строго такой:

```text
hard denylist
  > secret scan / suspicious detection
  > explicit YAML exclude
  > explicit YAML allowlist
  > canonical workspace allowlist
  > unknown
```

Hard denylist нельзя переопределить флагом `--yes`. Секретный файл нельзя разрешить обычным allowlist; для исключений требуется ручное снятие hard-deny правила в коде и отдельное архитектурное решение, что в v1 запрещено.

Перед первым bootstrap создаётся `sync-manifest.json` с полями `path`, `class`, `reason`, `size_bytes`, `git_tracked`, `sha256` для файлов класса `included`/`suspicious` без записи содержимого. Для подозрительных файлов сохраняются только путь и причина, не полный текст.

## 6. Конфигурация YAML

В workspace должен появиться отдельный конфигурационный файл, например `.freebuff/sync.yaml`. Секреты в него не записываются.

Пример контракта:

```yaml
version: 1

local:
  workspace_root: "."
  branch: "auto"

remote:
  ssh_alias: "wimp"
  workspace_root: "/path/to/freebuff"
  bare_repo: "/path/to/.freebuff-sync.git"
  worktree: "/path/to/freebuff"
  branch: "auto"
  lock_path: "/path/to/.freebuff-sync-lock"
  log_dir: "~/.cache/freebuff-sync"

sync:
  mode: "git"
  lock_timeout_sec: 30
  watch_interval_sec: 10
  watch_debounce_sec: 3
  delete_mode: "mirror-after-merge"
  conflict_mode: "stop-and-report"
  non_interactive: false
  require_clean_success: true

watch:
  enabled: true
  backend: "hybrid"
  auto_commit: true
  auto_push: true
  check_command: null
  commit_prefix: "chore(sync):"

filters:
  # Canonical platform code/docs/config. See spec §5.2 for the exact list.
  include:
    - ".freebuff/**"
    - ".github/**"
    - "buffy-playground_19/**"
    - "cli_07/**"
    - "core_02/**"
    - "docs_10/**"
    - "freebuff_plugin/**"
    - "freebuff_plugin_03/**"
    - "frontend_18/**"
    - "infa_20/**"
    - "plugins_04/**"
    - "pompts_11/**"
    - "projects_17/**"
    - "prototype_22/**"
    - "runtime_05/**"
    - "scripts_01/**"
    - "services_08/**"
    - "src_06/**"
    - "tests_09/**"
  root_allowlist:
    - ".cursorrules"
    - ".gitignore"
    - "AGENTS.md"
    - "BUFFY.md"
    - "BUFFY_PROJECT.md"
    - "CHANGELOG.md"
    - "CLAUDE.md"
    - "CODY.md"
    - "README.md"
    - "SPEC.md"
    - "TASK.md"
    - "__init__.py"
    - "freebuff_cli.py"
    - "generate_project_dump.sh"
    - "mypy.ini"
    - "pytest.ini"
    - "requirements.txt"
    - "run_checks.py"
    - "run_tests.sh"
    - "run_tests_fast.sh"
    - "setup_canonical.sh"
    - "smart_test_runner.sh"
    - "smart_test_runner_fixed.sh"
    - "status_report.sh"
    - "verify_archive.sh"
    - "freebuff-sync-spec.md"
  exclude:
    - ".git/**"
    - ".keys/**"
    - ".freezer/**"
    - "__pycache__/**"
    - "**/__pycache__/**"
    - ".mypy_cache/**"
    - ".pytest_cache/**"
    - ".test_logs/**"
    - ".test_temp/**"
    - "books_out_23/**"
    - "trash_21/**"
    - "screenshots_16/**"
    - "architecture_forensics_v2/**"
    - "intelligence_forensics_25/**"
    - "phase4_evaluation_24/**"
    - "phase5_intelligence_loop_26/**"
    - "phase6_code_contract_forensics_27/**"
    - "phase7_evaluation_28/**"
    - "phase8_evaluation_29/**"
    - "phase9_evaluation_30/**"
    - "phase9_implementation_continuation_31/**"
    - "platform_architectural_inventory_34/**"
    - "repository_organization_forensics_32/**"
    - "system_model_forensics_33/**"
    - "FORENSICS_104_105_106_107/**"
    - "**/.env"
    - "**/.env.*"
    - "**/*.session"
    - "**/*.session-journal"
    - "**/*.db-wal"
    - "**/*.db-shm"
    - "**/*.tar"
    - "**/*.tar.gz"
    - "**/*.tgz"
    - "**/*.zip"
    - "**/*.7z"
    - "**/*.rar"
    - "**/*.sha256"
    - "**/*.md5"
    - "**/*.log"
    - "**/*.pid"
    - "**/*.lock"
    - "**/*.tmp"
    - "**/*.bak"
    - "**/*.bak-*"
    - "**/*.orig"
    - "**/*~"
    - "**/*.pyc"
    - "**/*.pyo"
    - "**/node_modules/**"
    - "**/dist/**"
    - "**/build/**"
    - "**/.vite/**"
    - "data_13/.drift_last_run"
    - "data_13/.pulse_snapshot.json"
    - "docs_10/DRIFT_REPORT.md"
    - ".freebuff_original_agents"
    - ".freebuff_result"
    - "core/**"
    - "screenshots_16/**"
    - "status_report_20260801_205122.txt"
    - "verify_archive_marker.txt"
  runtime_data: false
  runtime_allowlist:
    - "data_13/forge_registry.yaml"
    - "data_13/missing_registry.yaml"
    - "data_13/opportunities.yaml"
    - "data_13/whims.yaml"
    - "data_13/scenario_decisions.yaml"
    - "data_13/lisa_calibration.yaml"
    - "data_13/hypothesis_ledger/**"
    - "context_12/unified_context.md"
    - "context_12/session_todos.md"
    - "context_12/checkpoints/**"
    - "context_12/summaries/**"
    - "context_12/memory/**"
    - "context_12/knowledge/**"
    - "context_12/exports/**"
  sqlite_allowlist: [***REMOVED***
  large_file_limit_mib: 25
  large_file_allowlist: [***REMOVED***
  unknown_policy: "exclude-and-report"

logging:
  external_log_dir: "~/.cache/freebuff-sync"
  tracked_report_dir: ".freebuff/sync-reports"
  include_diff: true
```

Фактические пути `remote.workspace_root`, `remote.bare_repo` и `remote.worktree` должны быть заданы в YAML после discovery. Нельзя полагаться на случайный автоматически выбранный путь, если найдено несколько кандидатов.

## 7. Серверная Git-топология

### 7.1. Bare repository

На `wimp` создаётся отдельный bare repository, например:

```text
<server-base>/.freebuff-sync.git/
```

Bare repo является центральным Git transport/remote. Он не используется как рабочая директория.

### 7.2. Server worktree

Рядом с bare repo находится серверная рабочая копия Freebuff:

```text
<server-base>/freebuff/
```

Она используется для работы пользователя на сервере и обновляется hook-ом после push.

Рекомендуемая схема:

```text
Телефон:  Freebuff working copy
              |
              | git push/pull over SSH
              v
Сервер:   .freebuff-sync.git   (bare central repo)
              |
              | post-receive hook
              v
          freebuff/            (server working copy)
```

### 7.3. Branch policy

- `branch: auto` означает текущую ветку телефона на момент bootstrap.
- Серверная рабочая копия должна отслеживать ту же ветку.
- Скрипт не должен silently switch branch.
- Если текущая ветка detached HEAD, операция блокируется до явного указания ветки в YAML.
- Если на сервере есть дополнительные ветки, они сохраняются и не удаляются автоматически.

## 8. Безопасный bootstrap

Bootstrap является отдельным mutating-режимом CLI и не запускается автоматически из `status`, `push`, `pull` или `sync`. `status` может выполнять только read-only discovery; `bootstrap` запускается явно оператором после проверки dry-run.

### 8.1. Локальная discovery

Скрипт проверяет:

1. локальный корень Freebuff;
2. `ssh wimp` и доступность shell;
3. ОС, домашний каталог, наличие `git`, `python3`, `inotifywait`;
4. заданные YAML-пути;
5. существование серверной Freebuff-папки;
6. наличие `.git` или bare-repo;
7. ветки, remote URL, HEAD и незакоммиченные изменения;
8. права записи и свободное место;
9. существующие hooks и потенциальные конфликты с другими процессами.

### 8.1.1. Локальный алгоритм

1. При `--config PATH` взять `local.workspace_root` из YAML и разрешить его относительно каталога конфигурации.
2. Иначе выполнить `git -C <cwd> rev-parse --show-toplevel`.
3. Если Git не сработал, проверить текущий каталог и его родителей до filesystem root.
4. Корень считается Freebuff workspace только при наличии минимум двух маркеров из `AGENTS.md`, `BUFFY.md`, `core_02/`, `scripts_01/`, `projects_17/`.
5. Если найдено несколько подходящих корней, вернуть код `4` и список кандидатов. Ближайший путь нельзя выбирать молча.

Локальный discovery report обязан содержать `workspace_root`, `git_root`, `git_present`, `branch`, `head`, `clean`, `markers` и `config_path`. До SSH-вызова проверить наличие `git`, `ssh`, текущего Python interpreter и каталогов local lock/log. `inotifywait` проверяется отдельно как optional dependency для `watch`. Скрипт не читает приватный ключ и не изменяет `~/.ssh/config`.

### 8.2. Bounded SSH discovery на `wimp`

Удалённый discovery выполняется только через `remote.ssh_alias` из YAML:

```text
ssh -o BatchMode=yes -o ConnectTimeout=10 wimp <fixed-probe>
```

Пользовательские пути нельзя конкатенировать в shell-команду. Реализация передаёт фиксированный POSIX probe через `ssh wimp sh -s -- <validated-args>` или использует argv-массив с проверенными absolute paths. `shell=True` и произвольный текст из YAML запрещены.

Первый read-only probe возвращает versioned key/value contract:

```text
protocol=1
host=<hostname>
user=<ssh-user>
home=<absolute-home>
os=<uname>
arch=<uname-m>
git=<absolute-path-or-missing>
python3=<absolute-path-or-missing>
inotifywait=<absolute-path-or-missing>
```

SSH timeout/exit `255` означает infrastructure error; отсутствие `protocol=1` означает incompatible remote; `git=missing` блокирует bootstrap. Parser отклоняет дубликаты ключей и неизвестный формат. Probe не выводит environment, secrets или содержимое файлов.

Если `remote.workspace_root` не задан, поиск ограничен `$HOME`, `$HOME/work`, `$HOME/workspace`, `$HOME/projects`, `$HOME/src`, `$HOME/PROJECTS`, `/srv`, `/opt`; `find` использует `-maxdepth 4 -xdev` и фиксированные markers. Кандидат должен содержать минимум два из `AGENTS.md`, `BUFFY.md`, `core_02/`, `scripts_01/`, `projects_17/` и один из `.git/`, `workspace.yaml`, `BUFFY_PROJECT.md`, `SPEC.md`.

Scoring используется только для сортировки: `AGENTS.md` +20, `BUFFY.md` +20, `core_02/` +20, `scripts_01/` +20, `projects_17/` +15, `.git/` +10, `workspace.yaml`/`BUFFY_PROJECT.md`/`SPEC.md` +5, basename `freebuff` +5. Score `<60` отбрасывается; разница `<10` между кандидатами блокирует выбор и требует пути в YAML; bare repo не считается worktree.

Discovery сохраняет `sync-discovery.json` во внешнем log directory или выводит его через `--json`, но не изменяет YAML автоматически.

После resolution `remote.workspace_root`, `remote.bare_repo`, `remote.worktree` должны быть absolute paths, принадлежать одному SSH user, иметь writable parents, а также не пересекаться:

```text
bare_repo != worktree
bare_repo не находится внутри worktree
worktree не находится внутри bare_repo
```

Рекомендуемая раскладка: `/home/user/freebuff/` как worktree, `/home/user/.freebuff-sync.git/` как bare repo, `/home/user/.freebuff-sync-lock/` как remote lock и `/home/user/.cache/freebuff-sync/` как remote logs.

### 8.3. Existing server folder

Существующая папка не уничтожается и не очищается без резервирования.

При обнаружении существующих файлов скрипт должен:

- создать timestamped backup/branch или архив внутри серверного служебного каталога;
- зафиксировать список файлов и Git status;
- проверить, является ли папка тем же Freebuff репозиторием;
- сравнить origin/refs/HEAD и содержимое;
- определить, можно ли выполнить merge без потери данных;
- остановиться с понятным отчётом при неоднозначной структуре.

Нельзя использовать `rm -rf`, `git reset --hard`, `git clean -fd` или принудительный overwrite как скрытую часть bootstrap.

#### 8.3.1. Матрица состояния серверной папки

Перед изменениями сохранить remote inventory: `path`, `type`, `size_bytes`, `mtime`, `git_tracked`, `sha256` для included/suspicious файлов. Содержимое секретных файлов не записывать.

| Состояние | Действие |
|---|---|
| Путь отсутствует | Создать parent dirs, bare repo и worktree clone |
| Путь пустой | Создать worktree clone из bare repo |
| Валидный Freebuff worktree с ожидаемым remote | Проверить branch/dirty/ahead-behind и reuse после backup metadata |
| Worktree другого remote | Не переподключать автоматически; backup и код `4` |
| Freebuff markers без Git | Capture server seed, затем staging bootstrap |
| Не-Freebuff каталог с файлами | Не использовать как worktree; остановиться или выбрать другой путь |
| Bare repo есть, worktree нет | Проверить refs/HEAD и clone нужной branch |
| Bare repo невалиден | Не перезаписывать; потребовать новый YAML path |

### 8.4. Bootstrap phases

Каждая фаза имеет durable report и повторяется идемпотентно.

#### Phase 0 — plan only

```bash
freebuff-sync bootstrap --config .freebuff/sync.yaml --dry-run
```

Plan показывает local root/branch/HEAD, SSH identity, capabilities, candidates/score, выбранные пути, file classification, backup path, Git refs, hook paths, free space, planned mutations и запрещённые операции. Dry-run не создаёт каталоги, repo, hooks, commits, persistent locks или YAML changes.

#### Phase 1 — reserve and backup

Получить local и remote locks, повторно проверить SSH identity/paths, создать backup вне worktree и bare repo, сохранить inventory и metadata-preserving копию worktree. При нехватке места остановиться; backup не удаляется автоматически.

#### Phase 2 — initialize bare repository

Если `remote.bare_repo` отсутствует, выполнить `git init --bare <validated-bare-repo>` и проверить `rev-parse --is-bare-repository == true`, owner, permissions, HEAD и hooks directory. Существующий bare repo не инициализировать повторно и не менять refs до inventory.

#### Phase 3 — capture server seed

Для существующего worktree без совместимой Git-истории применить §5 filters, создать staging worktree, скопировать included files, сделать commit `chore(sync): capture pre-bootstrap server state` и сохранить seed в `refs/heads/bootstrap/server-seed-<timestamp>`. Seed не является основной веткой.

#### Phase 4 — publish local history

Проверить local status и hard-deny paths. В пустой bare repo выполнить обычный push текущей ветки без force. При существующей истории сделать fetch и обычный merge; unrelated histories разрешать только в явно подтверждённом bootstrap plan после сохранения seed.

#### Phase 5 — create or reuse server worktree

Если worktree отсутствует, создать clone из bare repo во временный путь, проверить branch/clean state и выполнить atomic rename. Старый путь сохраняется в backup. Валидный clean worktree можно reuse; dirty worktree блокирует bootstrap.

#### Phase 6 — install hooks

Установить versioned `pre-receive` и `post-receive` в `<bare-repo>/hooks/`. `post-receive` обновляет worktree только при clean state и fast-forward:

```text
git -C <worktree> fetch <bare> <branch>
git -C <worktree> merge --ff-only FETCH_HEAD
```

При dirty worktree или невозможном fast-forward hook не затирает файлы и пишет failure report. Hooks не запускают приложения, tests, systemd или production deployment.

#### Phase 7 — verify

Проверить bare ref, local HEAD, server worktree HEAD, clean state, отсутствие denylisted paths в new commits, executable/versioned hooks, сохранённый report и освобождённые locks. Bootstrap успешен только если local HEAD == server HEAD.

### 8.5. Non-interactive operation

После заполнения YAML bootstrap может запускаться без вопросов, например через `--non-interactive` или настройку `sync.non_interactive: true`.

В non-interactive режиме операция должна завершаться ошибкой, если:

- серверный путь не определён однозначно;
- найдены подозрительные файлы без allowlist;
- существует грязное серверное дерево;
- обнаружен неизвестный Git remote/branch;
- есть конфликт или риск потери данных;
- не удалось создать резервную копию;
- требуется удалить файлы, но политика удаления не подтверждена конфигом.

## 9. CLI-контракт

Основная команда:

```bash
python -m freebuff_sync <mode> [options***REMOVED***
```

Допускается также исполняемый wrapper `freebuff-sync`.

### 9.1. `bootstrap`

Одноразовая настройка серверной Git-топологии. По умолчанию только показывает план; mutating bootstrap требует `--apply` или `--yes` в non-interactive режиме:

```bash
freebuff-sync bootstrap --config .freebuff/sync.yaml --dry-run
freebuff-sync bootstrap --config .freebuff/sync.yaml --apply
freebuff-sync bootstrap --config .freebuff/sync.yaml --apply --non-interactive --yes
```

`bootstrap` вызывает §8.1–§8.5 в указанном порядке. Повторный запуск идемпотентен: существующий bare repo, clean worktree и hooks с ожидаемой version marker переиспользуются. Dirty/ambiguous state не исправляется автоматически.

### 9.2. `status`

Показывает локально и на сервере:

- workspace root;
- SSH alias;
- server paths;
- branch и HEAD SHA;
- local/server ahead-behind;
- clean/dirty state обеих рабочих копий;
- список untracked/modified/deleted/conflicted файлов;
- последний успешный sync;
- последний неуспешный sync;
- lock state;
- наличие hooks;
- число included/ignored/suspicious/unknown файлов;
- доступный диск;
- серверную версию Git и runtime;
- exit code, отражающий состояние.

`status` не должен менять рабочие деревья.

### 9.3. `push`

Алгоритм:

1. взять локальный lock;
2. получить серверный sync lock или остановиться;
3. подготовить согласованные SQLite backup-файлы;
4. проверить фильтры и подозрительные файлы;
5. показать/записать план изменений;
6. при необходимости выполнить настроенную проверку;
7. создать commit только если политика разрешает commit для данного режима;
8. выполнить `git fetch`/проверку удалённых изменений;
9. при расхождении сначала выполнить merge/rebase согласно контракту `sync`, а не force push;
10. push в bare repo;
11. дождаться результата hook-а;
12. проверить server HEAD и clean state;
13. записать полный diff/log report.

Обычный `push` не должен автоматически затирать серверные коммиты.

### 9.4. `pull`

Алгоритм:

1. взять locks;
2. fetch из bare repo;
3. проверить наличие локальных незакоммиченных изменений;
4. если дерево грязное, сохранить изменения через обычный Git-процесс или остановиться;
5. выполнить fast-forward/merge при совместимой истории;
6. при конфликте остановиться и вывести список конфликтных файлов;
7. после успешного merge обновить локальную рабочую копию;
8. проверить clean state и записать отчёт.

`pull` не должен удалять локальные изменения через force/reset.

### 9.5. `sync`

`sync` — полный двусторонний цикл:

```text
lock -> discover -> classify -> snapshot/SQLite backup -> fetch
     -> local commit if configured -> merge both histories
     -> resolve or stop on conflict -> push
     -> server hook updates worktree
     -> verify local/server HEAD and clean trees
     -> write audit + diff report -> unlock
```

Целевой успешный результат: локальный HEAD и server worktree HEAD соответствуют одному commit, обе рабочие копии clean, bare repo содержит этот commit.

### 9.6. `watch`

Watch работает на телефоне в Termux foreground-процессе.

Backend:

1. использовать `inotifywait`, если утилита доступна;
2. иначе перейти на polling по Git status и mtime;
3. debounce изменений по `watch_debounce_sec`;
4. игнорировать изменения в excluded paths;
5. при обнаружении изменений получить lock;
6. выполнить configurable check command;
7. создать служебный commit;
8. выполнить push;
9. при конфликте остановить автоматический цикл, записать ошибку и не повторять разрушительные действия бесконечно;
10. продолжить после следующего явного `sync` или команды восстановления.

Рекомендуемый commit message:

```text
chore(sync): update workspace from Termux
```

Для server-originated изменений watch не должен напрямую менять телефон без pull/fetch; при необходимости используется отдельный watch/status цикл или ручной `pull/sync`.

### 9.7. Дополнительные параметры CLI

Минимальный набор:

```text
--config PATH
--apply
--non-interactive
--dry-run
--yes
--verbose
--json
--continue
--abort
--list-conflicts
--no-hooks
--no-watch-check
--lock-timeout SEC
--interval SEC
--include PATH
--exclude PATH
```

Опасные операции должны требовать явного `--yes` либо соответствующего флага в YAML даже в non-interactive режиме.

## 10. Конфликты и удаления

### 10.1. Конфликты

При Git conflict скрипт должен:

- сохранить исходный merge state;
- не выполнять `reset --hard`;
- не выполнять force push;
- записать конфликтующие пути, branch, local HEAD, remote HEAD и merge base;
- вывести команды для продолжения (`git status`, редактирование, `git add`, `git commit`);
- вернуть ненулевой exit code;
- не запускать автоматический повтор в watch.

Пример отчёта:

```text
SYNC CONFLICT
local:  <sha>
remote: <sha>
files:
  - docs_10/...
  - projects_17/...
resolve manually, then run: freebuff-sync sync --continue
```

Поддержать `--continue`, `--abort` и `--list-conflicts`, если это не усложняет основной CLI.

### 10.2. Удаления

Удаление является обычным Git-изменением.

- удаление на телефоне переносится на сервер после commit/merge/push;
- удаление на сервере приходит на телефон через pull/merge;
- после успешного merge отсутствующие tracked-файлы удаляются на другой стороне как часть Git checkout;
- untracked-файлы не удаляются автоматически;
- ignored-файлы не удаляются автоматически;
- любые массовые удаления показываются в plan и журнале;
- при превышении настраиваемого порога удалений операция блокируется до `--yes`.

## 11. Hooks

### 11.1. Server-side hooks

Bare repo должен получить tracked или генерируемые при bootstrap hooks:

- `pre-receive` или `update`:
  - проверка branch policy;
  - запрет push в неизвестную ветку при строгом режиме;
  - проверка базовых ограничений размера/секретов;
  - проверка lock state;
  - понятный stderr при reject;
- `post-receive`:
  - обновление серверной рабочей копии из bare repo;
  - проверка clean state перед checkout;
  - использование отдельного server lock;
  - запись результата в server log;
  - отсутствие запуска приложений и production-сервисов.

Если серверная рабочая копия dirty, `post-receive` не должна безусловно затирать её. Hook обязан остановиться и записать причину; рабочее дерево сохраняется для ручного решения.

### 11.2. Local hooks

Допускается установка локального `pre-commit`/`post-commit` hook, но он не должен запускать тяжёлый полный test suite без явной настройки. Локальный hook может:

- проверить denylist;
- проверить наличие секретов;
- проверить максимальный размер файлов;
- добавить запись в внешний audit log.

## 12. Locking

Lock необходим на обеих сторонах:

- локально: `~/.cache/freebuff-sync/lock`;
- сервер: служебный lock рядом с bare repo/worktree.

Lock должен содержать:

- PID;
- hostname;
- timestamp;
- mode;
- workspace path;
- process start marker.

Правила:

- stale lock определяется по TTL и проверке процесса, где возможно;
- автоматическое удаление stale lock разрешено только после проверки и записи в log;
- lock timeout настраивается в YAML;
- read-only `status` может показывать lock, но не должен обходить активный lock для mutating mode;
- hooks и CLI используют один формат lock, чтобы не возникло двух независимых блокировок.

## 13. Логирование и отчёты

### 13.1. Внешний audit log

Хранить вне Git, например:

```text
~/.cache/freebuff-sync/sync.log
~/.cache/freebuff-sync/runs/<timestamp>-<mode>.json
```

Включать:

- timestamp и duration;
- mode и CLI arguments без секретов;
- local/server paths;
- branch и commit IDs;
- Git commands в безопасно redacted-виде;
- fetch/pull/merge/push results;
- created/changed/deleted/conflict counts;
- lock events;
- hook result;
- SQLite backup result;
- exit code;
- полный diff по выбранной политике.

Содержимое секретных файлов никогда не логировать.

### 13.2. Tracked report

Внутри workspace использовать отдельную папку, например:

```text
.freebuff/sync-reports/
```

Там хранить только итоговые отчёты, пригодные для Git-аудита. Содержимое должно быть ограничено metadata/diff policy; секретные значения маскируются.

Чтобы отчёты не создавали бесконечный цикл `watch -> commit -> push`, tracked reports должны иметь debounce/ignore-механику или записываться после sync с защитой от повторного запуска.

## 14. Обработка ошибок

Скрипт обязан fail-closed при:

- недоступном SSH;
- неправильном SSH alias;
- отсутствии Git;
- отсутствии или неоднозначности server path;
- неожидаемом remote URL;
- dirty server worktree во время hook update;
- конфликте;
- неуспешном SQLite backup;
- обнаружении неподтверждённых подозрительных файлов;
- истечении lock timeout;
- нехватке диска;
- попытке force push/reset/clean без явного разрешения;
- некорректном YAML.

Exit codes должны быть стабильными, например:

| Код | Значение |
|---:|---|
| `0` | Успех; обе стороны verified clean/equal |
| `1` | Операционная ошибка или инфраструктура недоступна |
| `2` | Конфликт или требуется ручное решение |
| `3` | Небезопасные/подозрительные файлы требуют решения |
| `4` | Неверная конфигурация |
| `5` | Lock занят или истёк timeout |

## 15. Безопасность

- SSH выполняется через настроенный alias `wimp`; пароль и приватный ключ скрипт не получает и не логирует.
- Не использовать `shell=True` для составления Git/SSH команд.
- Использовать argv-массивы и безопасное quoting только там, где shell неизбежен.
- Запрещены скрытые `git push --force`, `git reset --hard`, `git clean -fd` и рекурсивное удаление.
- Пути из YAML нормализуются и проверяются на выход за разрешённый workspace.
- Файлы `.env`, `.keys` и ключи должны быть защищены независимо от текущего состояния `.gitignore`.
- Скрипт должен проверять tracked secrets перед push.
- Логи и diff проходят redaction до записи.
- Hook не запускает произвольные команды из commit message или имени файла.

## 16. Требования к Termux

- Python 3.11+;
- Git доступен как `git`;
- OpenSSH-клиент доступен как `ssh`;
- отсутствие systemd не должно мешать `watch`;
- `watch` запускается в foreground и корректно завершается по SIGINT/SIGTERM;
- `inotifywait` определяется через `shutil.which`/эквивалент;
- при отсутствии `inotifywait` используется polling без падения;
- пути работают с Android storage и пробелами;
- не требовать root;
- не требовать Docker;
- не записывать runtime lock/log в `/tmp`, если это ухудшает сохранность после перезапуска Termux.

## 17. Acceptance criteria

### Bootstrap

- [ ***REMOVED*** локальный root найден по Git и canonical markers;
- [ ***REMOVED*** `ssh wimp` проходит BatchMode/timeout probe;
- [ ***REMOVED*** SSH identity, Git/runtime capabilities и free space записаны в discovery report;
- [ ***REMOVED*** remote probe ограничен фиксированным protocol=1 contract;
- [ ***REMOVED*** `remote.lock_path` и `remote.log_dir` валидированы;
- [ ***REMOVED*** найденные remote candidates записаны со score и reasons;
- [ ***REMOVED*** при неоднозначности путь не выбран молча;
- [ ***REMOVED*** серверная Freebuff-папка, bare repo и worktree заданы в YAML;
- [ ***REMOVED*** `bare_repo` и `worktree` не пересекаются;
- [ ***REMOVED*** dry-run plan проверен до mutating bootstrap;
- [ ***REMOVED*** существующее серверное содержимое сохранено до merge;
- [ ***REMOVED*** bare repo создан/проверен;
- [ ***REMOVED*** server worktree создан/подключён;
- [ ***REMOVED*** branch policy согласована;
- [ ***REMOVED*** hooks установлены и проверены;
- [ ***REMOVED*** `.gitignore` и фильтры применяются;
- [ ***REMOVED*** suspicious/unknown manifest сформирован;
- [ ***REMOVED*** секреты не попали в commit/push.

### Functional

- [ ***REMOVED*** `push` доставляет телефонный commit в bare repo и server worktree;
- [ ***REMOVED*** `pull` получает серверный commit без потери локальной работы;
- [ ***REMOVED*** `sync` объединяет изменения обеих сторон;
- [ ***REMOVED*** конфликт останавливает процесс и сохраняет merge state;
- [ ***REMOVED*** `watch` работает через inotify или polling fallback;
- [ ***REMOVED*** `status` показывает локальное и серверное состояние;
- [ ***REMOVED*** удаления зеркалируются только через Git;
- [ ***REMOVED*** untracked/ignored файлы не удаляются без явного разрешения;
- [ ***REMOVED*** lock защищает параллельные операции;
- [ ***REMOVED*** SQLite backup создаётся согласованно.

### Verification

- [ ***REMOVED*** после успешной операции local HEAD == server worktree HEAD;
- [ ***REMOVED*** оба дерева clean;
- [ ***REMOVED*** bare repo содержит текущий commit;
- [ ***REMOVED*** отчёт содержит commit IDs, counts, operations, errors и diff;
- [ ***REMOVED*** повторный `sync` идемпотентен и не создаёт пустых commits;
- [ ***REMOVED*** сервер не получает архивы, секреты, кэши и несвязанные документы;
- [ ***REMOVED*** скрипт запускается на Termux без ручного редактирования shell-команд.

## 18. Тестовая стратегия

До реализации необходимо добавить hermetic-тесты для:

- YAML parsing и defaults;
- include/exclude/allowlist classification;
- secret/suspicious file detection;
- command argv construction без `shell=True`;
- local/server discovery responses;
- bootstrap plan в dry-run;
- clean/dirty/conflict Git states;
- ahead/behind calculation;
- deletion threshold;
- stale lock и concurrent lock;
- SQLite backup path;
- inotify availability и polling fallback;
- watch debounce;
- hook installation and post-receive behavior through fake repositories;
- stable exit codes;
- JSON/text status output;
- redaction in log/diff reports.

Реальный SSH bootstrap и операции на `wimp` должны быть отдельным операторским acceptance-тестом с сохранённым run report. Unit-тесты не должны зависеть от настоящего сервера или production-секретов.

## 19. Рекомендуемая структура реализации

Предпочтительно добавить отдельный модуль, не переписывая существующие платформенные серверы:

```text
scripts_01/freebuff_sync.py          # CLI entry point
scripts_01/freebuff_sync_core.py     # sync orchestration
scripts_01/freebuff_sync_config.py   # YAML contract
scripts_01/freebuff_sync_git.py      # Git/SSH argv wrappers
scripts_01/freebuff_sync_lock.py     # local/server lock
scripts_01/freebuff_sync_watch.py    # inotify/polling backend
scripts_01/freebuff_sync_hooks.py    # hook templates/install
scripts_01/freebuff_sync_report.py   # logs, redaction, diff reports
scripts_01/freebuff_sync_sqlite.py   # SQLite backup API
.freebuff/sync.yaml                  # workspace config
.freebuff/sync-reports/              # tracked reports
```

Это предложение, а не обязательное требование к количеству файлов. Реализация должна оставаться аддитивной и не ломать существующие `remote_sync.py`, MCP/API-серверы и рабочие Git-процессы Freebuff.

## 20. Открытые предположения

1. SSH alias `wimp` уже настроен в `~/.ssh/config` и позволяет выполнять команды без пароля.
2. На сервере можно создать каталоги и Git hooks в пределах пользователя SSH.
3. На сервере установлен Git; Python 3.11+ желателен для скрипта и SQLite backup.
4. Фактический путь к серверной Freebuff-папке ещё не проверялся; он должен быть задан в `.freebuff/sync.yaml` после discovery.
5. У серверной существующей копии могут быть изменения, отсутствующие на телефоне; bootstrap обязан сохранить их и предложить merge.
6. Документы, архивы и прочие материалы, не связанные с платформой, должны быть классифицированы как `suspicious`/`unknown` и исключены до явного allowlist.
7. Точный список найденных runtime-баз зафиксирован в §5.4; по умолчанию `runtime_data: false`, а включение выполняется адресно через `runtime_allowlist` и `sqlite_allowlist`.
8. Серверный post-receive hook обновляет рабочую копию, но не запускает сервисы и не делает production deployment.
9. Автоматический `watch` допустим только после того, как YAML, hooks, filters и lock проверены dry-run.
10. `remote.lock_path` и `remote.log_dir` заданы явно либо получены из однозначного `$HOME` probe; runtime paths не подставляются молча.
11. Повторный bootstrap после успешного завершения не создаёт новый bare repo, seed branch или backup без обнаруженного изменения состояния.

## 21. Порядок будущей реализации

1. Провести read-only discovery локального и серверного окружения.
2. Выполнить локальную и bounded SSH discovery по §8.1–§8.2.
3. Зафиксировать выбранные реальные серверные пути в `.freebuff/sync.yaml`.
4. Выполнить классификацию файлов и согласовать suspicious/unknown manifest.
5. Реализовать Git/SSH wrappers и безопасные lock-и.
6. Реализовать dry-run bootstrap и резервирование существующей серверной папки.
7. Создать bare repo и server worktree.
8. Установить и проверить hooks.
9. Реализовать `status`, затем `push`/`pull`, затем `sync`.
10. Добавить SQLite backup и отчёты.
11. Добавить `watch` с inotify/polling fallback.
12. Запустить hermetic tests.
13. Выполнить операторский bootstrap на `wimp` только после проверки dry-run.
14. Проверить invariant `local HEAD == server HEAD` и clean trees.

## 22. Ограничение текущей сессии

В рамках подготовки этой спецификации:

- код не создавался и не изменялся;
- команды на `wimp` не выполнялись;
- серверная папка фактически не исследовалась;
- Git repository и hooks на сервере не создавались;
- allowlist/denylist дополнены по локальному дереву workspace и текущему `.gitignore`;
- этот файл является единственным новым артефактом текущей задачи.
