# Паспорт проекта Lead Aggregator + Attract-модуль

| Поле | Значение |
|---|---|
| **Название** | Lead Aggregator (Attract-модуль) |
| **Версия** | 0.2.0 (Фаза 2 архитектура + Фаза 3 код v1 + Фаза 4 Deploy CLI, 40 тестов) |
| **Назначение** | Автономный поиск заказов/клиентов для AI-фрилансера: pull-агрегатор Kwork + TG-каналы → классификация → доставка в TG-бот |
| **Владелец** | Владелец устройства (AI-фрилансер: Python, TG-боты, FastAPI, лендинги) |
| **Лицензия** | MIT |
| **Среда** | Termux на Android (ARM64), Python 3.14.6, SQLite-only |
| **Требования к правам** | No-root |
| **Статус** | 🟢 Фазы 2–4 завершены: CLI (`app/cli.py`) + dry-run/боевой запуск (TG: 2 блока, 0 целевых — сервисные сообщения); **W-16**: Kwork стал SPA — нужен headless (W-2); 40 тестов зелёные |

## Цели

1. Автономно находить заказы по запросу пользователя («разработка Telegram-ботов») без ручного поиска.
2. Агрегировать заказы из публичных источников (Kwork, TG-каналы-агрегаторы).
3. Классифицировать релевантность: L1 regex → L2 intent → L3 LLM-score (ModelGateway).
4. Доставлять отобранные лиды в TG-бот платформы (уведомления).
5. Не нарушать юридический гейт: read-only, без outbound-спама, без приватных данных.
6. (Трек B7, отдельно) — inbound-видимость: автопубликация кейсов/портфолио.

## Архитектура

- **Pull-модель** (IDEA EXPLORER Candidate A): читаем публичные источники, не спамим.
- **Pipeline:** Adapter (Kwork / TG) → нормализация → LeadRecord → L1/L2/L3-классификатор → порог ≥70 → доставка в TG-бот.
- **Абстракции (PHASE2):** `TLSClient` (httpx, curl_cffi — optional W-2), `ProxyRotator` (stub), `CheckpointStore` (SQLite, дедупликация по хешу).
- **Reuse платформы:** `scripts_01/model_gateway.py` (L3-скоринг), паттерн Telethon из `core_02/_tg_client_v2.py`, `scripts_01/notification.py` (TG-доставка).
- **Ограничения среды (W-2..W-5):** без новых зависимостей; PostgreSQL/Redis → абстракция CheckpointStore (SQLite v1).

## Документация проекта

| Документ | Роль |
|---|---|
| `ROADMAP.md` | ROADMAP-LA-001 (pipeline-шаблон: explain-first, этапы, acceptance) |
| `STEPS.md` | Живой чек-лист этапов |
| `LESSONS.md` | CON-/ANTI- находки проекта |
| `PHASE1_RESEARCH.md` | Research: матрица уязвимостей, W-1..W-7, Lead Detection Engine |
| `ATTRACT_MODULE_RESEARCH.md` | Research: источники клиентов, W-8..W-11, интент-профиль |
| `PHASE2_ARCHITECTURE.md` | Утверждённая архитектура v1 |
| `IDEA_EXPLORER_RUN.md` | Прогон IDEA EXPLORER v2.0 (промт 70) — 7 веток → 3 кандидата → A |
| `PROMT_ARCHITECT_RUN.md` | Прогон ПРОМТ АРХИТЕКТОР 1.7 (промт 70) — исполнимый base prompt для Фазы 3 |
| `MANIFEST.md` | Настоящий паспорт проекта |
| `app/cli.py` | CLI Фазы 4: `--dry-run` / `--once` / `--forever`, `--sources`, `--json` |
| `settings.env` | Переменные окружения (загружаются автоматически; заполни `LA_TG_BOT_TOKEN`/`LA_TG_CHAT_ID` для доставки) |
| `decisions/DECISIONS.md` | Индекс project-local ADR (3 решения, v5.147.0) |
| Тесты | `tests_09/test_lead_aggregator_core.py` + `test_lead_aggregator_adapters.py` → **26 passed** (команда: `python -m pytest tests_09/test_lead_aggregator_core.py tests_09/test_lead_aggregator_adapters.py -q`); при выносе — переносятся в проект (протокол §3 шаг 2b) |
| `decisions/ADR-001…003` | Проектные решения: pull-модель, юр. гейт, контракты-адаптеры |

## Правила проекта (scope)

- **Аддитивность:** только `projects_17/lead_aggregator/` — 0 изменений в `core_02/`, `scripts_01/`.
- **Юридический гейт (W-7):** read-only сбор, без outbound-сообщений заказчикам, без приватных данных.
- **Не плодить модули платформы:** reuse ModelGateway/Telethon/notification (CON-40 capability-check).
- **Только существующие зависимости:** httpx/telethon; curl_cffi/playwright — optional (W-2).

## Контроль Buffy

Buffy может:
- читать `MANIFEST.md`, `ROADMAP.md`, `STEPS.md`, `PHASE2_ARCHITECTURE.md`, `IDEA_EXPLORER_RUN.md`, `PROMT_ARCHITECT_RUN.md`;
- запускать `python -m projects_17.lead_aggregator.app.cli --dry-run` (реальные источники, без доставки);
- запускать боевой прогон: `python -m projects_17.lead_aggregator.app.cli --once` (после заполнения `LA_TG_BOT_TOKEN`/`LA_TG_CHAT_ID` в `settings.env`);
- прогонять тесты: `python -m pytest tests_09/test_lead_aggregator_core.py tests_09/test_lead_aggregator_adapters.py tests_09/test_lead_aggregator_cli.py -q` → **40 passed**;
- проверять прогресс по `STEPS.md` (этапы с acceptance-критериями).

Проект **не импортирует** `freebuff_plugin` (автономный пакет), но **использует** конвенции платформы (PIPELINE_TEMPLATE, AGENTS.md правила, engineering memory).

## Миграция (готовность к выносу)

- Project-local ADR: `decisions/` (ADR-001 pull-модель, ADR-002 юр. гейт, ADR-003 контракты-адаптеры) — решения переживут вынос.
- Протокол: [`docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md`***REMOVED***(../../docs_10/templates/PROJECT_MIGRATION_TEMPLATE.md) — инвентаризация, проверка самодостаточности (0 реальных `import` платформы в `app/`; live-верифицировано 2026-08-10 — см. ADR-003 §5), конвертация платформенных ADR с provenance, приёмка.
- Платформенный аналог: [ADR_014***REMOVED***(../../docs_10/engineering-memory/decisions/ADR_014_Lead_Aggregator_Attract_Module.md) (решение о модуле на уровне платформы; project-local ADR — self-contained копии).
