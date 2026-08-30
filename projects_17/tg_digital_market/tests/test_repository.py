"""test_repository.py — базовые CRUD-тесты."""

from market_bot.models import OrderStatus


def test_upsert_user_creates(services):
    repo = services["repo"]
    u = repo.upsert_user(100, "alice", "Alice")
    assert u.id == 100
    assert u.full_name == "Alice"
    assert u.role.value == "user"


def test_upsert_user_updates_full_name(services):
    repo = services["repo"]
    repo.upsert_user(200, "bob", "Bob v1")
    u = repo.upsert_user(200, "bob", "Bob v2")
    assert u.full_name == "Bob v2"


def test_product_create_and_search(services, make_seller, make_buyer):
    repo = services["repo"]
    catalog = services["catalog"]
    sid = make_seller(1, "S1")
    product = catalog.seller_create(sid, "Steam 100$", "gift", "steam", 100)
    assert product.is_active is True
    repo.add_keys(product.id, ["K1", "K2", "K3"])
    assert repo.count_available_keys(product.id) == 3

    by_cat = repo.list_products(active_only=True, category="steam")
    assert [x.id for x in by_cat] == [product.id]


def test_order_pending_keys_reserved(services, make_seller, make_buyer):
    repo = services["repo"]
    orders = services["orders"]
    sid = make_seller(50, "S2")
    bid = make_buyer(500, "B2")
    product = services["catalog"].seller_create(sid, "X", "d", "x", 50)
    repo.add_keys(product.id, ["K1"])
    # ВАЖНО: orders.create_order_for_product принимает int product_id, не Product.
    order, item = orders.create_order_for_product(bid, product.id)
    assert order.status == OrderStatus.PENDING
    assert item.price_stars == 50
    # Ключ зарезервирован, в наличии 0.
    assert repo.count_available_keys(product.id) == 0
    row = repo.raw_conn.execute(
        "SELECT status FROM product_keys WHERE product_id = ?", (product.id,)
    ).fetchone()
    assert row["status"] == "reserved"


def test_payment_lifecycle(services, make_seller, make_buyer):
    repo = services["repo"]
    orders = services["orders"]
    payments = services["payments"]
    sid = make_seller(60, "S6")
    bid = make_buyer(600, "B6")
    product = services["catalog"].seller_create(sid, "Q", "d", "q", 200)
    repo.add_keys(product.id, ["QK1"])
    order, _ = orders.create_order_for_product(bid, product.id)
    payment = payments.attach_to_order(order)
    from market_bot.services.payments import IncomingPayment
    incoming = IncomingPayment(external_id="ext-1", expected_amount=200)
    final, ok = payments.finalize(payment, incoming)
    assert ok is True
    assert final.status.value == "succeeded"
