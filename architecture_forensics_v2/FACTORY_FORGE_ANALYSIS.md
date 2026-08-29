# FACTORY_FORGE_ANALYSIS.md — Factory и Forge

> **Статус:** FORENSIC FACT

---

## 1. Factory Analysis

### 1.1 Есть ли реальная Factory abstraction?

**FACT:** ДА. `BaseFactory` (core_02/factory_base.py) — template class.

### 1.2 Контракт Factory

| Аспект | Реализация |
|--------|------------|
| Interface | BaseFactory (не ABC, но с class-level constants + abstract normalize_input) |
| Registry | FactoryRegistry (auto-discovery YAML из runtime_05/factories/) |
| Lifecycle | Нет явного lifecycle (instantiate → execute) |
| Capabilities | Class-level CAPABILITIES tuple per subclass |
| Inputs | Opportunity dataclass (id, project_id, title, description, provenance) |
| Outputs | Artifact dict (id, kind, opportunity_id, factory_id, forge_id, overall, validation) |
| Ownership | FactoryPassport (factory.yaml) |

### 1.3 Конкретные Factory

| Factory | Файл | Capabilities | Artifact kind |
|---------|------|--------------|---------------|
| ResearchFactory | scripts_01/research_factory.py | research, research_web | research_artifact |
| ContentFactory | scripts_01/content_factory.py | article_generation, book_generation, report_generation | content_artifact |
| TestFactory | scripts_01/test_factory.py | code (canonical: test/verifier) | test_artifact |

### 1.4 Позволяет ли архитектура расширение?

**FACT:** ДА. Registry auto-discovers новые директории `runtime_05/factories/<factory_id>/`. Новая Factory = новый BaseFactory subclass + YAML manifest + registry.yaml entry.

**INFERENCE:** Research/Content/Software/Design/Image/Video/Analysis Factory — **все возможны** через существующий паттерн.

## 2. Forge Analysis

### 2.1 Что фактически является Forge?

**FACT:** Forge — это **production pipeline** (вариант B + C из промта).

| Аспект | Реализация |
|--------|------------|
| ForgeFacade | core_02/forge_facade.py — единственный мост (§7.3) |
| ForgePipeline | core_02/forge_pipeline.py — 6-stage pipeline |
| ForgeRegistry | core_02/forge_registry.py — статусы проектов |
| Lifecycle | FORGE→CHECK→BUILD→TEST→DEPLOY→REPORT |
| Chain | ForgeFacade.run_chain() — 14 ролей |
| Stages | stage_forge, stage_check, stage_build, stage_test, stage_deploy, stage_report |
| Roles | PIPELINE_ROLES (14), LIGHT_ROLES (8), HEAVY_ROLES (4), REFERENCE_ROLES (2) |
| Execution | subprocess (shell/pytest/npm) + artifact existence check |
| Artifacts | RUNNABLE.md, CHECKLIST.md, STEPS.md + role outputs |
| Validation | RoleArtifactValidator (existence-only) + ForgeRegistry.validate_schema() |

### 2.2 Forge — это A/B/C/D/E/F?

| Вариант | Ответ | Обоснование |
|---------|-------|-------------|
| A. capability | ❌ | Forge не capability |
| B. production pipeline | ✅ | ForgePipeline = 6-stage build pipeline |
| C. executor | ⚠️ | Частично — subprocess execution |
| D. factory instance | ❌ | Не экземпляр Factory |
| E. workflow | ⚠️ | Chain-runner = workflow, но ForgePipeline = pipeline |
| F. другое | ⚠️ | ForgeFacade = bridge (gate + delegation) |

**INFERENCE:** Forge используется **неоднородно**: ForgePipeline = pipeline, ForgeFacade = bridge/gate, ForgeRegistry = state tracker.

## 3. Capability discovery chain

```
Factory (BaseFactory)
  ↓
resolve(capability) → FactoryRegistry.select_forge
  ↓
(FactoryPassport, ForgePassport)
  ↓
ForgeFacade.run_chain(project, role_ids)
  ↓
ForgePipeline (6 stages)
  ↓
Agent (pipeline-роль) → Skill (routing_hint) → Tool (ToolRegistry)
```

**FACT:** Кто обнаруживает отсутствие capability?
- `FactoryRegistry.find_by_capability()` → [***REMOVED*** если нет
- `BaseFactory.resolve()` → None если capability не зарегистрирована
- `MissingRegistry` — register-first lifecycle для недостающих элементов

**INFERENCE:** Обнаружение отсутствующей capability есть, но **нет автоматического** создания/подключения новой capability.

## 4. Рекомендации (INFERENCE)

1. Унифицировать терминологию Forge (pipeline vs bridge vs registry)
2. Добавить Factory lifecycle (registered → design_ready → implemented)
3. Автоматический capability gap detection → MissingRegistry → prompt → implementation
