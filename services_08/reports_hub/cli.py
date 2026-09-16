"""CLI Reports Hub: generate / serve / list / diff (спека §10.1, каркас H1).

Полная генерация и сервер — этапы H3–H5. В H1: каркас команд,
``list`` (автообход проектов) работает, остальные — честная заглушка.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _projects_root() -> Path:
    """Корень projects_17/ относительно репозитория платформы."""
    here = Path(__file__).resolve()
    # services_08/reports_hub/cli.py -> корень = parents[2]
    return here.parents[2] / "projects_17"


def cmd_list(args: argparse.Namespace) -> int:
    """Показать обнаруженные проекты (автообход + статусы)."""
    from services_08.reports_hub.config import discover_projects

    root = Path(args.projects_root) if args.projects_root else _projects_root()
    profiles = discover_projects(root)
    for profile in profiles:
        if profile.excluded:
            status = "excluded"
        elif profile.invalid_reason:
            status = f"INVALID: {profile.invalid_reason}"
        elif profile.has_report_docs:
            status = "has-docs"
        else:
            status = "no-data"
        print(f"{profile.slug}\t{status}\t{profile.title}")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Заглушка generate (полная реализация — H3)."""
    print("generate: не реализовано в H1 (этап H3 по спеке §14)", file=sys.stderr)
    return 2


def cmd_serve(args: argparse.Namespace) -> int:
    """Заглушка serve (полная реализация — H5)."""
    print("serve: не реализовано в H1 (этап H5 по спеке §14)", file=sys.stderr)
    return 2


def cmd_diff(args: argparse.Namespace) -> int:
    """Заглушка diff (полная реализация — H4)."""
    print("diff: не реализовано в H1 (этап H4 по спеке §14)", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    """Построить argparse-парсер CLI."""
    parser = argparse.ArgumentParser(prog="reports_hub", description="Reports Hub — сервис отчётов платформы")
    sub = parser.add_subparsers(dest="command", required=True)

    p_generate = sub.add_parser("generate", help="сгенерировать сайт отчётов")
    p_generate.add_argument("--project", default=None, help="slug проекта (по умолчанию — все)")
    p_generate.add_argument("--platform", action="store_true", help="включить отчёт платформы")
    p_generate.add_argument("--all", action="store_true", help="все проекты + платформа")
    p_generate.add_argument("--force", action="store_true", help="перегенерировать принудительно")
    p_generate.set_defaults(func=cmd_generate)

    p_serve = sub.add_parser("serve", help="локальный сервер просмотра")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8310)
    p_serve.set_defaults(func=cmd_serve)

    p_list = sub.add_parser("list", help="обнаруженные проекты")
    p_list.add_argument("--projects-root", default=None, help="каталог projects_17 (для тестов)")
    p_list.set_defaults(func=cmd_list)

    p_diff = sub.add_parser("diff", help="diff последней генерации")
    p_diff.add_argument("--project", default=None, help="slug проекта")
    p_diff.set_defaults(func=cmd_diff)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
