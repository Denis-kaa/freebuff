"""Точка входа `python -m printcalc_web` — запуск uvicorn."""

from __future__ import annotations

import uvicorn

from printcalc_web import create_app

app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8300)
