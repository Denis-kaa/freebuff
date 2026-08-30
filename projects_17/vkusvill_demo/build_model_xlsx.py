"""
build_model_xlsx.py — построить модельный .xlsx для демо-сценария ВкусВилл.

⚠️ МОДЕЛЬНЫЙ пример. Не привязан к реальным данным ритейлера. Использует:
core_02/xlsx_builder (платформенная обёртка над openpyxl).

Per Q1-Q4 clarifications:
- Q1 (variant b): pre-computed values для snapshot + формулы для Excel-eval;
  parity_check осуществляет сравнение БЕЗ Excel round-trip (NO LibreOffice).
- Q2: 3 категории (молочка/крупа/напиток).
- Q3: ровно 2 неочевидных элемента.
- Q4: only Mission B (платформенный skill + модельный пример).
"""
from __future__ import annotations

import datetime
import json
}
from statistics import pstdev

# === sys.path injection (run as direct script, not as -m module) ===
# mirror forecast.py + parity_check.py pattern: prepend project_root so that
# `from core_02.xlsx_builder import Workbook` resolves regardless of cwd.
# Minimal-invasive option (d): NO __init__.py markers added (per user constraint
# «не расширять архитектуру платформы» в promt 62).
import sys as _sys_for_path
] as _Path_for_path
_sys_for_path.path.insert(
    0, str(_Path_for_path(__file__).resolve().parent.parent.parent)
)

from core_02.xlsx_builder import Workbook

# === Re-exports (one source of truth for build_model_xlsx, forecast.py, parity_check.py) ===
__all__ = [
    "HEADER", "BASE_DATE", "WEEKS",
    "CATEGORIES", "DEFAULT_STOCK",
    "SMA_WINDOW", "WEEKDAY_BASE", "SERVICE_LEVEL_Z",
    "SHELF_CRITICAL_RATIO", "INCIDENT_2024_CORRECTION", "ORDER_BUFFER",
    "OUT_DIR", "OUT_PATH", "SNAPSHOT_PATH",
]


HEADER = (
    "МОДЕЛЬНЫЙ пример, построен для демонстрации подхода к разбору legacy "
    "Excel/VBA логики прогноза/автозаказа. НЕ привязан к реальным данным "
    "ВкусВилла или иного ритейлера."
)

BASE_DATE = datetime.date(2025, 6, 2)  # синтетический понедельник

# === 3 категории (per Q2 clarification) ===
CATEGORIES: list[dict] = [
    {
        "sku": "Молоко 3.2% 1л",
        "cat": "dairy",
        "shelf_life": 7,
        "lead_time": 2,
        "baseline": 35,
        "wd": [1.10, 1.00, 1.00, 1.05, 1.20, 1.40, 1.30],
    },
    {
        "sku": "Крупа гречневая 800г",
        "cat": "groats",
        "shelf_life": 365,
        "lead_time": 5,
        "baseline": 12,
        "wd": [1.05, 1.00, 1.00, 1.00, 1.15, 1.10, 0.90],
    },
    {
        "sku": "Напиток газир. 1л",
        "cat": "beverage",
        "shelf_life": 90,
        "lead_time": 3,
        "baseline": 22,
        "wd": [0.90, 0.85, 0.85, 0.95, 1.25, 1.50, 1.30],
    },
]
WEEKS = 12

# === 4 принципа: named constants (NO magic numbers) ===
SMA_WINDOW = 4                                       # принцип 1: SMA по 4 неделям
WEEKDAY_BASE = 1.2                                   # пятница для прогнозной недели W13 (informational)
SERVICE_LEVEL_Z = 1.65                               # принцип 3: Z для 95% сервиса — NON_OBVIOUS_1
SHELF_CRITICAL_RATIO = 2.0                           # принцип 4: порог shelf_life/lead_time
INCIDENT_2024_CORRECTION = 0.92                      # NON_OBVIOUS_2: cell-content proxy legacy defined name
DEFAULT_STOCK = {cat["sku"]: 10 + i * 5 for i, cat in enumerate(CATEGORIES)}
ORDER_BUFFER = 0.10                                  # 10% day-cover buffer в формуле заказа

OUT_DIR = Path("projects_17/vkusvill_demo")
OUT_PATH = OUT_DIR / "model_forecast.xlsx"
SNAPSHOT_PATH = OUT_DIR / "model_snapshot.json"


def build_history(wb: Workbook, base: datetime.date) -> tuple[
    dict[str, tuple[int, int]], dict[str, list[int]]
]:
    """Sheet 'history': 12 weeks × 3 categories. Returns sku->(start_row, end_row)
    + sku->list_of_12 sales_qty (raw values for downstream use)."""
    wb.sheet("history")
    wb.cell("A1", value=HEADER, fmt={"bold": True})
    wb.cell("A3", value="week")
    wb.cell("B3", value="date")
    wb.cell("C3", value="sku_name")
    wb.cell("D3", value="sales_qty")

    row = 4
    sku_rows: dict[str, tuple[int, int]] = {}
    sku_sales: dict[str, list[int]] = {}
    for cat in CATEGORIES:
        start = row
        sales: list[int] = []
        for wk in range(WEEKS):
            wk_date = base + datetime.timedelta(weeks=wk)
            wd_idx = wk_date.weekday()
            drift = 1 + wk * 0.005
            qty = round(cat["baseline"] * cat["wd"][wd_idx] * 7 * drift)
            wb.cell(f"A{row}", value=f"W{wk+1}")
            wb.cell(f"B{row}", value=str(wk_date))
            wb.cell(f"C{row}", value=cat["sku"])
            wb.cell(f"D{row}", value=qty)
            sales.append(qty)
            row += 1
        sku_rows[cat["sku"]] = (start, row - 1)
        sku_sales[cat["sku"]] = sales
        row += 1  # blank separator
    return sku_rows, sku_sales


def compute_forecast_values(
    sku_sales: list[int], cat: dict, base: datetime.date
) -> dict:
    """Pre-compute forecast values (Python side, deterministic mirror of Excel formulas)."""
    sma = sum(sku_sales[-SMA_WINDOW:]) / SMA_WINDOW
    sigma_p = pstdev(sku_sales[-SMA_WINDOW:])
    wd_factor = cat["wd"][(base.weekday() + WEEKS) % 7]
    safety = sigma_p * SERVICE_LEVEL_Z * (cat["lead_time"] ** 0.5)
    shelf = 0.5 if cat["shelf_life"] < cat["lead_time"] * SHELF_CRITICAL_RATIO else 1.0
    final = ((sma * wd_factor) + safety) * shelf
    return {
        "sma": sma, "wd_factor": wd_factor, "safety": safety,
        "shelf": shelf, "final": final,
    }


def build_forecast(
    wb: Workbook, sku_rows: dict[str, tuple[int, int]],
    sku_sales: dict[str, list[int]], base: datetime.date,
) -> dict[str, dict]:
    wb.sheet("forecast")
    wb.cell("A1", value=HEADER, fmt={"bold": True})
    wb.cell("A3", value="sku_name")
    wb.cell("B3", value="week")
    wb.cell("C3", value="forecast_sma4w")
    wb.cell("D3", value="weekday_factor")
    wb.cell("E3", value="safety_buffer")
    wb.cell("F3", value="shelf_correction")
    wb.cell("G3", value="final_forecast")
    wb.cell("H3", value="notes")

    # Parameters block (right side)
    wb.cell("J3", value="PARAM_LEGEND:")
    wb.cell("J4", value="SMA_WINDOW:")
    wb.cell("K4", value=SMA_WINDOW)
    wb.cell("J5", value="SERVICE_LEVEL_Z:")  # NON_OBVIOUS_1: 1.65 висит без видимого комментария
    wb.cell("K5", value=SERVICE_LEVEL_Z)
    wb.cell("J6", value="LEAD_TIME_DEFAULT:")
    wb.cell("K6", value=3)
    wb.cell("J7", value=(
        "NOTE: H22 содержит INCIDENT_2024_CORRECTION "
        "(cell-content proxy defined-name 'post_incident_2024_correction' "
        "— молочка получает -8% legacy-норматив после инцидента 2024)."
    ))

    forecasts: dict[str, dict] = {}
    for cat_i, cat in enumerate(CATEGORIES):
        h_start, h_end = sku_rows[cat["sku"]]
        row_n = 4 + cat_i
        last4_ref = f"'history'!D{h_end-3}:D{h_end}"
        vals = compute_forecast_values(sku_sales[cat["sku"]], cat, base)
        wb.cell(f"A{row_n}", value=cat["sku"])
        wb.cell(f"B{row_n}", value=f"W{WEEKS + 1}")  # W13 = forecast week
        wb.cell(f"C{row_n}", formula=f"=AVERAGE({last4_ref})")
        wb.cell(f"D{row_n}", value=vals["wd_factor"])
        wb.cell(f"E{row_n}", formula=f"=STDEV.P({last4_ref})*{SERVICE_LEVEL_Z}*SQRT({cat['lead_time']})")
        wb.cell(f"F{row_n}", formula=f"=IF({cat['shelf_life']}<{cat['lead_time']*SHELF_CRITICAL_RATIO},0.5,1.0)")
        wb.cell(f"G{row_n}", formula=f"=(C{row_n}*D{row_n}+E{row_n})*F{row_n}")
        wb.cell(f"H{row_n}", value="baseline")
        forecasts[cat["sku"]] = vals

    # NON_OBVIOUS_2: H22 — INCIDENT_2024_CORRECTION cell-content proxy
    wb.cell("H22", value=INCIDENT_2024_CORRECTION)
    return forecasts


def build_order(
    wb: Workbook, forecasts: dict[str, dict]
) -> dict[str, dict]:
    wb.sheet("order")
    wb.cell("A1", value=HEADER, fmt={"bold": True})
    wb.cell("A3", value="sku_name")
    wb.cell("B3", value="final_forecast")
    wb.cell("C3", value="current_stock")
    wb.cell("D3", value="lead_time_demand")
    wb.cell("E3", value="order_qty")
    wb.cell("F3", value="notes")

    orders: dict[str, dict] = {}
    for cat_i, cat in enumerate(CATEGORIES):
        row_n = 4 + cat_i
        forecast_row = 4 + cat_i
        final = forecasts[cat["sku"]]["final"]
        stock = DEFAULT_STOCK[cat["sku"]]
        order_qty = max(0, (final * cat["lead_time"]) - stock + (final * ORDER_BUFFER))
        # Mirror forecast.py compute_order: INCIDENT_2024_CORRECTION применяется
        # только для category='dairy' (NON_OBVIOUS_2 — legacy -8% rule post-инцидента 2024).
        if cat["cat"] == "dairy":
            order_qty *= INCIDENT_2024_CORRECTION
        wb.cell(f"A{row_n}", value=cat["sku"])
        wb.cell(f"B{row_n}", formula=f"='forecast'!G{forecast_row}")
        wb.cell(f"C{row_n}", value=stock)
        wb.cell(f"D{row_n}", formula=f"=B{row_n}*{cat['lead_time']}")
        # BUG-001 FIX (2026-08-08): Excel-формула теперь математически эквивалентна
        # forecast.py compute_order — INCIDENT_2024_CORRECTION применяется ко ВСЕМУ заказу:
        #   Excel:  =MAX(0,D-C+B*BUF)*CORR   (dairy) / *1.0 (прочие)
        #   Python: max(0, D-C+B*BUF) * CORR (dairy) / *1.0 (прочие)
        # Раньше: =MAX(0,D-C+B*BUF*CORR) — коррекция применялась только к буферу B*BUF,
        # расхождение с Python 8.3% для dairy (823.87 vs 760.90), parity не ловил.
        _corr = INCIDENT_2024_CORRECTION if cat["cat"] == "dairy" else 1.0
        wb.cell(f"E{row_n}", formula=f"=MAX(0,D{row_n}-C{row_n}+B{row_n}*{ORDER_BUFFER})*{_corr}")
        notes = "INCIDENT_2024_CORRECTION (-8%) применён" if cat["cat"] == "dairy" else ""
        wb.cell(f"F{row_n}", value=notes)
        orders[cat["sku"]] = {
            "final_forecast": final, "current_stock": stock, "order_qty": order_qty,
        }

    total = sum(o["order_qty"] for o in orders.values())
    total_row = 4 + len(CATEGORIES) + 1
    wb.cell(f"A{total_row}", value="TOTAL:", fmt={"bold": True})
    wb.cell(f"E{total_row}", formula=f"=SUM(E4:E{3+len(CATEGORIES)})", fmt={"bold": True})
    wb.cell(f"F{total_row}", value=f"total={total:.2f}")
    orders["_total"] = {"order_qty": total}
    return orders


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    sku_rows, sku_sales = build_history(wb, BASE_DATE)
    forecasts = build_forecast(wb, sku_rows, sku_sales, BASE_DATE)
    orders = build_order(wb, forecasts)
    wb.save(OUT_PATH)
    sidecar = {
        "forecasts": forecasts,
        "orders": {k: v for k, v in orders.items() if k != "_total"},
        "_meta": {
            "base_date": str(BASE_DATE),
            "weeks": WEEKS,
            "categories": [c["sku"] for c in CATEGORIES],
            "non_obvious": {
                "service_level_z": SERVICE_LEVEL_Z,
                "incident_2024_correction": INCIDENT_2024_CORRECTION,
            },
        },
    }
    SNAPSHOT_PATH.write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK: {OUT_PATH}")
    print(f"OK: {SNAPSHOT_PATH}")
    print(f"Snapshot summary: {len(CATEGORIES)} categories, total order = {orders['_total']['order_qty']:.2f}")


if __name__ == "__main__":
    main()
