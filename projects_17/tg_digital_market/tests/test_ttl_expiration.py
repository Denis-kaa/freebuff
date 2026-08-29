"""test_ttl_expiration.py — TTL-сборка просроченных pending-заказов."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from market_bot.models import OrderStatus, PaymentStatus, UserRole


def test_overdue_pending_is_cancelled_and_key_returned(
    services, make_seller, make_buyer
):
    repo = services["repo"***REMOVED***
    orders = services["orders"***REMOVED***
    payments = services["payments"***REMOVED***

    sid = make_seller(8000, "TTL-Seller")
    bid = make_buyer(8001, "TTL-Buyer")
    product = services["catalog"***REMOVED***.seller_create(sid, "T", "t", "t", 10)
    repo.add_keys(product.id, ["TTL-1"***REMOVED***)
    order, _ = orders.create_order_for_product(bid, product.id)
    payment = payments.attach_to_order(order)
    # Подменим created_at на 100 секунд в прошлое.
    past_iso = (
        datetime.now(timezone.utc).replace(microsecond=0)
        - timedelta(seconds=100)
    ).isoformat()
    repo.raw_conn.execute(
        "UPDATE orders SET created_at = ? WHERE id = ?", (past_iso, order.id)
    )

    cancelled = orders.expire_overdue(ttl_seconds=60)
    assert order.id in cancelled

    final = orders.get(order.id)
    assert final.status == OrderStatus.CANCELLED

    # Ключ вернулся в сток.
    assert repo.count_available_keys(product.id) == 1

    # Связанный платёж — failed (см. фикс thinker'а #3d).
    final_payment = repo.get_payment_by_order(order.id)
    assert final_payment is not None
    assert final_payment.status == PaymentStatus.FAILED
