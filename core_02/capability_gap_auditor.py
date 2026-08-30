"""core_02/capability_gap_auditor.py — Capability Gap Auditor (registry-first).

ADR-016 (auto-generation of light-role artifacts): этот модуль добавляет
детерминированный ``BaseRoleExecutor`` с ``role_id='capability_gap_auditor'``,
который решает задачу «перед стартом новой нетривиальной задачи — сказать,
каких платформенных сущностей не хватает и как их зарегистрировать».

Контракт (согласован с README v1 thinker'а):

1. **No side-effects on global state.** Executor НЕ вызывает
   ``MissingRegistry.register_missing()`` напрямую (§7.3 Wizard↔Forge
   orthogonal-stateboundary; защита от silent global mutation). Вместо этого
   он пишет paste-friendly bash-блок с командами ``python -m core_02.missing_registry register ...``,
   который оператор запускает вручную.
2. **Deterministic v1.** Парсинг markdown-секций + keyword/regex-матч по
   курируемой таксономии (TAXONOMY). Никакого LLM в v1 — тестируется in-memory
   без сети и без фейков модели. LLM-вариант (``CapabilityGapLlmExecutor``,
   ``kind='llm'``) — следующая итерация, см. TODO в конце файла.
3. **DI registry.** ``MissingRegistry`` инжектится через ``__init__``; по
   умолчанию загружается из канонического пути ``data_13/missing_registry.yaml``.
   Тесты подменяют registry на in-memory fixture без диска.
4. **Fail-safe per ADR-016.** Любая ошибка (нет входного файла, битый MR,
   исключение внутри) → ``[]`` (chain пометит ``gen_failed``), НЕ exception
   наружу.
5. **Прозрачный tagging.** Каждое утверждение в отчёте явно отмечено как
   ``[observation]`` (regex+MR lookup, детерминировано) или ``[conclusion]``
   (first-slice рекомендация, требует ручной валидации) — соблюдение §24
   Code Quality Standard.

Использование::

    from core_02.capability_gap_auditor import CapabilityGapAuditorExecutor
    from core_02.missing_registry import MissingRegistry

    auditor = CapabilityGapAuditorExecutor(registry=MissingRegistry())
    created = auditor.execute(project, "capability_gap_auditor")
    # -> ["capability_gap_report.md"]

CLI::

    python -m core_02.capability_gap_auditor audit <project_root>
    python -m core_02.capability_gap_auditor audit <project_root> \\
        --registry /tmp/alt_registry.yaml
    python -m core_02.capability_gap_auditor audit <project_root> --json
"""

from __future__ import annotations

import json
import logging
}
import shlex
import sys
}
from typing import Any, Dict, List, Optional, Tuple

from core_02.role_executor import BaseRoleExecutor, RoleExecutorRegistry
from core_02.workspace import Project

# Lazy / type-checked импорт MissingRegistry: опциональный по умолчанию, чтобы
# unit-тесты без канонического data_13/missing_registry.yaml не падали на импорте.
try:
    from core_02.missing_registry import MissingRegistry
    _MissingRegistryCls: Optional[type] = MissingRegistry
except ImportError:  # pragma: no cover — defensive
    _MissingRegistryCls = None  # type: ignore[assignment]


# ══════════════════════════════════════════════════════════════════════
# Public API surface (используется ``from module import *``)
# ══════════════════════════════════════════════════════════════════════
__all__ = [
    "CapabilityGapAuditorExecutor",
    "CapabilityGapLlmExecutor",
    "CapabilityGapReporter",
    "TAXONOMY",
    "capability_audit_executor_registry",
    "capability_audit_llm_executor_registry",
    "main",
    "DEFAULT_TASK_CANDIDATES",
    "REPORT_FILE",
    "LLM_REPORT_FILE",
    "LLM_ROLE_ID",
    "LLM_SYSTEM_PROMPT",
    "LLM_USER_PROMPT_TEMPLATE",
    "_parse_llm_response",
]

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Курируемая таксономия: regex → (item_id, kind, factory, description)
# ════════════════════════════════════════════════════════════════════════
# v1: in-code constant. v2 TODO: вынести в data_13/capability_taxonomy.yaml,
# чтобы курировать без правки кода (planned post-v5.189.5x).
#
# Каждое совпадение добавляет ОДНУ capability в gap-отчёт. Совпадения
# объединяются по item_id (regex может сработать несколько раз — отчёт
# остаётся компактным).

# Тип: (compiled regex, item_id, kind, factory, description)
_TaxonomyEntry = Tuple[re.Pattern[str], str, str, str, str]


# ══════════════════════════════════════════════════════════════════════
# Закрытое множество KINDS для LLM-парсера (ANTI-6b vocabulary defense)
# ══════════════════════════════════════════════════════════════════════
# v1: in-code frozenset (mirrors MissingRegistry.KINDS). Парсер молча отбрасывает
# записи с kind вне этого множества, иначе — silent drift на registry cross-check
# (LLM может вернуть kind="service"/"agent"/"skill", а в MR они не зарегистрированы).
# Синхронизирован с MissingRegistry.KINDS (требует ревью при изменении того файла).
_KINDS: frozenset = frozenset({"tool", "module", "role", "engine"})


TAXONOMY: tuple[_TaxonomyEntry, ...] = (
    # research_web: web-исследование, чтение URL
    (re.compile(r"(?i)\b(web[- )?research|читать\s+url|url\s+research|external\s+url|web\s+page|scrape)\b"),
     "research_web", "tool", "research",
     "Web Research — корпус URL-источников (веб-чтение, поиск, источник-трекинг)"),

    # lisa_estimator + unit economics (отдельные item_id'ы — оба блокеры в EdTech)
    (re.compile(r"(?i)\b(unit\s+economics|teacher\s+time|contribution\s+margin|calibration)\b"),
     "lisa_estimator", "tool", "research",
     "Estimation / Unit-economics для creator-economy (Teacher Time/$, калибровка)"),

    # qualitative_review_analyzer: отзывы, qualitative
    (re.compile(r"(?i)\b(review|отзыв|qualitative)\b\s*(?i:analys|кластер|pain[- )?point)?"),
     "qualitative_review_analyzer", "tool", "research",
     "Качественный анализ отзывов (pain-points / churn / praise кластеризация)"),

    # competitor_matrix_builder
    (re.compile(r"(?i)\b(конкурент|competitor)\b\s*(?i:анализ|матрица|карта|landscape)?"),
     "competitor_matrix_builder", "tool", "research",
     "Конкурентная матрица (плюсы/минусы/копировать/не копировать)"),

    # pricing_enumerator
    (re.compile(r"(?i)\b(pric|цен)\w*\b\s*(?i:enumerat|скан|vali|verif|find|real)?"),
     "pricing_enumerator", "tool", "research",
     "Верифицированный прайс-сканер (реальный price, не «примерно 10–20 тыс.»)"),

    # anti_pattern_miner
    (re.compile(r"(?i)\b(anti[- )?pattern|заброш\w*|закрыт\w*)\s+(курс|школ|проект|launch|product)?"),
     "anti_pattern_miner", "tool", "research",
     "Anti-pattern mining (закрытые курсы/школы/заброшенные продукты)"),

    # mvp_design_wizard
    (re.compile(r"(?i)\b(mvp\s+(design|experiment|механик)|предпродаж|пилотн\w*\s+групп)"),
     "mvp_design_wizard", "module", "doc",
     "MVP-механики (предпродажа, пилот, диагностическая воронка)"),

    # business_model_constructor
    (re.compile(r"(?i)\b(business\s+model|бизнес[- )модел|монетизаци\w*|14[- )полей\s+конструкци)"),
     "business_model_constructor", "module", "doc",
     "Конструктор бизнес-моделей (14 полей, валидированный шаблон)"),

    # hypothesis_ledger
    (re.compile(r"(?i)\b(hypothesis\s+ledger|гипотез\w*\s+(статус|ledger)|kill[- )?criteria)"),
     "hypothesis_ledger", "module", "docs_10",
     "Hypothesis ledger (статусы open/supported/refuted/kill-criteria-met)"),

    # devil_advocate_pass
    (re.compile(r"(?i)\b(adversarial|devil.?s\s+advocate|kill.?question|опроверж\w*|честн\w*\s+ответ)"),
     "devil_advocate_pass", "module", "thinker",
     "Adversarial review (3 kill-questions в конце, anti-confirmation-bias)"),

    # corpus_persistence (sources между сессиями)
    (re.compile(r"(?i)\b(corpus|persistence|источник\w*\s+между\s+сесси|сохран\w*\s+url)"),
     "corpus_persistence", "tool", "nil",
     "Corpus-persistence (источники между сессиями, не теряются)"),

    # claim_source_tracker (NOTE: bracketed tags [observation]/[hypothesis]/[conclusion]
    # опущены намеренно — иначе аудит собственного отчёта даёт false-positive, т.к.
    # тело отчёта использует ровно эти метки. Сохраняем `[fact]` (он не используется
    # в отчёте) и русскую фразу «факт/наблюден/гипотез»).
    (re.compile(r"(?i)\b(кажд\w*\s+существенн\w*\s+утвержден\w*\s+подкрепл\w*\s+источник\w*|не\s+выдава\w*\s+предположен\w*\s+за\s+факт\w*|claim\s+source\s+tracker|факт\s*\/\s*наблюден\s*\/\s*гипотез\w*|tag(?:ging)?\w*\s+\[fact\*)|\[fact\*)|\bfact\b\s*\/\s*observation|\[hypothesis\*])"),
     "claim_source_tracker", "module", "docs_10",
     "Claim-source-tracker (тег [fact] и формат факт/наблюдение/гипотеза)"),

    # vanity_metric_filter
    (re.compile(r"(?i)\b(vanity\s+metric|лайк\w*\s+не\s+успех|подписч\w*\s+не\s+успех|просмотр\w*\s+не\s+успех)"),
     "vanity_metric_filter", "module", "doc",
     "Vanity-metric filter (что НЕ считать успехом)"),

    # weighted_scoring_engine
    (re.compile(r"(?i)\b(weighted\s+scor|scor\w*\s+модел\w*\s+по\s+критер|взвешенн\w*\s+оцен\w*|8\s+критер\w*\s+×\s+вес)"),
     "weighted_scoring_engine", "tool", "nil",
     "Weighted scoring engine (multi-criteria × weights → итоговый балл)"),

    # persona_funnel_analyzer (фан↔ученик)
    (re.compile(r"(?i)\b(persona\s+funnel|персон\w*\s+воронк|фан\s*\u2194\s*ученик|monetiz\w*\s+reputation)"),
     "persona_funnel_analyzer", "tool", "research",
     "Persona funnel анализ (фан↔ученик конверсия)"),
)


# ════════════════════════════════════════════════════════════════════════
# Section parser (markdown)
# ════════════════════════════════════════════════════════════════════════
# Распознаёт заголовки: `## 1.`, `# 1.`, `## 1)`, `## I.`, `## (1)`, `## 1.1.`.
# Возвращает список (heading, body). heading — текст после маркера `#`.

_SECTION_RE = re.compile(
    r"^(?:#{1,4]\s+|(?:\d+|[IVX]+)\.\s+|\(\d+\)\s+)(.+?)(?:\n|$)",
    re.MULTILINE,
)

# Минимальная длина body, чтобы секция считалась содержательной (>60 символов).
_MIN_BODY_LEN = 60


def _split_sections(text: str) -> List[Tuple[str, str]]:
    """Сплитит markdown на список (heading, body). Если заголовков нет — весь текст как одна секция."""
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        intro = text.strip()
        return [("(intro)", intro)] if intro else []
    out: List[Tuple[str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw_heading = m.group(1).strip().rstrip(":").strip()
        body = text[start:end].strip()
        # Heading = первая строка body без маркера.
        first_nl = body.find("\n")
        first_line = body[:first_nl].strip() if first_nl >= 0 else body
        heading = raw_heading or first_line or f"(section {i+1})"
        out.append((heading, body))
    return out


def _extract_capabilities_from_text(text: str) -> List[Tuple[str, str, str, str]]:
    """Возвращает список найденных (item_id, kind, factory, description) для данного текста.

    Дедуп по item_id (несколько regex могут сработать на один cap — берём первое описание).
    """
    found: Dict[str, Tuple[str, str, str, str]] = {}
    for pattern, item_id, kind, factory, description in TAXONOMY:
        if item_id in found:
            continue
        if pattern.search(text):
            found[item_id] = (item_id, kind, factory, description)
    return list(found.values())


# ════════════════════════════════════════════════════════════════════════
# Reporter (детерминированный Markdown-генератор)
# ════════════════════════════════════════════════════════════════════════

# Приоритет блокеров: ниже rank = блокеровее. Single source of truth (per code-reviewer v2).
# Ранг < _IMPLEMENTED_RANK означает «не реализован» → блокер для first-slice.
_IMPLEMENTED_RANK = 9
_IMPLEMENTED_STATUS = "implemented"
_BLOCKER_PRIORITY: Dict[str, int] = {
    "absent": 0,
    "registered": 1,
    "design_ready": 2,
    "prompt_written": 3,
    "implemented": _IMPLEMENTED_RANK,    # sentinel — не блокер
}

# Set comprehension из _BLOCKER_PRIORITY (single source of truth; dead-consistency loop fix).
_BLOCKER_STATUSES = frozenset(
    status for status, rank in _BLOCKER_PRIORITY.items() if rank < _IMPLEMENTED_RANK
)


class CapabilityGapReporter:
    """Генерирует Markdown-отчёт. DI: registry для cross-check (None = автономный режим).

    ``pre_extracted_entries`` (keyword-only, optional) — если передан ``Dict[item_id, (kind, factory, description)]``,
    ``render()`` пропускает детерминированный ``_extract_capabilities_from_text`` и напрямую
    использует переданный map. Это путь LLM-варианта ``CapabilityGapLlmExecutor`` —
    backward-compatible default ``None`` сохраняет детерминированное поведение.
    """

    def __init__(
        self,
        registry: Optional["MissingRegistry"] = None,
        *,
        pre_extracted_entries: Optional[Dict[str, Tuple[str, str, str]]] = None,
    ) -> None:
        self.registry = registry
        self._pre_extracted_entries = pre_extracted_entries

    def render(self, sections: List[Tuple[str, str]]) -> str:
        # ── 1. Сбор требуемых capabilities по секциям ─────────────────
        per_section: List[Tuple[str, List[Tuple[str, str, str, str]]]] = []
        all_required: Dict[str, Tuple[str, str, str]] = {}  # item_id → (kind, factory, description)

        if self._pre_extracted_entries is not None:
            # LLM-путь: единый плоский список (без per-section breakdown).
            all_required = dict(self._pre_extracted_entries)
            per_section = [(heading, []) for heading, _ in sections]
        else:
            for heading, body in sections:
                entries = _extract_capabilities_from_text(body)
                per_section.append((heading, entries))
                for item_id, kind, factory, description in entries:
                    if item_id not in all_required:
                        all_required[item_id] = (kind, factory, description)

        # ── 2. Рендер структуры отчёта ────────────────────────────────
        lines: List[str] = []
        lines.append("# Capability Gap Audit Report")
        lines.append("")
        lines.append("> Сгенерировано `CapabilityGapAuditorExecutor` (ADR-016, deterministic v1).")
        lines.append("> Вердикт основан на keyword/regex-матче секций задачи против курируемой таксономии.")
        lines.append("> LLM-вариант (более точный вывод, дополнительная стоимость) — `CapabilityGapLlmExecutor`, следующая итерация.")
        lines.append("")
        lines.append(f"**Всего секций проанализировано:** {len(sections)} [observation]")
        lines.append(f"**Уникальных требуемых capabilities:** {len(all_required)} [observation]")
        lines.append(f"**Блокеров (first-slice):** {self._count_blockers(all_required)} [observation]")
        lines.append(f"**Режим registry:** {'injected (DI)' if self.registry is not None else '(автономный, registry=None)'} [observation]")
        lines.append("")

        # ── 3. Сводная таблица ────────────────────────────────────────
        lines.append("## 1. Сводная таблица")
        lines.append("")
        lines.append("| Capability | В MissingRegistry? | Статус | kind | factory | Описание |")
        lines.append("|------------|--------------------|--------|------|---------|----------|")
        sorted_items = sorted(all_required.items(), key=lambda kv: kv[0])
        for item_id, (kind, factory, description) in sorted_items:
            status_label, in_mr = self._lookup(item_id)
            in_label = "да" if in_mr else "нет"
            lines.append(
                f"| `{item_id}` | {in_label} | `{status_label}` | `{kind}` | "
                f"`{factory or '-'}` | {description} |"
            )
        lines.append("")

        # ── 4. Section breakdown OR flat-list (conditional on mode) ─────
        if self._pre_extracted_entries is not None:
            # LLM-путь: единый плоский список (per-section breakdown смысла не имеет,
            # т.к. LLM extracted все capabilities разом из всего текста, а не
            # per-section). Это закрывает BLOCKER v5.189.55-review: было — для всех
            # 17 секций VOCAL_TASK_FRAGMENT печаталось “Не требует новой capability”,
            # дискредитируя весь отчёт.
            lines.append("## 2. LLM-extracted capabilities (flat list)")
            lines.append("")
            lines.append(
                f"- [methodology] Извлечено через `CapabilityGapLlmExecutor` "
                f"(role_id=`{LLM_ROLE_ID}`); единый список из {len(all_required)} capabilities "
                f"(per-section breakdown skip — LLM extracted глобально, не per-section)."
            )
            lines.append("")
            for item_id, (kind, factory, description) in sorted(
                all_required.items(), key=lambda kv: kv[0],
            ):
                status_label, in_mr = self._lookup(item_id)
                if in_mr and status_label == _IMPLEMENTED_STATUS:
                    marker = "\u2705"   # ✅ implemented (valid BMP char)
                    marker_text = "уже реализован"
                elif in_mr:
                    marker = "\u26a0"    # ⚠ in registry, not implemented (valid BMP, no surrogate)
                    marker_text = "в реестре, статус отличен от implemented"
                else:
                    marker = "\u274c"    # ❌ absent (valid BMP char; избегаем surrogate pair)
                    marker_text = "отсутствует в реестре"
                lines.append(
                    f"- {marker} `{item_id}` (kind=`{kind}`, factory=`{factory or '-'}`) — "
                    f"{description} → {marker_text} [{status_label}]"
                )
            lines.append("")
        else:
            # Детерминированный путь: per-section breakdown (original behavior,
            # 22 существующих теста в test_capability_gap_auditor.py остаются зелёными).
            lines.append("## 2. Детализация по секциям")
            lines.append("")
            for heading, entries in per_section:
                display_heading = (heading or "(без заголовка)")[:120]
                if not entries:
                    lines.append(f"### {display_heading}")
                    lines.append("- Не требует новой capability (preamble/quality/conf/Q&A).")
                    lines.append("")
                    continue
                lines.append(f"### {display_heading}")
                for item_id, kind, factory, description in entries:
                    status_label, in_mr = self._lookup(item_id)
                    if in_mr and status_label == _IMPLEMENTED_STATUS:
                        marker = "\u2705"   # ✅ implemented (valid BMP char)
                        marker_text = "уже реализован"
                    elif in_mr:
                        marker = "\u26a0"    # ⚠ in registry, not implemented (valid BMP, no surrogate)
                        marker_text = "в реестре, статус отличен от implemented"
                    else:
                        marker = "\u274c"    # ❌ absent (valid BMP char; избегаем surrogate pair U+D83D+U+DD34)
                        marker_text = "отсутствует в реестре"
                    lines.append(
                        f"- {marker} `{item_id}` (kind=`{kind}`, factory=`{factory or '-'}`) — "
                        f"{description} → {marker_text} [{status_label}]"
                    )
                lines.append("")

        # ── 5. Paste-friendly register-команды ───────────────────────
        lines.append("## 3. Рекомендуемые register-команды")
        lines.append("")
        commands = self._register_commands(all_required)
        if commands:
            lines.append("Скопируйте блок → выполните в `core_02/` → затем сделайте")
            lines.append("`mark-prompt-written` и `mark-implemented` согласно AGENTS.md §5 REGISTER-FIRST.")
            lines.append("")
            lines.append("```bash")
            lines.extend(commands)
            lines.append("```")
            lines.append("")
        else:
            lines.append("Все требуемые capabilities уже есть в MissingRegistry или реализованы.")
            lines.append("Регистрация не требуется — исполняйте исходный промт напрямую. [observation)")
            lines.append("")

        # ── 6. First-slice recommendation ─────────────────────────────
        lines.append("## 4. First-slice (блокеры исполнения)")
        lines.append("")
        lines.append("- [conclusion) Ниже — рекомендуемый порядок реализации недостающих сущностей.")
        lines.append("- Правило: сначала absent (0) → registered (1) → design_ready (2) → prompt_written (3).")
        lines.append("- Первые 3 — **минимально необходимый** набор для запуска исходной задачи.")
        lines.append("- Если среди блокеров есть `corpus_persistence` или `claim_source_tracker` → это особенно критично.")
        lines.append("")
        first_slice = self._first_slice(all_required)
        if first_slice:
            for idx, item_id in enumerate(first_slice, 1):
                kind, factory, description = all_required[item_id]
                status_label, _ = self._lookup(item_id)
                lines.append(f"{idx}. `{item_id}` (kind=`{kind}`, factory=`{factory or '-'}`) — статус: `{status_label}`")
            lines.append("")
            lines.append("После реализации блокеров в порядке 1→2→3, вернитесь к исходному промту.")
        else:
            lines.append("Все блокеры закрыты (или задача требует только уже реализованные capabilities). [observation)")
        lines.append("")

        # ── 7. Дисклеймеры (per §24 Code Quality Standard) ────────────
        lines.append("## 5. Дисклеймеры (per Code Quality Standard §24)")
        lines.append("")
        lines.append("- **Детермин vs LLM:** это детерминированный keyword-анализ по курируемой таксономии. [methodology)")
        lines.append("  LLM-вариант может извлечь больше неочевидных зависимостей, но требует подключённой модели и стоимости.")
        lines.append("- **Tagging:** каждое утверждение явно отмечено `[observation)`/`[conclusion]`/`[methodology]`")
        lines.append("  (закрывает ANTI-6b/vocabulary defense + §24 «факт/наблюдение/вывод/гипотеза»).")
        lines.append("- **No side-effects:** этот executor НЕ вызывает `MissingRegistry.register_missing()` напрямую.")
        lines.append("  Все команды — paste-friendly для оператора; регистрация остаётся человеку или supervised-агенту.")
        lines.append("- **Audit trail:** отчёт — `capability_gap_report.md` в `project.root` (logged via `execute() -> List[str)`).")
        lines.append("- **Testability:** таксономия детерминирована, тесты инжектят `MissingRegistry` через конструктор — без сети и диска.")
        lines.append("")
        return "\n".join(lines)

    # ── helpers ─────────────────────────────────────────────────────────

    def _lookup(self, item_id: str) -> Tuple[str, bool]:
        """Возвращает (status_label, in_mr). Если registry=None — ('(registry=None)', False)."""
        if self.registry is None:
            return ("(registry=None)", False)
        try:
            item = self.registry.get(item_id)
        except Exception:  # noqa: BLE001 — fail-safe
            return ("(lookup-error)", False)
        if item is None:
            return ("absent", False)
        return (str(item.status), True)

    def _register_command(
        self, item_id: str, kind: str, factory: str, description: str,
    ) -> str:
        """Сгенерировать одну строку CLI для register.

        NOTE: фильтрация «уже реализован» выполняется централизованно в
        ``_register_commands`` (через ``continue``); здесь — только форматирование.
        Защита от dead-branch удалена в v1 (per code-reviewer review).
        """
        if not item_id or not kind:
            return f"# SKIP: invalid entry {item_id!r}/{kind!r}"
        # Безопасное shell-quoting (защита от injection в description).
        desc_quoted = shlex.quote(description or item_id)
        cmd = (
            f"python -m core_02.missing_registry register {shlex.quote(item_id)} "
            f"--kind {shlex.quote(kind)}"
        )
        if factory:
            cmd += f" --factory {shlex.quote(factory)}"
        cmd += f" --description {desc_quoted}"
        return cmd

    def _register_commands(self, all_required: Dict[str, Tuple[str, str, str]]) -> List[str]:
        out: List[str] = []
        for item_id, (kind, factory, description) in sorted(all_required.items()):
            status_label, in_mr = self._lookup(item_id)
            if in_mr and status_label == _IMPLEMENTED_STATUS:
                continue  # уже реализован — не дублируем
            out.append(self._register_command(item_id, kind, factory, description))
        return out

    def _first_slice(self, all_required: Dict[str, Tuple[str, str, str]]) -> List[str]:
        candidates: List[Tuple[int, str]] = []
        for item_id in all_required:
            status_label, _ = self._lookup(item_id)
            rank = _BLOCKER_PRIORITY.get(status_label, _IMPLEMENTED_RANK)
            if rank < _IMPLEMENTED_RANK:   # magic-number fix (per code-reviewer v2)
                candidates.append((rank, item_id))
        candidates.sort(key=lambda t: (t[0], t[1]))
        return [item_id for _, item_id in candidates[:3]]

    def _count_blockers(self, all_required: Dict[str, Tuple[str, str, str]]) -> int:
        return sum(
            1
            for item_id in all_required
            if (self._lookup(item_id)[0] in _BLOCKER_STATUSES)
        )


# ════════════════════════════════════════════════════════════════════════
# Executor (BaseRoleExecutor)
# ════════════════════════════════════════════════════════════════════════


# Кандидаты входных файлов (по приоритету — первый существующий + непустой).
DEFAULT_TASK_CANDIDATES: tuple[str, ...] = (
    "задача.md",
    "task.md",
    "promt1.md",
    "brief.md",
    "README.md",
)


REPORT_FILE = "capability_gap_report.md"


class CapabilityGapAuditorExecutor(BaseRoleExecutor):
    """Детерминированный ``BaseRoleExecutor`` под ``role_id='capability_gap_auditor'``.

    Читает task-файл из ``project.root`` (по ``DEFAULT_TASK_CANDIDATES``),
    парсит секции, генерирует ``capability_gap_report.md`` со сводкой по
    платформенным capability, paste-friendly bash-блоком для
    ``missing_registry register`` и first-slice рекомендацией.

    ADR-016 fail-safe: любое исключение → ``[]``.
    """

    role_id = "capability_gap_auditor"

    def __init__(self, registry: Optional["MissingRegistry"] = None) -> None:
        self._registry = registry  # DI для тестов (in-memory fixture без диска)

    def execute(self, project: Project, role_id: str, **kwargs) -> List[str]:
        """Генерирует capability_gap_report.md. Возвращает [REPORT_FILE] или [] (fail-safe)."""
        try:
            text = self._read_task(project)
            if text is None:
                logger.info(
                    "CapabilityGapAuditorExecutor: нет task-файла в %s "
                    "(кандидаты: %s) — отчёт не сгенерирован",
                    project.root, DEFAULT_TASK_CANDIDATES,
                )
                return []
            if len(text.strip()) < _MIN_BODY_LEN:
                logger.info(
                    "CapabilityGapAuditorExecutor: task-файл найден, но слишком короткий (<%d)",
                    _MIN_BODY_LEN,
                )
                return []
            sections = _split_sections(text)
            if not sections:
                return []
            reporter = CapabilityGapReporter(registry=self._registry)
            report_md = reporter.render(sections)
            # Записываем в project.root, не трогая project-контейнер (ADR-016).
            out = project.root / REPORT_FILE
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report_md + "\n", encoding="utf-8")
            return [REPORT_FILE] if out.is_file() else []
        except Exception as exc:  # noqa: BLE001 — ADR-016 fail-safe
            logger.warning("CapabilityGapAuditorExecutor failed: %s", exc)
            return []

    # ── входной файл (по приоритету) ──────────────────────────────────

    def _read_task(self, project: Project) -> Optional[str]:
        for name in DEFAULT_TASK_CANDIDATES:
            # glob-match для «promtNN.md» / «pompts_11/promt*.md»: первый существующий.
            if "promt" in name and "*" not in name:
                # попробуем общий glob: «promt*.md» в корне и в pompts_11/
                }
                    project.root.glob("promt*.md"),
                    project.root.glob("pomts_11/promt*.md"),
                }
                for pat in patterns:
                    candidates = sorted(pat)
                    for c in candidates:
                        txt = self._safe_read(c)
                        if txt:
                            return txt
                continue
            p = project.root / name
            txt = self._safe_read(p)
            if txt:
                return txt
        return None

    @staticmethod
    def _safe_read(p: Path) -> Optional[str]:
        if not p.is_file():
            return None
        try:
            text = p.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return text or None


# ════════════════════════════════════════════════════════════════════════
# Public registry factory (для интеграции с ForgeFacade.run_chain)
# ════════════════════════════════════════════════════════════════════════


def capability_audit_executor_registry(
    registry: Optional["MissingRegistry"] = None,
) -> RoleExecutorRegistry:
    """Возвращает ``RoleExecutorRegistry`` с одним ``CapabilityGapAuditorExecutor``.

    Подключается к ``ForgeFacade.run_chain(light_mode='generate')`` через
    параметр ``executor_registry`` (ADR-016) — тогда MISSING-стадия
    ``capability_gap_auditor`` материализуется автоматически.
    """
    return RoleExecutorRegistry([CapabilityGapAuditorExecutor(registry=registry)])


# ══════════════════════════════════════════════════════════════════════
# LLM-вариант: CapabilityGapLlmExecutor (дополняет детерминированный)
# ══════════════════════════════════════════════════════════════════════
#
# TODO v1 → v2: для `execute()` фактически не обязательно иметь DI gardener;
# достаточно ModelGateway с методом ``generate_by_capabilities(cap_list, messages)``.
#
# Использование:
#
#     from core_02.capability_gap_auditor import CapabilityGapLlmExecutor
#
#     gw = build_gateway()  # любая ModelGateway-совместимая обёртка
#     executor = CapabilityGapLlmExecutor(gateway=gw)
#     created = executor.execute(project, "capability_gap_auditor_llm")
#     # -> ["capability_gap_report_llm.md"]
#
# Качественный баръер (per user): тот же VOCAL_TASK_FRAGMENT должен дать ≥18 capabilities
# vs 15 у детерминированного — т.е. LLM находит +3+ неочевидные (meta-skills, infra,
# anti-patterns). Парсер валидирует и тихо отбрасывает неполные элементы (ADR-016).

LLM_REPORT_FILE = "capability_gap_report_llm.md"

# ANTI-6b vocabulary defense: magic numbers извлекаем в константы (so future tuning is
# one-line, не scattered). Top-K для corpus context hint: достаточно 5 для hint
# (больше = prompt bloat, меньше = слабый signal).
_CORPUS_CONTEXT_TOP_K = 5
LLM_ROLE_ID = "capability_gap_auditor_llm"

LLM_SYSTEM_PROMPT = """\
Ты — expert платформенный архитектор (Workspace OS, AGENTS.md §5 REGISTER-FIRST).
Твоя задача — проанализировать входной текст задачи и выдать JSON-массив ТРЕБУЕМЫХ
платформенных capabilities для её выполнения. Каждый элемент — словарь с полями:

  - item_id: snake_case id (например, "corpus_persistence", "weighted_scoring_engine")
  - kind: "tool" | "module" | "role" | "engine" (закрытое множество — MissingRegistry.KINDS)
  - factory: "research" | "doc" | "governance" | "code" | "" (пустая строка если N/A)
  - description: 1 предложение, что именно делает сущность (≤200 символов)
  - confidence: 0.0–1.0 (насколько уверен, что нужна для ДАННОЙ задачи)
  - explicit: true если concept прямо упомянут в задаче, false если выведен неявно

Включай как EXPLICIT capabilities (прямо упомянутые в тексте), так и INFERRED
(мета-инструменты, инфраструктура, аудит-инструменты, anti-patternы, hypothesis/ledger
инструменты) — именно INFERRED обычно даёт +3..+5 к количеству найденного vs
keyword-only парсера. НЕ выдумывай ради количества — только логически нужные.

Игнорируй: собственные имена проекта, команды shell, UI-цвета, формулировки
про окружение (Termux/Android), action-глаголы ("сделать", "проверить").

Верни ТОЛЬКО JSON-массив, обёрнутый в ```json ... ```. Без пояснений вне блока.
"""

LLM_USER_PROMPT_TEMPLATE = """\
Ниже — текст задачи. Выдай JSON-массив требуемых платформенных capabilities.

=== TASK START ===
{task_text}
=== TASK END ===

Требования к выходу:
- Минимум 18 элементов (до 30+ для сложных задач; не выдумывай ради количества).
- Каждый item уникален по item_id (дедупликация внутри массива).
- explicit=true ТОЛЬКО если concept прямо упомянут в тексте задачи.
- Если не уверен в нужности — confidence < 0.7, но всё равно включай
  (false negative блокирует выполнение, false positive только раздувает отчёт).
- Верни ТОЛЬКО ```json [...] ``` блок, ничего вне.
"""


def _parse_llm_response(content: str) -> List[Dict[str, Any]]:
    """Извлекает JSON-массив capabilities из ответа LLM.

    Стратегия (per thinker design v5.189.55):

    1. Ищем fenced ````json ...`````` блок (re.DOTALL для многострочных массивов).
    2. Fallback: первое вхождение ``[`` ... последнее ``]``.
    3. Парсим через ``json.loads``.
    4. Валидация: item должен содержать ``item_id``/``kind``/``description``.
       Невалидные тихо отбрасываются (ADR-016 fail-safe: 1 bad item не валит batch).
    5. Возвращает ``List[Dict]`` (Reporter.render-convertible). Пустой список при любой ошибке.
    """
    if not content or not isinstance(content, str):
        return []
    fenced = re.search(r"```json\s*(\[.*?\*))\s*```", content, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        bracket_start = content.find("[")
        bracket_end = content.rfind(")")
        if bracket_start < 0 or bracket_end <= bracket_start:
            return []
        candidate = content[bracket_start:bracket_end + 1]
    try:
        data = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        item_id = item.get("item_id")
        kind = item.get("kind")
        description = item.get("description")
        if not (
            isinstance(item_id, str) and item_id
            and isinstance(kind, str) and kind in _KINDS
            and isinstance(description, str) and description
        ):
            continue  # закрытое множество KINDS (ANTI-6b vocabulary defense)
        out.append({
            "item_id": item_id,
            "kind": kind,
            "factory": str(item.get("factory", "") or ""),
            "description": description,
            "confidence": (
                float(item["confidence"])
                if isinstance(item.get("confidence"), (int, float)) else 0.5
            ),
            "explicit": bool(item.get("explicit", False)),
        ])
    return out


class CapabilityGapLlmExecutor(BaseRoleExecutor):
    """LLM-вариант ``BaseRoleExecutor`` под ``role_id='capability_gap_auditor_llm'``.

    Дополняет детерминированный ``CapabilityGapAuditorExecutor`` — НЕ заменяет
    (cross-validation pattern). Используется когда нужна глубина: niche capabilities,
    meta-skills, infrastructure tools, anti-patterns. Тот же ``VOCAL_TASK_FRAGMENT``
    даёт ≥18 capabilities (vs 15 у детерминированного).

    Контракт:
    - DI ModelGateway через constructor (``gateway=...``). Должен предоставлять
      ``gateway.generate_by_capabilities(capabilities: List[str], messages: List[dict])``
      возвращающий объект с ``.content`` (str).
    - При любой ошибке (нет gateway, LLM crash, битый JSON) → ``[]`` (ADR-016).
    - NO global mutation (НЕ вызывает ``MissingRegistry.register_missing()`` напрямую).
    """

    role_id = LLM_ROLE_ID

    # Capability-тэги для вызова ModelGateway (provider-agnostic; cloud-first per CON-65
    # в SmartRouter). plan+code+explain покрывают задачу «архитектурный анализ задачи».
    DEFAULT_CAPABILITIES: tuple = ("plan", "code", "explain")

    def __init__(
        self,
        gateway: Optional[Any] = None,
        registry: Optional["MissingRegistry"] = None,
        *,
        corpus_root: Optional[Path] = None,
        corpus_context_enabled: bool = True,
    ) -> None:
        self._gateway = gateway
        self._registry = registry
        self._corpus_root = corpus_root
        self._corpus_context_enabled = corpus_context_enabled

    def execute(self, project: Project, role_id: str, **kwargs) -> List[str]:
        """Генерирует capability_gap_report_llm.md. Возвращает [LLM_REPORT_FILE] или []."""
        try:
            # Reuse: детерминированный исполнитель имеет единую точку чтения
            # task-файла; соблазн дублировать ничтожен.
            text = CapabilityGapAuditorExecutor(registry=self._registry)._read_task(project)
            if text is None:
                logger.info(
                    "CapabilityGapLlmExecutor: нет task-файла в %s ", project.root,
                )
                return []
            if len(text.strip()) < _MIN_BODY_LEN:
                return []
            entries = self._extract_via_llm(text)
            if not entries:
                logger.info("CapabilityGapLlmExecutor: LLM не вернул валидных entries")
                return []
            reporter = CapabilityGapReporter(
                registry=self._registry,
                pre_extracted_entries=entries,
            )
            # Единая synthetic-секция: Reporter не детализирует per-section для LLM-пути
            # (его дизайн — один плоский список).
            report_md = reporter.render([("(LLM-extracted capabilities)", text)])
            out = project.root / LLM_REPORT_FILE
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report_md + "\n", encoding="utf-8")
            return [LLM_REPORT_FILE] if out.is_file() else []
        except Exception as exc:  # noqa: BLE001 — ADR-016 fail-safe
            logger.warning("CapabilityGapLlmExecutor failed: %s", exc)
            return []

    # ── helpers ──────────────────────────────────────────────────────

    def _extract_via_llm(self, text: str) -> Dict[str, Tuple[str, str, str]]:
        """Шлёт текст в ModelGateway → парсит JSON → возвращает map ``item_id → (kind, factory, desc)``."""
        if self._gateway is None:
            logger.warning(
                "CapabilityGapLlmExecutor: ModelGateway не инжектирован, пропускаем",
            )
            return {}
        # ── Corpus context injection (default ON; ADR-016 fail-safe).
        # Top-5 recent URLов из corpus_persistence.lookup_by_source(role_id)
        # добавляются в user message как memory hint, с явным framing
        # «historical memory, IGNORE as constraint» чтобы LLM НЕ
        # over-anchor на них (anti-anchoring per designer v5.189.57 +
        # strengthened framing per code-reviewer post-fix).
        # Empty corpus / lookup-error → silently omit context block
        # (Option X per designer: НЕ загромождать prompt пустой фразой).
        context_block = ""
        if self._corpus_context_enabled:
            raw_entries: list = []  # defensive init (UnboundLocalError-safety)
            try:
                from scripts_01.corpus_persistence import (
                    lookup_by_source, CorpusEntry,
                )
                raw_entries = lookup_by_source(
                    self.role_id, root=self._corpus_root,
                )
            except Exception as exc:  # noqa: BLE001 — fail-safe на любой corpus error
                logger.warning(
                    "CapabilityGapLlmExecutor: corpus lookup failed: %s", exc,
                )
                raw_entries = []
            if raw_entries:
                # Dedup by URL (keep newest timestamp per URL) — код-reviewer
                # post-fix v5.189.57: multiple sources могли persist тот же URL;
                # dedup гарантирует что top-5 не забит дубликатами.
                seen: Dict[str, CorpusEntry] = {}
                for e in raw_entries:
                    if e.url not in seen or e.timestamp > seen[e.url].timestamp:
                        seen[e.url] = e
                entries_sorted = sorted(
                    seen.values(), key=lambda e: e.timestamp, reverse=True,
                )
                top = entries_sorted[:_CORPUS_CONTEXT_TOP_K]  # ANTI-6b: magic-number → module const
                lines = [
                    f"[{i+1}] {e.url}" + (f" — {e.title}" if e.title else "")
                    for i, e in enumerate(top)
                ]
                # Stronger anti-anchoring framing per code-reviewer v5.189.57:
                # imperative «IGNORE these URLs when assessing» вместо
                # purely advisory «memory, NOT a constraint».
                context_block = (
                    "PRIOR CORPUS CONTEXT — historical memory ONLY. "
                    "IGNORE these URLs when assessing dependencies; "
                    "extract capabilities independently:\n"
                    + "\n".join(lines) + "\n\n"
                )
        messages = [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": context_block + LLM_USER_PROMPT_TEMPLATE.format(task_text=text)},
        ]
        try:
            response = self._gateway.generate_by_capabilities(
                list(self.DEFAULT_CAPABILITIES), messages,
            )
        except Exception as exc:  # noqa: BLE001 — fail-safe on hard errors
            logger.warning(
                "CapabilityGapLlmExecutor: gateway.generate_by_capabilities failed: %s", exc,
            )
            return {}
        content = getattr(response, "content", None) if response is not None else None
        parsed = _parse_llm_response(content or "")
        return {
            item["item_id"]: (item["kind"], item.get("factory", ""), item["description"])
            for item in parsed
        }


def capability_audit_llm_executor_registry(
    gateway: Optional[Any] = None,
    registry: Optional["MissingRegistry"] = None,
) -> RoleExecutorRegistry:
    """Возвращает ``RoleExecutorRegistry`` с одним ``CapabilityGapLlmExecutor``.

    Подключается к ``ForgeFacade.run_chain(light_mode='generate')`` через параметр
    ``executor_registry`` — тогда MISSING-стадия ``capability_gap_auditor_llm``
    материализуется автоматически.
    """
    return RoleExecutorRegistry([CapabilityGapLlmExecutor(gateway=gateway, registry=registry)])


# ════════════════════════════════════════════════════════════════════════
# CLI: python -m core_02.capability_gap_auditor audit <project_root>
# ════════════════════════════════════════════════════════════════════════


def _print_json(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.

    Usage::

        python -m core_02.capability_gap_auditor audit <project_root>
            [--registry PATH] [--json] [--no-write]

    ``--no-write`` — печатает отчёт в stdout/stderr, не пишет файл (для тестов и превью).
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="capability_gap_auditor",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="capability_gap_auditor 1.0.0 (ADR-016, register-first, deterministic v1)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_audit = sub.add_parser(
        "audit",
        help="прочитать task из <project_root> и сгенерировать capability_gap_report.md",
    )
    p_audit.add_argument("project_root", help="путь к проекту (Project.root)")
    p_audit.add_argument(
        "--registry",
        default=None,
        help="путь к MissingRegistry YAML (default=data_13/missing_registry.yaml)",
    )
    p_audit.add_argument("--json", action="store_true", help="вывод JSON-резюме вместо markdown-отчёта")
    p_audit.add_argument(
        "--no-write",
        action="store_true",
        help="только stdout; не записывать capability_gap_report.md",
    )

    args = parser.parse_args(argv)

    if args.cmd != "audit":
        parser.error(f"unsupported command {args.cmd!r}")
        return 2  # pragma: no cover

    root = Path(args.project_root)
    if not root.is_dir():
        sys.stderr.write(f"error: project_root {root} не существует или не директория\n")
        return 2

    # Lazy import Project для CLI (избегаем circular на module-load).
    if _MissingRegistryCls is None:
        sys.stderr.write("error: MissingRegistry недоступна (ImportError)\n")
        return 2
    try:
        registry = _MissingRegistryCls(args.registry) if args.registry else _MissingRegistryCls()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"error: не удалось открыть MissingRegistry: {exc}\n")
        return 2

    project = Project.load(root)
    executor = CapabilityGapAuditorExecutor(registry=registry)

    try:
        text = executor._read_task(project)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"error: чтение task-файла: {exc}\n")
        return 1

    if text is None or len(text.strip()) < _MIN_BODY_LEN:
        sys.stderr.write("info: task-файл не найден или слишком короткий — отчёт пуст\n")
        return 0

    sections = _split_sections(text)
    reporter = CapabilityGapReporter(registry=registry)
    report_md = reporter.render(sections)

    if args.no_write:
        if args.json:
            _print_json({
                "project_root": str(root),
                "report_file": REPORT_FILE,
                "no_write": True,
                "sections": len(sections),
            ])
        else:
            sys.stdout.write(report_md + "\n")
        return 0

    out_path = root / REPORT_FILE
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md + "\n", encoding="utf-8")

    if args.json:
        _print_json({
            "project_root": str(root),
            "report_file": str(out_path.relative_to(root)) if out_path.is_relative_to(root) else str(out_path),
            "sections": len(sections),
            "report_bytes": len(report_md.encode("utf-8")),
        ])
    else:
        sys.stdout.write(f"\u2705 {REPORT_FILE} written ({len(report_md)} chars, {len(sections)} sections)\n")
        sys.stdout.write(f"   path: {out_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
