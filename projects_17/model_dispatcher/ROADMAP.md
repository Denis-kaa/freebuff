# ROADMAP.md — Model Dispatcher (081_19_model_dispatcher)

> Шаблон: PIPELINE_TEMPLATE (этапы + acceptance). Статусы: ⬜ plan · 🔄 wip · ✅ done.

| Этап | Задача | Статус | Acceptance |
|------|--------|--------|-----------|
| 1 | Исследование платформы + аудит (структура, каноны, существующие скрипты) | ✅ done | Аудит: 90% функционала уже есть в prompt_dispatcher/model_gateway/wrapper; GLM/MiniMax HTTP-провайдеров нет — решено использовать выбор на стартовом экране freebuff |
| 2 | Инициация проекта (каркас по PROJECT_RULES) | ✅ done | MANIFEST/LESSONS/decisions/ROADMAP/README/RUNNABLE/CHECKLIST/STEPS созданы |
| 3 | config.yaml (таймер 1ч, приоритет моделей, пути очереди) | ✅ done | Конфиг читается, дефолты работают |
| 4 | md_models — детект моделей на экране + выбор по убыванию | ✅ done | 7 unit-тестов (детект, недоступность, fallback) |
| 5 | md_queue — файловая очередь pompts_11/user→running→done/failed | ✅ done | 6 unit-тестов (создание, перемещение, отчёты) |
| 6 | md_freebuff — tmux-драйвер (запуск, выбор, промпт, таймер, рестарт) | ✅ done | 8 unit-тестов с инъекцией tmux |
| 7 | dispatcher CLI (--check/--models/--dry-run/--once/--all/--screen) | ✅ done | 6 unit-тестов CLI |
| 8 | Боевой прогон на реальном freebuff (когда инстанс свободен) | ⬜ plan | Промт из user/ → done/; модель выбрана по приоритету; таймер работает |
| 9 | Расширение: продолжение сессий через --continue (задача из running/) | ⬜ plan | Отложенная сессия возобновляется после таймера |

## Следующий шаг

Этап 8 — боевой прогон: положить промт в `pompts_11/user/`, выполнить
`python -m projects_17.model_dispatcher.dispatcher --once` при свободном
инстансе freebuff (сейчас живая сессия — мы в ней).
