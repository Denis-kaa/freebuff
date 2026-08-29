# AUDIT REPORT — sheet_project (D2 конфигурируемый генератор Excel-дашбордов)

> **Роль:** auditor (Architectural Auditor / Quality Gate, blueprint `07_auditor.md` v3.1.0)
> **Вход:** architecture.md, contracts.yaml, decomposition.md, module_list.md, integration_topology.md, adr/ADR-002, risk_matrix.md, brief.md, parsed_requirements.md.
> **Метод:** production-oriented ревизия; каждое замечание — со severity, последствиями и минимальным исправлением. Не перепроектирую систему, не пишу код.

---

## 1. Executive Summary

### Overall Assessment
Архитектура **D2 корректна по сути**: разделение `CONFIG / DATA / STYLES / GENERATOR / VALIDATOR` с однонаправленными зависимостями и изоляцией openpyxl — правильный, минимальный Modular Monolith для локального offline-генератора. Ключевые P0-риски (R1 расчёт формул, R2 зашитая бизнес-логика) закрыты на уровне контрактов и ADR. Инвариант «ядро не знает шаблона» формализован и защищён тестом в плане.

### Production Readiness
**Medium.** Архитектура реализуема, но есть 2 **High**-недоопределённости в контрактах (якорение формул/ссылок к данным; привязка DATA→sheet), которые надо закрыть **до или в самом начале реализации**, иначе developer будет принимать произвольные решения на ходу.

### Main Risks
1. **[High***REMOVED*** Формулы/ссылки заякорены на статические координаты** (`Formula.cell`, `Reference.cell`) — при росте строк/колонок координаты «плывут», ссылки бьются. Стратегия якорения к диапазонам данных не определена.
2. **[High***REMOVED*** Привязка DATA→sheet недоопределена** — контракт задаёт `list[Record***REMOVED***`, но не сказано, как записи распределяются по нескольким листам с разными наборами колонок.
3. **[Medium***REMOVED*** Двойное представление формул** — `KPI.source` («поле данных или формула») vs сущность `Formula`; граница ownership размыта.
4. **[Medium***REMOVED*** Эволюция CONFIG-схемы** — есть `schema_version`, но нет стратегии миграции/обратной совместимости.

### Final Verdict
**READY WITH FIXES** — архитектура пригодна к реализации при точечной доработке контрактов (см. §7 и §9). Критических (Critical) дефектов нет.

---

## 2. Architecture Completeness Audit

| Area | Status | Findings |
|------|--------|----------|
| Domain model | ⚠️ Partial | Сущности покрывают D2, но `KPI.source` vs `Formula` дублируют понятие «формула» (M3). |
| Data flow | ⚠️ Partial | Главный путь ясен, но распределение `list[Record***REMOVED***` по листам не описано (H2). |
| Contracts | ⚠️ Partial | Контракты стыков есть, но `Formula.cell`/`Reference.cell` — статичные координаты без стратегии якорения (H1). |
| Security | ✅ OK | Formula injection (R9) закрыт экранированием; CONFIG не исполняется; openpyxl изолирован. |
| Observability | ✅ OK (базово) | Логи генерации/валидации + EventBus/Learning Loop (lisa_estimator паттерн) спроектированы. |
| Scaling | ✅ OK (задел) | Write-only mode openpyxl + потоковая запись обозначены как Growth Stage (§6 architecture.md). |
| Failure handling | ⚠️ Partial | Fail-fast на входе и atomic-запись есть, но контракт ошибок генерации (типы/exit-коды) не формализован (L2). |
| Configuration | ⚠️ Partial | CONFIG отделён, но эволюция схемы (`schema_version`) не расписана (M2). |
| Deployment assumptions | ✅ OK | Локальный offline-скрипт; нет деплоя/сети — адекватно. |
| Micro-architecture | ⚠️ Partial | God-modules нет; коллизия имён `generator/validation.py` vs `validator/validator.py` (L1); soft-coupling CONFIG→DATA по именам полей (M4). |

---

## 3. Module Audit

### config/schema.py
- **Responsibility Check:** корректна — доменная модель CONFIG (чистые данные).
- **Boundary Check:** OK — не знает openpyxl, не исполняется.
- **Dependency Audit:** OK — только stdlib.
- **Data Ownership Audit:** владеет структурой дашборда. ⚠️ `DataSource.field_map` хранит **имена полей DATA** (`data_field`) — скрытая связь CONFIG→DATA по строковым именам (soft coupling, R6/R10).
- **Failure Risks:** невалидный CONFIG (битая ссылка лист/поле) — fail-fast заявлен, но формат ошибки не специфицирован.
- **Scaling Risks:** рост числа шаблонов → нужен реестр шаблонов (обозначен в §6, не реализован).
- **Security Risks:** нет (данные, без eval).
- **Observability Gaps:** нет.
- **Contract Risks:** **M4** — `field_map` ссылается на поля DATA по имени; validator обязан проверять существование этих полей (иначе тихий mismatch).
- **Micro-Architecture Violations:** нет.
- **Suggested Fixes:** (1) добавить в validator правило «каждый `data_field` из `field_map` существует в моделях DATA»; (2) документировать формат ошибки валидации CONFIG.

### config/project_dashboard.py
- **Responsibility Check:** корректна — use-case сборки CONFIG первого шаблона.
- **Boundary Check:** OK — единственное место, знающее конкретный шаблон; ядро его не импортирует.
- **Dependency Audit:** OK — только `schema.py`.
- **Data Ownership Audit:** OK.
- **Failure Risks:** опечатка в имени листа/поля при сборке CONFIG → должна всплыть на валидации CONFIG (fail-fast).
- **Scaling Risks:** новых шаблонов = новые такие модули; реестр шаблонов отложен (не блокер MVP).
- **Security Risks:** нет.
- **Observability Gaps:** нет.
- **Contract Risks:** нет.
- **Micro-Architecture Violations:** нет.
- **Suggested Fixes:** держать шаблон минимальным (R4/R5); не добавлять сущности «на вырост».

### data/models.py + data/sample_data.py
- **Responsibility Check:** корректна — нормализованные модели, source-agnostic.
- **Boundary Check:** OK — не знает источник и layout листа.
- **Dependency Audit:** OK — только внутренние модели.
- **Data Ownership Audit:** владеет значениями. ⚠️ **H2** — контракт задаёт `list[Record***REMOVED***`, но workbook содержит несколько листов с разными колонками; не определено, как записи (или разные коллекции) биндятся к листам.
- **Failure Risks:** пустые/неполные данные → расхождение с CONFIG должен ловить validator.
- **Scaling Risks:** большой объём → write-only/потоковая запись (Growth Stage).
- **Security Risks:** formula injection из значений данных — закрыто экранированием на стороне GENERATOR (надо подтвердить тестом).
- **Observability Gaps:** нет.
- **Contract Risks:** **H2** (см. выше) — основной пробел контракта DATA.
- **Micro-Architecture Violations:** нет.
- **Suggested Fixes:** уточнить в contracts.yaml модель DATA: либо `map[sheet -> list[Record***REMOVED******REMOVED***`, либо явный `DataSource` на каждый лист с собственным `field_map` (рекомендуется второе — локальнее и согласовано с `Sheet`).

### styles/theme.py
- **Responsibility Check:** корректна — чистые визуальные данные.
- **Boundary Check:** OK — не знает openpyxl/листов.
- **Dependency Audit:** OK.
- **Data Ownership Audit:** владеет визуалом. ⚠️ **M3** — условное форматирование (`DisplayRule.kind=conditional_format`) живёт в CONFIG, но по смыслу это «стиль+логика»; граница STYLES↔CONFIG для conditional formatting размыта.
- **Failure Risks:** отсутствующий ключ стиля → fallback+warning (заявлен).
- **Scaling Risks:** несколько тем/брендингов → несколько theme-модулей (обозначено).
- **Security Risks:** нет.
- **Observability Gaps:** warning при fallback — достаточно.
- **Contract Risks:** **M3**.
- **Micro-Architecture Violations:** нет.
- **Suggested Fixes:** зафиксировать ownership conditional formatting: правило-условие — в CONFIG (это бизнес-правило), а визуальный стиль правила — в STYLES; задокументировать в contracts.yaml одним предложением.

### generator/* (workbook, sheets, dashboard, formulas, validation, references)
- **Responsibility Check:** корректна — единое неизменяемое ядро; `workbook.py` как фасад.
- **Boundary Check:** OK — инвариант «не импортирует config/project_dashboard.py» формализован.
- **Dependency Audit:** OK — читает schema/models/theme, openpyxl изолирован здесь.
- **Data Ownership Audit:** владеет процессом и промежуточным Workbook; не владеет CONFIG/DATA/STYLES — корректно.
- **Failure Risks:** **H1** — `formulas.py`/`references.py` пишут формулы/ссылки по статическим координатам (`Formula.cell`, `Reference.cell`); при N строках данных координаты сдвигаются → битые ссылки/формулы.
- **Scaling Risks:** Excel-лимиты (1 048 576 строк / 16 384 колонок) — валидация заранее заявлена; ок.
- **Security Risks:** formula injection — экранирование строк данных (префикс `'`) заявлено; требуется тест.
- **Observability Gaps:** тайминги/число строк — заявлено; ок.
- **Contract Risks:** **H1** + **L1** — коллизия имени `generator/validation.py` (data validation: списки/диапазоны) vs `validator/validator.py` (пост-проверка структуры); разные сущности, схожие имена.
- **Micro-Architecture Violations:** Medium-complexity наибольший модуль — но это суть системы; god-file не прогнозируется (разбит на 6 файлов).
- **Suggested Fixes:** (1) ввести в CONFIG семантику **якоря формул/ссылок** (привязка к колонке/диапазону + смещение, а не фиксированный `cell`) — вычисление фактических координат в `formulas.py`/`references.py` по числу строк данных; (2) переименовать `generator/validation.py` → `generator/data_validation.py` (снять коллизию).

### validator/validator.py
- **Responsibility Check:** корректна — только structural check; расчёт формул явно вне scope.
- **Boundary Check:** OK — не вызывает Excel/LibreOffice, не чинит результат, только читает.
- **Dependency Audit:** OK — openpyxl (чтение) изолирован; НЕ зависит от generator.
- **Data Ownership Audit:** не владеет — только читает.
- **Failure Risks:** файл отсутствует/повреждён → подробный отчёт (заявлен); формат отчёта есть (`findings`).
- **Scaling Risks:** читать по листам, не материализуя всё (заявлено).
- **Security Risks:** только чтение; не `eval` содержимого ячеек — ок.
- **Observability Gaps:** число проверок/failures/verdict — заявлено.
- **Contract Risks:** scope покрывает листы/колонки/типы/validation/формулы/ссылки; **не покрывает** проверку `field_map` на существование полей DATA (M4) и проверку якорей ссылок (H1) — добавить.
- **Micro-Architecture Violations:** нет.
- **Suggested Fixes:** расширить scope validator: (1) `field_map` → поля существуют в DATA; (2) ссылки/формулы указывают на существующие листы/диапазоны.

### main.py
- **Responsibility Check:** корректна — тонкий оркестратор.
- **Boundary Check:** OK — не содержит генерационной/валидационной логики.
- **Dependency Audit:** OK — вызывает фасады контекстов.
- **Failure Risks:** **L2** — контракт ошибок генерации (какие исключения, какие exit-коды) не формализован; validator имеет `exit_code 0/1`, генератор — нет.
- **Suggested Fixes:** зафиксировать exit-коды генератора (0 ok / 1 ошибка конфигурации / 2 ошибка данных / 3 ошибка записи) в contracts.yaml или README.

---

## 2.5. Micro-Architecture Audit

| File/Module | Violation | Severity | Why It Matters | Fix |
|-------------|-----------|----------|----------------|-----|
| `generator/validation.py` vs `validator/validator.py` | коллизия имён | Low | «validation» в двух разных смыслах (data validation vs пост-проверка) сбивает при чтении | переименовать `generator/validation.py` → `generator/data_validation.py` |
| `contracts.yaml` `Formula.cell`/`Reference.cell` | статичные координаты | High | координаты плывут при росте данных | якоря к колонке/диапазону + смещение |
| `contracts.yaml` `KPI.source` | «поле данных или формула» — неоднозначно | Medium | дублирует `Formula`, размывает ownership | KPI ссылается на Formula по id или на data_field; единственный источник |
| `contracts.yaml` `DisplayRule` | conditional format straddles CONFIG/STYLES | Medium | смешение бизнес-правила и визуала | условие → CONFIG, стиль правила → STYLES |
| `contracts.yaml` `DataSource.field_map` | soft-coupling по именам полей | Medium | тихий mismatch CONFIG↔DATA | validator проверяет существование полей |
| `architecture.md`/`contracts.yaml` | нет exit-кодов генератора | Low | невозможна автоматизация/CI | зафиксировать exit-коды (0/1/2/3) |

---

## 4. Dangerous Integration Points

| Integration | Risk | Severity | Why It Fails | Mitigation |
|-------------|------|----------|--------------|------------|
| DATA → GENERATOR (распределение записей по листам) | записи попадают не в тот лист / пустые листы | High | контракт `list[Record***REMOVED***` не задаёт sheet-биндинг | `DataSource` на каждый лист + `field_map`; validator сверяет |
| CONFIG → GENERATOR (формулы/ссылки) | битые ссылки/формулы при росте данных | High | статичные координаты | якоря к диапазонам; пересчёт координат по числу строк |
| CONFIG → DATA (field_map по имени) | тихий mismatch поля | Medium | строковая связь без проверки | validator: `data_field` существует в моделях DATA |
| GENERATOR → openpyxl (единственный инфра-вызов) | замена/обновление openpyxl ломает всё | Medium | расползание инфраструктуры | openpyxl строго в одном слое (уже заявлено); обёртка-адаптер |
| GENERATOR → XLSX (частичная запись) | «почти готовый» файл принят за готовый | Medium | ошибка в середине генерации | генерировать в память → сохранять одним шагом (уже заявлено, R6) |
| DATA-значение → ячейка (formula injection) | выполнение формул из данных | High (security) | значение начинается с `=`/`+`/`-`/`@` | экранирование префиксом `'` (заявлено) + тест |
| validator → XLSX (перечитывание) | формула прочитана как формула, не значение | Low | openpyxl не считает | осознанная граница (R1); calculation — отдельный слой |

> **Race conditions / retry storms / deadlocks / eventual consistency** — не применимы: single-threaded, локальный offline-процесс без сети/очередей. Это корректное архитектурное решение (не упрощение-дефект).

---

## 5. Architectural Test Scenarios

### config/schema.py
| Scenario | Input/Event | Expected Result | Failure Risk |
|----------|-------------|-----------------|--------------|
| happy path | валидный Workbook-граф | конструируется без ошибок | — |
| invalid input | ссылка на несуществующий лист | fail-fast с именем поля | тихий пропуск |
| invalid input | неизвестный тип поля | fail-fast | fallback на str |
| contract mismatch | `field_map` → отсутствующее поле DATA | validator фиксирует mismatch | тихий пропуск |

### generator/* (ядро)
| Scenario | Input/Event | Expected Result | Failure Risk |
|----------|-------------|-----------------|--------------|
| happy path | CONFIG+DATA+STYLES → XLSX | файл создан, все листы на месте | — |
| invalid input | CONFIG с битой ссылкой | fail-fast до записи файла | частичный файл |
| growth | DATA с N строками | формулы/ссылки указывают на актуальные диапазоны | битые ссылки (H1) |
| security | значение данных `=cmd|...` | записано как текст (экранировано) | выполнение формулы |
| contract mismatch | CONFIG ↔ DATA расходятся | validator-отчёт с расхождением | молчаливый «ок» |

### validator/validator.py
| Scenario | Input/Event | Expected Result | Failure Risk |
|----------|-------------|-----------------|--------------|
| happy path | корректный XLSX + CONFIG | exit 0, все checks passed | — |
| invalid input | отсутствует лист | finding + exit 1 | ложный «ок» |
| partial failure | один лист невалиден | itemized finding, остальные проверены | аварийный стоп на первом |
| contract mismatch | формула/ссылка на несуществующий лист | finding | пропуск (H1) |

### data/models.py + sample_data.py
| Scenario | Input/Event | Expected Result | Failure Risk |
|----------|-------------|-----------------|--------------|
| happy path | sample_data → list[Record***REMOVED*** | данные нормализованы | — |
| invalid input | пустой датасет | validator-предупреждение о пустых листах | пустой файл без предупреждения |
| edge case | значение, похожее на формулу | экранировано на записи | injection |

### styles/theme.py
| Scenario | Input/Event | Expected Result | Failure Risk |
|----------|-------------|-----------------|--------------|
| happy path | полная тема | стили применены | — |
| invalid input | отсутствующий ключ стиля | fallback на default + warning | падение |
| edge case | условное форматирование | условие из CONFIG, стиль из STYLES | смешение (M3) |

### main.py (оркестратор)
| Scenario | Input/Event | Expected Result | Failure Risk |
|----------|-------------|-----------------|--------------|
| happy path | CLI-запуск | CONFIG→DATA→STYLES→GENERATOR→XLSX→VALIDATOR, exit 0 | — |
| invalid input | битый CONFIG | exit 1 с понятным сообщением | traceback в stdout |
| partial failure | ошибка генерации | файл не записан, exit != 0 | «почти готовый» файл |

---

## 6. Role Decomposition

| Module | Suggested Role | Why |
|--------|----------------|-----|
| `config/schema.py` | Backend Core | доменная модель, чистая логика |
| `config/project_dashboard.py` | Backend Core | use-case конфигурации шаблона |
| `data/models.py` + `sample_data.py` | Data Engineering | нормализация + источник данных |
| `generator/*` | Backend Core | ядро генерации XLSX |
| `styles/theme.py` | Frontend (visual layer) | визуальная конфигурация |
| `validator/validator.py` | QA / Verification | структурная проверка |
| `main.py` | Backend Core | оркестрация |

> D2 — локальный скрипт: роли DevOps/SRE/Integration не требуются (нет деплоя/сети).

---

## 7. Missing Layers & Blind Spots

1. **Слой якорения формул/ссылок (High).** Архитектор задал `Formula.cell`/`Reference.cell` как координаты, но не описал, как координаты пересчитываются при динамическом числе строк. Это главный слепой участок — реализуй без него, получишь битые ссылки на первом же «длинном» датасете.
2. **Модель привязки DATA к листам (High).** `list[Record***REMOVED***` не отвечает на вопрос «какие записи в какой лист». Недоопределено.
3. **Стратегия эволюции CONFIG-схемы (Medium).** `schema_version: "1.0"` есть, но что делать при добавлении/переименовании поля — не сказано. Для «конфигурируемой» системы это важно (иначе старые CONFIG молча ломаются).
4. **Ошибки генерации (Low).** Типы ошибок и exit-коды генератора не формализованы (в отличие от validator).
5. **Тест на formula injection (Low/Medium).** Экранирование заявлено, но отдельного тест-сценария нет — рискует не быть реализовано.

---

## 8. Production Readiness Gaps

- **Secrets:** N/A (нет внешних API в D2); при появлении Bitrix24/Google Sheets — секреты только через `.env`, не в CONFIG (уже в R10).
- **Migrations:** нет стратегии миграции CONFIG-схемы (M2) — единственный значимый production-gap для «конфигурируемой» системы.
- **Rollback strategy:** N/A (перезапись детерминированная; output атомарный).
- **Observability:** базовые логи + EventBus/Learning Loop есть; корреляция по шаблону/листу достаточна для локального скрипта.
- **Disaster recovery / monitoring / alerting / operational tooling:** N/A для offline-скрипта; не строить заранее (R4).

**Итог по production:** для локального CLI-генератора gaps минимальны; единственный структурный — миграция CONFIG-схемы.

---

## 9. Final Verdict

**READY WITH FIXES**

Архитектура корректна и реализуема: разделение изменяемого/неизменяемого, изоляция openpyxl, разделение structural/calculation validation и формализованный инвариант «ядро не знает шаблона» — всё на месте. Критических дефектов нет.

**Обязательные точечные исправления перед/в начале реализации (иначе developer примет решения на ходу):**
1. **[High***REMOVED***** Определить семантику якорения формул/ссылок к диапазонам данных (не фиксированные `cell`).
2. **[High***REMOVED***** Определить привязку DATA→sheet (рекомендация: `DataSource` на каждый лист со своим `field_map`).
3. **[Medium***REMOVED***** Разрешить ownership `KPI.source` vs `Formula` (единственный источник формулы).
4. **[Medium***REMOVED***** Зафиксировать ownership conditional formatting (CONFIG — условие, STYLES — стиль правила).
5. **[Medium***REMOVED***** Добавить в validator проверку `field_map` → существование полей DATA.
6. **[Low***REMOVED***** Переименовать `generator/validation.py` → `generator/data_validation.py`; зафиксировать exit-коды генератора.

После закрытия пунктов 1–2 архитектура повышается до **READY** и передаётся developer без архитектурной неопределённости.
