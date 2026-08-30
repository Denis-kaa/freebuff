# core_02/learning_loop.py — Learning Loop (AFC: Analyze → Formalize → Codify)
# Organizational Memory Engine (RFC_ORGANIZATIONAL_MEMORY_ENGINE_V1.md §7)

"""Цикл обучения Organizational Memory.

Этап 3.4 из PLAN_NEXT_OPERATIONS.md. Триггеры:
  - код-ревью нашло проблему
  - тест упал
  - пользователь явно попросил «запомни»

AFC-цикл:
  analyze(context)   -> Analysis (релевантные уроки, известный/новый паттерн)
  formalize(analysis)-> KnowledgeObject (создание/обновление, связи в графе)
  codify(ko)         -> Action (LESSONS.md CON-N, ARCHITECTURAL_DEBT.md, TG)

Использование:
    loop = LearningLoop(store, semantic)
    loop.record_feedback("ko-xxx", "success")   # замыкание цикла (§7)
    loop.capture(context, kind="lesson", ...)    # полный AFC одной командой
"""

from __future__ import annotations

}
from datetime import datetime, timezone
}
from typing import Any, Dict, List, Optional

from core_02.memory_store import MemoryStore
from core_02.semantic_layer import SemanticLayer

# Шаблон CON-N в LESSONS.md
CON_PATTERN = re.compile(r"\bCON-(\d+)\b")


class Analysis:
    """Результат фазы analyze: релевантные знания + классификация ситуации."""

    def __init__(
        self,
        situation: str,
        relevant: List[Dict[str, Any]],
        is_known_pattern: bool,
        suggested_kind: str,
    ):
        self.situation = situation
        self.relevant = relevant
        self.is_known_pattern = is_known_pattern
        self.suggested_kind = suggested_kind

    def to_dict(self) -> Dict[str, Any]:
        return {
            "situation": self.situation,
            "relevant": self.relevant,
            "is_known_pattern": self.is_known_pattern,
            "suggested_kind": self.suggested_kind,
        }


class LearningLoop:
    """AFC-цикл: анализ ситуации → формализация знания → кодификация."""

    def __init__(
        self,
        store: MemoryStore,
        semantic: Optional[SemanticLayer] = None,
        lessons_path: Optional[str | Path] = None,
        debt_path: Optional[str | Path] = None,
    ):
        self.store = store
        self.semantic = semantic
        self.lessons_path = Path(lessons_path) if lessons_path else Path("core_02/LESSONS.md")
        self.debt_path = Path(debt_path) if debt_path else Path("docs_10/core/ARCHITECTURAL_DEBT.md")

    # ── Фаза 1: Analyze ──────────────────────────────────────────────
    def analyze(
        self,
        situation: str,
        top_k: int = 5,
    ) -> Analysis:
        """Оценить ситуацию: какие знания релевантны, паттерн известен? (RFC §7)."""
        relevant: List[Dict[str, Any]] = []
        if self.semantic is not None:
            relevant = self.semantic.find_similar_patterns(situation, top_k=top_k)
        best = relevant[0] if relevant else None
        is_known = bool(best and best.get("score", 0) >= 0.5)
        kind = self._suggest_kind(situation)
        return Analysis(
            situation=situation,
            relevant=relevant,
            is_known_pattern=is_known,
            suggested_kind=kind,
        )

    @staticmethod
    def _suggest_kind(situation: str) -> str:
        s = situation.lower()
        # «урок» проверяем ДО «повтор», иначе «не повторяй» матчит pattern раньше
        if any(w in s for w in ("урок", "не повтори", "не повторяй", "learned", "lesson")):
            return "lesson"
        if any(w in s for w in ("паттерн", "pattern", "повторяется", "повторение", "повторяющ")):
            return "pattern"
        if any(w in s for w in ("правило", "запрет", "всегда", "never", "rule")):
            return "rule"
        if any(w in s for w in ("архитектур", "решение", "adr")):
            return "adr"
        if any(w in s for w in ("чек-лист", "checklist", "порядок")):
            return "checklist"
        if any(w in s for w in ("гайд", "guide", "рекомендац")):
            return "guideline"
        if any(w in s for w in ("вопрос", "faq", "как сделать")):
            return "faq"
        if any(w in s for w in ("процесс", "workflow", "пайплайн")):
            return "workflow"
        if any(w in s for w in ("наблюден", "observation", "заметил")):
            return "observation"
        if any(w in s for w in ("кандидат", "возможно", "candidate")):
            return "candidate"
        return "lesson"

    # ── Фаза 2: Formalize ────────────────────────────────────────────
    def formalize(
        self,
        analysis: Analysis,
        title: str = "",
        summary: str = "",
        content: str = "",
        tags: Optional[List[str]] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        confidence: float = 0.5,
    ) -> str:
        """Создать/обновить Knowledge Object и связать с релевантными (RFC §7).

        Возвращает knowledge_id. Если паттерн известен (score >= 0.5) — обновляет
        существующий объект (evidence_count+1), иначе создаёт новый.
        """
        best = analysis.relevant[0] if analysis.relevant else None
        if best and best.get("score", 0) >= 0.5:
            kid = best["knowledge_id"]
            self.store.update_knowledge(
                kid,
                title=title or best.get("title", ""),
                summary=summary,
                content=content or None,
                confidence_score=max(confidence, float(best.get("confidence") or 0.5)),
            )
            self._bump_evidence(kid)
            self._link_to_related(kid, analysis.relevant)
            return kid
        # Новый Knowledge Object
        kid = self.store.store_knowledge(
            kind=analysis.suggested_kind,
            title=title or analysis.situation[:80],
            summary=summary,
            content=content or analysis.situation,
            tags=tags or [],
            sources=sources or [],
            lifecycle_stage="candidate" if analysis.is_known_pattern else "raw",
            status="draft",
            confidence_score=confidence,
        )
        self._link_to_related(kid, analysis.relevant)
        return kid

    def _bump_evidence(self, knowledge_id: str) -> None:
        if self.store.get_knowledge(knowledge_id):
            self.store._execute(
                "UPDATE knowledge_objects SET evidence_count = evidence_count + 1 WHERE id=?",
                (knowledge_id,),
            )

    def _link_to_related(self, kid: str, relevant: List[Dict[str, Any]]) -> None:
        for rel in relevant[:5]:
            other = rel["knowledge_id"]
            if other == kid:
                continue
            try:
                self.store.link_knowledge(kid, other, "supports", weight=float(rel.get("score", 0.5)))
            except Exception:
                continue

    # ── Фаза 3: Codify ───────────────────────────────────────────────
    def codify(
        self,
        knowledge_id: str,
        notify_tg: bool = False,
    ) -> Dict[str, Any]:
        """Кодифицировать знание в артефакты: LESSONS.md (CON-N), DEBT.md, TG.

        Возвращает action-отчёт: {lessons_updated, con_id, debt_updated, tg_sent}.
        """
        ko = self.store.get_knowledge(knowledge_id)
        if not ko:
            raise KeyError(f"Knowledge Object {knowledge_id} не найден")

        action: Dict[str, Any] = {"lessons_updated": False, "con_id": None,
                                  "debt_updated": False, "tg_sent": False]

        # 1) LESSONS.md — запись CON-N
        if ko.get("kind") in ("lesson", "pattern", "anti_pattern", "guideline", "rule", "adr", "workflow"):
            con_id = self._next_con_id()
            entry = self._format_con_entry(con_id, ko)
            self.lessons_path.parent.mkdir(parents=True, exist_ok=True)
            with self.lessons_path.open("a", encoding="utf-8") as f:
                f.write("\n" + entry + "\n")
            action["lessons_updated"] = True
            action["con_id"] = con_id

        # 2) ARCHITECTURAL_DEBT.md — если это архитектурный долг
        if ko.get("kind") == "adr" and "долг" in (ko.get("summary") or "").lower():
            with self.debt_path.open("a", encoding="utf-8") as f:
                f.write(f"\n- {ko.get('title')} (OM:{knowledge_id})\n")
            action["debt_updated"] = True

        # 3) Telegram-уведомление
        if notify_tg:
            try:
                from core_02.telegram_contract import send_message  # type: ignore
                send_message(
                    f"🧠 OM: {ko.get('kind')} «{ko.get('title')}» зафиксирован (CON-{action['con_id'] or '—'})"
                )
                action["tg_sent"] = True
            except Exception:
                action["tg_sent"] = False
        return action

    def _next_con_id(self) -> int:
        if not self.lessons_path.exists():
            return 1
        text = self.lessons_path.read_text(encoding="utf-8")
        ids = [int(m) for m in CON_PATTERN.findall(text)]
        return (max(ids) + 1) if ids else 1

    @staticmethod
    def _format_con_entry(con_id: int, ko: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        title = ko.get("title") or ko.get("kind", "knowledge")
        summary = ko.get("summary") or ko.get("content", "")[:200]
        return (
            f"### CON-{con_id} — {title}\n\n"
            f"**Сценарий:** {summary}\n"
            f"**Knowledge Object:** `{ko.get('id')}` (kind={ko.get('kind')}, "
            f"confidence={ko.get('confidence_score')}, OM {now})\n"
        )

    # ── Замыкание цикла: feedback (§7) ──────────────────────────────
    def record_feedback(self, knowledge_id: str, outcome: str) -> Optional[float]:
        """Feedback после применения: success/failure/neutral. Возвращает confidence."""
        confidence = self.store.update_feedback(knowledge_id, outcome)
        self.store.record_learning_event(
            trigger_id=f"feedback-{knowledge_id}",
            context_snapshot={"outcome": outcome},
            outcome=outcome,
            lesson_id=knowledge_id,
        )
        return confidence

    # ── Полный цикл одной командой ───────────────────────────────────
    def capture(
        self,
        situation: str,
        title: str = "",
        summary: str = "",
        content: str = "",
        tags: Optional[List[str]] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        notify_tg: bool = False,
    ) -> Dict[str, Any]:
        """AFC одной командой: analyze → formalize → codify → feedback neutral."""
        analysis = self.analyze(situation)
        kid = self.formalize(analysis, title=title, summary=summary,
                             content=content, tags=tags, sources=sources)
        action = self.codify(kid, notify_tg=notify_tg)
        self.store.record_learning_event(
            trigger_id="capture",
            context_snapshot={"situation": situation, "kind": analysis.suggested_kind},
            outcome="neutral",
            lesson_id=kid,
        )
        return {
            "knowledge_id": kid,
            "analysis": analysis.to_dict(),
            "action": action,
        }
