# Interior Planner (Дизайнер интерьеров)

**Версия:** 1.0  
**Дата:** 2026-08-06  
**Статус:** 🚧 Active development  
**Стек:** React + react-native-web + HTML5 Canvas + Zustand + esbuild-wasm

## Назначение

Веб-приложение для визуального проектирования интерьеров. Позволяет:
- Создавать план комнаты с размерами
- Выбирать материалы (стены, пол, потолок) с текстурами
- Расставлять мебель drag & drop
- Генерировать промт для AI-рендера интерьера

## Архитектура

```
src/
├── App.tsx                    # Точка входа
├── components/
│   ├── RoomEditor.tsx         # Главный экран: сайдбар + холст + панель
│   └── Canvas2D.tsx           # HTML5 Canvas: комната, текстуры, мебель
├── store/
│   └── roomStore.ts           # Zustand + localStorage
├── data/
│   └── knowledge_base_ru.json # Каталог мебели и материалов (русский)
└── types/
    └── domain.ts              # Типы: Project, Room, FurnitureObject
```

## Быстрый старт

```bash
cd interior_planner_web
npm install --legacy-peer-deps --no-bin-links
node node_modules/esbuild-wasm/bin/esbuild src/index.tsx --bundle --outfile=dist/bundle.js --alias:react-native=react-native-web --define:global=window --format=iife --loader:.tsx=tsx --platform=browser
node /tmp/serve.js </dev/null >/tmp/server.log 2>&1 &
# Открыть: http://192.168.0.5:8080
```

## Связанные документы

- `RUNNABLE.md` — полные инструкции по запуску
- `CHECKLIST.md` — pre-flight проверки
- `PROJECT_REQUIREMENTS.md` — стандарт готовности проектов
- `core_02/LESSONS.md` — CON-41/42/43 (уроки Android/Termux)
