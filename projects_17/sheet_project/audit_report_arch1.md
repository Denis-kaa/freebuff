# AUDIT REPORT — arch_1.md (альтернативная архитектура D2)

> **Роль:** auditor (Architectural Auditor / Quality Gate, blueprint `07_auditor.md` v3.1.0)
> **Вход:** `arch_1.md` (альтернативный архитектурный документ) в сравнении с каноном `architecture.md` + `contracts.yaml` + существующим `audit_report.md`.
> **Задача:** прогнать `arch_1.md` через quality gate ДО переноса его идей в канон. Выявить его собственные слабые места, противоречия, переусложнения; отделить «что стоит перенести» от «что не стоит».
> **Метод:** production-oriented ревизия; severity + последствия + минимальное исправление. Не перепроектирую, не пишу код.

---

## 1. Executive Summary

### Overall Assessment
`arch_1.md` — **сильная, более полная архитектура того же D2 Modular Monolith**, что и канон. База идентична (CONFIG/DATA/STYLES/GENERATOR/VALIDATOR, «ядро не знает шаблона», openpyxl не считает формулы, Normalized Data Contract, декларативный CONFIG). Документ добавляет то, чего канону не хватает: **artifact lifecycle (ADR-006)**, **уровни валидации L1–L4**, **generation_id + template_id/version**, **atomic delivery**, **input snapshot**, **7 ADR вместо 2**.

Но как самостоятельный канон `arch_1.md` **непригоден без доработки**: в нём есть внутренние противоречия (заявлено «7 модулей», перечислено 9; модуль `rules/` то выделен, то рекомендован к слиянию), он **менее готов к реализации на уровне сущностей** (нет field-level схемы, которую даёт `contracts.yaml`), и в нём **пропущено правило data formula injection** (закрыто в каноне как R9).

### Production Readiness
**Medium.** Архитектура реализуема и по ряду осей сильнее канона, но не самодостаточна: должна быть дополнена field-level контрактом (`contracts.yaml`) и закрыть собственные 3 Medium-противоречия.

### Main Risks (по arch_1.md)
1. **[High***REMOVED*** Пропущен data-level formula injection** — security-секция arch_1.md покрывает только CONFIG-injection («CONFIG → произвольный Python»), но НЕ экранирование значений данных (`=cmd|...`, `+ - @`). Канон закрывает это R9. Если брать arch_1.md изолированно — developer рискует не реализовать экранирование.
2. **[Medium***REMOVED*** Внутреннее противоречие «7 модулей» vs перечислено 9** — `финальное решение` заявляет 7 bounded modules, но по тексту их 9 (Configuration, Template Definition, Data, Style/Theme, Rules, Generation Core, Validator, Orchestrator, Artifact Delivery), а итоговая диаграмма ещё и опускает `Rules`.
3. **[Medium***REMOVED*** Неопределённость ownership валидации CONFIG** — на data-flow «Config Validation» показан как отдельный pre-generation узел (значит, его делает Configuration-модуль), а в модуле Validator уровень L1 тоже называется «CONFIG». Кто валидирует CONFIG — модуль конфигурации (fail-fast на входе) или валидатор (пост-фактум)? Это две разные вещи под одним именем.

### Final Verdict
**READY WITH FIXES** — `arch_1.md` не должен заменять канон целиком, но его идеи G1–G5 следует точечно перенести в `contracts.yaml`/`architecture.md`. Критических (Critical) дефектов нет.

---

## 2. Architecture Completeness Audit

| Area | Status | Findings |
|------|--------|----------|
| Domain model | ⚠️ Partial | Сущности названы, но **без field-level схемы** (нет required/типы/enum — это есть только в contracts.yaml). Entity «Relationship Definition» возвращает уже закрытую D1 (Relationship поглощён Reference). |
| Data flow | ✅ OK | Явный граф с «Config Validation» pre-generation узлом; главный путь корректен. |
| Contracts | ⚠️ Partial | 6 главных контрактов названы, но без формальной спецификации полей; `GenerationArtifact` требует metadata, но не указано ГДЕ хранить (sidecar? workbook props? память?). |
| Security | 🔴 Gap | **Нет data formula injection** (только CONFIG-injection). Канон R9 закрывает. |
| Observability | ✅ OK | generation_id + template_id/version + duration + size + status + error category — полнее канона. |
| Scaling | ✅ OK (задел) | Bottleneck назван (rows × formatting × formulas × conditional formatting); «оптимизировать после измерений» — здраво. |
| Failure handling | ✅ OK | Atomic delivery, «no artifact marked ready», retry-стратегия «не retry deterministic failure» — сильнее канона. |
| Configuration | ⚠️ Partial | Декларативность + versioning есть, но **нет стратегии миграции schema** (у канона M2 — та же дыра; arch_1 её не закрывает). |
| Deployment assumptions | ✅ OK | Локальный offline; явно отвергнуты microservices/queue/broker — корректно. |
| Micro-architecture | ⚠️ Partial | Физическая слоистость `domain/application/infrastructure` показана, но сам документ оговаривает «не создавать папку ради каждой коробки» — дерево противоречит своей же оговорке для простых модулей (styles). |

---

## 3. Module Audit (кратко, по значимым)

### Module: Configuration + Template Definition
- **Проблема:** два модуля (`Configuration` = schema/normalization; `Template Definition` = preset project_management), но сам документ в §7 «Что можно упростить» допускает их слияние. Для MVP с одним шаблоном это избыточно: канон уже делает то же плоским `config/schema.py` (domain) + `config/project_dashboard.py` (application).
- **Severity:** Low. **Fix:** не вводить `Template Definition` отдельным bounded module; оставить как application-слой внутри `config/`.

### Module: Formula / Reference Rules
- **Проблема:** модуль описан отдельно, в `Core Entities` `Formula Definition`/`Relationship Definition` помечены ownership `Rules`, НО итоговая диаграмма «7 модулей» его не содержит, а §7 рекомендует «оставить частью Configuration Domain». Три разных статуса одного модуля.
- **Severity:** Medium (противоречие документа). **Fix:** для D2 формулы/ссылки — это данные CONFIG (как уже решено D1/D4 в каноне); НЕ выделять `rules/` отдельным модулем, пока у него нет собственного lifecycle.
- **Связь с H1 аудита канона:** arch_1.md НЕ решает главный High-риск канона — якорение формул/ссылок к диапазонам данных. Он лишь констатирует «Formula Definition ≠ Formula Evaluation». H1 остаётся открытым.

### Module: Validator
- **Проблема ownership L1:** см. §1 Risk 3.
- **Проблема неопределённости L3:** уровень «L3 SEMANTIC» назван, но не конкретизирован (что именно сверяется — типы? обязательность? CONFIG↔DATA?). Канон уже формализовал это в `contracts.yaml validator.scope` (пункт «CONFIG↔DATA: каждый data_field из field_map существует в моделях DATA»). arch_1 даёт красивую рамку L1–L4, но канон даёт конкретику.
- **Severity:** Medium. **Fix:** объединить — рамку L1–L4 взять из arch_1, конкретику L3 — из contracts.yaml.

### Module: Generation Core
- **Сильно:** ownership Workbook «только Generation Core», atomic «generation failed → no artifact ready», изоляция openpyxl «единственный слой, тесно связанный с XLSX library», observability-контракт.
- **Проблема:** нет явного экранирования formula injection из DATA (см. §2 Security). **Fix:** добавить правило R9.

### Module: Orchestrator + Artifact Delivery
- **Delivery как отдельный bounded module — избыточно для MVP.** Для локального offline-скрипта «доставить артефакт» = «записать файл в output/». Канон делает это просто папкой `output/`. Ownership-переход Generation→Delivery — концептуально верен, но на D2 это лишний вес.
- **Severity:** Low. **Fix:** сохранить `output/` как папку, Delivery как формальный модуль не вводить; при появлении внешнего storage — выделить тогда.

---

## 2.5. Micro-Architecture Audit

| File/Module | Violation | Severity | Why It Matters | Fix |
|-------------|-----------|----------|----------------|-----|
| `arch_1.md` §4 дерево | глубокая вложенность `domain/application/infrastructure` для каждого контекста | Low | противоречит собственной оговорке «не дробить ради коробки»; для styles это явный овер-инжиниринг | держать плоскую структуру канона; слои = dependency boundaries, не папки |
| `arch_1.md` «7 модулей» | заявлено 7, перечислено 9, диаграмма опускает Rules | Medium | неоднозначный контракт для developer | привести число/список/диаграмму к одному согласованному виду |
| `arch_1.md` Security | отсутствует data formula injection | High | риск R9 не будет реализован | добавить правило экранирования `= + - @` из DATA |

---

## 4. Dangerous Integration Points

| Integration | Risk | Severity | Why It Fails | Mitigation |
|-------------|------|----------|--------------|------------|
| DATA-значение → ячейка | formula injection | High | arch_1 не описывает экранирование данных | экранировать `= + - @` (R9) + тест |
| CONFIG → Validator L1 | двойной владелец валидации CONFIG | Medium | конфигурация валидируется и pre-generation (fail-fast) и пост-фактум (validator) без разграничения | разграничить: L1 на входе = Configuration-модуль (fail-fast); Validator проверяет ARTIFACT против контракта |
| Formula → диапазон данных | статичные координаты (H1 канона) | High | arch_1 не решает; при росте строк ссылки бьются | перенести стратегию якорения (H1 из аудита канона) |
| GenerationArtifact metadata | не определено хранилище metadata | Medium | developer выберет произвольно (sidecar vs in-memory) | зафиксировать в contracts.yaml: sidecar `.json` или workbook properties |
| Delivery → файл | ownership-переход без необходимости | Low | лишний концептуальный слой на MVP | output/ как папка; Delivery — future boundary |

> Race conditions / retry storms / deadlocks / eventual consistency — корректно отвергнуты (single-threaded, offline). Совпадает с каноном.

---

## 5. Architectural Test Scenarios (ключевые, дополняющие канон)

| Module | Scenario | Expected Result | Failure Risk |
|--------|----------|-----------------|--------------|
| Generation Core | artifact status lifecycle CREATING→GENERATED→VALIDATING→READY | Delivery видит только READY | файл без статуса принят за готовый |
| Generation Core | atomic delivery: ошибка записи | temp-файл не публикуется, output не содержит битый .xlsx | «почти готовый» файл |
| Generation Core | input snapshot: DATA мутирует во время генерации | Generator работает с фиксированным снимком | смесь состояний |
| Validator | L3 SEMANTIC: field_map → поле отсутствует в DATA | finding + exit 1 | тихий mismatch |
| Configuration | CONFIG с битой ссылкой лист/поле | fail-fast до генерации | поздний отказ |

---

## 6. Что СТОИТ перенести в канон (G1–G5)

Это дешёвые контрактные усиления, закрывающие реальные дыры канона:

1. **G1 — Artifact lifecycle** (ADR-006): `CREATING → GENERATED → VALIDATING → READY` (+ INVALID/FAILED). В контракт `GenerationArtifact.status`.
2. **G2 — Уровни валидации L1–L4**, обязательны L1–L3, L4 — отдельная граница. L3 SEMANTIC = уже есть в `contracts.yaml validator.scope` (закрывает High H2 аудитора). Нужно только разграничить ownership L1 (Configuration-модуль vs Validator).
3. **G3 — generation_id + template_id/version** в метаданные артефакта и observability.
4. **G4 — Atomic delivery** (temp → rename) как явное правило записи (усиливает R6 канона).
5. **G5 — Input snapshot** — фиксировать входы на старте генерации (усиливает strong consistency канона).

## 7. Что НЕ СТОИТ переносить (переусложнение для локального скрипта)

- **Delivery как отдельный bounded module** → оставить `output/` папкой.
- **`rules/` как отдельный модуль** → оставить формулы/ссылки в CONFIG (D1/D4 уже решены).
- **Физическую вложенность `domain/application/infrastructure`** → держать плоскую структуру канона (сам arch_1 это разрешает).
- **`Relationship` отдельной сущностью** → держать D1 (Reference поглощает Relationship).
- **`Template Definition` отдельным модулем** → держать как application-слой `config/project_dashboard.py`.

## 8. Что arch_1.md НЕ закрывает (обязательно добавить при переносе)

- **Data formula injection (R9)** — arch_1 пропустил; канон уже имеет, не терять.
- **Field-level схему сущностей** — arch_1 без contracts.yaml не готов к реализации; переносим только идеи-надстройки поверх существующего contracts.yaml.
- **Стратегию миграции CONFIG-схемы** — ни один документ не закрывает (канон M2, arch_1 тоже).
- **Якорение формул/ссылок (H1)** — arch_1 не решает; остаётся главным open-риском.

---

## 9. Final Verdict

**READY WITH FIXES**

`arch_1.md` — полезное расширение канона, но не замена. Он добавляет ровно то, чего не хватает канону (lifecycle, уровни валидации, идентичность артефакта, atomic delivery, snapshot), и при этом содержит собственные Medium-противоречия (7 vs 9 модулей, статус `rules/`, ownership L1) и пропускает data formula injection.

**Рекомендованный путь:** НЕ делать `arch_1.md` каноном. Точечно перенести G1–G5 в `contracts.yaml` + `architecture.md` (с разграничением ownership L1 и сохранением R9), а `arch_1.md` оставить как справочный «superset-документ» с пометкой о расхождениях.

После переноса G1–G5 канон повышается с «READY WITH FIXES (H1, H2)» до «READY WITH FIXES (только H1 — якорение формул/ссылок)». H1 arch_1 не решает — это следующий отдельный дизайн-вопрос перед этапом 1.
