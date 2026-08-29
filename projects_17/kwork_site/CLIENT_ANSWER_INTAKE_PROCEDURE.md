# CLIENT_ANSWER_INTAKE_PROCEDURE.md — Процедура обработки ответов из Kwork-чата

> **Дата создания:** 2026-08-17
> **Когда читать:** когда клиент прислал ответы в Kwork-чат на вопросы из [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md)
> **Что НЕ делает этот документ:** **сам НЕ редактирует** [`STEPS.md`***REMOVED***(STEPS.md) [`SPEC.md`***REMOVED***(SPEC.md) [`LESSONS.md`***REMOVED***(LESSONS.md) [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) — это инструкция для исполнителя, что и как обновлять.
> **Канон:** [`docs_10/core/PROJECT_RULES.md`***REMOVED***(../../docs_10/core/PROJECT_RULES.md) §3 (контекст в проекте; уроки фиксировать по ходу) + §4 (порядок работы)
> **Стилевые образцы:** `projects_17/lead_aggregator/PHASE1_RESEARCH.md` (research-flow), `core_02/LESSONS.md` (CON/CAN/ANTI/PB-формат)

---

## 0. TL;DR

После получения ответов клиента — **3 обязательных обновления + 2 опциональных**:

| # | Действие | Обязательность | Файл |
|---|---|:---:|---|
| 1 | Flip чекбоксов `_ [ ***REMOVED***_ ❌_` → `_ [x***REMOVED***_ ✅_` | ✅ обязательно | [`STEPS.md`***REMOVED***(STEPS.md) §0 |
| 2 | Заполнить таблицу open questions ответом | ✅ обязательно | [`SPEC.md`***REMOVED***(SPEC.md) §11 |
| 3 | Добавить CAN/CON запись(и) для nontrivial-ответов | ✅ если nontrivial | [`LESSONS.md`***REMOVED***(LESSONS.md) |
| 4 | Bump v1 → v2 + обновить status | 🟡 опционально (рекомендуется) | [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) |
| 5 | Создать ADR-002 (Python vs PHP) + ADR-003 (Excel schema) | 🟡 опционально; **🔴 обязательно для Q1 и Q2** при их resolved | [`decisions/ADR-NNN_*.md`***REMOVED***(decisions/ADR-NNN_*.md) |

**Время выполнения:** ~15 минут на полное обновление (для опытного буффи, меньше для новичка).

---

## 1. Pre-conditions (чек перед стартом)

Перед обработкой ответов убедись, что:

- [ ***REMOVED*** Ответ клиента получен в Kwork-чате (текст ответа, не голосовое).
- [ ***REMOVED*** Существует [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) (после 1-й итерации — актуальная версия).
- [ ***REMOVED*** Известен **тип ответа** для каждого Q:
  - **Default принят** (клиент сказал «дефолт» или явно не ответил И прошло >3 дней).
  - **Custom override** (клиент дал конкретный ответ, отличный от default).
  - **Partial** (частично подтвердил + частично изменил).
  - **Conflict** (ответ противоречит ребром default).
  - **Missing** (клиент не ответил в указанный срок — treat как default с пометкой `silence=YYYY-MM-DD`).

---

## 2. Шаг 1 — Запись ответов в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md)

Для каждого resolved Q (любого типа) обновите per-Q таблицу:

### 2.1 Поля для заполнения

| Поле в таблице | Что заполнить | Пример |
|---|---|---|
| **Дата отправки** | TBD → конкретная дата | `2026-08-18` |
| **Статус ответа** | `❓ не получен` → `✅ получен` (или `🟡 partial`, `⚠️ conflict`) | `✅ получен` |
| **Ответ клиента** | заполнить текстом ответа (с конкретными HEX, полями, именами файлов) | `Python подтверждён` / `2 файла: файл_1.xlsx, файл_2.xlsx (структура: ...)` |
| **Дата ответа** | TBD → конкретная дата | `2026-08-19` |
| **Комментарии** | свободное поле для особенностей | `прислал файлы 18.08 вечером, общий ключ = номер контейнера (verified)` |

### 2.2 Default-политика

Если клиент **молчит** >3 дней на 🔴 вопрос:

- Применить **Default** из per-Q таблицы автоматически.
- Записать `silence=YYYY-MM-DD` в поле «Ответ клиента».
- В [`LESSONS.md`***REMOVED***(LESSONS.md) добавить отдельную **CAN-запись** (см. §4.2) с пометкой: «гипотеза default принята в условии молчания клиента; подтвердится при первом ответ клиента, который можно верифицировать».

### 2.3 Conflict-политика

Если ответ клиента явно противоречит default:

- Пример: Q3 default = «jpg в папке = скрины», а клиент прислал отдельный PNG.
- В [`LESSONS.md`***REMOVED***(LESSONS.md) добавить **ANTI-запись** (см. §4.3) с пометкой: «default был неточен; в следующих проектах уточнить у клиента ещё на этапе бриф'а».

### 2.4 Header / Общий статус

После записи ответов — обновить **Header / Общий статус**:

| Состояние | Status | Когда |
|---|---|---|
| Все 5🔴 resolved | 🟢 All-blockers-resolved | готов к Этапу 1.0 |
| Часть resolved, часть 🟡 | 🟡 Partial | некоторые hard blockers ещё не решены |
| Половина+ resolved | 🟡 Partial→Resolving | тренд к разрешению |

Также bump **Версия файла**: v1 → v2.

---

## 3. Шаг 2 — Flip чекбоксов в [`STEPS.md`***REMOVED***(STEPS.md) §0

### 3.1 Паттерн правки

Для каждого resolved Q найдите в [`STEPS.md`***REMOVED***(STEPS.md) §0 соответствующую строку:

**До:**
```markdown
- [ ***REMOVED*** 🔴 **Стек Excel-движка: Python vs PHP** (дословный «php или питон» в [`бриф.md`***REMOVED***(бриф.md); промт фиксирует Python — нужно подтверждение клиента)
```

**После (минимальная правка):**
```markdown
- [x***REMOVED*** ✅ **Стек Excel-движка: Python vs PHP** — Python подтверждён клиентом (2026-08-19; см. [ADR-002***REMOVED***(decisions/ADR-002_python_vs_php.md))
```

### 3.2 Multi-line правка для soft-блокеров

Если ответ 🟡 partial (не closed), альтернативный формат:

```markdown
- [x***REMOVED*** 🟡 **Q-soft B: Деплой-платформа** — VPS (Ubuntu 22.04, Python 3.10+, systemd-сервис); `RUNNABLE.md` обновить под VPS-сценарий [Этап 2.5***REMOVED***
```

> 🟡 **Расхождение классификаций:** [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) использует классификацию (5🔴 + 3🟡), тогда как [`STEPS.md`***REMOVED***(STEPS.md) §0 формально отмечен (6🔴 + 2🟡). При флипе чекбоксов **опирайтесь на актуальное состояние [`STEPS.md`***REMOVED***(STEPS.md) §0**; если классификация разошлась — **сначала синхронизируйте 2 файла в §0 чек-листа ниже**, потом флипайте по обновлённой классификации. Логика default-применения и partial-ответов идентична в обеих классификациях.

### 3.3 Чек-лист после правки

После всех правок убедитесь:
- [ ***REMOVED*** Все 🔴-строки либо `[x***REMOVED*** ✅`, либо `[ ***REMOVED*** 🟡 partial` (но НЕ остались `[ ***REMOVED*** 🔴` без resolved).
- [ ***REMOVED*** Каждая `[x***REMOVED***` строка содержит **конкретный ответ клиента** + **дату**.
- [ ***REMOVED*** Если есть pointer на ADR (Q1 → ADR-002, Q2 → ADR-003) — ссылка добавлена.

---

## 4. Шаг 3 — Заполнение [`SPEC.md`***REMOVED***(SPEC.md) §11 (Open Questions)

### 4.1 Структура таблицы §11 (до правки)

В файле [`SPEC.md`***REMOVED***(SPEC.md) §11 сейчас формат:

```markdown
| # | Блокер | Тип | Статус | Когда закрывается |
|---|---|---|---|
| **Q1** | **Стек Excel-движка:** Python (по `промт.md`) или PHP (альтернатива из `бриф.md` — дословно «php или питон скрипт»)? Подтверждение клиента требуется **до** Этапа 1. | 🔴 | _открыт_ | До старта Этапа 1.0 |
```

### 4.2 Паттерн правки

**До:**
```markdown
| **Q1** | **Стек Excel-движка:** Python ... | 🔴 | До старта Этапа 1.0 |
```

**После:**
```markdown
| **Q1** ✅ | **Стек Excel-движка (= Python)** — подтверждён клиентом **2026-08-19**; см. [ADR-002***REMOVED***(decisions/ADR-002_python_vs_php.md) + [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) §Q1 | 🔴 | ✅ Resolved | Resolved |
```

Или более компактный формат (если раздел длинный):

```markdown
| **Q1** ✅ | Стек Excel-движка: **Python подтверждён** (ответ: 2026-08-19) | 🔴 | ✅ Resolved | см. [ADR-002***REMOVED***(decisions/ADR-002_python_vs_php.md) |
```

### 4.3 Чек-лист после правки

- [ ***REMOVED*** Все 🔴-строки либо `✅ Resolved`, либо `🟡 Partial`.
- [ ***REMOVED*** Каждая resolved строка содержит дату + ссылку на урок/ADR где применимо.
- [ ***REMOVED*** Summary в §11 (если есть) обновлён: «N из M 🔴 resolved».

---

## 5. Шаг 4 — Добавление LESSONS-записей ([`LESSONS.md`***REMOVED***(LESSONS.md))

### 5.1 Когда добавлять LESSONS-запись

Создавать запись в [`LESSONS.md`***REMOVED***(LESSONS.md) **только** когда ответ клиента выявил **nontrivial** решение/урок. Триггеры:

- ✅ **CON:** ответ клиента подтвердил подход, который полезно цитировать в следующих проектах.
- 🟡 **CAN:** гипотеза (default) подтвердилась клиентом.
- ⚠️ **ANTI:** default оказался неточен — полезный анти-паттерн для следующих проектов.
- 🟠 **PB:** процессный баг — например, ответ потерялся в чате, или клиент отвечал на «wrong» вопрос.

### 5.2 Шаблон CON-записи (наиболее частый случай)

Скопировать блок из [`LESSONS.md`***REMOVED***(LESSONS.md) и заполнить:

```markdown
### CON-NNN: <краткое название урока>
**Дата:** YYYY-MM-DD (дата получения ответа клиента)
**Контекст:** Клиент ответил на Q[N***REMOVED*** в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md); тема — <что спрашивали>
**Следствие:** Что это меняет в [`SPEC.md`***REMOVED***(SPEC.md) §[X***REMOVED***, [`STEPS.md`***REMOVED***(STEPS.md) §[Y***REMOVED***, или в коде

<детальное описание 2-5 предложений>

**Связанные файлы:** [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) §Q[N***REMOVED*** · [`SPEC.md`***REMOVED***(SPEC.md) §11 · (опц.) [decisions/ADR-NNN_*.md***REMOVED***(decisions/ADR-NNN_*.md) · коммит
```

### 5.3 Шаблон ANTI-записи (если default был неточен)

```markdown
### ANTI-NNN: <что default оказалось неточным>
**Дата:** YYYY-MM-DD
**Контекст:** Default в [CLIENT_QUESTIONS_v1.md***REMOVED***(CLIENT_QUESTIONS_v1.md) §Q[N***REMOVED*** — <что предлагали>; клиент дал альтернативу.
**Следствие:** В следующих проектах для схожих Q — **спросить раньше** (на этапе брифа), не угадывать.

<описание 2-5 предложений>

**Связанные файлы:** ...
```

### 5.4 Шаблон CAN-записи (default подтверждён молчанием)

```markdown
### CAN-NNN: Default ХХХ принят клиентом (silence = YYYY-MM-DD)
**Дата:** YYYY-MM-DD (3+ дней после отправки без возражений клиента)
**Контекст:** В [CLIENT_QUESTIONS_v1.md §Q[N***REMOVED******REMOVED***(CLIENT_QUESTIONS_v1.md) был предложен default <описание>; клиент НЕ ответил в течение 3 дней → default применён.
**Следствие:** Проверить, что default не противоречит реальным ожиданиям клиента при первом демо. Если подтвердится → перевод в CON-NNN+1.

<описание 1-3 предложения>

**Связанные файлы:** ...
```

### 5.5 Чек-лист после правки

- [ ***REMOVED*** Нумерация последовательная (`CON-001`, `CAN-002`, и т. д.) — не дублируется с уже существующими.
- [ ***REMOVED*** Каждая запись имеет **дату** + **конкретный след** (что это меняет в коде/SPEC/STEPS).
- [ ***REMOVED*** Cross-links явно указаны.

---

## 6. Шаг 5 (опционально) — Создание условных ADR

> 🟡 **Bootstrap:** если каталог [`decisions/`***REMOVED***(decisions/) отсутствует в проекте (по [`MANIFEST.md`***REMOVED***(MANIFEST.md) — это pending-часть каркаса наряду с `ROADMAP.md` / `RUNNABLE.md` / `CHECKLIST.md`), **сначала** создать:
> 1. `decisions/DECISIONS.md` — индекс ADR с шапкой и кратким описанием формата;
> 2. `decisions/ADR-NNN_<slug>.md` — сам ADR в canonical-формате (**Context / Options / Decision / Rationale / Consequences**).
>
> Только после bootstrap'а каталога — создавать ADR-002 (Python vs PHP) и ADR-003 (Excel schema v1), упомянутые ниже.

### 6.1 Когда создавать ADR

Только если резолюция вопроса требует формального фиксирования design-decision. Триггеры:

| Q | Резолюция триггерит ADR-NNN? | Условие |
|---|:---:|---|
| Q1 (Python vs PHP) | 🔴 да | Всегда (любой ответ фиксируется как ADR-002) |
| Q2 (Excel schema) | 🔴 да | Всегда (спецификация Excel-полей → ADR-003 «Excel schema v1») |
| Q3-Q5 | 🟡 нет | Решение — конкретное значение параметра, не design-decision |
| Q-soft A (гео-координаты) | 🟡 нет | Точечные данные, не design |
| Q-soft B (деплой) | 🟡 нет | Операционный выбор, не design-decision; фиксируется в `RUNNABLE.md` |
| Q-soft C (лицензия) | 🟡 опционально | Если клиент выбрал нестандартную лицензию — может стать ADR-NNN |

### 6.2 Шаблон ADR

См. существующие ADR в проекте. Если проект ещё не имеет ADR-папки, создать `decisions/DECISIONS.md` + `decisions/ADR-NNN_<slug>.md` параллельно с этой процедурой.

Standard ADR structure (Context / Options / Decision / Rationale / Consequences):

```markdown
# ADR-NNN: <slug>

## Context
<что спрашивали у клиента, какой был default и какие альтернативы рассматривались>

## Options
1. <вариант A> (default)
2. <вариант B> (например, PHP)

## Decision
<что выбрал клиент>

## Rationale
<почему клиент выбрал это / техническая обоснованность>

## Consequences
- Обновить [`SPEC.md`***REMOVED***(SPEC.md) §[X***REMOVED***
- [... + ...***REMOVED***
```

---

## 7. Quality checks (финальный чек-лист всей процедуры)

После всех обновлений **обязательно** проверить:

- [ ***REMOVED*** **STEPS.md §0:** все 🔴 закрыты (либо `[x***REMOVED*** ✅`, либо `[ ***REMOVED*** 🟡 partial`); даты и ссылки на ADR присутствуют.
- [ ***REMOVED*** **SPEC.md §11:** таблица обновлена; все hard blockers имеют статус `✅ Resolved` или `🟡 Partial`; каждая resolved строка содержит дату и cross-ref.
- [ ***REMOVED*** **LESSONS.md:** все nontrivial ответы имеют CON/CAN/ANTI запись; нумерация последовательная; cross-links валидны.
- [ ***REMOVED*** **CLIENT_QUESTIONS_v1.md:** bumped to v2; per-Q таблицы заполнены; Header статус обновлён (`🟡` / `🟢`).
- [ ***REMOVED*** **(если применимо) ADR-002 + ADR-003:** созданы; содержат дату клиентского ответа; cross-links на SPEC/STEPS.
- [ ***REMOVED*** **Cross-references consistent:** ссылки между всеми файлами не протухли.
- [ ***REMOVED*** **Бюджет не нарушен:** правки не привели к новым обязательствам сверх 30 000 ₽.

---

## 8. Edge cases (что делать в нетипичных ситуациях)

### 8.1 Клиент молчит >7 дней

- **Day 3:** автоматически применить default (per §2.2 → CAN-запись в LESSONS).
- **Day 7:** отправить polite reminder в Kwork-чате.
- **Day 14:** если нет ответа — формально зафиксировать как «клиент не отвечает» в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md), bump статус до `🟡 Pause` (проект на паузе).

### 8.2 Клиент отвечает на «другую» тему (off-topic)

- Зафиксировать ответ клиента в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) в поле «Комментарии» (любой Q).
- Не использовать этот ответ как resolved — уточнить в follow-up ответе.

### 8.3 Клиент даёт partial ответ (только на Q1, Q3 — без остальных)

- Resolved: Q1, Q3 (статус `✅`).
- Partial: остальные (статус `🟡`, ожидание).
- Header статус: `🟡 Partial→Resolving`.

### 8.4 Клиент даёт ответ, который противоречит locked решению

Locked решения (per [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) §8):

- Decision 1: freeze DB schema до Excel-эталонов (Q2). Если клиент уже прислал эталоны — идём по плану, иначе stop.
- Decision 2: manual `/admin/upload`. Если клиент хочет API — это новый заказ (out-of-scope по 30 000 ₽). Зафиксировать как **ANTI** в LESSONS.

### 8.5 Клиент отвечает устно через голосовое Kwork

- Отправить текстовое уточнение в Kwork-чате: «Подтвердите, пожалуйста, текстом».
- Только после текстового подтверждения фиксировать в [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md).

---

## 9. Временной таймлайн (нормативы)

| Действие | Время | Зависит от |
|---|---:|---|
| Чтение ответа + сопоставление с Q | 5 мин | объём ответа клиента |
| Правка `CLIENT_QUESTIONS_v1.md` per-Q (8 таблиц × ~5 мин) | 30 мин | длина ответа |
| Flip чекбоксов в `STEPS.md` §0 | 5 мин | сложность правки |
| Обновление `SPEC.md` §11 таблица | 10 мин | количество Q |
| Создание LESSONS-записей (CON/CAN/ANTI) | 10–20 мин | nontrivial-ность ответов |
| Условное создание ADR | 30 мин на ADR | design-impact |
| Quality check | 5 мин | — |
| **Итого на 8 Q** | **~1.5–2 ч** | в среднем |

---

## 10. Cross-links (где применять процедуру)

- [`CLIENT_QUESTIONS_v1.md`***REMOVED***(CLIENT_QUESTIONS_v1.md) — Q1..Q5 + Q-soft A/B/C (8 вопросов)
- [`STEPS.md`***REMOVED***(STEPS.md) §0 — чекбоксы ❌/✅ обновляются здесь
- [`SPEC.md`***REMOVED***(SPEC.md) §11 — таблица open questions
- [`LESSONS.md`***REMOVED***(LESSONS.md) — CON/CAN/ANTI/PB журнал (project-local)
- [`decisions/DECISIONS.md`***REMOVED***(decisions/DECISIONS.md) — индекс ADR (завести при первом ADR)
- [`decisions/ADR-NNN_*.md`***REMOVED***(decisions/ADR-NNN_*.md) — отдельные ADR (Context/Options/Decision/Rationale/Consequences)
- [`01_PLAN_BREAKDOWN.md`***REMOVED***(01_PLAN_BREAKDOWN.md) §8 — locked decisions (Decision 1/2/3 — должны оставаться константой)
- [`MANIFEST.md`***REMOVED***(MANIFEST.md) «Открытые вопросы» — после всех правок → «Open Questions closed» (в MANIFEST обновить секцию)

---

## 11. После полного завершения всех правок

После прохождения всех quality checks:

1. Сообщить клиенту в Kwork-чате: «Все блокеры ✅ resolved, начинаем Этап 1.0».
2. Зафиксировать готовность к коду (🟡 → 🟢) в [`MANIFEST.md`***REMOVED***(MANIFEST.md) «Статус (детально)».
3. Старт Этапа 1.0 (Архитектурный шаг) — фиксируется в [`STEPS.md`***REMOVED***(STEPS.md) §1.0 (чекбоксы `[x***REMOVED***`).

---

*Процедурный документ создан: 2026-08-17 · Канон: PROJECT_RULES.md §3 + §4 · Стилевые образцы: lead_aggregator/PHASE1_RESEARCH + core_02/LESSONS · Автор: Buffy (Workspace OS / Freebuff) · Версия: v1*
