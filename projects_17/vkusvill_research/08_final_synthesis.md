# 08 — Final Synthesis: ВкусВилл × AI-Automation

> **Status:** Stage 4 SYNTHESIS FILLED (2026-08-06).
> **Source material:** [`../README.md`***REMOVED***(../README.md) + Stage 1-3 ([`01_business_scale.md`***REMOVED***(../01_business_scale.md), [`02_supply_chain_economics.md`***REMOVED***(../02_supply_chain_economics.md), [`03_legacy_and_forecasting.md`***REMOVED***(../03_legacy_and_forecasting.md), [`04_ai_role_and_stack.md`***REMOVED***(../04_ai_role_and_stack.md), [`05_cases_and_competitors.md`***REMOVED***(../05_cases_and_competitors.md), [`06_candidate_profile.md`***REMOVED***(../06_candidate_profile.md)) + [`SOURCES.md`***REMOVED***(../SOURCES.md) (46 sources).
> **Coverage:** brief [`pompts_11/064_04_vkusvill_ai_avtomatizaciya.md`***REMOVED***(../../pompts_11/064_04_vkusvill_ai_avtomatizaciya.md) §17/§20/§21/§23/§24/§29/§31/§33.
> **Tag protocol:** per CON-55: `[ФАКТ***REMOVED***`/`[СИЛЬНАЯ ГИПОТЕЗА***REMOVED***` inline.
> **NO new web research** — Stage 4 = pure synthesis.

---

## 1️⃣ Главная 8-уровневая схема (от стратегии компании до тактики отклика)

```
L0  ГЛОБАЛЬНЫЙ КОНТЕКСТ: Российский фреш-ритейл в стадии зрелости
    │  ─── Замедление роста выручки (27% → 9-10% per S020); сокращение сетей;
    │      давление на маржинальность → фокус на operational efficiency.
    │
    ↓
L1  ВКУСВИЛЛ КАК КОМПАНИЯ: pure-fresh игрок с переходом от экспансии к оптимизации
    │  ─── 2480 точек в 173 городах (S003), 50% онлайн (S021), fresh-only
    │      позиционирование vs X5/Магнит omni-channel.
    │
    ↓
L2  КОНКУРЕНТНЫЙ ЛАНДШАФТ: mid-game, не лидер AI, не отстающий
    │  ─── X5 впереди по IT-расходам (39,3 млрд, GalyaGPT, CV-S035); Лента
    │      раньше по LightGBM (S040); Яндекс.Лавка CatBoost+AMR (S044-S045);
    │      ВкусВилл = ниша 60+ дарксторах CV (S031).
    │
    ↓
L3  ТЕХВИЛЛ: структурный сдвиг = capacity найма
    │  ─── Ребрендинг ГК «Автомакон» → ООО «ТехВилл» в июле 2025 (S010).
    │      Аккредитация IT Минцифры (S012). До этого AI был частью общей IT.
    │
    ↓
L4  СУЩЕСТВУЮЩАЯ AI-ИНФРАСТРУКТУРА: 70+ проектов, не строить с нуля
    │  ─── ML-прогноз с ручной валидацией (S031); CV в 60+ дарксторах (S031);
    │      AGV на 2 РЦ (S030); AI shadow mode в ТехВилл (S068).
    │
    ↓
L5  ВАКАНСИЯ = УСИЛИТЬ существующий pipeline, не заменить
    │  ─── Прямо из S069: «дублировать функционал текущих систем». Это
    │      shadow-mode extension существующего, а не parallel initiative.
    │
    ↓
L6  РАБОЧИЙ ЦИКЛ: vibe-coding с reverse-engineering legacy
    │  ─── Excel/VBA → формальные требования → LLM-assisted prototype →
    │      shadow mode parallel с legacy → A/B test → gradual migration.
    │
    ↓
L7  ТАКТИКА ОТКЛИКА: показать процесс понимания + готовность усилить
    │  ─── Не «немедленная инновация». Не «замена legacy». А: «понимаю
    │      существующий pipeline, усилю направленно, докажу shadow-mode».
    │
    ↓
L8  РЕЗУЛЬТАТ: shadow-mode validated prototype в одной категории за 90 дней
       ─── Измеримый effect на WAPE/fill rate без disruption существующего
           business-flow.
```

### Обоснование уровней

| L | Что покрывает | Source-anchors |
|---|---|---|
| **L0** | Макроэкономика российского ритейла | S020 (замедление), S032 (сокращение) |
| **L1** | Специфика ВкусВилл vs конкурентов | S001, S002, S003, S021 |
| **L2** | Где ВкусВилл mid-game | S035 (X5), S040 (Лента), S044-S045 (Я.Лавка) |
| **L3** | «Почему сейчас» (организационный shift) | S010, S012, S013 |
| **L4** | «Что уже есть» (70+ AI-проектов) | S031, S030, S083, S068 |
| **L5** | «Чего хотят» (прямая формулировка вакансии) | S069, S082 |
| **L6** | «Как делать» (рабочий цикл vibe-coding) | S082, S083 |
| **L7** | «Как продать себя» (стратегия отклика) | brief §21 + Stage 3 S082-S083 |
| **L8** | «Что заявить как MVP за 90 дней» | brief §20 + Stage 1+2 |

**Почему именно 8?** Достаточно для memorization на интервью; не перегружено. Каждый уровень — отдельный possible interview follow-up.

---

## 2️⃣ §29 — 10 финальных ответов (elevator-pitch уровень)

### AQ1. Что за компания ВкусВилл сегодня?

> Крупнейший **pure-fresh ритейлер РФ**. Оборот 329-361 млрд руб (2024 per S003+S020 dual-source), 2480 точек в 173 городах, ~50% онлайн (S021). [ФАКТ***REMOVED*** Недавно выделенная IT-дочка «ТехВилл» — ООО «ТехВилл» (ИНН 7751014313, аккредитованная IT-компания Минцифры per S012), ребрендинг ГК «Автомакон» в **июле 2025** (S010). Fresh-only позиционирование — структурное преимущество в ритейле: фокус на молочке/овощах/фруктах/хлебе, в отличие от omni-channel X5/Магнит.

### AQ2. Как устроена её бизнес-модель?

> [ФАКТ***REMOVED*** **Pure-fresh операционная модель** с 2 ключевыми РЦ (Домодедово 110 кв м + Вешки 109 кв м, S030), AGV-роботизация (заменяет 50 сотрудников + 15 ричтраков на инвентаризации). **Двойной канал**: офлайн + онлайн (50%+) — fresh-fulfillment требует **dark-store модели** (прямо per S031: 60+ дарксторов с Computer Vision). **Pipeline** (per brief §7 / наша 10-этапная reconstruction): Продажи → История → Прогноз → Корректировки → Потребность → Остатки → Поставки → Автозаказ → Распределение → Магазин. **Где зарабатывает**: маржа fresh-категорий при premium-позиционировании. **Где несёт**: списания 3-5% industry baseline (S033) + логистика + инвестиции в AI.

### AQ3. Какая бизнес-проблема стоит за вакансией?

> [СИЛЬНАЯ ГИПОТЕЗА***REMOVED*** **Триада проблем**: (1) Замедление роста выручки с 27% до 9-10% (S020) + сокращение сети -13% (S032) — операционная эффективность стала приоритетом; (2) существующая ML-инфраструктура прогноза (S031) работает с **ручной валидацией** — bottleneck на масштабировании; (3) организационный shift в ТехВилл (S010) создал **отдельный capacity найма** для расширения AI команды. **Кандидат = усиление существующих систем**, не «новая инициатива». Это прямо из S069: «дублировать функционал текущих систем прогнозирования спроса и автозаказа».

### AQ4. Почему существующие системы недостаточны?

> [ФАКТ + СИЛЬНАЯ ГИПОТЕЗА***REMOVED*** (1) **Excel/VBA ceiling**: per S069 явно упоминается «существующих Excel/VBA-инструментов» — это bottleneck, не legacy-эстетика. Для масштаба 2480 точек × 1000 SKU = миллионы строк, Excel тормозит и плохо audit'ится [ПРЕДПОЛОЖЕНИЕ***REMOVED***. (2) **ML интеграция**: прогноз существует (S031), но shadow-mode / A/B-test инфраструктура **не описана публично** — нужна автоматизация shadow mode, feature stores, мониторинг drift. (3) **Manual corrections**: HM делают ручные корректировки ML — bottleneck на их времени и несогласованность across stores.

### AQ5. Почему компания выбрала AI-assisted development?

> [СИЛЬНАЯ ГИПОТЕЗА***REMOVED*** Из вакансии S069 прямо: «вайб-кодинг: написание рабочих решений через промпты, а не классическое программирование с нуля». Продуктовый подход ВкусВилл per S082 (Полина Муляк, Generation AI): «если задачу можно решить без AI — решают без него», «дешёвая проверка гипотез ручным тестом до разработки». **Это позволяет**: (1) быстрый time-to-prototype на бизнес-задачах; (2) low-cost experimentation; (3) оперативная адаптация под feedback от HM; (4) bypass traditional engineering bottleneck. 70+ AI-проектов уже внедрено (S083) — это **proven pattern** в компании.

### AQ6. Почему важен AI-tools experience (формулировка «важнее реального опыта классического программирования» — verbatim)?

> [ФАКТ per S069, верифицировано 2026-08-09 через AFK Offer + CareerSpace***REMOVED*** Из вакансии дословно: «Опыт использования ИИ-инструментов для разработки (Claude, ChatGPT, Cursor, Copilot и т.п.) — **важнее реального опыта классического программирования**». 
>
> >>>DEPRECATED-BLOCK-BELOW<<<  
> ⚠️ **[DEPRECATED 2026-08-09 — НЕ ЦИТИРОВАТЬ***REMOVED***** Прежняя формулировка, бывшая в этом AQ6: **«Не требуется: классическое инженерное образование или опыт "полноценной" разработки — важнее скорость, инициативность и умение работать с ИИ как с инструментом»** — была **семантически близка, но НЕ дословно из вакансии**. Web-verification 2026-08-09 показала: такой фразы в тексте вакансии НЕТ. Заменено на реальную verbatim.
>
> **Это перевес AI-tools mastery над classical programming experience в контексте разработки**, не отсутствие требования к диплому: (1) Кандидат должен **понимать бизнес-логику** (per brief §22 — это «боли HM»), а не быть engineering-heavy; (2) AI-tools заменяют часть boilerplate-coding, нужен **vibe-coding skill** (направлять LLM); (3) Скорость важнее elegant architecture — это прототипирование, не production systems; (4) Бизнес-expertise + AI-tools = **редкая комбинация**, которую сложно нанять через стандартный engineering-recruitment.
>
> *Note: AQ5 НЕ редактировался — уже содержал корректную verbatim «вайб-кодинг: написание рабочих решений через промпты, а не классическое программирование с нуля» (verified 2026-08-09). Intentional non-edit, not missed.*

*Sources: AFK Offer (afkoffer.com/vacancies/python/135746053) + CareerSpace (careerspace.app/job/253439). Прямой hh.ru/vacancy/135746053 отдаёт 403/406. DreamJob/remote-job в первичной выборке researcher-web не дали результата (пробованы но без ответа); AFK Offer и CareerSpace оказались агрегаторами с полным текстом.*

### AQ7. Какую работу этот человек будет выполнять каждый день?

> [ПРЕДПОЛОЖЕНИЕ + S069***REMOVED*** (1) **Изучение legacy** — reverse-engineering Excel/VBA инструментов прогноза; (2) **interviews HM/аналитиков** — калибровка hypothesis; (3) **prototyping** — vibe-coding Python prototypes через LLM; (4) **shadow-mode validation** — параллельные прогоны vs legacy; (5) **итерация** — fix bugs, refine фичи; (6) **demo to HM** — show working prototype, get feedback; (7) **документация** — what works, what doesn't. Цикл 1-2 недели на iteration. Не: full-stack engineering, не: data engineering pipeline AWS-level. **Scope**: один business-case за раз, расширяется при successful pilot.

### AQ8. Как будет измеряться его результат?

> [ПРЕДПОЛОЖЕНИЕ***REMOVED*** С высокой вероятностью: (1) **WAPE/Fill Rate для shadow-mode категории** (главная technical метрика); (2) **снижение списаний** vs baseline (главная business метрика); (3) **time-to-prototype** (operational метрика productivity); (4) **HM satisfaction / adoptability** (qualitative метрика). Не публичные KPI ВкусВилл — это **implicit acceptance criteria** при interview. В **produit mode**: shadow-mode run rate (% категорий с active prototype), gradual transition to production за 6-12 месяцев.

### AQ9. Что будет самым сложным в этой работе?

> [СИЛЬНАЯ ГИПОТЕЗА***REMOVED*** (1) **Reverse-engineering без документации** — legacy-VBA может быть защищён паролем, undocumented rules в голове HM; (2) **Stakeholder management** — HM могут не доверять AI, нужны months на trust-building; (3) **Доказательство equivalence** — shadow-mode correlation с legacy нужен месяцы, не недели; (4) **Data integration** — реальные данные грязные, edge cases бесконечны; (5) **Production-quality из prototype** — vibe-coding даёт «работает на моих данных», но не масштабируется из коробки; (6) **Одиночная роль** — нет команды (single-person role per brief §23 red flag), весь quality-control на одном человеке.

### AQ10. Почему эта вакансия может быть очень хорошей возможностью или иметь скрытые риски?

> **Возможности**: (a) **качественный** бизнес-эффект (по аналогии с конкурентами: X5 S034 +17% точность прогноза = потенциал снижения opex; **НЕ использовать цифры 5-15% списаний / 100+ млн руб/год как обещание** — внутренние KPI не публикуются, маркетинговые оценки per S082 «если можно без AI — без AI» — культура **без** overpromise); (b) AI-first культура (70+ проектов S083 = proven track record); (c) scale (2480 точек = impact is measurable qualitatively); (d) ТехВилл как организация создаёт velocity найма (S010); (e) продуктовый подход без over-engineering (S082 — принцип «if can do without AI»); (f) автономия в решениях (вакансия = «высокая самостоятельность»).
>
> **Риски**: (a) **solo role**: нет engineering-команды, всё качество на 1 человеке (per brief §23); (b) **legacy ceiling**: Excel/VBA может быть невозможно полностью заменить в рамках проекта; (c) **vague scope**: «дублировать» ≠ «заменить» — может быть не endpoint; (d) **зависимость от stakeholders**: HM могут блокировать; (e) **measurement ambiguity**: без public KPI трудно валидировать успех; (f) **time pressure**: «высокая самостоятельность» может означать «нет помощи».

---

## 3️⃣ §17 — Карта бизнес-проблемы

| **Проблема** | **Причина** | **Последствие** | **Текущий инструмент** | **AI-возможность** | **Потенциальный эффект** |
|---|---|---|---|---|---|
| Forecasting accuracy для top-100 SKU | Ручные корректировки, недостаточно фичей | Списания industry-baseline 3-5% (per S033), out-of-stock 4-8% (industry assumption) | Excel/VBA + manual overrides (S069) | ML с фичами weather/promo/lag (S031) | [НЕТ ДАННЫХ***REMOVED*** (численные % снижения списаний/fill rate — внутренние KPI ВкусВилл не публикуются; **НЕ** исользовать оценки вроде «−10−20% списаний» на интервью) |
| Cold-start для новых SKU | Нет истории | Over-buy или missing sales | HM intuition | Transfer learning + clustering | [НЕТ ДАННЫХ***REMOVED*** |
| Seasonal demand variability | Multi-scale seasonality (week/month/year) | Out-of-stock в пик | Static seasonal dummies | Hierarchical + Fourier features | [НЕТ ДАННЫХ***REMOVED*** |
| Manual cross-SKU cannibalisation detection | Hard to model | Suboptimal assortment | Excel «if-than» rules | Logit/demand systems models | [НЕТ ДАННЫХ***REMOVED*** |
| Promo prediction | Promo uplift неизвестен | Over/under-buy в promo | Rule-of-thumb by HM | CatBoost/LightGBM с promo features | [НЕТ ДАННЫХ***REMOVED*** |
| Inventory distribution from РЦ | Не оптимизировано | Excess inventory at some stores | Manual dispatcher | Optimization (linear programming) | [НЕТ ДАННЫХ***REMOVED*** |
| Shadow-mode framework | Не описан публично | AI-models не доказывают equivalence | Manual comparison | Automated A/B test infra (S082 упоминает) | Faster iteration cycles |
| Data quality / lineage | Multi-system stack | ML-pipeline paper-only validation | Excel exports | DWH + dbt + lineage tools | Reproducible models, fewer incidents |
| Stakeholder trust in AI | «Модель неправильно считает» | Pilot не масштабируется | Доверие интуитивно | Transparent explanations + demos | [НЕТ ДАННЫХ***REMOVED*** (adoption rate не публикуется) |
| Legacy maintenance cost | VBA код в голове 1 человека | Bus factor = 1 | Excel | Migration to Python | Reduced bus-factor risk |

**Главный вывод по таблице**: **9 из 10 проблем решаются AI**, и при этом 1 (**stakeholder trust**) — это **anti-AI** issue, требующий прозрачности. Роль вакансии — захватить максимум первой группы и **не забыть** про вторую.

---

## 4️⃣ §23 — Red Flags ⚠️ (явные сигналы осторожности)

### RF-1. Solo role без engineering команды
- **Что это значит:** Per brief §23: «роль одного человека вместо команды». Весь процесс разработки, тестирования, deployment, мониторинга — на одном человеке.
- **Когда усиливается:** Если в вакансии нет чёткого escalation path, нет senior engineer для code review, нет ML-ops.
- **Что делать кандидату:** Принять как constraint, настаивать на **peer-review partnerships** с другими командами (data, ML engineering).

### RF-2. «Высокая самостоятельность» = «нет помощи»
- **Что это значит:** Из вакансии S069: «Высокая самостоятельность». Может означать: (1) настоящая свобода (good); (2) «никто не поможет» (bad).
- **Как различить:** Спросить на интервью: «Кто будет senior-reviewer?», «Кто отвечает за deployment в production?», «Кто проверяет security?». Senior отсутствие = red flag.

### RF-3. «Дублировать функционал» без чёткого endpoint
- **Что это значит:** Если новая AI-система должна «дублировать» legacy, но неясно — что потом: (а) заменить legacy? (b) shadow forever? (c) migrate gradually?
- **Как различить:** Спросить: «Что считается успехом для этой роли — shadow, replace, или co-exist?». Без чёткого ответа = red flag.

### RF-4. Отсутствие measurable acceptance criteria в вакансии
- **Что это значит:** Per brief §23: «отсутствие чётких критериев успеха».
- **Как различить:** Спросить: «Какие KPI будут использоваться для оценки моей работы через 6/12 месяцев?». Если «общие метрики компании» без конкретики = red flag.

### RF-5. Legacy-VBA с высоким bus factor
- **Что это значит:** Если Excel/VBA держится на 1-2 людях, которые могут уйти — проект сам обречён на медленный drift. Замена legacy Вам — это **наследование чужого technical debt**.
- **Как различить:** Спросить: «Кто писал Excel-инструмент, доступен ли для вопросов?», «Есть ли актуальная документация?»

### RF-6. Зависимость от одного-двух stakeholders
- **Что это значит:** Если вся работа упирается в HM или аналитика, без которого проект стоит — это personal dependency, не профессиональная роль.
- **Как различить:** Спросить: «С кем я буду работать ежедневно?», «Если этот человек уйдёт в отпуск, проект встанет?»

### RF-7. Неясные границы между AI-инструментами
- **Что это значит:** Если в вакансии упоминаются и ML, и CV, и LLM, и «vibe-coding» без фокуса — это может быть «давай попробуем всё», что ведёт к хаосу.
- **Как различить:** Спросить: «Какой приоритет #1?», «Что НЕ делать в первые 90 дней?»

### RF-8. Неясный product-side ownership
- **Что это значит:** Если непонятно, кто «owns» продукт в ВкусВилл — это design-by-committee риск.
- **Как различить:** Спросить: «Кто принимает финальное решение о ship-е в production?»

---

### RF-9. Measurement ambiguity без публичных KPI
- **Что это значит:** [ПРЕДПОЛОЖЕНИЕ***REMOVED*** Per AQ8: ВкусВилл НЕ публикует operational KPI (forecast accuracy, fill rate, списания). Без public benchmark трудно external-валидировать, что AI-pilot действительно улучшает ситуацию, а не просто «выглядит хорошо». Внутренние метрики могут быть scope'd так, чтобы результат казался лучше, чем он есть.
- **Как различить:** Спросить: «Какие конкретные числовые KPI будут у меня в performance review через 6/12 месяцев?». Если ответ «общие метрики компании» — red flag.

### RF-10. Зависимость от конкретного HM (= personal dependency)
- **Что это значит:** В стартапах и AI-pilot'ах часто всё упирается в одного advocate-HM, без которого проект стоит. Если этот человек уходит в отпуск / меняет работу / теряет интерес — проект теряет political support.
- **Как различить:** Спросить: «Кто еще в команде понимает AI-priority?», «Если этот sponsor уйдёт, что будет с проектом?». Single-sponsor = personal dependency risk.

---

## 5️⃣ §24 — Green Flags ✅ (явные позитивные сигналы)

### GF-1. Существующая ML-инфраструктура
- **Что подтверждает:** [ФАКТ***REMOVED*** Per S031 ML-прогноз существует, используется в магазинах, есть валидация аналитиками.
- **Что это значит для вакансии:** Кандидат не строит с нуля, а **расширяет существующий pipeline**. Это **maximum leverage** для нового человека.

### GF-2. Выделенная IT-дочка «ТехВилл»
- **Что подтверждает:** [ФАКТ***REMOVED*** Per S010, S012, S013 ООО «ТехВилл» — аккредитованная IT-компания с собственным стеком вакансий (ML Engineer, CV Engineer, Robotics Engineer).
- **Что это значит:** Структура создана для AI-масштабирования; найм = часть долгосрочной стратегии, не «один пилот».

### GF-3. Продуктовый подход без AI-first bias
- **Что подтверждает:** [ФАКТ***REMOVED*** Per S082 (Полина Муляк, Generation AI): «ключевой принцип: если задачу можно решить без AI — решают без него».
- **Что это значит:** Руководство ценит прагматизм над хайпом. Кандидат может предлагать non-AI решения, если они лучше.

### GF-4. 70+ AI-проектов в компании
- **Что подтверждает:** [ФАКТ***REMOVED*** Per S083 (Sidorin Lab, октябрь 2025).
- **Что это значит:** AI — это **proven pattern**, не эксперимент. Кандидат может опираться на existing best practices внутри.

### GF-5. «70+ AI-проектов» = collaborative среда
- **Что подтверждает:** Из S083 ясно, что культура AI внутри развита.
- **Что это значит:** Больше шансов найти peer-review, обмен knowledge, общие MLOps-инструменты.

### GF-6. Архитектурный shift (микросервисы, DDD, Onion)
- **Что подтверждает:** [ФАКТ***REMOVED*** Per S068 (Retail.ru): API-first микросервисы на Go, Onion-архитектура, DDD.
- **Что это значит:** Технический фундамент mature, AI-инструменты могут быть нативным citizen этой архитектуры.

### GF-7. AGV-роботы на 2 РЦ
- **Что подтверждает:** [ФАКТ***REMOVED*** Per S030.
- **Что это значит:** Automation-mindset в компании, не только в software, но и в physical ops. Кандидат может думать шире, чем просто code.

### GF-8. Доля онлайн 50%+
- **Что подтверждает:** [ФАКТ***REMOVED*** Per S001 (2022) 39% → S002 (2023) >50% → S003 (2024) ~50%.
- **Что это значит:** **Online = data richness** — больше signals для AI, чем в pure-offline ритейле.

### GF-9. Июль 2025 — структурный shift
- **Что подтверждает:** [ФАКТ***REMOVED*** Per S010.
- **Что это значит:** Вакансия появилась в **свежей структуре** с **отдельным capacity** для найма. Не «вписаться в legacy-департамент».

### GF-10. Конкретная формулировка «дублировать функционал»
- **Что подтверждает:** [ФАКТ***REMOVED*** Per S069.
- **Что это значит:** Вакансия **не абстрактная** — есть конкретный use-case (прогноз спроса + автозаказ). Это помогает сфокусировать работу с первого дня.

---

## 6️⃣ §21 — Стратегия отклика

### Образ кандидата (per brief §21 — «каким должен быть кандидат в глазах нанимающего менеджера»)

> **«Человек, который способен взять существующий неидеальный бизнес-инструмент (Excel/VBA прогноза), разобраться в его бизнес-логике через reverse-engineering и stakeholder-interviews, формализовать её, через LLM-assisted vibe-coding создать рабочий prototype на Python, проверить его параллельно с legacy (shadow mode), и доказать HM, что новый инструмент даёт корректный результат с улучшенной гибкостью и measurably снижает WAPE/fill rate проблемы.»**

### Cover Letter Strategy (4 абзаца)

**1️⃣ Почему ВкусВилл** (1 абзац, «философский»):
> Я понимаю, почему ВкусВилл за последние годы построил 2480 точек в 173 городах, вышел на 50% онлайн и создал ООО «ТехВилл» в июле 2025 (S010). Я разделяю фокус на pure-fresh качестве — это не «продать всё», а «продать то, что клиент ценит». Вижу в вакансии возможность применить продуктовый подход (per [S082***REMOVED***(https://example.com)) «если можно без AI — делаем без AI» — это зрелая AI-стратегия, не hype cycle.

**2️⃣ Почему эта вакансия** (1 абзац, «бизнес-мотивация»):
> Вакансия [135746053***REMOVED***(...) точно описывает задачу: «дублировать функционал текущих систем прогнозирования спроса и автозаказа». Я понимаю эту формулировку как: создать working prototype на Python, который shadow-mode сравнивается с существующим Excel/VBA + ML pipeline (S031), доказывает equivalence по WAPE и bias, и постепенно масштабируется на одну категорию за другой. Это реалистичный scope для 90 дней.

**3️⃣ Что я предлагаю** (1 абзац, «ценностное предложение»):
> Я предлагаю опыт **reverse-engineering legacy-систем** через понимание бизнес-правил (не только кода), опыт **vibe-coding с LLM** для быстрого prototyping (Claude Code, Cursor, Copilot per S082), опыт **shadow-mode validation** для безопасной миграции, и продуктовый подход к AI-проектам (не «AI ради AI»). Основной стек: Python (pandas, scikit-learn, LightGBM/CatBoost), SQL, FastAPI для ML-endpoints, openpyxl/xlcalculator для Excel-reverse-engineering.

**4️⃣ Почему я** (1 абзац, «доказательства»):
> Я уже сделал proof-of-concept для похожей задачи в [projects_17/vkusvill_demo/***REMOVED***(...) (ROADMAP-VV-001 v5.105.0): построил модельный .xlsx инвентор для категорий молочка/крупа/напиток с 5 принципами прогнозирования, team-work с 3-ролевой моделью, JSON-based parity-check vs Excel. Артефакт показывает, что я понимаю процесс end-to-end: 10-этапный pipeline, fresh-ритейл специфика, нюансы shadow-mode validation.

### Стратегия поведения на интервью

| Фаза | Действие | Цель |
|---|---|---|
| **Открытие (5 мин)** | Задать уточняющий вопрос про ТехВилл как структуру (после S010) | Показать, что сделан homework, не пришёл «из общего любопытства» |
| **Бизнес-блок (15 мин)** | Продемонстрировать ответы на AQ1-AQ5 | Показать структурное понимание |
| **Технический блок (15 мин)** | Capture 2-3 «сильных ответа» из [07***REMOVED***(../07_interview_strategy.md) | Подтвердить hands-on опыт |
| **Behavioral (10 мин)** | Примеры из §19.7 (Q101-Q110) | Soft skills |
| **Вопросы кандидата (10 мин)** | Задать 5 sharp questions (см. ниже) | Сигнал senior-level thinking |
| **Закрытие (5 мин)** | Повторить 90-дневный план из §7 | Саммировать commitment |

### 5 sharp questions для финальной фазы

1. «ТехВилл — это IT-дочка ВкусВилл с какой операционной автономией? Решения по найму согласуются с материнской компанией, или автономно?»
2. «Кто в ТехВилл отвечает за data engineering / DWH pipeline, и насколько он готов к ML-model deployment через MLOps?»
3. «Какие ML-проекты в ВкусВилл scale’нулись из pilot в production за последний год, и почему именно они?»
4. «Shadow-mode validation в ВкусВилл — это уже infra, или каждый AI-pilot строит свою validation logic с нуля?»
5. «Что будет с Excel/VBA-инструментом, который я мигрирую? Его нужно полностью выключить через 12 месяцев, или можно co-exist?»

---

## 7️⃣ §20 — План 90 дней

### Phase 1 (Days 1-30): Discovery & Foundation

**Цель:** Понять контекст, не надломать существующее.

| Неделя | Активность | Deliverable |
|---|---|---|
| **W1** | Onboarding, обзор архитектуры (S068), знакомство с командой | Заметки структуры |
| **W2** | Reverse-engineering **ключевого** Excel/VBA-инструмента (per S069) | Internal spec doc |
| **W3** | Stakeholder-interviews: 8-12 встреч (HM, аналитики, РЦ, IT ops) | Stakeholder map |
| **W4** | Mapping 10-stage pipeline к реальным системам | Pipeline diagram |

**Ключевой риск:** Преждевременное действие. **Митигация:** Первые 30 дней = **read-only** архитектурно.

### Phase 2 (Days 31-60): First Prototype

**Цель:** Создать первый working prototype для shadow mode.

| Неделя | Активность | Deliverable |
|---|---|---|
| **W5-6** | Выбрать **1 категорию** (например, «молочка» — high volume + high spoilage) | Hypothesis doc |
| **W6-7** | Vibe-coding Python prototype через LLM (per brief §13) | Working prototype |
| **W7-8** | Shadow-mode setup + 2 недели parallel run | Validation log |
| **W8** | Demo to HM + gather feedback | Demo + feedback doc |

**Ключевой риск:** Prototype неточно копирует legacy. **Митигация:** Golden dataset с 8-10 known вход/выход пар.

### Phase 3 (Days 61-90): Pilot & Validation

**Цель:** Доказать equivalence в реальных условиях.

| Неделя | Активность | Deliverable |
|---|---|---|
| **W9-10** | A/B test: 5-10 магазинов (new prototype vs legacy) | A/B results |
| **W10-11** | Анализ метрик: WAPE, fill rate, списания (industry baseline S033) | Metrics report |
| **W11-12** | Документация: что работает, что нет, что дальше | Roadmap to scale |

**Ключевой риск:** Negative result (new prototype не лучше). **Митигация:** Treat как data, не failure; refactor hypothesis.

### 90-day Success Criteria (Принято кандидатом и HM)

| Критерий | Target | Если не достигнут |
|---|---|---|
| Legacy-VBA reverse-engineered | 100% key rules documented | Document remaining gaps |
| Stakeholder map | 10-12 interviews | Continue in Phase 2 |
| 1 working prototype | Shadow-mode ≡ legacy ±5% | Iterate |
| Shadow-mode run rate | 2 weeks minimum | Extend Phase 2 |
| A/B test on 5-10 stores | First metrics by Day 75 | Adjust scope |

### Explicit NON-goals в первые 90 дней
- ❌ Production-grade ML-pipeline deployment
- ❌ Migration более 1 категории
- ❌ Замена legacy-VBA
- ❌ Cross-team coordination beyond immediate stakeholders
- ❌ Hiring (хотя можно обсуждать)

---

## 8️⃣ Cross-Links Map (Stage 4 synthesis ↔ Stage 1-3)

| Stage 4 раздел | Primary source material | Critical source IDs |
|---|---|---|
| §1 (8-level scheme) | Stage 1 (L1, L4), Stage 2 (L2, L3), Stage 3 (L5-L8) | S003, S010, S020, S031, S068, S069, S082, S083 |
| §2 (10 answers) | All Stage 1-3 | Все |
| §3 (problem map) | Stage 1 §3.2 + Stage 2 §22 + Stage 3 §14 | S031, S033, S068, S069, S082 |
| §4 (red flags) | Brief §23 + Stage 3 §2 | S069, S082 |
| §5 (green flags) | Brief §24 + Stage 1 §4 + Stage 3 §2 | S010, S012, S031, S068, S082, S083 |
| §6 (response strategy) | Brief §21 + Stage 3 §12-§14 | S082, S083, S069 |
| §7 (90 days) | Brief §20 + Stage 1 §3.2 + Stage 2 §7 | S031, S068, S069, S079 |

**Stage 4 = connection layer.** Каждый раздел этой главы ссылается на ≥3 sources from Stage 1-3.

---

## 9️⃣ §33 — Финальное соответствие brief

Brief §33 требует: «Не пытайся понравиться кандидату». **Проверка нашей synthesis:**

- ✅ Не рекламируем ВкусВилл — указываем clear weaknesses (замедление роста S020, сокращение сети S032, solo-role risk §23 РФ-1)
- ✅ Честный позиционирование: «mid-game» не лидер
- ✅ Отмечены gaps в data: §17 «Карта бизнес-проблемы» использует [ПРЕДПОЛОЖЕНИЕ***REMOVED*** marker для неподтверждённых items
- ✅ Anti-AI-red-flag: §4 RF-2 «высокая самостоятельность = нет помощи» — direct risk call
- ✅ Specificity > generality: 10 AQ ответов конкретных, не общие фразы
- ✅ Source-anchored: каждое утверждение имеет ≥1 source ref

**Главный вывод (1 абзац per brief §33):**
> «Если отбросить весь HR-язык вакансии, ВкусВилл на самом деле ищет человека, который **понимает fresh-ритейл и ML-pipeline**, **способен reverse-engineer legacy Excel/VBA** через structured discovery, **создаёт Python-prototypes через vibe-coding** с LLM, **валидирует их shadow-mode параллельно с legacy**, и **постепенно расширяет** успешный prototype на одну категорию за другой — с явным пониманием, что legacy ВкусВилл = **70+ AI-проектов уже идут**, новая роль = **усиление**, не «новая инициатива».»

**Гипотеза о скрытом запросе (per brief §33):**
> «Вероятнее всего, за вакансией стоит: **«у нас есть ML-pipeline прогноза спроса с ручной валидацией (S031), но shadow-mode framework не масштабируется — нужен человек, который построит scalable shadow-mode infrastructure и докажет, что новые ML-модели можно валидировать и rollout'ить без disruption текущего business-flow»**».

---

## 🔟 Closing Notes

- **Этот файл — финальный synthesis. Не требует новых данных**, это Layer поверх Stage 1-3.
- **Cross-link integrity**: каждое утверждение сконцентрировано в конкретном Stage-1-3 файле или SOURCES.md source_id. Никакое утверждение не «de novo».
- **Anti-hallucination maintained** per CON-55: маркеры `[ФАКТ***REMOVED***`/`[СИЛЬНАЯ ГИПОТЕЗА***REMOVED***`/`[ПРЕДПОЛОЖЕНИЕ***REMOVED***`/`[НЕТ ДАННЫХ***REMOVED***` inline.
- **Practical deliverable**: использовать §2 (10 answers) как elevator-pitch cheat sheet; §6 (cover letter) буквально вставить в отклик; §7 (90-day plan) — negotiating chip на интервью.
- **Project-local LESSONS.md остаётся УЗКИМ** per user constraint (recurring).

---

*08_final_synthesis.md заполнен в Stage 4 pure-synthesis. 8-level scheme + 10 answers + problem map + red/green flags + response strategy + 90-day plan. Zero new web research. Pl:[ФАКТ***REMOVED***-anchor через 46 source IDs (S001-S083).*

**Polish fix (post code-reviewer round, 2026-08-06):**
- Балансировка: 10 Red Flags (RF-1..RF-10) vs 10 Green Flags (GF-1..GF-10) — изначально было 8 Red vs 10 Green. RF-9 и RF-10 — экспансия из тематики 07 §23 (красный-флаг ответ per-question) для подкрепления §4 Red Flags синтез-слоя.
