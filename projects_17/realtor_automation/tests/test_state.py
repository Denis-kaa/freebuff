"""Tests for state manager."""

}

from realtor_automation.state import StateManager


def test_state_manager_creates_default_state(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)
    assert manager.state.version == "0.1.0"
    assert manager.state.phase == "init"


def test_state_manager_persists_state(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)
    manager.set_phase("setup")
    manager.add_installed("ollama")

    new_manager = StateManager(state_file)
    assert new_manager.state.phase == "setup"
    assert "ollama" in new_manager.state.installed


def test_state_manager_recovers_from_corrupted_state(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text("not json", encoding="utf-8")
    manager = StateManager(state_file)
    assert manager.state.phase == "init"
    assert (tmp_path / "state.json.bak").exists()
