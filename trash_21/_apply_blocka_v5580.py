"""Block-A recovery apply script (v5.58.0).

Replaces the parents[1] sys.path block in BOTH canonical sibling-project
scripts with the locator+resolver pattern. Locator file
`scripts/_freebuff_locator.py` is written by the parent (write_file tool)
BEFORE this apply runs; this script only does the two str_replacements.

Idempotent: if a script already uses locator pattern, no-op (warn + skip).
"""
from __future__ import annotations
from pathlib import Path

PROJ = Path(
    "/storage/emulated/0/PROJECTS/workstation/interior_planner_e2e/"
    "interior_planner/scripts"
)

REGISTER = PROJ / "interior_consultant_register.py"
E2E = PROJ / "e2e_promt47.py"


def replace_block(path: Path, old: str, new: str, label: str) -> bool:
    """Replace exact-string `old` → `new` in `path`. Returns True on success."""
    if not path.exists():
        print(f"  [{label}] ERROR: {path} not found")
        return False
    text = path.read_text()
    if "from _freebuff_locator ]solve_freebuff_root" in text:
        print(f"  [{label}] already-applied (locator import present) — SKIP")
        return True
    if old not in text:
        print(f"  [{label}] ERROR: pattern not found in {path}")
        return False
    path.write_text(text.replace(old, new, 1))
    print(f"  [{label}] OK — {path}")
    return True


# ---- register.py --------------------------------------------------------
REGISTER_OLD = (
    "# --- Restore CON-17 sys.path block (Option A: keep parents[1] form for CAN-8 closure) ---\n"
    "# NOTE: `parents[1]` (= parent of scripts/ = interior_planner/) does NOT contain\n"
    "# core_02/, so this block alone does NOT enable core_02 import. Real core_02\n"
    "# discovery requires Block-A recovery (`from _freebuff_locator import ...`)\n"
    "# which is a SEPARATE debt; CAN-8 closure kept parents[1] form per scope.\n"
    "ROOT = Path(__file__).resolve().parents[1]\n"
    "if str(ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(ROOT))\n"
)
REGISTER_NEW = (
    "# --- Freebuff locator (Block-A recovery, v5.58.0) ---\n"
    "# Resolves Freebuff root so `core_02/` is importable WITHOUT PYTHONPATH env.\n"
    "# Resolution: $FREEBUFF_ROOT > canonical hardcode (`/storage/.../freebuff`).\n"
    "# See canonical scripts/_freebuff_locator.py for the contract.\n"
    "from _freebuff_locator ]solve_freebuff_root\n"
    "ROOT = resolve_freebuff_root()\n"
    "if str(ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(ROOT))\n"
)

# ---- e2e_promt47.py -----------------------------------------------------
E2E_OLD = (
    "ROOT = Path(__file__).resolve().parents[1]\n"
    "if str(ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(ROOT))\n"
)
E2E_NEW = (
    "# --- Freebuff locator (Block-A recovery, v5.58.0) ---\n"
    "# Resolves Freebuff root so `core_02/` is importable WITHOUT PYTHONPATH env.\n"
    "# Resolution: $FREEBUFF_ROOT > canonical hardcode (`/storage/.../freebuff`).\n"
    "# Note: ROOT is now the Freebuff root (not `parents[1]`); downstream refs\n"
    "# (DEFAULT_E2E_LOG, PROMT47_FILE, _CANONICAL_MANIFEST) resolve into Freebuff's\n"
    "# docs_10/ runtime_05/ pompts_11/ — fixing a silent drift where they had been\n"
    "# pointing to `interior_planner/`.\n"
    "from _freebuff_locator ]solve_freebuff_root\n"
    "ROOT = resolve_freebuff_root()\n"
    "if str(ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(ROOT))\n"
)


def main() -> int:
    print("=== Block-A recovery apply (v5.58.0) ===\n")
    ok_register = replace_block(REGISTER, REGISTER_OLD, REGISTER_NEW, "register")
    ok_e2e = replace_block(E2E, E2E_OLD, E2E_NEW, "e2e_promt47")
    print()
    if ok_register and ok_e2e:
        print("=== Block-A apply complete ✅ ===")
        return 0
    print("=== Block-A apply INCOMPLETE — see errors above ===")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
