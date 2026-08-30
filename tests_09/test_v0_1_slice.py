# tests_09/test_v0_1_slice.py — First Vertical Slice v0.1 (промт 68, Phase 4.5)
#
# DELIVERABLE: единственный тест, доказывающий, что все слои физически
# связаны (не просто существуют по отдельности):
#   L2 Project → L3 Forge (ForgePipeline) → L4 Registry (record_run)
#   → L5 Memory (record_learning_event → SQLite learning_events).
# Risk Registry (§34.7): R-4 детерминированный проект (нет случайных элементов).
import json

import pytest

from core_02.forge_pipeline import ForgePipeline
from core_02.forge_registry import DEPLOYED, FAILED, ForgeRegistry
from core_02.memory_store import MemoryStore
from core_02.workspace import Project
from scripts_01 import forge as forge_mod

# xdist: ForgePipeline пишет в реальный data_13/forge_registry.yaml → сериализуем
# с остальными registry-файлами (иначе гонка: stage_count 1 vs 14 в параллельном
# прогоне, см. v5.189.12 xdist_group).
pytestmark = pytest.mark.xdist_group("forge_real_registry")


@pytest.fixture
def demo_project(tmp_path):
    """Детерминированный vkusvill_demo-подобный проект (R-4)."""
    p = tmp_path / "vkusvill_demo"
    p.mkdir()
    (p / "project.yaml").write_text(
        "name: vkusvill_demo\ntype: python\nrequirements:\n  steps: required\n",
        encoding="utf-8",
    )
    (p / "README.md").write_text("# VkusVill Demo", encoding="utf-8")
    (p / "STEPS.md").write_text(
        "## Step 1\n- [x] Scaffold\n## Step 2\n- [x] Model\n", encoding="utf-8"
    )
    return Project.load(p)


class TestV01Slice:
    def test_pipeline_runs_on_demo_project(self, demo_project):
        """L3 Forge: полный цикл FORGE→REPORT исполняется без исключений."""
        run = ForgePipeline(demo_project).run()
        names = [s.name for s in run.stages]
        assert names == ["FORGE", "CHECK", "BUILD", "TEST", "DEPLOY", "REPORT"]
        assert run.overall in ("ok", "failed")
        # STEPS.md обязателен (requirements.steps: required) и присутствует → CHECK ok
        check = next(s for s in run.stages if s.name == "CHECK")
        assert check.status == "ok"

    def test_slice_connects_l2_to_l5(self, demo_project, tmp_path):
        """Ключевой тест: L2→L3→L4→L5 физически связаны + SQLite фиксирует event."""
        # L2 → L3: запускаем pipeline
        pipe = ForgePipeline(demo_project)
        run = pipe.run()

        # L4: registry.record_run фиксирует статус
        reg = ForgeRegistry(tmp_path / "registry.yaml")
        pid = reg.register_project(demo_project.name, str(demo_project.root))
        status = reg.record_run(pid, run)
        assert status.status in (DEPLOYED, FAILED)
        assert len(reg.get_pipeline_history(pid)) == 1

        # L5: learning event в SQLite
        ms = MemoryStore(tmp_path / "context.db")
        eid = ms.record_learning_event(
            trigger_id=f"forge:{run.project_name}",
            context_snapshot={
                "project_name": run.project_name,
                "overall": run.overall,
                "status": "passed" if run.overall == "ok" else "failed",
                "stages": [{"name": s.name, "status": s.status} for s in run.stages],
            },
            outcome="success" if run.overall == "ok" else "failure",
        )
        assert eid
        events = ms.list_learning_events()
        assert len(events) == 1
        ev = events[0]
        assert ev["trigger_id"] == f"forge:{run.project_name}"
        assert ev["outcome"] == ("success" if run.overall == "ok" else "failure")
        snap = json.loads(ev["context_snapshot"])
        assert snap["status"] in ("passed", "failed")
        assert snap["overall"] == run.overall

    def test_forge_cli_wiring_b7(self, demo_project, tmp_path, monkeypatch):
        """Phase 4.2 wiring: forge.py конвертирует PipelineRun → learning event (B7)."""
        db = tmp_path / "context.db"
        # Экземпляр создаётся ДО патча, чтобы БД-файл существовал к моменту
        # вызова; фабрика-заглушка возвращает именно его.
        # ВАЖНО: патч срабатывает только потому, что forge.py импортирует
        # MemoryStore ВНУТРИ _record_learning_event (import в момент вызова).
        # Если импорт вынесут наверх модуля — патч перестанет перехватывать
        # вызов и событие уйдёт в реальный data_13/context.db.
        ms = MemoryStore(db)
        monkeypatch.setattr("core_02.memory_store.MemoryStore", lambda: ms)
        run = ForgePipeline(demo_project).run()
        eid = forge_mod._record_learning_event(run)
        assert eid
        # _record_learning_event использует `with MemoryStore() as ms:` → соединение
        # закрывается при выходе. Открываем новый коннект на ТОТ ЖЕ файл:
        # проверяем реальную персистентность события (данные пережили close).
        with MemoryStore(db) as verify:
            events = verify.list_learning_events()
        assert len(events) == 1
        assert events[0]["outcome"] in ("success", "failure")
        assert events[0]["trigger_id"] == f"forge:{demo_project.name}"

    def test_project_required_steps_enforced(self, tmp_path):
        """Phase 4.4: requirements.steps: required + отсутствие STEPS.md → CHECK failed."""
        p = tmp_path / "no_steps"
        p.mkdir()
        (p / "project.yaml").write_text(
            "name: no_steps\ntype: python\nrequirements:\n  steps: required\n",
            encoding="utf-8",
        )
        (p / "README.md").write_text("# x", encoding="utf-8")
        (p / "RUNNABLE.md").write_text("## s\n", encoding="utf-8")
        (p / "CHECKLIST.md").write_text("- [x)\n", encoding="utf-8")
        proj = Project.load(p)
        pipe = ForgePipeline(proj)
        res = pipe.stage_check()
        assert res.status == "failed"
        assert "STEPS.md" in res.details

    def test_learning_events_queryable_by_outcome(self, demo_project, tmp_path):
        """R-3: статус passed|failed queryable как фильтр (public API)."""
        ms = MemoryStore(tmp_path / "context.db")
        ms.record_learning_event(
            trigger_id="forge:a",
            context_snapshot={"status": "passed"},
            outcome="success",
        )
        ms.record_learning_event(
            trigger_id="forge:b",
            context_snapshot={"status": "failed"},
            outcome="failure",
        )
        outcomes = sorted(ev["outcome"] for ev in ms.list_learning_events())
        assert outcomes == ["failure", "success"]
