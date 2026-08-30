"""Тесты выбора модели по убыванию мощности (md_models)."""

from projects_17.model_dispatcher import md_models

PRIORITY = [
    {"name": "glm-5.2", "keywords": ["glm", "5.2"]},
    {"name": "mimo-2.5-pro", "keywords": ["mimo", "2.5"]},
    {"name": "minimax-m3", "keywords": ["minimax", "m3"]},
    {"name": "deepseek-v4-flash", "keywords": ["deepseek"], "free_fallback": True},
]
MARKERS = ["out of", "sold out", "exhausted", "no sessions", "0 available"]


def test_parse_screen_glm_first_available():
    """GLM доступна → выбираем её (позиция 0 — рекомендованная)."""
    screen = """
    ✨ Start coding for free
    > GLM 5.2 · premium
      MiMo 2.5 Pro
      MiniMax M3
      DeepSeek V4 Flash · free unlimited
    """
    entries = md_models.parse_screen(screen, PRIORITY, MARKERS)
    assert entries, "нет распознанных моделей"
    assert entries[0].name == "glm-5.2"
    assert entries[0].position == 0
    assert entries[0].available

    sel = md_models.pick_model(entries, PRIORITY)
    assert sel.name == "glm-5.2"
    assert sel.position == 0
    assert sel.source == "detected"


def test_pick_model_falls_to_next_when_glm_unavailable():
    """GLM израсходована → берём следующую доступную (MiMo)."""
    screen = """
      Start coding for free
      GLM 5.2 · premium · out of sessions
    > MiMo 2.5 Pro
      MiniMax M3
      DeepSeek V4 Flash · free
    """
    entries = md_models.parse_screen(screen, PRIORITY, MARKERS)
    by_name = {e.name: e for e in entries}
    assert not by_name["glm-5.2"].available, "GLM должна быть недоступна"

    sel = md_models.pick_model(entries, PRIORITY)
    assert sel.name == "mimo-2.5-pro"
    assert sel.position == by_name["mimo-2.5-pro"].position
    assert sel.source == "detected"


def test_pick_model_fallback_to_free():
    """Только DeepSeek видна на экране → берём её (поз.0, детект или fallback)."""
    screen = """
      Start coding for free
      DeepSeek V4 Flash · free unlimited
    """
    entries = md_models.parse_screen(screen, PRIORITY, MARKERS)
    sel = md_models.pick_model(entries, PRIORITY)
    assert sel.name == "deepseek-v4-flash"
    assert sel.position == 0
    assert sel.source in ("detected", "fallback")


def test_pick_model_empty_screen_fallback():
    """Экран пуст/не распознан → fallback на free-модель без падения."""
    sel = md_models.pick_model([], PRIORITY)
    assert sel.source == "fallback"
    assert sel.name == "deepseek-v4-flash"


def test_pick_model_no_priority_no_crash():
    """Пустой конфиг → 'auto' без падения."""
    sel = md_models.pick_model([], [])
    assert sel.name == "auto"
    assert sel.position == 0


def test_parse_screen_case_insensitive():
    """Детект регистронезависим."""
    screen = "GLM 5.2 available\n  mimo 2.5 pro\n"
    entries = md_models.parse_screen(screen, PRIORITY, MARKERS)
    names = {e.name for e in entries}
    assert "glm-5.2" in names
    assert "mimo-2.5-pro" in names


def test_unavailable_markers_detect():
    """Маркеры недоступности (sold out) → available=False."""
    screen = "GLM 5.2 · sold out\n  MiMo 2.5 Pro\n"
    entries = md_models.parse_screen(screen, PRIORITY, MARKERS)
    by_name = {e.name: e for e in entries}
    assert not by_name["glm-5.2"].available
    assert by_name["mimo-2.5-pro"].available
