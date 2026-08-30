"""Тесты CLI-обёртки dispatcher (без реального запуска freebuff)."""

import json

from projects_17.model_dispatcher import dispatcher


def test_load_config_defaults(tmp_path):
    """Нет config.yaml → разумные дефолты (таймер 1 час)."""
    cfg = dispatcher.load_config(str(tmp_path / "missing.yaml"))
    assert dispatcher.session_timeout_seconds(cfg) == 3600
    assert cfg["session"]["timeout_minutes"] == 60


def test_load_config_real_file():
    """Читаем реальный config.yaml проекта."""
    cfg = dispatcher.load_config()
    assert cfg["session"]["timeout_minutes"] == 60
    assert dispatcher.session_timeout_seconds(cfg) == 3600
    models = cfg["models"]["priority"]
    names = [m["name"] for m in models]
    assert names == ["glm-5.2", "mimo-2.5-pro", "minimax-m3", "deepseek-v4-flash"]
    assert models[-1]["free_fallback"] is True


def test_cmd_models_prints_priority(capsys):
    cfg = dispatcher.load_config()
    rc = dispatcher.cmd_models(cfg)
    out = capsys.readouterr().out
    assert "glm-5.2" in out
    assert "deepseek-v4-flash" in out
    assert "free-fallback" in out
    assert rc == 0


def test_cmd_check_runs(capsys):
    cfg = dispatcher.load_config()
    rc = dispatcher.cmd_check(cfg)
    out = capsys.readouterr().out
    assert "очередь" in out.lower() or "очередь" in out
    assert rc == 0


def test_dry_run_process_one(monkeypatch, tmp_path):
    """--dry-run возвращает первый промт без запуска freebuff."""
    from projects_17.model_dispatcher import md_queue

    monkeypatch.setattr(md_queue, "resolve_root", lambda: tmp_path)
    cfg = {
        "queue": {
            "user_dir": "pompts_11/user",
            "running_dir": "pompts_11/running",
            "done_dir": "pompts_11/done",
            "failed_dir": "pompts_11/failed",
        },
        "session": {"timeout_minutes": 60},
        "models": {"priority": [], "unavailable_markers": []},
        "freebuff": {"binary_cmd": "", "continue_resume": True},
    }
    md_queue.new_prompt_file("прочитай 081_19_model_dispatcher", title="Тест", cfg=cfg)
    r = dispatcher.process_one(cfg, dry_run=True)
    assert r["handled"] is True
    assert r["status"] == "dry-run"
    assert r["title"] == "Тест"


def test_noop_when_queue_empty(monkeypatch, tmp_path):
    from projects_17.model_dispatcher import md_queue

    monkeypatch.setattr(md_queue, "resolve_root", lambda: tmp_path)
    cfg = {"queue": {}, "session": {}, "models": {}, "freebuff": {}}
    r = dispatcher.process_one(cfg, dry_run=True)
    assert r["status"] == "noop"


def test_resume_one_continues_timeout_saved_task(monkeypatch, tmp_path):
    """resume-путь: задача из running/ + .md_state → --continue → done.

    «Сессия, ориентированная на час, не исчезает» — главный сценарий:
    таймер истёк, задача осталась в running/, --resume продолжает её.
    """
    import json
    from projects_17.model_dispatcher import md_freebuff, md_queue

    # Изолируем очередь в tmp_path
    monkeypatch.setattr(md_queue, "resolve_root", lambda: tmp_path)
    cfg = {
        "queue": {
            "user_dir": "pompts_11/user",
            "running_dir": "pompts_11/running",
            "done_dir": "pompts_11/done",
            "failed_dir": "pompts_11/failed",
        },
        "session": {"timeout_minutes": 60},
        "models": {"priority": []},
        "freebuff": {"binary_cmd": "", "continue_resume": True},
    }
    # Задача уже в running/ (таймер истёк ранее)
    running_path = md_queue.new_prompt_file(
        "задача из прошлой сессии", title="Old", cfg=cfg, queue_status="running"
    )
    # Контекст сессии сохранён
    state_dir = tmp_path / ".md_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = state_dir / f"{running_path.stem.split('_')[-1]}.json"
    state.write_text(json.dumps({"tmux_session": "md_old", "model": "glm-5.2"}), encoding="utf-8")

    # Фейковый драйвер: сессия мертва → старт с --continue; маркер появится
    class FakeTm:
        def __init__(self):
            self.started = 0
            self.commands: list = []

        def run(self, cmd):
            self.commands.append(cmd)
            self.started += 1

        def capture(self, s):
            return "Enter a coding task"

        def send(self, s, k):
            self.keys = getattr(self, "keys", []) + [k]

        def has(self, s):
            return False  # сессия мертва — нужен рестарт с --continue

    fake = FakeTm()

    def fake_build_driver(cfg, work_dir):
        d = md_freebuff.FreebuffDriver(
            work_dir=work_dir,
            timeout_s=60,
            run_cmd=fake.run,
            capture_pane=fake.capture,
            send_keys=fake.send,
            has_session=fake.has,
            startup_wait_s=1,
            poll_s=0.01,
            max_restarts=1,
            restart_delay_s=0,
        )
        return d

    monkeypatch.setattr(dispatcher, "build_driver", fake_build_driver)

    # Маркер результата появится сразу (после старта) — эмуляция завершения
    def fake_mtime(cfg):
        return None

    monkeypatch.setattr(dispatcher, "result_marker_mtime", fake_mtime)

    r = dispatcher.process_one(cfg, resume=True)
    assert r["handled"] is True
    # Сессия перезапущена с --continue
    assert fake.started >= 1
    launch_cmds = [c for c in fake.commands if c and c[0] == "tmux" and c[1] == "new-session"]
    assert launch_cmds, "tmux new-session не вызван при resume"
    assert any("--continue" in " ".join(c) for c in launch_cmds), "resume должен идти с --continue"

    # Фейк детерминирован: сессия всегда мертва после рестартов → crashed
    # (макс. 1 рестарт при max_restarts=1), маркер никогда не пишется.
    assert r["status"] == "crashed"
    # Задача не потеряна: перемещена в failed/ через set_report
    assert r.get("path")
    assert (tmp_path / "pompts_11" / "failed").exists()


def test_resume_one_reattaches_alive_session(monkeypatch, tmp_path):
    """Живая сессия (tmux ещё стоит — «вернулся через 3 часа») → re-attach без рестарта."""
    import json
    from projects_17.model_dispatcher import md_freebuff, md_queue

    monkeypatch.setattr(md_queue, "resolve_root", lambda: tmp_path)
    cfg = {
        "queue": {
            "user_dir": "pompts_11/user",
            "running_dir": "pompts_11/running",
            "done_dir": "pompts_11/done",
            "failed_dir": "pompts_11/failed",
        },
        "session": {"timeout_minutes": 60},
        "models": {"priority": []},
        "freebuff": {"binary_cmd": "", "continue_resume": True},
    }
    running_path = md_queue.new_prompt_file(
        "живая задача", title="Live", cfg=cfg, queue_status="running"
    )
    state_dir = tmp_path / ".md_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = state_dir / f"{running_path.stem.split('_')[-1]}.json"
    state.write_text(json.dumps({"tmux_session": "md_live", "model": "glm-5.2"}), encoding="utf-8")

    # Живая сессия: has() → True, рестарт НЕ должен произойти
    class LiveTm:
        def __init__(self):
            self.started = 0
            self.commands: list = []
            self.keys: list = []

        def run(self, cmd):
            self.commands.append(cmd)
            self.started += 1

        def capture(self, s):
            return "Enter a coding task"

        def send(self, s, k):
            self.keys.append(k)

        def has(self, s):
            return True

    fake = LiveTm()

    def fake_build_driver(cfg, work_dir):
        return md_freebuff.FreebuffDriver(
            work_dir=work_dir,
            timeout_s=0.2,          # быстрый таймаут мониторинга
            run_cmd=fake.run,
            capture_pane=fake.capture,
            send_keys=fake.send,
            has_session=fake.has,
            startup_wait_s=1,
            poll_s=0.01,
            max_restarts=0,
        )

    monkeypatch.setattr(dispatcher, "build_driver", fake_build_driver)
    monkeypatch.setattr(dispatcher, "result_marker_mtime", lambda cfg: None)

    r = dispatcher.process_one(cfg, resume=True)
    # Re-attach: НИКАКОГО нового tmux new-session (сессия уже жива)
    assert fake.started == 0
    # Продолжение отправлено в живую сессию
    assert fake.keys and "продолжай" in fake.keys[0]
    # Маркер не появился → timeout-saved (сессия сохранена, задача в running/)
    assert r["status"] == "timeout-saved"
    assert (tmp_path / "pompts_11" / "running" / running_path.name).exists()


def test_resume_one_noop_when_no_running(monkeypatch, tmp_path):
    """Нет отложенных задач в running/ → noop (без запуска freebuff)."""
    from projects_17.model_dispatcher import md_queue

    monkeypatch.setattr(md_queue, "resolve_root", lambda: tmp_path)
    cfg = {"queue": {}, "session": {}, "models": {}, "freebuff": {}}
    r = dispatcher.process_one(cfg, resume=True)
    assert r["status"] == "noop"
