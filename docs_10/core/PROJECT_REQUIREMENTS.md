# PROJECT_REQUIREMENTS.md — Стандарт готовности проектов Freebuff

**Версия:** 1.0  
**Дата:** 2026-08-06  
**Релиз:** v5.98.0  
**Статус:** 📋 Принято  
**Основание:** PB-15, CON-41/42/43 (interior_planner launch — Android/Termux)

---

## 1. Обязательные артефакты проекта

Каждый проект в `projects_17/` или внешнем workspace **должен** содержать:

| Файл | Назначение | Блокирует запуск без него? |
|------|-----------|---------------------------|
| **RUNNABLE.md** | Инструкции по запуску на всех платформах | ✅ Да |
| **CHECKLIST.md** | Pre-flight проверки среды | ✅ Да |
| **README.md** | Описание проекта, архитектура, ссылки | ⚠️ Warning |
| **package.json / Cargo.toml / requirements.txt** | Зависимости с зафиксированными версиями | ✅ Да |

---

## 2. RUNNABLE.md — структура

```markdown
# RUNNABLE — Project Name

## Поддерживаемые платформы
- [x***REMOVED*** Web (esbuild-wasm)
- [ ***REMOVED*** iOS (Expo Go)
- [ ***REMOVED*** Android (Expo Go)

## Минимальные требования
- Node.js: >= 20 LTS
- Файловая система: ext4 / APFS / NTFS (symlinks required)
- Свободная память: >= 2 GB
- Порты: 8080, 3000

## Быстрый старт

### Web (рекомендуется для тестирования)
\`\`\`bash
npm install --legacy-peer-deps --no-bin-links
node node_modules/esbuild-wasm/bin/esbuild src/index.tsx --bundle --outfile=dist/bundle.js --alias:react-native=react-native-web --define:global=window --format=iife --loader:.tsx=tsx --platform=browser
python3 -m http.server 8080
\`\`\`

### iOS / Android
\`\`\`bash
npx expo start
\`\`\`

## Известные блокеры
- **FAT32/exFAT (sdcard):** --no-bin-links → npx/expo не работают. Используйте полные пути к CLI.
- **Android/Termux:** фоновые процессы требуют \`</dev/null\`. Expo/Metro нежизнеспособен — используйте web-фолбэк.
- **Node v26:** возможна несовместимость с нативными модулями. Используйте v20/v22 LTS.

## Переменные окружения
| Переменная | Назначение | По умолчанию |
|-----------|-----------|-------------|
| \`PROJECT_HOME\` | Корень проекта | \`pwd\` |
| \`PORT\` | Порт dev-сервера | 8080 |
```

---

## 3. CHECKLIST.md — структура

```markdown
# CHECKLIST — Project Name

## Pre-flight (запускать перед каждым билдом)

### Окружение
- [ ***REMOVED*** Node.js: `node --version` (ожидается >= 20 LTS)
- [ ***REMOVED*** Файловая система: `df -T .` (не FAT32/exFAT)
- [ ***REMOVED*** Symlinks: `ln -sf /dev/null /tmp/_test_ln && rm /tmp/_test_ln` (должен отработать)
- [ ***REMOVED*** Свободная память: `free -m` (>= 1 GB available)

### Зависимости
- [ ***REMOVED*** `npm install` / `pip install -r requirements.txt` (без ошибок; на FAT32/exFAT: `npm install --legacy-peer-deps --no-bin-links`)
- [ ***REMOVED*** `python -c 'import yaml'` (для Python-проектов)
- [ ***REMOVED*** `node -e "require('react')"` (для Node-проектов)

### Порты
- [ ***REMOVED*** `ss -tlnp | grep PORT` (порт свободен)

### Web-фолбэк (если проект с нативными зависимостями)
- [ ***REMOVED*** esbuild-wasm установлен: `ls node_modules/esbuild-wasm`
- [ ***REMOVED*** Web-бандл собирается: `node node_modules/esbuild-wasm/bin/esbuild ...`
- [ ***REMOVED*** HTML5 Canvas работает: открыть в браузере
```

---

## 4. Web-фолбэк — обязателен для проектов с нативными зависимостями

Любой проект, использующий React Native, Expo, или другие нативные фреймворки, **должен** иметь web-версию для тестирования на устройстве разработчика.

### Требования к web-фолбэку

1. **Бандлер:** `esbuild-wasm` (чистый WASM, работает на любом CPU).
2. **Адаптер:** `react-native` → `react-native-web` (alias в esbuild).
3. **Холст:** HTML5 Canvas вместо react-native-skia.
4. **Хранилище:** `localStorage` вместо AsyncStorage.
5. **Жесты:** нативные mouse events вместо react-native-gesture-handler.
6. **Сервер:** `python3 -m http.server` или Node.js `http.createServer`.

### Команда сборки (шаблон)

```bash
node node_modules/esbuild-wasm/bin/esbuild src/index.tsx \
  --bundle --outfile=dist/bundle.js \
  --alias:react-native=react-native-web \
  --define:process.env.NODE_ENV="development" \
  --define:global=window \
  --format=iife --loader:.tsx=tsx --loader:.ts=ts \
  --platform=browser
```

---

## 5. Environment Doctor — роль для blueprint_v3

**Role ID:** `environment_doctor`  
**Capabilities:** `["diagnose", "validate", "report"***REMOVED***`  
> ⚠️ **TODO:** токены `diagnose`, `validate`, `report` должны быть зарегистрированы в `ModelCatalog.capabilities` (CON-8 vocabulary defense). Без этого SmartRouter уйдёт в fallback.  

### Обязанности
1. Проверяет окружение перед запуском любого проекта (Node, FS, память, порты).
2. Сверяет наличие RUNNABLE.md и CHECKLIST.md.
3. Возвращает `{ ok: boolean, warnings: string[***REMOVED***, blockers: string[***REMOVED*** ***REMOVED***`.

### Контракт
- **Input:** путь к проекту (`project_root`)
- **Output:** JSON-отчёт о готовности среды
- **Блокирует запуск** при наличии blockers (не warnings).

### Алгоритм (псевдокод)
```python
def diagnose(project_root: Path) -> dict:
    blockers = [***REMOVED***
    warnings = [***REMOVED***

    # 1. Файловая система
    fs_type = get_fs_type(project_root)
    if fs_type in ("fuseblk", "exfat", "fat32"):
        blockers.append(f"FS {fs_type***REMOVED*** не поддерживает symlinks")

    # 2. Node.js
    node_ver = get_node_version()
    if node_ver.major < 20:
        blockers.append(f"Node {node_ver***REMOVED*** < 20 LTS")

    # 3. Память
    avail_mb = get_available_memory()
    if avail_mb < 1024:
        blockers.append(f"Доступно {avail_mb***REMOVED***MB (< 1GB)")

    # 4. Артефакты
    for f in ("RUNNABLE.md", "CHECKLIST.md"):
        if not (project_root / f).exists():
            blockers.append(f"Отсутствует {f***REMOVED***")

    # 5. Порты
    if is_port_used(8080):
        warnings.append("Порт 8080 занят")

    return {"ok": len(blockers) == 0, "warnings": warnings, "blockers": blockers***REMOVED***
```

---

## 6. Требования к коду

### 6.1 Структура проекта
```
project/
├── RUNNABLE.md          # обязателен
├── CHECKLIST.md         # обязателен
├── README.md            # обязателен
├── src/                 # исходный код
├── tests/               # тесты
├── dist/                # web-бандл (для web-фолбэка)
├── package.json         # зависимости с pinned versions
└── index.html           # точка входа для web-фолбэка
```

### 6.2 Типы файловых систем
| FS | Symlinks | Рекомендация |
|----|----------|-------------|
| ext4 | ✅ | Штатный режим |
| APFS | ✅ | Штатный режим |
| NTFS | ⚠️ | Могут быть проблемы с правами |
| **FAT32/exFAT (sdcard)** | ❌ | Только web-фолбэк, `--no-bin-links`, полные пути к CLI |

### 6.3 Версии Node.js
| Версия | Статус |
|--------|--------|
| 20 LTS | ✅ Рекомендуется |
| 22 LTS | ✅ Рекомендуется |
| 26 | ⚠️ Возможна несовместимость с нативными модулями. На Termux — единственная доступная, штатная. |
| < 20 | ❌ Не поддерживается |

---

## 7. Процесс приёмки нового проекта

1. **Environment Doctor** — проверка среды (автоматически).
2. **Артефакты** — RUNNABLE.md, CHECKLIST.md, README.md присутствуют.
3. **Web-фолбэк** — если проект с нативными зависимостями: esbuild-wasm конфиг работает.
4. **Pre-flight** — CHECKLIST.md пройден без blockers.
5. **Запуск** — `RUNNABLE.md` → быстрый старт отрабатывает без ошибок.

---

## Связанные артефакты

- `core_02/LESSONS.md` — CON-41, CON-42, CON-43, PB-15
- `docs_10/core/ARCHITECTURAL_DEBT.md` — CAN-8 (interior_planner /tmp hardcodes)
- `projects_17/interior_planner/` — боевой пример применения стандарта
