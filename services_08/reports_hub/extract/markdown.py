"""Markdown-парсер Reports Hub (спека §5.1.1, H2).

Свой, без тяжёлых зависимостей: заголовки h1–h4, таблицы, списки,
блочные цитаты. Выход — дерево секций. Не додумывает факты:
нет данных → секция помечается «источник не найден» на слое сборки.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Table:
    """Markdown-таблица: заголовок + строки (сырые ячейки)."""

    header: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class Section:
    """Секция документа: заголовок + тело + таблицы + цитаты."""

    level: int
    title: str
    body_lines: list[str] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    quotes: list[str] = field(default_factory=list)

    def body_text(self) -> str:
        """Текст тела секции одной строкой (для резюме/поиска)."""
        return "\n".join(self.body_lines).strip()


@dataclass
class ParsedDocument:
    """Результат парсинга одного Markdown-документа."""

    path: str
    title: str = ""
    sections: list[Section] = field(default_factory=list)
    top_quotes: list[str] = field(default_factory=list)


_HEADING_RE = re.compile(r"^(#{1,4})\s+(.*?)\s*$")
_QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")

#: Строка-разделитель таблицы: только | - : пробелы (минимум 3 знака).
_SEP_CHARS = frozenset("|-: \t")


def _is_table_separator(line: str) -> bool:
    """Проверить строку-разделитель таблицы (| --- | --- |).

    Строго: только символы | - : пробел, есть хотя бы один дефис.
    Цитаты вида `> Дата: ...` не проходят (содержат буквы).
    """
    text = line.strip()
    if len(text) < 3 or "-" not in text:
        return False
    return all(ch in _SEP_CHARS for ch in text)


def _split_row(line: str) -> list[str]:
    """Разбить строку таблицы на ячейки (крайние pipe опциональны)."""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [cell.strip() for cell in text.split("|")]


def parse_markdown(text: str, path: str = "") -> ParsedDocument:
    """Распарсить Markdown-текст в дерево секций.

    Args:
        text: содержимое .md файла.
        path: имя файла (для диагностики, в модель не вшивается).

    Returns:
        ParsedDocument с секциями h1–h4, таблицами, цитатами.
    """
    doc = ParsedDocument(path=path)
    current: Section | None = None
    pending_header: list[str] | None = None
    in_table: bool = False

    def push_current() -> None:
        if current is not None:
            doc.sections.append(current)

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        heading = _HEADING_RE.match(line)
        if heading:
            push_current()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            if doc.title == "" and level == 1:
                doc.title = title
            current = Section(level=level, title=title)
            pending_header = None
            in_table = False
            continue
        stripped = line.strip()
        if stripped in ("---", "***", "___"):
            # Горизонтальная линейка: сбрасывает табличное состояние.
            if pending_header is not None and current is not None:
                current.body_lines.append("|".join(pending_header))
                pending_header = None
            in_table = False
            if current is not None:
                current.body_lines.append(line)
            continue
        quote = _QUOTE_RE.match(line)
        if quote:
            content = quote.group(1).strip()
            if current is not None and not doc.sections and not current.tables:
                # Цитаты шапки документа (секция h1 до первой ---/h2):
                # дублируем в верхние цитаты и в секцию (шапка видна везде).
                doc.top_quotes.append(content)
                current.quotes.append(content)
            elif current is None:
                doc.top_quotes.append(content)
            else:
                current.quotes.append(content)
            pending_header = None
            continue
        if _is_table_separator(line) and pending_header is not None and current is not None:
            current.tables.append(Table(header=pending_header, rows=[]))
            pending_header = None
            in_table = True
            continue
        if "|" in line and current is not None:
            cells = _split_row(line)
            if len(cells) >= 2 and not stripped.startswith("*") and not stripped[0].isdigit():
                if in_table and current.tables:
                    # Строка данных таблицы (после разделителя).
                    current.tables[-1].rows.append(cells)
                    continue
                # Возможный заголовок таблицы: следующая строка — разделитель.
                pending_header = cells
                continue
        if current is None:
            if line.strip():
                # Текст до первого заголовка: создаём безымянную секцию уровня 0.
                current = Section(level=0, title="")
                current.body_lines.append(line)
            pending_header = None
            continue
        if pending_header is not None:
            # Не таблица: заголовок-кандидат был обычным текстом с pipe.
            current.body_lines.append("|".join(pending_header))
            pending_header = None
        in_table = False
        current.body_lines.append(line)
    if pending_header is not None and current is not None:
        current.body_lines.append("|".join(pending_header))
    push_current()
    return doc


def find_sections(doc: ParsedDocument, keywords: tuple[str, ...]) -> list[Section]:
    """Найти секции, чей заголовок содержит любой из keywords (case-insensitive)."""
    lowered = [k.lower() for k in keywords]
    return [s for s in doc.sections if any(k in s.title.lower() for k in lowered)]


def first_paragraph(section: Section, max_chars: int = 500) -> str:
    """Первый содержательный абзац секции (для детерминированных резюме, спека §5.3).

    Пропускает служебные строки (``**Коммит:** ...``, одиночные ``**...**``),
    чтобы резюме начиналось с сути, а не с метаданных.
    """
    paragraph: list[str] = []
    for line in section.body_lines:
        stripped = line.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if _LIST_RE.match(line):
            if paragraph:
                break
            continue
        if stripped.startswith("**") and stripped.endswith("**") and len(stripped) < 120:
            continue
        if stripped.startswith("**Коммит:"):
            continue
        paragraph.append(stripped)
    text = " ".join(paragraph).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text
