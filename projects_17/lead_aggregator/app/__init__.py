"""lead_aggregator — Attract-модуль: поиск клиентов по запросу (промт 69, Фаза 3).

Асинхронный конвейер: запрос → сигнатуры → адаптеры источников → LDE (L1/L2/L3)
→ дедупликация → скоринг → checkpoint → доставка в Telegram.

Стек: Python 3.14 / httpx / asyncio / SQLite (WAL).
"""
