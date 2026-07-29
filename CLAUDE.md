# CLAUDE.md — Freebuff Workspace

For full context, read `BUFFY.md` and `AGENTS.md`.

This is the **Freebuff AI Engineering Workspace** — a Python-based agentic platform and Knowledge OS running in Termux on Android (ARM64).

## Quick protocol

1. Read `BUFFY.md` first.
2. Read `TASK.md` and `CHANGELOG.md`.
3. Run `python freebuff_cli.py status` to see system state.
4. After changes run `python -m pytest tests/ -v` and `python -m mypy scripts/ core/ --ignore-missing-imports`.

See `AGENTS.md` for the complete agent protocol.
