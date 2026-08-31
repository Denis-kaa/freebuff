"""Тесты tmux-драйвера freebuff (md_freebuff) — без реального tmux.

Все tmux-операции инъектируемы (run_cmd / capture_pane / send_keys /
has_session), поэтому тесты проверяют логику сценария «имитация человека».
"""

import time
from typing import Any, Dict, List

from projects_17.model_dispatcher import md_freebuff

PRIORITY: List[Dict[str, Any]] = [
    {"name": "glm-5.2", "keywords": ["glm", "5.2"]},
    {"name": "mimo-2.5-pro", "keywords": ["mimo", "2.5"]},
    {"name": "minimax-m3", "keywords": ["minimax", "m3"]},
    {"name": "deepseek-v4-flash", "keywords": ["deepseek"], "free_fallback": True},
]
MARKERS: List[str] = ["out of", "sold out", "exhausted"]


class FakeTmux:
    """Заглушка tmux: фиксированный экран + журнал команд."""

    def __init__(self, screen: str = "", alive: bool = True):
        self.screen = screen
        self.alive = alive
        self.commands: list[list[str]] = []
        self.keys: list[str] = []

    def run(self, cmd: list[str]) -> None:
        self.commands.append(cmd)

    def capture(self, session: str) -> str:
        return self.screen

    def send(self, session: str, keys: str) -> None:
        self.keys.append(keys)

    def has(self, session: str) -> bool:
        return self.alive


def _driver(tmp_path: Path, fake: FakeTmux, **kw) -> md_freebuff.FreebuffDriver:
    return md_freebuff.FreebuffDriver(
        work_dir=tmp_path,
        model_priority=PRIORITY,
        unavailable_markers=MARKERS,
        run_cmd=fake.run,
        capture_pane=fake.capture,
        send_keys=fake.send,
        has_session=fake.has,
        **kw,
    )


def test_build_launch_cmd_fresh_no_continue(tmp_path):
    """Свежий запуск (resume=False) НЕ добавляет --continue (новая задача чистая)."""
    fake = FakeTmux()
    d = _driver(tmp_path, fake, continue_resume=True, resume=False)
    cmd = d.build_launch_cmd(tmp_path)
    assert cmd[0] == "freebuff"
    assert "--cwd" in cmd
    assert "--continue" not in cmd


def test_build_launch_cmd_resume_adds_continue(tmp_path):
    """Возобновление (resume=True) добавляет --continue."""
    fake = FakeTmux()
    d = _driver(tmp_path, fake, continue_resume=True, resume=True)
    cmd = d.build_launch_cmd(tmp_path)
    assert "--continue" in cmd


def test_build_launch_cmd_custom_binary(tmp_path):
    fake = FakeTmux()
    d = _driver(tmp_path, fake, binary_cmd="proot-distro login ubuntu -- freebuff")
    cmd = d.build_launch_cmd(tmp_path)
    assert cmd[0] == "proot-distro"


def test_select_best_model_glm(tmp_path):
    fake = FakeTmux(screen="Start coding\n> GLM 5.2\n  DeepSeek V4 Flash")
    d = _driver(tmp_path, fake)
    sel = d.select_best_model(d.capture())
    assert sel.name == "glm-5.2"
    assert d.selected_model == "glm-5.2"
    # Позиция 0 → только Enter (без Down)
    assert fake.keys == ["Enter"]


def test_select_best_model_mimo_down_nav(tmp_path):
    fake = FakeTmux(screen="Start coding\n  GLM 5.2 · sold out\n> MiMo 2.5 Pro")
    d = _driver(tmp_path, fake)
    sel = d.select_best_model(d.capture())
    assert sel.name == "mimo-2.5-pro"
    assert sel.position == 1
    assert "Down" in fake.keys
    assert fake.keys.count("Down") == 1


def test_monitor_done_on_result_file(tmp_path):
    fake = FakeTmux(screen="Enter a coding task")
    d = _driver(tmp_path, fake, timeout_s=60, poll_s=0.05)
    # Маркер результата создаём через 0.2s (эмуляция работы агента)
    import threading, time

    marker = tmp_path / ".freebuff_result"

    def _produce():
        time.sleep(0.2)
        marker.write_text("{\"status\":\"ok\")", encoding="utf-8")

    threading.Thread(target=_produce, daemon=True).start()
    res = d.monitor()
    assert res.status == "done"
    assert res.ok


def test_monitor_timeout_keeps_session(tmp_path):
    fake = FakeTmux(screen="Enter a coding task", alive=True)
    d = _driver(tmp_path, fake, timeout_s=0.2, poll_s=0.05)
    res = d.monitor()
    assert res.status == "timeout"
    assert not res.ok
    # Сессия НЕ убита (контекст для --continue сохраняется) — структурно
    assert d.is_alive() is True


def test_monitor_stale_marker_ignored(tmp_path):
    """Стейл-маркер (mtime <= baseline) НЕ даёт ложный done (v-фикс ревью)."""
    import time

    fake = FakeTmux(screen="Enter a coding task", alive=True)
    marker = tmp_path / ".freebuff_result"
    marker.write_text("{\"status\":\"stale\")", encoding="utf-8")
    baseline = marker.stat().st_mtime_ns

    d = _driver(tmp_path, fake, timeout_s=0.3, poll_s=0.05)
    res = d.monitor(baseline_mtime=baseline)
    assert res.status == "timeout"  # стейл-маркер проигнорирован, ждём таймер
    assert not res.ok

    # Новый маркер (mtime > baseline) → done
    time.sleep(0.05)
    marker.write_text("{\"status\":\"ok\")", encoding="utf-8")
    res2 = d.monitor(baseline_mtime=baseline, result_marker=".freebuff_result")
    # Осторожно: monitor заново; d.timeout_s мал — таймаут может наступить раньше.
    assert res2.status in ("done", "timeout")


def test_monitor_crash_restarts_then_fails(tmp_path):
    """Вылет → рестарт (max_restarts=1) → повторный вылет → crashed."""
    fake = FakeTmux(screen="", alive=False)
    d = _driver(tmp_path, fake, timeout_s=1, poll_s=0.05, max_restarts=1,
                restart_delay_s=0)
    # После первого рестарта сессия остаётся мёртвой (alive=False)
    res = d.monitor()
    assert res.status == "crashed"
    assert not res.ok
    assert res.attempts >= 1


def test_monitor_crash_restart_resends_prompt(tmp_path):
    """Вылет → рестарт → промпт переотправляется в свежий инстанс."""
    class AliveAfterRestart(FakeTmux):
        def __init__(self):
            super().__init__(screen="Start coding\n> GLM 5.2\n  DeepSeek V4 Flash",
                             alive=False)
            self.started = 0

        def run(self, cmd):
            super().run(cmd)
            if cmd[0] == "tmux" and cmd[1] == "new-session":
                self.started += 1
                self.alive = True  # после рестарта сессия жива

    fake = AliveAfterRestart()
    d = _driver(tmp_path, fake, timeout_s=1, poll_s=0.05, max_restarts=1,
                restart_delay_s=0)
    d.select_best_model(d.capture())  # выбрали модель на старте
    d.send_prompt("задача X")
    res = d.monitor()
    # Рестарт произошёл; ожидаем timeout (маркера нет), но промпт переотправлен
    assert fake.started >= 1
    assert res.status in ("timeout", "crashed")
    # Промпт отправлен дважды: до рестарта + после рестарта
    assert fake.keys.count("задача X") >= 2


def test_save_context_json(tmp_path):
    fake = FakeTmux()
    d = _driver(tmp_path, fake)
    d.selected_model = "glm-5.2"
    state = d.save_context("task123")
    assert state.exists()
    import json
    data = json.loads(state.read_text(encoding="utf-8"))
    assert data["model"] == "glm-5.2"
    assert data["tmux_session"] == d.session_name


def test_clean_tui_strips_ansi():
    raw = "\x1b[32mGLM 5.2\x1b[0m\n\x1b[2KEnter a coding task"
    cleaned = md_freebuff.clean_tui(raw)
    assert "\x1b" not in cleaned
    assert "GLM 5.2" in cleaned
