# Runtime Recipes — System

> **Дата:** 2026-07-29
> **Версия:** 1.0.0
> **Основание:** [promt16.md***REMOVED***(../pompts/promt16.md) Задача 2.1

---

## Назначение

Runtime Recipes — воспроизводимые рецепты установки, настройки и обслуживания
AI Runtime в среде Android/Termux. Каждый Recipe — это самодостаточный документ,
описывающий полный жизненный цикл Runtime.

## Структура

```
runtime/
├── README.md                    # Этот файл
└── recipes/
    ├── freebuff/
    │   └── RECIPE.md            # FreeBuff CLI
    ├── claude_code/
    │   └── RECIPE.md            # Claude Code
    ├── openclaw/                # План
    ├── hermes/                  # План
    ├── codex/                   # План
    └── ollama/                  # План
```

## Формат RECIPE.md

Каждый Recipe должен описывать:

1. **Установку** — команды, зависимости, проверки
2. **Зависимости** — системные пакеты, pip, npm
3. **Wrapper** — скрипты-обёртки (для proot, glibc)
4. **Patch** — необходимые патчи и workaround'ы
5. **Update** — процедура обновления
6. **Uninstall** — процедура удаления
7. **Doctor** — диагностика работоспособности
8. **Recovery** — восстановление после сбоя

## Уровни совместимости

См. [docs/core/COMPATIBILITY_MATRIX.md***REMOVED***(../docs/core/COMPATIBILITY_MATRIX.md)

| Runtime | Уровень | Recipe |
|---------|---------|--------|
| FreeBuff CLI | 4 — Stable | [recipes/freebuff/RECIPE.md***REMOVED***(recipes/freebuff/RECIPE.md) |
| Claude Code | 2 — Manual | [recipes/claude_code/RECIPE.md***REMOVED***(recipes/claude_code/RECIPE.md) |
| OpenClaw | 1 — Research | План |
| Ollama (Qwen) | 2 — Manual | План |
| Hermes | 0 — Unknown | План |
| Codex | 0 — Unknown | План |

## Связанные документы

- [RUNTIME_VALIDATION_FRAMEWORK.md***REMOVED***(../docs/core/RUNTIME_VALIDATION_FRAMEWORK.md)
- [ARCHITECTURE_PRINCIPLES.md***REMOVED***(../docs/core/ARCHITECTURE_PRINCIPLES.md)
