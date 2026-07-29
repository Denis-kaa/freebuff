# Agent Instructions for Freebuff CLI

> **Project:** `/mnt/sdcard/PROJECTS/workstation/freebuff`
> **Language:** Python 3.11+
> **Environment:** Android/Termux (ARM64)

## What this project is

This is **Freebuff AI Engineering Workspace** — a Python-based agentic platform and knowledge OS running in Termux on Android. It is NOT the npm `freebuff` CLI itself; it is the local workspace that the `freebuff` agent operates on.

## First things to do on every session

1. Read `BUFFY.md` (canonical agent manifest).
2. Read `TASK.md` for the current active task.
3. Read `CHANGELOG.md` for recent changes.
4. Run `python freebuff_cli.py status` to see active sessions and system health.

## Key files

| File | Purpose |
|------|---------|
| `BUFFY.md` | Agent identity, rules, environment, tools |
| `BUFFY_PROJECT.md` | Architecture and roadmap |
| `SPEC.md` | Technical specification |
| `TASK.md` | Current task |
| `CHANGELOG.md` | History of changes |
| `freebuff_cli.py` | Local CLI for sessions, status, conspect |
| `scripts/bootstrap.py` | Startup self-check and context recovery |
| `scripts/drift_check.py` | Daily documentation/code drift audit |

## Commands to verify work

```bash
# Tests
python -m pytest tests/ -v

# Type check (key files)
python -m mypy scripts/ core/ --ignore-missing-imports

# Local status
python freebuff_cli.py status
```

## Rules

- **Project State First:** The main entity is project state, not the chat.
- **Read before edit:** Study existing code and tests before modifying.
- **Run tests + mypy after changes.**
- **Keep docs in sync:** Update `CHANGELOG.md` and relevant docs when architecture changes.
- **No secrets in code:** Use `.env` and `.keys/` for credentials.
- **Prefer minimal changes** and reuse existing helpers.

### CODE QUALITY STANDARD — base, immutable rules (always apply)

> **Canonical source:** `pompts/CODE_QUALITY_STANDART.md`  
> **Rule:** Before writing or modifying any code, re-read the standard. If a choice exists between a quick fix and a reliable fix, always choose the reliable one. Every delivered script is considered **production-ready**.

All code must follow the standard defined in `pompts/CODE_QUALITY_STANDART.md`. Summarized, every script must be:

- **Modular & single-purpose** with low coupling, no duplication, no magic numbers/strings.
- **Readable** with clear names, comments, README, and consistent style.
- **Reliable** with error handling, logging, idempotency, and recovery.
- **Secure** with no hardcoded secrets, input validation, no arbitrary shell, no root requirements, Termux-safe.
- **Compatible** with Termux/Android/ARM64 and POSIX commands.
- **Efficient** with minimal RAM, disk, and process usage, using caches.
- **User-friendly** with `--help`, `--version`, DEBUG/QUIET modes, and correct exit codes.
- **Documented & tested** with install/run instructions, CLI params, dependency lists, and test scenarios.
- **Scalable** and following KISS, DRY, and SOLID where applicable.

> **Golden rule:** If a choice exists between a quick solution and a reliable solution, always choose the reliable one. Every delivered script is considered production-ready.

## What to avoid

- Don't install global packages without user confirmation.
- Don't push to Git remotes without confirmation.
- Don't modify files outside `/mnt/sdcard/PROJECTS/workstation/freebuff` without permission.
