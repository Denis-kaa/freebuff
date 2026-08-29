# GAP_MAP.md — Мапа разрывов

> **Статус:** FORENSIC FACT + INFERENCE

---

## 1. MISSING (не существует в коде)

| # | Gap | Приоритет | Описание |
|---|-----|-----------|----------|
| G-1 | Agent ABC | High | Нет единой абстракции агента |
| G-2 | Intelligence Layer (как единый модуль) | High | Нет единого слоя; размыт по модулям. Прим.: Intelligence как emergent-свойство частично реализован (см. PLATFORM R.1) — «единый модуль» missing vs «emergent-свойство» partial |
| G-3 | Skill abstraction | Medium | Нет сущности Skill (между Role и Tool) |
| G-4 | Artifact Registry | Medium | Нет единого реестра артефактов с lineage |
| G-5 | Proactive Companion | Medium | Нет активного советника/критика |
| G-6 | Evolution Engine | Low | Нет механизма самоэволюции |
| G-7 | Intent Router | Medium | Нет отдельного intent parsing |
| G-8 | A2A communication | Medium | Нет agent-to-agent messaging |
| G-9 | Project isolation | Medium | Нет per-project knowledge/memory boundary |
| G-10 | External capability gateway | Medium | Нет project→gateway→external capability |

## 2. PARTIAL (существует частично)

| # | Gap | Что есть | Чего нет |
|---|-----|----------|----------|
| P-1 | Feedback loop | _accumulate + scenario history | Не меняет factory/forge manifests |
| P-2 | Project boundary | Контейнер контекста | Не security/knowledge/memory boundary |
| P-3 | Artifact provenance | opportunity_id + tags | Нет единого lineage query |
| P-4 | Agent lifecycle | Presence register/unregister | Нет lifecycle для pipeline-ролей |
| P-5 | External isolation | WorkspaceRegistry privacy | Нет project-level gateway |
| P-6 | Companion | ScenarioIntelligence reactive | Нет proactive |
| P-7 | Intelligence | 5+ модулей emergent | Нет единого интерфейса |

## 3. CONCEPT ONLY (описано в док., не в коде)

| # | Концепт | Где описано | Статус |
|---|---------|-------------|--------|
| C-1 | "Workspace OS" | AGENTS.md §3, PLATFORM.md | Весь репозиторий = umbrella term |
| C-2 | "Intelligence" | промт104, docs | Emergent, не отдельный модуль |
| C-3 | "Companion" | промт104 §3 | ScenarioIntelligence — ближайший |
| C-4 | "Evolution" | BUFFY.md, VISION_3.0 | Нет кода |

## 4. Architectural Blind Spots (не в модели, но существуют)

| # | Подсистема | Файлы | Важность |
|---|------------|-------|----------|
| B-1 | Security | .keys/, Bearer auth | Критичная |
| B-2 | Policy Engine | freebuff_plugin_03/policy/ | Высокая |
| B-3 | Observability | metrics.py, notification.py | Высокая |
| B-4 | ACP Protocol | freebuff_plugin_03/acp_protocol.py | Средняя |
| B-5 | Bridge Layer | freebuff_plugin_03/bridge*.py | Средняя |
| B-6 | Bootstrap | freebuff_plugin_03/bootstrap/ | Средняя |
| B-7 | DIS Engine | core_02/dis_engine.py | Средняя |
| B-8 | MissingRegistry | core_02/missing_registry.py | Средняя |
| B-9 | Engineering Memory | scripts_01/engineering_memory.py | Средняя |
| B-10 | Remote Sync | core_02/remote_sync.py | Средняя |
| B-11 | Phone Control MCP | scripts_01/phone_control_mcp.py | Низкая |
| B-12 | Project Pulse | scripts_01/project_pulse.py | Средняя |

## 5. Contradictions

| # | Противоречие | Детали |
|---|--------------|--------|
| CT-1 | "Workspace OS" = весь репозиторий, но Workspace = dataclass с 3 полями | Модель vs реальность |
| CT-2 | Scenario ≠ Forge Pipeline (ортогональны), но в модели = последовательность | §7.3 |
| CT-3 | Agent в модели = активный участник, в коде = stateless pipeline-роль | Без communication |
| CT-4 | "Intelligence" в модели = отдельный слой, в коде = emergent | Без единого интерфейса |

## 6. Provenance / Traceability Gaps

| # | Gap | Описание |
|---|-----|----------|
| T-1 | Whim → Project | Слабый link (project_id строка, не FK) |
| T-2 | Decision → Execution | ScenarioDecision не linked to ChainRun |
| T-3 | Artifact → Feedback | Нет query: "все артефакты для opportunity" |
| T-4 | Pipeline Run → Role | Role execution details не сохраняются |
| T-5 | Session → Project | Session → workflow → artifact path не трассируется |
