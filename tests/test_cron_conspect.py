"""Tests for scripts/cron_conspect.sh.

Verifies that the cron script never invokes auto_conspect in demo mode.
"""
***REMOVED***


class TestCronConspect:
    """Тесты cron_conspect.sh."""

    @property
    def script_path(self) -> Path:
        project_root = Path(__file__).resolve().parent.parent
        return project_root / "scripts" / "cron_conspect.sh"

    def _read_script(self) -> str:
        return self.script_path.read_text(encoding="utf-8")

    def test_script_exists(self):
        assert self.script_path.exists(), "cron_conspect.sh must exist"

    def test_script_has_shebang(self):
        text = self._read_script()
        assert text.startswith("#!/"), "cron_conspect.sh must have a shebang line"

    def test_script_does_not_invoke_demo_mode(self):
        """Скрипт не должен содержать --demo в вызове auto_conspect."""
        text = self._read_script()
        assert "--demo" not in text, "cron_conspect.sh must not pass --demo to auto_conspect"

    def test_script_invokes_auto_conspect(self):
        """Скрипт должен вызывать python scripts/auto_conspect.py без --demo."""
        text = self._read_script()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("python scripts/auto_conspect.py"):
                assert not stripped.startswith("#"), (
                    "auto_conspect invocation line must not be commented out"
                )
                assert "--demo" not in stripped, (
                    f"auto_conspect invocation must not include --demo: {stripped!r***REMOVED***"
                )
                return
        raise AssertionError("cron_conspect.sh should invoke python scripts/auto_conspect.py")
