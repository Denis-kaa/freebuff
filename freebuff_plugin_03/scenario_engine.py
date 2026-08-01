"""
Freebuff Plugin — Scenario Engine.

Управляет каталогом готовых промтов под типовые задачи.
Сценарии — это markdown-файлы с YAML-секцией и готовым промтом для freebuff/Claude Code.

Использование:
    from freebuff_plugin_03.scenario_engine import ScenarioEngine
    
    engine = ScenarioEngine()
    all_scenarios = engine.list_scenarios()
    freelancing = engine.list_scenarios(category="freelancing")
    scenario = engine.get_scenario("freelance_parser")
    prompt = engine.apply_scenario("freelance_parser", {"URL": "https://..."***REMOVED***)
"""

from __future__ import annotations

import os
***REMOVED***
import json
***REMOVED***
from typing import Any


# ── Парсинг YAML-секции из markdown ─────────────────────────

def _parse_yaml_front_matter(text: str) -> dict[str, Any***REMOVED***:
    """Парсит YAML-секцию из начала markdown-файла.
    
    Формат:
        ---
        ключ: значение
        массив:
          - элемент1
          - элемент2
        ---
        ... остальной контент ...
    """
    result: dict[str, Any***REMOVED*** = {***REMOVED***
    # Ищем блок между двумя ---
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return result
    
    yaml_block = match.group(1)
    current_key = None
    in_list = False
    
    for line in yaml_block.split("\n"):
        line = line.rstrip()
        if not line:
            continue
        
        # Ключ: значение
        kv_match = re.match(r"^([a-zA-Zа-яА-Я0-9_\-***REMOVED***+):\s*(.*)", line)
        if kv_match:
            current_key = kv_match.group(1).strip()
            value = kv_match.group(2).strip()
            if value:
                result[current_key***REMOVED*** = _parse_yaml_value(value)
            else:
                result[current_key***REMOVED*** = [***REMOVED***
                in_list = True
            continue
        
        # Элемент списка
        list_match = re.match(r"^\s*[-****REMOVED***\s+(.*)", line)
        if list_match and current_key and in_list:
            if isinstance(result.get(current_key), list):
                result[current_key***REMOVED***.append(_parse_yaml_value(list_match.group(1).strip()))
            continue
        
        in_list = False
    
    return result


def _parse_yaml_value(value: str) -> Any:
    """Парсит YAML значение (строка, число, bool)."""
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1***REMOVED***
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1***REMOVED***
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.lower() == "null" or value.lower() == "none":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _strip_yaml_front_matter(text: str) -> str:
    """Удаляет YAML-секцию из markdown, возвращает чистый контент."""
    return re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL).strip()


# ═══════════════════════════════════════════════════════════════
# Scenario Engine
# ═══════════════════════════════════════════════════════════════

class Scenario:
    """Один сценарий."""

    def __init__(
        self,
        slug: str,
        title: str,
        category: str = "",
        complexity: str = "",
        description: str = "",
        tags: list[str***REMOVED*** | None = None,
        prompt_template: str = "",
        metadata: dict[str, Any***REMOVED*** | None = None,
    ):
        self.slug = slug  # имя файла без .md
        self.title = title
        self.category = category
        self.complexity = complexity
        self.description = description
        self.tags = tags or [***REMOVED***
        self.prompt_template = prompt_template  # шаблон с {placeholders***REMOVED***
        self.metadata = metadata or {***REMOVED***

    def to_dict(self) -> dict[str, Any***REMOVED***:
        return {
            "slug": self.slug,
            "title": self.title,
            "category": self.category,
            "complexity": self.complexity,
            "description": self.description,
            "tags": self.tags,
            "has_template": bool(self.prompt_template),
            "metadata": self.metadata,
        ***REMOVED***

    def apply(self, variables: dict[str, str***REMOVED*** | None = None) -> str:
        """Подставляет переменные в шаблон промта."""
        if not variables:
            return self.prompt_template
        result = self.prompt_template
        for key, value in variables.items():
            result = result.replace(f"{{{key***REMOVED******REMOVED******REMOVED***", str(value))
        return result


class ScenarioEngine:
    """Загружает, ищет и применяет сценарии из директории scenarios/."""

    def __init__(self, scenarios_dir: str | Path | None = None):
        self._dir = Path(scenarios_dir) if scenarios_dir else (
            Path(__file__).parent / "scenarios"
        )
        self._scenarios: dict[str, Scenario***REMOVED*** = {***REMOVED***
        self._load_scenarios()

    # ── Загрузка ─────────────────────────────────────────────

    def _load_scenarios(self) -> None:
        """Сканирует scenarios/ и загружает все .md файлы."""
        self._scenarios = {***REMOVED***
        if not self._dir.exists():
            return
        
        for filepath in sorted(self._dir.glob("*.md")):
            if filepath.name == "__init__.md":
                continue
            scenario = self._parse_file(filepath)
            if scenario:
                self._scenarios[scenario.slug***REMOVED*** = scenario

    def _parse_file(self, filepath: Path) -> Scenario | None:
        """Парсит .md файл в объект Scenario."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            return None

        slug = filepath.stem  # имя без .md
        meta = _parse_yaml_front_matter(content)
        body = _strip_yaml_front_matter(content)

        # Извлекаем заголовок первого уровня
        title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = title_match.group(1) if title_match else slug.replace("_", " ").title()

        # Извлекаем блок промта (после "## Промт для freebuff")
        prompt_match = re.search(
            r"## Промт для freebuff\s*\n+```\s*\n(.*?)```",
            body, re.DOTALL
        )
        prompt_template = prompt_match.group(1).strip() if prompt_match else ""

        # Извлекаем описание
        desc = meta.get("description", "")
        if not desc and body:
            # Первый абзац как описание
            desc = body.split("\n\n")[0***REMOVED***.replace("#", "").strip()[:200***REMOVED***

        tags = meta.get("tags", [***REMOVED***)
        if isinstance(tags, str):
            tags = [tags***REMOVED***

        return Scenario(
            slug=slug,
            title=title,
            category=meta.get("category", ""),
            complexity=meta.get("сложность", meta.get("complexity", "")),
            description=desc,
            tags=tags,
            prompt_template=prompt_template,
            metadata=meta,
        )

    # ── API ──────────────────────────────────────────────────

    def list_scenarios(
        self,
        category: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any***REMOVED******REMOVED***:
        """Список всех сценариев, опционально фильтр по категории/тегу."""
        scenarios = list(self._scenarios.values())
        
        if category:
            scenarios = [s for s in scenarios if s.category == category***REMOVED***
        if tag:
            scenarios = [s for s in scenarios if tag in s.tags***REMOVED***
        
        return [s.to_dict() for s in scenarios***REMOVED***

    def get_scenario(self, slug: str) -> Scenario | None:
        """Получить сценарий по slug (имя файла без .md)."""
        return self._scenarios.get(slug)

    def search_scenarios(self, query: str) -> list[dict[str, Any***REMOVED******REMOVED***:
        """Полнотекстовый поиск по названиям и описаниям."""
        query_lower = query.lower()
        results = [***REMOVED***
        for scenario in self._scenarios.values():
            if (query_lower in scenario.title.lower()
                    or query_lower in scenario.description.lower()
                    or query_lower in scenario.category.lower()
                    or any(query_lower in t.lower() for t in scenario.tags)):
                results.append(scenario.to_dict())
        return results

    def apply_scenario(
        self,
        slug: str,
        variables: dict[str, str***REMOVED*** | None = None,
    ) -> dict[str, Any***REMOVED***:
        """Применить сценарий: получить сгенерированный промт.
        
        Returns:
            dict: {slug, title, prompt, variables***REMOVED***
        """
        scenario = self.get_scenario(slug)
        if not scenario:
            return {
                "error": f"Scenario not found: {slug***REMOVED***",
                "available": list(self._scenarios.keys()),
            ***REMOVED***
        
        prompt = scenario.apply(variables)
        
        return {
            "slug": scenario.slug,
            "title": scenario.title,
            "category": scenario.category,
            "prompt": prompt,
            "variables": variables or {***REMOVED***,
            "has_template": bool(scenario.prompt_template),
        ***REMOVED***

    def reload(self) -> int:
        """Перезагрузить все сценарии с диска."""
        self._load_scenarios()
        return len(self._scenarios)


# ═══════════════════════════════════════════════════════════════
# CLI тест
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scenario Engine CLI")
    parser.add_argument("command", choices=["list", "get", "search", "apply", "reload"***REMOVED***,
                       help="Команда")
    parser.add_argument("arg", nargs="?", help="Аргумент (slug, query)")
    parser.add_argument("--category", "-c", help="Фильтр по категории")
    parser.add_argument("--tag", "-t", help="Фильтр по тегу")
    parser.add_argument("--vars", "-v", help="Переменные в JSON: {\"URL\": \"...\"***REMOVED***")

    args = parser.parse_args()
    engine = ScenarioEngine()

    if args.command == "list":
        scenarios = engine.list_scenarios(category=args.category, tag=args.tag)
        print(f"Scenarios: {len(scenarios)***REMOVED***")
        for s in scenarios:
            tags = f"[{', '.join(s['tags'***REMOVED***)***REMOVED******REMOVED***" if s['tags'***REMOVED*** else ""
            print(f"  {s['slug'***REMOVED***:30s***REMOVED*** | {s['category'***REMOVED***:15s***REMOVED*** | {s['title'***REMOVED***[:40***REMOVED******REMOVED*** {tags***REMOVED***")

    elif args.command == "get":
        if not args.arg:
            print("Укажи slug сценария")
            return
        s = engine.get_scenario(args.arg)
        if s:
            print(f"Slug:    {s.slug***REMOVED***")
            print(f"Title:   {s.title***REMOVED***")
            print(f"Category:{s.category***REMOVED***")
            print(f"Complex: {s.complexity***REMOVED***")
            print(f"Desc:    {s.description[:100***REMOVED******REMOVED***...")
            print(f"Tags:    {', '.join(s.tags)***REMOVED***")
            print(f"Prompt:  {len(s.prompt_template)***REMOVED*** chars")
            if s.prompt_template:
                print(f"---\n{s.prompt_template[:500***REMOVED******REMOVED***...")
        else:
            print(f"Scenario not found: {args.arg***REMOVED***")

    elif args.command == "search":
        results = engine.search_scenarios(args.arg or "")
        print(f"Found: {len(results)***REMOVED***")
        for s in results:
            print(f"  {s['slug'***REMOVED***:30s***REMOVED*** | {s['title'***REMOVED******REMOVED***")

    elif args.command == "apply":
        if not args.arg:
            print("Укажи slug сценария")
            return
        variables = json.loads(args.vars) if args.vars else None
        result = engine.apply_scenario(args.arg, variables)
        if "error" in result:
            print(f"Error: {result['error'***REMOVED******REMOVED***")
            return
        print(f"Scenario: {result['title'***REMOVED******REMOVED*** ({result['slug'***REMOVED******REMOVED***)")
        print(f"Variables: {result['variables'***REMOVED******REMOVED***")
        print(f"Prompt ({len(result['prompt'***REMOVED***)***REMOVED*** chars):")
        print("---")
        print(result['prompt'***REMOVED***)

    elif args.command == "reload":
        count = engine.reload()
        print(f"Reloaded: {count***REMOVED*** scenarios")


if __name__ == "__main__":
    main()
