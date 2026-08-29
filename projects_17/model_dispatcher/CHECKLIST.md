# CHECKLIST.md — контрольный список Model Dispatcher

## Каркас проекта (PROJECT_RULES §2)

- [x***REMOVED*** `MANIFEST.md` — паспорт
- [x***REMOVED*** `LESSONS.md` — журнал уроков
- [x***REMOVED*** `decisions/DECISIONS.md` + ADR-001/002/003
- [x***REMOVED*** `ROADMAP.md` — этапы и прогресс
- [x***REMOVED*** `README.md` — быстрый старт
- [x***REMOVED*** `RUNNABLE.md` + `CHECKLIST.md` — готовность
- [x***REMOVED*** `STEPS.md` — журнал шагов

## Функциональность

- [x***REMOVED*** config.yaml: таймер 1ч по умолчанию, приоритет моделей, пути очереди
- [x***REMOVED*** md_models: детект моделей на экране + выбор по убыванию (7 тестов)
- [x***REMOVED*** md_queue: очередь user→running→done/failed, формат совместим с pompts_11 (6 тестов)
- [x***REMOVED*** md_freebuff: tmux-драйвер, выбор модели, промпт, таймер, рестарты (8 тестов)
- [x***REMOVED*** dispatcher CLI: --check / --models / --dry-run / --once / --all / --screen (6 тестов)

## Безопасность/изоляция

- [x***REMOVED*** Изоляция: работа только внутри рабочей папки
- [x***REMOVED*** Нет правки core_02/scripts_01/freebuff_plugin_03 (Additive)
- [x***REMOVED*** Нет shell=True / exec (subprocess-списки)
- [x***REMOVED*** Инъекция tmux-команд в драйвер (тестируемость)

## Боевой прогон

- [ ***REMOVED*** --check → окружение OK
- [ ***REMOVED*** --dry-run → показывает очередь
- [ ***REMOVED*** --once на реальном freebuff (свободный инстанс) → done/
