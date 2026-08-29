# RUNNABLE — Interior Planner (Дизайнер интерьеров)

**Версия:** 1.0  
**Дата:** 2026-08-06  
**Проект:** `projects_17/interior_planner/interior_planner_web`

## Поддерживаемые платформы

- [x***REMOVED*** **Web** (esbuild-wasm + HTML5 Canvas) — основной режим
- [ ***REMOVED*** iOS (Expo Go) — не тестировалось
- [ ***REMOVED*** Android (Expo Go) — нежизнеспособен на Termux (CON-41)

## Минимальные требования

- Node.js: >= 20 LTS (на Termux: v26 — штатная)
- Файловая система: ext4 / APFS (symlinks required). **FAT32/exFAT: только web-фолбэк с --no-bin-links**
- Свободная память: >= 1 GB
- Порты: 8080 (или 3000)

## Быстрый старт

### Web (рекомендуется для тестирования)

```bash
cd projects_17/interior_planner/interior_planner_web

# 1. Установка зависимостей
npm install --legacy-peer-deps --no-bin-links

# 2. Сборка
node node_modules/esbuild-wasm/bin/esbuild src/index.tsx \
  --bundle --outfile=dist/bundle.js \
  --alias:react-native=react-native-web \
  --define:global=window \
  --format=iife --loader:.tsx=tsx --loader:.ts=ts \
  --platform=browser

# 3. Запуск сервера
node /tmp/serve.js </dev/null >/tmp/server.log 2>&1 &
# Открыть: http://192.168.0.5:8080
```

### iOS / Android (Expo — нестабильно)

```bash
cd projects_17/interior_planner/interior_planner_app_expo
npm install --legacy-peer-deps --no-bin-links
node node_modules/expo/bin/cli start
```

## Известные блокеры

| Блокер | Причина | Обход |
|--------|---------|-------|
| **FAT32/exFAT (sdcard)** | Нет symlinks → `npx`/`expo` не работают | Полные пути к CLI: `node node_modules/expo/bin/cli` |
| **Android/Termux** | Phantom Process Killer, OOM, нет arm64-бинарников | Только web-фолбэк (esbuild-wasm) |
| **Node v26** | Несовместимость с нативными модулями | Web-фолбэк не использует нативные модули — безопасно |
| **Порт 8080 занят** | Другой сервер | Использовать порт 3000 |
| **Фоновый процесс умирает** | stdin закрывается | `</dev/null >log.txt 2>&1` |

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|-----------|-----------|-------------|
| `PORT` | Порт dev-сервера | 8080 |

## Связанные документы

- `PROJECT_REQUIREMENTS.md` — стандарт готовности проектов
- `CON-41/42/43` в `core_02/LESSONS.md` — уроки запуска на Android/Termux
- `PB-15` — проекты без RUNNABLE.md
