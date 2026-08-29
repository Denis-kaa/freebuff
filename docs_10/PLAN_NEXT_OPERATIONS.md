# PLAN_NEXT_OPERATIONS — Развёрнутый план следующих операций

| Поле | Значение |
|------|----------|
| **Документ ID** | PLAN-NEXT-001 |
| **Версия** | 1.0 |
| **Статус** | 📋 В работе |
| **Релиз платформы** | v5.101.0 |
| **Дата** | 2026-08-06 |
| **Автор** | Buffy (анализ + синтез) |
| **Основание** | CON-45, interior_planner боевая задача, RFC Forge v1, Organizational Memory |

---

## 🔭 Контекст: что есть в системе

### Проекты (`projects_17/`)

| Проект | Статус | Тип | Стек |
|--------|--------|-----|------|
| `interior_planner/` | 🔴 боевая задача | Web-приложение | React Native Web + Canvas + esbuild-wasm |
| `diet_platform/` | ⚪ не исследован | ? | ? |
| `freebuff_flutter_app/` | ⚪ не исследован | Flutter | Dart/Flutter |
| `realtor_automation/` | ⚪ не исследован | ? | ? |
| `realtor_os/` | ⚪ не исследован | ? | ? |
| `tg_terminal_messenger/` | 🟢 рабочий (используется для TG-доставки) | CLI | Python + Telethon |

### Платформенные модули (`core_02/`)

| Модуль | Статус | Назначение |
|--------|--------|-----------|
| `blueprint_v3.py` | 🟢 | Канон ролей (17 ролей, registry.yaml) |
| `environment_doctor.py` | 🟢 v5.99.0 | Диагностика окружения |
| `router.py` / `SmartRouter` | 🟢 | Маршрутизация по capability-токенам |
| `scenario.py` + `scenario_registry.py` | 🟢 | Multi-scenario registry |
| `wizard_lib.py` | 🟢 | Wizard run поверх registry |
| `telegram_contract.py` | 🟢 | TG-отправка через Telethon |
| `workspace_registry.py` | 🟢 | Регистрация ролей в workspace |
| `remote_sync.py` | 🟢 | Remote sync StateV2a |
| `contracts.py` | 🟡 | Контракты (частично) |
| `interfaces.py` | 🟡 | Интерфейсы (частично) |

### Документация (`docs_10/`)

| Документ | Статус |
|----------|--------|
| `RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md` | 📋 RFC |
| `RFC_BUFFY_FORGE_V1.md` | 📋 RFC v1.1 |
| `core/PROJECT_REQUIREMENTS.md` | 🟢 v5.98.0 |
| `core/ARCHITECTURE_PRINCIPLES.md` | 🟢 |
| `core/CODE_QUALITY_STANDARD.md` | 🟢 |
| `core/ARCHITECTURAL_DEBT.md` | 🟢 |
| `INDEX.md` | 🟢 |
| `DOCUMENT_REGISTRY.md` | 🟢 79 документов |
| `ARCH_TRACK_SUMMARY_2026-08-05.md` | 🟢 |
| `decisions/IDEAS.md` | 🟢 §14 обновлён |

---

## 📊 Этапы плана

```
Этап 0: Закрытие долгов (CON-46, CON-47, v5.101.0 CHANGELOG)
Этап 1: Исследование проектов (diet_platform, realtor_os, freebuff_flutter_app)
Этап 2: Interior Planner — фичи v5 (touch-жесты, текстуры мебели, undo/redo)
Этап 3: Organizational Memory Engine — MVP-реализация
Этап 4: Buffy Forge v1 — метасистема L0-L5
Этап 5: Полный прогон тестов + CI-гейты
Этап 6: Архитектурный аудит + синхронизация документации
```

---

## 🟢 Этап 0: Закрытие долгов (30 мин)

### Задача 0.1 — CON-46: Урок о падении Unsplash Source API

**Промт:**
```
Зарегистрируй CON-46 в core_02/LESSONS.md — урок о внешних API-зависимостях:

Сценарий: при попытке использовать Unsplash Source API (source.unsplash.com) для картинок материалов в interior_planner обнаружилось, что сервис закрыт в 2024 году. Перешли на Picsum Photos seed API (picsum.photos/seed/{id***REMOVED***/300/300) — бесплатно, без API-ключа, стабильные изображения по ID материала.

Проблема: полагаться на бесплатные API без проверки их статуса. Unsplash был Deprecated в 2021, Sunset в 2024 — но документация всё ещё висела в поисковой выдаче.

Решение: Picsum Photos seed API — детерминированные изображения по строковому ключу. Формат: picsum.photos/seed/{seed***REMOVED***/{width***REMOVED***/{height***REMOVED***. Кэшируются браузером. Бесплатно, без регистрации.

Урок: перед интеграцией любого внешнего API проверять его статус (isitdown, статус-страница). Для некоммерческих проектов предпочитать сервисы без API-ключа (Picsum > Unsplash API > платные alternatives).
```

### Задача 0.2 — CON-47: Урок о `<img>` в react-native-web

**Промт:**
```
Зарегистрируй CON-47 в core_02/LESSONS.md — урок о несовместимости HTML-тегов с react-native-web:

Сценарий: после добавления SwatchImage компонента с сырым <img> тегом внутри react-native View приложение interior_planner перестало загружаться. esbuild молча скомпилировал бандл (без <img> в выводе), но react-native-web не смог отрендерить HTML-элемент внутри RN-дерева.

Проблема: React Native Web транслирует RN-компоненты (View→div, Text→span, etc.), но не знает что делать с сырыми HTML-тегами. Пропсы src, onLoad, onError, style={{objectFit:"cover"***REMOVED******REMOVED*** — невалидны для RN.

Решение: замена <img> на <Image source={{uri***REMOVED******REMOVED*** resizeMode="cover"> из react-native. onLoad/onError — нативные колбэки RN Image. Стиль opacity работает через RN StyleSheet.

Урок: в react-native-web всегда использовать RN-компоненты (Image, не img; TextInput, не input; ScrollView, не div с overflow). Для внешних изображений — <Image source={{uri: url***REMOVED******REMOVED*** resizeMode="cover">. Единственное исключение — <canvas> (нет RN-аналога), но его надо оборачивать в <View ref={containerRef***REMOVED***>.
```

### Задача 0.3 — v5.101.0 CHANGELOG

**Промт:**
```
Добавь v5.101.0 в CHANGELOG.md (препенд перед v5.100.0):

## [5.101.0***REMOVED*** — 2026-08-06

### Interior Planner — Picsum Photos + mobile-first fix (CON-46, CON-47)

- **CHANGED** `projects_17/interior_planner/interior_planner_web/src/components/RoomEditor.tsx`:
  - SwatchImage: заменён сырой <img> на <Image source={{uri***REMOVED******REMOVED*** resizeMode="cover"> (CON-47 — fix crash)
  - Добавлен useEffect для SSR-safe открытия сайдбара на десктопе
  - Правая панель — overlay на мобильных (< 768px) с кнопкой закрытия
  - Импорт Image из react-native
- **CHANGED** `projects_17/interior_planner/interior_planner_web/src/components/Canvas2D.tsx`:
  - Заменён фиксированный cp=Math.min(sw-340,700) на ResizeObserver (измерение реального clientWidth контейнера)
  - Асинхронная загрузка текстур из Picsum Photos: Image → createPattern, кэш в imagePatternCache
  - Убран неиспользуемый useWindowDimensions, мёртвый параметр kind в getFill
  - Контейнер: flex:1 вместо фиксированного padding
- **NEW** `projects_17/interior_planner/README.md` — закрыт warning Env Doctor
- **CON-46** (Unsplash API dead), **CON-47** (<img> crash) — зарегистрированы в core_02/LESSONS.md

Синхронизировать версии: TASK.md, BUFFY_PROJECT.md → v5.101.0.
```

---

## 🔵 Этап 1: Исследование проектов (1-2 часа)

### Задача 1.1 — Аудит diet_platform

**Промт:**
```
Исследуй projects_17/diet_platform/:
1. Прочитай README.md/RUNNABLE.md/CHECKLIST.md (если есть)
2. Определи стек (язык, фреймворк, зависимости)
3. Оцени состояние: работает/сломан/не доделан
4. Найди AGENTS.md или role-файлы
5. Запиши findings в docs_10/projects_meta/diet_platform_audit.md

Формат отчёта:
- Статус: 🟢/🟡/🔴
- Стек
- Что работает
- Что сломано
- Нужные роли (если проект запускать через пайплайн)
- Зависимости от платформы (core_02, scripts_01)
```

### Задача 1.2 — Аудит realtor_os + realtor_automation

**Промт:**
```
Исследуй projects_17/realtor_os/ и projects_17/realtor_automation/:
1. Прочитай README/RUNNABLE/CHECKLIST
2. Определи стек и зависимости
3. Оцени состояние
4. Найди связи между этими двумя проектами (один — OS, другой — automation?)
5. Запиши findings в docs_10/projects_meta/realtor_projects_audit.md
```

### Задача 1.3 — Аудит freebuff_flutter_app

**Промт:**
```
Исследуй projects_17/freebuff_flutter_app/:
1. Прочитай README/pubspec.yaml
2. Определи state (скомпилирован/запускается/сломан)
3. Проверь, есть ли связь с платформой (API-клиент к freebuff?)
4. Запиши findings в docs_10/projects_meta/freebuff_flutter_audit.md
```

### Задача 1.4 — Сводный документ по проектам

**Промт:**
```
Создай docs_10/projects_meta/PROJECTS_OVERVIEW.md — сводную таблицу всех проектов:

| Проект | Стек | Статус | Роли | Платформенные зависимости | Приоритет |
|--------|------|--------|------|--------------------------|-----------|
| interior_planner | RNW + Canvas | 🟡 в разработке | interior_consultant | environment_doctor, router | HIGH |
| diet_platform | ? | ? | ? | ? | ? |
| ... | ... | ... | ... | ... | ... |

Добавь секцию «Рекомендации»:
- Какие проекты запускать в первую очередь
- Какие требуют ролей
- Какие блокированы окружением (Android/Termux)
```

---

## 🟡 Этап 2: Interior Planner — фичи v5 (2-3 часа)

### Задача 2.1 — Touch-жесты на канвасе

**Промт:**
```
Добавь touch-поддержку в projects_17/interior_planner/interior_planner_web/src/components/Canvas2D.tsx:

1. Добавь onTouchStart/onTouchMove/onTouchEnd обработчики на canvas элемент
2. Логика:
   - Один палец — pan (перемещение выделенного объекта или скролл)
   - Два пальца — pinch-to-zoom (изменение zoomRef.current)
   - Тап — select объекта (hit-test по координатам)
   - Двойной тап — rotate (поворот на 45°)
3. Предотврати дефолтное поведение (e.preventDefault на touchstart — чтобы не скроллилась страница)
4. Учитывай DPR при конвертации touch-координат
5. Проверь что mouse-жесты продолжают работать (не сломай существующий onMouseDown/onMouseMove)

Файл: projects_17/interior_planner/interior_planner_web/src/components/Canvas2D.tsx
```

### Задача 2.2 — Текстуры мебели из Picsum на канвасе

**Промт:**
```
Добавь загрузку Picsum-текстур для мебели в Canvas2D.tsx:

Сейчас стены/пол используют getFill() → imagePatternCache для Picsum-текстур. Мебель рисуется сплошным цветом (f?.color).

1. Расширь предзагрузку в useEffect: добавь furniture catalog_id в список загружаемых текстур
2. В render: для каждого объекта мебели проверяй getImagePattern(o.catalog_id) и используй как fillStyle вместо f.color
3. Если текстура не загружена — fallback на f.color
4. Добавь furniture-текстуры в imagePatternCache

Учти: catalog_id мебели (например "sofa-3seat") отличается от materialId стен/пола. Picsum seed должен быть уникальным: `interior-furniture-${catalog_id***REMOVED***`.
```

### Задача 2.3 — Undo/Redo в roomStore

**Промт:**
```
Добавь undo/redo в projects_17/interior_planner/interior_planner_web/src/store/roomStore.ts:

1. Добавь в store: history: ProjectSnapshot[***REMOVED***, historyIndex: number
2. ProjectSnapshot = { room, objects, style_id, _light_id ***REMOVED***
3. После каждого addObject/moveObject/rotateObject/deleteObject/setRoom/setStyle — пуши snapshot в history (обрезая future)
4. Добавь экшены: undo(), redo()
5. Лимит истории: 50 снапшотов
6. Экспортируй canUndo/canRedo селекторы
7. Добавь кнопки ↩ Undo / ↪ Redo в RoomEditor.tsx (в топ-бар или сайдбар)

Файлы:
- projects_17/interior_planner/interior_planner_web/src/store/roomStore.ts
- projects_17/interior_planner/interior_planner_web/src/components/RoomEditor.tsx
```

### Задача 2.4 — Валидация размеров комнаты

**Промт:**
```
Добавь валидацию размеров комнаты в RoomEditor.tsx:

1. Минимальные размеры: 2×2м
2. Максимальные: 20×20м
3. При вводе невалидных значений — красная обводка TextInput + подсказка
4. Кнопка «Создать проект» неактивна (opacity: 0.5) при невалидных размерах
5. При клике на неактивную кнопку — Alert с описанием проблемы

Файл: projects_17/interior_planner/interior_planner_web/src/components/RoomEditor.tsx
```

### Задача 2.5 — Пересборка + тест на устройстве

**Промт:**
```
Пересобери interior_planner бандл и проверь:
1. cd projects_17/interior_planner/interior_planner_web
2. node node_modules/esbuild-wasm/bin/esbuild src/index.tsx --bundle --outfile=dist/bundle.js --alias:react-native=react-native-web --define:process.env.NODE_ENV=development --define:global=window --format=iife --loader:.tsx=tsx --loader:.ts=ts --platform=browser
3. Убедись что сборка прошла без ошибок
4. Проверь что сервер отвечает на http://192.168.0.5:8080/
5. Прогони код-ревью через code-reviewer-deepseek
```

---

## 🟠 Этап 3: Organizational Memory Engine — MVP (3-4 часа)

### Задача 3.1 — Memory Store (SQLite schema)

**Промт:**
```
Реализуй Memory Store для Organizational Memory Engine согласно RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md:

1. Создай core_02/memory_store.py
2. SQLite schema (таблицы):
   - knowledge_objects (id, type, source, content, embedding_id, created_at, updated_at, access_count, importance_score)
   - knowledge_links (source_id, target_id, rel_type, weight, created_at)
   - learning_events (id, trigger_id, context_snapshot, outcome, lesson_id, created_at)
   - experience_analytics (metric_name, metric_value, dimension, recorded_at)
3. API:
   - store_knowledge(type, content, source) → knowledge_id
   - link_knowledge(source_id, target_id, rel_type)
   - query_by_type(type) → list[KnowledgeObject***REMOVED***
   - semantic_search(embedding) → list[(KnowledgeObject, score)***REMOVED***
   - record_learning_event(trigger_id, outcome)
   - get_analytics(metric_name, dimension, time_range)
4. Используй sqlite3 из stdlib (не sqlalchemy/orm)
5. База: data_13/context.db (существующая)

Файлы: core_02/memory_store.py, tests_09/test_memory_store.py
```

### Задача 3.2 — Knowledge Graph (8 новых rel_types)

**Промт:**
```
Добавь Knowledge Graph слой поверх Memory Store согласно RFC §6:

1. В core_02/memory_store.py добавь методы:
   - find_related(knowledge_id, rel_types=None, max_depth=2) → subgraph
   - find_patterns() → list[Pattern***REMOVED*** (повторяющиеся структуры связей)
   - shortest_path(from_id, to_id) → list[KnowledgeLink***REMOVED***
2. 8 rel_types из RFC: REPLACES, EXTENDS, CONTRADICTS, SUPPORTS, RESOLVES, CAUSED, PRECEDES, RELATES_TO
3. Graph traversal: BFS с ограничением глубины (max_depth=2 default)
4. Pattern detection: поиск повторяющихся троек (A→B→C) с одинаковыми rel_types

Файлы: core_02/memory_store.py, tests_09/test_memory_store.py
```

### Задача 3.3 — Semantic Layer (reuse KnowledgeEngine)

**Промт:**
```
Интегрируй существующий KnowledgeEngine (scripts_01/knowledge_engine.py) как семантический слой Organizational Memory:

1. Создай core_02/semantic_layer.py
2. API:
   - index_knowledge(knowledge_id, content) → embedding_id
   - semantic_search(query, top_k=10) → list[(knowledge_id, score)***REMOVED***
   - find_similar_patterns(situation_vector) → list[PatternMatch***REMOVED***
3. Reuse KnowledgeEngine для эмбеддингов
4. Кэширование эмбеддингов в knowledge_objects.embedding_id

Файлы: core_02/semantic_layer.py, tests_09/test_semantic_layer.py
```

### Задача 3.4 — Learning Loop (AFC: Analyze → Formalize → Codify)

**Промт:**
```
Реализуй Learning Loop согласно RFC §8:

1. Создай core_02/learning_loop.py
2. AFC цикл:
   - analyze(trigger_context) → Analysis
     - Какие уроки релевантны? (semantic search по ситуации)
     - Это новый паттерн или повторение известного?
   - formalize(analysis) → KnowledgeObject
     - Создать/обновить knowledge_object с типом lesson/pattern/anti_pattern
     - Связать с существующими через Knowledge Graph
   - codify(knowledge_object) → Action
     - Записать в LESSONS.md (CON-N)
     - Обновить ARCHITECTURAL_DEBT.md если нужно
     - Отправить уведомление в TG
3. Триггеры: код-ревью нашло проблему, тест упал, пользователь явно попросил «запомни»

Файлы: core_02/learning_loop.py, tests_09/test_learning_loop.py
```

---

## 🟣 Этап 4: Buffy Forge v1 — метасистема (4-6 часов)

### Задача 4.1 — Workspace/Project контейнеры (L-1, L-2)

**Промт:**
```
Реализуй организационные контейнеры согласно RFC_BUFFY_FORGE_V1.md §2a:

1. Создай core_02/workspace.py (L-1 Workspace)
   - WorkspaceConfig: name, root_path, projects[***REMOVED***, default_environment
   - load_workspace(path) → Workspace
   - list_projects() → list[ProjectRef***REMOVED***
   - validate() → WorkspaceHealth (все проекты проходят Env Doctor?)

2. Создай core_02/project.py (L-2 Project)
   - ProjectConfig: name, type, stack, roles[***REMOVED***, contracts[***REMOVED***
   - load_project(path) → Project
   - get_requirements() → ProjectRequirements (из PROJECT_REQUIREMENTS.md)
   - run_env_doctor() → EnvDiagnosis (вызывает environment_doctor.diagnose())
   - get_agents_md() → AGENTS.md content

Файлы: core_02/workspace.py, core_02/project.py, tests_09/test_workspace.py, tests_09/test_project.py
```

### Задача 4.2 — Forge Pipeline (L-3)

**Промт:**
```
Реализуй Forge Pipeline согласно RFC §3:

1. Создай core_02/forge_pipeline.py
2. Стадии пайплайна на проект:
   - FORGE → CHECK → BUILD → TEST → DEPLOY → REPORT
3. FORGE: генерация/обновление артефактов проекта (AGENTS.md, RUNNABLE.md, CHECKLIST.md)
4. CHECK: Env Doctor + линтеры
5. BUILD: сборка (esbuild для web, etc.)
6. TEST: прогон тестов
7. DEPLOY: копирование в dist/ или web-сервер
8. REPORT: TG-уведомление о результате
9. Каждая стадия — отдельный метод, можно запускать индивидуально

Файлы: core_02/forge_pipeline.py, tests_09/test_forge_pipeline.py
```

### Задача 4.3 — Forge Registry (L-4)

**Промт:**
```
Реализуй Forge Registry согласно RFC §4:

1. Создай core_02/forge_registry.py
2. Реестр всех проектов и их состояний:
   - register_project(project_config) → project_id
   - get_project_status(project_id) → ForgeStatus
   - list_projects_by_status(status_filter)
   - get_pipeline_history(project_id) → list[PipelineRun***REMOVED***
3. Хранение: YAML-файл в data_13/forge_registry.yaml
4. Статусы: UNFORGED, CHECKING, BUILDING, TESTING, DEPLOYED, FAILED
5. История запусков пайплайна с timestamp + результатами

Файлы: core_02/forge_registry.py, tests_09/test_forge_registry.py
```

### Задача 4.4 — Forge CLI (L-5)

**Промт:**
```
Реализуй CLI для Buffy Forge:

1. Создай scripts_01/forge.py
2. Команды:
   - forge forge <project_path> — полный цикл FORGE→REPORT
   - forge check <project_path> — только Env Doctor
   - forge status — список всех проектов со статусами
   - forge register <project_path> — зарегистрировать новый проект
   - forge report <project_path> — TG-отчёт
3. Интеграция с существующим Environment Doctor, SmartRouter, telegram_contract
4. --dry-run флаг для preview без side-effects

Файл: scripts_01/forge.py
```

---

## ✅ Этап 5: Полный прогон тестов + CI-гейты (30 мин)

### Задача 5.1 — Все тесты tests_09/

**Промт:**
```
Прогони все тесты в tests_09/ батчами по 10-15 файлов:

Batch 1: test_environment_doctor.py test_blueprint_v3.py test_wizard.py test_scenario_registry.py test_prompt_dispatcher.py test_prompt_queue.py test_workspace_registry.py test_scenario_engine.py test_roles.py test_wizard_lib.py

Batch 2: test_memory_engine.py test_engineering_memory.py test_knowledge_engine.py test_semantic_index.py test_graph_index.py test_rag_engine.py test_seed_knowledge.py

Batch 3: test_bootstrap.py test_bootstrap_engine.py test_consistency_check.py test_drift_check.py test_verifier.py test_context_manager.py test_context_builder.py

Batch 4: test_telegram_contract.py test_tg_client_v2.py test_tg_roundtrip_verify.py test_telegram_bot.py test_telegram_bot_notify.py test_tgbot.py test_tgbot_base.py test_tgbot_escalate.py

Batch 5: test_remote_sync.py test_remote_sync_integration.py test_remote_sync_listener.py test_remote_sync_status.py test_e2e_remote_sync.py

Batch 6: test_event_bus.py test_event_store.py test_event_subscribers.py test_mcp_event_tools.py test_mcp_event_tools_core.py test_mcp_fastapi.py test_mcp_server.py test_plugin_api.py test_plugin_contract.py

Batch 7: остальные (test_agent_context_bridge.py, test_auto_conspect.py, test_bridge_layer.py, test_collaboration.py, test_cron_conspect.py, test_freebuff.py, test_lightpanda_worker.py, test_metrics.py, test_model_gateway.py, test_multi_turn_dispatcher.py, test_notification.py, test_orchestrator.py, test_phone_control_mcp.py, test_policy_conversational.py, test_policy_engine.py, test_presence.py, test_project_pulse.py, test_prompts_naming.py, test_runtime_abstraction.py, test_session_utils.py, test_stream_bridge.py, test_stream_session.py, test_task_manager.py, test_tool_runtime.py, test_work_area_view.py, test_wrapper_phase.py)

Для каждого батча: python3 -m pytest <files> -v. Если батч падает — отдельно прогони упавшие файлы с -x для первой ошибки.
```

### Задача 5.2 — Сводный отчёт

**Промт:**
```
Создай docs_10/audits/TEST_REPORT_2026-08-06.md:

- Общее количество тестов: N
- Passed: N
- Failed: N
- Skipped: N
- Список упавших с причинами
- Время выполнения по батчам
- Рекомендации по починке
```

---

## 🔴 Этап 6: Архитектурный аудит + синхронизация (1 час)

### Задача 6.1 — ARCH_TRACK_SUMMARY обновление

**Промт:**
```
Обнови docs_10/ARCH_TRACK_SUMMARY_2026-08-05.md → 2026-08-06:

Добавь ветки дня:
- v5.99.0: Environment Doctor роль (CON-41/42/43, PB-15)
- v5.100.0: Юнит-тесты Environment Doctor (CON-45, 21 тест)
- v5.101.0: Interior Planner — Picsum Photos + mobile-first fix (CON-46, CON-47)
- ARB-REV-002: план операций PLAN_NEXT_OPERATIONS.md

Обнови итоги:
- Тестов: 21 (env doctor) + существующие
- CON: 45, 46, 47
- Проектов в аудите: 6
```

### Задача 6.2 — DRIFT_CHECK финальный

**Промт:**
```
Прогони scripts_01/drift_check.py и scripts_01/consistency_check.py.

Исправь все найденные расхождения между:
- DOCUMENT_REGISTRY.md и реальной файловой системой
- CHANGELOG.md и TASK.md/BUFFY_PROJECT.md версиями
- LESSONS.md CON-номерами и CHANGELOG references
```

### Задача 6.3 — Регистрация плана

**Промт:**
```
Зарегистрируй PLAN_NEXT_OPERATIONS.md:

1. INDEX.md: добавь строку в раздел «Планы и дорожные карты»
2. DOCUMENT_REGISTRY.md: 79 → 80 документов
3. CHANGELOG.md: v5.101.0 — включи PLAN-NEXT-001
4. TASK.md / BUFFY_PROJECT.md: версия v5.101.0
```

---

## 📋 Сводная таблица приоритетов

| Этап | Приоритет | Время | Блокирует |
|------|-----------|-------|-----------|
| 0: Долги | 🔴 CRITICAL | 30 мин | — |
| 1: Исследование | 🔴 CRITICAL | 1-2 ч | Этап 4 (Forge требует знания проектов) |
| 2: Interior v5 | 🟡 HIGH | 2-3 ч | — |
| 3: Memory Engine | 🟡 HIGH | 3-4 ч | Этап 4 (Forge использует Memory) |
| 4: Forge v1 | 🟢 MEDIUM | 4-6 ч | — |
| 5: Тесты | 🟡 HIGH | 30 мин | — |
| 6: Аудит | 🟢 MEDIUM | 1 ч | — |

---

## 🔗 Связанные артефакты

- `core_02/LESSONS.md` — CON-45, CON-46, CON-47
- `core_02/environment_doctor.py` — диагностика окружения
- `docs_10/engineering-memory/RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md` — спецификация Memory Engine
- `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` — спецификация Forge
- `docs_10/core/PROJECT_REQUIREMENTS.md` — стандарт готовности проектов
- `projects_17/interior_planner/` — боевая задача
- `CHANGELOG.md` — v5.99.0, v5.100.0, v5.101.0
