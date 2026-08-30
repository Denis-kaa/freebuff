# tests_09/test_missing_registry.py — Missing Registry (register-first принцип)
import json

import pytest

from core_02.missing_registry import (
    MissingItem,
    MissingRegistry,
    REGISTERED,
    DESIGN_READY,
    PROMPT_WRITTEN,
    IMPLEMENTED,
    KINDS,
    seed_defaults,
    main,
)


@pytest.fixture
def registry(tmp_path):
    return MissingRegistry(tmp_path / "missing_registry.yaml")


# ─── register-first: register → prompt → implemented ───────────────────────


def test_register_and_get(registry):
    item_id = registry.register_missing(
        "research_web", kind="tool", factory="research",
        description="Web Research",
    )
    item = registry.get(item_id)
    assert item is not None
    assert item.status == REGISTERED
    assert item.factory == "research"
    assert registry.count() == 1


def test_register_empty_id_rejected(registry):
    with pytest.raises(ValueError):
        registry.register_missing("", kind="tool")


def test_register_bad_kind_rejected(registry):
    with pytest.raises(ValueError):
        registry.register_missing("x", kind="no-such-kind")


def test_register_bad_status_rejected(registry):
    with pytest.raises(ValueError):
        registry.register_missing("x", kind="tool", status="nope")


def test_lifecycle_forward(registry):
    registry.register_missing("research_web", kind="tool", factory="research")
    item = registry.mark_prompt_written("research_web", "pompts_11/075_04_research_web_capability.md")
    assert item.status == PROMPT_WRITTEN
    item = registry.mark_implemented("research_web", "scripts_01/research_web.py")
    assert item.status == IMPLEMENTED


def test_lifecycle_no_regression(registry):
    """implemented не откатывается повторным register_missing (register-first)."""
    registry.register_missing("research_web", kind="tool", factory="research")
    registry.mark_implemented("research_web", "scripts_01/research_web.py")
    registry.register_missing("research_web", kind="tool", status=REGISTERED)
    assert registry.get("research_web").status == IMPLEMENTED


def test_lifecycle_no_regression_design_ready(registry):
    """design_ready не откатывается до registered (forward-only lifecycle)."""
    registry.register_missing("factory_registry", kind="registry", status=DESIGN_READY)
    registry.register_missing("factory_registry", kind="registry", status=REGISTERED)
    assert registry.get("factory_registry").status == DESIGN_READY


def test_mark_prompt_written_unknown_key(registry):
    with pytest.raises(KeyError):
        registry.mark_prompt_written("ghost", "075_04_research_web_capability.md")


def test_mark_implemented_unknown_key(registry):
    with pytest.raises(KeyError):
        registry.mark_implemented("ghost", "scripts_01/x.py")


def test_mark_prompt_written_no_regression(registry):
    """mark_prompt_written не откатывает implemented (lifecycle forward-only)."""
    registry.register_missing("research_web", kind="tool", factory="research")
    registry.mark_implemented("research_web", "scripts_01/research_web.py")
    item = registry.mark_prompt_written("research_web", "pompts_11/075_04_research_web_capability.md")
    assert item.status == IMPLEMENTED


# ─── queries ────────────────────────────────────────────────────────────────


def test_list_by_status(registry):
    registry.register_missing("a", kind="tool")
    registry.register_missing("b", kind="engine")
    registry.mark_implemented("b", "scripts_01/b.py")
    assert len(registry.list_all()) == 2
    assert [i.item_id for i in registry.list_by_status(REGISTERED)] == ["a"]
    assert [i.item_id for i in registry.list_by_status(IMPLEMENTED)] == ["b"]


def test_list_by_factory(registry):
    registry.register_missing("research_web", kind="tool", factory="research")
    registry.register_missing("x", kind="tool", factory="code")
    assert [i.item_id for i in registry.list_by_factory("research")] == ["research_web"]


def test_unregister(registry):
    registry.register_missing("temp", kind="tool")
    assert registry.unregister("temp") is True
    assert registry.get("temp") is None
    assert registry.unregister("temp") is False


# ─── B10/R-127 schema validation ────────────────────────────────────────────


def test_validate_schema_clean(registry):
    registry.register_missing("x", kind="tool")
    assert registry.schema_violations == []


def test_validate_schema_bad_kind(registry):
    reg = MissingRegistry.__new__(MissingRegistry)  # минуя init
    reg._load_error = None
    reg._data = {"x": {"item_id": "x", "kind": "bogus", "status": REGISTERED}}
    assert any("invalid kind" in v for v in reg.validate_schema())


def test_validate_schema_implemented_requires_impl(registry):
    reg = MissingRegistry.__new__(MissingRegistry)
    reg._load_error = None
    reg._data = {"x": {"item_id": "x", "kind": "tool", "status": IMPLEMENTED}}
    assert any("implementation empty" in v for v in reg.validate_schema())


def test_validate_schema_prompt_requires_path(registry):
    reg = MissingRegistry.__new__(MissingRegistry)
    reg._load_error = None
    reg._data = {"x": {"item_id": "x", "kind": "tool", "status": PROMPT_WRITTEN}}
    assert any("prompt_path empty" in v for v in reg.validate_schema())


def test_from_dict_ignores_unknown_keys():
    """Лишний ключ в ручном YAML не роняет реестр (паттерн ScenarioManifest)."""
    item = MissingItem.from_dict({
        "item_id": "x", "kind": "tool", "status": REGISTERED,
        "extra_unknown_key": "ignored",
    })
    assert item.item_id == "x"
    assert item.kind == "tool"


# ─── persistence + seed ─────────────────────────────────────────────────────


def test_persistence_roundtrip(tmp_path):
    path = tmp_path / "missing.yaml"
    r1 = MissingRegistry(path)
    r1.register_missing("research_web", kind="tool", factory="research")
    r1.mark_implemented("research_web", "scripts_01/research_web.py")
    r2 = MissingRegistry(path)  # перечитываем с диска
    item = r2.get("research_web")
    assert item is not None
    assert item.status == IMPLEMENTED


def test_seed_defaults_idempotent(tmp_path):
    path = tmp_path / "missing.yaml"
    r1 = MissingRegistry(path)
    assert seed_defaults(r1) == 7
    assert r1.count() == 7
    # research_web из seed — implemented
    assert r1.get("research_web").status == IMPLEMENTED
    # #1/#2 — design_ready (дизайн готов, не промт)
    assert r1.get("factory_registry").status == DESIGN_READY
    assert r1.get("scenario_engine").status == DESIGN_READY
    # повторный seed ничего не добавляет
    assert seed_defaults(r1) == 0


def test_missing_item_to_dict():
    item = MissingItem(item_id="research_web", kind="tool", factory="research")
    d = item.to_dict()
    assert d["item_id"] == "research_web"
    assert d["status"] == REGISTERED


# ─── CLI (python -m core_02.missing_registry) ──────────────────────────────


def test_cli_seed(tmp_path):
    path = tmp_path / "missing.yaml"
    assert main(["--path", str(path), "seed"]) == 0
    assert main(["--path", str(path), "seed"]) == 0  # идемпотентно
    reg = MissingRegistry(path)
    assert reg.count() == 7


def test_cli_register_and_list(tmp_path, capsys):
    path = tmp_path / "missing.yaml"
    assert main(["--path", str(path), "register", "my_tool", "--kind", "tool",
                 "--factory", "code", "--description", "недостающий тул"]) == 0
    assert main(["--path", str(path), "list"]) == 0
    out = capsys.readouterr().out
    assert "my_tool" in out
    assert "code" in out


def test_cli_list_json(tmp_path, capsys):
    path = tmp_path / "missing.yaml"
    main(["--path", str(path), "register", "x", "--kind", "engine"])
    capsys.readouterr()  # сбросить вывод register
    assert main(["--path", str(path), "list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["item_id"] == "x"
    assert payload[0]["status"] == REGISTERED


def test_cli_mark_implemented_unknown_item_clean_exit(tmp_path, capsys):
    """mark-implemented несуществующего item → clean message + exit 1 (не traceback).

    Контракт runbook MISSING_REGISTRY_RUNBOOK.md §3: несуществующий item → exit 1
    с сообщением в stderr, НЕ сырой traceback (KeyError обрабатывается в dispatch).
    """
    path = tmp_path / "missing.yaml"
    code = main(["--path", str(path), "mark-implemented", "ghost_item",
                 "--implementation", "scripts_01/x.py"])
    captured = capsys.readouterr()
    assert code == 1
    assert "ghost_item" in captured.err
    assert "зарегистрирован" in captured.err
    assert "Traceback" not in captured.out and "Traceback" not in captured.err


def test_cli_mark_prompt_written_unknown_item_clean_exit(tmp_path, capsys):
    """mark-prompt-written несуществующего item → clean message + exit 1."""
    path = tmp_path / "missing.yaml"
    code = main(["--path", str(path), "mark-prompt-written", "ghost_item",
                 "--prompt", "pompts_11/promt99.md"])
    captured = capsys.readouterr()
    assert code == 1
    assert "ghost_item" in captured.err
    assert "Traceback" not in captured.out and "Traceback" not in captured.err


def test_cli_mark_implemented(tmp_path, capsys):
    path = tmp_path / "missing.yaml"
    main(["--path", str(path), "register", "research_web", "--kind", "tool"])
    assert main(["--path", str(path), "mark-implemented", "research_web",
                 "--implementation", "scripts_01/research_web.py"]) == 0
    reg = MissingRegistry(path)
    assert reg.get("research_web").status == IMPLEMENTED
    assert "implemented" in capsys.readouterr().out


def test_cli_check_valid(tmp_path, capsys):
    path = tmp_path / "missing.yaml"
    main(["--path", str(path), "seed"])
    assert main(["--path", str(path), "check"]) == 0
    assert "валиден" in capsys.readouterr().out


def test_cli_check_invalid(tmp_path, capsys):
    """Повреждённая запись (implemented без implementation) → exit 1."""
    path = tmp_path / "missing.yaml"
    main(["--path", str(path), "register", "x", "--kind", "tool"])
    reg = MissingRegistry(path)
    reg._data["x"]["status"] = IMPLEMENTED  # вручную ломаем инвариант
    reg._save()
    assert main(["--path", str(path), "check"]) == 1
    assert "violation" in capsys.readouterr().out


# ─── multi-prompt support (promt 087) ───────────────────────────────────────


def test_related_prompts_roundtrip(registry):
    """register с related_prompts → get → to_dict/from_dict → persistence."""
    registry.register_missing(
        "intelligence_integration", kind="capability", factory="content",
        prompt_path="pompts_11/085_19_close_intelligence_loop.md",
        related_prompts=["pompts_11/084_19_intelligence_integration_forensics.md"],
    )
    item = registry.get("intelligence_integration")
    assert item.prompt_path == "pompts_11/085_19_close_intelligence_loop.md"
    assert item.related_prompts == ["pompts_11/084_19_intelligence_integration_forensics.md"]
    d = item.to_dict()
    assert d["related_prompts"] == ["pompts_11/084_19_intelligence_integration_forensics.md"]
    restored = MissingItem.from_dict(d)
    assert restored.related_prompts == item.related_prompts


def test_add_related_prompt_appends_and_dedups(registry):
    registry.register_missing("x", kind="tool")
    item = registry.add_related_prompt("x", "pompts_11/084_19_intelligence_integration_forensics.md")
    assert item.related_prompts == ["pompts_11/084_19_intelligence_integration_forensics.md"]
    # dedup: повторный путь не дублируется
    item = registry.add_related_prompt("x", "pompts_11/084_19_intelligence_integration_forensics.md")
    assert item.related_prompts == ["pompts_11/084_19_intelligence_integration_forensics.md"]
    # второй related
    item = registry.add_related_prompt("x", "pompts_11/085_19_close_intelligence_loop.md")
    assert item.related_prompts == [
        "pompts_11/084_19_intelligence_integration_forensics.md",
        "pompts_11/085_19_close_intelligence_loop.md",
    ]


def test_add_related_prompt_unknown_key(registry):
    with pytest.raises(KeyError):
        registry.add_related_prompt("ghost", "pompts_11/promt99.md")


def test_mark_implemented_with_related_prompts(registry):
    registry.register_missing("x", kind="tool")
    item = registry.mark_implemented(
        "x", "scripts_01/x.py",
        prompt_path="pompts_11/086_19_opportunity_ranking.md",
        related_prompts=["pompts_11/084_19_intelligence_integration_forensics.md"],
    )
    assert item.status == IMPLEMENTED
    assert item.related_prompts == ["pompts_11/084_19_intelligence_integration_forensics.md"]


def test_backward_compat_no_related_prompts(registry):
    """Записи без related_prompts → [] (не падают)."""
    registry.register_missing("legacy", kind="tool", prompt_path="pompts_11/promt99.md")
    item = registry.get("legacy")
    assert item.related_prompts == []
    assert item.prompt_path == "pompts_11/promt99.md"


def test_validate_schema_related_prompts_not_list(registry):
    reg = MissingRegistry.__new__(MissingRegistry)
    reg._load_error = None
    reg._data = {"x": {"item_id": "x", "kind": "tool", "status": REGISTERED,
                        "related_prompts": "not-a-list"}}
    assert any("related_prompts must be a list" in v for v in reg.validate_schema())


def test_validate_schema_related_prompts_empty_string(registry):
    reg = MissingRegistry.__new__(MissingRegistry)
    reg._load_error = None
    reg._data = {"x": {"item_id": "x", "kind": "tool", "status": REGISTERED,
                        "related_prompts": [""]}}
    assert any("non-empty strings" in v for v in reg.validate_schema())


# ─── backfill: bool (machine-readable, B10) ─────────────────────────────────


def test_register_backfill_false_by_default(registry):
    registry.register_missing("x", kind="tool")
    assert registry.get("x").backfill is False


def test_register_backfill_true_requires_implemented(registry):
    """backfill=True с не-implemented статусом → ValueError (defense-in-depth)."""
    with pytest.raises(ValueError, match="requires status='implemented'"):
        registry.register_missing("x", kind="tool", status=REGISTERED, backfill=True)


def test_register_with_backfill_true(registry):
    registry.register_missing(
        "role_executor", kind="module", factory="forge",
        implementation="core_02/role_executor.py",
        status=IMPLEMENTED, backfill=True,
    )
    item = registry.get("role_executor")
    assert item.backfill is True
    assert item.status == IMPLEMENTED
    # roundtrip через YAML-словарь
    d = item.to_dict()
    assert d["backfill"] is True
    restored = MissingItem.from_dict(d)
    assert restored.backfill is True


def test_register_update_preserves_backfill(registry):
    registry.register_missing(
        "x", kind="tool", implementation="scripts_01/x.py",
        status=IMPLEMENTED, backfill=True,
    )
    # Повторный register без backfill не сбрасывает факт (как lifecycle).
    registry.register_missing("x", kind="tool", status=IMPLEMENTED,
                              implementation="scripts_01/x.py")
    assert registry.get("x").backfill is True


def test_validate_schema_backfill_non_bool(registry):
    reg = MissingRegistry.__new__(MissingRegistry)
    reg._load_error = None
    reg._data = {"x": {"item_id": "x", "kind": "tool", "status": IMPLEMENTED,
                        "implementation": "scripts_01/x.py",
                        "backfill": "yes"}}
    assert any("backfill must be a bool" in v for v in reg.validate_schema())


def test_validate_schema_backfill_true_requires_implemented(registry):
    reg = MissingRegistry.__new__(MissingRegistry)
    reg._load_error = None
    reg._data = {"x": {"item_id": "x", "kind": "tool", "status": REGISTERED,
                        "backfill": True}}
    assert any("backfill=true but status" in v for v in reg.validate_schema())


def test_validate_schema_backfill_true_implemented_clean(registry):
    reg = MissingRegistry.__new__(MissingRegistry)
    reg._load_error = None
    reg._data = {"x": {"item_id": "x", "kind": "tool", "status": IMPLEMENTED,
                        "implementation": "scripts_01/x.py",
                        "backfill": True}}
    assert reg.validate_schema() == []


def test_from_dict_backfill_default_false():
    item = MissingItem.from_dict({"item_id": "x", "kind": "tool", "status": REGISTERED})
    assert item.backfill is False


def test_cli_register_backfill(tmp_path):
    path = tmp_path / "missing.yaml"
    assert main(["--path", str(path), "register", "role_executor", "--kind", "module",
                 "--implementation", "core_02/role_executor.py",
                 "--status", "implemented", "--backfill"]) == 0
    reg = MissingRegistry(path)
    assert reg.get("role_executor").backfill is True


def test_cli_register_no_backfill(tmp_path):
    path = tmp_path / "missing.yaml"
    main(["--path", str(path), "register", "x", "--kind", "tool"])
    assert MissingRegistry(path).get("x").backfill is False


def test_cli_add_related_prompt(tmp_path, capsys):
    path = tmp_path / "missing.yaml"
    main(["--path", str(path), "register", "x", "--kind", "tool"])
    capsys.readouterr()
    assert main(["--path", str(path), "add-related-prompt", "x",
                 "--prompt", "pompts_11/084_19_intelligence_integration_forensics.md"]) == 0
    reg = MissingRegistry(path)
    assert reg.get("x").related_prompts == ["pompts_11/084_19_intelligence_integration_forensics.md"]
    assert "related=1" in capsys.readouterr().out


def test_cli_mark_implemented_related_prompt(tmp_path, capsys):
    path = tmp_path / "missing.yaml"
    main(["--path", str(path), "register", "x", "--kind", "tool"])
    capsys.readouterr()
    assert main(["--path", str(path), "mark-implemented", "x",
                 "--implementation", "scripts_01/x.py",
                 "--prompt", "pompts_11/086_19_opportunity_ranking.md",
                 "--related-prompt", "pompts_11/084_19_intelligence_integration_forensics.md"]) == 0
    reg = MissingRegistry(path)
    item = reg.get("x")
    assert item.status == IMPLEMENTED
    assert item.prompt_path == "pompts_11/086_19_opportunity_ranking.md"
    assert item.related_prompts == ["pompts_11/084_19_intelligence_integration_forensics.md"]


def test_cli_list_json_includes_related_prompts(tmp_path, capsys):
    path = tmp_path / "missing.yaml"
    main(["--path", str(path), "register", "x", "--kind", "tool"])
    main(["--path", str(path), "add-related-prompt", "x",
          "--prompt", "pompts_11/084_19_intelligence_integration_forensics.md"])
    capsys.readouterr()
    assert main(["--path", str(path), "list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["related_prompts"] == ["pompts_11/084_19_intelligence_integration_forensics.md"]
