"""tests_09/test_consistency_check_idempotency.py — TRACK-001 close (v5.189.67).

Validates consistency_check produces identical total_issues + consistent
across multiple sequential runs (idempotency invariant).

Design (v5.189.67 round-3 fix):
    consistency_check.main() calls argparse.parse_args() which reads sys.argv.
    Calling main() from pytest pollutes the assertion with pytest-collected
    argv (e.g. 'tests_09/test_consistency_check.py -q' -> argparse rejects
    with 'unrecognized arguments'). Solution: drive build_report(workspace)
    directly (no subprocess, no argparse). This is the canonical DRY
    idempotency pattern.

Background (TRACK-001, deferred in v5.189.59 AVOID-block):
    consistency_check was deferred during first-slice blockers, then counter
    and section 20 map drifted. TRACK-001 close requires that the check
    itself be idempotent -- otherwise cyclic runs introduce drift paradoxically.

Critical invariant:
    run N (>= 1): build_report(workspace) returns identical dict across N
    invocations in the same Python process.

If consistent=False, the test still passes IF total_issues is stable
(idempotency does not require consistency; it requires consistency to NOT
toggle BETWEEN runs -- only the determinism of the report is asserted here).
"""

from __future__ import annotations

import pytest

import scripts_01.consistency_check as _cc


class TestConsistencyCheckIdempotency:
    """cyclic_runs_produce_same_state: TRACK-001 close invariant."""

    def test_two_sequential_runs_produce_same_total_issues(self) -> None:
        """Run 1 vs Run 2: total_issues and consistent must both be identical.

        Asserts idempotency of the REPORT state across two consecutive
        build_report(workspace) invocations.
        """
        report1 = _cc.build_report(_cc.PROJECT_ROOT)
        report2 = _cc.build_report(_cc.PROJECT_ROOT)
        assert report1['total_issues'] == report2['total_issues'], (
            'consistency_check is not idempotent on total_issues: '
            f'run1={report1["total_issues"]} run2={report2["total_issues"]}. '
            'If TRACK-001 closure is broken, replays should NOT toggle.'
        )
        assert report1['consistent'] == report2['consistent'], (
            'consistency_check is not idempotent on consistent flag: '
            f'run1={report1["consistent"]} run2={report2["consistent"]}'
        )

    def test_three_sequential_runs_all_equal(self) -> None:
        """Run 1+2+3 all equal. Triple-check that no side effects accumulate."""
        report1 = _cc.build_report(_cc.PROJECT_ROOT)
        report2 = _cc.build_report(_cc.PROJECT_ROOT)
        report3 = _cc.build_report(_cc.PROJECT_ROOT)
        assert (
            report1['total_issues']
            == report2['total_issues']
            == report3['total_issues']
        ), (
            'consistency_check has lingering state between runs: '
            f'run1={report1["total_issues"]} run2={report2["total_issues"]} '
            f'run3={report3["total_issues"]}'
        )
        assert (
            report1['consistent']
            == report2['consistent']
            == report3['consistent']
        )

    def test_run_consistency_when_consistent_true(self) -> None:
        """If first run says consistent=True, all subsequent runs also must.

        Pre-condition: the workspace currently passes consistency_check
        (TRACK-001 closed). If this assertion fails, the close-out is
        incomplete and someone re-introduced drift.
        """
        first = _cc.build_report(_cc.PROJECT_ROOT)
        assert first['consistent'] is True, (
            f'TRACK-001 closure incomplete: total_issues={first["total_issues"]} '
            '(expected 0 baseline). If you see this in CI, refresh CHANGELOG/CQS '
            'counters or close TRACK-001 first.'
        )
        for n in range(2, 5):
            report = _cc.build_report(_cc.PROJECT_ROOT)
            assert report['consistent'] is True, (
                f'after first consistent run, run #{n} returned consistent=False '
                f'(total_issues={report["total_issues"]}) -> '
                'consistency_check is not idempotent on baseline assertion'
            )

    def test_invocations_have_no_side_effects_on_workspace(self) -> None:
        """Run consistency_check -> workspace tree (non-output files) unchanged.

        Read CHANGELOG.md BEFORE/AFTER (checker should NOT write to it).
        Time invariant: any filesystem write the checker makes is an
        unattributed side effect (= drift paradoxically).
        """
        }

        sample_path = Path('CHANGELOG.md')
        if not sample_path.exists():
            pytest.skip('CHANGELOG.md not present')
        before_mtime = sample_path.stat().st_mtime
        before_size = sample_path.stat().st_size

        for _ in range(3):
            _cc.build_report(_cc.PROJECT_ROOT)

        after_mtime = sample_path.stat().st_mtime
        after_size = sample_path.stat().st_size

        assert before_mtime == after_mtime, (
            f'CHANGELOG.md mtime changed ({before_mtime} -> {after_mtime}): '
            'consistency_check wrote to it (unexpected side effect)'
        )
        assert before_size == after_size, (
            f'CHANGELOG.md size changed ({before_size} -> {after_size}): '
            'consistency_check mutated it (side effect)'
        )
