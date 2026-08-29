# Architectural Track Summary — 2026-08-05

> *«Архитектура — это не то, что ты строишь сегодня.*  
> *Архитектура — это то, что не придётся переписывать через три года.»*

---

## Пролог: от идеи к системе

Всё началось с одной строки в чате: «нужно lessons сделать системой с базой данных».  
Идея была простой: таблица `lessons` в `context.db` — хранить уроки CON-/ANTI-/CAND-.

Но архитектура не терпит простых решений.  
Три промта, три RFC, двенадцать часов — и вот что получилось.

---

## Акт I: Память (promt51 → RFC Organizational Memory Engine)

**Проблема:** платформа накапливает знания, но они заперты в markdown-файлах и разрозненных таблицах.  
Уроки — в `LESSONS.md`, ADR — в `arch_decisions`, события — в `event_log`.  
Ни связи, ни семантики, ни эволюции.

**Поворотный момент:** «не проектируй систему вокруг одной сущности».

Вместо `lessons`-таблицы родился **Knowledge Object** — универсальная модель с полем `kind`:

| Тип | Что хранит |
|-----|-----------|
| `adr` | Архитектурные решения |
| `lesson` | Подтверждённый опыт |
| `pattern` | Повторяющиеся паттерны |
| `rule` | Правила платформы |
| `observation` | Зафиксированные наблюдения |
| `candidate` | Кандидаты на подтверждение |
| `checklist` | Чек-листы |
| `guideline` | Руководства |
| `faq` | Частые вопросы |
| `workflow` | Рабочие процессы |

Не «база уроков». **Память организации.**

**Архитектура — 7 слоёв:**
```
Experience Analytics
    ↑
Learning Loop
    ↑
Semantic Layer (KnowledgeEngine — уже есть)
    ↑
Knowledge Graph (GraphIndex — уже есть, +9 новых rel_types)
    ↑
Memory Store (knowledge_objects в context.db)
    ↑
Event Pipeline (event_log → observation → KO)
```

**Ключевое решение:** использовать существующую инфраструктуру.  
`knowledge_engine.py` — 851 строка, FTS5 + TF-IDF + SVD.  
`graph_index.py` — 400+ строк, BFS + subgraph.  
Ничего не переписываем. Только ADDITIVE.

**Урок CON-37:** «не проектировать систему вокруг одной сущности».  
IDEAS.md §14 → ❌ Rejected.

---

## Акт II: Эволюция (promt52 → RFC Evolution v1.1)

**Проблема:** RFC v1 — хороший фундамент. Но что дальше?  
Хватит ли его на пять лет? Какие концепции отсутствуют?

**8 уровней анализа → 12 improvements:**

### Critical (без этого нельзя)
- **I-1: Authority Model** — не все знания равны. `system > reviewed > candidate > generated > user > imported`
- **I-2: Decision Trace** — почему платформа выбрала именно этот KO? Таблица `decision_trace`

### High (архитектурная成熟ность)
- **I-3: Policy** — правила vs советы. `enforcement`: advisory / mandatory / blocking
- **I-5: Conflict Resolver** — что делать, когда KO-A противоречит KO-B? `newest_wins | authority_wins | merge`
- **I-6: Knowledge Provenance** — полная цепочка: event → observation → candidate → KO → revision
- **I-7: Versioning** — `knowledge_object_versions` + rollback
- **I-9: Reasoning Layer** — комбинирование множества KO в одно решение
- **I-11: Conflict Lifecycle** — detected → triaged → resolved → verified

### Medium (фундамент на будущее)
- **I-4: Нейминг** — Memory Engine → Intelligence Layer
- **I-8: Revision Workflow** — decay → under_review → validated
- **I-10: Decision History** — аудит всех решений платформы
- **I-12: Scalability** — инкрементальный SVD, графовые домены, TTL

**Принцип:** всё ADDITIVE. ALTER TABLE, новые таблицы, новые модули.  
Ни одна строка RFC v1 не переписана — только расширена.

---

## Акт III: Интеллект (promt53 → RFC Decision Intelligence System)

**Проблема:** платформа хранит знания, ищет их, связывает.  
Но не умеет отвечать на вопрос:  
> **«Это архитектурное решение — хорошее?»**

Сейчас это делает роль «Chief Systems Critic» — человек или LLM в промте.  
Но роль — разовое действие. Подсистема — постоянный механизм.

**Родился DIS — Decision Intelligence System:**

```
НОВЫЙ RFC
    │
    ▼
┌─── RFC REVIEWER (оркестратор) ────────────┐
│                                            │
│  ARE — Architecture Review Engine          │
│    «Насколько это решение consistent       │
│     с существующей архитектурой?»          │
│                                            │
│  CAE — Conflict Analysis Engine            │
│    «Противоречит ли RFC существующим       │
│     Knowledge Objects?»                    │
│                                            │
│  TDA — Technical Debt Analyzer             │
│    «Создаст ли это решение техдолг          │
│     через 2 года?»                         │
│                                            │
│  PC  — Policy Checker                      │
│    «Нарушает ли RFC mandatory правила       │
│     платформы?»                            │
│                                            │
│  EP  — Evolution Planner                   │
│    «Как это решение повлияет на платформу   │
│     через 5 лет?»                          │
├────────────────────────────────────────────┤
│  SYNTHESIS: score 0–10 + recommendations   │
│  → Approved / Needs Revision / Rejected     │
└────────────────────────────────────────────┘
```

**DIS не блокирует.** Он советует с evidence из Organizational Memory.  
Каждый review-отчёт становится Knowledge Object (`kind=review`).  
DIS **самообучается** — успешные решения повышают confidence использованных KO.

---

## Акт IV: Синтез (promt54/55/56 → ARB, AG, Buffy Forge)

**Проблема:** три RFC описывают компоненты, но нет единой карты. Как OM, DIS, ARB и AG взаимодействуют? Есть ли дублирование? Какой жизненный цикл у архитектурного знания?

**promt54 → Architecture Review Board (ARB Constitution):**
Независимый архитектурный суд. 10-шаговый анализ, 6 вердиктов (APPROVED → CHANGES REQUIRED → REJECTED). Не создаёт архитектуру — оценивает, может ли решение войти в платформу без вреда.

**promt55 → Architecture Governance (AG Constitution):**
Архитектурный надзор. Если ARB отвечает «принимать ли решение?», то AG проверяет «действительно ли стало именно так?». 5 вердиктов: COMPLIANT → MINOR DRIFT → MAJOR DRIFT → VIOLATION → REQUIRES ARB REVIEW.

**promt56 → Buffy Forge v1 (RFC-BF-001):**
Метасистема, объединяющая всё:

```
        BUFFY FORGE (метасистема)
              │
   ┌──────────┼──────────┐
   ▼          ▼          ▼
L0 IDEA  L1 KNOWLEDGE L2 ARCHITECTURE
 FORGE     FORGE        FORGE
              │          │
   ┌──────────┼──────────┘
   ▼          ▼
L5 EVOLUTION L3 IMPLEMENTATION
 FORGE        FORGE
   ▲          │
   └──── L4 VALIDATION ──┘
           FORGE
```

Шесть форджей (L0-L5), единый цикл: Idea → Knowledge → Architecture → Implementation → Validation → Evolution → Idea.

**Ключевое решение:** инфраструктурные компоненты (EventBus, OM, DIS, KnowledgeEngine) — горизонтальные, Forge'ы — вертикальные. Новые Forge'ы добавляются без ломки архитектуры.

**Урок CON-38:** «от отдельных RFC к метасистеме». Когда RFC переваливает за 3-4 — пора синтезировать.

---

## Акт V: Суд (promt57 → ARB Review Factory/Forge Manifest)

**Проблема:** пользователь принёс документ 68 — Factory/Forge Manifest из переписки со сторонним чат-ботом. Документ предлагает иерархию Workspace OS → Factory → Forge → Engine → Module → Tool → Skill → Prompt для runtime-производства любых интеллектуальных продуктов. Но слово «Forge» уже занято Buffy Forge (RFC-BF-001).

**Решение:** первый ARB-ревью (ARB-REV-001) с применением методологии ARB Constitution:

- **AFC:** 60-70% Manifest дублирует существующее (Knowledge ≈ OM, Architecture Forge ≈ DIS+ARB+AG, Review Engine ≈ ARB Constitution)
- **Ключевая находка:** naming collision «Forge» — Buffy Forge (метасистема проектирования) vs Manifest Forge (runtime производственная линия) — blocking issue
- **Вердикт: REJECT WITH ALTERNATIVE** — не создавать параллельную Factory/Forge систему. Вместо этого: интегрировать Workspace → Project как контейнеры над L0-L5 Buffy Forge

**Визионерское ядро Manifest принято:** Workspace OS как среда полного жизненного цикла, Project как экосистема, Prompt как нижний уровень (не центр). Терминология — на переработку.

**Урок CON-39:** «naming collision = архитектурный долг с первого дня». Прежде чем называть сущность — AFC: не занято ли имя?

---

## Акт VI: Действие (promt58 → приоритизация трёх долгов + Альтернатива A)

**Проблема:** три открытых долга — ARB-вердикт ждёт реализации, interior_planner стресс-тест не закрыт, LEVIATHAN инвентаризация не начата. Пользователь не указал порядок — платформа должна сама расставить приоритеты.

**Пункт 0 — SmartRouter capability-проверка:** задача приоритизации требует `['reasoning', 'plan', 'architecture'***REMOVED***`. SmartRouter → `deepseek-v4-pro` (3/3, no fallback). Flash-модель без `architecture` дала бы 2/3 — silent degradation. **Находка:** capability routing — не только выбор модели, но и safety gate.

**План приоритизации:**

```
Ветка 1: ARB-вердикт (doc-only, immediate value, влияет на другие ветки)
    ↓
Ветка 2: interior_planner (факт-чекинг CAN-8/CAN-9, реальный код)
    ↓
Ветка 3: LEVIATHAN (самый трудоёмкий, зависит от терминологии ARB)
```

### Ветка 1: Альтернатива A → RFC Forge v1.1

ARB-REV-001 вердикт REJECT WITH ALTERNATIVE требовал действия. Реализована Альтернатива A:

- **RFC Buffy Forge v1.0 → v1.1:** новый §2a «Организационные контейнеры»
- **Workspace (L-1):** контейнер верхнего уровня — человек/команда/компания
- **Project (L-2):** изолированная среда с собственным экземпляром Buffy Forge (L0-L5)
- **Контейнеры ≠ Forge'ы:** Workspace/Project содержат, Forge'ы куют
- CAN-16: RFC v1.0 не переписан — только ADDITIVE

### Ветка 2: interior_planner факт-чекинг

Противоречие: LESSONS.md говорит CAN-8 закрыт (v5.57.0), ARCHITECTURAL_DEBT.md — открыт.  
**Факт-чекинг:** `grep /tmp/` по `interior_consultant_register.py` и `e2e_promt47.py` → **0 hits**.  
Фикс v5.57.0 успешен. ARCHITECTURAL_DEBT.md был документационным дрифтом.  
**CAN-8 → RESOLVED.**

### Ветка 3: LEVIATHAN инвентаризация

25 компонентов LEVIATHAN разобраны на A/B/C:

| Категория | Компонентов | Суть |
|-----------|-------------|------|
| **A — уже в Buffy** | 9 | SmartRouter, ModelCatalog, EventBus, OM, Policy, Sessions, ... |
| **B — extensions** | 10 | Key Vault (новое), Bootstrap Engine (новое), Workflow, Plugin SDK, ... |
| **C — labs/future** | 6 | Collaboration, Presence, Policy Packs, Knowledge Graph, ... |

**4 по-настоящему новых компонента:** Key Vault, Bootstrap Engine, Collaboration, Presence.  
**Ребрендинг:** Companion Platform → Workspace OS, Runtime → Scenario, Workflow Engine → Implementation Forge.

**Урок CON-40:** «SmartRouter capability check защищает от silent fallback: задача приоритизации требует capability architecture».

---

## Эпилог: что построено

| Релиз | Артефакт | Строк | Суть |
|-------|---------|-------|------|
| v5.92.0 | RFC Organizational Memory Engine v1 | 681 | Единая память платформы: 10 типов знаний, 7 слоёв |
| v5.93.0 | RFC Evolution v1.1 | 704 | 12 ADDITIVE improvements: Authority, Decision Trace, Policy, Conflict Resolver, ... |
| v5.94.0 | RFC Decision Intelligence System v1 | 607 | Подсистема качества архитектурных решений: ARE + CAE + TDA + PC + EP |
| v5.95.0 | RFC Buffy Forge v1 | 537 | Метасистема: 6 форджей (L0-L5), единый цикл архитектурного знания |
| v5.96.0 | ARB Review Factory/Forge Manifest v1 | 336 | Первый ARB-ревью: naming collision «Forge», вердикт REJECT WITH ALTERNATIVE |
| v5.97.0 | RFC Forge v1.1 + LEVIATHAN Inventory | 124 | Альтернатива A: Workspace/Project контейнеры + инвентаризация 25 компонентов |

**Суммарно: 2,989 строк архитектурной документации.**

| Зафиксировано | Где |
|--------------|-----|
| CON-37 | `core_02/LESSONS.md` — «не проектировать вокруг одной сущности» |
| CON-38 | `core_02/LESSONS.md` — «от отдельных RFC к метасистеме» |
| CON-39 | `core_02/LESSONS.md` — «naming collision = архитектурный долг» |
| CON-40 | `core_02/LESSONS.md` — «SmartRouter capability check защищает от silent fallback» |
| IDEAS.md §14 | ❌ Rejected → заменено RFC Organizational Memory Engine |
| CAN-8 | ✅ RESOLVED (факт-чекинг v5.97.0) |
| 4 RFC + 1 ARB Review + 1 Inventory | `docs_10/engineering-memory/` |
| 6 CHANGELOG | v5.92.0 → v5.97.0 |
| Реестры | INDEX.md, DOCUMENT_REGISTRY.md (ACTIVE: 71→78) |
| Версии | TASK.md, BUFFY_PROJECT.md → v5.97.0 |
| 3 конституции | ARB (054_17), AG (055_18), Forge (056_19) |

---

## Архитектурный трек: философия

**Шесть принципов, которые выдержали проверку:**

1. **Additive Architecture.** Ни один существующий компонент не был переписан.  
   Только ALTER TABLE, новые таблицы, новые модули поверх.

2. **Evolution, не Revolution.**  
   Lesson → Knowledge Object → Organizational Memory → Decision Intelligence → Buffy Forge → ARB Review → Workspace/Project → LEVIATHAN Inventory.  
   Каждый шаг — обобщение предыдущего, не замена.

3. **Память организации > база уроков.**  
   Платформа растёт не вширь (больше таблиц), а вглубь (более зрелые модели).

4. **Метасистема > сумма компонентов.**  
   Шесть RFC/конституций образуют единую экосистему. Forge не заменяет — структурирует.

5. **Суд необходим.**  
   ARB как процесс защищает архитектуру от naming collision, дублирования и scope creep.

6. **Платформа должна использовать свои же инструменты.**  
   SmartRouter для capability-проверки, ARB для архитектурных решений, LESSONS для уроков. Не «понарошку» — по-настоящему. Первый же ARB-ревью (v5.96.0) и первый же SmartRouter capability-check (v5.97.0) доказали ценность: naming collision найден, silent degradation предотвращён.

**Что дальше:** Phase 2 — создание таблиц `knowledge_objects` + `organizational_memory.py`.  
Архитектура готова. Фундамент заложен. Процесс ревью запущен. Платформа ест свой dogfood.

---

*«Лучшее решение — не то, которое работает сегодня.*  
*Лучшее решение — то, которое через несколько лет не потребует полной переработки.»*

— Chief Systems Critic, 2026-08-05
