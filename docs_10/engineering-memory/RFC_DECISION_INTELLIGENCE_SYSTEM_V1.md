# RFC: Decision Intelligence System v1

**Статус:** 📋 RFC (ожидает утверждения)
**Автор:** Buffy (promt53 → 053_16_organizational_intelligence_final_synthesis)
**Дата:** 2026-08-05
**Основание:** [pompts_11/053_16_organizational_intelligence_final_synthesis.md***REMOVED***(../../pompts_11/053_16_organizational_intelligence_final_synthesis.md) — user directive
**Связанные RFC:** [Organizational Memory Engine v1***REMOVED***(./RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md) (v5.92.0), [Evolution v1.1***REMOVED***(./RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1_EVOLUTION.md) (v5.93.0)
**Финальный синтез:** promt51 (память) + promt52 (эволюция) + promt53 (интеллект решений)

---

## 0. Architectural Fit Check (AFC)

### Что уже существует

| Компонент | Что даёт | Статус |
|-----------|---------|--------|
| **Organizational Memory** (RFC v5.92.0) | Knowledge Objects 10+ типов, Knowledge Graph, Semantic Layer, Learning Loop, Analytics | 📋 RFC |
| **Knowledge Engine** | FTS5 + TF-IDF + SVD — семантический поиск по знаниям | ✅ Production |
| **Graph Index** | Граф связей между документами (7+9 rel_types) | ✅ Production |
| **Event Bus** | Публикация событий платформы | ✅ Production |
| **ADR (Architecture Decision Records)** | Фиксация принятых архитектурных решений | ✅ Готов (arch_decisions) |
| **LESSONS.md** | ~46 уроков CON-/ANTI-/CAND- | ✅ Production (ручной) |
| **Pattern Discovery** | Кластеризация событий → candidate → lesson | 📋 RFC (Evolution I-6) |
| **Learning Loop** | Feedback → confidence → validation | 📋 RFC |
| **Policy Engine** | Правила vs советы (enforcement) | 📋 RFC (Evolution I-3) |
| **Decision Trace** | Почему платформа выбрала конкретный KO | 📋 RFC (Evolution I-2) |
| **Authority Model** | Уровни доверия к знаниям | 📋 RFC (Evolution I-1) |

### Что отсутствует

Есть компоненты, которые хранят знания, ищут их, связывают и оценивают. Но нет компонента, который отвечает на вопрос:

> **«Это архитектурное решение — хорошее? Какие у него риски? Есть ли альтернативы? Не создаст ли оно технический долг?»**

Сейчас эту функцию выполняет **роль** «Chief Systems Critic» — человек или LLM в конкретном промте. Но роль — это разовое действие. Подсистема — это постоянный механизм.

### Почему нельзя заменить одной ролью

| Роль (prompt) | Подсистема (DIS) |
|--------------|-----------------|
| Работает один раз | Работает постоянно |
| Контекст ограничен одним промтом | Имеет доступ ко всей Organizational Memory |
| Не помнит предыдущие решения | Отслеживает эволюцию решений во времени |
| Не может предотвратить повтор ошибок | Сравнивает новые RFC с историей конфликтов |
| Даёт рекомендацию и исчезает | Отслеживает outcome решения и обновляет модель |

---

## 1. Назначение подсистемы

**Decision Intelligence System (DIS)** — подсистема платформы Buffy, которая:

1. **Анализирует** архитектурные решения (RFC, ADR, идеи) на качество, риски и противоречия
2. **Сравнивает** новые предложения с существующей Organizational Memory
3. **Обнаруживает** будущий технический долг до реализации
4. **Объясняет** рекомендации со ссылками на Knowledge Objects
5. **Отслеживает** жизненный цикл архитектурных решений от идеи до outcome
6. **Самообучается**: каждое решение → feedback → улучшение модели оценки

**Фундаментальная проблема, которую решает DIS:**
Платформа накапливает знания, но не умеет применять их для оценки новых архитектурных решений. Без DIS каждое новое решение оценивается «с нуля» — человеком или LLM без полного контекста Organizational Memory.

---

## 2. Архитектурные принципы

1. **Additive Architecture** — DIS расширяет существующие компоненты, не заменяет их
2. **Memory-first** — все оценки строятся на Organizational Memory, не на «мнении»
3. **Traceable** — каждая рекомендация имеет цепочку: KO → анализ → вывод
4. **Self-improving** — outcome решения → обновление confidence KOs → более точные оценки
5. **Не блокирует** — DIS советует, но не запрещает (enforcement = advisory, не blocking)
6. **Explainable** — «почему это решение risky» всегда со ссылками на конкретные уроки/ADR

---

## 3. Место в общей архитектуре

```
┌──────────────────────────────────────────────────────────────┐
│                    DECISION INTELLIGENCE SYSTEM                │
│  Architecture Review · Conflict Analysis · Debt Prediction    │
│  Policy Check · Alternative Search · Evolution Planning       │
├──────────────────────────────────────────────────────────────┤
│                   ORGANIZATIONAL MEMORY                       │
│  Knowledge Objects · Graph · Semantic · Learning · Analytics  │
├──────────────────────────────────────────────────────────────┤
│  Knowledge Engine  │  Event Bus  │  ADR  │  LESSONS  │  ...  │
└──────────────────────────────────────────────────────────────┘
```

**DIS использует:**
- `OrganizationalMemory` → все Knowledge Objects для анализа
- `KnowledgeEngine` → семантический поиск похожих решений
- `GraphIndex` → поиск related/contradicts/supersedes связей
- `EventBus` → публикация review-событий
- `DecisionTrace` → история принятых решений и их исходов

**DIS используется:**
- Через CLI: `python scripts_01/decision_intelligence.py review RFC_*.md`
- Через API: `dis.review_architecture(document_text) → ReviewReport`
- Через EventBus: автоматический review при создании нового ADR/KO

**Зависимости запрещены:**
- DIS не зависит от конкретных LLM-моделей (использует SmartRouter)
- DIS не имеет доступа к runtime-состоянию (только к Organizational Memory)
- DIS не модифицирует исходные документы (только создаёт review-записи)

---

## 4. Основные компоненты

### 4.1 Architecture Review Engine (ARE)

**Назначение:** Оценивает архитектурный документ (RFC, ADR, idea) по 10+ критериям.

**Вход:** текст документа + контекст (связанные KO)
**Выход:** `ReviewReport` с оценками, рисками, рекомендациями

**Критерии оценки:**
| Критерий | Что проверяется | Вес |
|----------|----------------|-----|
| Consistency | Не противоречит ли существующим ADR/KO? | 0.20 |
| Completeness | Все ли необходимые разделы присутствуют? | 0.10 |
| Scalability | Выдержит ли 10× рост? | 0.15 |
| Coupling | Много ли новых зависимостей? | 0.15 |
| Additivity | Не ломает ли существующее? | 0.15 |
| Debt Risk | Создаст ли технический долг? | 0.15 |
| Evolution Fit | Вписывается ли в долгосрочную стратегию? | 0.10 |

**Механизм:**
```python
class ArchitectureReviewEngine:
    def review(self, document: str, context: ReviewContext) -> ReviewReport:
        # 1. Извлечь утверждения из документа
        claims = self._extract_claims(document)
        
        # 2. Для каждого утверждения: semantic search в Organizational Memory
        for claim in claims:
            related_kos = om.search(claim, kind=['adr','lesson','pattern'***REMOVED***, top_k=10)
            contradictions = [ko for ko in related_kos if self._contradicts(claim, ko)***REMOVED***
            supports = [ko for ko in related_kos if self._supports(claim, ko)***REMOVED***
        
        # 3. Оценить по критериям
        scores = self._score_criteria(claims, contradictions, supports)
        
        # 4. Сгенерировать рекомендации
        recommendations = self._generate_recommendations(scores, contradictions)
        
        return ReviewReport(scores=scores, contradictions=contradictions,
                           supports=supports, recommendations=recommendations,
                           confidence=self._calculate_confidence(scores))
```

### 4.2 Conflict Analysis Engine (CAE)

**Назначение:** Ищет противоречия между новым предложением и Organizational Memory.
**Обёртка над:** Evolution I-5 (Conflict Resolver) — CAE **оркестрирует** обнаружение, классификацию и lifecycle-conflict'ов, делегируя разрешение Conflict Resolver'у. Новое: классификация contradiction/duplicate/overlap + severity scoring + связь с конкретными claims RFC.

**Типы конфликтов:**
- **Logical contradiction**: KO-A утверждает X, RFC утверждает not-X
- **Architectural conflict**: RFC нарушает принцип из существующего ADR
- **Pattern violation**: RFC противоречит подтверждённому паттерну (CON-*)
- **Dependency conflict**: RFC вводит зависимость, которую платформа уже исключила

**Механизм:**
```python
class ConflictAnalysisEngine:
    def analyze(self, document: str, domain: str = None) -> ConflictReport:
        # 1. Semantic search: найти KO с противоположной позицией
        claims = self._extract_claims(document)
        for claim in claims:
            opposite = om.search(f"NOT {claim***REMOVED***", top_k=10, mode='semantic')
            for ko in opposite:
                if self._is_contradiction(claim, ko):
                    conflicts.append(Conflict(claim=claim, contradicts=ko, 
                                             severity=self._severity(claim, ko)))
        
        # 2. Проверить против ADR и Policy
        adrs = om.search(kind='adr', top_k=20)
        policies = om.search(kind='rule', enforcement='mandatory', top_k=10)
        
        return ConflictReport(conflicts=conflicts, ...)
```

### 4.3 Technical Debt Analyzer (TDA)

**Назначение:** Предсказывает будущий технический долг до реализации.
**Обёртка над:** Evolution I-12 (Scalability/debt patterns) — TDA **специализирует** debt-паттерны для RFC-анализа, добавляя: сравнение с ANTI-* уроками, severity-оценку, estimated_debt_years. Не дублирует I-12 — использует его каталог паттернов как источник.

**Анализируемые паттерны долга:**
| Паттерн | Признак | Пример |
|---------|--------|--------|
| Single-entity design | Проектирование вокруг одной сущности | «Lessons» вместо Knowledge Objects (ANTI: CON-37) |
| Hardcoded paths | Абсолютные пути в коде | `/tmp/interior_planner_seed` (ANTI: CAN-8) |
| Missing abstraction | Конкретная реализация вместо интерфейса | ABC не выделен (ANTI-7) |
| Premature optimization | Сложность до подтверждения потребности | SVD до FTS5 |
| God component | Один класс делает всё | `KnowledgeEngine` 851 строка |
| Missing lifecycle | Нет decay, нет validation | Статус без lifecycle_stage |
| Authority flatness | Все знания равны | Без authority-модели (Evolution I-1) |

**Механизм:**
```python
class TechnicalDebtAnalyzer:
    def analyze(self, document: str) -> DebtReport:
        patterns = self._detect_debt_patterns(document)
        # Каждый паттерн сравнивается с CON/ANTI из Organizational Memory
        for pattern in patterns:
            related_lessons = om.search(pattern, kind='lesson', top_k=5)
            if related_lessons and any(l.id.startswith('ANTI-') for l in related_lessons):
                pattern.severity = 'high'
        return DebtReport(patterns=patterns, estimated_debt_years=...)
```

### 4.4 Policy Checker

**Назначение:** Проверяет RFC на соответствие Policy (правилам платформы).

**Обёртка над:** Evolution I-3 (Policy Enforcement Point `policy_checker.py`) — DIS Policy Checker **специализирует** проверку для RFC-документов: вместо проверки action_context (runtime), проверяет claims документа против mandatory/blocking правил.

**Механизм:**
```python
class PolicyChecker:
    def check(self, document: str) -> PolicyReport:
        policies = om.search(kind='rule', enforcement__in=['mandatory','blocking'***REMOVED***, top_k=50)
        violations = [***REMOVED***
        for policy in policies:
            if self._violates(document, policy):
                violations.append(PolicyViolation(policy=policy, ...))
        return PolicyReport(violations=violations)
```

### 4.5 Evolution Planner

**Назначение:** Оценивает, как RFC повлияет на платформу через 1 / 3 / 5 лет.

**Анализируемые измерения:**
- Рост числа KO в затронутых доменах
- Необходимость миграции при масштабировании
- Новые зависимости, которые станут блокерами
- Совместимость с прогнозируемыми изменениями платформы

### 4.6 RFC Reviewer (интеграция всех компонентов)

**Назначение:** Оркестратор — запускает все анализаторы и синтезирует единый отчёт.

```python
class RFCReviewer:
    def __init__(self, om: OrganizationalMemory, ke: KnowledgeEngine, 
                 graph: GraphIndex, event_bus: EventBus):
        self.are = ArchitectureReviewEngine(om, ke)
        self.cae = ConflictAnalysisEngine(om, ke, graph)
        self.tda = TechnicalDebtAnalyzer(om, ke)
        self.pc = PolicyChecker(om)
        self.ep = EvolutionPlanner(om, graph)
        self.event_bus = event_bus
    
    def review_rfc(self, rfc_path: Path) -> SynthesisReport:
        document = rfc_path.read_text()
        
        architecture = self.are.review(document)
        conflicts = self.cae.analyze(document)
        debt = self.tda.analyze(document)
        policies = self.pc.check(document)
        evolution = self.ep.plan(document)
        
        synthesis = self._synthesize(architecture, conflicts, debt, policies, evolution)
        
        self.event_bus.publish(Event(type='dis.review.completed', 
                                     data={'rfc': str(rfc_path), 'score': synthesis.overall_score***REMOVED***))
        
        return synthesis
```

---

## 5. Потоки данных

```
НОВЫЙ RFC / ADR / ИДЕЯ
    │
    ▼
┌─────────────────────────────────────┐
│        RFC REVIEWER (оркестратор)     │
├─────────────────────────────────────┤
│  ARE ──→ ReviewReport               │
│  CAE ──→ ConflictReport             │
│  TDA ──→ DebtReport                 │
│  PC  ──→ PolicyReport               │
│  EP  ──→ EvolutionReport            │
├─────────────────────────────────────┤
│  SYNTHESIS → SynthesisReport         │
│    · overall_score (0–10)            │
│    · critical_issues (blockers)       │
│    · warnings                        │
│    · recommendations                 │
│    · confidence                      │
└─────────────────────────────────────┘
    │
    ├─→ Organizational Memory (review как KO kind=review)
    ├─→ Event Bus (dis.review.completed)
    ├─→ Decision Trace (какие KO использованы в анализе)
    └─→ CLI / API (вывод пользователю)
```

**После реализации решения:**
```
IMPLEMENTATION OUTCOME
    │
    ▼
FEEDBACK → Organizational Memory
    · confidence обновляется у КО, использованных в review
    · Если решение успешно → authority KOs повышается
    · Если решение провалилось → review-методология корректируется
```

---

## 6. Взаимодействие с Organizational Memory

### Что DIS берёт из Memory

| Запрос | Для чего |
|--------|---------|
| `om.search(claim, kind=['adr','lesson','pattern'***REMOVED***)` | Поиск похожих и противоречащих знаний |
| `graph.get_related(ko_id, rel_type='contradicts')` | Поиск известных конфликтов |
| `om.search(kind='rule', enforcement='mandatory')` | Policy check |
| `dt.get_decision_history(similar_context)` | Как платформа решала похожие проблемы |

### Что DIS сохраняет обратно

| Artifact | kind | Описание |
|----------|------|---------|
| Review Report | `review` | Полный отчёт анализа RFC |
| Found contradiction | `observation` | Новый обнаруженный конфликт (→ candidate → lesson) |
| Debt prediction | `observation` | Предсказанный технический долг (→ candidate) |
| Recommendation | `guideline` | Рекомендация, если подтверждена outcome |

### Что становится частью опыта платформы

1. **Успешный review → confidence KOs растёт** — использованные KO подтвердили свою полезность
2. **Review нашёл реальную проблему → authority ревьюера растёт** — методология улучшается
3. **Review пропустил проблему → ANTI-pattern** — фиксируется как урок на будущее
4. **Повторяющийся паттерн конфликтов → новый CON-** — платформа учится предотвращать

---

## 7. Жизненный цикл архитектурного решения

```
IDEA (💡)
    │
    ▼
RFC DRAFT (📋)
    │
    ▼
┌─── DIS REVIEW ───────────────────────────┐
│  ARE: consistency, completeness, scale   │
│  CAE: conflicts with existing KOs        │
│  TDA: debt risk assessment               │
│  PC:  policy compliance                  │
│  EP:  long-term evolution impact         │
├──────────────────────────────────────────┤
│  SYNTHESIS: score + recommendations      │
└──────────────────────────────────────────┘
    │
    ├─ score ≥ 7, 0 critical → APPROVED
    ├─ score 4–7, ≤2 critical → NEEDS REVISION
    └─ score < 4, >2 critical → REJECTED
    │
    ▼
REVISION (🔄) — автор дорабатывает, новый review
    │
    ▼
APPROVED → ADR (📝) — решение зафиксировано
    │
    ▼
IMPLEMENTATION (🔧)
    │
    ▼
OUTCOME FEEDBACK
    │
    ├─ SUCCESS → связанные KO: confidence↑, authority reviewed
    └─ FAILURE → анализ причин → ANTI-pattern / lesson update
    │
    ▼
KNOWLEDGE UPDATE → Organizational Memory обновлена
```

---

## 8. Decision Intelligence: поиск, анализ, объяснение

### 8.1 Поиск альтернатив

```python
dis.find_alternatives(rfc) → List[Alternative***REMOVED***
# Использует semantic search + graph traversal:
# «какие ещё решения предлагались для похожих проблем?»
# Источники: rejected ADRs, CAN-* candidates, IDEAS.md 💡/❌
```

### 8.2 Поиск противоречий

```python
dis.find_contradictions(rfc) → List[Contradiction***REMOVED***
# Использует CAE + GraphIndex.contradicts:
# «какие существующие знания противоречат этому RFC?»
```

### 8.3 Проверка политик

```python
dis.check_policies(rfc) → PolicyReport
# Использует PC:
# «нарушает ли RFC mandatory/blocking правила платформы?»
```

### 8.4 Анализ архитектурных рисков

```python
dis.analyze_risks(rfc) → RiskReport
# Использует TDA + семантический поиск ANTI-* уроков:
# «какие риски наиболее вероятны на основе прошлого опыта?»
```

### 8.5 Объяснение рекомендаций

```python
dis.explain_recommendation(rec_id) → Explanation
# Цепочка: рекомендация → KO-1 (поддерживает) + KO-2 (противоречит) → вывод
# «Рекомендация: не использовать X, потому что:
#  - CON-37: проектирование вокруг одной сущности создало проблему Y
#  - ANTI-7: single-source hardcode привёл к мажорному рефакторингу в v5.XX»
```

### 8.6 Сравнение вариантов

```python
dis.compare_options(rfc_list: List[RFC***REMOVED***) → ComparisonReport
# «RFC-A vs RFC-B: сравнение по 7 критериям ARE + evolution impact»
```

---

## 9. Policy Layer — место Policy в модели знаний

### Что такое Policy

Policy — это знание с `enforcement ≠ 'advisory'`. В отличие от обычного урока, Policy **требует** определённого поведения.

### Отличие Policy от других типов знаний

| Тип | Суть | Пример | enforcement |
|-----|------|--------|-------------|
| **Policy** | Обязательное правило платформы | «Без --no-tg не диспатчить ночью» | mandatory / blocking |
| **Rule** | Правило с рекомендательной силой | «Перед деплоем: drift_check» | advisory |
| **Guideline** | Руководство к действию | «Как документировать CON-уроки» | passive |
| **Lesson** | Проверенный опыт | CON-36: «не восстанавливать node_modules» | passive |
| **ADR** | Архитектурное решение | «Router вынесен в отдельный модуль» | passive (но может ссылаться на Policy) |

**Иерархия нормативной силы:**
```
Policy (mandatory/blocking)  ← DIS проверяет compliance
    ↓
Rule (advisory)              ← DIS предупреждает о нарушении
    ↓
Guideline / Lesson           ← DIS использует как evidence
    ↓
ADR                         ← DIS использует как контекст
```

---

## 10. Decision Trace для DIS

### Что сохраняется

```sql
CREATE TABLE decision_intelligence_traces (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id       TEXT NOT NULL,           -- UUID review-сессии
    rfc_path        TEXT NOT NULL,
    claim           TEXT NOT NULL,           -- конкретное утверждение из RFC
    ko_id_used      TEXT NOT NULL,           -- KO, использованный для оценки
    ko_role         TEXT NOT NULL,           -- supports|contradicts|related|policy
    influence_score REAL NOT NULL DEFAULT 0.0,  -- насколько KO повлиял на итоговую оценку
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (ko_id_used) REFERENCES knowledge_objects(id)
);
```

**Для каждого review сохраняется:**
- Какие KO были использованы для оценки каждого утверждения RFC
- Какой вклад (influence_score) каждый KO внёс в итоговый score
- Какие альтернативы были рассмотрены
- Какие варианты были отклонены и почему

---

## 11. Предотвращение технического долга

DIS предотвращает долг на этапе RFC, а не постфактум.

**Механизм:**

1. **Паттерн-матчинг**: TDA сравнивает RFC с каталогом ANTI-паттернов из Organizational Memory
2. **Симуляция эволюции**: EP моделирует рост системы на +1/+3/+5 лет с учётом RFC
3. **Сравнение с историей**: DIS ищет похожие решения, которые стали источником долга → ANTI-*
4. **Policy gate**: mandatory/blocking правила предотвращают известные ошибки

**Пример:**
> RFC предлагает новую таблицу `lessons` в отдельной БД.
> DIS: ⚠️ HIGH DEBT RISK
> - ANTI: CON-37 — «не проектировать вокруг одной сущности» (single-entity design)
> - Policy: «Все Knowledge Objects в context.db» (mandatory)
> - History: v5.92.0 заменил Lessons Memory Engine на Organizational Memory именно по этой причине

---

## 12. Future Evolution (5 лет)

### Год 1: DIS v1 — RFC Review
- Review RFC/ADR/идей через CLI
- Conflict detection (CAE) + Policy check (PC)
- Метрика: DIS находит ≥70% реальных конфликтов (измеряется post-hoc)

### Год 2: DIS v2 — Proactive
- Автоматический review при создании нового ADR (через EventBus)
- Architecture health dashboard: визуализация состояния архитектуры
- Метрика: DIS предотвращает ≥50% ANTI-* паттернов ДО реализации

### Год 3-5: DIS v3 — Predictive
- **Cross-project analysis**: сравнение архитектурных решений между проектами
- **Debt forecasting**: предсказание техдолга с точностью ≥60% (измеряется через 6 мес. после реализации)
- **Architecture recommendations**: DIS предлагает альтернативные архитектурные решения на основе Organizational Memory

**Что закладывается сейчас для этого:**
- `kind='review'` в Knowledge Objects — review-отчёты становятся частью памяти
- `DecisionTrace` — полная прослеживаемость решений
- `Authority` — модель доверия, которая будет усложняться
- API-first design — DIS доступен через CLI + API + EventBus
- Расширяемость компонентов: каждый анализатор (ARE, CAE, TDA) — независимый модуль, заменяемый/улучшаемый без переписывания оркестратора

---

## 13. Риски

| Риск | Вероятность | Влияние | Митигация |
|------|-----------|---------|----------|
| **DIS слишком консервативен** — блокирует инновации | Средняя | Высокое | DIS = advisory (не blocking); человек всегда может override |
| **Ложные срабатывания** — DIS находит «противоречия» там, где их нет | Высокая (v1) | Среднее | Confidence score у review; feedback-петля исправляет |
| **DIS не видит новых паттернов** — не может оценить unprecedented решения | Средняя | Среднее | ARE score < 5 при отсутствии related KOs → «недостаточно данных», не блокирует |
| **Зависимость от качества Organizational Memory** — garbage in, garbage out | Высокая | Высокое | Authority-модель (I-1) фильтрует шум; только reviewed+ KO влияют на critical-оценки |
| **Сложность поддержки** — 6 компонентов, много кода | Средняя | Среднее | Компоненты независимы; можно использовать по одному (ARE без CAE и т.д.) |

---

## 14. Альтернативы

### 14.1 Оставить как роль (Chief Systems Critic)
**Отклонено.** Роль не помнит, не учится, не масштабируется. DIS — это автоматизация роли с памятью.

### 14.2 Встроить в Organizational Memory (не отдельная подсистема)
**Отклонено.** OM хранит знания, DIS анализирует решения. Разные задачи. OM не должен знать о «review process».

### 14.3 Использовать только LLM (без структурного анализа)
**Отклонено.** LLM хорош для synthesis, но не для систематического сравнения с 500+ KOs. DIS использует LLM для synthesis, но structural analysis — детерминированный.

---

## 15. План внедрения

### Phase 1: RFC Reviewer Core (минимальный viable DIS)
- `scripts_01/rfc_reviewer.py` — оркестратор + ARE (только consistency + completeness)
- CLI: `python scripts_01/rfc_reviewer.py review docs_10/engineering-memory/RFC_*.md`
- Интеграция с Organizational Memory (read-only search)

### Phase 2: Conflict Analysis + Policy Check
- CAE + PC
- Интеграция с Knowledge Graph (contradicts-рёбра)

### Phase 3: Technical Debt Analyzer + Evolution Planner
- TDA на основе ANTI-* паттернов
- EP с симуляцией роста

### Phase 4: Self-improving Loop
- Feedback от outcome решений → обновление confidence KOs
- Автоматический review при создании нового ADR

---

## 16. Рекомендации

1. **Начать с Phase 1** — RFC Reviewer Core: минимальный компонент, immediate value
2. **Интегрировать с Organizational Memory Phase 2** — без OM нет данных для анализа
3. **DIS = advisory, не blocking** — платформа советует, человек решает
4. **Review-отчёты — это Knowledge Objects** (`kind='review'`) — DIS сам становится частью Organizational Memory
5. **Не пытаться сделать DIS «идеальным» в v1** — confidence + feedback-петля исправят ошибки со временем

---

**Статус RFC:** Ожидает утверждения пользователем.

**Следующий шаг:** Phase 1 — RFC Reviewer Core + интеграция с Organizational Memory Phase 2.
