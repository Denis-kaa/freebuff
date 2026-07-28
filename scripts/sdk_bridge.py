"""
SDK Bridge: freebuff.core ↔ termux-ai-agent

Интеграция унифицированного SDK с termux-ai-agent:
  - SmartRouter → router adapter для агента
  - AgentResult ↔ ToolResult конвертация
  - IAgent → агентский контракт

Использование в termux-ai-agent main.py:
    from freebuff.scripts.sdk_bridge import SmartRouterAdapter
    adapter = SmartRouterAdapter()
    # Передать в run() как router=
    result = run(query, router=adapter)
"""

from __future__ import annotations

import sys
***REMOVED***
from typing import Any, Dict, Optional

# Добавляем freebuff в путь (если не установлен как пакет)
FREEBUFF = Path("/storage/emulated/0/PROJECTS/workstation/freebuff")
if str(FREEBUFF) not in sys.path:
    sys.path.insert(0, str(FREEBUFF))

from freebuff.core.interfaces import AgentResult, TaskStatus
from freebuff.core.router import SmartRouter, ModelCatalog


class SmartRouterAdapter:
    """Адаптер: freebuff SmartRouter → termux-ai-agent Router.

    Реализует контракт termux-ai-agent:
        route(NormalizedRequest) → RoutingDecision

    Может быть передан в run(router=adapter).
    """

    def __init__(self, catalog: Optional[ModelCatalog***REMOVED*** = None):
        self._catalog = catalog or ModelCatalog.default()
        self._router = SmartRouter(self._catalog)

    def route(self, request: Any) -> Any:
        """Совместимый с termux-ai-agent интерфейс.

        Принимает NormalizedRequest, возвращает RoutingDecision-совместимый dict.
        Использует capability-based роутинг.
        """
        from freebuff.core.router import Preference

        # Извлекаем текст из NormalizedRequest
        text = getattr(request, 'normalized_text', None) or getattr(request, 'raw_text', str(request)) or ""
        corr_id = getattr(request, 'correlation_id', 'unknown')

        # Определяем требуемые capabilities по тексту
        words = len(text.split())
        context_size = len(text)

        caps = [***REMOVED***
        if words < 10:
            caps = ["fast", "classify"***REMOVED***  # короткий запрос → быстрая классификация
        elif any(kw in text.lower() for kw in ["изображен", "картинк", "фото", "image", "picture"***REMOVED***):
            caps = ["vision", "multimodal", "reasoning"***REMOVED***
        elif any(kw in text.lower() for kw in ["архитектур", "спроектиру", "design", "architecture"***REMOVED***):
            caps = ["architecture", "reasoning", "plan"***REMOVED***
        elif words > 200:
            caps = ["code", "reasoning", "plan"***REMOVED***
        else:
            caps = ["code", "reasoning"***REMOVED***

        # Предпочтение: если текст маленький → local
        pref = Preference.LOCAL if words < 50 else Preference.BALANCED

        decision = self._router.route(
            required_capabilities=caps,
            max_tokens_needed=context_size,
            preference=pref,
        )

        # Возвращаем объект с attribute access (совместим с RoutingDecision)
        from types import SimpleNamespace
        return SimpleNamespace(
            correlation_id=corr_id,
            tool_name=decision.model,
            confidence=min(1.0, len(caps) / 3),
            method="capability_router",
            matched_keywords=caps,
            llm_calls_used=0,
        )


def result_to_agent_result(
    tool_result: Dict[str, Any***REMOVED***,
    agent_name: str = "termux-ai-agent",
) -> AgentResult:
    """Конвертировать ToolResult (dict) → AgentResult."""
    status_map = {
        "ok": TaskStatus.OK,
        "partial": TaskStatus.WARN,
        "error": TaskStatus.ERROR,
    ***REMOVED***
    raw_status = tool_result.get("status", "ok")
    status = status_map.get(raw_status, TaskStatus.ERROR)

    return AgentResult(
        status=status,
        agent=agent_name,
        task=tool_result.get("tool", "unknown"),
        data=tool_result.get("data"),
        warnings=tool_result.get("warnings", [***REMOVED***),
        errors=[tool_result["error"***REMOVED******REMOVED*** if tool_result.get("error") else [***REMOVED***,
        meta={
            "duration_ms": tool_result.get("duration_ms"),
            "llm_calls": tool_result.get("llm_calls"),
        ***REMOVED***,
    )


def agent_result_to_dict(result: AgentResult) -> Dict[str, Any***REMOVED***:
    """Конвертировать AgentResult → dict для termux-ai-agent."""
    return {
        "status": result.status.value,
        "tool": result.task,
        "data": result.data,
        "warnings": result.warnings,
        "error": result.errors[0***REMOVED*** if result.errors else None,
        "duration_ms": result.meta.get("duration_ms"),
        "llm_calls": result.meta.get("llm_calls"),
    ***REMOVED***


# ── Пример использования ────────────────────────────────────

if __name__ == "__main__":
    adapter = SmartRouterAdapter()

    # Симуляция NormalizedRequest
    class FakeRequest:
        correlation_id = "test-001"
        normalized_text = ""

    tests = [
        ("привет", "простой"),
        ("напиши функцию для парсинга JSON с обработкой ошибок", "средний"),
        ("разработай архитектуру микросервиса с event sourcing и CQRS", "сложный"),
    ***REMOVED***

    for query, label in tests:
        req = FakeRequest()
        req.normalized_text = query
        result = adapter.route(req)
        print(f"[{label***REMOVED******REMOVED*** {query[:50***REMOVED******REMOVED***... → {result['tool_name'***REMOVED******REMOVED*** (conf={result['confidence'***REMOVED***:.2f***REMOVED***)")
