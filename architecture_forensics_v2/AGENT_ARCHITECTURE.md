# AGENT_ARCHITECTURE.md — Агентная архитектура

> **Статус:** FORENSIC FACT

---

## 1. Что является "агентом" в системе

### 1.1 Pipeline-роли (Blueprint v3, 14 штук)

| Роль | Тип | Capabilities | Outputs |
|------|-----|--------------|---------|
| explainer | analysis | summarize, explain, classify | brief.md, parsed_requirements.md |
| lisa | estimation | summarize, estimation | lisa_report.md |
| risk | analysis | summarize, explain, reasoning | risk_matrix.md |
| decomposer | analysis | architecture, explain, plan | decomposition.md, module_list.md |
| architect | architecture | architecture, explain, summarize | architecture.md, adr/*.md |
| auditor | validation | review, architecture, explain | audit_report.md |
| developer | implementation | code, refactor, explain | src/**, tests/** |
| frontend | implementation | code, summarize, explain | frontend/** (web-only) |
| devops | infrastructure | code, summarize, reasoning | Dockerfile, docker-compose.yml |
| tester | validation | code, summarize, review | tests/**, mutation_report |
| fixer | implementation | code, refactor, explain | bug_fixes.md, regression_tests.py |
| acceptance | validation | review, explain, summarize | acceptance_report.md |
| documenter | delivery | summarize, explain | README.md, API_DOCS.md |
| retrospective | evolution | summarize, explain, reasoning | retrospective_report.md, LESSONS.md |

### 1.2 Presence-агенты (PresenceEngine)

- `agent_name` (уникальный)
- `status` (online/offline/away/busy)
- `heartbeat` (обновление presence)
- `metadata` (capabilities, roles)

### 1.3 Collaboration-участники (CollaborationEngine)

- `ParticipantRole`: OWNER / EDITOR / VIEWER
- `session_id`, `name`, `role`, `joined_at`

### 1.4 Role assignments (RoleEngine)

- `RoleDefinition`: name, description, capabilities[***REMOVED***
- `AgentRole`: agent_name, role_name, assigned_by, assigned_at

## 2. Что НЕ является агентом

- **Нет Agent ABC** — нет единого контракта для агента
- **Нет agent lifecycle** — pipeline-роли stateless; presence-агенты имеют register/unregister, но не lifecycle
- **Нет Agent-to-Agent communication** — pipeline-роли не общаются друг с другом (только через артефакты)
- **Нет agent memory/state** — агенты не имеют собственного состояния

## 3. Agent → Agent связи

**FACT:** Нет прямых Agent→Agent связей. Pipeline-роли связаны только через:
- `PIPELINE_CHAIN` (порядок выполнения)
- Артефакты предыдущей роли (existence check через RoleArtifactValidator)

**INFERENCE:** Это слабое место модели. Для настоящей multi-agent коллаборации нужен Agent ABC + A2A messaging + agent memory.

## 4. Intelligence → Agent

**FACT:** ScenarioIntelligence выбирает scenario/capability, но НЕ выбирает конкретного агента. ForgeFacade.run_chain() исполняет роли по фиксированному PIPELINE_CHAIN.

**INFERENCE:** Выбор "какого агента запустить" — это выбор capability → factory → forge → role_ids, а не выбор агента.

## 5. Рекомендации (INFERENCE, не решения)

1. Ввести `Agent` ABC с lifecycle (created→ready→running→done)
2. Добавить A2A messaging через EventBus (agent.message)
3. Дать агентам agent-scoped memory (per-agent namespace в MemoryStore)
4. Связать RoleEngine с pipeline-ролями (роли = агенты)
