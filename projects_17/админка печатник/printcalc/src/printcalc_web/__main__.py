"""Точка входа `python -m printcalc_web` — запуск uvicorn.

Хост/порт можно переопределить аргументами CLI (systemd-юнит передаёт
--host 0.0.0.0 --port 8300); по умолчанию — локальный запуск для разработки.
"""

from __future__ import annotations

import argparse

import uvicorn

from printcalc_web import create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="printcalc_web", description="PrintCalc Pro web (Phase 1)")
    parser.add_argument("--host", default="127.0.0.1", help="адрес привязки (по умолчанию 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8300, help="порт (по умолчанию 8300)")
    args = parser.parse_args()
    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
