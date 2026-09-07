# MIGRATION_PLAN.md — план миграции в PrintCalc Pro

> Статус: COMPLETE · Дата: 2026-09-07 · Принцип: аддитивно, старое не ломаем до паритета (Evolution over Revolution).

## 1. Таблица миграции модулей

| Модуль | Источник | Целевое место | Способ | Зависимости | Риск | Rollback |
|---|---|---|---|---|---|---|
| Движок + API | — (новый) | `app/`, `calculators/core/` | новый код | FastAPI, Pydantic | низкий | не влияет на старое |
| Riso | `Общий…/riso_calc.py` (канон) | `calculators/riso/` | формула → pure + schema | реестр | низкий | старое EXE остаётся |
| Tablichki | `Общий…/tablichki.py` | `calculators/tablichki/` | то же | реестр | низкий | — |
| Sign | `Общий…/sign_calc.py` | `calculators/sign/` | то же + фото-логика опционально | реестр | средний (2 режима цены) | — |
| Wide | `Общий…/wide_format.py` | `calculators/wide/` | то же | реестр | низкий | — |
| Digital | `Общий…/digital_calc.py` | `calculators/digital/` | то же | реестр | низкий | — |
| CNC | `cnc_calc.py` | `calculators/cnc/` | формула из JS → pure + schema | реестр | средний (перевод JS→Python) | — |
| Design | `design_calc.py` | `calculators/design/` + `services/pdf.py` | форма-схема уже JSON — перенос напрямую | ReportLab | средний | — |
| Costing | `universal_calc.py` + equipment.json | `calculators/costing/` | модель амортизации → pure | реестр | средний | — |
| Справочники | 3 JSON | `data/registry/` | конвертация в YAML/JSON реестра | — | низкий | git |
| Смета/история | память окна | SQLite | новая фича | — | низкий | — |
| EXE-доставка | build_exe.py | новый spec (uvicorn+webview) | пересборка | PyInstaller | средний | старые EXE в dist/ сохранены |

Порядок: Движок → Riso → Tablichki → Wide → Digital → Sign → Costing → CNC → Design(+PDF) → Смета/история → EXE-доставка.

## 2. Этапы (по промту §12)

- **Этап 1 — аудит:** выполнен (артефакты 0–15).
- **Этап 2 — подготовка:** репозиторий `printcalc`, requirements.txt, CI (pytest), golden-тесты формул из старых файлов.
- **Этап 3 — фундамент:** движок, реестр, FastAPI скелет, web-UI каркас, CSV-экспорт.
- **Этап 4 — перенос:** Riso/Tablichki/Wide/Digital (низкий риск, формулы идентичны).
- **Этап 5 — объединение:** Sign (2 режима), Costing (амортизация), CNC (JS→Python), Design (PDF).
- **Этап 6 — интерфейс:** единый стиль, мобильная адаптация, настройки admin.
- **Этап 7 — тестирование:** golden-тесты + параллельная сверка со старыми EXE на 10–20 кейсах (старое как оракул).
- **Этап 8 — production:** desktop-пакет для офиса; при желании — сервер внутри сети; бэкап реестра в git.

## 3. MVP → V1 → V2

- **MVP:** движок + реестр + web-UI + Riso/Tablichki/Wide/Digital + CSV + смета в памяти.
- **V1:** Sign/Costing/CNC/Design+PDF, история смет (SQLite), настройки admin, EXE-пакет.
- **V2:** клиенты/заказы, роли, синхронизация между машинами, мобильная PWA, интеграции (CRM/таблицы).

## 4. DoD

- [x] у каждого модуля есть судьба; [x] порядок определён; [x] зависимости учтены; [x] rollback предусмотрен; [x] MVP без необязательного.
