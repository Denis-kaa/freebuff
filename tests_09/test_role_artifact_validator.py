# tests_09/test_role_artifact_validator.py — RoleArtifactValidator (P3, шаг 2 ROADMAP §16)
#
# Шаг 2 ROADMAP-LA-001 (промт 68/70, v5.155.0 .. v5.156.0):
# RoleArtifactValidator — аддитивный валидатор существования файлов-артефактов
# ролей Blueprint v3. Композирует существующий ForgePipeline.stage_check() без
# модификаций. scope=existence (НЕ content-schema). Существующие модули
# (workspace.py/forge_pipeline.py/forge_registry.py) не изменяются.
#
# Фиксы v5.156.0 (по замечаниям code-reviewer):
#   - _base_check использует dry_run=False (не dry_run=True) → stage_check
#     возвращает реальный ok/failed, а не "skipped".
#   - project_id = ForgeRegistry._slug() (DRY: один источник истины).
#   - present содержит ТОЛЬКО real relative-paths (≤ PRESENT_CAP=10), без
#     mixed-annotations типа "src/**/*.py (15 files)".
#   - _Project alias-import убран (Project уже импортирован).
import json

import pytest

from core_02.forge_facade import (
    DEFAULT_REGISTRY_CANDIDATES,
    DEFAULT_ROLE_OUTPUTS,
    PIPELINE_ROLES,
    ForgeFacade,
    RoleArtifactReport,
    RoleArtifactValidator,
    ValidationSummary,
)
from core_02.workspace import Project


# ─── helpers ────────────────────────────────────────────────────────────────


@pytest.fixture
def project(tmp_path):
    """Минимальный Project с README + RUNNABLE + CHECKLIST (базовый CHECK ok)."""
    p = tmp_path / "vkusvill_demo"
    p.mkdir()
    (p / "project.yaml").write_text("name: vkusvill_demo\ntype: script\n",
                                     encoding="utf-8")
    (p / "README.md").write_text("# vkusvill_demo\n", encoding="utf-8")
    (p / "RUNNABLE.md").write_text("# RUNNABLE\n", encoding="utf-8")
    (p / "CHECKLIST.md").write_text("# CHECKLIST\n", encoding="utf-8")
    return Project.load(p)


def _write_yaml_registry(path, pipeline):
    """Пишет registry.yaml в формате blueprints_v3 (pipeline: list)."""
    import yaml
    payload = {"pipeline": pipeline, "metadata": {"version": "test"}}
    with open(str(path), "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)


def _materialize_outputs(root, patterns):
    """Создаёт файлы-«артефакты» по каждому паттерну (прямой файл или простой
    path для нескольких glob). Для каждого паттерна создаётся сам файл."""
    }
    for pat in patterns:
        if "*" in pat:
            # Превращаем "src/**/*.py" → "src/foo.py" (простой путь).
            simple = re.sub(r"\*\*?/|\*", "x", pat)
            (root / simple).parent.mkdir(parents=True, exist_ok=True)
            (root / simple).write_text("# artifact\n", encoding="utf-8")
        else:
            (root / pat).parent.mkdir(parents=True, exist_ok=True)
            (root / pat).write_text("# artifact\n", encoding="utf-8")


# ─── scope defaults ─────────────────────────────────────────────────────────


class TestScopeDefaults:
    def test_default_role_ids_is_pipeline_scope(self):
        assert len(PIPELINE_ROLES) == 14
        # Default = все 14 pipeline-ролей (включая frontend+devops), НЕ reference.
        assert "orchestrator" not in PIPELINE_ROLES
        assert "context_keeper" not in PIPELINE_ROLES
        assert "response_writer" not in PIPELINE_ROLES

    def test_default_role_outputs_covers_pipeline(self):
        # Все pipeline-роли имеют хотя бы 1 output (для fallback).
        for rid in PIPELINE_ROLES:
            assert rid in DEFAULT_ROLE_OUTPUTS, \
                f"pipeline-роль {rid} отсутствует в DEFAULT_ROLE_OUTPUTS"
            assert len(DEFAULT_ROLE_OUTPUTS[rid]) >= 1

    def test_default_registry_candidates_priority(self):
        # Первый кандидат — blueprints_v3/registry.yaml (платформенный стандарт).
        assert DEFAULT_REGISTRY_CANDIDATES[0] == "blueprints_v3/registry.yaml"


# ─── loaded registry: ok / partial / missing ───────────────────────────────


class TestLoadedRegistry:
    def test_registry_loaded_all_outputs_present(self, tmp_path, project):
        # Реестр с outputs pipeline-ролей; все артефакты материализованы.
        registry_path = tmp_path / "blueprints_v3" / "registry.yaml"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        explainer_id, explainer_patterns = "explainer", ("brief.md", "parsed_requirements.md")
        lisa_id, lisa_patterns = "lisa", ("lisa_report.md",)
        pipeline = [
            {"id": explainer_id, "outputs": list(explainer_patterns)},
            {"id": lisa_id, "outputs": list(lisa_patterns)},
        ]
        _write_yaml_registry(registry_path, pipeline)

        _materialize_outputs(project.root, list(explainer_patterns) + list(lisa_patterns))

        # Явный registry_path — обязательно: project_root/blueprints_v3/registry.yaml
        # не существует (registry лежит рядом с tmp_path, не внутри project_root).
        validator = RoleArtifactValidator(registry_path=registry_path)
        summary = validator.validate(project, role_ids=(explainer_id, lisa_id),
                                       compose_check=False)

        assert isinstance(summary, ValidationSummary)
        assert summary.registry_status == "loaded"
        assert summary.registry_path == str(registry_path)
        assert summary.roles_checked == (explainer_id, lisa_id)
        assert summary.overall == "ok"
        # Каждый role_report имеет ok-статус и пустой missing.
        for rprt in summary.role_reports:
            assert isinstance(rprt, RoleArtifactReport)
            assert rprt.status == "ok"
            assert rprt.missing == ()
            assert len(rprt.present) >= 1

    def test_registry_loaded_some_outputs_missing(self, tmp_path, project):
        registry_path = tmp_path / "blueprints_v3" / "registry.yaml"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        pipeline = [
            {"id": "explainer", "outputs": ["brief.md", "parsed_requirements.md"]},
            {"id": "lisa", "outputs": ["lisa_report.md"]},
        ]
        _write_yaml_registry(registry_path, pipeline)

        # Только brief.md; parsed_requirements.md и lisa_report.md отсутствуют.
        _materialize_outputs(project.root, ["brief.md"])

        # Явный registry_path (см. test_registry_loaded_all_outputs_present).
        validator = RoleArtifactValidator(registry_path=registry_path)
        summary = validator.validate(project,
                                       role_ids=("explainer", "lisa"),
                                       compose_check=False)

        assert summary.registry_status == "loaded"
        assert summary.overall == "partial"
        explainer_rprt = next(r for r in summary.role_reports if r.role_id == "explainer")
        lisa_rprt = next(r for r in summary.role_reports if r.role_id == "lisa")
        assert explainer_rprt.status == "partial"
        assert "parsed_requirements.md" in explainer_rprt.missing
        assert "brief.md" in explainer_rprt.present
        assert lisa_rprt.status == "missing"
        assert lisa_rprt.missing == ("lisa_report.md",)
        assert lisa_rprt.present == ()

    def test_registry_unknown_role_id_skipped(self, tmp_path, project):
        # Если role_id не в registry + не в fallback → role_report требует empty.
        registry_path = tmp_path / "blueprints_v3" / "registry.yaml"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        _write_yaml_registry(registry_path, [])  # пустой registry

        validator = RoleArtifactValidator(registry_path=registry_path)
        # orchestrator — reference; в DEFAULT_ROLE_OUTPUTS его нет → required=()
        summary = validator.validate(project,
                                       role_ids=("orchestrator",),
                                       compose_check=False)

        orchestrator_rprt = summary.role_reports[0]
        assert orchestrator_rprt.required == ()
        assert orchestrator_rprt.status == "ok"  # нет required → ok по классификации


# ─── registry resolution: missing / unreadable / explicit ──────────────────


class TestRegistryResolution:
    def test_missing_registry_uses_fallback(self, project):
        # Нет ни registry в project_root, ни в cwd (cwd = repo).
        validator = RoleArtifactValidator()
        summary = validator.validate(project,
                                       role_ids=("explainer", "lisa"),
                                       compose_check=False)

        assert summary.registry_status == "missing"
        assert summary.registry_path is None
        assert summary.overall == "degraded"
        # Fallback DEFAULT_ROLE_OUTPUTS применён, всё missing.
        explainer_rprt = next(r for r in summary.role_reports if r.role_id == "explainer")
        assert "brief.md" in explainer_rprt.required
        assert explainer_rprt.status == "missing"
        assert "brief.md" in explainer_rprt.missing

    def test_unreadable_registry_status(self, tmp_path, project):
        path = tmp_path / "blueprints_v3" / "registry.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pipeline: [unclosed\n", encoding="utf-8")  # битый YAML

        # Явный registry_path — иначе резолвер ищет в project_root/, и не находит.
        validator = RoleArtifactValidator(registry_path=path)
        summary = validator.validate(project,
                                       role_ids=("explainer",),
                                       compose_check=False)

        # registry найден, но не парсится → fallback + degraded.
        assert summary.registry_path == str(path)
        assert summary.registry_status == "unreadable"
        assert summary.overall == "degraded"
        explainer_rprt = summary.role_reports[0]
        assert "brief.md" in explainer_rprt.required  # из fallback
        assert explainer_rprt.status == "missing"

    def test_cwd_fallback_resolves_registry(self, tmp_path, project, monkeypatch):
        """Registry найден через cwd, не project_root.

        Резолвер в RoleArtifactValidator._resolve_registry ищет candidates в:
        1) явный путь (None в нашем случае) — не сработает.
        2) project_root/<cand> — НЕ находит (registry лежит в cwd, не project_root).
        3) cwd/<cand> — находит, потому что registry лежит в cwd.

        Изоляция: monkeypatch.chdir(tmp_path), чтобы cwd не указывал на
        реальный repo root (иначе тест может случайно найти существующий
        blueprints_v3/registry.yaml на платформе, что сделало бы cwd-resolution
        не-reproducible).
        """
        monkeypatch.chdir(tmp_path)
        reg_dir = tmp_path / "blueprints_v3"
        reg_dir.mkdir(parents=True, exist_ok=True)
        registry_path = reg_dir / "registry.yaml"
        _write_yaml_registry(registry_path, [{
            "id": "explainer", "outputs": ["brief.md"],
        ]])
        _materialize_outputs(project.root, ["brief.md"])

        # Валидатор БЕЗ явного registry_path: резолвер должен найти registry
        # через cwd.
        validator = RoleArtifactValidator()
        summary = validator.validate(project,
                                       role_ids=("explainer",),
                                       compose_check=False)

        assert summary.registry_status == "loaded"
        assert summary.registry_path == str(registry_path)
        # project_root path resolution: НЕ нашёлся (registry НЕ лежит в project_root).
        # Только cwd-resolution сработал.
        explainer_rprt = summary.role_reports[0]
        assert explainer_rprt.status == "ok"
        assert explainer_rprt.missing == ()

    def test_explicit_registry_path_must_exist(self, tmp_path, project):
        nonexistent = tmp_path / "nope.yaml"
        validator = RoleArtifactValidator(registry_path=nonexistent)
        summary = validator.validate(project,
                                       role_ids=("explainer",),
                                       compose_check=False)
        assert summary.registry_status == "missing"
        assert summary.registry_path == str(nonexistent)
        assert summary.overall == "degraded"

    def test_json_registry_compatible_when_yaml_available(self, tmp_path, project):
        # JSON-валидный синтаксис = yaml.safe_load парсит его как dict (без
        # падения). Этот тест валит yaml-путь; json-fallback не нужен пока yaml
        # доступен (yaml парсит JSON).
        path = tmp_path / "r.yaml"
        path.write_text(
            json.dumps({"pipeline": [{"id": "explainer", "outputs": ["brief.md"]}]}),
            encoding="utf-8",
        )
        _materialize_outputs(project.root, ["brief.md"])
        validator = RoleArtifactValidator(registry_path=path)
        summary = validator.validate(project,
                                       role_ids=("explainer",),
                                       compose_check=False)
        assert summary.registry_status == "loaded"
        explainer_rprt = summary.role_reports[0]
        assert explainer_rprt.status == "ok"

    def test_explicit_registry_path_takes_priority_over_cwd(self, tmp_path,
                                                                project,
                                                                monkeypatch):
        """Explicit registry_path побеждает cwd-fallback (precedence semantics).

        Резолвер в RoleArtifactValidator._resolve_registry:
        1) явный путь — приоритет (early check).
        2) project_root/<cand> — fallback.
        3) cwd/<cand> — fallback не используется если (1) сработал.

        Этот тест cover edge-case: explicit registry_path указывает на
        ОДИН файл (отличающийся по содержимому от cwd-альтернативы),
        monkeypatch.chdir делает доступным ДРУГОЙ registry в cwd, имя
        которого MATCHит DEFAULT_REGISTRY_CANDIDATES (blueprints_v3/registry.yaml);
        validate ДОЛЖЕН использовать explicit, НЕ cwd fallback.

        (c5.0 enhancement: cwd_registry_path теперь создаётся в
        blueprints_v3/registry.yaml — name которое реально найдёт cwd
        fallback iter. Без этого test проходит тривиально с cwd fallback
        который никогда не срабатывает.)
        """
        # 1) explicit registry (cодержит explainer без missing).
        explicit_path = tmp_path / "explicit_registry.yaml"  # НЕ под DEFAULT_REGISTRY_CANDIDATES.
        _write_yaml_registry(explicit_path, [
            {"id": "explainer", "outputs": ["brief.md"]},
        ])
        _materialize_outputs(project.root, ["brief.md"])

        # 2) cwd registry (отличающийся по роли — содержит lisa). Имя = DEFAULT_REGISTRY_CANDIDATES[0].
        # Это имя реально matchится cwd fallback iter (find first match в candidates).
        monkeypatch.chdir(tmp_path)
        cwd_alt_dir = tmp_path / "blueprints_v3"
        cwd_alt_dir.mkdir(parents=True, exist_ok=True)
        cwd_alt_registry_path = cwd_alt_dir / "registry.yaml"
        _write_yaml_registry(cwd_alt_registry_path, [
            {"id": "lisa", "outputs": ["brief.md"]},  # different role_id
        ])

        # SANITY: confirm that cwd fallback WOULD find cwd_alt_registry (если бы
        # explicit_path не был задан). Создаём second validator БЕЗ registry_path
        # — он ДОЛЖЕН использовать cwd fallback.
        validator_cwd_only = RoleArtifactValidator()
        summary_cwd_only = validator_cwd_only.validate(
            project, role_ids=("lisa",), compose_check=False,
        )
        assert summary_cwd_only.registry_status == "loaded"
        assert summary_cwd_only.registry_path == str(cwd_alt_registry_path)
        assert summary_cwd_only.role_reports[0].role_id == "lisa"
        # This confirms cwd-fallback is functional and finds the alt registry.

        # Validate с explicit registry_path. Должен использовать explicit,
        # НЕ cwd registry (даже если cwd fallback сработал бы — precedence test).
        validator = RoleArtifactValidator(registry_path=explicit_path)
        summary = validator.validate(project,
                                       role_ids=("explainer",),
                                       compose_check=False)

        # Explicit использован → loaded from explicit, role = explainer, status = ok.
        # (Если бы использовался cwd_alt, role = lisa → role_reports[0].role_id был бы другая.)
        assert summary.registry_status == "loaded"
        assert summary.registry_path == str(explicit_path)
        assert summary.role_reports[0].role_id == "explainer"
        assert summary.role_reports[0].status == "ok"


# ─── glob semantics ─────────────────────────────────────────────────────────


class TestGlobSemantics:
    def test_simple_glob_pattern_match_in_subdir(self, tmp_path, project):
        # registry объявляет "src/**/*.py"; в проекте есть src/foo/bar.py.
        (project.root / "src" / "foo").mkdir(parents=True, exist_ok=True)
        (project.root / "src" / "foo" / "bar.py").write_text("# code\n",
                                                              encoding="utf-8")

        registry_path = tmp_path / "r.yaml"
        _write_yaml_registry(registry_path, [
            {"id": "developer", "outputs": ["src/**/*.py"]},
        ])
        validator = RoleArtifactValidator(registry_path=registry_path)
        summary = validator.validate(project,
                                       role_ids=("developer",),
                                       compose_check=False)

        assert summary.overall == "ok"
        dev_rprt = summary.role_reports[0]
        assert dev_rprt.status == "ok"
        assert dev_rprt.missing == ()
        assert len(dev_rprt.present) >= 1
        assert any("bar.py" in p for p in dev_rprt.present)

    def test_multi_level_glob_no_match_yields_missing(self, tmp_path, project):
        registry_path = tmp_path / "r.yaml"
        _write_yaml_registry(registry_path, [
            {"id": "tester", "outputs": ["tests/**/*.py"]},
        ])
        # Проект пустой по tests/ — статус missing.
        validator = RoleArtifactValidator(registry_path=registry_path)
        summary = validator.validate(project,
                                       role_ids=("tester",),
                                       compose_check=False)

        tester_rprt = summary.role_reports[0]
        assert tester_rprt.status == "missing"
        assert "tests/**/*.py" in tester_rprt.missing

    def test_present_cap_limits_max_matches_reported(self, tmp_path, project):
        # Создаём 15 .py файлов в src/, проверяем что present ≤ PRESENT_CAP(10).
        for i in range(15):
            (project.root / "src" / f"m{i}.py").parent.mkdir(parents=True, exist_ok=True)
            (project.root / "src" / f"m{i}.py").write_text("# x\n", encoding="utf-8")

        # SANITY: на ФС действительно 15 файлов (не "изначально мало").
        # Без этой проверки тест прошёл бы даже если PRESENT_CAP=100 (cap не режет).
        assert len(list((project.root / "src").glob("**/*.py"))) == 15

        registry_path = tmp_path / "r.yaml"
        _write_yaml_registry(registry_path, [
            # Только src/**/*.py — без tests/migrations — чтобы status был ok.
            {"id": "developer", "outputs": ["src/**/*.py"]},
        ])
        # Явный registry_path (резолвер не ищет автоматически).
        validator = RoleArtifactValidator(registry_path=registry_path)
        summary = validator.validate(project,
                                       role_ids=("developer",),
                                       compose_check=False)

        dev_rprt = summary.role_reports[0]
        assert dev_rprt.status == "ok"
        # Единый формат: real relative-paths (≤ PRESENT_CAP=10) даже при 15 файлах.
        assert len(dev_rprt.present) <= 10
        assert all(p.startswith("src/") and p.endswith(".py") for p in dev_rprt.present)
        assert dev_rprt.missing == ()

    def test_present_exactly_at_present_cap(self, tmp_path, project):
        """Граничный случай: ровно PRESENT_CAP матчей -> present ровно PRESENT_CAP.

        PRESENT_CAP=10 в RoleArtifactValidator (v5.157.0). Ровно 10 файлов ->
        present ровно 10 (NO truncation beyond this point, NO divide-by-zero,
        NO edge-of-slice artifact_loss). Граничный случай для `[:PRESENT_CAP]`
        slicing semantics.
        """
        PRESENT_CAP = RoleArtifactValidator.PRESENT_CAP
        assert PRESENT_CAP == 10  # sanity: PRESENT_CAP не дрейфанул.

        # SANITY: на ФС ровно PRESENT_CAP файлов (не 9, не 11).
        for i in range(PRESENT_CAP):
            (project.root / "src" / f"cap{i}.py").parent.mkdir(
                parents=True, exist_ok=True,
            )
            (project.root / "src" / f"cap{i}.py").write_text(
                "# x\n", encoding="utf-8",
            )
        assert len(list((project.root / "src").glob("**/*.py"))) == PRESENT_CAP

        registry_path = tmp_path / "r.yaml"
        _write_yaml_registry(registry_path, [{
            "id": "developer", "outputs": ["src/**/*.py"],
        ]])
        validator = RoleArtifactValidator(registry_path=registry_path)
        summary = validator.validate(project,
                                       role_ids=("developer",),
                                       compose_check=False)
        dev_rprt = summary.role_reports[0]
        # Граничный случай: present ровно 10 (все матчи с шапкой, без truncation).
        assert len(dev_rprt.present) == PRESENT_CAP
        # Все real-relative-paths, без mixed-annotations.
        assert all(p.startswith("src/") and p.endswith(".py")
                   for p in dev_rprt.present)
        assert dev_rprt.missing == ()
        # status should be 'ok' since all 10 files materialized.
        assert dev_rprt.status == "ok"

    def test_present_returns_relative_paths_not_annotations(self, tmp_path, project):
        # Регрессия: present содержит ТОЛЬКО relative-paths, без mixed-annotations
        # типа "src/**/*.py (15 files)" (старый формат, до фикса code-reviewer).
        for i in range(3):
            (project.root / "src" / f"x{i}.py").parent.mkdir(parents=True, exist_ok=True)
            (project.root / "src" / f"x{i}.py").write_text("# x\n", encoding="utf-8")

        registry_path = tmp_path / "r.yaml"
        _write_yaml_registry(registry_path, [
            {"id": "developer", "outputs": ["src/**/*.py"]},
        ])
        validator = RoleArtifactValidator(registry_path=registry_path)
        summary = validator.validate(project,
                                       role_ids=("developer",),
                                       compose_check=False)
        dev_rprt = summary.role_reports[0]
        # Никаких скобок с counts в present.
        for entry in dev_rprt.present:
            assert "(" not in entry
            assert "files" not in entry
        # Required сохраняет исходный glob-паттерн для трассировки.
        assert "src/**/*.py" in dev_rprt.required

    def test_present_cap_with_zero_matches_returns_empty_tuple(self, tmp_path,
                                                                   project):
        """Граничный случай: 0 матчей → present = (), status = "missing".

        Симметрично к test_present_exactly_at_present_cap (10 матчей → 10 в present)
        и test_present_cap_limits_max_matches_reported (15 матчей → ≤10 в present).
        PRESENT_CAP slicing [:PRESENT_CAP] должен корректно обработать edge-case
        пустого списка (`[][:10] == []`). Также статус classification:
        required defined в registry, present=(), missing=("src/**/*.py") → ok_count=0
        → status="missing".
        """
        # SANITY: на ФС действительно 0 .py файлов (НЕ "изначально мало").
        assert len(list((project.root / "src").glob("**/*.py"))) == 0

        registry_path = tmp_path / "r.yaml"
        _write_yaml_registry(registry_path, [
            {"id": "developer", "outputs": ["src/**/*.py"]},
        ])
        validator = RoleArtifactValidator(registry_path=registry_path)
        summary = validator.validate(project,
                                       role_ids=("developer",),
                                       compose_check=False)
        dev_rprt = summary.role_reports[0]

        # Граничный случай: пустой список.
        assert dev_rprt.present == ()  # empty tuple, не None.
        assert dev_rprt.missing == ("src/**/*.py",)
        # required сохраняет glob-паттерн (для трассировки, даже при 0 матчах).
        assert dev_rprt.required == ("src/**/*.py",)
        # Classification: required определены, present=0 → ok_count=0 → status="missing".
        # Reference: RoleArtifactValidator._classify_role_status: required=True, ok_count=0 → "missing".
        assert dev_rprt.status == "missing"
        # overall: registry loaded, role не ok → "partial".
        assert summary.overall == "partial"
        # base_check not run (compose_check=False в этом тесте).
        assert summary.base_check_status == "skipped"


# ─── compose с ForgePipeline.stage_check() ─────────────────────────────────


class TestComposeWithStageCheck:
    def test_compose_off_skips_base_check(self, project):
        validator = RoleArtifactValidator()
        summary = validator.validate(project,
                                       role_ids=("explainer",),
                                       compose_check=False)
        assert summary.base_check_status == "skipped"
        assert summary.base_check_missing == ()

    def test_compose_on_with_readme_passes_base_check(self, project):
        # project fixture имеет README.md → base_check реально ok
        # (dry_run=False в _base_check иначе возвращался бы "skipped").
        validator = RoleArtifactValidator()
        summary = validator.validate(project,
                                       role_ids=("explainer",),
                                       compose_check=True)
        assert summary.base_check_status == "ok"
        # README есть — missing не содержит README.
        assert "README.md" not in summary.base_check_missing

    def test_compose_on_without_readme_fails_base_check(self, tmp_path):
        p = tmp_path / "no_readme"
        p.mkdir()
        (p / "project.yaml").write_text("name: no_readme\ntype: script\n",
                                          encoding="utf-8")
        proj = Project.load(p)
        validator = RoleArtifactValidator()
        summary = validator.validate(proj,
                                       role_ids=("explainer",),
                                       compose_check=True)
        assert summary.base_check_status == "failed"
        assert "README.md" in summary.base_check_missing


# ─── additive: ForgeFacade.validate_role_artifacts delegate ─────────────────


class TestFacadeDelegate:
    def test_facade_validate_returns_validation_summary(self, project):
        facade = ForgeFacade()
        summary = facade.validate_role_artifacts(project,
                                                  role_ids=("explainer",),
                                                  compose_check=False)
        assert isinstance(summary, ValidationSummary)
        assert summary.roles_checked == ("explainer",)

    def test_facade_validate_with_explicit_registry(self, tmp_path, project):
        path = tmp_path / "r.yaml"
        _write_yaml_registry(path, [
            {"id": "lisa", "outputs": ["lisa_report.md"]},
        ])
        _materialize_outputs(project.root, ["lisa_report.md"])

        facade = ForgeFacade()
        summary = facade.validate_role_artifacts(
            project, role_ids=("lisa",), compose_check=False,
            registry_path=path,
        )
        assert summary.registry_status == "loaded"
        lisa_rprt = summary.role_reports[0]
        assert lisa_rprt.status == "ok"


# ─── additive invariant: existing modules untouched ────────────────────────


class TestAdditiveInvariant:
    """CON-16/CON-21/промт 68: forge_facade НЕ модифицирует другие модули."""

    def test_workspace_untouched_by_new_methods(self):
        import core_02.workspace as mod
        src = open(mod.__file__, encoding="utf-8").read()
        assert "RoleArtifactValidator" not in src
        assert "RoleArtifactReport" not in src

    def test_forge_pipeline_untouched_by_new_methods(self):
        import core_02.forge_pipeline as mod
        src = open(mod.__file__, encoding="utf-8").read()
        assert "RoleArtifactValidator" not in src
        assert "RoleArtifactReport" not in src

    def test_forge_registry_untouched_by_new_methods(self):
        import core_02.forge_registry as mod
        src = open(mod.__file__, encoding="utf-8").read()
        assert "RoleArtifactValidator" not in src


# ─── DRY: project_id алгоритм = ForgeRegistry._slug ─────────────────────────


class TestSlugReuse:
    def test_project_id_matches_forge_registry_slug(self, project):
        # project_id в ValidationSummary должен совпадать с ForgeRegistry._slug.
        from core_02.forge_registry import ForgeRegistry
        expected = ForgeRegistry._slug(project.name)
        validator = RoleArtifactValidator()
        summary = validator.validate(project,
                                       role_ids=("explainer",),
                                       compose_check=False)
        assert summary.project_id == expected

    def test_project_id_handles_non_alnum_chars(self, tmp_path):
        # "my-web app!" → "my-web-app-" → strip → "my-web-app".
        from core_02.forge_registry import ForgeRegistry
        p = tmp_path / "my-web app!"
        p.mkdir()
        (p / "project.yaml").write_text("name: my-web app!\ntype: script\n",
                                          encoding="utf-8")
        (p / "README.md").write_text("# X\n", encoding="utf-8")
        proj = Project.load(p)
        validator = RoleArtifactValidator()
        summary = validator.validate(proj, role_ids=("explainer",),
                                       compose_check=False)
        expected = ForgeRegistry._slug("my-web app!")
        assert summary.project_id == expected
        assert summary.project_id == "my-web-app"
