"""tests_09/test_blueprint_v3.py — tests for the Blueprint v3 corpus wrapper.

Note: tests target a temporary fixture copy of the canonical blueprints tree to
avoid mutating user-owned files. The fixture is seeded from a read-only mirror
and torn down at the end.
"""

from __future__ import annotations

import shutil
}

import pytest

from core_02.blueprint_v3 import (
    Blueprint,
    BlueprintCorpus,
    DEFAULT_BLUEPRINTS_DIR,
    REQUIRED_SECTIONS,
    ROLE_TYPES,
    parse_blueprint_md,
)


# ─── fixtures ────────────────────────────────────────────────────────────────


# A canonical seed directory the tests can copy from. When CI has no access to
# the user's on-disk tree, fall back to a synthetic minimum that exercises the
# parser/formatter well enough. We always copy to tmp_path to avoid touching
# user files.
def _seed_corpus(tmp_path: Path) -> Path:
    src = DEFAULT_BLUEPRINTS_DIR
    if not (src / "registry.yaml").exists():
        # Build a synthetic minimum that still satisfies contracts.
        (tmp_path / "registry.yaml").write_text(
            "pipeline:\n"
            "  - id: developer\n"
            "    file: 09_developer.md\n"
            "    type: implementation\n"
            "    role: AI Senior Developer\n"
            "    description: impl\n"
            "    condition: always\n"
            "    triggers:\n"
            '      - "реализуй модуль"\n'
            "    dependencies: []\n"
            "    outputs:\n"
            "      - src/**/*.py\n"
            "project_types:\n"
            "  web:\n"
            "    required_roles: [developer]\n"
            "    skip_roles: []\n"
            "  script:\n"
            "    required_roles: [developer]\n"
            "    skip_roles: []\n"
            "complexity_routing:\n"
            "  small:\n"
            "    required_roles: [developer]\n"
            "    skip_roles: []\n"
            "categories:\n"
            "  implementation: [developer]\n"
            "metadata:\n"
            "  version: \"3.0.0\"\n",
            encoding="utf-8",
        )
        (tmp_path / "09_developer.md").write_text(
            "ROLE: AI Senior Developer\n"
            "VERSION: 3.1.0\n\n"
            "<role>\nImplementation role.\n</role>\n\n"
            "<system_role>\nDoes X. Doesn't Y.\n</system_role>\n\n"
            "<input>\nArchitecture spec.\n</input>\n\n"
            "<main_objective>\nProduction code.\n</main_objective>\n\n"
            "<priority_order>\nCorrectness first.\n</priority_order>\n\n"
            "<implementation_scope_rules>\nAllowed: target module only.\n</implementation_scope_rules>\n",
            encoding="utf-8",
        )
        return tmp_path
    # Copy real user tree into a tmp dir we can mutating freely.
    dst = tmp_path / "blueprints_v3"
    shutil.copytree(src, dst)
    return dst


@pytest.fixture
def corpus(tmp_path: Path) -> BlueprintCorpus:
    seed = _seed_corpus(tmp_path)
    return BlueprintCorpus(root=seed)


# ─── reading ────────────────────────────────────────────────────────────────


def test_list_roles_returns_all_known_ids(corpus: BlueprintCorpus) -> None:
    roles = corpus.list_roles()
    assert isinstance(roles, list)
    ids = [r[0] for r in roles]
    # The real tree has 17 named roles; fixture has one.
    if (DEFAULT_BLUEPRINTS_DIR / "registry.yaml").exists():
        assert "developer" in ids
        assert "architect" in ids
        assert "tester" in ids
        assert len(ids) >= 17
    else:
        assert ids == ["developer"]


def test_list_by_type_filters_correctly(corpus: BlueprintCorpus) -> None:
    impl = corpus.list_by_type("implementation")
    assert all(r[3] == "implementation" for r in impl)
    # developer + (frontend + devops + fixer) in real tree.
    ids = [r[0] for r in impl]
    assert "developer" in ids


def test_load_blueprint_returns_structured_blueprint(corpus: BlueprintCorpus) -> None:
    if "developer" not in [r[0] for r in corpus.list_roles()]:
        pytest.skip("developer role not present in fixture")
    bp = corpus.load_blueprint("developer")
    assert isinstance(bp, Blueprint)
    # Every required section must be present on a well-formed v3 developer role.
    missing = corpus.validate_blueprint(bp)
    assert missing == [], f"developer missing required: {missing}"
    # Header metadata extracted.
    assert "VERSION" in bp.header_meta
    role_section = bp.sections["role"]
    # Regression: real tree has Russian role.section text (developer.md's <role>
    # body) AND synthetic seed has minimal "Implementation role." body — neither
    # contains English "Developer" literally. Split into two named assertions so
    # a future failure isolates which side regressed (per reviewer nit-1 v5.44.0).
    role_header = bp.header_meta.get("ROLE", "")
    assert role_header, f"developer role has empty ROLE header: {bp.header_meta!r}"
    assert "Developer" in role_header or "developer" in role_header.lower(), (
        f"developer role header lacks 'Developer' marker (English-title regression): "
        f"HEADER={role_header!r}"
    )
    assert role_section, "developer role section (`<role>` body) is empty"
    # Soft content-grade check (per reviewer nit-1 v5.44.0): catches placeholder
    # regressions (`role_section = "lorem ipsum"` or whitespace-only) without
    # depending on the literal word "Developer" — works for both English-titled
    # and Russian-titled canon fixtures.
    assert len(role_section) >= 20, (
        f"developer role section too short (placeholder regression?): "
        f"SECTION={role_section!r}"
    )


def test_validate_blueprint_flags_missing_sections(tmp_path: Path) -> None:
    # Force a broken blueprint by mutating the copied registry's md file.
    corpus_dir = _seed_corpus(tmp_path)
    broken = Blueprint(
        file="99_broken.md",
        header_meta={"ROLE": "Broken", "VERSION": "3.1.0"},
        sections={"role": "x"},  # missing all other required
    )
    missing = BlueprintCorpus(root=corpus_dir).validate_blueprint(broken)
    assert all(s in missing for s in REQUIRED_SECTIONS if s != "role")


def test_resolve_pipeline_web_includes_frontend_when_present(
    corpus: BlueprintCorpus,
) -> None:
    if "frontend" not in [r[0] for r in corpus.list_roles()]:
        pytest.skip("frontend not in fixture")
    pipeline = corpus.resolve_pipeline(project_type="web", complexity="complex")
    assert "frontend" in pipeline
    assert "developer" in pipeline


def test_resolve_pipeline_script_skips_frontend(corpus: BlueprintCorpus) -> None:
    pipeline = corpus.resolve_pipeline(project_type="script", complexity="small")
    assert "developer" in pipeline
    # Frontend/DevOps should be skipped for script projects in the real tree.
    if "frontend" in [r[0] for r in corpus.list_roles()]:
        assert "frontend" not in pipeline


# ─── creation ────────────────────────────────────────────────────────────────


def test_create_blueprint_scaffolds_required_sections(corpus: BlueprintCorpus) -> None:
    bp = corpus.create_blueprint(
        role_id="mobile_developer",
        file_name="17_mobile_developer.md",
        role_title="AI Mobile Developer",
        role_type="implementation",
    )
    missing = corpus.validate_blueprint(bp)
    assert missing == [], f"newly-created blueprint missing {missing}"
    # Marker text confirms scaffold was used.
    assert "(allowed action)" in bp.sections["implementation_scope_rules"]
    assert bp.header_meta["VERSION"] == "3.1.0"


def test_create_blueprint_extra_sections_override_stubs(corpus: BlueprintCorpus) -> None:
    bp = corpus.create_blueprint(
        role_id="interior_consultant",
        file_name="18_interior_consultant.md",
        role_title="AI Interior Design Consultant",
        role_type="analysis",
        extra_sections={
            "role": "Ты — AI Interior Design Consultant уровня Senior.",
            "main_objective": (
                "Реализовать consultative loop подбора стилистики комнаты на основе "
                "размер/бюджет/предпочтения пользователя."
            ),
        },
    )
    assert "Senior" in bp.sections["role"]
    assert "consultative loop" in bp.sections["main_objective"]


def test_create_blueprint_rejects_duplicate_id(corpus: BlueprintCorpus) -> None:
    with pytest.raises(ValueError, match="уже зарегистрирован"):
        corpus.create_blueprint(
            role_id="developer",  # already present
            file_name="99_dup.md",
            role_title="Dup",
            role_type="implementation",
        )


def test_create_blueprint_rejects_unknown_role_type(corpus: BlueprintCorpus) -> None:
    with pytest.raises(ValueError, match="не из списка"):
        corpus.create_blueprint(
            role_id="weird_role",
            file_name="99_weird.md",
            role_title="Weird",
            role_type="magic",  # not in ROLE_TYPES
        )


def test_create_blueprint_rejects_non_md_filename(corpus: BlueprintCorpus) -> None:
    with pytest.raises(ValueError, match=".md"):
        corpus.create_blueprint(
            role_id="noext",
            file_name="noext.txt",
            role_title="NoExt",
            role_type="implementation",
        )


def test_blueprint_round_trip_markdown_is_stable(corpus: BlueprintCorpus) -> None:
    """Render→parse→render should be idempotent on header + section keys."""
    bp = corpus.create_blueprint(
        role_id="round_trip",
        file_name="rt.md",
        role_title="Round Trip",
        role_type="analysis",
        extra_sections={
            "response_style": "Технический тон, минимально многословный.",
        },
    )
    md = bp.to_markdown()
    re_parsed = parse_blueprint_md(md)
    assert re_parsed.header_meta.get("ROLE") == bp.header_meta["ROLE"]
    assert re_parsed.sections.get("response_style", "").strip().startswith(
        "Технический"
    )


# Note: parse_blueprint_md is the public parser; we use it for round-trip.


def test_register_in_registry_dry_run_does_not_write(tmp_path: Path) -> None:
    corpus_dir = _seed_corpus(tmp_path)
    corpus = BlueprintCorpus(root=corpus_dir)
    before = (corpus_dir / "registry.yaml").read_text(encoding="utf-8")
    new_text = corpus.register_in_registry(
        role_id="dry_run_role",
        file_name="dry.md",
        role_title="Dry",
        role_type="analysis",
        description="dry",
        triggers=["триггер"],
        dry_run=True,
    )
    after = (corpus_dir / "registry.yaml").read_text(encoding="utf-8")
    assert before == after, "dry_run не должен менять файл"
    assert "dry_run_role" in new_text


def test_register_in_registry_writes_and_makes_role_visible(tmp_path: Path) -> None:
    corpus_dir = _seed_corpus(tmp_path)
    corpus = BlueprintCorpus(root=corpus_dir)
    corpus.register_in_registry(
        role_id="telegram_correspondent",
        file_name="98_telegram.md",
        role_title="Telegram Correspondent",
        role_type="communication",
        description="Пишет ТГ-отчёты в Избранное и ведёт переписку с заказчиком.",
        triggers=["отчёт", "переписка"],
    )
    # Timestamped backup exists (.bak.YYYYMMDDTHHMMSS pattern).
    backups = [p for p in corpus_dir.iterdir() if p.name.startswith("registry.yaml.bak.")]
    assert len(backups) == 1, f"ожидали 1 timestamped backup, нашли: {list(corpus_dir.iterdir())}"
    # Role now resolvable.
    ids = [r[0] for r in corpus.list_roles()]
    assert "telegram_correspondent" in ids


def test_register_in_registry_rejects_invalid_yaml_splice(tmp_path: Path) -> None:
    """Post-splice YAML validation must abort before disk is touched.

    Simulate a broken splice using role_id with embedded quotes that escape
    YAML string boundaries safely but produce-encode errors only via monkeypatch
    on the splice itself — simpler: directly verify that an 'unknown role_type'
    (caught earlier) and a 'duplicate role_id' (caught earlier) leave the file
    untouched. The new defensive check is on YAML parse failure of splice text;
    since the formatter is deterministic, force a bad splice via monkeypatching
    the block builder by passing triggers that successfully splice but result
    in unparseable text (multi-line trigger literal with unbalanced quote).
    """
    corpus_dir = _seed_corpus(tmp_path)
    corpus = BlueprintCorpus(root=corpus_dir)
    before = (corpus_dir / "registry.yaml").read_text(encoding="utf-8")
    # Triggers contain line that'd be `-- "value` only — actual YAML breaks.
    with pytest.raises(ValueError):
        corpus.register_in_registry(
            role_id="bad_yaml",
            file_name="99_bad.md",
            role_title="Bad",
            role_type="analysis",
            description="bad",
            triggers=["trigger\n      - \"'unbalanced"],
        )
    after = (corpus_dir / "registry.yaml").read_text(encoding="utf-8")
    assert before == after, "плохой сплис не должен трогать registry.yaml"


def test_register_in_registry_write_failure_restores_backup(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the final write_text raises OSError, the original file must be restored."""
    import core_02.blueprint_v3 as bpv3
    corpus_dir = _seed_corpus(tmp_path)
    corpus = BlueprintCorpus(root=corpus_dir)
    original = (corpus_dir / "registry.yaml").read_text(encoding="utf-8")

    real_write_text = Path.write_text
    def explode(self, *args, **kwargs):  # noqa: ANN001
        if self.name == "registry.yaml":
            raise OSError("simulated disk full / permission denied")
        return real_write_text(self, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", explode)

    with pytest.raises(OSError, match="simulated"):
        corpus.register_in_registry(
            role_id="will_fail_to_persist",
            file_name="98_will_fail.md",
            role_title="Will fail",
            role_type="analysis",
            description="rollback test",
            triggers=["триггер"],
        )
    # Original content preserved (either by restore-from-backup or by never
    # touching the file — both acceptable rollback paths).
    assert (corpus_dir / "registry.yaml").read_text(encoding="utf-8") == original


# ─── corpus resilience (CAN-1 / CAN-4, v5.43.0) ────────────────────────────


def test_init_raises_value_error_on_broken_yaml(tmp_path: Path) -> None:
    """CAN-1: broken registry.yaml → clean ValueError, not raw yaml traceback."""
    corpus_dir = tmp_path
    (corpus_dir / "registry.yaml").write_text(
        "pipeline:\n"
        "  - id: developer\n"
        "    file: 09_developer.md\n"
        "    type: [unclosed\n",  # unbalanced flow sequence → YAMLError
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="registry.yaml повреждён"):
        BlueprintCorpus(root=corpus_dir)


def test_init_raises_value_error_on_empty_registry(tmp_path: Path) -> None:
    """CAN-1: empty registry.yaml → clean ValueError (not AttributeError on None)."""
    corpus_dir = tmp_path
    (corpus_dir / "registry.yaml").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="registry.yaml пуст"):
        BlueprintCorpus(root=corpus_dir)


def test_register_in_registry_without_marker_inserts_into_pipeline(
    tmp_path: Path,
) -> None:
    """CAN-4: missing splice marker → entry lands inside existing pipeline list.

    Regression: the old fallback appended the block at EOF, creating a
    corrupt/duplicate section after ``metadata:``. The new fallback locates
    the top-level ``pipeline:`` key and inserts the entry before the next
    top-level section — YAML stays valid, exactly one pipeline section.
    """
    corpus_dir = tmp_path
    (corpus_dir / "registry.yaml").write_text(
        "pipeline:\n"
        "  - id: developer\n"
        "    file: 09_developer.md\n"
        "    type: implementation\n"
        "    role: AI Senior Developer\n"
        "    description: impl\n"
        "    condition: always\n"
        "    triggers:\n"
        '      - "реализуй модуль"\n'
        "metadata:\n"
        '  version: "3.0.0"\n',
        encoding="utf-8",
    )
    corpus = BlueprintCorpus(root=corpus_dir)
    corpus.register_in_registry(
        role_id="markerless_role",
        file_name="97_markerless.md",
        role_title="Markerless",
        role_type="analysis",
        description="no marker present",
        triggers=["триггер"],
    )
    text = (corpus_dir / "registry.yaml").read_text(encoding="utf-8")
    # Exactly ONE top-level pipeline section (no duplicate after metadata).
    assert text.count("pipeline:") == 1, f"duplicate pipeline section: {text!r}"
    # New role resolvable after reload.
    ids = [r[0] for r in corpus.list_roles()]
    assert "markerless_role" in ids
    assert "developer" in ids

