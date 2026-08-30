"""test_order_fsm.py — стейт-машина заказа.

Покрывает:
  * полный happy-path: PENDING → PAID → DELIVERED с публикацией ключа;
  * идемпотентность mark_paid;
  * запрет cancel на PAID (см. фикс thinker'а #3a);
  * cancel на PENDING освобождает ключ.
"""

from __future__ import annotations

import pytest

from market_bot.models import OrderStatus
from market_bot.services.orders import InvalidOrderStateError
from market_bot.services.payments import IncomingPayment


def test_full_path_pending_paid_delivered(services, make_seller, make_buyer):
    repo = services["repo"]
    orders = services["orders"]
    payments = services["payments"]
    delivery = services["delivery"]

    sid = make_seller(900, "S9")
    bid = make_buyer(9000, "B9")
    product = services["catalog"].seller_create(sid, "Steam 50$", "Card", "steam", 500)
    repo.add_keys(product.id, ["DLV-1"])

    order, _ = orders.create_order_for_product(bid, product.id)
    assert order.status == OrderStatus.PENDING

    payment = payments.attach_to_order(order)
    incoming = IncomingPayment(external_id="tg-charge-1", expected_amount=500)
    payments.finalize(payment, incoming)
    orders.mark_paid(order.id)
    delivery.publish(order.id)

    final = orders.get(order.id)
    assert final.status == OrderStatus.DELIVERED

    code = delivery.code_for_order(order.id)
    assert code == "DLV-1"
    # key теперь status='delivered'
    rows = repo.raw_conn.execute(
        "SELECT status FROM product_keys WHERE code = ?", ("DLV-1",)
    ).fetchall()
    assert all(r["status"] == "delivered" for r in rows)


def test_mark_paid_is_idempotent(services, make_seller, make_buyer):
    repo = services["repo"]
    orders = services["orders"]
    sid = make_seller(901, "S10")
    bid = make_buyer(9001, "B10")
    product = services["catalog"].seller_create(sid, "X", "d", "x", 10)
    repo.add_keys(product.id, ["k1"])
    order, _ = orders.create_order_for_product(bid, product.id)
    o1 = orders.mark_paid(order.id)
    o2 = orders.mark_paid(order.id)
    assert o1.status == OrderStatus.PAID
    assert o2.status == OrderStatus.PAID


def test_cancel_paid_is_refused(services, make_seller, make_buyer):
    repo = services["repo"]
    orders = services["orders"]
    sid = make_seller(902, "S11")
    bid = make_buyer(9002, "B11")
    product = services["catalog"].seller_create(sid, "Y", "d", "x", 10)
    repo.add_keys(product.id, ["k2"])
    order, _ = orders.create_order_for_product(bid, product.id)
    orders.mark_paid(order.id)
    with pytest.raises(InvalidOrderStateError):
        orders.cancel(order.id)


def test_cancel_pending_releases_key(services, make_seller, make_buyer):
    repo = services["repo"]
    orders = services["orders"]
    sid = make_seller(903, "S12")
    bid = make_buyer(9003, "B12")
    product = services["catalog"].seller_create(sid, "Z", "d", "x", 10)
    repo.add_keys(product.id, ["k3"])
    order, _ = orders.create_order_for_product(bid, product.id)
    assert repo.count_available_keys(product.id) == 0
    orders.cancel(order.id, reason="user_changed_mind")
    final = orders.get(order.id)
    assert final.status == OrderStatus.CANCELLED
    assert repo.count_available_keys(product.id) == 1
