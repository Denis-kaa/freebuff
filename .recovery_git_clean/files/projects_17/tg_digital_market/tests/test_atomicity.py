"""test_atomicity.py — атомарность резервирования ключа под параллельными покупателями.

Сценарий: 10 потоков одновременно пытаются купить один и тот же товар с 5 ключами.
Ожидаемо: ровно 5 успехов, 5 — OutOfStockError. Без атомарного UPDATE в
`reserve_key_for_order` возможны двойные резервирования (тест бы упал).
"""

from __future__ import annotations

import threading

import pytest

from market_bot.services.orders import OutOfStockError


def test_reserve_key_under_concurrency(services, make_seller):
    """10 покупателей одновременно покупают товар с 5 ключами в стоке."""
    repo = services["repo"***REMOVED***
    catalog = services["catalog"***REMOVED***
    orders = services["orders"***REMOVED***
    sid = make_seller(7777, "AtomicSeller")
    product = catalog.seller_create(sid, "Roblox 10$", "Atomic test", "roblox", 100)
    repo.add_keys(product.id, [f"KEY-{i***REMOVED***" for i in range(5)***REMOVED***)

    buyers = [10_000 + i for i in range(10)***REMOVED***
    for b in buyers:
        repo.upsert_user(b, None, f"Buyer{b***REMOVED***")

    barrier = threading.Barrier(len(buyers))
    successes: list[int***REMOVED*** = [***REMOVED***
    failures: list[int***REMOVED*** = [***REMOVED***
    lock = threading.Lock()

    def buy(uid: int) -> None:
        try:
            barrier.wait(timeout=5)  # синхронизируем старт
            order, _ = orders.create_order_for_product(uid, product.id)
            with lock:
                successes.append(order.id)
        except OutOfStockError:
            with lock:
                failures.append(uid)

    threads = [threading.Thread(target=buy, args=(b,)) for b in buyers***REMOVED***
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(successes) == 5, f"Ожидалось 5 успехов, получено {len(successes)***REMOVED***"
    assert len(failures) == 5, f"Ожидалось 5 неудач, получено {len(failures)***REMOVED***"

    # Все 5 ключей перешли в статус reserved.
    reserved_count = int(
        repo.raw_conn.execute(
            "SELECT COUNT(*) FROM product_keys WHERE product_id = ? AND status = 'reserved'",
            (product.id,),
        ).fetchone()[0***REMOVED***
    )
    assert reserved_count == 5

    # Ни один ключ не доставлен (delivery ещё не было).
    delivered_count = int(
        repo.raw_conn.execute(
            "SELECT COUNT(*) FROM product_keys WHERE product_id = ? AND status = 'delivered'",
            (product.id,),
        ).fetchone()[0***REMOVED***
    )
    assert delivered_count == 0
