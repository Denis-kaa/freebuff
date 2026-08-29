ИЗУЧИ ПРОМТ НИЖЕ, ПРОВЕДИ ИССЛЕДОВАНИЕ  КАКИОН ЛОЖИТСЯ НА НАШУ ПЛАТФОРМУ , СОПОСТАВЬ ЕГО С ЗАДАЧЕЙ КОТОРУЮ ВЫПОЛНЯЛИ ПЕРЕД ЭТОЙ. ПОСМОТРИ КАК ЕЕ СОПОСТАВИТЬ С factory , scenario , forge

РОЛЬ

Ты — Senior AI Systems Architect.

Твоя задача — спроектировать Research Engine как нативный
capability/tool внутри существующей AI Workspace Platform.

ВАЖНО:

Не проектируй отдельного чат-бота.
Не проектируй отдельное приложение.
Не создавай автономный продукт "Market Research Agent".

Research Engine должен стать внутренним инструментом Workspace,
который может вызываться существующим Orchestrator/Agent Runtime
точно так же, как любой другой capability.

==================================================
1. КОНТЕКСТ
==================================================

Workspace — это AI-производственная среда.

Пользователь создаёт проекты, задачи и цели.
AI-агенты помогают исследовать, планировать и выполнять работу.
В процессе выполнения появляются новые знания, инструменты,
workflow и reusable capabilities.

Необходимо добавить capability:

RESEARCH

Он должен позволять системе проводить исследования
реального мира и возвращать структурированные результаты,
которые могут использоваться другими агентами и сохраняться
в Knowledge/Workspace.

Пример:

Пользователь:

"Мне нужно заработать 30 000 ₽ в месяц.
Исследуй рынок фриланса и найди направления,
которые подходят моим навыкам и одновременно
могут прокачать Workspace."

Orchestrator должен иметь возможность вызвать:

research(
    objective=...,
    constraints=...,
    context=...
)

и получить структурированный результат.

==================================================
2. ОСНОВНАЯ АРХИТЕКТУРНАЯ ИДЕЯ
==================================================

Research должен быть не prompt-only capability.

Раздели систему на:

1. Research Tool Interface
2. Research Orchestrator
3. Research Planner
4. Source Discovery
5. Source Adapter Layer
6. Evidence Collector
7. Evidence Store
8. Data Normalizer
9. Pattern Detection
10. Evaluation Engine
11. Economic Analysis
12. Recommendation Engine
13. Knowledge Integration
14. Research Report Generator

Определи ответственность каждого компонента.

==================================================
3. TOOL INTERFACE
==================================================

Спроектируй стабильный API инструмента.

Минимально:

research.start()
research.status()
research.get_result()
research.cancel()

Определи:

- input schema;
- output schema;
- task_id;
- research_id;
- progress;
- status;
- errors;
- partial results;
- provenance;
- confidence.

Поддержать long-running research.

Инструмент НЕ должен требовать, чтобы вызывающий агент
ждал завершения всей работы в одном synchronous call.

==================================================
4. RESEARCH MISSION
==================================================

Research Engine получает Research Mission.

Mission должна содержать:

objective
questions
constraints
context
target_user
desired_output
depth
sources
budget
time_limit

Пример:

objective:
"Найти коммерческие направления для заработка"

constraints:
target_income = 30000 RUB
available_skills = [...***REMOVED***
available_time = [...***REMOVED***
workspace_strategy = "каждый заказ должен увеличивать reusable capability"

questions:
- что покупают?
- где покупают?
- сколько платят?
- насколько подходит пользователю?
- насколько повторяемо?
- можно ли превратить в capability?

==================================================
5. TOOL-AGNOSTIC ARCHITECTURE
==================================================

КРИТИЧЕСКОЕ ТРЕБОВАНИЕ.

Research Engine НЕ должен знать,
используется ли:

- web search;
- browser;
- Kwork connector;
- API;
- MCP;
- plugin;
- scraper;
- internal database.

Создай Source Adapter Interface.

Например:

SourceAdapter

discover()
search()
fetch()
extract()
validate()

Research Engine работает через абстракцию SourceAdapter.

Это позволит позже подключать новые источники
без изменения Research Engine.

==================================================
6. SOURCE REGISTRY
==================================================

Спроектируй registry источников.

Каждый источник должен описываться metadata:

source_id
name
type
capabilities
adapter
availability
authentication
cost
rate_limit
freshness
reliability

Примеры:

web_search
kwork
freelancehunt
upwork
hh
reddit
company_websites

Но НЕ предполагай наличие конкретного коннектора.
Архитектура должна позволять подключать их динамически.

==================================================
7. EVIDENCE-FIRST MODEL
==================================================

Research Engine не должен генерировать выводы
не подкреплённые evidence.

Создай сущность:

Evidence

Содержит:

evidence_id
source_id
url/reference
timestamp
raw_data
normalized_data
claim
confidence
provenance

Каждый вывод должен иметь связь:

Conclusion
→ Evidence[***REMOVED***

==================================================
8. RESEARCH PIPELINE
==================================================

Спроектируй pipeline:

MISSION
↓
PLANNING
↓
SOURCE DISCOVERY
↓
QUERY GENERATION
↓
COLLECTION
↓
EXTRACTION
↓
NORMALIZATION
↓
DEDUPLICATION
↓
CLASSIFICATION
↓
PATTERN DETECTION
↓
EVALUATION
↓
SYNTHESIS
↓
RECOMMENDATION
↓
KNOWLEDGE UPDATE

Каждая стадия должна быть независимой.

Pipeline должен поддерживать:

- retry;
- partial failure;
- resume;
- checkpoint;
- cancellation.

==================================================
9. RESEARCH MEMORY
==================================================

Research не должен каждый раз начинать с нуля.

Предусмотри:

Research History
Evidence Store
Pattern Library
Source History
Previous Conclusions
Workspace Knowledge

Если система уже знает:

"Lead → Telegram → CRM"

необходимо использовать существующее знание
как starting hypothesis, но не считать его доказательством.

==================================================
10. PATTERN ENTITY
==================================================

Создай reusable сущность:

CommercialPattern

Например:

pattern:
"Автоматизация обработки входящих заявок"

properties:

problem
buyer
trigger
deliverable
price_range
time_range
technologies
demand_signal
competition
repeatability
automation_potential
productization_potential
workspace_leverage
evidence[***REMOVED***

CommercialPattern должен быть пригоден
для повторного использования между исследованиями.

==================================================
11. OPPORTUNITY ENTITY
==================================================

Создай:

Opportunity

Она должна объединять:

market_pattern
user_fit
economic_model
competition
execution_complexity
workspace_leverage
evidence
recommendation

Это позволяет отделить:

"существующий рынок"

от:

"рынок, который подходит конкретному пользователю".

==================================================
12. USER CONTEXT
==================================================

Research Engine может получать context пользователя:

skills
experience
tools
projects
available_capabilities
constraints
goals

Но Research Engine НЕ должен жёстко зависеть
от конкретного пользователя.

Context является параметром Mission.

==================================================
13. WORKSPACE LEVERAGE
==================================================

Это обязательная часть.

Для каждого Opportunity система должна определить:

manual_work
automation_candidates
reusable_components
new_capabilities
future_reuse
estimated_time_reduction

Пример:

Client project
→ Telegram lead parser

создаёт:

Capability:
Lead Intake

Следующий проект:

WhatsApp lead parser

использует существующий capability.

==================================================
14. ECONOMIC MODEL
==================================================

Research Engine должен уметь рассчитывать:

target_income
project_price
projects_required
hours_per_project
monthly_hours
effective_hourly_rate
automation_factor
repeatability

Необходимо хранить assumptions отдельно
от фактических данных.

==================================================
15. OUTPUT CONTRACT
==================================================

Research Engine должен возвращать machine-readable результат.

Например:

ResearchResult

{
  research_id,
  status,
  executive_summary,
  evidence,
  market_patterns,
  opportunities,
  ranking,
  economics,
  recommendations,
  workspace_capabilities,
  next_actions,
  confidence,
  provenance
***REMOVED***

Не возвращай только markdown.

Markdown/HTML/PDF — presentation layer,
а не основной формат результата.

==================================================
16. AGENT INTEGRATION
==================================================

Покажи, как существующий Workspace Agent
использует Research Engine.

Пример:

USER
↓
Workspace Agent
↓
понимает, что требуется external research
↓
tool call: research.start()
↓
Research Engine
↓
progress updates
↓
research result
↓
Workspace Agent
↓
принимает решение
↓
создаёт project/task/capability

Research Engine НЕ должен самостоятельно
становиться главным агентом Workspace.

Он выполняет специализированную функцию.

==================================================
17. HUMAN-IN-THE-LOOP
==================================================

Определи точки, где система должна запросить человека.

Например:

- утверждение research scope;
- платные источники;
- авторизация;
- ambiguous objective;
- потенциально дорогой action;
- публикация результата.

Но не спрашивай пользователя там,
где решение можно принять безопасно автоматически.

==================================================
18. OBSERVABILITY
==================================================

Добавь:

research_id
mission_id
source_id
tool_call_id
stage
duration
token_usage
cost
errors
retry_count
evidence_count

Необходима возможность понять:

"Почему система пришла именно к этому выводу?"

==================================================
19. COST CONTROL
==================================================

Research может быть дорогим.

Спроектируй:

- research budget;
- token budget;
- tool-call budget;
- source priority;
- early stopping;
- diminishing-return detection.

Если новые источники перестали давать
новые patterns — остановить исследование.

==================================================
20. SECURITY
==================================================

Учесть:

- credentials;
- API keys;
- source authentication;
- tenant isolation;
- user permissions;
- data provenance;
- untrusted external content;
- prompt injection из внешних источников.

Внешний источник НИКОГДА не должен
получать возможность менять инструкции Research Engine.

==================================================
21. DELIVERABLE

Не пиши код сразу.

Сначала выдай:

1. архитектуру;
2. component map;
3. data model;
4. tool contracts;
5. state machine;
6. source adapter interface;
7. research pipeline;
8. persistence model;
9. agent integration;
10. failure handling;
11. observability;
12. security model;
13. MVP scope;
14. future extensions.

После этого:

MVP implementation plan.

==================================================
22. ГЛАВНЫЙ КРИТЕРИЙ

Research должен стать не отдельным приложением,
а новой способностью Workspace.

После реализации должно быть возможно:

любому агенту сказать:

"Мне необходимо исследование X"

и получить:

исследование → evidence → patterns → opportunities
→ decision → actions → knowledge.

При этом результаты одного исследования
должны повышать качество следующих исследований.

Система должна становиться не просто
способной искать информацию,

а способной НАБИРАТЬ КОММЕРЧЕСКИЙ ОПЫТ.