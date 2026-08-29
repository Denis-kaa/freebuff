#!/usr/bin/env python3
"""
[5.61.0***REMOVED*** regression — pompts_11/ NNN_TT_имя.md convention hardening.

User directive (v5.61.0): "добавь regression-тест на naming convention."

Two-layer guard:
  (a) Reuse `consistency_check.check_naming_convention` (Stage 9) via `build_report(PROJECT_ROOT)`
      — if consistency_check raises prompt violation, this test catches the drift.
  (b) Direct local scan — assert each file in `pompts_11/` matches `^[0-9***REMOVED***+_[0-9***REMOVED***+_.*\.md$`
      with NNN in 001..999, TT in 01..14 (canonical theme codes per FINAL_STRUCTURE §2.1).
      This is independent from consistency_check and survives a regression where the
      broader consistency_check is bypassed.

Why both layers?
  - Layer (a) = "the official auditor says clean" (catches via integrity of build_report).
  - Layer (b) = "the actual files all match the regex literally" (catches via standalone
    pytest, runs even if scripts_01/ isn't importable).

When to update this test:
  - Add new canonical theme codes (FINAL_STRUCTURE §2.1) → extend _VALID_THEMES tuple.
  - DEBT-CLOSED: 2026-08-03 (v5.61.0). Historical context:
      * Until v5.51.0 the file was bare `promt47.md`.
      * In v5.61.0 it was renamed to `047_06_e2e_platform_test.md` (046_06 was available
        chronologically before this v5.61.0 commit; gap 018–021/035 already documented).
      * This test ensures no naked prompt file reappears (the failure mode v5.61.0 closed).

Independent of consistency_check's `check_naming_convention`:
  That's a registry-driven check; this is a file-driven check.
  Both should agree. If they ever disagree, that's a meta-bug — but in practice this
  test catches a `prompts_11/structure.md` (legacy) or `prompts_11/error.md` (artifact)
  faster than consistency_check does, because consistency_check runs once a day.
"""

from __future__ import annotations

***REMOVED***
import sys
***REMOVED***

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Convention pattern (FINAL_STRUCTURE §2.1). Imports mirror
#    scripts_01/consistency_check.py::_PROMPT_FILE_RE for parity.
_PROMPT_NAME_RE = re.compile(r"^(\d{3***REMOVED***)_(\d{2***REMOVED***)_.*\.md$")

# Canonical theme codes (FINAL_STRUCTURE §2.1: TT = 01..14; same set as
# scripts_01/consistency_check._VALID_THEME_CODES). If a new theme code is added
# in FINAL_STRUCTURE, update both this tuple AND consistency_check.
_VALID_THEMES: frozenset[str***REMOVED*** = frozenset({f"{i:02d***REMOVED***" for i in range(1, 22)***REMOVED***)  # 01..21: синхронизировано с consistency_check._VALID_THEME_CODES (темы 15-21: promt52-58)

# Files explicitly exempt from NNN_TT_имя.md (служебные файлы очереди pompts_11;
# синхронизировано со skip в scripts_01/consistency_check.py naming-проверке).
EXEMPT_FILES: frozenset[str***REMOVED*** = frozenset({"README.md", "errors.md"***REMOVED***)


# ═══════════════════════════════════════════════════════════════
# Layer (b): direct file scan
# ═══════════════════════════════════════════════════════════════


class TestPromptNameRegex:
    """Pure regex compliance — single file, no project coupling."""

    @pytest.mark.parametrize("name", [
        "001_01_workspace_os.md",
        "014_02_arhitektura.md",
        "032_09_konsolidaciya.md",
        "038_03_audit_prompt.md",
        "046_09_tripwire_v1.md",
        "047_06_e2e_platform_test.md",  # v5.61.0 canonical name post-rename
        "043_08_workspace_os_ui.md",
        "999_14_max_test.md",  # synthetic for boundary
    ***REMOVED***)
    def test_valid_names_ok(self, name: str) -> None:
        m = _PROMPT_NAME_RE.match(name)
        assert m is not None, f"{name***REMOVED*** не соответствует NNN_TT_имя.md"
        n, t = m.group(1), m.group(2)
        assert len(n) == 3 and n.isdigit()
        assert t in _VALID_THEMES

    @pytest.mark.parametrize("name", [
        "promt47.md",                       # bare name (post-v5.40.0 debt)
        "README.md",                        # index file in pompts dir
        "structure.md",                     # legacy artifact
        "promt18.md",                       # legacy empty
        "001_first.md",                     # missing TT
        "001_99_bad_theme.md",              # TT out of canonical range
        "001_01_no_extension",              # missing .md
        "_01.md",                           # missing NNN
        "abc_01_test.md",                   # non-digit NNN
        "prompts_11.md",                    # weird
        "047_06_e2e_platform_test.txt",     # wrong extension
    ***REMOVED***)
    def test_invalid_names_detected(self, name: str) -> None:
        """Bad names MUST be detected as invalid (either via regex rejection OR theme-code violation).

        Test PASSES (NOT fails) when invalidity is detected via EITHER layer:
          - (a) base regex rejects structurally malformed names → early `return`.
          - (b) base regex matches but theme code falls outside canonical set →
                 assertion `m.group(2) not in _VALID_THEMES` confirms violation.

        Symmetric to `test_valid_names_ok` (also Layer A): together they prove
        the regex + theme-code combo correctly partitions name space.
        """
        m = _PROMPT_NAME_RE.match(name)
        if m is None:
            # Layer (a): base regex correctly rejected everything after `prompts_11/<name>.md`-prefix.
            # No theme-code check needed — the structural mismatch is enough.
            return
        # Layer (b): if regex matched, theme code MUST be outside canonical set.
        # If theme IS canonical (passes the assert), the name is actually valid → test fixture bug.
        assert m.group(2) not in _VALID_THEMES, (
            f"{name***REMOVED*** matched base regex AND theme {m.group(2)***REMOVED*** IS canonical — "
            f"this name should have been in test_valid_names_ok, not here. "
            f"(strict-validate theme: 99/15/etc outside 01..14 are detected)"
        )


class TestPomptsDirectory:
    """Concrete project: каждой файл в pompts_11/ should match NNN_TT_имя.md."""

    def test_prompts_dir_present(self) -> None:
        assert (PROJECT_ROOT / "pompts_11").is_dir(), (
            "pompts_11/ отсутствует в PROJECT_ROOT — directory lost?"
        )

    def test_no_bare_name_files(self) -> None:
        prompts_dir = PROJECT_ROOT / "pompts_11"
        violations: list[str***REMOVED*** = [***REMOVED***
        for path in sorted(prompts_dir.glob("*.md")):
            if path.name in EXEMPT_FILES:
                continue
            m = _PROMPT_NAME_RE.match(path.name)
            if m is None:
                violations.append(
                    f"{path.name***REMOVED***: bare name (no NNN_TT_ prefix) — "
                    f"violates FINAL_STRUCTURE §2.1"
                )
                continue
            if m.group(2) not in _VALID_THEMES:
                violations.append(
                    f"{path.name***REMOVED***: theme code TT={m.group(2)***REMOVED*** outside "
                    f"canonical 01..14 (FINAL_STRUCTURE §2.1)"
                )
        assert violations == [***REMOVED***, (
            "pompts_11/ имеет NNN_TT нарушения — это и есть debt §5.13:\n"
            + "\n".join(f"  - {v***REMOVED***" for v in violations)
        )

    def test_promt47_renamed(self) -> None:
        """[5.61.0***REMOVED*** Регрессия-guard: `prompts_11/promt47.md` НЕ должен
        вновь появиться. Если кто-то когда-то откатит rename — этот
        тест мигом упадёт."""
        bad = PROJECT_ROOT / "pompts_11" / "promt47.md"
        assert not bad.exists(), (
            f"{bad***REMOVED*** появился снова — откатил rename из v5.61.0? "
            f"Каноническая версия файла теперь `047_06_e2e_platform_test.md`"
        )

    def test_renamed_file_exists(self) -> None:
        """Положительная проверка: новый файл живёт там где должен."""
        canonical = PROJECT_ROOT / "pompts_11" / "047_06_e2e_platform_test.md"
        assert canonical.is_file(), (
            f"{canonical***REMOVED*** отсутствует — rename из v5.61.0 не выполнился?"
        )

    def test_prompts_unique_numbers(self) -> None:
        """Номера NNN должны быть уникальны (gaps OK, duplicates NOT)."""
        seen: dict[str, str***REMOVED*** = {***REMOVED***
        for path in sorted((PROJECT_ROOT / "pompts_11").glob("*.md")):
            m = _PROMPT_NAME_RE.match(path.name)
            if m is None:
                continue
            num = m.group(1)
            assert num not in seen, (
                f"Дубликат номера NNN={num***REMOVED***: {seen[num***REMOVED******REMOVED*** vs {path.name***REMOVED*** "
                f"— §5.13 explicit rule (FINAL_STRUCTURE §2.1)."
            )
            seen[num***REMOVED*** = path.name


# ═══════════════════════════════════════════════════════════════
# Layer (a): consistency_check end-to-end invariant
# ═══════════════════════════════════════════════════════════════


class TestConsistencyCheckIntegration:
    """consistency_check.py::check_naming_convention должен давать zero
    prompt violations в текущем проекте. Если этот тест провалился — это
    либо (1) новый prompt добавился без NNN_TT_имя.md, либо (2)
    consistency_check.py сам сломан (regex сдвинулся nustring'ом)."""

    def test_real_project_check_naming_convention_clean(self) -> None:
        try:
            from scripts_01.consistency_check import check_naming_convention
        except ImportError:
            pytest.skip("scripts_01/consistency_check.py недоступен")
        issues = check_naming_convention(PROJECT_ROOT)
        # Filter out only "prompt" kind (we don't care about top-level dirs here).
        prompt_issues = [i for i in issues if i.get("kind") == "prompt"***REMOVED***
        assert prompt_issues == [***REMOVED***, (
            "consistency_check нашёл NNN_TT нарушения в реальном проекте:\n"
            + "\n".join(f"  - {i***REMOVED***" for i in prompt_issues)
        )


class TestNamingConventionContract:
    """[5.61.0***REMOVED*** hardening: явный contract для DEVELOPMENT. Если будущий
    разработчик добавит новый файл `prompts_11/foo.md` (забыв NNN_TT_),
    эти тесты ловят на pre-commit / CI — debt §5.13 prevented regressively."""

    def test_regex_has_expected_groups(self) -> None:
        groups = _PROMPT_NAME_RE.groups
        assert groups == 2, "regex должен захватывать ровно NNN и TT"
        sample = "047_06_e2e_platform_test.md"
        m = _PROMPT_NAME_RE.match(sample)
        assert m is not None
        assert m.group(1) == "047"
        assert m.group(2) == "06"

    def test_valid_themes_count_is_21(self) -> None:
        """Канон theme codes расширен до 01..21 (promt52-58: RFC/ARB/AG/Forge).
        Если добавляется тема — обновить _VALID_THEMES И consistency_check
        _VALID_THEME_CODES синхронно."""
        assert len(_VALID_THEMES) == 21, (
            f"_VALID_THEMES имеет {len(_VALID_THEMES)***REMOVED*** элементов — "
            f"ожидается 21 (канон 01..21). При добавлении новой "
            f"темы обновить sync с consistency_check._VALID_THEME_CODES."
        )
