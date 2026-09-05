"""
parity_check.py — reviewer-role артефакт (Task 2, variant (b) per Q1) — v3.

Dual-leg parity (BUG-005 fix, 2026-08-08):

- **Leg 1 — Python-consistency:** `model_snapshot.json` (build_model_xlsx.py
  pre-computed values) vs `forecast_python.json` (forecast.py recompute).
  Проверяет, что обе Python-реализации дают одинаковые числа.

- **Leg 2 — Excel-eval (independent):** `excel_eval.py` читает ФОРМУЛЫ прямо
  из `model_forecast.xlsx` (data_only=False) и вычисляет их независимым
  парсером (AVERAGE/STDEV.P/SQRT/IF/MAX/SUM, cross-sheet refs). Результат
  сравнивается с `forecast_python.json` (Python recompute).

  Это закрывает BUG-005: parity теперь реально доказывает, что формулы
  В ФАЙЛЕ (то, что посчитал бы Excel) дают те же значения, что Python —
  а не только Python-vs-Python.

Почему собственный evaluator вместо pycel/LibreOffice (Termux, Python 3.14):
- pycel падает на py3.14 (`ast.Str` removed); formulas требует numpy/pandas
  (не ставится на ARM64 Termux за разумное время); LibreOffice недоступен.
- excel_eval.py покрывает ровно подмножество формул demo и добавляет 0 новых
  зависимостей (только openpyxl, уже в requirements.txt).
"""
from __future__ import annotations

import json
import sys
***REMOVED***
from typing import Any

# sys.path injection: разрешить `import excel_eval` из той же папки
DEMO_DIR = Path("projects_17/vkusvill_demo")
sys.path.insert(0, str(DEMO_DIR))

from excel_eval import ExcelEval  # noqa: E402  (independent Excel formula evaluator)

SNAPSHOT = DEMO_DIR / "model_snapshot.json"          # build_model side
PYTHON_OUT = DEMO_DIR / "forecast_python.json"        # forecast.py side
XLSX = DEMO_DIR / "model_forecast.xlsx"               # source of formulas (leg 2)
REPORT = DEMO_DIR / "parity_report.md"

TOL = 0.01  # float tolerance для сравнения


def _load_json(path: Path) -> dict[str, Any***REMOVED***:
    """Read JSON dict (raw — no formula eval)."""
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Leg 1 — Python-consistency (snapshot vs python recompute)
# ---------------------------------------------------------------------------

def _compare_python(snapshot: dict, py_data: dict) -> tuple[bool, list[str***REMOVED******REMOVED***:
    """Pure-Python parity-check: snapshot.forecasts vs py_data[****REMOVED***.forecast."""
    overall_ok = True
    lines: list[str***REMOVED*** = [***REMOVED***
    snapshot_forecasts = snapshot.get("forecasts", {***REMOVED***)
    snapshot_orders = snapshot.get("orders", {***REMOVED***)

    for sku in sorted(snapshot_forecasts.keys()):
        snap_fc = snapshot_forecasts[sku***REMOVED***
        py_forecast = py_data.get(sku, {***REMOVED***).get("forecast", {***REMOVED***)
        py_order = py_data.get(sku, {***REMOVED***).get("order", {***REMOVED***)
        snap_order = snapshot_orders.get(sku, {***REMOVED***)

        for key, snap_key in (
            ("sma", "sma"),
            ("wd_factor", "wd_factor"),
            ("safety_buffer", "safety"),
            ("shelf_correction", "shelf"),
            ("final_forecast", "final"),
        ):
            sv = snap_fc.get(snap_key)
            pv = py_forecast.get(key)
            if sv is None or pv is None:
                ok = False
                diff_str = "MISSING"
            else:
                diff = abs(float(sv) - float(pv))
                ok = diff <= TOL
                diff_str = f"{diff:.4f***REMOVED***"
            sv_str = f"{float(sv):.4f***REMOVED***" if sv is not None else "None"
            pv_str = f"{float(pv):.4f***REMOVED***" if pv is not None else "None"
            overall_ok = overall_ok and ok
            lines.append(
                f"- {sku***REMOVED*** {key***REMOVED***: snapshot={sv_str***REMOVED***, python={pv_str***REMOVED***, "
                f"diff={diff_str***REMOVED***, **{'PASS' if ok else 'FAIL'***REMOVED*****"
            )

        so = snapshot_orders.get(sku, {***REMOVED***).get("order_qty")
        po = py_order.get("order_qty")
        if so is None or po is None:
            ok = False
            diff_str = "MISSING"
        else:
            diff = abs(float(so) - float(po))
            ok = diff <= TOL
            diff_str = f"{diff:.4f***REMOVED***"
        so_str = f"{float(so):.4f***REMOVED***" if so is not None else "None"
        po_str = f"{float(po):.4f***REMOVED***" if po is not None else "None"
        overall_ok = overall_ok and ok
        lines.append(
            f"- {sku***REMOVED*** order.order_qty: snapshot={so_str***REMOVED***, python={po_str***REMOVED***, "
            f"diff={diff_str***REMOVED***, **{'PASS' if ok else 'FAIL'***REMOVED*****"
        )
    return overall_ok, lines


# ---------------------------------------------------------------------------
# Leg 2 — Excel-eval vs Python recompute (independent formulas from xlsx)
# ---------------------------------------------------------------------------

# NOTE: должен оставаться синхронизированным с порядком `CATEGORIES` в
# build_model_xlsx.py (3 SKU, rows 4..6 в order/forecast листах). Если категории
# изменятся — обновить обе структуры.
SKU_BY_ROW = {4: "Молоко 3.2% 1л", 5: "Крупа гречневая 800г", 6: "Напиток газир. 1л"***REMOVED***


def _compare_excel_eval(py_data: dict) -> tuple[bool, list[str***REMOVED******REMOVED***:
    """Excel-eval: evaluate formulas from model_forecast.xlsx via excel_eval.py
    и сравнить с forecast_python.json (Python recompute)."""
    ev = ExcelEval(XLSX)
    overall_ok = True
    lines: list[str***REMOVED*** = [***REMOVED***

    # order_qty (order!E4:E6) и final_forecast (forecast!G4:G6)
    for row, sku in sorted(SKU_BY_ROW.items()):
        excel_order = ev.evaluate(f"order!E{row***REMOVED***")
        excel_final = ev.evaluate(f"forecast!G{row***REMOVED***")
        py_order = py_data.get(sku, {***REMOVED***).get("order", {***REMOVED***).get("order_qty")
        py_final = py_data.get(sku, {***REMOVED***).get("forecast", {***REMOVED***).get("final_forecast")

        for label, excel_v, py_v in (
            ("order_qty", excel_order, py_order),
            ("final_forecast", excel_final, py_final),
        ):
            if excel_v is None or py_v is None:
                ok = False
                diff_str = "MISSING"
            else:
                diff = abs(float(excel_v) - float(py_v))
                ok = diff <= TOL
                diff_str = f"{diff:.4f***REMOVED***"
            ex_str = f"{float(excel_v):.4f***REMOVED***" if excel_v is not None else "None"
            py_str = f"{float(py_v):.4f***REMOVED***" if py_v is not None else "None"
            overall_ok = overall_ok and ok
            lines.append(
                f"- {sku***REMOVED*** {label***REMOVED***: excel_eval={ex_str***REMOVED***, python={py_str***REMOVED***, "
                f"diff={diff_str***REMOVED***, **{'PASS' if ok else 'FAIL'***REMOVED*****"
            )

    # TOTAL (SUM order sheet) vs Python total — public helper, не лезем в _raw
    total_addr = None
    hit = ev.find_formula_cell("order", "E", prefix="=SUM(")
    if hit:
        total_addr = f"order!{hit[0***REMOVED******REMOVED***{hit[1***REMOVED******REMOVED***"
    excel_total = ev.evaluate(total_addr) if total_addr else None
    py_total = sum(
        py_data.get(sku, {***REMOVED***).get("order", {***REMOVED***).get("order_qty", 0.0)
        for sku in SKU_BY_ROW.values()
    )
    if excel_total is None:
        ok = False
        diff_str = "MISSING"
    else:
        diff = abs(float(excel_total) - float(py_total))
        ok = diff <= TOL
        diff_str = f"{diff:.4f***REMOVED***"
    overall_ok = overall_ok and ok
    ex_str = f"{float(excel_total):.4f***REMOVED***" if excel_total is not None else "None"
    lines.append(
        f"- TOTAL order_qty ({total_addr or 'order!E?'***REMOVED***): excel_eval={ex_str***REMOVED***, "
        f"python={py_total:.4f***REMOVED***, diff={diff_str***REMOVED***, **{'PASS' if ok else 'FAIL'***REMOVED*****"
    )
    return overall_ok, lines


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    if not SNAPSHOT.exists():
        print(f"ERR: {SNAPSHOT***REMOVED*** not found. Run build_model_xlsx.py first.")
        return 2
    if not PYTHON_OUT.exists():
        print(f"ERR: {PYTHON_OUT***REMOVED*** not found. Run forecast.py first.")
        return 2
    if not XLSX.exists():
        print(f"ERR: {XLSX***REMOVED*** not found. Run build_model_xlsx.py first.")
        return 2

    snapshot = _load_json(SNAPSHOT)
    py_data = _load_json(PYTHON_OUT)

    ok_1, lines_1 = _compare_python(snapshot, py_data)
    ok_2, lines_2 = _compare_excel_eval(py_data)
    overall_ok = ok_1 and ok_2

    lines_summary = [
        "# Parity Report — vkusvill_demo (dual-leg: Python-consistency + Excel-eval)",
        "",
        "**Leg 1 (Python-consistency):** `model_snapshot.json` (build_model_xlsx.py "
        "pre-computed values) vs `forecast_python.json` (forecast.py recompute).",
        "**Leg 2 (Excel-eval, BUG-005 fix):** `excel_eval.py` — независимое вычисление "
        "формул прямо из `model_forecast.xlsx` (data_only=False) vs `forecast_python.json`.",
        "**NO LibreOffice / Excel engine** — excel_eval.py парсит формулы сам "
        "(AVERAGE/STDEV.P/SQRT/IF/MAX/SUM, cross-sheet refs).",
        f"Tolerance: ±{TOL***REMOVED*** (float rounding).",
        "",
        "## Leg 1 — Python-consistency (per-row)",
        "",
    ***REMOVED*** + lines_1 + [
        "",
        f"**Leg 1 OVERALL: {'✅ PASS' if ok_1 else '❌ FAIL'***REMOVED*****",
        "",
        "## Leg 2 — Excel-eval vs Python (per-row, formulas from .xlsx)",
        "",
    ***REMOVED*** + lines_2 + [
        "",
        f"**Leg 2 OVERALL: {'✅ PASS' if ok_2 else '❌ FAIL'***REMOVED*****",
        "",
        f"**OVERALL (Leg 1 AND Leg 2): {'✅ PASS' if overall_ok else '❌ FAIL'***REMOVED*****",
        "",
    ***REMOVED***

    REPORT.write_text("\n".join(lines_summary), encoding="utf-8")
    print(f"OK: {REPORT***REMOVED*** written")
    print(f"Leg1(Python-consistency): {'PASS' if ok_1 else 'FAIL'***REMOVED***")
    print(f"Leg2(Excel-eval):         {'PASS' if ok_2 else 'FAIL'***REMOVED***")
    print(f"OVERALL:                  {'PASS' if overall_ok else 'FAIL'***REMOVED***")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
