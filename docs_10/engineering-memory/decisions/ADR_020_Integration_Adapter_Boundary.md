# ADR-020: Integration adapter boundary — единая граница для внешних мостов (TG/MCP/phone)

> **Статус:** Accepted (реализован в core_02/integration_base.py, v5.189.81)
> **Дата:** 2026-08-22
> **Связанные:** ARCHITECTURAL_BASELINE_V1.md §3 (Integration-слой — DOCUMENTED ONLY), ADR-017 (Workspace), ADR-018 (Factory→Forge), §7.3 (границы), B1 (Workspace↔Project), CON-16 (additive), CON-19 (single-source-of-truth),
> **Решение 108:** ARCHITECTURE_DECISION_108_V1.md §B (Integration) + TOP 10 #6; CONTRACT_GRAPH_V1.md §G1 (USER→WORKSPACE — множественные входы CONFIRMED).

## Context

Baseline (§3) фиксирует: **«Integration/Connector/Adapter слой — DOCUMENTED ONLY; мосты (TG/MCP/phone) вшиты в ядро»**. Code evidence:

| Мост | Где сейчас | Проблема |
|------|-----------|----------|
| Telegram | `scripts_01/telegram_bot.py`, `core_02/telegram_contract.py`, `freebuff_plugin_03/tgbot.py` | логика бота + вызовы ядра вперемешку |
| MCP | `scripts_01/mcp_server.py` (stdio), `scripts_01/mcp_fastapi.py` (HTTP+Bearer/Vault) | два транспорта, общий диспатч вшит |
| Phone control | `scripts_01/phone_control_mcp.py` | MCP-инструменты телефона в ядре |
| SDK Bridge | `scripts_01/sdk_bridge.py:31` (`SmartRouterAdapter`) | мост freebuff.core ↔ termux-ai-agent |
| Plugins | `plugins_04/*`, `freebuff_plugin_03/*` | отдельный plugin-слой, слабо связан с мостами |

Отсутствует **единая граница**: «внешний мир → стандартный adapter-контракт → ядро». Внешние системы знают внутренние сигнатуры (chat_id, tool-диспатч) напрямую.

**Evidence-следствие (CONTRACT_GRAPH G1):** USER→WORKSPACE реализован **множеством несогласованных входов** (CONFIRMED):
`mcp_server.py:236-237` (workspace_root), `telegram_bot.py:57` (WorkspaceRegistry), `forge_api.py` (HTTP),
`freebuff_cli.py` (CLI). Каждый вход по-своему знает ядро — это и есть P1-пробел, закрываемый единой границей.

## Decision

Ввести **`IntegrationAdapter` контракт** (аддитивно, `core_02/integration_base.py`) — граница, через которую ВСЕ внешние мосты общаются с ядром:

```python
class IntegrationAdapter(ABC):
    """Единый adapter-контракт для внешних мостов (design-only)."""

    adapter_id: str                 # tg | mcp_http | mcp_stdio | phone | plugin_*
    direction: str                  # inbound | outbound | bidirectional
    auth: AuthSpec                  # none | bearer | vault | chat_id_scope

    @abstractmethod
    def handle(self, request: AdapterRequest, *, event_bus=None) -> AdapterResponse:
        """Нормализованный вход (text/intent/params) → нормализованный выход (result/error)."""
        ...

    # наследуемые сервисы (ленивые, fail-safe):
    def route_to_capability(self, intent: str) -> str       # intent → capability-токен (закрытый словарь)
    def call_platform(self, capability: str, payload: dict) # → SmartRouter/Factory/ForgeFacade (явный вызов, не молча)
```

**Правила:**
1. **Внешний мир → adapter → ядро** (односторонняя нормализация): мосты НЕ вызывают внутренние сигнатуры напрямую.
2. **Auth/scope на границе**: каждый adapter декларирует `AuthSpec` (none/bearer/vault/chat_id_scope) — единый способ проверки доступа (для TG — chat_id-скоп, для HTTP — Bearer/Vault).
3. **Capability-роутинг на границе**: intent → capability-токен из закрытого словаря (ANTI-6b); неизвестный токен → fail-safe отказ с причиной, не краш.
4. **Явные вызовы**: adapter вызывает ядро только через `call_platform` (явный запрос), НЕ автоматически (§7.3 «не молча»).
5. **Additive**: существующие мосты не переписываются; контракт вводится, новые интеграции (или рефакторинг по одной) следуют ему.
6. **Наблюдаемость**: каждый inbound/outbound логируется в event_bus (Observability-принцип).

## Alternatives

- **(а) Оставить мосты вшитыми** (работает сегодня) — отвергнуто: baseline §3 зафиксировал P1-пробел; без границы каждая новая интеграция = дублирование auth/роутинга/нормализации.
- **(б) Полный рефакторинг всех мостов сразу** — отвергнуто: риск регрессий (telegram_bot — 500+ LOC с тестами); правильнее аддитивный контракт + поэтапная адаптация.
- **(в) Единый plugin-фреймворк для всего** (заменить мосты плагинами) — отвергнуто: плагины — часть экосистемы, но TG/MCP/phone — системные мосты с auth; граница должна быть поверх, не внутри plugin-механики.
- **(г) `core_02/integration_base.py` (Adapter-контракт) + декларация AuthSpec + capability-роутинг** — **ВЫБРАНО**: аддитивно, сохраняет существующее, закрывает P1-пробел, совместимо с будущим sandbox/ACL (P0).

## Trade-offs

- **Выигрываем:** единая граница безопасности (AuthSpec + chat_id-скоп на одном уровне); нормализация входов; capability-роутинг без знания внутренностей; наблюдаемость всех переходов; готовый каркас для sandbox/ACL (P0).
- **Теряем:** новый слой (митигировано: контракт-минимум, поэтапная адаптация); риск «парада адаптеров» (митигировано: единый ABC + общие сервисы в базе).

## Consequences

- **Реализация (отдельный заход):** `core_02/integration_base.py` (ABC + AuthSpec + AdapterRequest/Response + route_to_capability/call_platform) + 6-8 hermetic тестов (auth-декларация, capability-роутинг закрытый словарь, fail-safe неизвестного токена, event-наблюдаемость). Существующие мосты НЕ трогаются на первом шаге; адаптация — по одной интеграции. Совместимость с P0: AuthSpec-декларация — готовый каркас для sandbox/tool-ACL (boundaries_v17 → runtime).
- **Документация:** baseline §3 «Integration-слой — DOCUMENTED ONLY» → «design зафиксирован (ADR-020)»; §4 P1 «Integration adapter boundary» — закрыт дизайном; ARCHITECTURE_DECISION_108 §B/TOP #6 закрывается этим ADR.
- **Реестры:** DECISIONS.md + DOCUMENT_REGISTRY.md + CHANGELOG.
