# CONSISTENCY REPORT — LIGHT-артефакты sheet_project (D2)

> **Задача:** проверить согласованность цепочки `brief → parsed_requirements → decomposition → module_list → integration_topology → architecture → contracts` (плюс adr/ADR-002, risk_matrix, audit_report) на расхождения.
> **Метод:** cross-reference по 6 осям — (1) сущности доменной модели, (2) структура папок/модулей, (3) контракты на стыках, (4) validator scope, (5) вердикты ролей, (6) терминология.

---

## 1. Согласованные нити (CONSISTENT ✅)

| Нить | Документы | Статус |
|------|-----------|--------|
| **openpyxl не вычисляет формулы** → расчёт — отдельный слой (LibreOffice headless) | brief §3.4/§4 · parsed_requirements «подводные камни» · decomposition «границы» · module_list «правила ядра #4» · architecture §2.5/§5(R1)/§6 · contracts `validator.out_of_scope` | ✅ полный консенсус |
| **Инвариант «ядро не знает шаблона»** (нет `if project_dashboard:`, нет зашитых листов) | brief §3.1 · decomposition «принцип» · module_list «правила ядра #1» · integration_topology «что НЕ связано» · architecture §2.4/§7 · contracts `generator.invariants` + `dependency_direction.forbidden` | ✅ формализован во всех |
| **Структура папок** (`config/data/generator/styles/validator/output/main.py`) | brief §5 · module_list «структура» · architecture §4 | ✅ идентична |
| **Архитектурный стиль** — Modular Monolith, локальный offline-скрипт | architecture §1 · parsed_requirements «project type = Script» · decomposition (bounded contexts, не сервисы) | ✅ согласовано |
| **openpyxl изолирован** в GENERATOR (запись) + VALIDATOR (чтение) | architecture §2.4/§2.5 · integration_topology · contracts `dependency_direction.forbidden` | ✅ |
| **DATA нормализован + source-agnostic** (источник — будущий адаптер) | brief §3.2 · decomposition «границы» · module_list #3 · integration_topology · architecture §2.2 | ✅ |
| **STYLES — отдельная тема** (цвета/шрифты/границы/выравнивание/ширины) | brief §3.2 · decomposition · module_list · architecture §2.3 · contracts `styles.fields` | ✅ (набор полей совпадает) |
| **Вердикты ролей согласованы по смыслу** | risk `CONDITIONAL GO` ≈ lisa `COND` ≈ auditor `READY WITH FIXES` (все = «реализуемо при условиях», критических блокеров нет) | ✅ |

---

## 2. Расхождения (FINDINGS)

### D1 [Medium***REMOVED*** — сущность `Relationship` теряется по цепочке
- `parsed_requirements` FR-01 и `module_list` (`schema.py`) перечисляют **`Relationship`** как отдельную сущность (рядом с `Reference`).
- `architecture` §1 сворачивает их в одну строку **«Relationship / Reference»**.
- `contracts.yaml` содержит **только `Reference`** — сущности `Relationship` нет вовсе.
- **Последствие:** developer, реализуя `schema.py` по contracts.yaml, не получит `Relationship`; связь «многие-ко-многим» (если нужна) окажется непредставленной, либо `Reference` начнёт неявно выполнять две роли.
- **Рекомендация:** явно решить — либо `Reference` поглощает `Relationship` (удалить из FR-01/module_list), либо ввести `Relationship` в contracts.yaml отдельной сущностью с полями.

### D2 [Medium***REMOVED*** — validator scope уже, чем заявлено в brief
- `brief` §3.4 требует от validator: **«соответствие CONFIG↔DATA»**, **«наличие Dashboard-блоков»**, **«соответствие карточек CONFIG»**.
- `contracts.yaml` `validator.scope` перечисляет только: листы (набор/порядок), колонки (набор/типы), validation/списки/формулы/ссылки (присутствуют). Пункты про **CONFIG↔DATA**, **Dashboard**, **карточки** отсутствуют.
- **Пересекается с аудитом** (audit_report §3 validator «Contract Risks»: не покрывает `field_map` → существование полей DATA; и §9 п.5).
- **Последствие:** обязательная проверка из brief не попадёт в контракт → не будет реализована/протестирована.
- **Рекомендация:** расширить `validator.scope` в contracts.yaml тремя пунктами (CONFIG↔DATA, Dashboard-блоки, карточки).

### D3 [Low***REMOVED*** — `LookupTable`/«справочники» не во всех списках сущностей
- `brief` §3.2 (справочники) и `contracts.yaml` (`LookupTable`) содержат сущность.
- `parsed_requirements` FR-01 и `module_list` (`schema.py`) её **не** перечисляют.
- **Последствие:** косметическое, но список сущностей в двух источниках истины (FR-01 vs contracts) расходится.
- **Рекомендация:** дополнить FR-01 и module_list сущностью `LookupTable`.

### D4 [Low***REMOVED*** — дом `Style` размыт (CONFIG vs STYLES)
- `parsed_requirements` FR-01 и `module_list` помещают **`Style`** в `config/schema.py` (доменная модель CONFIG).
- `contracts.yaml` и `architecture` переносят стиль в секцию **STYLES** (`Style`/`Theme`), отдельно от CONFIG-сущностей.
- **Последствие:** непонятно, живёт ли `Style` в `schema.py` (как сущность CONFIG) или в `theme.py` (как данные STYLES). Это осознанное уточнение в contracts, но drift с FR-01/module_list не зафиксирован.
- **Рекомендация:** зафиксировать: CONFIG ссылается на стиль **по ключу/имени**, а сами значения стиля — в `styles/theme.py`; убрать `Style` из списка сущностей `schema.py` в FR-01/module_list.

### D5 [Low***REMOVED*** — GENERATION OPTIONS не смоделированы
- `brief` §3.2 объявляет контракт **GENERATION OPTIONS** (имя выходного файла, выбранный шаблон, доп. параметры) как MUST.
- `contracts.yaml` `generator.public_api.generate.input` = `{workbook, rows, theme***REMOVED***` — без имени файла/шаблона/параметров (только `writes: output/*.xlsx`).
- **Последствие:** выбор шаблона/имени файла остаётся вне контракта; `main.py` возьмёт это «из ниоткуда».
- **Рекомендация:** добавить в contracts вход `output_name`/`options` (или явно пометить как вне-scope на этапе 1).

### D6 [Low***REMOVED*** — терминологический дрейф «связь/relationship/reference/hyperlink»
- `brief` использует «связи» и «hyperlinks»; `parsed_requirements`/`module_list` — `Relationship` и `Reference`; `architecture`/`contracts` — `Reference`; `references.py` описано как «связи/гиперссылки».
- **Последствие:** риск, что разные артефакты говорят о разном (гиперссылка ≠ реляционная связь листов).
- **Рекомендация:** один глоссарий в contracts.yaml: `Reference` = гиперссылка/указатель на лист; `Relationship` = структурная связь (если нужна).

### D7 [Info***REMOVED*** — два дома ADR
- `decisions/ADR-001` (стек, PROJECT_RULES-конвенция) и `adr/ADR-002` (layered-архитектура, blueprint output `adr/*.md`).
- **Последствие:** два места для ADR; registry ожидает `adr/*.md` (chain — ok), но `decisions/` не покрывается валидатором.
- **Рекомендация:** зафиксировать, что архитектурные ADR идут в `adr/`, проектные решения — в `decisions/` (или объединить). Не блокер.

---

## 3. Traceability matrix (сущности → документы)

| Сущность/Требование | brief | parsed_req | module_list | architecture | contracts |
|---------------------|:-----:|:----------:|:-----------:|:------------:|:---------:|
| Workbook | ✅ | ✅ | ✅ | ✅ | ✅ |
| Sheet | ✅ | ✅ | ✅ | ✅ | ✅ |
| Field/Column | ✅ | ✅ | ✅ | ✅ | ✅ |
| DataSource | ✅ | ✅ | ✅ | ✅ | ✅ |
| DashboardBlock | ✅ | ✅ | ✅ | ✅ | ✅ |
| KPI | ✅ | ✅ | ✅ | ✅ | ✅ |
| Card | ✅ | ✅ | ✅ | ✅ | ✅ |
| ValidationRule | ✅ | ✅ | ✅ | ✅ | ✅ |
| Formula | ✅ | ✅ | ✅ | ✅ | ✅ |
| Reference | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Relationship** | ✅ | ✅ | ✅ | ⚠️ (объединён) | ❌ (отсутствует) |
| **LookupTable** | ✅ (справочники) | ❌ | ❌ | ✅ | ✅ |
| DisplayRule | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Style** | ✅ (STYLES) | ✅ (в CONFIG) | ✅ (в CONFIG) | ⚠️ (STYLES) | ⚠️ (STYLES) |
| **GENERATION OPTIONS** | ✅ | — | — | — | ❌ (нет) |
| **CONFIG↔DATA в validator** | ✅ | — | — | — | ❌ (нет в scope) |
| **Dashboard/карточки в validator** | ✅ | — | — | — | ❌ (нет в scope) |

---

## 4. Вывод

Цепочка LIGHT-артефактов **в целом согласована**: ядро архитектуры (отделение CONFIG/DATA/STYLES от GENERATOR, граница «openpyxl не считает формулы», инвариант «ядро не знает шаблона», структура папок, изоляция openpyxl) проведено единообразно через все документы без противоречий.

Обнаружено **7 расхождений**, из них **2 Medium** (D1 `Relationship` теряется; D2 validator scope уже brief §3.4) и 5 Low/Info. Оба Medium-расхождения и бо́льшая часть Low закрываются **до/в начале этапа 1** (`config/schema.py`) простым уточнением `contracts.yaml` — код пока не писался, поэтому это дешёвые правки документации.

Рекомендуемый порядок закрытия:
1. **D2 + D1** (контракт) — до этапа 1: расширить `validator.scope`, разрешить `Relationship`.
2. **D4 + D3 + D5** — в момент правки contracts.yaml (одним заходом).
3. **D6 + D7** — глоссарий/конвенция, не блокер, можно параллельно.

## 5. Статус закрытия (2026-08-18)

**D1–D6 ПРИМЕНЕНЫ** (contracts.yaml + parsed_requirements.md + module_list.md):
- **D1** — `Relationship` поглощён `Reference` (поле `kind: hyperlink|cross_sheet_ref`); удалён из FR-01/module_list.
- **D2** — `validator.scope` расширен: CONFIG↔DATA (field_map → существование полей DATA) + Dashboard-блоки/карточки.
- **D3** — `LookupTable` добавлен в FR-01 и module_list.
- **D4** — `Style` убран из списка сущностей CONFIG (schema.py); живёт в STYLES (theme.py), CONFIG ссылается по ключу.
- **D5** — `output_name`/`options` добавлены в `generator.public_api.generate.input`.
- **D6** — глоссарий в contracts.yaml (Reference — единая сущность; «связь»/«гиперссылка»/«reference» — синонимы).

**D7 (два дома ADR: decisions/ vs adr/) — ЗАКРЫТ** (зафиксирована конвенция, файлы НЕ переносились):
- **Проектные решения** (стек/toolchain/scope-выборы каркаса, по `PROJECT_RULES.md`) → `decisions/` (`DECISIONS.md` + `ADR-001_*.md`).
- **Архитектурные ADR** (роль architect, blueprint output `adr/*.md`) → `adr/` (`ADR-002_*.md`).
- Конвенция записана в шапке `decisions/DECISIONS.md` + дерево проекта в `architecture.md` §4; ссылки обновлены в MANIFEST.md/README.md.

---

## 6. Закрытие аудит-замечаний (2026-08-19)

После аудита (`audit_report.md`, вердикт READY WITH FIXES) и сравнения с `arch_1.md` (справочный superset) закрыты оба High-замечания + перенесены G1–G5. Архитектура поднята до **READY**.

| Замечание | Суть | Решение в каноне |
|-----------|------|------------------|
| **H1 [High***REMOVED***** | формулы/ссылки заякорены на статичные `cell`-координаты | сущность `Anchor` (колонка + строка-якорь `header|first_data|last_data` + смещение `offset` + протяжённость `range`); координаты разрешает ядро в момент генерации |
| **H2 [High***REMOVED***** | привязка DATA→sheet не определена (`list[Record***REMOVED***` vs несколько листов) | `Sheet.data_source` → `DataSource.source` (именованные коллекции `map[collection_name → list[Record***REMOVED******REMOVED***`) + `field_map` |
| **G1** | нет lifecycle артефакта | `generator.lifecycle`: `CREATING→GENERATED→VALIDATING→READY` (+FAILED/INVALID) |
| **G2** | уровни валидации не разграничены (двойной владелец L1) | `validator.levels`: L1 (config/schema.py, fail-fast) / L2 STRUCTURAL / L3 SEMANTIC / L4 CALCULATION (вне D2) |
| **G3** | нет identity артефакта | `Workbook.template_id/template_version` + `generator.artifact` (generation_id/status/…) |
| **G4** | риск битого output | atomic publish `temp → rename`, только READY на финальном пути |
| **G5** | mutable DATA посреди генерации | `generator.snapshot` (входы фиксируются на старте) |

Осознанно НЕ перенесено из `arch_1.md`: `Delivery` как модуль (в каноне — шаг оркестратора), `rules/` как модуль (формулы/ссылки в CONFIG/GENERATOR), физическая вложенность `domain/application/infrastructure`. R9 (formula injection) сохранён. `arch_1.md` помечен баннером «справочный superset — НЕ канон».
