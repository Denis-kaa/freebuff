"""conftest.py — общие фикстуры core-тестов.

Тесты НЕ импортируют aiogram. Все сервисы работают на синхронном SQLite
через stdlib — это позволяет тестировать атомарность и многопоточность
без event loop.
`pythonpath = src` в pytest.ini уже добавляет путь — sys.path-инжект
больше не нужен (фикс ревью #8).
"""

from __future__ import annotations

***REMOVED***

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "src" / "market_bot" / "db" / "schema.sql"

from market_bot.db.database import Database
from market_bot.db.repository import Repository
from market_bot.services.catalog import CatalogService
from market_bot.services.delivery import DeliveryService
from market_bot.services.notifications import FakeChannel, NotificationService
from market_bot.services.orders import OrderService
from market_bot.services.payments import MockPaymentProvider, PaymentService
from market_bot.models import UserRole


@pytest.fixture
def db(tmp_path) -> Database:
    """Свежий SQLite в tmp c применённой схемой."""
    d = Database(str(tmp_path / "test.sqlite"))
    d.set_schema(SCHEMA.read_text(encoding="utf-8"))
    d.init()
    yield d
    d.close()


@pytest.fixture
def services(db: Database):
    """Собранный граф сервисов с FakeChannel для уведомлений."""
    repo = Repository(db)
    catalog = CatalogService(repo)
    payments = PaymentService(repo, MockPaymentProvider())
    orders = OrderService(repo, payment_service=payments)
    delivery = DeliveryService(repo)
    notifications = NotificationService(repo, FakeChannel())
    return {
        "db": db,
        "repo": repo,
        "catalog": catalog,
        "payments": payments,
        "orders": orders,
        "delivery": delivery,
        "notifications": notifications,
    ***REMOVED***


@pytest.fixture
def make_seller(services):
    """Хелпер: создать продавца с заданным telegram id."""
    def _make(telegram_id: int, full_name: str = "Seller") -> int:
        repo = services["repo"***REMOVED***
        repo.upsert_user(telegram_id, None, full_name)
        repo.set_role(telegram_id, UserRole.SELLER)
        return telegram_id
    return _make


@pytest.fixture
def make_buyer(services):
    """Хелпер: создать покупателя (role=user)."""
    def _make(telegram_id: int, full_name: str = "Buyer") -> int:
        services["repo"***REMOVED***.upsert_user(telegram_id, None, full_name)
        return telegram_id
    return _make
