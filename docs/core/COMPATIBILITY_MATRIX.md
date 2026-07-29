# COMPATIBILITY MATRIX — Runtime Compatibility Matrix

> **Версия:** 1.0.0
> **Дата:** 2026-07-29
> **Статус:** Аудит v4.9.0 (1143 теста)
> **Основание:** [promt16.md***REMOVED***(../../pompts/promt16.md), [RUNTIME_VALIDATION_FRAMEWORK.md***REMOVED***(RUNTIME_VALIDATION_FRAMEWORK.md)

---

## Уровни совместимости

| Level | Название | Описание |
|-------|----------|----------|
| **0** | Не исследовано | Runtime известен, но не проверялся |
| **1** | Исследуется | Активно изучается, тестовый запуск |
| **2** | Запускается вручную | Можно запустить, нужна ручная настройка |
| **3** | Автоматическая установка | Установка через Bootstrap/Installer |
| **4** | Stable | Протестирован, работает стабильно |
| **5** | Community Verified | Подтверждён сообществом, документация |

---

## Матрица совместимости

| Runtime | Платформа | Уровень | Recipe | Ограничения | Дата проверки | Статус |
|---------|-----------|---------|--------|-------------|---------------|--------|
| **FreeBuff CLI** | Android/Termux | **4** — Stable | [Recipe***REMOVED***(../../runtime/recipes/freebuff/RECIPE.md) | Только Termux, ARM64 | 2026-07-29 | ✅ 1143 теста |
| **Claude Code** | Android/Termux | **2** — Запускается вручную | [Recipe***REMOVED***(../../runtime/recipes/claude_code/RECIPE.md) | Требует Node.js, npm, proot | 2026-07-29 | ⚠️ Только stdio |
| **OpenClaw** | Linux/macOS | **1** — Исследуется | — | Не тестировался на Android | — | 🔴 Не проверено |
| **Hermes** | Linux/macOS | **0** — Не исследовано | — | — | — | 🔴 Не проверено |
| **Codex** | Web/Cloud | **0** — Не исследовано | — | Только cloud API | — | 🔴 Не проверено |
| **Ollama (Qwen)** | Android/Linux | **2** — Запускается вручную | — | Требует proot + glibc, 4+ GB RAM | 2026-07-29 | ⚠️ Ручная установка |
| **GPT-5 (OpenAI)** | Cloud | **0** — Не исследовано | — | Только cloud API | — | 🔴 Не проверено |
| **Codebuff** | Cloud/CLI | **2** — Запускается вручную | — | Требует npm, API ключ | 2026-07-29 | ⚠️ Ручная установка |
| **Cursor** | Desktop | **0** — Не исследовано | — | GUI, не CLI | — | 🔴 Не проверено |

---

## Легенда статуса

| Символ | Значение |
|--------|----------|
| ✅ | Стабильно, тесты проходят |
| ⚠️ | Экспериментально, требует доработки |
| 🔴 | Не проверено / не исследовано |

---

## Сводка

| Уровень | Количество Runtime |
|---------|-------------------|
| Level 4 (Stable) | 1 (FreeBuff CLI) |
| Level 3 (Auto-install) | 0 |
| Level 2 (Manual) | 3 (Claude Code, Ollama, Codebuff) |
| Level 1 (Research) | 1 (OpenClaw) |
| Level 0 (Unknown) | 4 (Hermes, Codex, GPT-5, Cursor) |

**Всего известных Runtime:** 9
**Полностью протестированных:** 1 (11%)

---

*Связанные документы: [RUNTIME_VALIDATION_FRAMEWORK.md***REMOVED***(RUNTIME_VALIDATION_FRAMEWORK.md), [ARCHITECTURE_PRINCIPLES.md***REMOVED***(ARCHITECTURE_PRINCIPLES.md)*
