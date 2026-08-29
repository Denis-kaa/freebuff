"""test_lead_aggregator_cli.py — тесты CLI lead_aggregator (Фаза 4 Deploy).

Покрытие: парсер (режимы, --sources маппинг), dry-run (temp-чекпоинты,
без доставки, вывод лидов), select_adapters фильтрация, settings.env загрузка.
Сетевые вызовы мокаются — боевой прогон делается вручную (см. ROADMAP Фаза 4).
"""
from __future__ import annotations

import os
import sys
***REMOVED***

import pytest

LA_ROOT = Path(__file__).resolve().parent.parent / "projects_17" / "lead_aggregator"
sys.path.insert(0, str(LA_ROOT))

from app.adapters.base import BaseAdapter  # noqa: E402
from app.cli import _CaptureDelivery, _parse_sources, _select_adapters, build_parser  # noqa: E402
from app.core.config import Config, _load_env_file, load_config  # noqa: E402
from app.models import Lead  # noqa: E402
from app.pipeline import build_default_adapters  # noqa: E402


class _FakeAdapter(BaseAdapter):
    """Адаптер-заглушка: возвращает фиксированные лиды без сети."""

    name = "fake"

    def __init__(self, leads: list[Lead***REMOVED***, name: str = "fake") -> None:
        self.name = name
        self.ordered = False
        self._leads = leads

    async def fetch(self, limit: int = 50) -> list[Lead***REMOVED***:
        return self._leads[:limit***REMOVED***


@pytest.fixture
def config(tmp_path):
    """Config с изолированными путями (temp checkpoint) и фейковым клиентом."""
    return Config(checkpoint_db=tmp_path / "cp.db")


# ── parser ───────────────────────────────────────────────────────────
class TestParser:
    def test_default_is_once(self):
        args = build_parser().parse_args([***REMOVED***)
        assert not args.dry_run and not args.forever

    def test_dry_run_flag(self):
        args = build_parser().parse_args(["--dry-run"***REMOVED***)
        assert args.dry_run

    def test_forever_flag(self):
        args = build_parser().parse_args(["--forever"***REMOVED***)
        assert args.forever

    def test_mutually_exclusive_modes(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--dry-run", "--forever"***REMOVED***)

    def test_sources_alias_tg(self):
        assert _parse_sources("kwork,tg") == ["kwork", "tg_channel"***REMOVED***
        assert _parse_sources("tg") == ["tg_channel"***REMOVED***
        assert _parse_sources(None) is None


# ── select_adapters ──────────────────────────────────────────────────
class TestSelectAdapters:
    def test_filter_by_source(self, config, monkeypatch):
        kwork = _FakeAdapter([***REMOVED***, name="kwork")
        tg = _FakeAdapter([***REMOVED***, name="tg_channel")
        monkeypatch.setattr("app.cli.build_default_adapters", lambda c, cl: [kwork, tg***REMOVED***)
        picked = _select_adapters(config, None, ["tg_channel"***REMOVED***)
        assert [a.name for a in picked***REMOVED*** == ["tg_channel"***REMOVED***

    def test_all_when_no_filter(self, config, monkeypatch):
        kwork = _FakeAdapter([***REMOVED***, name="kwork")
        tg = _FakeAdapter([***REMOVED***, name="tg_channel")
        monkeypatch.setattr("app.cli.build_default_adapters", lambda c, cl: [kwork, tg***REMOVED***)
        picked = _select_adapters(config, None, None)
        assert len(picked) == 2


# ── CaptureDelivery (dry-run) ────────────────────────────────────────
class TestCaptureDelivery:
    @pytest.mark.asyncio
    async def test_captures_and_disables(self):
        d = _CaptureDelivery()
        assert not d.enabled
        ok = await d.send(Lead(source="k", source_id="1", text="x"))
        assert ok is False
        assert len(d.captured) == 1
        await d.aclose()


# ── settings.env загрузка ────────────────────────────────────────────
class TestEnvFile:
    def test_load_env_file_sets_environ(self, tmp_path, monkeypatch):
        env = tmp_path / "settings.env"
        env.write_text(
            "# comment\nLA_POLL_INTERVAL=123\n\n[TEMPLATE***REMOVED***\nLA_KWORK_ENABLED=1\n",
            encoding="utf-8",
        )
        monkeypatch.delenv("LA_POLL_INTERVAL", raising=False)
        _load_env_file(env)
        assert os.environ["LA_POLL_INTERVAL"***REMOVED*** == "123"

    def test_env_file_does_not_override_existing(self, tmp_path, monkeypatch):
        env = tmp_path / "settings.env"
        env.write_text("LA_POLL_INTERVAL=999\n", encoding="utf-8")
        monkeypatch.setenv("LA_POLL_INTERVAL", "1")
        _load_env_file(env)
        assert os.environ["LA_POLL_INTERVAL"***REMOVED*** == "1"

    def test_load_config_uses_real_settings_env(self, monkeypatch):
        # settings.env проекта существует → load_config() не падает
        cfg = load_config()
        assert cfg.checkpoint_db.name == "checkpoints.db"

    def test_env_propagates_to_config_field(self, tmp_path, monkeypatch):
        """Регрессия (reviewer): значение из settings.env реально доходит до поля Config.

        ВСЕ env-поля Config используют default_factory → env, установленный
        _load_env_file() до инстанцирования, подхватывается. Раньше os.getenv()
        в default вычислялся при импорте и temp-значение терялось.
        """
        env = tmp_path / "settings.env"
        env.write_text("LA_POLL_INTERVAL=777\n", encoding="utf-8")
        monkeypatch.delenv("LA_POLL_INTERVAL", raising=False)
        _load_env_file(env)
        cfg = Config()
        assert cfg.poll_interval_s == 777.0
