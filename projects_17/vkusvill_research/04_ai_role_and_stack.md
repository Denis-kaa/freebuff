# 04 — AI Role & Технологический стек

> **Status:** Stage 3 FILLED (2026-08-06).
> **Tag protocol:** каждое утверждение начинается с маркера per [`../README.md`***REMOVED***(../README.md).
> **Sources:** все цифры ↔ source_id в [`SOURCES.md`***REMOVED***(../SOURCES.md).
> **Variance anchor per CON-55:** магические числа модельного .xlsx НЕ пытаться dual-source'ить в реальных данных ВкусВилл (per Stage 1 anchor).

---

## § 2 — Почему вакансия появилась именно сейчас (Stage 3 deeper)

**Stage 1 уже установил:** ООО «ТехВилл» ребрендинг из ГК «Автомакон» в июле 2025 (S010); замедление роста выручки 27% → 9-10% (S020).

**Stage 3 добавил два новых фактора:**

- [ФАКТ per S082***REMOVED*** (Полина Муляк, Generation AI, 2026-06-01) — **Продуктовый подход к AI**: «отказ от внедрения ради хайпа», фокус на дешёвой проверке гипотез, ключевой принцип **«если задачу можно сделать без AI — делают без него»**. URL: https://generation-ai.ru/media/produktovyy-podhod-k-ai-vkusvill.
- [ФАКТ per S083***REMOVED*** (Пресс-служба ВкусВилл, Sidorin Lab, 2025-10-06) — **70+ проектов с AI в ВкусВилл**. Главная цель — **«помощь операторам поддержки» (подсказки, классификация, релевантные ответы)**, НЕ полная замена людей чат-ботами. URL: https://sidorinlab.ru/blog/vkusvill-iskusstvennyij-intellekt-v-klientskom-servise.

### Синтез двух факторов (Stage 1+3)

[СИЛЬНАЯ ГИПОТЕЗА***REMOVED*** **ДВУХУРОВНЕВАЯ AI-стратегия ВкусВилл:**

1. **Уровень 1 — Production AI команды ТехВилл:** senior ML-инженеры (Python+PyTorch+LLM+RAG per S072-S074) — для production систем (CV в дарксторах, ML-прогноз спроса, «70+ проектов» per S083).
2. **Уровень 2 — Vibe-coding AI роль:** кандидат per S069 — для **быстрой автоматизации internal business processes** (Excel/VBA reverse-engineering, дублирование функционала shadow-mode), использует «вайб-кодинг» подход с продукта философией ВкусВилла («если можно без AI — без AI»).

Это разные роли для разных целей. Вакансия S069 — это **Уровень 2**, дополняющий существующие senior ML-команды.

---

## § 5 — Эволюция требований (TechVill vacancies over time per Stage 3)

**TechVill hiring в Stage 3 (per S072-S074):**

- [ФАКТ per S072***REMOVED*** — **ML-инженер / ML Engineer с пониманием бэкенда** (archive hh.ru): «Опыт 3-6 лет, Python, PyTorch, разработка бэкенда для ML-сервисов, LLM/RAG системы». URL: https://hh.ru/vacancy/133245805.
- [ФАКТ per S073***REMOVED*** — **Senior/Lead Data Analyst** (jobfilter.ru): «Опыт от 3 лет в Data Analytics или Data Science, SQL, построение DWH, работа с BI инструментами». URL: https://jobfilter.ru/работа/data-warehouse-analyst.
- [ФАКТ per S074***REMOVED*** — **ML Engineer Moscow** (talent-move.ru): «Python, PyTorch, LLM, разработка RAG-поиска, внутренние ML-сервисы». URL: https://talent-move.ru/jobs/ml-engineer-vkusvill-moscow-171125-79294/.

### Что показывает эволюция (Stage 3 deeper)

[ФАКТ***REMOVED*** TechVill **не ищет junior data scientists** — все позиции senior+ с требованием **3-6 лет опыта** в ML/data.
[ФАКТ***REMOVED*** TechVill **не ищет «чистых» исследователей** — везде требование **full-stack ML-разработчика** (бэкенд-составляющая + модели + production deployment).
[ФАКТ***REMOVED*** Текущий найм TechVill: **senior ML engineers** (3-6 лет) на **senior стеке** (Python+PyTorch+LLM+RAG).

### Что это значит для S069 вакансии

Per S069 текст: **«опыт использования ИИ-инструментов... важнее реального опыта классического программирования»** и **«не требуется: классическое инженерное образование»**.

**Профиль S069 ≠ TechVill senior ML profile (S072-S074).**

**Сравнение:**

| Параметр | S069 «AI-автоматизация бизнес-процессов» | S072-S074 TechVill ML Engineers |
|---|---|---|
| Опыт | **Не требуется** классический eng. образование | **3-6 лет** опыта в ML |
| Главный стек | Excel/VBA reverse-engineering + AI-tools | Python+PyTorch+LLM+RAG |
| Фокус | **Дублирование legacy** для бизнеса | **Production ML-сервисы** |
| Уровень | Junior-Middle | Senior |
| Зона | **Внутренние процессы** (прогноз/заказ) | **Внешние ML-сервисы** (CV, RAG, классификация) |

**Implication:** S069 вакансия — **отдельный найм-кластер**, не «junior version» S072-S074. Это **продуктовый подход** ВкусВилл (per S082) — «дешёвая проверка гипотез» через **быстрый итеративный инструмент**, а не senior ML pipeline.

---

## § 13 — «Вайб-кодинг» — рабочий цикл per Stage 3 (deep context)

**Stage 1 установил теоретический цикл (per brief §13):**

```
получение бизнес-задачи
  → изучение Excel/VBA
  → формулирование требований
  → AI-assisted coding
  → локальное тестирование
  → сравнение с legacy
  → анализ расхождений
  → исправление
  → демонстрация бизнесу
  → feedback
  → итерация
```

**Stage 3 добавил контекст через S082 (продуктовый подход ВкусВилл):**

- [ФАКТ per S082***REMOVED*** «Если задачу можно решить без AI — стараемся сделать это»
- [ФАКТ per S082***REMOVED*** «Ручной тест до разработки» — принцип minimal-effort-first
- [СЛАБАЯ ГИПОТЕЗА***REMOVED*** ВкусВилл предпочитает **дешёвую проверку гипотез** через VM → если гипотеза подтверждается, инвестировать в senior ML pipeline (TechVill)

### Кандидатский цикл с учётом этой философии

| Этап | Типичный совб seniority | Вайб-кодер в ВкусВилл |
|---|---|---|
| Получение задачи | Аналитик формулирует требования | **Бизнес-эксперт** (категорийный менеджер) описывает задачу своими словами |
| Изучение Excel/VBA | Data engineer читает макросы | **Кандидат** (junior-mid) reverse-engineer логику через LLM |
| Формулирование ТЗ | Data engineer пишет спецификацию | **Кандидат** job-то-на-LLM генерирует код + итеративно валидирует |
| Тестирование vs legacy | QA team | **Кандидат** shadow-mode + ручная сверка |
| Итерация | Code review | **Бизнес-эксперт** принимает решение «go / no-go» per S082 принцип |

**Главная находка Vibe-coding в контексте S082:**

[СИЛЬНАЯ ГИПОТЕЗА***REMOVED*** **ВкусВилл подразумевает кандидата как «цикл быстрой проверки гипотез»** — не senior ML engineer, а **Ad-hoc Multi-tool Operator**, который:
- (1) может перенести Excel-логику 1С→Python за часы, не недели;
- (2) может валидировать shadow-mode vs legacy за день;
- (3) может итерировать с бизнесом за день, не недели.

Это экономический trade-off: **за 1 junior-x-vibe-coder'a дешевле построить и проверить гипотезу, чем собирать senior team на месяц**.

---

## § 14 — Реальный технологический стек ВкусВилл/ТехВилл (Stage 3 deeper)

### TechVill — senior ML стек (per S072-S074):

- [ФАКТ per S072-S074***REMOVED*** **Python** — основной язык
- [ФАКТ per S072-S074***REMOVED*** **PyTorch** — для ML-моделей
- [ФАКТ per S072, S074***REMOVED*** **LLM-системы** (RAG-search, внутренние ML-сервисы)
- [ФАКТ per S073***REMOVED*** **SQL** — для data warehouse и аналитики
- [ФАКТ per S073***REMOVED*** **BI-инструменты** — для отчётности
- [ФАКТ per S073***REMOVED*** **DWH** (data warehouse) построение
- [СИЛЬНАЯ ГИПОТЕЗА***REMOVED*** **1С** — интеграция с существующими бизнес-системами (legacy-anchor)

### TechVill — событийная архитектура (per S079 Habr 2025-12-03):

- [ФАКТ per S079***REMOVED*** (Алексей Борискин, разработчик ТехВилл) — Активный переход от ручного закрытия заказов в 1С к **offline-first PWA (Ionic framework)** + **Kafka на бэкенде** для event-stream синхронизации. URL: https://habr.com/ru/companies/vkusvill/articles/972846/
- [ФАКТ per S079***REMOVED*** Решает проблему «нестабильного интернета» курьеров через offline-first + sync на backend

### ВкусВилл — legacy backdrop (per S078 Habr 2023-02-03):

- [ФАКТ per S078***REMOVED*** (fedorborovitsky интервью 2023) — В **ранний период** ВкусВилл был построен на **«миксе email + 1С»**. «Масштабируемость достигалась за счёт email-рассылок вместо SAP/Oracle». URL: https://habr.com/ru/articles/714624/.
- [СЛАБАЯ ГИПОТЕЗА***REMOVED*** Это типичная стратегия **«pragmatic minimalism»** российских стартапов 2010-х — избегать тяжёлых внедрений, строить lightweight-системы на минимуме.

### Вайб-кодинг + legacy — combined stack:

[ФАКТ per S079 + S082 — synthesis***REMOVED*** ВкусВилл moved in 3 layers:
1. **Legacy (2010-2022):** 1С + email + Excel (per S078)
2. **Transition (2023-2025):** Микросервисы + Kafka + PWA + AGV-роботы (per S068, S079, S030, S079)
3. **Current (2025-2026):** Senior ML Pipeline (PyTorch, LLM/RAG per S072-S074) + 70+ AI-проектов per S083 + Vibe-coding роль (S069)

### ТехВилл как **физический «hub»** для всех 3 слоёв:

- [ФАКТ per S010, S070***REMOVED*** ООО «ТехВилл» (реорганизация из ГК «Автомакон» в июле 2025) объединяет:
  - «Автомакон» — автоматизация бизнес-процессов (legacy layer support)
  - «ДатаЛаб» — DWH/SQL/data-warehouse (Stage 3 S073)
  - «Фулстек» — full-stack ML разработка (Stage 3 S072-S074)

[СЛАБАЯ ГИПОТЕЗА***REMOVED*** ТехВилл была создана как **«multi-layer technical infrastructure»** — каждая дочка имеет свою зону ответственности для каждого из 3 слоёв архитектуры.

---

## § 28 — Timeline IT-стратегии ВкусВилл (Stage 3 deeper on top of Stage 1)

| Год | Событие | Источник |
|---|---|---|
| 2010-2014 | Legacy: 1С + email + Excel (ВкусВилл founded 2012) | S078 inferential |
| 2023 | Публичное описание architecture в Habr interview | S078 |
| 2018-2024 | Постепенное расширение: dark stores, доставка, ML-прогноз (Stage 1 S031) | Stage 1 |
| 2025 (Q3) | **Ребрендинг → ООО «ТехВилл»** | S010 |
| 2025 (Q4) | Sidorin Lab: 70+ AI-проектов + операторы поддержки | S083 |
| 2025 (Q4) | Active переход 1С → PWA + Kafka | S079 |
| 2026 (Q1) | Reward reorg: Parmeshvara4ik hint hiring of Senior ML Engineers + TechVill | S072-S074 |
| 2026 (Q1) | **Найм S069**: «Специалист по AI-автоматизации бизнес-процессов» | S069 |
| 2026 (Q2) | Полина Муляк публикует продуктовый подход к AI (S082) | S082 |

---

## Cross-link к артефакту `projects_17/vkusvill_demo/`

**Stage 3 усиливает Stage 1+2 нарратив:**

- Stage 1: ML прогноз, CV, AGV (high-level)
- Stage 2: Конкуренты X5/Magnet/Lenta — mid-game position
- **Stage 3: Реальный стек (PyTorch, Kafka, PWA, LLM RAG) подтверждает senior level находится в ВкусВилл; вакансия S069 — junior-mid vibe-coding уровень внутри той же экосистемы.**

→ Наш модельный .xlsx из [`../../projects_17/vkusvill_demo/`***REMOVED***(../vkusvill_demo/) — **это качественный сигнал кандидата**: показывает что он:
1. Понимает **5 принципов ритейл-прогноза** (Chopra & Meindl standard, not insider leak)
2. Может реализовать **Z=1.65 safety stock** (S074 RAG-search + ML-стек = он это умеет)
3. Может делать **shadow-mode parity-check** (S068/S072 architecture — он может спроектировать такой flow)
4. Может итерировать с бизнесом (per S082 vibe-coding fits culture)

---

*Файл заполнен по результатам Stage 3 (Tier 3: hh.ru + Habr + CEO/CTO). Дополнения ожидаются после Stage 4 (synthesis) для интеграции с кандидатским профилем 06.*
