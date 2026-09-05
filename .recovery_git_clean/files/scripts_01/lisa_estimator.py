"""scripts_01/lisa_estimator.py — Estimation capability (Tool: ``lisa_estimator``).

Missing Capability #7 (FACTORY_FORGE_ARCHITECTURE_V1.md §20, pompts_11/076_13_lisa_estimator_capability.md).
Research Factory → Research Forge → Estimation Engine. Результат: **LISA Report**
(``lisa_report.md`` + метрики) — оценка сложности проекта по фреймворку LISA-3
(AI-Native Complexity Estimator): engineering complexity, AI-native complexity,
verification burden, operational/production risk, AI suitability + вердикт.

**Детерминизм:** без внешних LLM-вызовов — оценка по эвристикам/сигналам из
описания проекта (пригодно для unit-тестов). LLM-синтез — будущий этап
(Estimation Forge с Engines, ROLE_FORGE_MATRIX §8 Q2).

**Безопасность:** вход читается только read-only, без ``exec``/``eval`` /
``shell=True`` / ``os.system``; валидация типов.

**Fail-safe:** пустой/битый вход → degraded-отчёт ``estimated: false`` + exit 0
(как research_web: ``sources_checked: 0``).

Usage::

    python scripts_01/lisa_estimator.py "веб-платформа с каталогом и оплатой" --out lisa_report.md
    python scripts_01/lisa_estimator.py --input brief.md --json
    python scripts_01/lisa_estimator.py "описание" --calibrate lisa_calibration.yaml --no-save
    python scripts_01/lisa_estimator.py "описание" --domain xlsx --no-save
    python scripts_01/lisa_estimator.py "описание" --calibrate proj.yaml --save-calibration xlsx --no-save
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
***REMOVED***
from typing import Any

DEFAULT_OUT = "lisa_report.md"

# Каноничное хранилище весов калибровки LISA-3 (платформенный уровень).
# Единый источник истины для доменных приоров: накапливаются между проектами
# и переиспользуются через `--domain <name>`. Обновляется ролью retrospective
# (Evolution Forge) или `--save-calibration <name>`.
DEFAULT_CALIBRATION_STORE: Path = (
    Path(__file__).resolve().parent.parent / "data_13" / "lisa_calibration.yaml"
)

# Оси LISA-3 (порядок фиксирован — используется в Scores / отчёте / JSON).
AXES = (
    "engineering_complexity",
    "ai_native_complexity",
    "verification_burden",
    "operational_risk",
    "production_risk",
    "ai_suitability",
)

# Ключи JSON-схемы DoD (076_13_lisa_estimator_capability §5.2): description, scores{...***REMOVED***, verdict, calibrated, degraded
JSON_SCHEMA_KEYS = ("description", "scores", "verdict", "calibrated", "degraded")


# ═══════════════════════════════════════════════════════════════════
# Сигналы LISA-3 (детерминированные эвристики, без LLM)
# ═══════════════════════════════════════════════════════════════════
#
# Для каждой оси — кортежи (подстрока, вес). Подстрока ищется в lower-копии
# описания («in»-матчинг, устойчив к морфологии). Положительные сигналы
# повышают оценку оси, для ai_suitability есть и отрицательные (понижают).

AXIS_POSITIVE: dict[str, tuple[tuple[str, float***REMOVED***, ...***REMOVED******REMOVED*** = {
    "engineering_complexity": (
        ("api", 0.7),
        ("интеграц", 0.8),
        ("integrat", 0.8),
        ("webhook", 0.9),
        ("платеж", 1.0),
        ("payment", 1.0),
        ("оплат", 1.0),
        ("корзин", 0.8),
        ("cart", 0.8),
        ("auth", 0.9),
        ("авториз", 0.9),
        ("аутентиф", 0.9),
        ("роли", 0.7),
        ("permission", 0.7),
        ("realtime", 1.0),
        ("websocket", 1.0),
        ("в реальном времени", 1.0),
        ("миллион", 0.8),
        ("масштаб", 0.6),
        ("scale", 0.6),
        ("высоконагруж", 1.0),
        ("high-load", 1.0),
        ("база данных", 0.6),
        ("database", 0.6),
        ("многопользовательск", 0.9),
        ("multi-tenant", 0.9),
        ("бэкенд", 0.5),
        ("backend", 0.5),
        ("микросервис", 1.1),
        ("microservice", 1.1),
    ),
    "ai_native_complexity": (
        ("нейросет", 1.0),
        ("neural", 1.0),
        ("llm", 1.0),
        ("gpt", 0.9),
        ("генерац", 1.0),
        ("generat", 1.0),
        ("классификац", 1.0),
        ("classif", 1.0),
        ("рекомендац", 1.0),
        ("recommend", 1.0),
        ("чат-бот", 1.0),
        ("chatbot", 1.0),
        ("распознаван", 1.0),
        ("recogn", 1.0),
        ("анализ текста", 1.0),
        ("nlp", 1.0),
        ("семантик", 1.0),
        ("semantic", 1.0),
        ("сентимент", 1.0),
        ("sentiment", 1.0),
        ("искусственн", 1.0),
        ("artificial intelligence", 1.0),
        ("ai-", 0.9),
        ("автогенерац", 1.2),
    ),
    "verification_burden": (
        ("безопасност", 1.0),
        ("security", 1.0),
        ("финанс", 1.0),
        ("financ", 1.0),
        ("точн", 0.8),
        ("accur", 0.8),
        ("атомарн", 1.0),
        ("согласован", 0.8),
        ("consisten", 0.8),
        ("верификац", 1.0),
        ("тестирован", 0.6),
        ("границ", 0.6),
        ("edge case", 0.8),
        ("конкурентн", 0.9),
        ("concurren", 0.9),
    ),
    "operational_risk": (
        ("внешн сервис", 0.8),
        ("third-party", 0.8),
        ("облак", 0.6),
        ("cloud", 0.6),
        ("деплой", 0.8),
        ("deploy", 0.8),
        ("мониторинг", 0.7),
        ("monitor", 0.7),
        ("креденциал", 0.9),
        ("credential", 0.9),
        ("секрет", 0.8),
        ("secret", 0.8),
        ("масштабир", 0.7),
        ("scalab", 0.7),
        ("внешний api", 0.8),
    ),
    "production_risk": (
        ("production", 1.0),
        ("uptime", 1.2),
        ("доступн", 0.8),
        ("sla", 1.2),
        ("отказоустойчив", 1.2),
        ("failover", 1.2),
        ("репликац", 1.0),
        ("нагрузк", 0.9),
        ("load", 0.7),
        ("бесперебойн", 1.0),
    ),
    "ai_suitability": (  # выше = проект лучше подходит для AI-реализации
        ("crud", 1.0),
        ("каталог", 0.8),
        ("форма", 0.6),
        ("список", 0.5),
        ("лендинг", 0.9),
        ("landing", 0.9),
        ("блог", 0.8),
        ("blog", 0.8),
        ("контент", 0.8),
        ("content", 0.8),
        ("типов", 0.5),
        ("стандартн", 0.5),
        ("документ", 0.6),
        ("document", 0.6),
        ("таблиц", 0.5),
        ("импорт", 0.6),
        ("экспорт", 0.6),
        ("копия", 0.5),
        ("import", 0.6),
    ),
***REMOVED***

AXIS_NEGATIVE: dict[str, tuple[tuple[str, float***REMOVED***, ...***REMOVED******REMOVED*** = {
    "ai_suitability": (  # понижают пригодность для AI-реализации
        ("hardware", -1.0),
        ("желез", -1.0),
        ("embedded", -1.0),
        ("микроконтроллер", -1.0),
        ("легаси", -0.8),
        ("legacy", -0.8),
        ("закрытый протокол", -0.8),
        ("proprietary", -0.8),
        ("строгий регламент", -0.6),
        ("compliance", -0.6),
        ("безопасност", -0.4),
        ("security", -0.4),
        ("точность", -0.4),
        ("критичн", -0.5),
    ),
***REMOVED***


# ═══════════════════════════════════════════════════════════════════
# Data models
# ═══════════════════════════════════════════════════════════════════


@dataclass
class Scores:
    """Оценки по шести осям LISA-3 (0–10)."""

    engineering_complexity: float = 0.0
    ai_native_complexity: float = 0.0
    verification_burden: float = 0.0
    operational_risk: float = 0.0
    production_risk: float = 0.0
    ai_suitability: float = 0.0

    def to_dict(self) -> dict[str, float***REMOVED***:
        return {
            "engineering_complexity": self.engineering_complexity,
            "ai_native_complexity": self.ai_native_complexity,
            "verification_burden": self.verification_burden,
            "operational_risk": self.operational_risk,
            "production_risk": self.production_risk,
            "ai_suitability": self.ai_suitability,
        ***REMOVED***


@dataclass
class LisaReport:
    """Результат оценки (LISA Report)."""

    description: str
    scores: Scores = field(default_factory=Scores)
    verdict: str = "NO-GO"
    calibrated: bool = False
    degraded: bool = False
    estimated: bool = True
    rationale: dict[str, list[str***REMOVED******REMOVED*** = field(default_factory=dict)
    warnings: list[str***REMOVED*** = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any***REMOVED***:
        return {
            "description": self.description,
            "scores": self.scores.to_dict(),
            "verdict": self.verdict,
            "calibrated": self.calibrated,
            "degraded": self.degraded,
            "estimated": self.estimated,
            "rationale": self.rationale,
            "warnings": self.warnings,
            "generated_at": self.generated_at,
        ***REMOVED***

    def to_markdown(self) -> str:
        """Markdown-отчёт (файл lisa_report.md по умолчанию)."""
        lines = [
            "# LISA Report (LISA-3 AI-Native Complexity Estimator)",
            "",
            f"**Описание:** {self.description or '(пусто)'***REMOVED***",
            f"**Сгенерирован:** {self.generated_at***REMOVED***",
            f"**Оценено:** {'да' if self.estimated else 'нет (degraded)'***REMOVED***",
            f"**Калибровка:** {'да' if self.calibrated else 'нет (дефолтные веса)'***REMOVED***",
            "",
            "## Оценки осей (0–10)",
            "",
            "| Ось | Оценка | Признаки |",
            "|-----|:------:|----------|",
        ***REMOVED***
        axis_labels = {
            "engineering_complexity": "Engineering complexity",
            "ai_native_complexity": "AI-native complexity",
            "verification_burden": "Verification burden",
            "operational_risk": "Operational risk",
            "production_risk": "Production risk",
            "ai_suitability": "AI suitability",
        ***REMOVED***
        for axis in AXES:
            value = getattr(self.scores, axis)
            signals = self.rationale.get(axis, [***REMOVED***)
            hint = ", ".join(signals[:5***REMOVED***) if signals else "_нет явных сигналов_"
            lines.append(f"| {axis_labels[axis***REMOVED******REMOVED*** | {value:.1f***REMOVED*** | {hint***REMOVED*** |")

        lines += [
            "",
            "## Вердикт",
            "",
            f"**{self.verdict***REMOVED***** — "
            + {
                "GO": "проект пригоден для AI-реализации.",
                "COND": "условно пригоден: требуется доработка/ручные этапы.",
                "NO-GO": "не пригоден для AI-реализации на текущем описании.",
            ***REMOVED***[self.verdict***REMOVED***,
            "",
            "## Предупреждения",
            "",
        ***REMOVED***
        if self.warnings:
            for w in self.warnings:
                lines.append(f"- ⚠️ {w***REMOVED***")
        else:
            lines.append("_Нет._")
        lines.append("")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Scoring (детерминированный пайплайн)
# ═══════════════════════════════════════════════════════════════════


def _score_axis(text: str, axis: str) -> tuple[float, list[str***REMOVED******REMOVED***:
    """Оценка одной оси по сигналам описания. Возвращает (score 0–10, matched).

    Args:
        text: описание проекта (lower-копия строится внутри).
        axis: одна из AXES.

    Returns:
        Кортеж (оценка 0–10 с округлением 0.1, список сработавших сигналов).
    """
    low = text.lower()
    matched: list[str***REMOVED*** = [***REMOVED***
    total = 0.0
    for term, weight in AXIS_POSITIVE.get(axis, ()):
        if term in low:
            total += weight
            matched.append(term)
    for term, weight in AXIS_NEGATIVE.get(axis, ()):
        if term in low:
            total += weight
            matched.append(term)
    return round(max(0.0, min(10.0, total)), 1), matched


def _verdict(scores: Scores) -> str:
    """Вердикт по оценкам: GO / COND / NO-GO (детерминированно)."""
    if (
        scores.ai_suitability >= 6.0
        and scores.engineering_complexity <= 7.0
        and scores.production_risk <= 6.0
    ):
        return "GO"
    if scores.ai_suitability >= 4.0:
        return "COND"
    return "NO-GO"


def _load_calibration(path: str) -> dict[str, float***REMOVED***:
    """Загрузить калибровку весов осей из YAML-файла.

    Формат::

        weights:
          engineering_complexity: 1.2
          ai_suitability: 0.8

    Raises:
        ValueError: файл битый / не mapping / weights не mapping.
    """
    import yaml  # local import — PyYAML нужен только для --calibrate

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("калибровка должна быть YAML mapping")
    weights_raw = raw.get("weights") or {***REMOVED***
    if not isinstance(weights_raw, dict):
        raise ValueError("калибровка: секция 'weights' должна быть mapping")
    out: dict[str, float***REMOVED*** = {***REMOVED***
    for axis in AXES:
        w = weights_raw.get(axis)
        if isinstance(w, (int, float)):
            out[axis***REMOVED*** = float(w)
    return out


def _load_calibration_store(
    path: str | Path,
) -> tuple[dict[str, float***REMOVED***, dict[str, dict[str, float***REMOVED******REMOVED******REMOVED***:
    """Загрузить каноничное хранилище весов (data_13/lisa_calibration.yaml).

    Returns:
        (weights, domains):
          - weights — глобальные множители осей (только заданные);
          - domains — {name: {axis: multiplier***REMOVED******REMOVED*** доменные приоры.
        Fail-safe: отсутствующий/битый файл → ({***REMOVED***, {***REMOVED***) (caller добавляет warning).
    """
    import yaml  # local import — PyYAML нужен только для калибровки

    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — fail-safe по дизайну
        return {***REMOVED***, {***REMOVED***
    if not isinstance(raw, dict):
        return {***REMOVED***, {***REMOVED***

    weights_raw = raw.get("weights") or {***REMOVED***
    weights: dict[str, float***REMOVED*** = {***REMOVED***
    if isinstance(weights_raw, dict):
        for axis in AXES:
            w = weights_raw.get(axis)
            if isinstance(w, (int, float)):
                weights[axis***REMOVED*** = float(w)

    domains_raw = raw.get("domains") or {***REMOVED***
    domains: dict[str, dict[str, float***REMOVED******REMOVED*** = {***REMOVED***
    if isinstance(domains_raw, dict):
        for name, entry in domains_raw.items():
            if not isinstance(entry, dict):
                continue
            dom: dict[str, float***REMOVED*** = {***REMOVED***
            for axis in AXES:
                w = entry.get(axis)
                if isinstance(w, (int, float)):
                    dom[axis***REMOVED*** = float(w)
            if dom:
                domains[str(name)***REMOVED*** = dom
    return weights, domains


def _merge_weights(
    base: dict[str, float***REMOVED***, override: dict[str, float***REMOVED***
) -> dict[str, float***REMOVED***:
    """Слить глобальные веса + доменное переопределение (override выигрывает)."""
    merged = dict(base)
    merged.update(override)
    return merged


def _save_calibration_to_store(
    name: str, weights: dict[str, float***REMOVED***, path: str | Path
) -> None:
    """Сохранить доменные веса в каноничное хранилище под именем ``name``.

    Merge-семантика: читает существующий файл (если есть), обновляет
    ``domains[name***REMOVED***``, пишет обратно атомарно (.tmp + replace). Существующие
    домены и глобальные веса не теряются.
    """
    import yaml  # local import

    p = Path(path)
    existing: dict[str, Any***REMOVED*** = {***REMOVED***
    if p.is_file():
        try:
            loaded = yaml.safe_load(p.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except Exception:  # noqa: BLE001 — fail-safe: перезапишем заново
            existing = {***REMOVED***

    if not isinstance(existing.get("weights"), dict):
        existing["weights"***REMOVED*** = {axis: 1.0 for axis in AXES***REMOVED***
    domains = existing.get("domains")
    if not isinstance(domains, dict):
        domains = {***REMOVED***
    domains[name***REMOVED*** = {axis: float(weights.get(axis, 1.0)) for axis in AXES***REMOVED***
    existing["domains"***REMOVED*** = domains
    existing.setdefault("version", "1.0")

    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(
        yaml.safe_dump(existing, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    tmp.replace(p)


# ═══════════════════════════════════════════════════════════════════
# Main API (076_13_lisa_estimator_capability §3.1)
# ═══════════════════════════════════════════════════════════════════


def lisa_estimator(
    description: str,
    out: str | None = None,
    calibrate: str | None = None,
    save: bool = True,
    domain: str | None = None,
    save_calibration: str | None = None,
    calibration_store: str | None = None,
) -> LisaReport:
    """Оценить сложность проекта по LISA-3. Возвращает LisaReport.

    Args:
        description: описание проекта / ТЗ (строка).
        out: путь файла отчёта (default lisa_report.md при save=True).
        calibrate: путь к lisa_calibration.yaml (веса осей; опционально).
        save: записать ли markdown-отчёт (False = dry-run / --no-save).
        domain: имя домена из каноничного хранилища (domains.<name>;
            merge поверх глобальных weights; опционально).
        save_calibration: имя домена, под которым сохранить текущие веса
            (из calibrate/domain) в каноничное хранилище (опционально).
        calibration_store: путь к каноничному хранилищу (default
            DEFAULT_CALIBRATION_STORE = data_13/lisa_calibration.yaml).

    Fail-safe: пустой/битый вход → degraded-отчёт ``estimated: false``.
    Детерминированно: без LLM-вызовов, эвристики по сигналам.
    """
    description = (description or "").strip()
    warnings: list[str***REMOVED*** = [***REMOVED***

    if not description:
        report = LisaReport(
            description="",
            scores=Scores(),
            verdict="NO-GO",
            calibrated=False,
            degraded=True,
            estimated=False,
            rationale={axis: [***REMOVED*** for axis in AXES***REMOVED***,
            warnings=["пустое описание: оценка невозможна (degraded)"***REMOVED***,
        )
        if save:
            _write_report(report, out or DEFAULT_OUT)
        _emit_events(report)
        return report

    rationale: dict[str, list[str***REMOVED******REMOVED*** = {***REMOVED***
    raw: dict[str, float***REMOVED*** = {***REMOVED***
    for axis in AXES:
        score, matched = _score_axis(description, axis)
        raw[axis***REMOVED*** = score
        rationale[axis***REMOVED*** = matched

    calibrated = False
    weights: dict[str, float***REMOVED*** = {***REMOVED***
    if calibrate and domain:
        warnings.append(
            f"--domain {domain!r***REMOVED*** игнорируется: задан --calibrate "
            f"(приоритет у --calibrate)"
        )
    if calibrate:
        try:
            weights = _load_calibration(calibrate)
            if weights:
                calibrated = True
        except Exception as exc:  # noqa: BLE001 — fail-safe по дизайну
            warnings.append(
                f"калибровка {calibrate***REMOVED*** не загружена: {type(exc).__name__***REMOVED***: {exc***REMOVED***"
            )
    elif domain:
        store_path = calibration_store or str(DEFAULT_CALIBRATION_STORE)
        try:
            global_weights, domains = _load_calibration_store(store_path)
            dom_weights = domains.get(domain)
            if dom_weights:
                weights = _merge_weights(global_weights, dom_weights)
                calibrated = True
            elif domain in domains:
                warnings.append(
                    f"домен {domain!r***REMOVED*** найден, но без числовых весов"
                )
            else:
                warnings.append(
                    f"домен {domain!r***REMOVED*** не найден в калибровке {store_path***REMOVED***"
                )
        except Exception as exc:  # noqa: BLE001 — fail-safe по дизайну
            warnings.append(
                f"калибровка {store_path***REMOVED*** не загружена: "
                f"{type(exc).__name__***REMOVED***: {exc***REMOVED***"
            )

    if weights:
        for axis, w in weights.items():
            raw[axis***REMOVED*** = round(max(0.0, min(10.0, raw[axis***REMOVED*** * w)), 1)

    if save_calibration:
        store_path = calibration_store or str(DEFAULT_CALIBRATION_STORE)
        if weights:
            try:
                _save_calibration_to_store(save_calibration, weights, store_path)
            except Exception as exc:  # noqa: BLE001 — fail-safe по дизайну
                warnings.append(
                    f"сохранение калибровки {save_calibration!r***REMOVED*** не удалось: "
                    f"{type(exc).__name__***REMOVED***: {exc***REMOVED***"
                )
        else:
            warnings.append(
                f"--save-calibration требует --calibrate или --domain "
                f"(нет весов для сохранения)"
            )

    scores = Scores(
        engineering_complexity=raw["engineering_complexity"***REMOVED***,
        ai_native_complexity=raw["ai_native_complexity"***REMOVED***,
        verification_burden=raw["verification_burden"***REMOVED***,
        operational_risk=raw["operational_risk"***REMOVED***,
        production_risk=raw["production_risk"***REMOVED***,
        ai_suitability=raw["ai_suitability"***REMOVED***,
    )

    report = LisaReport(
        description=description,
        scores=scores,
        verdict=_verdict(scores),
        calibrated=calibrated,
        degraded=False,
        estimated=True,
        rationale=rationale,
        warnings=warnings,
    )

    if save:
        _write_report(report, out or DEFAULT_OUT)
    _emit_events(report)
    return report


def _write_report(report: LisaReport, target: str) -> None:
    """Записать markdown-отчёт (идемпотентно, atomic-запись)."""
    path = Path(target)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(report.to_markdown(), encoding="utf-8")
    tmp.replace(path)


# ═══════════════════════════════════════════════════════════════════
# Observability (best-effort, никогда не валит основной поток)
# ═══════════════════════════════════════════════════════════════════


def _emit_events(report: LisaReport) -> None:
    """Записать событие в EventBus + Learning Loop (best-effort, не блокирует)."""
    try:
        from scripts_01.event_bus import Event, EventBus

        EventBus().publish(
            Event(
                type="lisa_estimator.completed",
                data={
                    "description": report.description[:200***REMOVED***,
                    "verdict": report.verdict,
                    "degraded": report.degraded,
                    "calibrated": report.calibrated,
                ***REMOVED***,
                source="lisa_estimator",
            )
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        from core_02.memory_store import MemoryStore

        MemoryStore().record_learning_event(
            trigger_id="lisa_estimator",
            context_snapshot={
                "description": report.description[:200***REMOVED***,
                "verdict": report.verdict,
                "degraded": report.degraded,
            ***REMOVED***,
            outcome="success" if report.estimated else "neutral",
        )
    except Exception:  # noqa: BLE001
        pass


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LISA-3 complexity estimator (Tool: lisa_estimator) — Research Factory"
    )
    parser.add_argument("description", nargs="?", default=None,
                        help="описание проекта/ТЗ (или --input / stdin)")
    parser.add_argument("--out", default=None, help=f"файл отчёта (default {DEFAULT_OUT***REMOVED***)")
    parser.add_argument("--json", action="store_true", help="stdout в JSON (для Scenario Engine/API)")
    parser.add_argument("--input", default=None,
                        help="вход из файла (brief.md / parsed_requirements.md)")
    parser.add_argument("--calibrate", default=None,
                        help="файл калибровки lisa_calibration.yaml (веса осей)")
    parser.add_argument("--domain", default=None,
                        help="доменные веса из data_13/lisa_calibration.yaml (domains.<name>)")
    parser.add_argument("--save-calibration", default=None, metavar="NAME",
                        help="сохранить веса (из --calibrate/--domain) в каноничное хранилище под именем NAME (независимо от --no-save)")
    parser.add_argument("--calibration-store", default=None,
                        help=f"путь к каноничному хранилищу (default {DEFAULT_CALIBRATION_STORE***REMOVED***)")
    parser.add_argument("--no-save", action="store_true", help="без записи файла (dry-run)")
    args = parser.parse_args()

    description = args.description or ""
    if args.input:
        try:
            description = (
                description + "\n" + Path(args.input).read_text(encoding="utf-8")
            ).strip()
        except OSError as exc:
            print(f"error: не удалось прочитать вход {args.input***REMOVED***: {exc***REMOVED***", file=sys.stderr)
            return 2
    if not description and not sys.stdin.isatty():
        description = sys.stdin.read().strip()

    report = lisa_estimator(
        description,
        out=args.out,
        calibrate=args.calibrate,
        save=not args.no_save,
        domain=args.domain,
        save_calibration=args.save_calibration,
        calibration_store=args.calibration_store,
    )

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(report.to_markdown())
    return 0


if __name__ == "__main__":
    sys.exit(main())
