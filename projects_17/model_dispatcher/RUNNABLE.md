# RUNNABLE.md — готовность проекта к запуску

> По `docs_10/core/PROJECT_REQUIREMENTS.md`. Статусы: ⬜ / ✅.

## Окружение

- [x***REMOVED*** Python 3.10+ (`python3 --version`)
- [x***REMOVED*** tmux доступен (`tmux -V`)
- [x***REMOVED*** freebuff установлен (`freebuff --version` → 0.0.128)
- [x***REMOVED*** Рабочая папка: `/storage/emulated/0/PROJECTS/workstation/freebuff/`
- [x***REMOVED*** Очередь `pompts_11/{user,running,done,failed***REMOVED***` существует
- [x***REMOVED*** config.yaml читается (`python -m projects_17.model_dispatcher.dispatcher --check`)

## Зависимости

- [x***REMOVED*** Только stdlib (yaml — опционально, дефолты работают без него)

## Тесты

- [x***REMOVED*** `python -m pytest projects_17/model_dispatcher/tests/ -q` → зелёные
  (тесты инъекционные: без реального tmux/freebuff)

## Боевой запуск (этап 8 ROADMAP — требует свободного инстанса)

- [ ***REMOVED*** Инстанс freebuff свободен (живая сессия занята — мы в ней)
- [ ***REMOVED*** Промт в `pompts_11/user/`
- [ ***REMOVED*** `python -m projects_17.model_dispatcher.dispatcher --once` → done/
- [ ***REMOVED*** Модель выбрана по приоритету (лог/отчёт в файле)
