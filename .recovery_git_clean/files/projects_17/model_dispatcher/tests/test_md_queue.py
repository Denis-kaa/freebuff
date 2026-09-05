"""Тесты файловой очереди промтов (md_queue)."""

***REMOVED***

from projects_17.model_dispatcher import md_queue


def _cfg(tmp_path: Path) -> dict:
    """Конфиг с корнем в tmp_path (изоляция от реальной очереди)."""
    return {
        "queue": {
            "user_dir": "pompts_11/user",
            "running_dir": "pompts_11/running",
            "done_dir": "pompts_11/done",
            "failed_dir": "pompts_11/failed",
        ***REMOVED***
    ***REMOVED***


def test_new_prompt_file_lands_in_user(monkeypatch, tmp_path):
    monkeypatch.setattr(md_queue, "resolve_root", lambda: tmp_path)
    cfg = _cfg(tmp_path)
    path = md_queue.new_prompt_file("сделай X", title="Тест", cfg=cfg)
    assert path.exists()
    assert path.parent.name == "user"

    meta = md_queue.parse_prompt(path)
    assert meta is not None
    assert meta.title == "Тест"
    assert meta.body == "сделай X"
    assert meta.model == "auto"


def test_scan_and_move_status(monkeypatch, tmp_path):
    monkeypatch.setattr(md_queue, "resolve_root", lambda: tmp_path)
    cfg = _cfg(tmp_path)
    md_queue.new_prompt_file("задача 1", title="T1", cfg=cfg)
    md_queue.new_prompt_file("задача 2", title="T2", cfg=cfg)

    pending = md_queue.scan("user", cfg)
    assert len(pending) == 2

    moved = md_queue.move_to_status(pending[0***REMOVED***.path, "running", cfg)
    assert moved.parent.name == "running"
    assert len(md_queue.scan("user", cfg)) == 1
    assert len(md_queue.scan("running", cfg)) == 1


def test_set_report_moves_and_appends(monkeypatch, tmp_path):
    monkeypatch.setattr(md_queue, "resolve_root", lambda: tmp_path)
    cfg = _cfg(tmp_path)
    path = md_queue.new_prompt_file("сделай Y", title="TY", cfg=cfg)
    final = md_queue.set_report(path, "done", "✅ Выполнено", cfg)
    assert final.parent.name == "done"
    text = final.read_text(encoding="utf-8")
    assert "## Отчёт" in text
    assert "✅ Выполнено" in text
    assert "# TASK: TY" in text


def test_queue_counts(monkeypatch, tmp_path):
    monkeypatch.setattr(md_queue, "resolve_root", lambda: tmp_path)
    cfg = _cfg(tmp_path)
    md_queue.new_prompt_file("a", title="A", cfg=cfg)
    md_queue.new_prompt_file("b", title="B", cfg=cfg)
    counts = md_queue.queue_counts(cfg)
    assert counts["user"***REMOVED*** == 2
    assert counts["running"***REMOVED*** == 0


def test_parse_invalid_file_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(md_queue, "resolve_root", lambda: tmp_path)
    cfg = _cfg(tmp_path)
    bad = tmp_path / "pompts_11" / "user" / "no_header.md"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("просто текст без заголовка", encoding="utf-8")
    assert md_queue.parse_prompt(bad) is None
