# ADR_012: Buffy-as-Swappable-Brain — Multi-Model Router + User-Replacement Protocol

**Status:** Accepted (Proposed 2026-08-04, encoded v5.74.0)
**Component:** Identity architecture (clarification layer atop §CORE_PROMPT v1.0.0)
**Deciders:** Buffy (autonomous, per CORE_PROMPT §3 обязанности), User (operator, semantic clarifier)
**Supersedes:** Identity-fragmented framing pre-v5.74.0 ("Buffy = assistant OF Freebuff"; "Freebuff = platform"; "Workspace OS = roadmap name") — replaced with **unified identity model**.
**Related:** [CORE_PROMPT §1***REMOVED***(../core/CORE_PROMPT.md), [BUFFY.md identity §***REMOVED***(../../BUFFY.md), [pompts_11/048_11_platform_rewrite_directive.md***REMOVED***(../../pompts_11/048_11_platform_rewrite_directive.md), ADR-001 (Позиционирование: aggregator, not competitor), ADR-010 (Remote Sync ADR), ADR_011 (Listener Loop).

---

## 1. Context

До v5.74.0 в канонических доках (`CORE_PROMPT.md`, `BUFFY.md`, `BUFFY_PROJECT.md`) идентичность была раздроблена:

- `CORE_PROMPT.md` §1: *«Buffy, главный AI-ассистент и стратегический навигатор **платформы** Freebuff (Workspace OS)»* — отделяет Buffy от Freebuff, представляет Freebuff платформой.
- `BUFFY.md` top section: *«Ты — главный AI-ассистент **в системе** Freebuff»* — Buffy сидит "в" Freebuff как sub-agent.
- `BUFFY_PROJECT.md` Блок 1-§1: *«Buffy — это не coding assistant. Buffy — Agentic Platform и Knowledge Operating System»* — выдаёт Buffy за всю платформу, что тоже неточно.

Реальное использование показало другую картину (user clarification 2026-08-04):

1. **Promt-48** интерпретировался как «запуск Баффи как subprocess» — на самом деле это **внешний интерфейс** к ИИ-мозгу Freebuff, доступный когда вся платформа (Workspace OS) скачана на телефон из облака и работает on-device (Termux). Пользователь хочет управлять системой Freebuff со смартфона, **не только из локального терминала**.
2. **Buffy ≡ Freebuff** (неразрывны): «подключиться к Баффи» = «подключиться к системе Freebuff». Buffy — её ИИ-мозг, а не отдельный sub-agent.
3. **Workspace OS** — целевое имя платформы (сейчас синоним с Freebuff; rebrand planned). Платформа ≠ мозг.
4. **Future**: другие пользователи должны иметь возможность **заменить Buffy целиком** либо **распределить по задачам** (multi-agent брейн-слой) — без переписывания платформы.

Этот ADR фиксирует результат уточнения.

---

## 2. Decision

Принята **трёхуровневая identity model**:

| Уровень | Имя | Что это | Кто меняет |
|---|---|---|---|
| **1. Платформа** | **Workspace OS** (= rebrand «Freebuff» codebase) | Кодовая база + infra: `core_02/`, `scripts_01/`, `freebuff_plugin_03/`, `runtime_05/`, `runtime_*/scenarios/`, `docs_10/`, `pompts_11/`, MCP server, plugins | Только core team (через PR-review) |
| **2. ИИ-мозг** | **Buffy / Freebuff-agent** | Агентский слой: LLM router, memory engines, context builder, tool runtime, capability router | Может быть замещён пользователем (если infra позволяет) или распределён по задачам |
| **3. Каналы доступа** | Telegram `/task`, MCP server (FastAPI :8765), REST `/metrics/*`, `/sync/status`, `pompts_11/` файловая очередь, локальный терминал | Интерфейсы «снаружи» → ИИ-мозг | Расширяются постепенно (TG bot, MCP tools, REST endpoints) |

**Ключевые properties:**

- **Identity unification** (Buffy ≡ Freebuff): пользователь, говорящий «Баффи» имеет в виду всю систему Freebuff (платформа + мозг), а не «ассистента в системе».
- **Workspace OS rebrand safe**: канонические имена уровня 1 мигрируют постепенно (в доксах, именах файлов); на текущем этапе Workspace OS ≡ Freebuff (синонимы).
- **Swappable-brain protocol**: ядро `core_02/router.py` (Capability Router) уже умеет роутить между LLM-провайдерами. Пользователь-замена = поднять свой `core_02/router.py` с другим scoring/правилами; платформа остаётся той же.
- **Multi-agent distribution (deferred в v6.x)**: распределение Buffy по задачам требует новой инфраструктуры (`core_02/multi_agent_router.py`); ADR-012 декларирует намерение, но не навязывает runtime.

---

## 3. Альтернативы, которые рассматривались

1. **Status quo (Buffy = sub-agent OF Freebuff)** — **rejected**. Не отражает реальный UX (пользователь скачивает всю систему и обращается к ней). Расщепление идентичности ведёт к фразеологии типа "ассистент в системе", которая вводит в заблуждение относительно границ замены.
2. **Hard-coded Buffy lock-in** — **rejected**. Блокирует другие брейн-реализации (e.g. локальный Qwen, Claude, юзерский брейн на собственной инфре) и multi-agent scenarios.
3. **Buffy-as-Swappable-Brain (принято)** — модель distributed brain layer: core infrastructure сохраняется за платформой (Workspace OS), но брейн заменяем через `core_02/router.py`-extension + alternative scorer. Платформа и мозг — два разных продукта эволюционно.
4. **Federation of Buffys (deferred в v6.x)** — каждый пользователь имеет свой брейн-инстанс, федеративный orchestration. Пересекается с §3, но требует отдельного инфра-слоя (`core_02/federation.py`); track в [ADR backlog***REMOVED***(https://example) (TODO).

---

## 4. Consequences

### Положительные

- **Идентичность docs стабильна**: 3 canonical-файла (CORE_PROMPT §1, BUFFY.md top, promt48.md ЦЕЛЬ) получили согласованный «Clarification (2026-08-04, v5.74.0)» block. Никаких новых требований к коду promt-48 / MCP / TG.
- **Workspace OS rebrand готов к миграции**: имя введено в docs как синоним, но не форсируется замена путей и §BUFFY_PROJECT.md сразу — планомерная миграция в v5.74+ если команда одобрит.
- **Future user replacement возможен** с минимальными doc-изменениями: поднимаешь свой `core_02/router.py` альтернативный скорер → система работает; canonical attribution исчезает, capability-based routing остаётся.
- **Multi-agent distribution** имеет явный anchor в ADR backlog — будущий `core_02/multi_agent_router.py` имеет прецедент и motivation, не требует "cold start" обоснования.

### Негативные / риски

- **No runtime yet**: ядро `core_02/router.py` уже в production, но full swappable-brain API surface (load balancer, A/B brain selector, brain hot-swap) — не существует. Это технический долг, не блокирующий семантику.
- **Workspace OS rebrand требует миграции**: canonical doc-файлы (~5+ : `CORE_PROMPT.md`, `BUFFY.md`, `BUFFY_PROJECT.md`, `AGENTS.md`, deck `pompts_11/023_02_kanonicheskaya_model_workspace_os.md`, `pompts_11/044_09_canonical_history_mission.md`). Рекомендуется поэтапная миграция (v5.74 — docs identity, v5.80+ — file/path rename).
- **Multi-agent distribution нужен runtime** (v6.x scope): `core_02/multi_agent_router.py` — новый файл, нужен reviewer + tests. SEPARATE ADR eventually, чтобы не размывать ADR_012.

---

## 5. Forward-looking guards

1. **`core_02/router.py` — Capability Router уже production** (✅ v5.20+). Новые scoring-функции / brain-плагины могут добавляться без изменения платформы.
2. **Canonical docs reference ADR_012**:
   - `docs_10/core/CORE_PROMPT.md` §1 [✅ clarification block v5.74.0***REMOVED***
   - `BUFFY.md` top [✅ clarification block v5.74.0***REMOVED***
   - `pompts_11/promt48.md` ЦЕЛЬ [✅ item 0 clarification v5.74.0***REMOVED***
   - `docs_10/decisions/DECISIONS.md` (canonical index) [TODO: добавить строку при ship v5.74.0***REMOVED***
   - `docs_10/vision/decision_index.md` (navigation) [TODO***REMOVED***
3. **Lesson в `core_02/LESSONS.md` (CON-NEW)**: документирует lesson learned по identity split → unified, чтобы следующий рефакторинг не разворачивал канонические определения без согласования.
4. **Test surface**: прямо сейчас test для "swappable brain" не существует (нет runtime для brain hot-swap). Min ACCEPTED criterion — **`core_02/router.py` API не сломан** (existing tests green в v5.74.0). EXTENDED criterion — new brain pluggable interface (`core_02/brain_plugin.py`) — отдельный ADR в v6.x scope.

---

## 6. Cross-references

- [`docs_10/core/CORE_PROMPT.md` §1***REMOVED***(../core/CORE_PROMPT.md) — Identity (clarification block v5.74.0)
- [`BUFFY.md`***REMOVED***(../../BUFFY.md) — top section (clarification block v5.74.0)
- [`pompts_11/048_11_platform_rewrite_directive.md`***REMOVED***(../../pompts_11/048_11_platform_rewrite_directive.md) — ЦЕЛЬ (item 0 clarification v5.74.0)
- [`CHANGELOG.md`***REMOVED***(../../CHANGELOG.md) v5.74.0 — запись этого clarification
- [`core_02/LESSONS.md`***REMOVED***(../../core_02/LESSONS.md) — CON-NEW lesson (clarification discipline)
- Canonical decisions index: [`docs_10/decisions/DECISIONS.md`***REMOVED***(../decisions/DECISIONS.md) [planned entry***REMOVED***
- [`docs_10/vision/decision_index.md`***REMOVED***(../vision/decision_index.md) [planned navigation entry***REMOVED***
- ADR-001 (positioning: aggregator, not competitor) — WorkSpace OS = aggregator pattern
- ADR-010 (Remote Sync Telegram Relay) — uses same "platform layer oblivious to brain" principle
- ADR_011 (Listener Loop) — independent infra

---

## 7. Implementation status

| Шаг | Где | Статус |
|---|---|---|
| Clarification block в CORE_PROMPT.md §1 | CORE_PROMPT.md L13-15 | ✅ v5.74.0 |
| Clarification block в BUFFY.md top | BUFFY.md L11-19 | ✅ v5.74.0 |
| Item 0 в 048_11_platform_rewrite_directive.md ЦЕЛЬ | 048_11_platform_rewrite_directive.md L4-13 | ✅ v5.74.0 |
| ADR_012 файл | docs_10/engineering-memory/decisions/ADR_012_buffy_swappable_brain.md | ✅ this file |
| CON-NEW в LESSONS.md | core_02/LESSONS.md (прибавляется) | ✅ v5.74.0 |
| CHANGELOG v5.74.0 | CHANGELOG.md top (прибавляется) | ✅ v5.74.0 |
| DECISIONS.md index update | docs_10/decisions/DECISIONS.md | 📌 TODO при ship |
| decision_index.md nav update | docs_10/vision/decision_index.md | 📌 TODO при ship |
| BUFFY_PROJECT.md rename (Buffy Project 2.0 → Workspace OS 2.0) | deferred к v5.80+ | 📌 DEFERRED |
| Brain-plugin runtime API (`core_02/brain_plugin.py`) | deferred к v6.x | 📌 DEFERRED |
| Multi-agent router (`core_02/multi_agent_router.py`) | deferred к v6.x | 📌 DEFERRED |

— *ADOPTED 2026-08-04 (v5.74.0)*
