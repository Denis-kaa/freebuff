# TARGET_ARCHITECTURE.md — целевая архитектура PrintCalc Pro

> Статус: COMPLETE · Дата: 2026-09-07

## 1. Контур системы

```
┌────────────────────────────────────────────────────┐
│ Web UI (responsive SPA)                            │
│ каталог калькуляторов · расчёт · смета · настройки │
└──────────────┬─────────────────────────────────────┘
               │ HTTP JSON (REST)
┌──────────────▼─────────────────────────────────────┐
│ FastAPI backend                                    │
│ /api/calculators  /api/calculate  /api/estimates   │
│ /api/registry     /api/export                      │
├────────────────────────────────────────────────────┤
│ Calculator Engine (контракт CALC-*)                │
│ реестр → валидация входа → pure-расчёт → результат │
├────────────────────────────────────────────────────┤
│ Registry Service (справочники)   Export Service    │
│ материалы·прайсы·оборудование    CSV · PDF         │
├────────────────────────────────────────────────────┤
│ Persistence: SQLite (сметы/история) + JSON/YAML    │
│ (реестр калькуляторов и справочников, git-friendly)│
└────────────────────────────────────────────────────┘
Desktop-доставка: PyInstaller (uvicorn + локальный webview/браузер)
```

## 2. Frontend

- Страницы: `/` (главная: поиск, категории, избранное, последние), `/calculators` (каталог), `/calculators/:id` (экран калькулятора, рендер по input-schema), `/estimate` (смета), `/settings` (справочники, роли админа).
- Состояние: клиентская форма ↔ серверная валидация; результат — блок «Цена / Себестоимость / Прибыль» + детализация строкой (как в текущих логах).
- Общие UI-компоненты: поле с единицами, селектор справочника, таблица сметы, карточка результата.

## 3. Backend

- `api/` — роутеры FastAPI; `services/` — расчёты, реестр, экспорт; `calculators/<id>/` — модули (см. CALCULATOR_ARCHITECTURE.md); `models/` — Pydantic-схемы; `data/` — SQLite + YAML/JSON реестр.
- Ошибки: единый формат `{error: {code, message, field?}}`; валидация — Pydantic по input-schema калькулятора.

## 4. Data flow (пример)

`POST /api/calculate {calc:"riso", input:{format:"A4", qty:300, ...}}` → реестр находит модуль → Pydantic-валидация → `calc.compute(input, registry)` → `{price, cost, profit, breakdown[], warnings[]}` → UI рендерит по result-schema.

## 5. Authentication / конфигурация / логирование / мониторинг

- MVP: без auth (локальный инструмент); V1: простая роль admin/user (настройки только admin).
- Конфиг: `.env` + `settings.yaml`; логирование: structlog/JSON в файл; мониторинг MVP не требуется, V1 — healthcheck + метрики uvicorn.

## 6. Testing / deployment

- pytest: unit (формулы), contract (схемы калькуляторов), e2e (FastAPI TestClient).
- Deployment: desktop-пакет (PyInstaller onefile, как сейчас) и/или сервер (docker-compose: uvicorn + nginx).

## 7. Стратегия масштабирования

- Новый калькулятор = новый каталог в `calculators/` + запись в реестре; ядро не меняется (критерий DoD этапа 11).
- Новая валюта/налог/прайс = правка реестра, не кода.

## 8. DoD

- [x] компоненты описаны; [x] связи определены; [x] поток данных определён; [x] API-контракты концептуально; [x] масштабирование; [x] тестирование; [x] добавление калькулятора без переписывания ядра.
