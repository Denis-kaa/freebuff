"""test_lead_aggregator_adapters.py — тесты адаптеров и пайплайна (Фаза 3).

KworkAdapter: парсинг ленты заказов из HTML.
TGChannelAdapter: парсинг t.me/s/ web-preview.
LeadPipeline: полный конвейер (fetch → L1/L2 → dedup → score → checkpoint).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

LA_ROOT = Path(__file__).resolve().parent.parent / "projects_17" / "lead_aggregator"
sys.path.insert(0, str(LA_ROOT))

from app.adapters.kwork_adapter import KworkAdapter  # noqa: E402
from app.adapters.tg_channel_adapter import TGChannelAdapter  # noqa: E402
from app.core.config import Config  # noqa: E402
from app.core.retry_policy import RetryPolicy  # noqa: E402
from app.models import Lead  # noqa: E402
from app.pipeline import LeadPipeline  # noqa: E402
from app.processors.intent_classifier import IntentClassifier  # noqa: E402
from app.processors.scorer import Scorer  # noqa: E402
from app.storage.checkpoint_store import CheckpointStore  # noqa: E402


class FakeClient:
    """TLSClient-заглушка: возвращает заранее заданный HTML."""

    def __init__(self, html: str) -> None:
        self._html = html

    async def get(self, url: str, **kwargs):  # noqa: ANN001
        return self._html


KWORK_HTML = """
<html><body>
<div class="wcard">
  <a href="https://kwork.ru/projects/telegram-bot-dlya-magazina">Нужен телеграм бот для магазина</a>
</div>
<div class="wcard">
  <a href="https://kwork.ru/projects/landing-page">Нужен лендинг под ключ</a>
</div>
<div class="wcard">
  <a href="https://kwork.ru/projects/spam-rassylka">Казино накрутка заработок</a>
</div>
</body></html>
"""

TG_HTML = """
<html><body>
<div class="tgme_widget_message" data-post="freelance_tg/138170">
  <div class="tgme_widget_message_text js-message_text">Ищу разработчика телеграм бота</div>
</div>
<div class="tgme_widget_message" data-post="freelance_tg/138171">
  <div class="tgme_widget_message_text js-message_text">Предлагаю услуги фрилансера, ищу работу</div>
</div>
</body></html>
"""

# W-16 (Фаза 4, live-verify 2026-08-10): на живом t.me/s блок может иметь
# ДОПОЛНИТЕЛЬНЫЕ классы: `tgme_widget_message text_not_supported_wrap
# service_message js-widget_message` — regex должен матчить префикс, не весь класс.
TG_HTML_LIVE_CLASSES = """
<html><body>
<div class="tgme_widget_message text_not_supported_wrap service_message js-widget_message" data-post="freelance_tg/200001">
  <div class="tgme_widget_message_text js-message_text">Нужен бот для телеграм, кто может сделать</div>
</div>
<div class="tgme_widget_message_wrap js-widget_message_wrap">
  <div class="tgme_widget_message service_message js-widget_message" data-post="freelance_tg/200002">
    <div class="tgme_widget_message_text js-message_text">Сделаю лендинг под ключ, ищу заказы</div>
  </div>
</div>
</body></html>
"""

# W-16 (Фаза 4): kwork.ru/projects стал SPA — статичный HTML = скелет с прелоадерами.
KWORK_SPA_SHELL_HTML = """
<html><body>
<div class="js-wants-list-preloaders"><img src="preloader.svg"></div>
<div class="wants-content"><img src="preloader-project.svg"></div>
</body></html>
"""


class TestKworkAdapter:
    @pytest.mark.asyncio
    async def test_parse_orders(self):
        adapter = KworkAdapter(FakeClient(KWORK_HTML))
        leads = await adapter.fetch()
        assert len(leads) == 3
        assert leads[0].source == "kwork"
        assert "telegram-bot-dlya-magazina" in leads[0].url
        assert leads[0].source_id == "telegram-bot-dlya-magazina"


class TestTGChannelAdapter:
    @pytest.mark.asyncio
    async def test_parse_preview(self):
        adapter = TGChannelAdapter(FakeClient(TG_HTML), "freelance_tg")
        leads = await adapter.fetch()
        assert len(leads) == 2
        assert leads[0].source_id == "freelance_tg/138170"
        assert leads[0].url == "https://t.me/freelance_tg/138170"
        assert "телеграм бота" in leads[0].text

    @pytest.mark.asyncio
    async def test_parse_live_class_variants(self):
        """Регрессия W-16: блоки с доп. классами (реальный t.me/s) парсятся."""
        adapter = TGChannelAdapter(FakeClient(TG_HTML_LIVE_CLASSES), "freelance_tg")
        leads = await adapter.fetch()
        assert len(leads) == 2
        assert leads[0].source_id == "freelance_tg/200001"
        assert leads[1].source_id == "freelance_tg/200002"


class TestKworkSpaShell:
    @pytest.mark.asyncio
    async def test_spa_shell_returns_empty_not_crash(self):
        """Регрессия W-16: SPA-скелет Kwork → 0 лидов + warning, без падения."""
        adapter = KworkAdapter(FakeClient(KWORK_SPA_SHELL_HTML))
        leads = await adapter.fetch()
        assert leads == []


class TestBuildDefaultAdapters:
    def test_factory_kwork_and_tg_channels(self, tmp_path):
        from app.core.tls_client import TLSClient
        from app.pipeline import build_default_adapters

        cfg = Config(checkpoint_db=tmp_path / "cp.db")
        cfg.kwork_enabled = True
        cfg.tg_channels = ["freelance_tg", "proger_orders"]
        adapters = build_default_adapters(cfg, TLSClient())
        names = [a.name for a in adapters]
        assert names.count("kwork") == 1
        assert names.count("tg_channel") == 2

    def test_factory_kwork_disabled(self, tmp_path):
        from app.core.tls_client import TLSClient
        from app.pipeline import build_default_adapters

        cfg = Config(checkpoint_db=tmp_path / "cp.db")
        cfg.kwork_enabled = False
        cfg.tg_channels = []
        assert build_default_adapters(cfg, TLSClient()) == []


class TestTelegramDelivery:
    @pytest.mark.asyncio
    async def test_format_escapes_html(self):
        from app.delivery.telegram import TelegramDelivery

        d = TelegramDelivery()
        lead = Lead(source="kwork", source_id="1", text="<script>alert(1)</script> нужен бот", intent="client", score=70.0)
        formatted = d._format(lead)
        assert "<script>" not in formatted
        assert "&lt;script&gt;" in formatted
        await d.aclose()


class TestPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline(self, tmp_path):
        cfg = Config(checkpoint_db=tmp_path / "cp.db")
        cfg.lead_score_threshold = 40  # client=40 база проходит, seeker=0 отсекается
        adapter = TGChannelAdapter(FakeClient(TG_HTML), "freelance_tg")
        pipeline = LeadPipeline(
            config=cfg,
            adapters=[adapter],
            classifier=IntentClassifier(
                stopwords=cfg.stopwords,
                client_markers=cfg.client_markers,
                seeker_markers=cfg.seeker_markers,
            ),
            scorer=Scorer(signals=cfg.competence_signals),
            checkpoint=CheckpointStore(tmp_path / "cp.db"),
            retry=RetryPolicy(max_attempts=1, failure_threshold=10),
        )
        stats = await pipeline.run_once()
        # 2 лида из TG; seeker отсеивается L2; client проходит
        assert stats["fetched"] == 2
        assert stats["new"] == 1
        assert pipeline.checkpoint.get_last("tg_channel") is not None
        await pipeline.aclose()

    @pytest.mark.asyncio
    async def test_adapter_error_isolation(self, tmp_path):
        class BrokenAdapter:
            name = "broken"
            ordered = False

            async def fetch(self, limit: int = 50):  # noqa: ARG002
                from app.adapters.base import AdapterError

                raise AdapterError("down")

        class GoodAdapter:
            name = "good"
            ordered = False

            async def fetch(self, limit: int = 50):  # noqa: ARG002
                return [Lead(source="good", source_id="1", text="нужен бот")]

        cfg = Config(checkpoint_db=tmp_path / "cp.db")
        cfg.lead_score_threshold = 40
        pipeline = LeadPipeline(
            config=cfg,
            adapters=[BrokenAdapter(), GoodAdapter()],
            classifier=IntentClassifier(
                stopwords=[], client_markers=["нужен"], seeker_markers=[]
            ),
            scorer=Scorer(signals=[]),
            checkpoint=CheckpointStore(tmp_path / "cp.db"),
            retry=RetryPolicy(max_attempts=1, failure_threshold=10),
        )
        stats = await pipeline.run_once()
        assert stats["errors"] == 1  # broken упал, но good отработал
        assert stats["new"] == 1
        await pipeline.aclose()
