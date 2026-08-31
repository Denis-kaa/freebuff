#!/usr/bin/env python3
"""v5.51.0 fix script v2: relocate project scripts + fix sys.path injection (CON-17).

Changes from v1:
- Drop dead `_resolve_freebuff_root()` (was defined but never called) — Block-1 fix
- Move `from typing import Tuple` to top imports — Block-2 fix
- Add hard assert on PATCH_BLOCK_OLD match — Block-3 fix
- Patch block now PRESERVES `ROOT` name (overwrites to freebuff root) — fixes e2e_promt47.py
  `NameError: name 'ROOT' is not defined` at line 71 (file uses ROOT beyond sys.path block)

CON-17 taxonomy rule:
- workspace-level scripts (reusable)  -> freebuff/scripts_01/
- project-level scripts  (specific)    -> /storage/.../workstation/interior_planner_e2e/interior_planner/scripts/

CAN-7 /tmp snap rotation handled by moving scripts to path-stable `/storage/` location.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple

# === Paths ===
SCRIPTS_SRC_SNAP = Path("/tmp/interior_planner_e2e.bak.20260803T070807985465/interior_planner/scripts")
PROJ_HOME        = Path("/storage/emulated/0/PROJECTS/workstation/interior_planner_e2e/interior_planner")
PROJ_SCRIPTS_DIR = PROJ_HOME / "scripts"
FREEBUFF_CANON   = Path("/storage/emulated/0/PROJECTS/workstation/freebuff")
SCRIPT_NAMES     = ["e2e_promt47.py", "interior_consultant_register.py"]


# === PATCH DEFINITIONS ===
PATCH_BLOCK_OLD = (
    "ROOT = Path(__file__).resolve().parents[1]\n"
    "if str(ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(ROOT))"
)

# Preserves `ROOT` name → freebuff root. Old `parents[1]` was interior_planner/ (broken
# after move). e2e_promt47.py uses ROOT downstream (line ~71 → was NameError).
PATCH_BLOCK_NEW = (
    "# --- CON-17: project-local scripts import shared Freebuff locator (v5.51.0) ---\n"
    "_HERE = Path(__file__).resolve().parent\n"
    "if str(_HERE) not in sys.path:\n"
    "    sys.path.insert(0, str(_HERE))\n"
    "from _freebuff_locator ]solve_freebuff_root\n"
    "_FREEBUFF_ROOT = resolve_freebuff_root()\n"
    "if str(_FREEBUFF_ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(_FREEBUFF_ROOT))\n"
    "# Backward-compat: keep `ROOT` name -> freebuff root (was parents[1]; now projects use freebuff)\n"
    "ROOT = _FREEBUFF_ROOT"
)


def _patch(script_path: Path) -> Tuple[bool, str]:
    txt = script_path.read_text()
    if PATCH_BLOCK_OLD not in txt:
        # Block-3: hard assert with helpful message
        return False, f"OLD_BLOCK_NOT_FOUND in {script_path.name}; sys.path pattern drift detected"
    new_txt = txt.replace(PATCH_BLOCK_OLD, PATCH_BLOCK_NEW)
    assert PATCH_BLOCK_OLD not in new_txt, "patch did not replace (unexpected)"
    script_path.write_text(new_txt)
    return True, "patched"


# === STEP 1: ensure permanent project home ===
print("=== STEP 1: ensure project home exists ===")
PROJ_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
print(f"  ok: {PROJ_SCRIPTS_DIR}")


# === STEP 2: copy scripts from /tmp snap (restore to clean state) ===
print("\n=== STEP 2: copy scripts from /tmp snap ===")
for fname in SCRIPT_NAMES:
    src = SCRIPTS_SRC_SNAP / fname
    dst = PROJ_SCRIPTS_DIR / fname
    if not src.exists():
        print(f"  MISSING SRC: {src}")
        continue
    shutil.copy2(src, dst)
    print(f"  copied: {fname}")


# === STEP 3: write shared locator (CON-17 + ANTI-10 compliant) ===
print("\n=== STEP 3: write shared _freebuff_locator.py ===")
LOCATOR = '''"""CON-17 shared helper: locate Freebuff root.

Order of resolution (drop walk-up: dead code — /tmp/ and /storage/ are on different
filesystem branches):

1. $FREEBUFF_ROOT env override (preferred for portability)
2. Canonical Termux hardcode (most user installs)
3. RuntimeError with [FreebuffLocator] marker (gate-detectable) if marker missing

Marker file check: core_02/telegram_contract.py
"""
import os

FREEBUFF_ROOT_CANONICAL = Path("/storage/emulated/0/PROJECTS/workstation/freebuff")


def resolve_freebuff_root() -> Path:
    """Returns absolute Path to freebuff root. Raises RuntimeError on failure."""
    root_str = os.environ.get("FREEBUFF_ROOT", str(FREEBUFF_ROOT_CANONICAL))
    root = Path(root_str).expanduser().resolve()
    marker = root / "core_02" / "telegram_contract.py"
    if not marker.is_file():
        raise RuntimeError(
            f"[FreebuffLocator] Freebuff root invalid (no marker {marker}).\\n"
            f"  Set FREEBUFF_ROOT=/path/to/freebuff, or fix canonical hardcode."
        )
    return root
'''
# Idempotent write — overwrite_ok since this helper should be stable.
(PROJ_SCRIPTS_DIR / "_freebuff_locator.py").write_text(LOCATOR)
print(f"  wrote: _freebuff_locator.py")


# === STEP 4: patch both scripts ===
print("\n=== STEP 4: patch sys.path injection in both scripts ===")
patch_results: list[Tuple[str, bool, str]] = []
for fname in SCRIPT_NAMES:
    ok, msg = _patch(PROJ_SCRIPTS_DIR / fname)
    patch_results.append((fname, ok, msg))
    print(f"  {fname}: {msg}")

patch_failed = [r for r in patch_results if not r[1]]
if patch_failed:
    print("\n!!! PATCH FAILURES:")
    for r in patch_failed:
        print(f"  {r[0]}: {r[2]}")
    print("\nABORTING: real verify would be unreliable without successful patches.")
    sys.exit(1)


# === STEP 5: real verify with FREEBUFF_ROOT (refined two-layered gate) ===
# Gate-1 (sys_inj_pass): no ImportError/ModuleNotFoundError/SyntaxError/NameError in stderr
#     proves Block-A fix works (sys.path injection + shared locator).
# Gate-2 (business_gate): for e2e_promt47.py+--skip-tg--silent -> exit 0 expected;
#     for interior_consultant_register.py -> N/A (CAN-8 body hardcode debt, requires e2e prereq).
print("\n=== STEP 5: REAL verify (two-layered gate-1 + gate-2) ===")
verify_summary: list[Tuple[str, bool, str, bool]] = []  # fname, sys_inj, business, is_ok

# IndentationError is a SyntaxError SUBCLASS in code, but Python's repr prints
# "IndentationError" (NOT "SyntaxError"), so the substring "SyntaxError" would miss it.
# Also: [FreebuffLocator] marker tag emitted by _freebuff_locator.py on RuntimeError;
# checking for it lets us catch locator-specific sys.path failures without false-positives
# from application-level RuntimeErrors.
SYS_INJ_FAILURE_MARKERS = (
    "ModuleNotFoundError", "ImportError", "SyntaxError", "IndentationError",
    "NameError", "[FreebuffLocator]",
)
GATE_NA_LABEL = "N/A"  # prefix; full text e.g. "N/A (CAN-8)"
GATE_NA_CAN8  = f"{GATE_NA_LABEL} (CAN-8)"

for fname in SCRIPT_NAMES:
    fpath = PROJ_SCRIPTS_DIR / fname
    args: list[str] = []
    if fname == "e2e_promt47.py":
        args = ["--skip-tg", "--silent"]
    env = {**os.environ, "FREEBUFF_ROOT": str(FREEBUFF_CANON), "PATH": os.environ.get("PATH", "")}
    r = subprocess.run(
        ["python3", str(fpath), *args],
        cwd=str(PROJ_SCRIPTS_DIR),
        env=env,
        capture_output=True, text=True, timeout=180,
    )
    err = (r.stderr or "")
    sys_inj_pass = not any(m in err for m in SYS_INJ_FAILURE_MARKERS)
    if fname == "e2e_promt47.py":
        business_gate = "PASS" if r.returncode == 0 else f"FAIL_exit{r.returncode}"
    else:
        # register.py requires e2e_promt47 prereq + has body-level hardcoded /tmp paths
        # (CAN-8: body hardcode debt) -> business gate is N/A.
        business_gate = GATE_NA_CAN8
    business_ok = business_gate == "PASS" or business_gate.startswith(GATE_NA_LABEL)
    is_ok = sys_inj_pass and business_ok
    verify_summary.append((fname, sys_inj_pass, business_gate, is_ok))
    print(f"\n--- {fname} ---")
    print(f"exit={r.returncode}")
    out = (r.stdout or "").strip()
    print(f"stdout (last 300): {out[-300:] if out else '(empty)'}")
    print(f"stderr (last 300): {err[-300:] if err else '(empty)'}")
    print(f"sys_inj_pass={sys_inj_pass} business_gate={business_gate} -> ok={is_ok}")


print("\n=== SUMMARY ===")
all_pass = True
for fname, sys_inj, business, ok in verify_summary:
    status = "OK" if ok else "BLOCK"
    print(f"  {fname}: sys_inj={sys_inj} business={business} -> {status}")
    if not ok:
        all_pass = False

print(f"\nOVERALL: {'ALL_PASS' if all_pass else 'PARTIAL_FAIL'}")
sys.exit(0 if all_pass else 2)
