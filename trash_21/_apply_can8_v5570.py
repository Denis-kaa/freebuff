#!/usr/bin/env python3
"""CAN-8 closure apply script (v5.57.0).

Surgical body-level /tmp hardcode removal in the project-local scripts.
Idempotent: re-runs are safe (each old-string match is unique-by-design).
Raises on missing/multi-match patterns to surface drift early.

Edits:
1. interior_consultant_register.py
   - Add `import os`
   - Replace sys.path block (v5.51.0 fix) — still uses `parents[1]` here
   - Insert inline `def resolve_interior_planner_home()` (CAP-8 closure)
   - DEFAULT_ARTIFACT: drop `Path(str(...))` cast, use resolver directly
   - DEFAULT_SEED: replace /tmp hardcode with resolver-derived Path
   - Docstring L5: `/tmp/interior_planner_seed/` → `$INTERIOR_PLANNER_HOME/interior_planner_seed/`
   - Help strings L14-15: similar update (ANTI-11 holistic)
2. e2e_promt47.py
   - Inline resolver body: canonical fallback `/tmp/interior_planner_e2e` → `/storage/.../interior_planner_e2e`
     (the inline resolver was already in place per v5.56.0, but pointed at OLD path;
      v5.57.0 corrects it to post-relocation canonical).

After apply, the helper `_interior_planner_home.py` is dropped (anti-fragile
inline-only decision per thinker-with-files recommendation).
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(
    "/storage/emulated/0/PROJECTS/workstation/interior_planner_e2e/interior_planner/scripts"
)
REG = SCRIPTS_DIR / "interior_consultant_register.py"
E2E = SCRIPTS_DIR / "e2e_promt47.py"
HELPER = SCRIPTS_DIR / "_interior_planner_home.py"


# ─── Edit 1: register.py sys.path/imports/inline def/DEFAULT_ARTIFACT/DEFAULT_SEED ───
old_reg_a = (
    "import argparse\n"
    "import shutil\n"
    "import sys\n"
    "]\n"
    "\n"
    "\n"
    "ROOT = Path(__file__).resolve().parents[1]\n"
    "if str(ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(ROOT))\n"
    "\n"
    "\n"
    "DEFAULT_ARTIFACT = Path(\n"
    "    str(resolve_interior_planner_home() / \"interior_planner\" / \"roles\" / \"18_interior_consultant.md\")\n"
    ")\n"
    "DEFAULT_SEED = Path(\"/tmp/interior_planner_seed\")\n"
)
new_reg_a = (
    "import argparse\n"
    "import os\n"
    "import shutil\n"
    "import sys\n"
    "]\n"
    "\n"
    "\n"
    "# --- Workspace locator (CAN-8 closure, v5.57.0) ---\n"
    "# Inline def mirrors e2e_promt47.py — anti-fragile (helper file can be lost\n"
    "# on relocation; inline lives with the script). Resolution chain:\n"
    "# $INTERIOR_PLANNER_HOME env override > canonical hardcode (post-v5.51.0).\n"
    "def resolve_interior_planner_home() -> Path:\n"
    "    \"\"\"Resolve project-home root: $INTERIOR_PLANNER_HOME > canonical /storage/.../interior_planner_e2e.\"\"\"\n"
    "    return Path(\n"
    "        os.environ.get(\n"
    "            \"INTERIOR_PLANNER_HOME\",\n"
    "            \"/storage/emulated/0/PROJECTS/workstation/interior_planner_e2e\",\n"
    "        )\n"
    "    )\n"
    "\n"
    "\n"
    "DEFAULT_ARTIFACT = (\n"
    "    resolve_interior_planner_home() / \"interior_planner\" / \"roles\" / \"18_interior_consultant.md\"\n"
    ")\n"
    "DEFAULT_SEED = resolve_interior_planner_home() / \"interior_planner_seed\"\n"
)

# ─── Edit 2: register.py docstring L5 (seed path mention) ───
old_reg_b = (
    "2. Builds local seed at /tmp/interior_planner_seed/ (registry.yaml + minimal scaffold)."
)
new_reg_b = (
    "2. Builds local seed at $INTERIOR_PLANNER_HOME/interior_planner_seed/ (registry.yaml + minimal scaffold)."
)

# ─── Edit 3: register.py help strings L14-15 (artifact + seed-dir defaults) ───
old_reg_c = (
    "    [--artifact PATH]                  # default /tmp/interior_planner_e2e/interior_planner/roles/18_interior_consultant.md\n"
    "    [--seed-dir PATH]                  # default /tmp/interior_planner_seed\n"
)
new_reg_c = (
    "    [--artifact PATH]                  # default = $INTERIOR_PLANNER_HOME/interior_planner/roles/18_interior_consultant.md\n"
    "    [--seed-dir PATH]                  # default = $INTERIOR_PLANNER_HOME/interior_planner_seed\n"
)

# ─── Edit 4: e2e_promt47.py inline resolver canonical fallback (was /tmp, now /storage/...) ───
old_e2e = (
    '    return Path(os.environ.get("INTERIOR_PLANNER_HOME", "/tmp/interior_planner_e2e"))'
)
new_e2e = (
    '    return Path(\n'
    '        os.environ.get(\n'
    '            "INTERIOR_PLANNER_HOME",\n'
    '            "/storage/emulated/0/PROJECTS/workstation/interior_planner_e2e",\n'
    '        )\n'
    "    )"
)


def apply(path: Path, edits: list[tuple[str, str, str]]) -> None:
    txt = path.read_text()
    for label, old, new in edits:
        if old not in txt:
            raise SystemExit(
                f"  ✗ {path.name}: pattern not found for '{label}'\n"
                f"    Hint: pattern drift — re-read canonical content. ABORT."
            )
        if txt.count(old) > 1:
            raise SystemExit(
                f"  ✗ {path.name}: '{label}' appears {txt.count(old)} times (ambiguous). ABORT."
            )
        txt = txt.replace(old, new)
        print(f"  ✓ {path.name}: {label}")
    path.write_text(txt)


print("=== Applying CAN-8 edits (v5.57.0) ===\n")
apply(
    REG,
    [
        ("sys.path + inline def + DEFAULT_ARTIFACT + DEFAULT_SEED", old_reg_a, new_reg_a),
        ("docstring L5 seed path", old_reg_b, new_reg_b),
        ("help strings L14-15", old_reg_c, new_reg_c),
    ],
)
print()
apply(E2E, [("inline resolver canonical fallback /tmp -> /storage/...", old_e2e, new_e2e)])

# Drop helper file (anti-fragile: function lives inline in both scripts now)
print()
if HELPER.exists():
    HELPER.unlink()
    print(f"  ✓ dropped helper: {HELPER}")
else:
    print(f"  - helper already absent: {HELPER}")

print("\n=== CAN-8 apply complete ===")
