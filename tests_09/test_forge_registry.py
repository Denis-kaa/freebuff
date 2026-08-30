# tests_09/test_forge_registry.py — Forge Registry (Этап 4.3)
}

import pytest

from core_02.forge_registry import (
    ForgeRegistry,
    ForgeStatus,
    UNFORGED,
    DEPLOYED,
    FAILED,
    CHECKING,
)


@pytest.fixture
def registry(tmp_path):
    return ForgeRegistry(tmp_path / "forge_registry.yaml")


class TestRegistry:
    def test_register_and_get(self, registry):
        pid = registry.register_project("web_app", "/tmp/web_app")
        st = registry.get_project_status(pid)
        assert st is not None
        assert st.status == UNFORGED
        assert st.name == "web_app"
        assert registry.count() == 1

    def test_register_slug(self, registry):
        pid = registry.register_project("My Cool App", "/tmp/mca")
        assert pid == "my-cool-app"

    def test_get_by_root(self, registry):
        registry.register_project("app1", "/tmp/root1")
        st = registry.get_project_status_by_root("/tmp/root1")
        assert st is not None and st.name == "app1"
        assert registry.get_project_status_by_root("/nope") is None

    def test_list_by_status(self, registry):
        registry.register_project("a", "/tmp/a")
        registry.register_project("b", "/tmp/b")
        statuses = registry.list_projects_by_status()
        assert len(statuses) == 2
        assert registry.list_projects_by_status(UNFORGED) == statuses
        assert registry.list_projects_by_status(DEPLOYED) == []

    def test_record_run_updates_status(self, registry):
        pid = registry.register_project("web_app", "/tmp/web_app")
        run = {"project_name": "web_app", "overall": "ok", "stages": [{"name": "FORGE", "status": "ok"}]}
        st = registry.record_run(pid, run)
        assert st.status == DEPLOYED
        assert st.last_run_at is not None
        assert len(registry.get_pipeline_history(pid)) == 1

    def test_record_run_failed(self, registry):
        pid = registry.register_project("broken", "/tmp/broken")
        registry.record_run(pid, {"overall": "failed"})
        st = registry.get_project_status(pid)
        assert st.status == FAILED

    def test_record_run_degraded_keeps_deployed(self, registry):
        """v5.189.7: degraded (exit 0) НЕ даунгрейдит DEPLOYED → сертификация держится."""
        pid = registry.register_project("cert", "/tmp/cert")
        registry.record_run(pid, {"overall": "ok"})
        st = registry.record_run(pid, {"overall": "degraded"})
        assert st.status == DEPLOYED
        # last_pipeline при этом сохраняется (нужно для --resume).
        assert st.last_pipeline.get("overall") == "degraded"
        assert len(registry.get_pipeline_history(pid)) == 2
        assert registry.validate_schema() == []

    def test_record_run_degraded_keeps_failed(self, registry):
        """v5.189.7: degraded не сертифицирует и не даунгрейдит FAILED."""
        pid = registry.register_project("broken", "/tmp/broken")
        registry.record_run(pid, {"overall": "failed"})
        st = registry.record_run(pid, {"overall": "degraded"})
        assert st.status == FAILED

    def test_record_run_degraded_on_unforged_preserves_unforged(self, registry):
        """v5.189.10 (R-1 closure): degraded (exit 0) на UNFORGED НЕ маппится в
        FAILED — статус остаётся UNFORGED, персист (last_run_at/last_pipeline/
        history) пропускается: нет ok/run_ok для --resume, а UNFORGED +
        last_pipeline = B10/R-127 violation. Схема остаётся валидной."""
        pid = registry.register_project("fresh", "/tmp/fresh")
        st = registry.record_run(pid, {"overall": "degraded"})
        assert st.status == UNFORGED
        assert st.last_run_at is None
        assert st.last_pipeline == {}
        assert registry.get_pipeline_history(pid) == []
        assert registry.validate_schema() == []

    def test_record_run_degraded_on_transient_preserves_status(self, registry):
        """v5.189.10 (R-1 closure): degraded на транзиентном статусе (CHECKING)
        сохраняет его и персистит last_pipeline (нет last_run_at-ограничения
        для этих статусов → схема валидна)."""
        pid = registry.register_project("mid", "/tmp/mid")
        registry._data[pid]["status"] = CHECKING
        registry._save()
        st = registry.record_run(pid, {"overall": "degraded"})
        assert st.status == CHECKING
        assert st.last_pipeline.get("overall") == "degraded"
        assert registry.validate_schema() == []

    def test_record_run_ok_after_degraded_upgrades_to_deployed(self, registry):
        """v5.189.7: последующий ok-прогон корректно апгрейдит degraded-состояние."""
        pid = registry.register_project("upgrade", "/tmp/upgrade")
        registry.record_run(pid, {"overall": "degraded"})
        st = registry.record_run(pid, {"overall": "ok"})
        assert st.status == DEPLOYED
        assert registry.validate_schema() == []

    def test_record_run_unknown_project(self, registry):
        with pytest.raises(KeyError):
            registry.record_run("ghost", {"overall": "ok"})

    def test_record_run_caps_history(self, registry):
        pid = registry.register_project("app", "/tmp/app")
        for i in range(25):
            registry.record_run(pid, {"overall": "ok", "run": i})
        history = registry.get_pipeline_history(pid)
        assert len(history) == 20

    def test_persistence_roundtrip(self, tmp_path):
        path = tmp_path / "forge.yaml"
        r1 = ForgeRegistry(path)
        r1.register_project("persist", "/tmp/persist")
        r1.record_run("persist", {"overall": "ok"})
        r2 = ForgeRegistry(path)  # перечитываем с диска
        st = r2.get_project_status("persist")
        assert st is not None
        assert st.status == DEPLOYED

    def test_unregister(self, registry):
        pid = registry.register_project("temp", "/tmp/temp")
        assert registry.unregister(pid) is True
        assert registry.get_project_status(pid) is None
        assert registry.unregister(pid) is False

    def test_forge_status_to_dict(self):
        st = ForgeStatus(project_id="p1", name="n", root="/r", status=CHECKING)
        d = st.to_dict()
        assert d["project_id"] == "p1"
        assert d["status"] == CHECKING


class TestStateDriftGuard:
    """v5.189.71: ephemeral-root mock-записи НЕ утекают в реальный реестр.

    Hermetic: перехватываем Path.write_text через monkeypatch, чтобы не
    мутировать реальный data_13/forge_registry.yaml.
    """

    def test_is_ephemeral_path_detects_tmp_and_tempdir(self) -> None:
        assert ForgeRegistry._is_ephemeral_path("/tmp/x") is True
        assert ForgeRegistry._is_ephemeral_path("/tmp/freebuff-bun-tmp/y") is True
        assert ForgeRegistry._is_ephemeral_path("/mnt/sdcard/PROJECTS/x") is False
        assert ForgeRegistry._is_ephemeral_path("projects_17/x") is False
        assert ForgeRegistry._is_ephemeral_path("/nonexistent") is False

    def test_ephemeral_root_skipped_when_registry_is_real(self, tmp_path, monkeypatch) -> None:
        """Эфемерный root + НЕ-эфемерный реестр → запись фильтруется из _save()."""
        reg = ForgeRegistry(tmp_path / "real_like.yaml")
        # Симулируем реальный реестр: путь НЕ под /tmp.
        monkeypatch.setattr(reg, "path", Path("/mnt/sdcard/PROJECTS/workstation/freebuff/data_13/forge_registry.yaml"))
        captured: dict = {}
        monkeypatch.setattr(Path, "write_text", lambda self, data, encoding=None: captured.update(data=data))
        reg.register_project("mock-leak", "/tmp/mock_root")
        # Запись осталась in-memory, но НЕ попала в записанный payload.
        assert "mock-leak" in reg._data
        assert "mock-leak" not in str(captured.get("data", ""))

    def test_ephemeral_root_persists_when_registry_also_ephemeral(self, tmp_path, monkeypatch) -> None:
        """Эфемерный root + эфемерный реестр (unit-тест сценарий) → персист обязателен."""
        reg = ForgeRegistry(tmp_path / "tmp_registry.yaml")
        captured: dict = {}
        monkeypatch.setattr(Path, "write_text", lambda self, data, encoding=None: captured.update(data=data))
        reg.register_project("unit-test-proj", "/tmp/unit_root")
        assert "unit-test-proj" in str(captured.get("data", ""))

    def test_real_root_persists_even_when_registry_is_real(self, tmp_path, monkeypatch) -> None:
        """Реальный root + реальный реестр → запись персистится (не ложно-фильтруется)."""
        reg = ForgeRegistry(tmp_path / "real_like.yaml")
        monkeypatch.setattr(reg, "path", Path("/mnt/sdcard/PROJECTS/workstation/freebuff/data_13/forge_registry.yaml"))
        captured: dict = {}
        monkeypatch.setattr(Path, "write_text", lambda self, data, encoding=None: captured.update(data=data))
        reg.register_project("real-proj", "projects_17/real_proj")
        assert "real-proj" in str(captured.get("data", ""))
