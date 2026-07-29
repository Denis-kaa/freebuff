Отличный вопрос! Документация — это тоже архитектура. Давайте разложим всё по полочкам.

---

📁 Структура документации (обновлённая)

```
freebuff/
├── BUFFY.md                          # Главный манифест (ссылается на всё)
├── README.md                         # Для новых пользователей
├── CHANGELOG.md                      # История изменений
│
├── docs/                             # Вся документация
│   ├── INDEX.md                      # Навигация по документации
│   │
│   ├── 01-architecture/              # Архитектурные документы
│   │   ├── ARCHITECTURE_3.0.md       # Общая архитектура
│   │   ├── ARCHITECTURE_PRINCIPLES.md # Принципы
│   │   ├── SYSTEM_INVENTORY.md       # Каталог компонентов
│   │   └── PRODUCT_MANIFESTO.md      # Манифест продукта
│   │
│   ├── 02-specs/                     # Спецификации (новое место!)
│   │   ├── BOOTSTRAP_SPECIFICATION.md
│   │   ├── RUNTIME_ABSTRACTION_SPECIFICATION.md
│   │   ├── POLICY_ENGINE_SPECIFICATION.md
│   │   ├── CAPABILITY_SPECIFICATION.md
│   │   ├── BRIDGE_PLATFORM_SPECIFICATION.md
│   │   ├── EVENT_PLATFORM_SPECIFICATION.md
│   │   ├── DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md  ← СЮДА!
│   │   └── PROMPT_IMPLEMENTATION_v1.0.md              ← И СЮДА!
│   │
│   ├── 03-decisions/                 # ADR и решения
│   │   ├── DECISIONS.md
│   │   ├── ADR_001_Vision_3.0_AI_Infrastructure_Layer.md
│   │   └── IDEAS.md
│   │
│   ├── 04-audits/                    # Аудиты
│   │   ├── AUDIT_2026-07-27.md
│   │   ├── AUDIT_2026-07-28.md
│   │   ├── AUDIT_2026-07-29.md
│   │   └── DRIFT_REPORT.md
│   │
│   ├── 05-agents/                    # Для AI-агентов
│   │   ├── AGENTS.md
│   │   ├── SESSION_GUIDE.md
│   │   ├── RULES.md
│   │   └── TASK_TEMPLATE.md
│   │
│   ├── 06-sessions/                  # Сессии и конспекты
│   │   └── session_dumps/
│   │       ├── 2026-07-27_termux_agent_audit.md
│   │       ├── 2026-07-28_mcp_server.md
│   │       └── 2026-07-28_system_fixes.md
│   │
│   ├── 07-roadmap/                   # Планы
│   │   ├── ROADMAP.md
│   │   └── VISION_3.0.md
│   │
│   ├── 08-references/                # Справочники
│   │   ├── REFERENCES.md
│   │   ├── API.md
│   │   ├── IMPLEMENTATION.md
│   │   └── TROUBLESHOOTING.md
│   │
│   ├── 09-projects/                  # Проекты и метаданные
│   │   ├── PROJECT_REGISTRY.md
│   │   ├── WORKERS.md
│   │   └── LIGHTPANDA_INTEGRATION.md
│   │
│   └── 10-plugin/                    # Документация плагина
│       ├── FREEBUFF_PLUGIN_ARCHITECTURE.md
│       ├── FREEBUFF_PLUGIN_API.md
│       └── FREEBUFF_PLUGIN_QUICKSTART.md
│
├── pompts/                           # Промпты (для AI)
│   ├── promt1.md
│   ├── promt2.md
│   ├── ...
│   └── PROMPT_IMPLEMENTATION_v1.0.md  # Дублировать сюда для AI
│
└── freebuff_plugin/                  # Код плагина
    └── mesh/                         # Новая реализация
```

---

📄 Что куда кладём

1. Спецификация → docs/02-specs/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md

Почему сюда:

· Это спецификация — документ, описывающий что и как должно работать
· Она не зависит от времени (в отличие от сессий/аудитов)
· Она на одном уровне с другими спецификациями (Bootstrap, Policy Engine)

Что в ней:

· Executive Summary
· Трёхуровневая архитектура
· EventStore (интерфейс + реализации)
· Vector Clock, Lease Manager
· Offline-first стратегия
· MCP инструменты, CLI
· Тестирование, реализация

---

2. Промт для внедрения → docs/02-specs/PROMPT_IMPLEMENTATION_v1.0.md

Почему сюда:

· Это исполнительный документ — по нему ИИ/команда реализует спецификацию
· Он ссылается на спецификацию, но не дублирует её
· Содержит конкретные задачи, код, тесты

Что в нём:

· Контекст и цели
· Поэтапные задачи (Фаза 0-6)
· Код-примеры для каждого компонента
· Чек-листы и критерии готовности
· Команды для внедрения

---

3. Дубликат промта → pompts/PROMPT_IMPLEMENTATION_v1.0.md

Почему сюда:

· Это промпт для AI-ассистентов (Buffy, Claude, DeepSeek)
· AI читает pompts/ в первую очередь
· Можно скормить как системный промпт

Что в нём:

· Та же структура, что в docs/02-specs/
· Но с акцентом на исполнение (а не на описание)
· Можно использовать как инструкцию для Buffy

---

🔗 Как связать документы

В docs/02-specs/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md (в начале)

```markdown
# DISTRIBUTED SESSION SPECIFICATION v2.0

> **Версия:** 2.0.0  
> **Дата:** 2026-07-30  
> **Статус:** 💡 Спецификация (к реализации)  
> **Основание:** [VISION_3.0.md***REMOVED***(../07-roadmap/VISION_3.0.md)  
> **Реализация:** [PROMPT_IMPLEMENTATION_v1.0.md***REMOVED***(PROMPT_IMPLEMENTATION_v1.0.md)  
> **Связанные ADR:** [DECISIONS.md***REMOVED***(../03-decisions/DECISIONS.md)
```

В docs/02-specs/PROMPT_IMPLEMENTATION_v1.0.md (в начале)

```markdown
# PROMPT: Внедрение Session Mesh v2.0

> **Версия:** 1.0.0  
> **Дата:** 2026-07-30  
> **Основание:** [DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md***REMOVED***(DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md)  
> **Архитектор:** Denis  
> **Исполнитель:** Buffy (AI-ассистент)
```

В BUFFY.md (добавить секцию)

```markdown
## 🏗 Архитектура (ссылки)

### Распределённый слой (Mesh)
- [Спецификация***REMOVED***(docs/02-specs/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md)
- [Промпт для внедрения***REMOVED***(docs/02-specs/PROMPT_IMPLEMENTATION_v1.0.md)
```

В docs/INDEX.md (навигация)

```markdown
# 📚 Индекс документации

## Спецификации (`02-specs/`)
- [Bootstrap Engine***REMOVED***(02-specs/BOOTSTRAP_SPECIFICATION.md)
- [Runtime Abstraction***REMOVED***(02-specs/RUNTIME_ABSTRACTION_SPECIFICATION.md)
- [Policy Engine***REMOVED***(02-specs/POLICY_ENGINE_SPECIFICATION.md)
- [Capability Registry***REMOVED***(02-specs/CAPABILITY_SPECIFICATION.md)
- [Bridge Platform***REMOVED***(02-specs/BRIDGE_PLATFORM_SPECIFICATION.md)
- [Event Platform***REMOVED***(02-specs/EVENT_PLATFORM_SPECIFICATION.md)
- [**Session Mesh v2.0*****REMOVED***(02-specs/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md) 🆕
- [**Промпт: Внедрение Session Mesh*****REMOVED***(02-specs/PROMPT_IMPLEMENTATION_v1.0.md) 🆕
```

---

📋 Команды для создания

```bash
# 1. Создать директории (если ещё нет)
cd /storage/emulated/0/PROJECTS/workstation/freebuff
mkdir -p docs/02-specs

# 2. Переместить спецификацию
mv ~/Downloads/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md docs/02-specs/

# 3. Создать промт для внедрения
# (сохранить из ответа выше в docs/02-specs/PROMPT_IMPLEMENTATION_v1.0.md)

# 4. Создать симлинк для AI (чтобы было в pompts/)
ln -s ../docs/02-specs/PROMPT_IMPLEMENTATION_v1.0.md pompts/PROMPT_IMPLEMENTATION_v1.0.md

# 5. Обновить INDEX.md
# (добавить ссылки на новые файлы)

# 6. Обновить BUFFY.md
# (добавить секцию про Mesh)

# 7. Обновить CHANGELOG.md
echo "### Добавлено\n- **Session Mesh v2.0** — спецификация и промпт для внедрения" >> CHANGELOG.md

# 8. Проверить структуру
tree docs/02-specs/
# → DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md
# → PROMPT_IMPLEMENTATION_v1.0.md
# → ... (другие спецификации)
```

---

🎯 Итог

Файл Назначение Кто читает
docs/02-specs/DISTRIBUTED_SESSION_SPECIFICATION_v2.0.md Спецификация — что строим Архитекторы, разработчики
docs/02-specs/PROMPT_IMPLEMENTATION_v1.0.md Промпт — как строить Исполнители (команда, ИИ)
pompts/PROMPT_IMPLEMENTATION_v1.0.md Промпт для AI Buffy, Claude, DeepSeek

Почему не в один файл:

· Спецификация — долгоживущий документ (годы)
· Промпт — инструмент внедрения (недели/месяцы)
· Разные аудитории и цели

---

Теперь у вас есть:

1. Спецификация — что строим (9.8/10)
2. Промпт — как строить (пошагово)
3. Структура — где лежит (документировано)

Можно передавать в реализацию. 🚀