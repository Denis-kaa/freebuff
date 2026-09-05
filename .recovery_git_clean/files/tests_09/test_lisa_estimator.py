"""Tests for scripts_01/lisa_estimator.py (Missing Capability #7, 076_13_lisa_estimator_capability)."""
from __future__ import annotations

import json
import sys
***REMOVED***

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts_01 import lisa_estimator as le

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_side_effects(monkeypatch):
    """Отключить observability-хуки (EventBus/MemoryStore пишут в реальную БД)."""
    monkeypatch.setattr(le, "_emit_events", lambda report: None)


# ─── функциональные: вход/выход ────────────────────────────────────────────────


def test_lisa_estimator_returns_report(tmp_path) -> None:
    """DoD §5.1: описание + --out → lisa_report.md с оценками осей и вердиктом."""
    out = tmp_path / "lisa_report.md"
    report = le.lisa_estimator(
        "веб-платформа с каталогом, корзиной и оплатой",
        out=str(out),
    )
    assert report.description
    assert report.estimated is True
    assert not report.degraded
    assert report.verdict in ("GO", "COND", "NO-GO")
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "LISA Report" in text
    assert "Engineering complexity" in text
    assert "AI-native complexity" in text
    assert "Вердикт" in text


def test_lisa_estimator_no_save_dry_run(tmp_path) -> None:
    """--no-save: save=False → файл не создаётся."""
    target = tmp_path / "should_not_exist.md"
    report = le.lisa_estimator("простой crud-каталог", out=str(target), save=False)
    assert report.estimated is True
    assert not target.exists()


def test_json_schema_keys() -> None:
    """DoD §5.2: JSON содержит description, scores{...***REMOVED***, verdict, calibrated, degraded."""
    report = le.lisa_estimator("каталог товаров с оплатой", save=False)
    payload = report.to_dict()
    for key in ("description", "scores", "verdict", "calibrated", "degraded"):
        assert key in payload, f"missing JSON key: {key***REMOVED***"
    assert isinstance(payload["scores"***REMOVED***, dict)
    for axis in ("engineering_complexity", "ai_native_complexity",
                 "verification_burden", "operational_risk",
                 "production_risk", "ai_suitability"):
        assert axis in payload["scores"***REMOVED***, f"missing score axis: {axis***REMOVED***"
        assert 0.0 <= payload["scores"***REMOVED***[axis***REMOVED*** <= 10.0


def test_cli_json_stdout(monkeypatch, capsys) -> None:
    """CLI --json печатает валидный JSON со schema-ключами."""
    monkeypatch.setattr(sys, "argv", ["lisa_estimator", "веб-платформа", "--json", "--no-save"***REMOVED***)
    assert le.main() == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["description"***REMOVED*** == "веб-платформа"
    assert payload["verdict"***REMOVED*** in ("GO", "COND", "NO-GO")
    assert "scores" in payload


def test_cli_input_file(tmp_path, monkeypatch, capsys) -> None:
    """--input brief.md: вход из файла (DoD §3.1 #3)."""
    brief = tmp_path / "brief.md"
    brief.write_text("мобильное приложение с интеграцией API и оплатой", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["lisa_estimator", "--input", str(brief), "--json", "--no-save"***REMOVED***)
    assert le.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert "оплатой" in payload["description"***REMOVED***


# ─── fail-safe: пустой/битый вход ──────────────────────────────────────────────


def test_empty_input_degraded() -> None:
    """DoD §5.3: пустой вход → degraded-отчёт estimated: false, exit 0."""
    report = le.lisa_estimator("", save=False)
    assert report.degraded is True
    assert report.estimated is False
    assert report.verdict == "NO-GO"
    assert any("пустое" in w for w in report.warnings)


def test_whitespace_input_degraded() -> None:
    """Пробельный вход также degraded (strip перед проверкой)."""
    report = le.lisa_estimator("   \n\t  ", save=False)
    assert report.degraded is True
    assert report.estimated is False


def test_cli_empty_stdin_degraded(monkeypatch, capsys) -> None:
    """CLI без аргументов и без stdin (tty) → degraded, exit 0 (не краш)."""
    monkeypatch.setattr(le.sys, "stdin", _FakeStdin(tty=True))
    monkeypatch.setattr(sys, "argv", ["lisa_estimator", "--json", "--no-save"***REMOVED***)
    assert le.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["degraded"***REMOVED*** is True
    assert payload["estimated"***REMOVED*** is False


class _FakeStdin:
    def __init__(self, tty: bool):
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty

    def read(self) -> str:
        return ""


# ─── детерминизм ───────────────────────────────────────────────────────────────


def test_deterministic_same_input() -> None:
    """Одинаковый вход → одинаковые оценки (детерминированный пайплайн)."""
    a = le.lisa_estimator("веб-платформа с каталогом и оплатой", save=False)
    b = le.lisa_estimator("веб-платформа с каталогом и оплатой", save=False)
    assert a.scores.to_dict() == b.scores.to_dict()
    assert a.verdict == b.verdict


def test_scores_differ_for_complex_input() -> None:
    """Сложный проект (интеграции, payments, security) выше по осям, чем простой CRUD."""
    simple = le.lisa_estimator("простой каталог", save=False)
    complex_ = le.lisa_estimator(
        "высоконагруженная платформа с интеграцией API, оплатой и безопасностью",
        save=False,
    )
    assert (complex_.scores.engineering_complexity
            > simple.scores.engineering_complexity)
    assert (complex_.scores.verification_burden
            > simple.scores.verification_burden)


def test_rationale_lists_matched_signals() -> None:
    """Каждая оценка обоснована списком сработавших сигналов (§3.1 #6)."""
    report = le.lisa_estimator("платформа с оплатой и интеграцией API", save=False)
    assert report.rationale["engineering_complexity"***REMOVED***  # оплата/интеграция
    for axis in le.AXES:
        assert axis in report.rationale


# ─── калибровка (--calibrate) ──────────────────────────────────────────────────


def test_calibration_applies_weights(tmp_path) -> None:
    """--calibrate lisa_calibration.yaml: веса осей применяются, calibrated=True."""
    cal = tmp_path / "lisa_calibration.yaml"
    cal.write_text("weights:\n  engineering_complexity: 2.0\n", encoding="utf-8")
    baseline = le.lisa_estimator("платформа с оплатой", save=False)
    calibrated = le.lisa_estimator(
        "платформа с оплатой", save=False, calibrate=str(cal)
    )
    assert calibrated.calibrated is True
    assert (calibrated.scores.engineering_complexity
            > baseline.scores.engineering_complexity)


def test_calibration_broken_fail_safe(tmp_path) -> None:
    """Битый файл калибровки → warning, НЕ падение (fail-safe)."""
    cal = tmp_path / "broken.yaml"
    cal.write_text("not: [valid: yaml", encoding="utf-8")
    report = le.lisa_estimator("каталог", save=False, calibrate=str(cal))
    assert report.estimated is True
    assert report.calibrated is False
    assert any("калибровка" in w for w in report.warnings)


def test_calibration_missing_file_fail_safe(tmp_path) -> None:
    """Отсутствующий файл калибровки → warning, не падение."""
    report = le.lisa_estimator("каталог", save=False,
                               calibrate=str(tmp_path / "nope.yaml"))
    assert report.estimated is True
    assert report.calibrated is False


# ─── каноничное хранилище (--domain / --save-calibration) ─────────────────────

def test_domain_applies_weights_from_store(tmp_path) -> None:
    """--domain: доменные веса из хранилища применяются, calibrated=True."""
    store = tmp_path / "store.yaml"
    store.write_text(
        "weights:\n  ai_suitability: 1.0\n"
        "domains:\n  xlsx:\n    ai_suitability: 7.0\n",
        encoding="utf-8",
    )
    baseline = le.lisa_estimator("экспорт таблиц в excel", save=False)
    domain = le.lisa_estimator(
        "экспорт таблиц в excel", save=False,
        domain="xlsx", calibration_store=str(store),
    )
    assert domain.calibrated is True
    assert domain.scores.ai_suitability > baseline.scores.ai_suitability


def test_domain_missing_fail_safe(tmp_path) -> None:
    """Отсутствующий домен → warning, calibrated=False (fail-safe)."""
    store = tmp_path / "store.yaml"
    store.write_text("weights:\n  ai_suitability: 1.0\n", encoding="utf-8")
    report = le.lisa_estimator(
        "каталог", save=False, domain="nope", calibration_store=str(store)
    )
    assert report.estimated is True
    assert report.calibrated is False
    assert any("домен" in w for w in report.warnings)


def test_save_calibration_merges_into_store(tmp_path) -> None:
    """--save-calibration: промотирует веса в хранилище, домен переиспользуем."""
    cal = tmp_path / "proj.yaml"
    cal.write_text("weights:\n  ai_suitability: 7.0\n", encoding="utf-8")
    store = tmp_path / "store.yaml"
    le.lisa_estimator(
        "каталог", save=False, calibrate=str(cal),
        save_calibration="xlsx", calibration_store=str(store),
    )
    assert "xlsx" in store.read_text(encoding="utf-8")
    report = le.lisa_estimator(
        "экспорт таблиц", save=False,
        domain="xlsx", calibration_store=str(store),
    )
    assert report.calibrated is True
    assert report.scores.ai_suitability > 0.0


def test_save_calibration_without_source_warns(tmp_path) -> None:
    """--save-calibration без --calibrate/--domain → warning (нет весов)."""
    store = tmp_path / "store.yaml"
    report = le.lisa_estimator(
        "каталог", save=False, save_calibration="x", calibration_store=str(store)
    )
    assert report.estimated is True
    assert any("нет весов" in w for w in report.warnings)


def test_canonical_store_exists_parses_and_has_xlsx_domain() -> None:
    """Integration (read-only): каноничное data_13/lisa_calibration.yaml существует,
    парсится и содержит домен xlsx (герметично: без мутации реального хранилища)."""
    store = le.DEFAULT_CALIBRATION_STORE
    assert store.is_file(), f"каноничное хранилище отсутствует: {store***REMOVED***"
    weights, domains = le._load_calibration_store(store)
    assert isinstance(weights, dict)
    assert isinstance(domains, dict)
    assert "xlsx" in domains, f"домен xlsx отсутствует в {store***REMOVED***"
    # XLSX-домен поднимает ai_suitability выше нейтрального 1.0 (см. data_13/lisa_calibration.yaml)
    assert domains["xlsx"***REMOVED***.get("ai_suitability", 0.0) > 1.0


# ─── vocabulary-drift (ANTI-6b / CON-8) ────────────────────────────────────────


def test_estimation_token_in_known_capabilities() -> None:
    """genuine-токен `estimation` зарегистрирован в KNOWN_CAPABILITIES."""
    from core_02.blueprint_v3 import KNOWN_CAPABILITIES

    assert "estimation" in KNOWN_CAPABILITIES


def test_estimation_token_in_model_catalog() -> None:
    """Токен `estimation` есть в ModelCatalog → drift-тест не сломается."""
    from core_02.router import ModelCatalog

    caps: set[str***REMOVED*** = set()
    for entry in ModelCatalog.default().all:
        caps.update(entry.capabilities)
    assert "estimation" in caps


def test_lisa_estimator_not_in_known_capabilities() -> None:
    """`lisa_estimator` — имя Tool (kind: tool), НЕ capability-токен (076_13_lisa_estimator_capability §3.2.6)."""
    from core_02.blueprint_v3 import KNOWN_CAPABILITIES

    assert "lisa_estimator" not in KNOWN_CAPABILITIES


def test_lisa_role_override_valid() -> None:
    """Роль lisa использует только закрытые токены (summarize + estimation)."""
    from core_02.blueprint_v3 import CAPABILITIES_OVERRIDE, KNOWN_CAPABILITIES

    assert set(CAPABILITIES_OVERRIDE["lisa"***REMOVED***) <= set(KNOWN_CAPABILITIES)


# ─── helper-уровень ────────────────────────────────────────────────────────────


def test_score_axis_clamps_to_10() -> None:
    """Огромное количество сигналов → clamp 10.0 (не выше)."""
    text = "оплата платежи платёж корзина auth авторизация аутентификация " \
           "реалтайм websocket многопользовательский backend микросервисы " \
           "интеграция API высоконагруженный масштабируемый database бэкенд"
    score, matched = le._score_axis(text, "engineering_complexity")
    assert score <= 10.0
    assert matched


def test_score_axis_negative_allowed_for_suitability() -> None:
    """ai_suitability: негативные сигналы (security/hardware) понижают оценку."""
    friendly = le._score_axis("каталог лендинг блог", "ai_suitability")
    risky = le._score_axis("hardware embedded критичная безопасность", "ai_suitability")
    assert friendly[0***REMOVED*** > risky[0***REMOVED***
