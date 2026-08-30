"""Canary-режим P10: контролируемый live-прогон source через pipeline.

`run_canary` запускает существующий `run_offline_slice` с малым `limit`,
собирает отчёт и **никогда не включает постоянный polling**: каждый canary
делает ровно один срез. Live-доступ возможен только когда policy имеет
статус `ALLOWED` и `can_poll=True` (двойной гейт в адаптерах).

Для HH API токен передаётся через `make_token_http_get(env)` — адаптер не
хранит секрет. Для trudvsem токен не нужен.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.adapters.headhunter import HeadhunterAdapter, make_token_http_get
from app.adapters.trudvsem import TrudvsemAdapter
from app.domain import SearchProfile, SourcePolicy
from app.pipeline import PipelineResult, run_offline_slice


@dataclass(frozen=True, slots=True)
class CanaryReport:
    """Результат одного canary-прогона (P10)."""

    source_id: str
    source_status: str
    fetched: int
    new_publications: int
    accepted: int
    pending: int
    rejected: int
    delivered: int
    checkpoint: str | None
    ran_at: datetime
    error: str | None = None

    def summary(self) -> str:
        if self.error:
            return (
                f"canary {self.source_id} ERROR: {self.error} "
                f"(at {self.ran_at.isoformat()})"
            )
        return (
            f"canary {self.source_id} status={self.source_status} "
            f"fetched={self.fetched} new={self.new_publications} "
            f"accepted={self.accepted} pending={self.pending} "
            f"rejected={self.rejected} delivered={self.delivered} "
            f"checkpoint={self.checkpoint!r}"
        )


def build_source_adapter(
    *,
    source_id: str,
    policy: SourcePolicy,
    token: str | None = None,
    http_get: Any | None = None,
) -> Any:
    """Построить адаптер по source_id; token только для headhunter."""
    if source_id == "trudvsem":
        return TrudvsemAdapter(source_id, policy=policy, http_get=http_get)
    if source_id == "headhunter":
        http_get = http_get or (make_token_http_get(token) if token else None)
        return HeadhunterAdapter(source_id, policy=policy, http_get=http_get)
    raise ValueError(f"unknown live source: {source_id}")


async def run_canary(
    *,
    source_id: str,
    policy: SourcePolicy,
    profile: SearchProfile,
    storage: Any,
    checkpoint: Any,
    delivery: Any,
    owner_scope: str,
    limit: int = 10,
    token: str | None = None,
    http_get: Any | None = None,
) -> CanaryReport:
    """Один контролируемый live-прогон источника через pipeline.

    Ошибки адаптера/API не дают краха процесса — фиксируются в `error`
    отчёта, чтобы canary можно было прогонять в CI/manual без срыва.
    """
    ran_at = datetime.now(timezone.utc)
    try:
        adapter = build_source_adapter(
            source_id=source_id, policy=policy, token=token, http_get=http_get
        )
        result: PipelineResult = await run_offline_slice(
            adapter=adapter,
            profile=profile,
            storage=storage,
            checkpoint=checkpoint,
            delivery=delivery,
            owner_scope=owner_scope,
            limit=limit,
        )
    except Exception as exc:  # noqa: BLE001 — canary должен возвращать отчёт
        return CanaryReport(
            source_id=source_id,
            source_status=policy.status.value,
            fetched=0,
            new_publications=0,
            accepted=0,
            pending=0,
            rejected=0,
            delivered=0,
            checkpoint=None,
            ran_at=ran_at,
            error=str(exc),
        )
    return CanaryReport(
        source_id=result.source_id,
        source_status=policy.status.value,
        fetched=result.fetched,
        new_publications=result.new_publications,
        accepted=result.accepted,
        pending=result.pending,
        rejected=result.rejected,
        delivered=result.delivered,
        checkpoint=result.checkpoint,
        ran_at=ran_at,
    )


__all__ = ["CanaryReport", "build_source_adapter", "run_canary"]