"""Knowledge curator for generating structured learning plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class LearningSource:
    """A single learning resource."""

    title: str
    description: str
    why: str


@dataclass
class LearningPlan:
    """Structured learning plan for a given topic."""

    topic: str
    fundamentals: list[LearningSource] = field(default_factory=list)
    videos: list[LearningSource] = field(default_factory=list)
    services: list[LearningSource] = field(default_factory=list)
    strategies: list[LearningSource] = field(default_factory=list)
    legal: list[LearningSource] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def format(self) -> str:  # noqa: A003
        """Return a formatted markdown representation."""
        lines = [f"# План обучения: {self.topic}", ""]

        def section(title: str, items: list[LearningSource]) -> None:
            lines.append(f"## {title}")
            if not items:
                lines.append("_нет данных_")
            for item in items:
                lines.append(f"- **{item.title}** — {item.description}")
                lines.append(f"  *Почему важно:* {item.why}")
            lines.append("")

        section("Фундаментальная литература", self.fundamentals)
        section("Видео-материалы", self.videos)
        section("Практические сервисы", self.services)
        section("Стратегии и схемы", self.strategies)
        section("Нормативная база", self.legal)

        return "\n".join(lines)


def build_plan(topic: str) -> LearningPlan:
    """Create a default learning plan for a real-estate topic.

    In a production system this could query a local LLM or curated DB.
    """
    plan = LearningPlan(topic=topic)

    plan.fundamentals.append(
        LearningSource(
            title="СПИН-продажи (SPIN Selling)",
            description="Классическая методология вопросов для сложных B2C-продаж.",
            why="Помогает выявлять потребности клиента до презентации объекта.",
        )
    )
    plan.fundamentals.append(
        LearningSource(
            title="Чемпионы продаж (Jeff Shore)",
            description="Книга о переговорах и работе с возражениями.",
            why="Дает готовые скрипты для возражений 'дорого' и 'я сам продам'.",
        )
    )
    plan.videos.append(
        LearningSource(
            title="YouTube: 'Скрипты для риелторов 2026'",
            description="Поисковый запрос для самостоятельного изучения.",
            why="Позволяет найти актуальные разборы на русском языке.",
        )
    )
    plan.services.append(
        LearningSource(
            title="Локальный транскрибатор аудио (Whisper.cpp)",
            description="Offline ASR для анализа записей звонков.",
            why="Позволяет анализировать свои звонки без передачи данных в облако.",
        )
    )
    plan.strategies.append(
        LearningSource(
            title="Схема отработки возражения 'дорого'",
            description="Шаг 1 — признать, Шаг 2 — уточнить бюджет, Шаг 3 — альтернативы.",
            why="Унифицирует ответ и снижает эмоциональное сопротивление клиента.",
        )
    )
    plan.legal.append(
        LearningSource(
            title="Гражданский кодекс РФ (жилищные отношения)",
            description="Базовые статьи о купле-продаже недвижимости.",
            why="Помогает быстро отвечать на юридические вопросы клиентов.",
        )
    )
    return plan
