# AGENTS.md — канонические правила платформы Workspace OS

> **Статус:** CANONICAL · единый источник истины для агентских сессий.
> **Роль:** читается ОДИН раз при старте любой сессии — принципы, которые нельзя нарушать.
> **Объём:** короткий по дизайну (промт 70 Задача 1): ссылки на канонические документы + explicit «нельзя нарушать» список. Не пересказ источников.

---

## 0. Что это за файл

- AGENTS.md — **единственный кросс-инструментальный стандарт** платформы (Agentic AI Foundation; стюардится не отдельным инструментом).
- `CLAUDE.md` — содержит `@AGENTS.md` import вверху (НЕ симлинк — лимит Claude Code ~40k символов).
- `BUFFY.md` — расширенный манифест среды (идентичность, инструменты, видение); этот файл — правила.
- ⚠️ **Session-overlay:** плагин Freebuff на время сессии оборачивает этот файл заголовком `# Freebuff Plugin Session` + задачей, а **после сессии восстанавливает канон** (`.freebuff_original_agents`). Каноническое содержимое ниже — всегда актуально.

---

## 1. Архитектурные принципы (RFC_BUFFY_FORGE_V1.md §2)

| Принцип | Суть |
|---------|------|
| **Additive Architecture** | Каждый новый компонент добавляется БЕЗ переписывания существующих |
| **Low Coupling** | Компоненты связаны через события/контракты, НЕ прямые вызовы |
| **Contract First** | Интерфейсы — явные контракты (события, API) |
| **Single Source of Truth** | Каждый артефакт (RFC, ADR, Lesson) имеет ровно одно каноническое место |
| **Observability** | Каждый переход между компонентами логируется в event_log |
| **Backward Compatibility** | Новые компоненты не ломают существующие цепочки |
| **High Cohesion** | Внутри одного компонента — максимальная связность |

## 2. Что НЕ делает Forge (RFC_BUFFY_FORGE_V1.md §12)

Forge — метасистема проектирования. Он **не является**:
- ❌ **Runtime-платформой** — Forge не исполняет пользовательские запросы
- ❌ **CI/CD** — Forge не деплоит код
- ❌ **Мониторингом / балансировщиком / заменой разработчику**

Forge отвечает на вопрос «как Buffy проектирует себя», а не «как работает в production».

## 3. Определение Workspace OS (RESEARCH_V1 §31.5 — Final Definition, canonical)

> **Workspace OS** — локально-развёрнутая (local-first) операционная среда для долгоживущих проектов, координирующая работу одного или нескольких AI-агентов и людей через процессы (forge) + память (memory) + обратную связь (feedback) + оркестрацию (multi-agent).

Distinct positioning (4 оси): **project-centric · local-first · multi-mode (Human × Agent × Team) · stateful**.
Workspace OS — **НЕ** SaaS AI-agent platform, НЕ LLM orchestrator, НЕ workflow engine, НЕ agentic IDE, НЕ PKM-tool.

## 4. Границы, которые НЕЛЬЗЯ нарушать (RESEARCH_V1 §32 + §7.3)

14 архитектурных границ (B1–B14). Критичные для v0.1: **B1 (Workspace↔Project), B2 (Project↔Forge), B7 (Factory↔Forge), B9 (Capability↔Skill), B10 (State↔Mode)**. Полный список — §32.2/§32.3.

### 🚫 B-правила (5 decision rules, §32.4)
1. **B-Rule 1:** если два компонента разделяют state machine → это НЕ отдельные границы (напр. Forge + Scenario разделяют UNFORGED).
2. **B-Rule 2:** если один компонент терпим к отсутствию другого → граница.
3. **B-Rule 3:** разный lifecycle (long-lived vs ephemeral) → граница.
4. **B-Rule 4:** разный owner-file → граница.
5. **B-Rule 5:** разный namespace → граница.

### 🚫 Wizard↔Forge orthogonal-STATE (§7.3, Hypothesis C — ВЕРИФИЦИРОВАНА)
- Scenario и Forge Pipeline — **ортогональные state-домены**, не последовательность.
- **UNFORGED ≠ «проект не работал»** = «не прошёл forge CI-pipeline» (только Forge-слой).
- **Direct Forge call из Scenario — НЕТ (по дизайну).** Scenario НЕ вызывает Forge напрямую — только через Project/Facade.
- Проверено: 2 реальных инстанса (vkusvill_demo, interior_planner) работают при статусе UNFORGED.

## 5. Неприкосновенность промтов

- **Промты в `pompts_11/` нельзя удалять.** Запрещено удалять, перезаписывать или терять существующий промт при переименовании, реорганизации, очистке или массовой обработке.
- Изменения промта выполняются только аддитивно и с сохранением предыдущего содержимого. При необходимости новой редакции создаётся новый файл или версия, а старый остаётся в `pompts_11/`.
- Переименование допускается только после проверки, что содержимое сохранено, ссылки обновлены, а исходное имя и история доступны через Git. Удаление допускается только по явному отдельному указанию пользователя.
- Если промт обнаружен как отсутствующий, сначала искать его в истории, дампах и резервных копиях; не считать его утраченным без проверки.

## 6. ANTI-паттерны — правила на будущее (core_02/LESSONS.md)

- **ANTI-5 (scope discipline):** один сценарий за раз. Не замахиваться на wizard + contracts + AGENTS.md + build разом — непроверяемые модули накапливаются, ревью-петля раздувается.
- **ANTI-6b (vocabulary drift):** **CLOSE VOCABULARY contract** — каждый токен в `CAPABILITIES_OVERRIDE` ДОЛЖЕН быть в `KNOWN_CAPABILITIES` (closed set, mirrors `ModelCatalog.capabilities`). Иначе silent fallback на слабую модель (qwen2.5:1.5b / gemini-fallback) при «зелёных» тестах. Валидатор поднимает `ValueError` при drift — это фича, не баг.
- **REGISTER-FIRST (поправка 2026-08-11):** любой **обнаруженный недостающий элемент** (capability / tool / engine / forge / role / модуль) — НЕ «несуществующий токен», а способность, которую нужно **построить**. Порядок: **(1) зафиксировать в `core_02/missing_registry.py` (MissingRegistry, YAML `data_13/missing_registry.yaml`) + §20 карты v1.1** → (2) промт на реализацию (pompts_11/promtNN.md, `mark_prompt_written`) → (3) реализация (`mark_implemented` + пополнение `KNOWN_CAPABILITIES`/Tool Registry). Запрещено: молча игнорировать недостающее, использовать незарегистрированный токен, или реализовывать «на лету» без записи в реестре. Реестр — источник истины по недостающим элементам (B10-валидация `validate_schema`, lifecycle registered → design_ready → prompt_written → implemented, не откатывается).

  **CLI (`python -m core_02.missing_registry [--path data_13/missing_registry.yaml***REMOVED***`):**

  ```bash
  python -m core_02.missing_registry seed                                  # 7 записей §20, идемпотентно
  python -m core_02.missing_registry register my_tool --kind tool [--factory code***REMOVED*** [--description …***REMOVED***
  python -m core_02.missing_registry mark-prompt-written my_tool --prompt pompts_11/promtNN.md
  python -m core_02.missing_registry mark-implemented my_tool --implementation scripts_01/x.py
  python -m core_02.missing_registry list [--status registered|design_ready|prompt_written|implemented***REMOVED*** [--factory F***REMOVED*** [--json***REMOVED***
  python -m core_02.missing_registry check                                 # B10/R-127 → exit 0 = валиден
  ```

  Полный операционный manual: **`docs_10/runbook/MISSING_REGISTRY_RUNBOOK.md`**.

## 7. Быстрый протокол сессии

1. Прочитать этот файл (правила) → `BUFFY.md` (идентичность) → `TASK.md` (активные задачи) → `CHANGELOG.md` (последние релизы).
2. Перед изменениями кода — перечитать `docs_10/core/CODE_QUALITY_STANDARD.md` (обязательный регламент).
3. После изменений: `python -m pytest tests_09/ -q` + `python -m mypy scripts_01/ core_02/ --ignore-missing-imports`.
4. Изменения — **аддитивные** (Additive Architecture); никакой перезаписи существующих модулей без явной причины.
5. Ведение проектов — по `docs_10/core/PROJECT_RULES.md` (канон): **проект = контейнер контекста** (MANIFEST-паспорт, LESSONS, decisions/ADR, ROADMAP, STEPS «почему», RUNNABLE/CHECKLIST); задача идёт через проект; тиражируемое — дополнительно в общую базу; работа по платформе = проект «сама платформа» (корень freebuff/).

## 8. Cross-links (канонические источники)

- `docs_10/engineering-memory/RFC_BUFFY_FORGE_V1.md` — принципы §2, «что НЕ делает Forge» §12
- `docs_10/engineering-memory/WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md` — §31.5 (Definition), §32 (14 границ + B-Rules), §7.3 (Wizard↔Forge)
- `core_02/LESSONS.md` — ANTI-5, ANTI-6b, CON-8 (vocabulary defense)
- `docs_10/core/CORE_PROMPT.md` — личность, обязанности, ограничения (расширяет этот файл)
- `docs_10/canonical/architecture.md` — иерархия сущностей, JSON-контракты, AGENTS.md генерация
