#!/usr/bin/env python3
"""Tests for Reports Hub markdown extract (спека §12, тест 1: test_markdown_extract).

Фикстура — фрагмент реального PROJECT_STATUS_REPORT печатника.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services_08.reports_hub.extract.markdown import (
    find_sections,
    first_paragraph,
    parse_markdown,
)

# Фикстура из реального PROJECT_STATUS_REPORT.md (сводка + строка этапа + цитата).
FIXTURE = """# PROJECT_STATUS_REPORT.md — полный отчёт по этапам и соответствие кода

> Дата: 2026-09-10 · Версия на сервере: `0d67152` (мастер = GitHub = сервер)
> Состояние: **249 тестов зелёные, mypy clean (50 файлов), сервис активен, БД чистая**

---

## 1. Сводка «что сделано» (13 этапов)

| # | Этап | Коммит | Дата | Ядро результата |
|---|------|--------|------|-----------------|
| 0 | Аудит реализации | `1badef4` | 09-08 | IMPLEMENTATION_AUDIT_REPORT по 15 пунктам ТЗ |
| 1 | Клиенты + материалы | `2a85211` | 09-08 | clients/contacts/materials, matching, реестр |

## 2. Отчёт по каждому этапу

### Этап 0 — Аудит (старт работ)
**Коммит:** `1badef4` · **Отчёт:** IMPLEMENTATION_AUDIT_REPORT.md

Проверка 15 пунктов ТЗ перед началом кода: окружение, схема БД, движок.
"""


class TestMarkdownHeadings:
    def test_title_and_top_quotes(self) -> None:
        doc = parse_markdown(FIXTURE, path="PROJECT_STATUS_REPORT.md")
        assert "PROJECT_STATUS_REPORT" in doc.title
        assert any("2026-09-10" in q for q in doc.top_quotes)
        assert any("249 тестов" in q for q in doc.top_quotes)

    def test_sections_detected(self) -> None:
        doc = parse_markdown(FIXTURE, path="PROJECT_STATUS_REPORT.md")
        titles = [s.title for s in doc.sections]
        assert any("Сводка" in t for t in titles)
        assert any("Этап 0" in t for t in titles)


class TestMarkdownTables:
    def test_timeline_table_parsed(self) -> None:
        doc = parse_markdown(FIXTURE, path="PROJECT_STATUS_REPORT.md")
        summary = find_sections(doc, ("сводка",))[0]
        assert len(summary.tables) == 1
        table = summary.tables[0]
        assert table.header[:3] == ["#", "Этап", "Коммит"]
        assert len(table.rows) == 2
        assert table.rows[0][1] == "Аудит реализации"
        assert table.rows[1][2] == "`2a85211`"


class TestMarkdownHelpers:
    def test_find_sections_case_insensitive(self) -> None:
        doc = parse_markdown(FIXTURE, path="PROJECT_STATUS_REPORT.md")
        assert len(find_sections(doc, ("СВОДКА",))) == 1
        assert find_sections(doc, ("нет такой секции",)) == []

    def test_first_paragraph(self) -> None:
        doc = parse_markdown(FIXTURE, path="PROJECT_STATUS_REPORT.md")
        stage = find_sections(doc, ("этап 0",))[0]
        assert first_paragraph(stage).startswith("Проверка 15 пунктов ТЗ")
