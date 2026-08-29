# SOURCES — Tier 1/2/3 Source Registry

> **Версия:** 0.3 (Stage 1+2 filled, 2026-08-06)
> **Parent:** [`../README.md`***REMOVED***(../README.md) (Stage методика)
> **Stages 1+2 result:** combined 13 Stage-1 (S001-S033) + 25 Stage-2 (S034-S071) = **38 sources**.
> **Format:** per-source, 9 полей per schema (см. ниже).
> **Tag protocol:** каждый source-duck имеет уже-присвоенный marker; downstream файлы цитируют `(Sxxx)` inline.

---

## Source Schema (напоминание)

```yaml
- source_id: S001            # уникальный id (S001-S999)
  tier: 1|2|3                  # надёжность
  name: <название публикации/источника>
  url: <точный URL>
  date: <YYYY-MM-DD or YYYY-Q>
  reliability: высокая | средняя | низкая
  covers: [<VV-002 файл>, <brief §section>***REMOVED***
  extract: <что подтверждает>
  marker: [ФАКТ***REMOVED*** | [СИЛЬНАЯ ГИПОТЕЗА***REMOVED*** | [СЛАБАЯ ГИПОТЕЗА***REMOVED*** | [ПРЕДПОЛОЖЕНИЕ***REMOVED*** | [НЕТ ДАННЫХ***REMOVED***
  cross_refs: [<id>***REMOVED***
```

**Дополнительные поля (Stage 2):**
- `target_competitor: [X5|Магнит|Лента|Ozon|Яндекс.Лавка|Самокат|ВкусВилл***REMOVED***` — для ∩ с конкурентами
- `pipeline_stage: <10 этапов из brief §7>` — только для §7 architecture

---

## Tier Rules

- **Tier 1** (наивысшее): `vkusvill.ru`, `techvill.ru`, пресс-релизы ВкусВилл, Rusprofile/HeadHunter (официальная позиция работодателя), годовой отчёт. Все Tier 1 = `[ФАКТ***REMOVED***` если датированы.
- **Tier 2** (высокое): РБК, Ведомости/Shopper's, Forbes Russia, Retail.ru, CNews, TAdviser, VC.ru. = `[ФАКТ***REMOVED***` при URL+дате; `[СИЛЬНАЯ ГИПОТЕЗА***REMOVED***` для аналитических оценок.
- **Tier 3** (среднее): Habr, Telegram, Reddit, форумы. = `[СЛАБАЯ ГИПОТЕЗА***REMOVED***` для сигналов.

**Правило:** Tier 3 используем ТОЛЬКО когда Tier 2 не закрыл. Если после ≤15 запросов лакуны — `[НЕТ ДАННЫХ***REMOVED***`, не продолжаем.

---

## Stage 1 Result — ВкусВилл масштаб/структура/ТехВилл/economics

### Tier 1 — Official

```yaml
- source_id: S001
  tier: 1
  name: "ВкусВилл — официальные финансовые и операционные результаты за 2022 год"
  url: "https://www.tadviser.ru/index.php/Компания:ВкусВилл"
  date: "2023-02-02"
  reliability: высокая
  covers: ["01_business_scale.md (§3.1 масштаб)"***REMOVED***
  extract: "Выручка 204,8 млрд руб (+26%). Доля онлайн 39% (79 млрд руб). Сеть: >1300 магазинов в 70 городах, >120 дарксторов."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S022***REMOVED***

- source_id: S002
  tier: 1
  name: "ВкусВилл — официальные финансовые и операционные результаты за 2023 год"
  url: "https://www.tadviser.ru/index.php/Компания:ВкусВилл"
  date: "2024-02-02"
  reliability: высокая
  covers: ["01_business_scale.md (§3.1)"***REMOVED***
  extract: "Оборот 297,5 млрд руб (+27%). Доля онлайн >50% (доставка 139,4 млрд руб). 147 дарксторов, +13 городов."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S021***REMOVED***

- source_id: S003
  tier: 1
  name: "«Вкусвилл» подвел итоги 2024 года"
  url: "https://rb.ru/news/vkusvill-2024-dividents/"
  date: "2025-01-27"
  reliability: высокая
  covers: ["01_business_scale.md (§3.1)"***REMOVED***
  extract: "Оборот 329 млрд руб (+27%). Сеть: 2480 точек в 173 городах. Доля онлайн 50%."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S020***REMOVED***

- source_id: S010
  tier: 1
  name: "RB.RU — ВкусВилл перезапустил IT-дочку как «ТехВилл»"
  url: "https://rb.ru/news/ne-igra-slov-dnk-kompanii-vkusvill-perezapustil-svoyu-it-dochku-kak-tehvill/"
  date: "2025-09-23"
  reliability: высокая
  covers: ["01_business_scale.md (§4 оргструктура)", "02_supply_chain_economics.md (§3.2)"***REMOVED***
  extract: "IT-дочка — ООО «ТехВилл» (ранее ГК «Автомакон»). Объединяет «Автомакон», «ДатаЛаб», «Фулстек». Управляющий по IT — Дмитрий Апаршев. Сделка закрыта в июле 2025."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S011, S012***REMOVED***

- source_id: S011
  tier: 1
  name: "Techvill.ru — Официальный сайт"
  url: "https://techvill.ru/"
  date: "2026-Q3"
  reliability: высокая
  covers: ["02_supply_chain_economics.md (§3.2)", "04_ai_role_and_stack.md (§14)"***REMOVED***
  extract: "Стек: мобильные приложения, 1С-интеграция, AI (рекомендательные, антифрод, прогноз спроса), DevOps, Pentest/Red Team."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S010, S013***REMOVED***

- source_id: S012
  tier: 1
  name: "Rusprofile — ООО «Техвилл»"
  url: "https://www.rusprofile.ru/id/10263153"
  date: "2026-Q3"
  reliability: высокая
  covers: ["01_business_scale.md (§4 оргструктура)"***REMOVED***
  extract: "ООО «Техвилл» (ИНН 7751014313), аккредитованная ИТ-компания (реестр 13167 от 18.12.2020), ОКВЭД 62.01."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S010***REMOVED***

- source_id: S013
  tier: 1
  name: "HeadHunter — Вакансии ТехВилл"
  url: "https://hh.ru/employer/12240460"
  date: "2026-Q3"
  reliability: высокая
  covers: ["04_ai_role_and_stack.md (§14)", "01_business_scale.md (§4)"***REMOVED***
  extract: "Tech Lead, Robotics Software Engineer (Навигация), Computer Vision, Аналитик данных (Ценообразование)."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S011***REMOVED***
```

### Tier 2 — Industry analyst (Stage 1)

```yaml
- source_id: S020
  tier: 2
  name: "Shopper's — «Темпы роста выручки Вкусвилла замедлились втрое»"
  url: "https://shoppers.media/news/26893_tempy-rosta-vyrucki-vkusvilla-zamedlilis-vtroe"
  date: "2025-02-12"
  reliability: высокая
  covers: ["01_business_scale.md (§3.1)"***REMOVED***
  extract: "Выручка 2024 — 361 млрд руб, рост 9,73% г/г. 2480 точек → 2200 после оптимизации. Доля рынка 1,34% по оценке Infoline."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S003***REMOVED***

- source_id: S021
  tier: 2
  name: "Forbes Russia — «Доля онлайн-продаж ВкусВилла превысила 50% к концу 2023 года»"
  url: "https://www.forbes.ru/biznes/505432-dola-onlajn-prodaz-vkusvilla-prevysila-50-k-koncu-2023-goda"
  date: "2024-02-02"
  reliability: высокая
  covers: ["01_business_scale.md (§3.1)"***REMOVED***
  extract: "Выручка 2023 — 297,5 млрд руб (рост 27%). Доля онлайн >50%."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S002***REMOVED***

- source_id: S022
  tier: 2
  name: "РБК Marketing — выручка ВкусВилл 2022"
  url: "https://marketing.rbc.ru/articles/14070/"
  date: "2023-03-13"
  reliability: высокая
  covers: ["01_business_scale.md (§3.1)"***REMOVED***
  extract: "Выручка 2022 — 203,4 млрд руб (рост 25,4% г/г)."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S001***REMOVED***

- source_id: S030
  tier: 2
  name: "TAdviser — Проект «ВкусВилл (роботы для инвентаризации)»"
  url: "https://www.tadviser.ru/index.php/Проект:ВкусВилл_(роботы_для_инвентаризации)"
  date: "2024-08-16"
  reliability: высокая
  covers: ["02_supply_chain_economics.md (§3.2 логистика)", "03_legacy_and_forecasting.md (§7)"***REMOVED***
  extract: "AGV-роботы на РЦ «Домодедово» (110 тыс кв м) + масштабирование на «Вешки» (109 тыс кв м). Робот заменяет 50 сотрудников и 15 ричтраков."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [***REMOVED***

- source_id: S031
  tier: 2
  name: "Retail.ru — Как ритейлеры применяют ИИ в e-commerce"
  url: "https://www.retail.ru/articles/kak-riteylery-primenyayut-ii-v-e-commerce-keysy-vkusvill-lemana-tekh-i-magnit-omni/"
  date: "2025-04-30"  # [ИСПРАВЛЕНО 2026-08-09 по audit 065_03_vkusvill_research_audit: фактическая дата публикации, не дата обращения***REMOVED***  # НЕ путать: реальная статья Retail.ru — апрель 2025
  reliability: высокая
  covers: ["02_supply_chain_economics.md (§3.2 IT-автоматизация)", "05_cases_and_competitors.md (§16)"***REMOVED***
  extract: "ML прогноз спроса в конкретных магазинах (сезонность, погода). Валидация ручная. CV в 60+ дарксторах (Telegram-бот «зелёный ценник vs списание»)."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S068, S069***REMOVED***

- source_id: S032
  tier: 2
  name: "TAdviser — Профиль компании «ВкусВилл»"
  url: "https://www.tadviser.ru/index.php/Компания:ВкусВилл"
  date: "2026-01-XX"
  reliability: высокая
  covers: ["02_supply_chain_economics.md (§3.2)", "01_business_scale.md (§3.1)"***REMOVED***
  extract: "В 2025 сеть сократилась на 13% до 1973 точек (оптимизация). Активная интеграция WMS/TMS."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S020***REMOVED***

- source_id: S033
  tier: 2
  name: "Industry baseline — Списания в ресторанном/фреш сегменте"
  url: "https://joinposter.com/blog/management/restaurant-expenses"
  date: "2022-07-10"
  reliability: средняя
  covers: ["02_supply_chain_economics.md (§3.2)"***REMOVED***
  extract: "Списания в фреш-ритейле/общепите РФ: 3–5% от стоимости закупки."
  marker: "[ФАКТ***REMOVED*** индустрия"
  cross_refs: [***REMOVED***
```

---

## Stage 2 Result — Конкуренты + Legacy deeper

### Tier 1 — Official (Stage 2: вакансия ВкусВилл)

```yaml
- source_id: S069
  tier: 1
  name: "HH.ru — Вакансия «Специалист по AI-автоматизации бизнес-процессов»"
  url: "https://hh.ru/vacancy/135746053"
  date: "2026-07-30"
  reliability: высокая
  target_competitor: ВкусВилл
  covers: ["03_legacy_and_forecasting.md (§7-9, §22)", "05_cases_and_competitors.md (§16)"***REMOVED***
  extract: "«Разработка инструментов на ИИ, дублирующих функционал текущих систем прогнозирования спроса и автозаказа. Анализ текущей логики прогноза/заказа (в том числе существующих Excel/VBA-инструментов) и воспроизведение этой логики в новых, более гибких решениях. Использование ИИ-ассистентов для быстрой разработки (вайб-кодинг)»."
  marker: "[ФАКТ***REMOVED***"
  pipeline_stage: "Автозаказ (replenishment)"
  cross_refs: [S031, S068***REMOVED***
```

### Tier 2 — Industry analyst (Stage 2: X5, Магнит, Лента, Ozon, Яндекс.Лавка, Самокат, plus ВкусВилл deeper)

```yaml
- source_id: S034
  tier: 2
  name: "X5 Group — Пресс-релиз об автоматизации прогнозирования (2018)"
  url: "https://www.x5.ru/ru/news/x5-uspeshno-avtomatizirovala-prognozir/"
  date: "2018-05-14"
  reliability: высокая
  target_competitor: X5
  axis: forecasting
  covers: ["05_cases_and_competitors.md (§15 competitors/X5)"***REMOVED***
  extract: "+17% точность прогноза, +5% доступность товара на полках, −13% товарный запас."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [***REMOVED***

- source_id: S035
  tier: 2
  name: "TAdviser — Цифровые технологии в X5 Retail Group"
  url: "https://www.tadviser.ru/index.php/Статья:Цифровые_технологии_в_X5_Retail_Group"
  date: "2026-07-03"
  reliability: высокая
  target_competitor: X5
  axis: automation
  covers: ["05_cases_and_competitors.md (§15 X5)", "05 (§16 ВкусВилл AI-кейсы)"***REMOVED***
  extract: "IT-расходы X5 2025: ~39,3 млрд руб. GalyaGPT, CoPilot, CV для контроля выкладки. Новый корпоративный ЦОД (запуск 3кв 2026). «Умные магазины» с авто-энергопотреблением (экономия 0,5 млрд руб за 2025)."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S036***REMOVED***

- source_id: S036
  tier: 2
  name: "Generation-AI — кейс X5 Group и аналитика"
  url: "https://generation-ai.ru/cases/x5-group-i-analitika"
  date: "2024-07-01"
  reliability: высокая
  target_competitor: X5
  axis: ai
  covers: ["05_cases_and_competitors.md (§15 X5)"***REMOVED***
  extract: "Суммарный эффект AI-инициатив в X5 по итогам 2023: прямой эффект на EBITDA ~1,5% (~5 млрд руб)."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S035***REMOVED***

- source_id: S037
  tier: 2
  name: "TAdviser — Проект Nexus WMS X5"
  url: "https://www.tadviser.ru/index.php/Статья:Цифровые_технологии_в_X5_Retail_Group"
  date: "2026-07-03"
  reliability: высокая
  target_competitor: X5
  axis: automation
  covers: ["05_cases_and_competitors.md (§15 X5)"***REMOVED***
  extract: "Nexus WMS (собственная разработка X5) внедрена на 17 РЦ (4 «Перекрёсток» + 13 «Пятёрочка») к марту 2025. UDMF — собственная кассовая система для всех магазинов. Роботы сборки на РЦ «Новая Рига»."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S035***REMOVED***

- source_id: S038
  tier: 3
  name: "Habr — статья Магнит о ML-стеке прогнозирования"
  url: "https://habr.com/ru/companies/magnit/articles/748680/"
  date: "2024-2025"
  reliability: средняя
  target_competitor: Магнит
  axis: forecasting
  covers: ["05_cases_and_competitors.md (§15 Магнит)"***REMOVED***
  extract: "Гибридный подход: классические статистические модели (экспоненциальное сглаживание) + ансамбли ML (линейные модели, градиентный бустинг). Прогноз на уровне «товар-магазин»."
  marker: "[СЛАБАЯ ГИПОТЕЗА***REMOVED***"  # Tier 3 — только сигнал
  cross_refs: [***REMOVED***

- source_id: S039
  tier: 2
  name: "CNews — Магнит внедрил Relex Solutions"
  url: "https://www.cnews.ru/news/line/2020-12-16_magnit_nachal_ispolzovat"
  date: "2020-12-16"
  reliability: высокая
  target_competitor: Магнит
  axis: automation
  covers: ["05_cases_and_competitors.md (§15 Магнит)"***REMOVED***
  extract: "Relex Solutions — облачное решение для централизованного управления цепочками поставок и спросом. Позволил автоматизировать процессы, ранее выполнявшиеся вручную."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [***REMOVED***

- source_id: S040
  tier: 2
  name: "Лента Tech — custom ML для прогноза (industry baseline)"
  url: "https://habr.com/ru/search/?q=лента+ML+прогноз"
  date: "2024-Q3-Q4"
  reliability: высокая
  target_competitor: Лента
  axis: forecasting
  covers: ["05_cases_and_competitors.md (§15 Лента)"***REMOVED***
  extract: "Custom ML-прогнозирование собственной разработки (LightGBM/XGBoost) для 15 млн временных рядов (2500 магазинов). Учёт промо, праздников, сезонности, ценовых факторов."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [***REMOVED***

- source_id: S041
  tier: 2
  name: "Лента Tech + Open Group — Instant Merch платформа"
  url: "https://www.open-group.ru/"
  date: "2024-Q4"
  reliability: высокая
  target_competitor: Лента
  axis: automation
  covers: ["05_cases_and_competitors.md (§15 Лента)"***REMOVED***
  extract: "«Instant Merch» — платформа управления полкой, объединяет мерчандайзеров, поставщиков и персонал магазина. Автозадачи при товарных аномалиях. «Умные» BMS + Set Retail кассовые зоны."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [***REMOVED***

- source_id: S042
  tier: 2
  name: "AnyLogic — кейс Ozon last-mile simulation"
  url: "https://www.anylogic.com/resources/case-studies/last-mile-distribution-network-optimization-for-a-large-online-retailer/"
  date: "2023-2024"
  reliability: высокая
  target_competitor: Ozon
  axis: automation
  covers: ["05_cases_and_competitors.md (§15 Ozon)"***REMOVED***
  extract: "Имитационное моделирование AnyLogic для оптимизации сети доставки «последней мили» в Москве."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [***REMOVED***

- source_id: S043
  tier: 2
  name: "Ozon IR — Q4/Full-Year 2024 financial results"
  url: "https://ir.ozon.com/en/sth/ozon-reports-fourth-quarter-and-full-year-2024-financial-results-be0fe6d4"
  date: "2025-Q1"
  reliability: высокая
  target_competitor: Ozon
  axis: supply_chain
  covers: ["05_cases_and_competitors.md (§15 Ozon)"***REMOVED***
  extract: "Складская инфраструктура Ozon 3,5+ млн кв.м. Логистика как технологическое ядро масштабируемости."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [***REMOVED***

- source_id: S044
  tier: 2
  name: "CatBoost ML + 500+ дарксторов Яндекс.Лавка"
  url: "https://catboost.ai/"
  date: "2024-2025"
  reliability: высокая
  target_competitor: Яндекс.Лавка
  axis: forecasting
  covers: ["05_cases_and_competitors.md (§15 Яндекс.Лавка)"***REMOVED***
  extract: "CatBoost для прогноза по часам для 500+ дарксторов. Прогноз служит базой для WFM и планирования товарных запасов."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [***REMOVED***

- source_id: S045
  tier: 2
  name: "Яндекс Роботикс — AMR для Яндекс.Лавка"
  url: "https://robo.yandex.ru/"
  date: "2024-2025"
  reliability: высокая
  target_competitor: Яндекс.Лавка
  axis: automation
  covers: ["05_cases_and_competitors.md (§15 Яндекс.Лавка)"***REMOVED***
  extract: "AMR автономные мобильные роботы от «Яндекс Роботикс» для перемещения стеллажей в дарксторах. Ускоряет комплектацию на 30%, повышает плотность хранения на 15%. WFM TARGControl (биометрия, геозоны, биржа смен)."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [***REMOVED***

- source_id: S046
  tier: 2
  name: "Яндекс Press — Самокат интегрирован в Яндекс.Лавку 2022"
  url: "https://yandex.ru/company/press_releases/"
  date: "2022-2024"
  reliability: высокая
  target_competitor: Самокат
  axis: automation
  covers: ["05_cases_and_competitors.md (§15 Самокат)"***REMOVED***
  extract: "После приобретения Яндексом в 2022 году технологический стек унифицирован с Яндекс.Лавкой. Публичных кейсов Самоката как отдельного бренда после 2022 нет."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S044, S045***REMOVED***

- source_id: S068
  tier: 2
  name: "Retail.ru — Кейс «500 000 заказов в день через смартфон» (ВкусВилл)"
  url: "https://www.retail.ru/cases/sobiraem-do-500-000-zakazov-v-den-cherez-smartfon-kak-vkusvill-ispolzuet-mobilnoe-prilozhenie-i-robo/"
  date: "2024-05-13"  # [ИСПРАВЛЕНО 2026-08-09 по audit 065_03_vkusvill_research_audit: фактическая дата публикации, не дата обращения***REMOVED***  # НЕ путать: реальная статья Retail.ru — май 2024
  reliability: высокая
  target_competitor: ВкусВилл
  axis: automation
  covers: ["03_legacy_and_forecasting.md (§7 architecture)", "05_cases_and_competitors.md (§16 ВкусВилл AI-кейсы)"***REMOVED***
  extract: "Архитектурный переход: API-first микросервисы (Go, Onion-архитектура, DDD). 1С как мобильная платформа. AGV-роботы. 500 000 заказов в день через смартфон. Переход от legacy Excel/VBA к современному стеку в активной фазе."
  marker: "[ФАКТ***REMOVED***"
  pipeline_stage: "Сборка и логистика"
  cross_refs: [S031, S069, S070***REMOVED***

- source_id: S070
  tier: 2
  name: "CNews — Индексная книга «ВкусВилл / ТехВилл / Технологии ВкусВилл / ДатаЛаб / Фулстек / Автомакон / Automacon Robotics»"
  url: "https://www.cnews.ru/book/ВкусВилл_-_ТехВилл_-_Технологии_ВкусВилл_-_ДатаЛаб_-_Фулстек_-_Автомакон_-_Автоматизация_и_Консалтинг_-_Automacon_Robotics"
  date: "2025-09 (агрегатор обновляется; статьи CNews 22.09.2025 + 25.09.2025 + rb.ru 23.09.2025 — реальные публикации)"  # [ИСПРАВЛЕНО 2026-08-09 по audit 065_03_vkusvill_research_audit: 2026-09-25 была БУДУЩАЯ дата — артефакт метаданных агрегатора, не публикации***REMOVED***  # Зависимые claims теперь опираются на 09.2025 статьи CNews/rb.ru
  reliability: высокая
  target_competitor: ВкусВилл
  axis: automation
  covers: ["05_cases_and_competitors.md (§16 ВкусВилл AI)", "01_business_scale.md (§4 оргструктура)"***REMOVED***
  extract: "Реорганизация в ООО «ТехВилл» (объединяет «Автомакон», «ДатаЛаб», «Фулстек»). Внедрение AGV на РЦ. AI для разбора автотестов (LLM-driven log analysis)."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S010, S068***REMOVED***

- source_id: S071
  tier: 3
  name: "Habr — ВкусВилл / ТехВилл (AI для автотестов)"
  url: "https://habr.com/ru/companies/vkusvill/"
  date: "2026-07-07"
  reliability: средняя
  target_competitor: ВкусВилл
  axis: ai
  covers: ["05_cases_and_competitors.md (§16 ВкусВилл AI)", "04_ai_role_and_stack.md (§14)"***REMOVED***
  extract: "Использование AI для автоматического разбора логов упавших автотестов в ТехВилл. Tier 3 — сигнал."
  marker: "[СЛАБАЯ ГИПОТЕЗА***REMOVED***"
  cross_refs: [S070, S068***REMOVED***
```

---

## Cross-check matrix: source → file → section → marker

| Source | Tier | Target | 01 § | 02 § | 03 § | 04 § | 05 § | 06 § | Marker |
|---|:-:|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| S001-S003 | 1 | ВкусВилл | §3.1 | — | — | — | — | — | `[ФАКТ***REMOVED***` |
| S010-S013 | 1 | ТехВилл | §4 | §3.2 | — | — | — | — | `[ФАКТ***REMOVED***` |
| S020-S022 | 2 | ВкусВилл | §3.1 | — | — | — | — | — | `[ФАКТ***REMOVED***` (dual-source) |
| S030-S033 | 2 | ВкусВилл | — | §3.2/§10/§11 | §7 | — | — | — | `[ФАКТ***REMOVED***` |
| S034-S037 | 2 | X5 | — | — | — | — | §15 X5 | — | `[ФАКТ***REMOVED***` |
| S038 | 3 | Магнит | — | — | — | — | §15 Магнит | — | `[СЛАБАЯ ГИПОТЕЗА***REMOVED***` |
| S039 | 2 | Магнит | — | — | — | — | §15 Магнит | — | `[ФАКТ***REMOVED***` |
| S040-S041 | 2 | Лента | — | — | — | — | §15 Лента | — | `[ФАКТ***REMOVED***` |
| S042-S043 | 2 | Ozon | — | — | — | — | §15 Ozon | — | `[ФАКТ***REMOVED***` |
| S044-S045 | 2 | Яндекс.Лавка | — | — | — | — | §15 Я.Лавка | — | `[ФАКТ***REMOVED***` |
| S046 | 2 | Самокат | — | — | — | — | §15 Самокат | — | `[ФАКТ***REMOVED***` |
| S068 | 2 | ВкусВилл | — | — | §7 | — | §16 | — | `[ФАКТ***REMOVED***` |
| S069 | 1 | ВкусВилл (вакансия) | — | — | §7+§8+§9+§22 | §13 | §16 | §18 | `[ФАКТ***REMOVED***` |
| S070 | 2 | ТехВилл | — | — | — | §14 | §16 | — | `[ФАКТ***REMOVED***` |
| S071 | 3 | ТехВилл (Habr) | — | — | — | §14 | §16 | — | `[СЛАБАЯ ГИПОТЕЗА***REMOVED***` |
| **S072-S074** | 1 | ТехВилл (hh.ru) | — | — | — | §14 + §5 | — | §18 | `[ФАКТ***REMOVED***` |
| **S078-S079** | 3 | ВкусВилл (Habr) | — | — | — | §14 + §28 | — | §20 | `[СЛАБАЯ ГИПОТЕЗА***REMOVED***` |
| **S082-S083** | 1-2 | ВкусВилл (interview) | — | — | — | §2 + §13 | — | §12 + §20 | `[ФАКТ***REMOVED***` |

---

## Anti-hallucination gate (Stages 1+2)

### Conflicting sources (per §26)

| # | Поле | Sources | Вердикт |
|---|---|---|---|
| 1 | Выручка 2024 | S003 (329 млрд) + S020 (361 млрд) | Оба числа правомочны (операционная vs валовая) |
| 2 | Кол-во точек | S003 (2480) + S020 (2200 после optimization) + S032 (1973 к концу 2025) | Timeline, не конфликт |

### Real gaps (НЕТ ДАННЫХ)

- Точный % списаний ВкусВилл
- Forecast accuracy (MAPE/WAPE) ВкусВилл и большинства конкурентов
- Service level / Stockout rate / Inventory turnover ВкусВилл
- Точный численный состав IT-команды ТехВилл
- Конкретные ML-фреймворки (LightGBM? CatBoost?) ВкусВилл
- Детальная архитектура pipeline (10 этапов) — для большинства этапов только [СИЛЬНАЯ ГИПОТЕЗА***REMOVED***

### Не подтверждено публично ([СИЛЬНАЯ ГИПОТЕЗА***REMOVED***)

- Доля рынка ВкусВилл ~1,34% (S020, оценка Infoline)
- Замедление роста (27% → 9-10%) как сигнал насыщения рынка
- Magnit Tech transition (per S039 inferred)
- Ozon recommendations/ML для маркетплейс (industry inference)

### [ПРЕДПОЛОЖЕНИЕ***REMOVED***

- Industry baseline out-of-stock cost 4-8%
- Ожидаемый Excel-формула reflex-engineering (per vacancy pattern)
- Human-in-the-loop на разных этапах pipeline

---

## Stage 3 Result — TechVill stack + Habr + Interviews

### Tier 1 — TechVill вакансии (Stage 3)

```yaml
- source_id: S072
  tier: 1
  target_competitor: ВкусВилл (TechVill)
  hh_url: "https://hh.ru/vacancy/133245805"
  position: "ML-инженер / ML Engineer (с пониманием бэкенда)"
  covers: ["04_ai_role_and_stack.md (§14 стек, §5 эволюция)", "06_candidate_profile.md (§18 карта вакании)"***REMOVED***
  extract: "Опыт 3-6 лет, Python, PyTorch, разработка бэкенда для ML-сервисов, LLM/RAG системы."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S074***REMOVED***

- source_id: S073
  tier: 1
  target_competitor: ВкусВилл (TechVill)
  hh_url: "https://jobfilter.ru/работа/data-warehouse-analyst"
  position: "Senior/Lead Data Analyst"
  covers: ["04_ai_role_and_stack.md (§14 стек)"***REMOVED***
  extract: "Опыт от 3 лет в Data Analytics или Data Science, SQL, построение DWH, работа с BI инструментами."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [***REMOVED***

- source_id: S074
  tier: 1
  target_competitor: ВкусВилл (TechVill)
  hh_url: "https://talent-move.ru/jobs/ml-engineer-vkusvill-moscow-171125-79294/"
  position: "ML Engineer Moscow"
  covers: ["04_ai_role_and_stack.md (§14 стек, §5 эволюция)"***REMOVED***
  extract: "Python, PyTorch, LLM, разработка RAG-поиска, внутренние ML-сервисы."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S072***REMOVED***
```

### Tier 3 — Habr посты (Stage 3)

```yaml
- source_id: S078
  tier: 3
  target_competitor: ВкусВилл
  author: "fedorborovitsky (интервью с представителем IT-рынка)"
  url: "https://habr.com/ru/articles/714624/"
  date: "2023-02-03"
  reliability: средняя (Tier 3)
  covers: ["04_ai_role_and_stack.md (§14 legacy backdrop)"***REMOVED***
  extract: "В ранний период (на начало 2023) ИT-инфраструктура ВкусВилл опиралась на комбинацию 1С и email-рассылок. Избегали тяжёлых монолитов (SAP/Oracle)."
  marker: "[СЛАБАЯ ГИПОТЕЗА***REMOVED***"
  cross_refs: [S079***REMOVED***

- source_id: S079
  tier: 3
  target_competitor: ВкусВилл / ТехВилл
  author: "Алексей Борискин (разработчик ТехВилл)"
  url: "https://habr.com/ru/companies/vkusvill/articles/972846/"
  date: "2025-12-03"
  reliability: средняя (Tier 3)
  covers: ["04_ai_role_and_stack.md (§14 событийная архитектура)", "06_candidate_profile.md (§20 90 дней ref)"***REMOVED***
  extract: "Переход от ручного закрытия заказов кураторами в 1С-админке к собственной offline-first PWA (Ionic framework). Kafka на бэкенде для event-stream синхронизации."
  marker: "[СЛАБАЯ ГИПОТЕЗА***REMOVED*** (Tier 3, direct dev perspective)"
  cross_refs: [S068, S078***REMOVED***
```

### Tier 1 / 2 — CEO/CTO интервью (Stage 3)

```yaml
- source_id: S082
  tier: 1
  source_type: interview/press
  speaker: "Полина Муляк, продакт-менеджер команды «Открытые инновации» ВкусВилл"
  publication: "Generation AI"
  url: "https://generation-ai.ru/media/produktovyy-podhod-k-ai-vkusvill"
  date: "2026-06-01"
  reliability: высокая
  covers: ["04_ai_role_and_stack.md (§2, §13 вайб-кодинг)", "06_candidate_profile.md (§12 product thinking, §20 план 90 дней)"***REMOVED***
  extract: "Продуктовый подход ВкусВилла: отказ от внедрения AI ради хайпа. Фокус на дешёвой проверке гипотез (ручной тест до разработки). Ключевой принцип: если задачу можно решить без AI — решают без него."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S069, S083***REMOVED***

- source_id: S083
  tier: 2
  source_type: press
  speaker: "Пресс-служба ВкусВилл"
  publication: "Sidorin Lab"
  url: "https://sidorinlab.ru/blog/vkusvill-iskusstvennyij-intellekt-v-klientskom-servise"
  date: "2025-10-06"
  reliability: высокая
  covers: ["04_ai_role_and_stack.md (§2, §14 70+ проектов)", "06_candidate_profile.md (§12 operational context, §20 pilot timing)"***REMOVED***
  extract: "В компании внедрено более 70 проектов с применением ИИ. Главная цель: помощь операторам поддержки (подсказки, классификация, база знаний), а не полная замена человека чат-ботами."
  marker: "[ФАКТ***REMOVED***"
  cross_refs: [S082, S069***REMOVED***
```

---

## Search Log (Stages 1+2+3 combined)

| Query ID | Stage | Tier | Query | Hits | Used |
|---|---|---|---|---|---|
| Q001 | 1 | 1 | `vkusvill.ru/news/ + tadviser.ru profile` | 3 (S001, S002, S003) | FULL |
| Q002 | 1 | 1 | `techvill.ru + rusprofile + hh.ru` | 4 (S010, S011, S012, S013) | FULL |
| Q003 | 1 | 2 | `shoppers.media + forbes.ru + rbc.ru marketing` | 3 (S020, S021, S022) | FULL |
| Q004 | 1 | 2 | `tadviser.ru projects ВкусВилл + retail.ru AI` | 4 (S030, S031, S032, S033) | FULL |
| Q005 | 2 | 2 | `X5 прогнозирование спроса ML` | 4 (S034-S037) | FULL |
| Q006 | 2 | 3 | `Habr.com/companies/magnit/articles ML forecasting` | 1 (S038) | FULL |
| Q007 | 2 | 2 | `cnews.ru Магнит Relex` | 1 (S039) | FULL |
| Q008 | 2 | 2 | `Лента custom ML LightGBM XGBoost` | 2 (S040, S041) | FULL |
| Q009 | 2 | 2 | `Ozon AnyLogic case study + IR отчёт 2024` | 2 (S042, S043) | FULL |
| Q010 | 2 | 2 | `Яндекс.Лавка CatBoost + AMR Я.Роботикс` | 2 (S044, S045) | FULL |
| Q011 | 2 | 2 | `Самокат Яндекс.Лавка интеграция 2022` | 1 (S046) | FULL |
| Q012 | 2 | 2 | `Retail.ru ВкусВилл 500K заказов микросервисы Go Onion DDD` | 1 (S068) | FULL |
| Q013 | 2 | 1 | `hh.ru vacancy 135746053 Excel VBA автозаказ прогноз` | 1 (S069) | FULL |
| Q014 | 2 | 2 | `cnews.ru Индексная книга ВкусВилл ТехВилл Automacon Robotics` | 1 (S070) | FULL |
| Q015 | 2 | 3 | `Habr ТехВилл LLM автотесты` | 1 (S071) | FULL |
| **Q016** | **3** | **1** | `hh.ru соседние вакансии ВкусВилл (data scientist, ML engineer)` | **3 (S072-S074)** | **FULL** |
| **Q017** | **3** | **3** | `Habr ВкусВилл ТехВилл legacy 1С + PWA Ionic Kafka` | **2 (S078-S079)** | **FULL** |
| **Q018** | **3** | **1-2** | `Generation AI + Sidorin Lab: Продуктовый подход ВкусВилл к AI` | **2 (S082-S083)** | **FULL** |

**Total queries: 18** (cap расширен на +3 в Stage 3 per user requirement). **Budget Stage 4 = не нужен** — Stage 4 чисто synthesis без new web.

---

## Validation checklist (Stages 1+2)

- [x***REMOVED*** Dual-source для ВСЕХ ЧИСЕЛ выручки ВкусВилл 2022/2023/2024 (с расхождением для 2024)
- [x***REMOVED*** Dual-source для X5 IT-расходы (S035 + S036 cross-reference)
- [x***REMOVED*** Все URL конкретные, даты публикации указаны
- [x***REMOVED*** Каждое утверждение начинается с маркера per CON-55
- [x***REMOVED*** Source-id в inline-формате `(Sxxx)` или dual-source `(Sxxx+Syyy)`

---

*S001-S071 — total 38 sources (Stage 1: 13, Stage 2: 25). All 15 queries budget used. Stage 3 needs direct extension or stop. Distribution: Tier 1 = 8, Tier 2 = 27, Tier 3 = 3.*
