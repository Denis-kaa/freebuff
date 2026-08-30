"""test_payments.py — идемпотентность платёжного сервиса.

Покрывает фиксы reviewer'а #5 и #6:
  - attach_to_order возвращает existing PENDING, не падает на UNIQUE.
  - finalize на заказе PAID/DELIVERED не делает revert (фикс #3).
"""

from __future__ import annotations

from market_bot.models import OrderStatus, PaymentStatus
from market_bot.services.payments import IncomingPayment


def test_attach_to_order_returns_existing_pending(
    services, make_seller, make_buyer
):
    """Повторный attach_to_order должен вернуть existing PENDING (а не
    падать IntegrityError от UNIQUE order_id).
    """
    repo = services["repo"]
    orders = services["orders"]
    payments = services["payments"]
    sid = make_seller(910, "S-PA")
    bid = make_buyer(9100, "B-PA")
    product = services["catalog"].seller_create(sid, "PA", "d", "x", 50)
    repo.add_keys(product.id, ["PA-1"])
    order, _ = orders.create_order_for_product(bid, product.id)
    p1 = payments.attach_to_order(order)
    p2 = payments.attach_to_order(order)
    assert p1.id == p2.id
    assert p2.status == PaymentStatus.PENDING


def test_finalize_on_paid_order_is_no_op(services, make_seller, make_buyer):
    """Если платёж успешен и заказ уже PAID (после повторного successful_payment
    от Telegram), finalize не должен перезаписать статус заказа.
    """
    repo = services["repo"]
    orders = services["orders"]
    payments = services["payments"]
    sid = make_seller(920, "S-FN")
    bid = make_buyer(9200, "B-FN")
    product = services["catalog"].seller_create(sid, "FN", "d", "x", 700)
    repo.add_keys(product.id, ["FN-1"])
    order, _ = orders.create_order_for_product(bid, product.id)
    payment = payments.attach_to_order(order)
    incoming = IncomingPayment(external_id="tg-charge-FN", expected_amount=700)
    payments.finalize(payment, incoming)
    orders.mark_paid(order.id)
    services["delivery"].publish(order.id)

    # Доставить симулируем «ретрай successful_payment»: получим тот же payment
    # уже SUCCEEDED, попытка финализации кидает PaymentAlreadyProcessedError.
    import pytest
    from market_bot.services.payments import PaymentAlreadyProcessedError
    succeeded_payment = repo.get_payment(payment.id)
    assert succeeded_payment.status == PaymentStatus.SUCCEEDED
    with pytest.raises(PaymentAlreadyProcessedError):
        payments.finalize(succeeded_payment, incoming)

    # Статус заказа остался DELIVERED — никакого revert в PAID.
    final_order = orders.get(order.id)
    assert final_order.status == OrderStatus.DELIVERED


def test_attach_to_order_after_succeeded_raises(services, make_seller, make_buyer):
    """Если платёж уже SUCCEEDED, attach_to_order бросает PaymentAlreadyProcessedError."""
    import pytest
    repo = services["repo"]
    orders = services["orders"]
    payments = services["payments"]
    sid = make_seller(930, "S-AS")
    bid = make_buyer(9300, "B-AS")
    product = services["catalog"].seller_create(sid, "AS", "d", "x", 100)
    repo.add_keys(product.id, ["AS-1"])
    order, _ = orders.create_order_for_product(bid, product.id)
    payment = payments.attach_to_order(order)
    incoming = IncomingPayment(external_id="tg-AS", expected_amount=100)
    payments.finalize(payment, incoming)

    from market_bot.services.payments import PaymentAlreadyProcessedError as PAE
    with pytest.raises(PAE):
        payments.attach_to_order(order)
