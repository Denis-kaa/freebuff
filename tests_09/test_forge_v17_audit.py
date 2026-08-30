"""Phase 5 Forward-action #1 audit test — verifies 18-boundary compliance table.

Per WORKSPACE_OS_ARCHITECTURE_RESEARCH_V1.md §37.7 + §37.9: 18 boundaries.

Updated 2026-08-10 (промт 68, R-123/R-124/R-127 closure for v0.1):
B1, B2, B10 PARTIAL → ENFORCED → теперь 13 ENFORCED + 4 PARTIAL + 1 DOCTRINE
(было 10 ENFORCED + 7 PARTIAL). Партнерами остались B7/B9/B12/B16.
"""
import unittest
import importlib.util
import os


def load_boundaries_v17():
    """Load boundaries_v17 module from core_02 dir (dynamic import)."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "core_02", "boundaries_v17.py",
    )
    spec = importlib.util.spec_from_file_location("boundaries_v17", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestBoundariesV17Compliance(unittest.TestCase):
    """§37.7 compliance table verification."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_boundaries_v17()
        cls.b = cls.mod.BOUNDARIES_V17

    def test_18_boundaries_registered(self):
        """Per §37.7: 18 boundaries total."""
        self.assertEqual(len(self.b), 18)

    def test_13_enforced_4_partial_1_doctrine_states(self):
        """Per §37.7 после R-123/R-124/R-127 closure (2026-08-10):
        13 ENFORCED + 4 PARTIAL (B7/B9/B12/B16) + 1 DOCTRINE (B15)."""
        summary = self.mod.compliance_summary()
        self.assertEqual(summary.get("ENFORCED", 0), 13)
        self.assertEqual(summary.get("PARTIAL", 0), 4)
        self.assertEqual(summary.get("DOCTRINE", 0), 1)

    def test_b1_b2_b10_enforced_after_v01_closure(self):
        """R-123 (B1), R-124 (B2), R-127 (B10) — закрыты для v0.1 (промт 68)."""
        self.assertEqual(self.b["B1"].state.value, "ENFORCED")
        self.assertEqual(self.b["B2"].state.value, "ENFORCED")
        self.assertEqual(self.b["B10"].state.value, "ENFORCED")

    def test_b7_subproject_namespace(self):
        """Per §37.3.2: B7 namespace = forge:project_id:sub_project_id."""
        b7 = self.b["B7"]
        self.assertEqual(b7.namespace, "forge:project_id:sub_project_id")
        self.assertEqual(b7.state.value, "PARTIAL")

    def test_b16_exec_namespace(self):
        """Per §37.2.B: B16 namespace = exec:project_id:stage_id."""
        b16 = self.b["B16"]
        self.assertEqual(b16.namespace, "exec:project_id:stage_id")
        self.assertEqual(b16.state.value, "PARTIAL")

    def test_b_gui_namespace(self):
        """Per §37.4: B-GUI namespace = gui:ui_id (UI/headless separation)."""
        b_gui = self.b["B-GUI"]
        self.assertEqual(b_gui.namespace, "gui:ui_id")
        self.assertEqual(b_gui.state.value, "ENFORCED")

    def test_b15_borderline_doctrine(self):
        """Per §37.2.A: B15 = Collaboration = DOCTRINE (no enforcement yet)."""
        b15 = self.b["B15"]
        self.assertEqual(b15.state.value, "DOCTRINE")

    def test_b17_borderline_enforced(self):
        """Per §37.2.C: B17 = Governance = ENFORCED (DIS-v0.2 implemented per Phase 5 #3)."""
        b17 = self.b["B17"]
        self.assertEqual(b17.state.value, "ENFORCED")


if __name__ == "__main__":
    unittest.main()
