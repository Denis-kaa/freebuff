"""CLI Reports Hub (спека §10.1). H1-каркас: `list` рабочий, `generate` —
минимальный прогон discovery + сборка пустых моделей (H2 добавит extract),
`serve`/`diff` — заглушки с честным сообщением «этап H5/H4».
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from services_08.reports_hub.config import DiscoveryError, discover_projects

DEFAULT_PROJECTS_ROOT = Path("projects_17")


def cmd_list(root: Path) -> int:
    """`list`: найденные проекты + статус (спека §10.1)."""
    projects = discover_projects(root)
    print(f"проектов найдено: {len(projects)} (корень {root})")
    for p in projects:
        if p.has_data:
            print(f"  [данные] {p.name} → {p.slug}")
        elif p.profile_error:
            print(f"  [ошибка] {p.name}: {p.profile_error}")
        else:
            print(f"  [нет данных] {p.name}: {p.reason}")
    return 0


def cmd_generate(root: Path, _force: bool) -> int:
    """H1-минимум: discovery + пустые ProjectReport-каркасы (extract — H2)."""
    from services_08.reports_hub.model import ReportModel

    try:
        projects = discover_projects(root)
    except DiscoveryError as exc:
        print(f"ошибка обхода: {exc}", file=sys.stderr)
        return 1
    model = ReportModel(generated_at="h1-scaffold", projects=[])
    _ = projects  # H2: extract-слой наполнит секции
    print(f"модель собрана (каркас H1): {len(model.to_json()['projects'])} проектов")
    print("extract-слой будет добавлен на H2 (спека §14.2)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="services_08.reports_hub")
    parser.add_argument("--root", type=Path, default=DEFAULT_PROJECTS_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    gen = sub.add_parser("generate")
    gen.add_argument("--force", action="store_true")
    sub.add_parser("serve")
    sub.add_parser("diff")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "list":
        return cmd_list(args.root)
    if args.command == "generate":
        return cmd_generate(args.root, args.force)
    if args.command == "serve":
        print("serve появится на H5 (спека §14.5)", file=sys.stderr)
        return 2
    print("diff появится на H4 (спека §14.4)", file=sys.stderr)
    return 2
