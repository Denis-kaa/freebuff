"""core_02/integration_base.py — Единая граница для внешних интеграций (ADR-020).

ADR-020 (docs_10/engineering-memory/decisions/ADR_020_Integration_Adapter_Boundary.md):
закрывает P1-пробел baseline §3 («Integration-слой — DOCUMENTED ONLY») — вводит
официальный контракт IntegrationAdapter, через который ВСЕ внешние мосты
(TG/MCP/phone/plugins/SDK) общаются с ядром платформы.

    «внешний мир → adapter → ядро» (односторонняя нормализация)

Дизайн:
- ``IntegrationAdapter`` — ABC с ``handle()`` (нормализованный вход/выход),
  ``route_to_capability()`` и ``call_platform()`` — наследуемые сервисы.
- ``AuthSpec`` — декларация доступа на границе (none/bearer/vault/chat_id_scope).
- ``INTENT_CAPABILITY_MAP`` — закрытый словарь intent→capability (ANTI-6b defense).
- Существующие мосты НЕ переписываются; контракт вводится аддитивно.

Совместимость:
- ``core_02/telegram_contract.py`` — TG-контракт (report_to_saved_messages и др.) остаётся.
- ``scripts_01/mcp_server.py``, ``scripts_01/phone_control_mcp.py`` — остаются.
- ``scripts_01/sdk_bridge.py`` (SmartRouterAdapter) — остаётся.
- ``freebuff_plugin_03/bridge_layer.py`` — остаётся.
- ``IntegrationAdapter`` — официальный контракт поверх них (additive).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    pass

__all__ = [
    "AdapterDirection",
    "AdapterRequest",
    "AdapterResponse",
    "AuthSpec",
    "INTENT_CAPABILITY_MAP",
    "IntegrationAdapter",
***REMOVED***


# ═══════════════════════════════════════════════════════════════════════
# AuthSpec — декларация доступа на границе
# ═══════════════════════════════════════════════════════════════════════

class AuthMethod(str, Enum):
    """Способ аутентификации внешнего моста."""
    NONE = "none"             # без аутентификации (sandbox / local-only)
    BEARER = "bearer"         # Bearer token (HTTP заголовок)
    VAULT = "vault"           # Vault-токен (из secrets_15/)
    CHAT_ID_SCOPE = "chat_id_scope"  # TG: привязан к chat_id
    PHONE_SCOPE = "phone_scope"  # Phone control: привязан к устройству


@dataclass(frozen=True)
class AuthSpec:
    """Декларация требований аутентификации для IntegrationAdapter.

    Примеры:
    - TG: ``AuthSpec(method=AuthMethod.CHAT_ID_SCOPE, scope="Saved Messages")``
    - HTTP: ``AuthSpec(method=AuthMethod.BEARER, scope="freebuff-api")``
    - Phone: ``AuthSpec(method=AuthMethod.PHONE_SCOPE, scope="termux-device")``
    - Plugin local: ``AuthSpec(method=AuthMethod.NONE, scope="local-plugin")``
    """
    method: AuthMethod
    scope: str = ""  # human-readable: "Saved Messages", "freebuff-api", etc.

    def is_public(self) -> bool:
        """Нет ограничений доступа (NONE)."""
        return self.method == AuthMethod.NONE

    def is_token_based(self) -> bool:
        """Требуется токен (BEARER или VAULT)."""
        return self.method in (AuthMethod.BEARER, AuthMethod.VAULT)


# ═══════════════════════════════════════════════════════════════════════
# Adapter direction
# ═══════════════════════════════════════════════════════════════════════

class AdapterDirection(str, Enum):
    INBOUND = "inbound"       # мир → платформа (TG-бот, HTTP-запрос)
    OUTBOUND = "outbound"     # платформа → мир (отправка в TG)
    BIDIRECTIONAL = "bidirectional"


# ═══════════════════════════════════════════════════════════════════════
# Normalized request / response
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class AdapterRequest:
    """Нормализованный входящий запрос от внешнего моста.

    Все внешние системы приводят свои входы к этому формату.
    """
    intent: str                    # "execute_project", "report_status", "phone_sms"
    payload: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    meta: Dict[str, Any***REMOVED*** = field(default_factory=dict)
    # метаданные источника (chat_id, client_ip, session_id — зависит от адаптера)

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        return {
            "intent": self.intent,
            "payload": self.payload,
            "meta": self.meta,
        ***REMOVED***


@dataclass
class AdapterResponse:
    """Нормализованный ответ платформы → внешний мост."""
    status: str                   # "ok" | "error" | "deferred"
    intent: str                   # исходный intent запроса
    data: Any = None
    errors: List[str***REMOVED*** = field(default_factory=list)
    warnings: List[str***REMOVED*** = field(default_factory=list)
    capability_used: Optional[str***REMOVED*** = None  # capability-токен, выбранный роутером
    model_used: Optional[str***REMOVED*** = None       # модель, выбранная SmartRouter

    def to_dict(self) -> Dict[str, Any***REMOVED***:
        d: Dict[str, Any***REMOVED*** = {
            "status": self.status,
            "intent": self.intent,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
        ***REMOVED***
        if self.capability_used is not None:
            d["capability_used"***REMOVED*** = self.capability_used
        if self.model_used is not None:
            d["model_used"***REMOVED*** = self.model_used
        return d

    @property
    def ok(self) -> bool:
        return self.status == "ok"


# ═══════════════════════════════════════════════════════════════════════
# Closed vocabulary: intent → capability
# ═══════════════════════════════════════════════════════════════════════

# Закрытый словарь intent→capability (ANTI-6b: capability — подмножество
# agent_base.KNOWN_CAPABILITIES). Неизвестный intent → fail-safe отказ,
# НЕ fallback на неизвестную capability.
INTENT_CAPABILITY_MAP: Dict[str, str***REMOVED*** = {
    # TG
    "execute_project": "code",
    "status_check": "summarize",
    "report": "summarize",
    "decompose_task": "plan",
    "review_code": "review",
    "explain_code": "explain",
    "refactor_code": "refactor",
    # MCP / tools
    "tool_call": "tools",
    "mcp_request": "code",
    "model_routing": "router",
    # Phone
    "phone_sms": "tools",
    "phone_notification": "tools",
    "phone_battery": "summarize",
    # Plugins / sync
    "sync_workspace": "summarize",
    "knowledge_base_query": "long_context",
    # Fallback
    "fallback": "summarize",
***REMOVED***


# ═══════════════════════════════════════════════════════════════════════
# IntegrationAdapter — единый контракт для внешних мостов
# ═══════════════════════════════════════════════════════════════════════

class IntegrationAdapter(ABC):
    """Единый adapter-контракт для внешних мостов (ADR-020: design-only).

    Связывает: «кто вызывает (adapter_id/direction/auth) →
    какой intent → capability-роутинг → вызов платформы».

    **Правила:**
    1. Внешний мир → adapter → ядро (односторонняя нормализация).
    2. Auth/scope на границе (AuthSpec).
    3. Intent → capability-роутинг через закрытый словарь (ANTI-6b).
    4. Явные вызовы платформы через ``call_platform``, не молча (§7.3).
    5. Каждый inbound/outbound логируется в event_bus (наблюдаемость).
    """

    def __init__(
        self,
        *,
        adapter_id: str,
        direction: AdapterDirection = AdapterDirection.INBOUND,
        auth: Optional[AuthSpec***REMOVED*** = None,
    ) -> None:
        self.adapter_id = adapter_id
        self.direction = direction
        self.auth = auth or AuthSpec(method=AuthMethod.NONE, scope=adapter_id)

    # ── Abstract handle ────────────────────────────────────────────────

    @abstractmethod
    def handle(
        self,
        request: AdapterRequest,
        *,
        event_bus: Any = None,
    ) -> AdapterResponse:
        """Нормализованный вход → нормализованный выход.

        Подклассы ДОЛЖНЫ переопределить этот метод.

        Returns:
            AdapterResponse (status ok/error/deferred).
            Fail-safe: сбой → AdapterResponse(status="error", errors=[...***REMOVED***),
            НЕ exception наружу.
        """
        ...

    # ── Service: intent → capability routing ────────────────────────────

    def route_to_capability(self, intent: str) -> str:
        """Intent → capability-токен (закрытый словарь INTENT_CAPABILITY_MAP).

        Неизвестный intent → возвращает "fallback"-capability (НЕ краш;
        вызывающий слой добавит warning в AdapterResponse).

        Returns:
            capability-токен (str) — валидное подмножество
            agent_base.KNOWN_CAPABILITIES.
        """
        return INTENT_CAPABILITY_MAP.get(
            intent,
            INTENT_CAPABILITY_MAP["fallback"***REMOVED***,
        )

    # ── Service: platform call ──────────────────────────────────────────

    def call_platform(
        self,
        capability: str,
        payload: Dict[str, Any***REMOVED***,
        *,
        event_bus: Any = None,
    ) -> Dict[str, Any***REMOVED***:
        """Явный вызов платформы: capability → SmartRouter → модель.

        НЕ вызывает ForgePipeline напрямую (§7.3). Использует SmartRouter
        для model routing и ModelGateway для исполнения.

        Fail-safe: возвращает ``{"status": "error", ...***REMOVED***`` при сбое.

        Returns:
            dict с ключами status / model_used / result — совместимо с
            AdapterResponse для обратного маппинга.
        """
        try:
            from core_02.router import ModelCatalog, SmartRouter  # lazy import (fail-safe)

            catalog = ModelCatalog.default()  # type: ignore[attr-defined***REMOVED***
            router = SmartRouter(catalog)
            decision = router.route(
                required_capabilities=[capability***REMOVED***,
            )

            return {
                "status": "ok",
                "model_used": getattr(decision, "model", "fallback"),
                "provider": str(getattr(decision, "provider", "unknown")),
                "reason": getattr(decision, "reason", ""),
                "fallback_used": getattr(decision, "fallback_used", False),
                "payload": payload,
            ***REMOVED***
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
                "payload": payload,
            ***REMOVED***

    # ── Helpers ─────────────────────────────────────────────────────────

    def log_event(
        self,
        event_bus: Any,
        event_type: str,
        request: AdapterRequest,
        response: AdapterResponse,
    ) -> None:
        """Залогировать переход в event_bus (наблюдаемость).

        Бесшумный no-op если event_bus is None.
        """
        if event_bus is None:
            return
        try:
            event_bus.emit(
                event_type,
                adapter_id=self.adapter_id,
                intent=request.intent,
                status=response.status,
                capability_used=response.capability_used,
                model_used=response.model_used,
            )  # type: ignore[union-attr***REMOVED***
        except Exception:
            pass  # fail-safe: логгирование не ломает основной поток

    def _ok_response(
        self,
        request: AdapterRequest,
        data: Any = None,
        capability: Optional[str***REMOVED*** = None,
        model: Optional[str***REMOVED*** = None,
    ) -> AdapterResponse:
        """Создать успешный AdapterResponse."""
        return AdapterResponse(
            status="ok",
            intent=request.intent,
            data=data,
            capability_used=capability,
            model_used=model,
        )

    def _err_response(
        self,
        request: AdapterRequest,
        errors: List[str***REMOVED***,
        warnings: Optional[List[str***REMOVED******REMOVED*** = None,
    ) -> AdapterResponse:
        """Создать ошибочный AdapterResponse (fail-safe)."""
        return AdapterResponse(
            status="error",
            intent=request.intent,
            errors=errors,
            warnings=warnings or [***REMOVED***,
        )

    def __repr__(self) -> str:
        return (
            f"IntegrationAdapter(id={self.adapter_id!r***REMOVED***, "
            f"dir={self.direction.value***REMOVED***, "
            f"auth={self.auth.method.value***REMOVED***)"
        )