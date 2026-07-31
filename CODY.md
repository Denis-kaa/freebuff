# CODY.md — Freebuff Workspace

For full context, read `docs/core/CORE_PROMPT.md` (identity, duties, constraints, behavior), `BUFFY.md` and `AGENTS.md`.

This is the **Freebuff AI Engineering Workspace** — a Python-based agentic platform and Knowledge OS running in Termux on Android (ARM64).

## Quick protocol

1. Read `docs/core/CORE_PROMPT.md` first (single source of truth for behavior).
2. Read `BUFFY.md` and `AGENTS.md`.
3. Read `TASK.md` and `CHANGELOG.md`.
4. Run `python freebuff_cli.py status` to see system state.
5. After changes run `python -m pytest tests/ -v` and `python -m mypy scripts/ core/ --ignore-missing-imports`.

See `AGENTS.md` for the complete agent protocol.
