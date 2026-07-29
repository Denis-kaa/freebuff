# BOOTSTRAP SPECIFICATION — Bootstrap Engine

> **Версия:** 1.0.0  
> **Дата:** 2026-07-29  
> **Статус:** Спецификация (к реализации)  
> **Основание:** [VISION_3.0.md***REMOVED***(VISION_3.0.md), [promt14.md***REMOVED***(../pompts/promt14.md) (концепция #4)  

> **⚠️ Важно:** Существующий `scripts/bootstrap.py` отвечает за **сессионный bootstrap** (создание сессии, конспект, StreamBridge).
> Новая спецификация описывает **environment bootstrap** (развёртывание окружения).
> При реализации Bootstrap Engine оба компонента будут объединены:
> - `BootstrapEngine.session()` — сессионный bootstrap (миграция из `scripts/bootstrap.py`)
> - `BootstrapEngine.run()` — environment bootstrap (новый компонент)

---

## 1. Executive Summary

Bootstrap Engine — это компонент Core, отвечающий за **идемпотентное развёртывание полностью готовой AI-среды**.

**Ключевое требование:** повторный запуск никогда не должен ломать систему.

**Что делает Bootstrap Engine:**
- Проверяет окружение (Termux, Python, Node.js, Git, зависимости)
- Устанавливает недостающие компоненты (только если их нет)
- Настраивает конфигурацию (PATH, переменные окружения, алиасы)
- Запускает Runtime Installer для выбранных AI Runtime
- Выполняет диагностику после установки
- Создаёт отчёт о состоянии

**Bootstrap Engine — не установщик. Это менеджер состояния среды.**

---

## 2. Архитектура

### 2.1 Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                    BOOTSTRAP ENGINE                           │
│                                                               │
│  ┌─────────────────────┐    ┌─────────────────────────────┐  │
│  │  Environment Checker │    │     Environment Installer   │  │
│  │                      │    │                             │  │
│  │  • OS detection      │    │  • Package manager          │  │
│  │  • Termux check      │    │  • pip/npm/pkg             │  │
│  │  • Python version    │    │  • Runtime dependencies     │  │
│  │  • Node.js version   │    │  • System dependencies      │  │
│  │  • Git available     │    │  • proot-distro (опц.)      │  │
│  │  • Disk space        │    │                             │  │
│  │  • RAM               │    └─────────────────────────────┘  │
│  └─────────────────────┘                                      │
│                                                               │
│  ┌─────────────────────┐    ┌─────────────────────────────┐  │
│  │  Config Manager     │    │   Runtime Installer          │  │
│  │                     │    │                              │  │
│  │  • PATH setup       │    │  • freebuff CLI             │  │
│  │  • Environment vars │    │  • Claude Code (MCP)        │  │
│  │  • Aliases          │    │  • OpenClaw                  │  │
│  │  • .env file        │    │  • Qwen/Ollama (freebuff)   │  │
│  │  • Config profiles  │    │  • Будущие Runtime           │  │
│  └─────────────────────┘    └─────────────────────────────┘  │
│                                                               │
│  ┌─────────────────────┐    ┌─────────────────────────────┐  │
│  │  Runtime Doctor     │    │   Report Generator           │  │
│  │                     │    │                              │  │
│  │  • Проверка PATH   │    │  • Установленные компоненты  │  │
│  │  • Проверка Runtime│    │  • Пропущенные компоненты   │  │
│  │  • Проверка ключей │    │  • Версии                   │  │
│  │  • Health check    │    │  • Проблемы                 │  │
│  └─────────────────────┘    └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Абстракции

```
┌──────────────────────┐
│   BootstrapProfile   │  ← Профиль установки (Minimal, Developer, Offline, ...)
├──────────────────────┤
│   EnvironmentState   │  ← Текущее состояние окружения
├──────────────────────┤
│   InstallStep        │  ← Один шаг установки (идемпотентный)
├──────────────────────┤
│   RuntimeDefinition  │  ← Определение Runtime (имя, источник, версия)
├──────────────────────┤
│   BootstrapReport    │  ← Результат bootstrap (успех/ошибки/предупреждения)
└──────────────────────┘
```

### 2.3 Жизненный цикл

```
start()
  │
  ├── 1. SYSTEM CHECK ────────────────────────
  │     ├── OS detection (Android/Termux/Linux/Mac)
  │     ├── Python version check (>= 3.11)
  │     ├── Node.js check (>= 18, optional)
  │     ├── Git check
  │     ├── Disk space (> 1 GB free)
  │     ├── RAM (> 2 GB available)
  │     └── Termux environment (PREFIX, PATH, LD_LIBRARY_PATH)
  │
  ├── 2. CONFIG LOAD ─────────────────────────
  │     ├── Load profile (bootstrap_profile.yaml)
  │     ├── Load .env (if exists)
  │     ├── Load existing state (bootstrap_state.json)
  │     └── Determine steps needed
  │
  ├── 3. INSTALL ──────────────────────────────
  │     ├── System dependencies (curl, wget, build-essential)
  │     ├── Python packages (requirements.txt)
  │     ├── freebuff CLI (via npm/pip)
  │     ├── Runtime (по профилю)
  │     │     ├── freebuff CLI
  │     │     ├── Claude Code (через MCP)
  │     │     ├── OpenClaw (через git)
  │     │     ├── Qwen/Ollama (freebuff)
  │     │     └── Будущие Runtime
  │     └── Config files (.bashrc, .env, aliases)
  │
  ├── 4. DIAGNOSE ─────────────────────────────
  │     ├── Runtime Doctor
  │     ├── PATH check
  │     ├── Dependencies check
  │     ├── Key validation
  │     └── Health check
  │
  └── 5. REPORT ───────────────────────────────
        ├── bootstrap_report.json
        ├── bootstrap_report.md
        └── Exit code (0 = ok, 1 = warnings, 2 = errors)
```

---

## 3. Компоненты

### 3.1 BootstrapEngine (класс)

```python
class BootstrapEngine:
    """Главный класс Bootstrap Engine."""

    def __init__(self, workspace_root: Path, profile: str = "minimal"):
        ...

    def run(self) -> BootstrapReport:
        """Запускает полный bootstrap."""
        ...

    def check_environment(self) -> EnvironmentState:
        """Проверяет текущее состояние окружения."""
        ...

    def install_missing(self, state: EnvironmentState) -> List[InstallResult***REMOVED***:
        """Устанавливает недостающие компоненты (идемпотентно)."""
        ...

    def diagnose(self) -> DiagnosticReport:
        """Запускает Runtime Doctor."""
        ...

    def generate_report(self) -> BootstrapReport:
        """Генерирует отчёт."""
        ...
```

### 3.2 EnvironmentState

```python
@dataclass
class EnvironmentState:
    """Текущее состояние окружения."""

    # System
    os_type: str                          # android, linux, mac, unknown
    is_termux: bool
    python_version: str
    python_path: str
    node_version: Optional[str***REMOVED***
    git_available: bool
    has_proot: bool

    # Resources
    disk_free_gb: float
    ram_available_mb: int
    ram_total_mb: int

    # Dependencies
    pip_packages: Dict[str, str***REMOVED***          # name → version
    npm_packages: Dict[str, str***REMOVED***          # name → version
    system_packages: List[str***REMOVED***            # installed via pkg/apt

    # Runtimes
    runtimes: Dict[str, RuntimeState***REMOVED***     # name → {installed, version, path***REMOVED***

    # Config
    path_dirs: List[str***REMOVED***
    env_vars: Dict[str, str***REMOVED***
    has_env_file: bool
    has_keypool: bool

    # Project
    workspace: Path
    has_git: bool
    git_branch: str
    git_remote: Optional[str***REMOVED***
```

### 3.3 BootstrapProfile

```python
@dataclass
class BootstrapProfile:
    """Профиль установки."""

    name: str                              # "minimal", "developer", "offline", ...
    description: str

    # Что устанавливать
    runtimes: List[str***REMOVED***                    # Какие Runtime подключать
    extensions: List[str***REMOVED***                  # Какие Extensions активировать
    labs: List[str***REMOVED***                        # Какие Labs активировать

    # Системные зависимости
    system_packages: List[str***REMOVED***
    python_packages: List[str***REMOVED***
    npm_packages: List[str***REMOVED***

    # Настройки
    env_vars: Dict[str, str***REMOVED***
    aliases: Dict[str, str***REMOVED***
    config_files: List[str***REMOVED***

    # Runtime-specific
    default_runtime: str                   # Какой Runtime использовать по умолчанию
    default_provider: str                  # Какой провайдер
    default_model: str                     # Какая модель
    offline_mode: bool                     # Работать без интернета?
    auto_update: bool                      # Авто-обновление?
```

### 3.4 RuntimeDefinition

```python
@dataclass
class RuntimeDefinition:
    """Определение AI Runtime."""

    name: str                              # "freebuff", "claude-code", "openclaw", ...
    display_name: str                      # "Freebuff CLI", "Claude Code", ...
    source: str                            # "npm:@freebuff/cli", "github:...", ...
    version: str                           # "latest" или конкретная версия
    install_type: str                      # "npm", "pip", "git", "binary", "mcp"
    install_path: Optional[str***REMOVED***            # Куда устанавливать
    bin_name: str                          # Имя бинарника (freebuff, claude, ...)
    post_install: List[str***REMOVED***                # Команды после установки
    requires: List[str***REMOVED***                    # Зависимости (python >= 3.11, ...)
    mcp_config: Optional[Dict***REMOVED***             # Конфиг MCP для подключения
```

## 4. Bootstrap Profiles

| Профиль | Runtime | Components | Сценарий |
|---------|---------|------------|----------|
| **minimal** | Текущий Runtime | Core только | Быстрый старт, минимальное потребление |
| **developer** | freebuff + Claude | Core + Extensions (MCP, Bridge, Scenario) | Повседневная разработка |
| **offline** | freebuff (Qwen/Ollama) | Core + Knowledge + OOM | Работа без интернета |
| **cloud** | Любой через API | Core + Provider Pool + Policy Engine | Мощные модели по запросу |
| **android** | Termux + freebuff | Core + OOM + Monitor + TG Bot | Нативное использование на телефоне |
| **research** | Все доступные | Core + Extensions + Labs | Исследования, RAG, Graph |
| **enterprise** | По политикам | Core + Extensions + Labs + Audit | Командная работа, безопасность |
| **team** | freebuff + Claude | Core + Presence + Collaboration | Совместная разработка |

## 5. Идемпотентность

**Главный принцип Bootstrap Engine: повторный запуск не должен ничего ломать.**

### 5.1 Правила идемпотентности

| Операция | Правило |
|----------|---------|
| **Установка пакета** | `pip install` → проверка `pip list` перед установкой |
| **Клонирование репозитория** | `git clone` → проверка `if dir exists` |
| **Создание файла** | `write_file` → проверка `if not exists` или `if content changed` |
| **Добавление в PATH** | `export PATH=...` → проверка `if not already in PATH` |
| **Добавление алиаса** | `alias foo=...` → проверка `if not already set` |
| **Создание .env** | `write .env` → merge с существующим (не перезаписывать) |
| **Конфигурация** | `update_config` → diff-based, только изменившееся |

### 5.2 Авто-обновление

Bootstrap Engine поддерживает механизм авто-обновления для всех управляемых компонентов:

**Стратегия обновления:**
1. При каждом `run()` Engine сравнивает `bootstrap_state.json` с актуальными версиями из `profiles.yaml` и `runtimes.yaml`
2. Если версия компонента изменилась — запускается `install_missing(component_name, force=True)`
3. Если компонент установлен вручную (не через Engine) — Engine не трогает его, только предупреждает
4. Пользователь может отключить авто-обновление через `BootstrapProfile.auto_update = False`

**Правила обновления:**

| Компонент | Стратегия | Риск |
|-----------|-----------|------|
| Python-пакеты | `pip install --upgrade` | Низкий — semver в requirements.txt |
| npm-пакеты | `npm update -g` | Средний — breaking changes возможны |
| Git-репозитории | `git pull --ff-only` | Средний — merge conflict |
| Конфигурация | diff-based merge | Низкий — только новые поля |
| System packages | `pkg upgrade` (только если явно запрошено) | Высокий — меняет всю систему |

**Механизм сравнения версий:**
```python
from packaging.version import Version

def _needs_update(self, component: str, current_ver: str, expected_ver: str) -> bool:
    if expected_ver == "latest":
        return True  # всегда проверять latest
    if current_ver == expected_ver:
        return False  # уже актуально
    # semver comparison (packaging.version handles PEP 440)
    return Version(current_ver) < Version(expected_ver)
```

### 5.3 State-файл

```yaml
# bootstrap_state.json — сохраняется после каждого успешного bootstrap
bootstrap_version: "1.0.0"
timestamp: "2026-07-29T12:00:00Z"
profile: "developer"

environment:
  python: "3.14.1"
  node: "22.0.0"
  git: "2.45.0"
  os: "android"
  termux: true

runtimes:
  freebuff:
    installed: true
    version: "1.0.0"
    path: "/data/data/com.termux/files/usr/bin/freebuff"
  claude-code:
    installed: false
    reason: "not in profile"

steps:
  - name: "check_environment"
    status: "passed"
    duration_ms: 120
  - name: "install_python_deps"
    status: "passed"
    duration_ms: 15000
  - name: "install_freebuff"
    status: "skipped"
    reason: "already installed"

warnings: 2
errors: 0
report_path: "bootstrap_report.md"
```

## 6. API

### 6.1 CLI

```bash
# Полный bootstrap с профилем
buffy bootstrap --profile developer

# Только проверка
buffy bootstrap --check

# Диагностика
buffy doctor

# Список профилей
buffy bootstrap --list-profiles

# Статус последнего bootstrap
buffy bootstrap --status

# Переустановка конкретного компонента
buffy bootstrap --reinstall freebuff
```

### 6.2 Python API

```python
from freebuff_plugin.bootstrap import BootstrapEngine

engine = BootstrapEngine(
    workspace_root="/path/to/workspace",
    profile="developer",
)

# Запуск
report = engine.run()

# Результат
print(report.success)      # True/False
print(report.warnings)     # ["Python 3.14 not tested"***REMOVED***
print(report.errors)       # [***REMOVED***
print(report.steps)        # [InstallStep, ...***REMOVED***
```

### 6.3 MCP Tools (через MCP Server)

Bootstrap MCP tools регистрируются в `scripts/mcp_server.py` по тому же паттерну, что и Bridge Layer:

```python
# В mcp_server.py — паттерн регистрации (как у Bridge Layer):
def _get_bootstrap_engine(self) -> BootstrapEngine:
    if self._bootstrap_engine is None:
        from freebuff_plugin.bootstrap import BootstrapEngine
        self._bootstrap_engine = BootstrapEngine(self.workspace)
        self._bootstrap_engine.start()
    return self._bootstrap_engine

def _register_tools(self) -> None:
    # ... существующие инструменты (bridge_connect, memory_store, ...) ...
    self.tool("bootstrap_check")(self._handle_bootstrap_check)
    self.tool("bootstrap_run")(self._handle_bootstrap_run)
    self.tool("bootstrap_status")(self._handle_bootstrap_status)
```

Каждый инструмент публикует событие в Event Bus (`bootstrap.checked`, `bootstrap.ran`, `bootstrap.status`), консистентно с `bridge.connected` и `knowledge.searched`.

```json
{
    "name": "bootstrap_check",
    "description": "Проверить состояние окружения",
    "inputSchema": {***REMOVED***
***REMOVED***
{
    "name": "bootstrap_run",
    "description": "Запустить Bootstrap Engine",
    "inputSchema": {
        "profile": { "type": "string", "enum": ["minimal", "developer", "offline", "cloud"***REMOVED*** ***REMOVED***
    ***REMOVED***
***REMOVED***
{
    "name": "bootstrap_status",
    "description": "Статус последнего bootstrap",
    "inputSchema": {***REMOVED***
***REMOVED***
```

## 7. Интеграция с существующей архитектурой

### 7.1 Связи

```
BootstrapEngine
  ├── ContextManager ─── проверяет существование context.db
  ├── StreamSession ──── проверяет streams directory
  ├── oom_protect.sh ─── проверяет swap и настройки OOM
  ├── scripts/ ───────── проверяет наличие всех скриптов
  ├── requirements.txt ─ проверяет pip пакеты
  ├── .env ───────────── проверяет переменные окружения
  ├── keys/ ──────────── проверяет API-ключи
  └── ~/.local/bin/ ──── проверяет freebuff wrapper
```

### 7.2 Профили в архитектуре

```
BootstrapProfile → определяет какие Extensions/Labs активировать
  │
  ├── minimal ───────── Core только (ContextManager, Stream, Memory, Knowledge, Event, Workflow)
  ├── developer ─────── Core + MCP + Bridge + Scenario + OOM
  ├── offline ───────── Core + Knowledge + OOM (без Provider Pool)
  ├── cloud ─────────── Core + Provider Pool + Policy Engine
  ├── android ───────── Core + TG Bot + OOM + Monitor
  ├── research ──────── Core + Extensions + Labs (RAG, Graph)
  ├── enterprise ────── Core + Extensions + Labs + Audit
  └── team ──────────── Core + Presence + Collaboration (когда готово)
```

## 8. Реализация

### 8.1 Файлы

```
freebuff_plugin/bootstrap/
├── __init__.py              # BootstrapEngine class
├── engine.py                # Основная логика
├── profiles.yaml            # BootstrapProfile definitions
├── runtimes.yaml            # RuntimeDefinition definitions
├── checker.py               # Environment Checker
├── installer.py             # Idempotent installer
├── doctor.py                # Runtime Doctor
├── reporter.py              # Report Generator
└── state.py                 # State management
```

### 8.2 Этапы реализации

| Этап | Что | Тестов | Зависимости |
|------|-----|--------|-------------|
| **1. Checker** | EnvironmentState, проверка Python/Git/Disk | 10 | Нет |
| **2. State** | bootstrap_state.json, чтение/запись/merge | 8 | Checker |
| **3. Installer** | pip install, npm install, git clone (идемпотентно) | 15 | State |
| **4. Profiles** | Загрузка profiles.yaml, профили minimal/developer | 10 | Installer |
| **5. Runtimes** | RuntimeDefinition, установка freebuff CLI | 8 | Profiles |
| **6. Doctor** | Диагностика, проверка PATH, health check | 10 | Installer |
| **7. Engine** | BootstrapEngine.run() — полный цикл | 12 | Всё |
| **8. CLI** | buffy bootstrap --profile ... | 5 | Engine |
| **9. MCP** | bootstrap_check/run/status как MCP tools | 5 | Engine |
| **ИТОГО** | | **~83 теста** | |

### 8.3 Error Recovery

Bootstrap Engine должен корректно восстанавливаться после ошибок установки.

**Сценарии восстановления:**

| Сценарий | Поведение |
|----------|-----------|
| Прерванная установка (Ctrl+C, OOM) | State-файл помечается как `incomplete`. При следующем `run()` Engine проверяет каждый шаг заново (идемпотентно) и завершает незаконченные |
| Сетевая ошибка (timeout, DNS) | Retry 3 раза с exponential backoff (1s → 2s → 4s). Если всё ещё ошибка — шаг помечается как `skipped`, Engine продолжает без него |
| Недостаточно места на диске | Engine останавливается, report содержит `error: "disk_full: need 500 MB, have 100 MB"` |
| Конфликт версий (Python 3.12 vs 3.14) | Engine проверяет `requires` каждого Runtime. Несовместимость = warning, не error |
| Частичная установка (pip install упал на 5-м из 10 пакетов) | State-файл сохраняет прогресс: `installed: [a, b, c, d***REMOVED***`, `failed: [e***REMOVED***`. При retry устанавливаются только `failed` |
| Git merge conflict после pull | Engine делает `git stash push -m "bootstrap-auto-stash"` и помечает компонент как `manual_conflict` — пользователь решает сам |

**Принцип:** Bootstrap Engine никогда не оставляет систему в нерабочем состоянии. Если шаг упал — Engine откатывает его изменения и продолжает с предупреждением.

---

## 9. Тестирование

### 9.1 Unit-тесты

| Тест | Что проверяет |
|------|--------------|
| `test_empty_env` | Bootstrap в чистом окружении |
| `test_full_env` | Bootstrap когда всё уже установлено |
| `test_partial_env` | Частично установленные компоненты |
| `test_profile_minimal` | Профиль Minimal не устанавливает лишнего |
| `test_profile_developer` | Профиль Developer устанавливает всё |
| `test_idempotent_repeat` | Повторный bootstrap не меняет состояние |
| `test_state_persistence` | State сохраняется и восстанавливается |
| `test_doctor_finds_issues` | Doctor находит отсутствующие компоненты |
| `test_runtime_install` | Установка Runtime через Installer |
| `test_error_recovery` | Восстановление после ошибки установки |

### 9.2 Boundary Testing

- Терминал без интернета (offline mode)
- Терминал с очень маленьким диском (< 100 MB)
- Терминал с Python 3.12 / 3.13 / 3.14
- Терминал без Node.js
- Терминал с очень старыми версиями пакетов
- Повторный запуск 10 раз подряд
- Прерывание в середине установки (Ctrl+C)

---

## 10. Критерии готовности

- [ ***REMOVED*** `BootstrapEngine.run()` работает в чистом Termux
- [ ***REMOVED*** Профили minimal/developer/offline проходят тесты
- [ ***REMOVED*** Идемпотентность: 3 повторных запуска — 0 изменений
- [ ***REMOVED*** Runtime Doctor находит 100% известных проблем
- [ ***REMOVED*** MCP tools bootstrap_check/run/status зарегистрированы
- [ ***REMOVED*** CLI `buffy bootstrap` работает
- [ ***REMOVED*** 83+ теста, 0 failures
- [ ***REMOVED*** Документация в README.md

---

## 11. Открытые вопросы

| Вопрос | Решение |
|--------|---------|
| Как быть с версиями Python? (Termux имеет только 3.14) | Использовать `pkg install python311` если нужно |
| Установка Node.js в Termux | `pkg install nodejs` или `nvm` |
| Claude Code — как устанавливать? | Через `npm install -g @anthropic/claude-code` |
| OpenClaw — git clone или npm? | Пока git clone + setup |
| Как обновлять существующие компоненты? | ✅ Решено: секция 5.2 (Auto-update + force + semver) |
| Что делать если нет прав на запись? | Проверять `$PREFIX` и `$HOME` |
| Как быть с scripts/bootstrap.py (существующий)? | ✅ Решено: оба объединятся в `BootstrapEngine.session()` + `BootstrapEngine.run()` |
| Как интегрировать MCP tools? | ✅ Решено: паттерн `_get_bootstrap_engine()` + `_register_tools()` как у Bridge Layer |

---

*Связанные документы: [VISION_3.0.md***REMOVED***(VISION_3.0.md), [ARCHITECTURE_3.0.md***REMOVED***(ARCHITECTURE_3.0.md), [scripts/bootstrap.py***REMOVED***(../scripts/bootstrap.py)*
