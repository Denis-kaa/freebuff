"""services_container.py — DI-контейнер для aiogram-обработчиков.

Создаётся один раз при старте бота и кладётся в `dispatcher.workflow_data`,
чтобы хэндлеры доставали зависимости через `workflow_data["services"***REMOVED***`.
"""

from __future__ import annotations

from dataclasses import dataclass
***REMOVED***
from typing import Optional

from ..config import Config
from ..db.database import Database
from ..db.repository import Repository
from ..services.catalog import CatalogService
from ..services.delivery import DeliveryService
from ..services.notifications import NotificationService
from ..services.orders import OrderService
from ..services.payments import PaymentService, get_provider


@dataclass
class Services:
    db: Database
    repo: Repository
    catalog: CatalogService
    orders: OrderService
    payments: PaymentService
    delivery: DeliveryService
    notifications: NotificationService
    config: Config


class ServiceFactory:
    """Строит `Services` из конфига и notification-канала."""

    def __init__(self, config: Config) -> None:
        self._config = config

    def build(self, *, notification_channel=None) -> Services:
        cfg = self._config
        db = Database(Path(cfg.database_path))
        schema_sql = (
            Path(__file__).resolve().parent.parent / "db" / "schema.sql"
        ).read_text(encoding="utf-8")
        db.set_schema(schema_sql)
        db.init()

        repo = Repository(db)
        catalog = CatalogService(repo)
        # PaymentService вне цикла: не зависит от OrderService.
        provider = get_provider(cfg.payment_provider)
        payments = PaymentService(repo, provider)
        # OrderService знает о PaymentService для TTL/cancel.
        orders = OrderService(repo, payment_service=payments)
        delivery = DeliveryService(repo)

        if notification_channel is None:
            from ..services.notifications import FakeChannel  # noqa: WPS433
            notification_channel = FakeChannel()
        notifications = NotificationService(repo, notification_channel)

        return Services(
            db=db,
            repo=repo,
            catalog=catalog,
            orders=orders,
            payments=payments,
            delivery=delivery,
            notifications=notifications,
            config=cfg,
        )
