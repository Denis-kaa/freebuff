"""
freebuff/core_02/router.py — Capability-based LLM Router.

Вместо if-else с hardcoded именами моделей:
- Каждая модель описывает свои capabilities
- Роутер выбирает модель по совпадению required_capabilities
- Чисто data-driven, без привязки к конкретным провайдерам

Usage:
    from freebuff.core_02.router import SmartRouter, ModelCatalog
    router = SmartRouter(catalog)
    decision = router.route(required_capabilities=["code"])
    print(f"Using {decision.model} ({decision.reason})")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════


class Provider(str, Enum):
    """Модели-провайдеры."""
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    GROQ = "groq"
    SAMBANOVA = "sambanova"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"  # local


class Preference(str, Enum):
    """Предпочтения пользователя для роутинга."""
    LOCAL = "local"       # предпочитать локальные модели
    CLOUD = "cloud"       # предпочитать облачные модели
    FAST = "fast"         # минимальная задержка
    CHEAP = "cheap"       # минимальная стоимость
    BALANCED = "balanced" # баланс (по умолчанию)


# ═══════════════════════════════════════════════════════════════
# Data models
# ═══════════════════════════════════════════════════════════════


@dataclass
class ModelEntry:
    """Одна модель в каталоге.

    Каждая модель описывает свои capabilities — список строк.
    Роутер использует их для выбора, без hardcoded правил.
    """
    name: str
    provider: Provider
    max_tokens: int = 4096
    cost_per_1k: float = 0.0           # USD per 1K tokens
    latency_ms: int = 1000             # estimated latency
    capabilities: List[str] = field(default_factory=list)  # ["code", "vision", "tools"]


@dataclass
class RouteDecision:
    """Результат роутинга: выбранная модель."""
    """Результат роутинга."""
    model: str
    provider: Provider
    reason: str
    fallback_used: bool = False


# ═══════════════════════════════════════════════════════════════
# Model Catalog
# ═══════════════════════════════════════════════════════════════


class ModelCatalog:
    """Реестр моделей с capability profiles.

    Позволяет:
    - Добавлять/искать модели
    - Фильтровать по провайдеру, capabilities
    - Создавать дефолтный каталог для окружения пользователя
    """

    def __init__(self, entries: Optional[List[ModelEntry]] = None):
        self._entries: Dict[str, ModelEntry] = {}
        if entries:
            for e in entries:
                self._entries[e.name] = e

    def add(self, entry: ModelEntry) -> None:
        self._entries[entry.name] = entry

    def get(self, name: str) -> Optional[ModelEntry]:
        return self._entries.get(name)

    def list_by_provider(self, provider: Provider) -> List[ModelEntry]:
        return [e for e in self._entries.values() if e.provider == provider]

    def list_by_capability(self, capability: str) -> List[ModelEntry]:
        return [e for e in self._entries.values() if capability in e.capabilities]

    @property
    def all(self) -> List[ModelEntry]:
        return list(self._entries.values())

    def match(
        self,
        required: List[str],
        max_tokens: int = 0,
    ) -> List[Tuple[ModelEntry, int]]:
        """Возвращает модели, отсортированные по совпадению capabilities.

        Args:
            required: список требуемых capabilities (может быть пустым)
            max_tokens: минимальный контекст, который должна поддерживать модель.
                0 = без фильтрации.

        Returns:
            Список кортежей (model, match_score), от лучшего к худшему.
            match_score = сколько из required capabilities есть у модели.
        """
        required_set = set(required) if required else set()
        scored = []

        for entry in self._entries.values():
            # Фильтр: модель должна вмещать контекст
            if max_tokens > 0 and entry.max_tokens < max_tokens:
                continue

            if required:
                caps = set(entry.capabilities)
                matches = len(required_set & caps)
            else:
                matches = 0

            scored.append((entry, matches))

        # Сортируем: сначала больше совпадений, потом быстрее/дешевле
        scored.sort(key=lambda x: (-x[1], x[0].latency_ms, x[0].cost_per_1k))

        return scored

    @classmethod
    def default(cls) -> ModelCatalog:
        """Дефолтный каталог для среды разработчика.

        Каждая модель имеет capability profile — список того, что она умеет.
        Никаких if-else в роутере — только сравнение строк.
        """
        return cls([
            # ── Локальные модели ──────────────────────────────
            ModelEntry("qwen2.5:1.5b", Provider.OLLAMA,
                       max_tokens=4096, latency_ms=200, cost_per_1k=0.0,
                       capabilities=[
                           "local",        # работает локально, без интернета
                           "fast",         # низкая задержка
                           "code",         # умеет писать код
                           "summarize",    # умеет суммаризировать
                       ]),
            ModelEntry("qwen2.5:0.5b", Provider.OLLAMA,
                       max_tokens=2048, latency_ms=100, cost_per_1k=0.0,
                       capabilities=[
                           "local",
                           "fast",
                           "router",       # достаточно для роутинга задач
                           "classify",     # классификация
                       ]),
            # ── Облачные модели ───────────────────────────────
            ModelEntry("deepseek-v4-flash", Provider.DEEPSEEK,
                       max_tokens=128000, latency_ms=2000, cost_per_1k=0.00015,
                       capabilities=[
                           "code",
                           "reasoning",
                           "plan",
                           "refactor",
                           "explain",
                           "summarize",    # v5.189.49+: backup capability для LLM-ролей
                       ]),
            ModelEntry("deepseek-v4-pro", Provider.DEEPSEEK,
                       max_tokens=128000, latency_ms=3000, cost_per_1k=0.002,
                       capabilities=[
                           "code",
                           "reasoning",
                           "deep",         # глубокий анализ
                           "architecture", # архитектурное проектирование
                           "plan",
                           "review",
                           "diagnose",     # диагностика окружения
                           "validate",     # валидация
                           "report",       # отчётность
                           "research",     # веб-исследование (research_web, Missing Capability #6)
                           "estimation",   # оценка сложности LISA-3 (lisa_estimator, Missing Capability #7)
                           "article_generation",  # Content Factory (Phase 9, промт 092)
                           "book_generation",     # Content Factory (Phase 9, промт 092)
                           "report_generation",   # Content Factory (Phase 9, промт 092)
                       ]),
            ModelEntry("gemini-2.5-flash", Provider.GEMINI,
                       max_tokens=1048576, latency_ms=1500, cost_per_1k=0.00015,
                       capabilities=[
                           "code",
                           "vision",       # понимает изображения
                           "tools",        # умеет работать с инструментами
                           "long_context", # 1M+ токенов
                           "reasoning",
                           "multimodal",
                           "research",     # веб-исследование (research_web, Missing Capability #6)
                           "estimation",   # оценка сложности LISA-3 (lisa_estimator, Missing Capability #7)
                           "article_generation",  # Content Factory (Phase 9, промт 092)
                           "book_generation",     # Content Factory (Phase 9, промт 092)
                           "report_generation",   # Content Factory (Phase 9, промт 092)
                           "summarize",    # v5.189.49+: backup capability для LLM-ролей
                           "explain",      # v5.189.49+: backup capability для LLM-ролей
                       ]),
            ModelEntry("llama-3.3-70b-versatile", Provider.GROQ,
                       max_tokens=128000, latency_ms=800, cost_per_1k=0.00059,
                       capabilities=[
                           "fast",         # самая быстрая облачная
                           "code",
                           "reasoning",
                           "instruct",     # хорошо следует инструкциям
                           "summarize",    # v5.189.49+: backup capability, LLM-роли cross-cloud
                           "explain",      # v5.189.49+: backup capability, LLM-роли cross-cloud
                       ]),
        ])


# ═══════════════════════════════════════════════════════════════
# SmartRouter
# ═══════════════════════════════════════════════════════════════


class SmartRouter:
    """Capability-based LLM Router.

    Никаких if-else с именами моделей.
    Вся логика — data-driven: сравниваем capabilities, выбираем лучшее совпадение.
    """

    def __init__(
        self,
        catalog: ModelCatalog,
        fallback: str = "gemini-2.5-flash",
        provider_available: Optional[Callable[[Provider], bool]] = None,
    ):
        self.catalog = catalog
        self.fallback = fallback
        #: Предикат доступности провайдера (облачный = есть ключ; локальный =
        #: отвечает). None = все провайдеры считаются доступными (обратная
        #: совместимость). Применяется в route() до выбора лучшей модели —
        #: cloud-first, когда локальная модель недоступна (ANTI-6b defense).
        self.provider_available = provider_available

    def _filter_available(
        self,
        scored: List[Tuple[ModelEntry, int]],
    ) -> List[Tuple[ModelEntry, int]]:
        """Оставить только модели доступных провайдеров.

        Если ни один провайдер не доступен — вернуть исходный список
        (graceful degradation: вызывающий слой всё равно сделает fail-safe
        при попытке вызова недоступной модели).
        """
        if self.provider_available is None:
            return scored
        available = [
            (e, s) for e, s in scored if self.provider_available(e.provider)
        ]
        return available if available else scored

    def route(
        self,
        required_capabilities: Optional[List[str]] = None,
        max_tokens_needed: int = 0,
        preference: Preference = Preference.BALANCED,
    ) -> RouteDecision:
        """Выбирает лучшую модель по capabilities.

        Args:
            required_capabilities: что нужно модели уметь
                (например ["code", "vision"] или ["local", "fast"]).
                Если указано — выбор идёт по совпадению capabilities.
                Preference учитывается только при равном score.
            max_tokens_needed: сколько токенов нужно обработать
            preference: LOCAL / CLOUD / FAST / CHEAP / BALANCED.
                Учитывается только если required_capabilities не указаны.

        Returns:
            RouteDecision с выбранной моделью.

        Raises:
            RuntimeError: если ни одна модель не доступна.
        """
        req = required_capabilities or []

        # 1. Capability-based matching (availability-aware: cloud-first, когда
        #    локальный провайдер недоступен — ANTI-6b defense).
        scored = self._filter_available(
            self.catalog.match(req, max_tokens=max_tokens_needed)
        )

        if scored:
            best_score = scored[0][1]

            # Если есть совпадения — используем лучшую
            if best_score > 0:
                # CON-65 (v5.189.52): cloud-first среди tied-score моделей.
                # `_filter_available` уже убрал недоступных облачных провайдеров
                # (нет ключа → не в списке); среди выживших с равным best_score
                # предпочитаем облако (не-OLLAMA) над локальным qwen — ANTI-6b
                # defense против latency tie-break (local ~200ms < cloud ~800ms+).
                # Гейт по `provider_available`: cloud-first обоснован только когда
                # известна доступность (gateway передаёт provider_available).
                # Standalone `SmartRouter()` без предиката сохраняет прежний
                # pure-latency tie-break (backward compat: нельзя утверждать
                # «у облака есть ключ», не имея предиката).
                top_tier = [e for e, s in scored if s == best_score]
                if self.provider_available is not None:
                    cloud_tier = [e for e in top_tier if e.provider != Provider.OLLAMA]
                    best_entry = (cloud_tier or top_tier)[0]
                else:
                    best_entry = top_tier[0]
                return RouteDecision(
                    model=best_entry.name,
                    provider=best_entry.provider,
                    reason=f"capability_match:{best_score}/{len(req)}",
                    fallback_used=False,
                )

            # Если требований не было — выбираем по предпочтению
            if not req:
                entry = self._route_by_preference(scored, preference)
                return RouteDecision(
                    model=entry.name,
                    provider=entry.provider,
                    reason=f"preference:{preference.value}",
                    fallback_used=False,
                )

        # 2. Fallback: требования не совпали ни с одной моделью
        # Пробуем модель с максимальными tokens (чтобы хотя бы обработала)
        all_models = self._filter_available(
            self.catalog.match([], max_tokens=0)
        )

        if all_models:
            # Берём модель с самой большой ёмкостью контекста
            by_context = sorted(
                all_models, key=lambda x: -x[0].max_tokens
            )
            entry = by_context[0][0]
            return RouteDecision(
                model=entry.name,
                provider=entry.provider,
                reason=f"fallback:no_capability_match (needed {req}, best effort)",
                fallback_used=True,
            )

        # 3. Самая последняя надежда — fallback из конфига
        # (отдельная переменная + None-guard: mypy-конфликт Optional vs ModelEntry)
        fallback_entry = self.catalog.get(self.fallback)
        if fallback_entry:
            return RouteDecision(
                model=fallback_entry.name,
                provider=fallback_entry.provider,
                reason="fallback:last_resort",
                fallback_used=True,
            )

        raise RuntimeError("No models available in catalog")

    def _route_by_preference(
        self,
        scored: List[Tuple[ModelEntry, int]],
        preference: Preference,
    ) -> ModelEntry:
        """Выбирает модель на основе предпочтения (когда нет требований)."""
        if preference == Preference.LOCAL:
            # Сначала локальные, потом всё остальное
            local = [e for e, _ in scored if e.provider == Provider.OLLAMA]
            if local:
                return local[0]
        elif preference == Preference.CLOUD:
            cloud = [e for e, _ in scored if e.provider != Provider.OLLAMA]
            if cloud:
                return cloud[0]
        elif preference == Preference.FAST:
            # Сортируем по latency ascending
            by_latency = sorted(scored, key=lambda x: x[0].latency_ms)
            return by_latency[0][0]
        elif preference == Preference.CHEAP:
            # Сортируем по cost ascending
            by_cost = sorted(scored, key=lambda x: x[0].cost_per_1k)
            return by_cost[0][0]

        # BALANCED: берём первую (уже отсортирована)
        return scored[0][0]
