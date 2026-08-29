# 04_TARGET_SYSTEM_MODEL.md — Целевая модель

> **Статус:** это концептуальная гипотеза из promt106 (§1), НЕ подтверждённый факт.

---

## Целевая цепочка (гипотеза)

```
WHIM
 ↓
WORKSPACE
 ↓
PROJECT          ← «рабочая тетрадь»: идея, обсуждения, решения, гипотезы,
 │                 исследования, планы, задания, результаты, документы, артефакты
 ↓
AGENT / COLLABORATION   ← companion-слой: один основной агент + специализированные
 ↓
SCENARIO         ← ЧТО нужно получить + КАКОЙ тип работы выполнить
 ↓
FACTORY          ← организационная/исполнительная capability (класс результатов)
 │                 Research/Code/Design/Content/Image/Video/Document/Data
 ↓
FORGE            ← конкретная производственная способность / workflow / unit
 │                 (ResearchFactory → MarketResearch Forge, …)
 ↓
SKILLS / TOOLS / RUNTIME
 ↓
ARTIFACT         ← research report / architecture / source / image / website / …
 ↓
MEMORY / KNOWLEDGE
```

---

## Ответственность каждого концепта (target)

| Concept | Target responsibility |
|---------|----------------------|
| WHIM | сырая мысль «я хочу создать X» |
| WORKSPACE | локальная среда (local-first) |
| PROJECT | рабочая тетрадь/история проекта (идея→результаты) |
| AGENT | companion + специализированные исполнители, принимающие решение о запуске Factory/Forge |
| SCENARIO | ЧТО получить + тип работы (research/code/design/content) |
| FACTORY | capability, производящая класс результатов (НЕ конкретная работа) |
| FORGE | конкретный workflow внутри Factory (Market Research Forge и т.п.) |
| ROLE | участник внутри Forge (analyst/developer/reviewer) |
| SKILL | атомарная способность |
| TOOL | интерфейс к внешнему действию (git/shell/http/file) |
| RUNTIME | среда исполнения агента/инструмента |
| WORKFLOW | порядок шагов |
| ARTIFACT | результат |
| MEMORY | разговор/история |
| KNOWLEDGE | накопленные факты |
| EVENT | переходы между компонентами |
| TASK | единица работы |

---

## Иерархия (target-гипотеза, НЕ факт)

```
Workspace
  └── Project
       └── Scenario
            └── Factory (глобальная capability, НЕ принадлежит Project)
                 └── Forge (workflow)
                      └── Agent (исполнитель роли)
                           └── Skill
                                └── Tool
```

Вопросы иерархии, которые проверяет код (§7):
- Factory принадлежит Project? → гипотеза: НЕТ, глобальная capability.
- Forge принадлежит Factory? → гипотеза: ДА, workflow внутри Factory.
- Scenario вызывает Factory? → гипотеза: ДА.
- Agent вызывает Scenario или часть Forge? → гипотеза: оба.
