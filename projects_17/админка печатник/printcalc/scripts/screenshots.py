"""Playwright-проход по всем экранам printcalc_web со скриншотами.

Сценарий:
1. Сидит демо-данные через API (3 позиции прайса + заказ с пожеланиями и разделами).
2. Делает скриншоты всех страниц (десктоп, тёмная тема «Печатникъ», мобильный).
3. Очищает демо-данные — БД остаётся чистой.

Запуск на сервере whimco (где крутится приложение на 127.0.0.1:8300):
    ssh -o ControlMaster=no -o ControlPath=none -F ~/.ssh/config whimco \
        '/opt/printcalc-venv/bin/python -' < scripts/screenshots.py

Скриншоты падают в /tmp/printcalc-shots/ (перенести в docs/screenshots/).
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8300"
API = BASE + "/api"  # все JSON-эндпоинты живут под /api; /price-list — HTML-страница
OUT = pathlib.Path("/tmp/printcalc-shots")
OUT.mkdir(exist_ok=True, parents=True)
DB = "/opt/printcalc/data/printcalc.db"

DEMO_PRICE_ITEMS = [
    {"name": "Копия ч/б", "price": 5, "unit": "лист"},
    {"name": "Фото на паспорт (4 шт)", "price": 200, "unit": "компл."},
    {"name": "Ламинация А4", "price": 40, "unit": "шт"},
]


def api(method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:300]


def clean_db() -> None:
    """Полная очистка данных (демо-данные смоука). Seeded-разделы не трогаем."""
    conn = sqlite3.connect(DB)
    conn.executescript(
        """
        DELETE FROM order_section_values;
        DELETE FROM order_items;
        DELETE FROM orders;
        DELETE FROM price_list_items;
        DELETE FROM sqlite_sequence;
        """
    )
    conn.commit()
    conn.close()


def seed() -> None:
    ids: dict[str, int] = {}
    for item in DEMO_PRICE_ITEMS:
        status, created = api("POST", "/price-list", item)
        assert status == 201, f"price item failed: {status} {created}"
        ids[item["name"]] = created["id"]
    status, order = api(
        "POST",
        "/orders",
        {
            "status": "новый",
            "payment_method": "наличные",
            "items": [
                {"kind": "price_list", "price_list_item_id": ids["Копия ч/б"], "qty": 10},
                {"kind": "price_list", "price_list_item_id": ids["Ламинация А4"], "qty": 2},
                {"kind": "manual", "name": "Визитки 100 шт", "price": 900, "qty": 1},
            ],
            "wishes": "Тёмно-синий фон, как на прошлом макете.",
            "section_values": {"2": "срочно", "3": "самовывоз"},
        },
    )
    assert status == 201, f"order failed: {status} {order}"


def main() -> None:
    clean_db()
    seed()

    from playwright.sync_api import sync_playwright

    pages = [
        ("/", "01-main.png"),
        ("/orders", "02-orders.png"),
        ("/price-list", "03-price-list.png"),
        ("/constructor", "04-constructor.png"),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        for path, name in pages:
            page.goto(BASE + path, wait_until="load", timeout=20000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUT / name), full_page=True)
            print("shot:", name)

        # Тёмная тема «Печатникъ» — пресет активируется классом, логику не трогаем.
        page.goto(BASE + "/", wait_until="load", timeout=20000)
        page.evaluate("document.body.classList.add('pecatnik')")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "05-main-dark.png"), full_page=True)
        print("shot: 05-main-dark.png")

        # Мобильный вид главного экрана.
        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(BASE + "/", wait_until="load", timeout=20000)
        mobile.wait_for_timeout(500)
        mobile.screenshot(path=str(OUT / "06-main-mobile.png"), full_page=True)
        print("shot: 06-main-mobile.png")
        browser.close()

    clean_db()
    print("demo data cleaned; DB is empty again")
    print("OUT:", OUT)


if __name__ == "__main__":
    main()