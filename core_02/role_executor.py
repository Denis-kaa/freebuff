"""core_02/role_executor.py — RoleExecutorRegistry: автоисполнение LIGHT-ролей.

ADR-016 (docs_10/engineering-memory/decisions/ADR_016_Role_Executor_Auto_Chain_Generation.md):
закрывает разрыв «LIGHT-роли = check_only» — добавляет аддитивный слой
генераторов ``role_id → executor``, отдельный от Scenario (Scenario = корпус
данных, §7.3 не нарушается). ForgeFacade.run_chain в режиме
``light_mode="generate"`` обращается сюда за исполнителем недостающего артефакта.

Первый вертикальный срез — детерминированные роли:
  - ``lisa`` → :class:`LisaExecutor` (обёртка scripts_01/lisa_estimator.py).

LLM-роли (explainer / risk / decomposer / architect / auditor / documenter) —
следующий этап (вызов модели по blueprint-промпту роли).

Безопасность: executor НЕ вызывает Forge напрямую (§7.3) — только генерирует
файлы в ``project.root``; без eval/exec/shell. Fail-safe: любой сбой генерации
→ пустой список созданных файлов (chain пометит ``gen_failed``), НЕ exception
наружу из execute().
"""

from __future__ import annotations

import fnmatch
import logging
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional

from core_02.workspace import Project

if TYPE_CHECKING:  # только для аннотаций — runtime-импорт ленивый
    from core_02.blueprint_v3 import BlueprintCorpus
    from scripts_01.model_gateway import ModelGateway

__all__ = [
    "BaseRoleExecutor",
    "RoleExecutorRegistry",
    "LisaExecutor",
    "LlmRoleExecutor",
    "default_executor_registry",
    "llm_executor_registry",
    "LLM_ROLE_IDS",
]

logger = logging.getLogger(__name__)


class BaseRoleExecutor(ABC):
    """Генератор артефактов одной LIGHT-роли (role_id → executor, ADR-016).

    Интерфейс: ``execute(project, role_id, **kwargs) -> list[str]`` — список
    созданных файлов (relative paths от ``project.root``). Executor НЕ вызывает
    Forge напрямую (§7.3) и НЕ мутирует Project-контейнер (только файлы).
    """

    #: role_id, за который отвечает executor (должен совпадать с registry.yaml).
    role_id: str = ""

    @abstractmethod
    def execute(self, project: Project, role_id: str, **kwargs) -> List[str]:
        """Сгенерировать артефакты роли. Возвращает relative-пути созданных файлов.

        Fail-safe: сбой → ``[]`` (пустой список), НЕ exception наружу.
        """
        raise NotImplementedError


class RoleExecutorRegistry:
    """Реестр ``role_id → BaseRoleExecutor`` (аддитивный слой, ADR-016).

    Отдельный от Scenario: Scenario = корпус данных (блюпринты), этот реестр =
    генераторы. ``role_ids()`` / ``__contains__`` / ``__len__`` — для
    интроспекции и тестов.
    """

    def __init__(
        self, executors: Optional[List[BaseRoleExecutor]] = None
    ) -> None:
        self._executors: Dict[str, BaseRoleExecutor] = {}
        for ex in executors or []:
            self.register(ex)

    def register(self, executor: BaseRoleExecutor) -> None:
        """Зарегистрировать executor под его ``role_id`` (перезапись при дубле)."""
        if not executor.role_id:
            raise ValueError("executor без role_id нельзя регистрировать")
        self._executors[executor.role_id] = executor

    def get(self, role_id: str) -> Optional[BaseRoleExecutor]:
        """Executor для роли (None, если не зарегистрирован)."""
        return self._executors.get(role_id)

    def role_ids(self) -> List[str]:
        """Все зарегистрированные role_id (в порядке регистрации)."""
        return list(self._executors)

    def __len__(self) -> int:
        return len(self._executors)

    def __contains__(self, role_id: str) -> bool:
        return role_id in self._executors


class LisaExecutor(BaseRoleExecutor):
    """Детерминированный генератор ``lisa_report.md`` (обёртка lisa_estimator).

    Описание проекта собирается из первых доступных входных файлов (порядок
    приоритета: brief.md → parsed_requirements.md → promt1.md → README.md),
    fallback — ``project.name``. Затем ``scripts_01.lisa_estimator.lisa_estimator``
    пишет ``lisa_report.md`` в ``project.root`` (save=True).

    Выход: ``["lisa_report.md"]`` если файл создан, иначе ``[]``.
    """

    role_id = "lisa"

    # Порядок приоритета входных файлов для сбора описания проекта.
    INPUT_CANDIDATES: tuple[str, ...] = (
        "brief.md",
        "parsed_requirements.md",
        "promt1.md",
        "README.md",
    )

    def execute(self, project: Project, role_id: str, **kwargs) -> List[str]:
        description = self._gather_description(project)
        out = project.root / "lisa_report.md"
        try:
            from scripts_01.lisa_estimator import lisa_estimator

            lisa_estimator(description, out=str(out), save=True)
        except Exception:
            # fail-safe: сбой генерации → пустой список (chain пометит gen_failed).
            return []
        return ["lisa_report.md"] if out.is_file() else []

    def _gather_description(self, project: Project) -> str:
        """Собрать описание проекта из входных файлов (fallback — project.name)."""
        for name in self.INPUT_CANDIDATES:
            p = project.root / name
            if p.is_file():
                try:
                    text = p.read_text(encoding="utf-8").strip()
                except OSError:
                    continue
                if text:
                    return text
        return project.name or ""


def default_executor_registry() -> RoleExecutorRegistry:
    """Собрать реестр детерминированных executor'ов (первый срез ADR-016)."""
    return RoleExecutorRegistry([LisaExecutor()])


# ═══════════════════════════════════════════════════════════════════
# LLM-экзекьютор (ADR-016, этап 2): роль → вызов модели по blueprint-промпту
# ═══════════════════════════════════════════════════════════════════
#
# Один LLM-вызов на роль. Промпт собирается из Blueprint (system_role,
# main_objective, output_format) + контекст проекта (существующие артефакты).
# Ответ модели — file-block протокол (по блоку на каждый output-файл):
#
#     @@FILE:brief.md
#     <содержимое>
#     @@ENDFILE
#
# Безопасность: блоки вне expected_outputs и небезопасные пути (../, absolute)
# отбрасываются; executor НЕ вызывает Forge напрямую (§7.3); fail-safe → [].

# Роли, для которых есть LLM-экзекьютор (все LIGHT кроме детерминированной lisa).
LLM_ROLE_IDS: tuple[str, ...] = (
    "explainer", "risk", "decomposer", "architect", "auditor", "documenter",
)

# Входные артефакты для сбора контекста каждой LLM-роли (по dependencies
# registry.yaml). Читаются безопасно: отсутствующие игнорируются.
LLM_ROLE_INPUTS: Dict[str, tuple[str, ...]] = {
    "explainer": ("promt1.md", "задача.md", "task.md", "README.md"),
    "risk": ("brief.md", "parsed_requirements.md", "lisa_report.md"),
    "decomposer": (
        "parsed_requirements.md", "lisa_report.md", "risk_matrix.md",
    ),
    "architect": (
        "decomposition.md", "module_list.md", "integration_topology.md",
        "risk_matrix.md",
    ),
    "auditor": (
        "architecture.md", "contracts.yaml", "decomposition.md", "module_list.md",
    ),
    # NOTE: README.md НЕ включаем — это собственный output documenter'а
    # (self-referential input на повторном прогоне частично сгенерированного проекта).
    "documenter": (
        "brief.md", "parsed_requirements.md", "architecture.md", "contracts.yaml",
        "audit_report.md",
    ),
}

# Максимум символов одного входного файла в контексте (защита от раздувания промпта).
_CONTEXT_FILE_CAP: int = 8000

# File-block протокол: @@FILE:name + содержимое + @@ENDFILE (DOTALL, non-greedy).
_FILE_BLOCK_RE = re.compile(
    r"@@FILE:\s*([^\n]+?)\s*\n(.*?)\n@@ENDFILE",
    re.DOTALL,
)


def _is_safe_filename(name: str) -> bool:
    """Отклонить absolute/~/.. пути и пустые сегменты (path-traversal guard)."""
    if not name or name.startswith(("/", "\\", "~")):
        return False
    parts = name.replace("\\", "/").split("/")
    return not any(p in ("", ".", "..") for p in parts)


def _is_allowed_output(name: str, expected: tuple[str, ...]) -> bool:
    """Файл допустим, если совпадает с одним из expected_outputs (fnmatch)."""
    return any(fnmatch.fnmatch(name, pat) for pat in expected)


class LlmRoleExecutor(BaseRoleExecutor):
    """LLM-экзекьютор LIGHT-роли: модель по blueprint-промпту → артефакты.

    Один вызов ``ModelGateway.generate_by_capabilities`` на роль; capabilities
    берутся из ``corpus.routing_hint(role_id)``. Ответ парсится по file-block
    протоколу; блоки вне expected_outputs и небезопасные пути отбрасываются.

    Fail-safe: любая ошибка (модель недоступна, пустой ответ, битый blueprint) →
    ``[]`` (chain пометит gen_failed), НЕ exception наружу.

    Тестируемость: ``gateway`` и ``corpus`` внедряются через конструктор
    (fake-объекты в тестах, без сети и без monkeypatch).
    """

    def __init__(
        self,
        role_id: str,
        expected_outputs: tuple[str, ...],
        gateway: Optional["ModelGateway"] = None,
        corpus: Optional["BlueprintCorpus"] = None,
    ) -> None:
        self.role_id = role_id
        self.expected_outputs = tuple(expected_outputs)
        self._gateway = gateway
        self._corpus = corpus

    def execute(self, project: Project, role_id: str, **kwargs) -> List[str]:
        try:
            corpus = self._resolve_corpus()
            gateway = self._resolve_gateway()
            bp = corpus.load_blueprint(self.role_id)
            capabilities = corpus.routing_hint(self.role_id) or ["summarize"]
            system = self._build_system_prompt(bp)
            user = self._build_user_prompt(bp, self._gather_context(project))
            response = gateway.generate_by_capabilities(
                capabilities=capabilities,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return self._parse_and_save(project, response.content)
        except Exception as exc:  # noqa: BLE001 — fail-safe по дизайну
            logger.warning("LlmRoleExecutor(%s) failed: %s", self.role_id, exc)
            return []

    # ── dependency resolution (lazy, тестируемо через DI) ────────────────

    def _resolve_gateway(self) -> "ModelGateway":
        if self._gateway is not None:
            return self._gateway
        from scripts_01.model_gateway import ModelGateway
        return ModelGateway()

    def _resolve_corpus(self) -> "BlueprintCorpus":
        if self._corpus is not None:
            return self._corpus
        from core_02.blueprint_v3 import BlueprintCorpus
        return BlueprintCorpus()

    # ── prompt building ──────────────────────────────────────────────────

    @staticmethod
    def _build_system_prompt(bp) -> str:
        parts: List[str] = []
        for key in ("role", "system_role", "implementation_scope_rules"):
            val = bp.sections.get(key, "").strip()
            if val:
                parts.append(val)
        return "\n\n".join(parts) if parts else bp.sections.get("role", "")

    def _build_user_prompt(self, bp, context: str) -> str:
        parts: List[str] = []
        objective = bp.sections.get("main_objective", "").strip()
        if objective:
            parts.append(f"ЦЕЛЬ:\n{objective}")
        fmt = bp.sections.get("output_format", "").strip()
        if fmt:
            parts.append(f"ФОРМАТ ВЫХОДА:\n{fmt}")
        files = "\n".join(f"- {o}" for o in self.expected_outputs)
        parts.append(
            "ВЫВОДИ СТРОГО В ФОРМАТЕ ФАЙЛОВЫХ БЛОКОВ (по одному на файл):\n"
            "@@FILE:<имя_файла>\n<содержимое>\n@@ENDFILE\n"
            f"Требуемые файлы:\n{files}"
        )
        if context:
            parts.append(f"=== КОНТЕКСТ ПРОЕКТА ===\n{context}")
        return "\n\n".join(parts)

    # ── context gathering ────────────────────────────────────────────────

    def _gather_context(self, project: Project) -> str:
        candidates = LLM_ROLE_INPUTS.get(self.role_id, ())
        chunks: List[str] = []
        for name in candidates:
            p = project.root / name
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8").strip()
            except OSError:
                continue
            if not text:
                continue
            if len(text) > _CONTEXT_FILE_CAP:
                text = text[:_CONTEXT_FILE_CAP] + "\n...(truncated)"
            chunks.append(f"--- {name} ---\n{text}")
        if not chunks:
            chunks.append(f"--- project ---\n{project.name}")
        return "\n\n".join(chunks)

    # ── parse & save ─────────────────────────────────────────────────────

    def _parse_and_save(self, project: Project, text: str) -> List[str]:
        created: List[str] = []
        blocks = _FILE_BLOCK_RE.findall(text or "")
        for name, content in blocks:
            name = name.strip()
            content = content.strip()
            if not _is_safe_filename(name):
                logger.warning(
                    "LlmRoleExecutor(%s): отброшен небезопасный путь %r",
                    self.role_id, name,
                )
                continue
            if not _is_allowed_output(name, self.expected_outputs):
                logger.warning(
                    "LlmRoleExecutor(%s): отброшен файл %r вне expected_outputs",
                    self.role_id, name,
                )
                continue
            target = project.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content + "\n", encoding="utf-8")
            created.append(name)

        # Fallback: модель проигнорировала file-block, но роли нужен ровно один
        # конкретный output — пишем весь ответ в него (robustness к реальным LLM).
        if not blocks and text and text.strip():
            concrete = [
                o for o in self.expected_outputs
                if not any(ch in o for ch in "*?[")
            ]
            if len(concrete) == 1 and _is_safe_filename(concrete[0]):
                target = project.root / concrete[0]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text.strip() + "\n", encoding="utf-8")
                created.append(concrete[0])
        return created


def llm_executor_registry(
    gateway: Optional["ModelGateway"] = None,
    corpus: Optional["BlueprintCorpus"] = None,
) -> RoleExecutorRegistry:
    """Полный реестр: детерминированный LisaExecutor + 6 LLM-экзекьюторов.

    Lazy import DEFAULT_ROLE_OUTPUTS (из forge_facade) — единственный источник
    истины для output-паттернов ролей; на module-load избегаем circular import
    (forge_facade импортирует role_executor сверху).
    """
    from core_02.forge_facade import DEFAULT_ROLE_OUTPUTS

    reg = default_executor_registry()
    for role_id in LLM_ROLE_IDS:
        outputs = tuple(DEFAULT_ROLE_OUTPUTS.get(role_id, ()))
        if not outputs:
            continue
        reg.register(LlmRoleExecutor(
            role_id=role_id,
            expected_outputs=outputs,
            gateway=gateway,
            corpus=corpus,
        ))
    return reg
