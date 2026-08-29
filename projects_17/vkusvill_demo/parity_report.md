# Parity Report — vkusvill_demo (dual-leg: Python-consistency + Excel-eval)

**Leg 1 (Python-consistency):** `model_snapshot.json` (build_model_xlsx.py pre-computed values) vs `forecast_python.json` (forecast.py recompute).
**Leg 2 (Excel-eval, BUG-005 fix):** `excel_eval.py` — независимое вычисление формул прямо из `model_forecast.xlsx` (data_only=False) vs `forecast_python.json`.
**NO LibreOffice / Excel engine** — excel_eval.py парсит формулы сам (AVERAGE/STDEV.P/SQRT/IF/MAX/SUM, cross-sheet refs).
Tolerance: ±0.01 (float rounding).

## Leg 1 — Python-consistency (per-row)

- Крупа гречневая 800г sma: snapshot=92.5000, python=92.5000, diff=0.0000, **PASS**
- Крупа гречневая 800г wd_factor: snapshot=1.1000, python=1.1000, diff=0.0000, **PASS**
- Крупа гречневая 800г safety_buffer: snapshot=1.8448, python=1.8448, diff=0.0000, **PASS**
- Крупа гречневая 800г shelf_correction: snapshot=1.0000, python=1.0000, diff=0.0000, **PASS**
- Крупа гречневая 800г final_forecast: snapshot=103.5948, python=103.5948, diff=0.0000, **PASS**
- Крупа гречневая 800г order.order_qty: snapshot=513.3333, python=513.3333, diff=0.0000, **PASS**
- Молоко 3.2% 1л sma: snapshot=282.2500, python=282.2500, diff=0.0000, **PASS**
- Молоко 3.2% 1л wd_factor: snapshot=1.4000, python=1.4000, diff=0.0000, **PASS**
- Молоко 3.2% 1л safety_buffer: snapshot=3.4512, python=3.4512, diff=0.0000, **PASS**
- Молоко 3.2% 1л shelf_correction: snapshot=1.0000, python=1.0000, diff=0.0000, **PASS**
- Молоко 3.2% 1л final_forecast: snapshot=398.6012, python=398.6012, diff=0.0000, **PASS**
- Молоко 3.2% 1л order.order_qty: snapshot=760.8976, python=760.8976, diff=0.0000, **PASS**
- Напиток газир. 1л sma: snapshot=145.2500, python=145.2500, diff=0.0000, **PASS**
- Напиток газир. 1л wd_factor: snapshot=1.5000, python=1.5000, diff=0.0000, **PASS**
- Напиток газир. 1л safety_buffer: snapshot=2.3696, python=2.3696, diff=0.0000, **PASS**
- Напиток газир. 1л shelf_correction: snapshot=1.0000, python=1.0000, diff=0.0000, **PASS**
- Напиток газир. 1л final_forecast: snapshot=220.2446, python=220.2446, diff=0.0000, **PASS**
- Напиток газир. 1л order.order_qty: snapshot=662.7584, python=662.7584, diff=0.0000, **PASS**

**Leg 1 OVERALL: ✅ PASS**

## Leg 2 — Excel-eval vs Python (per-row, formulas from .xlsx)

- Молоко 3.2% 1л order_qty: excel_eval=760.8976, python=760.8976, diff=0.0000, **PASS**
- Молоко 3.2% 1л final_forecast: excel_eval=398.6012, python=398.6012, diff=0.0000, **PASS**
- Крупа гречневая 800г order_qty: excel_eval=513.3333, python=513.3333, diff=0.0000, **PASS**
- Крупа гречневая 800г final_forecast: excel_eval=103.5948, python=103.5948, diff=0.0000, **PASS**
- Напиток газир. 1л order_qty: excel_eval=662.7584, python=662.7584, diff=0.0000, **PASS**
- Напиток газир. 1л final_forecast: excel_eval=220.2446, python=220.2446, diff=0.0000, **PASS**
- TOTAL order_qty (order!E8): excel_eval=1936.9892, python=1936.9892, diff=0.0000, **PASS**

**Leg 2 OVERALL: ✅ PASS**

**OVERALL (Leg 1 AND Leg 2): ✅ PASS**
