# Project Registry

> **Дата:** 2026-07-29
> **Версия:** 2.0.0 (реорганизация docs/)
> **Всего проектов в `projects/`:** 4

---

## Сводка

| Проект | Язык | README | MANIFEST | Статус |
|--------|------|--------|----------|--------|
| [`diet_platform/`***REMOVED***(../../projects/diet_platform/) | Python | ❌ | ❌ | 🔴 Требует README + MANIFEST |
| [`realtor_automation/`***REMOVED***(../../projects/realtor_automation/) | Python | ✅ | ❌ | 🟡 Требует MANIFEST |
| [`realtor_os/`***REMOVED***(../../projects/realtor_os/) | Python | ✅ | ✅ | 🟢 OK |
| [`tg_terminal_messenger/`***REMOVED***(../../projects/tg_terminal_messenger/) | Python | ✅ | ✅ (manifest.md) | 🟡 Переименовать в MANIFEST.md |

---

## Проекты экосистемы Leviathan

Полный реестр из `~/leviathan/opt` хранится в `data/context.db` → таблица `projects` (62 записи).
Команды:
```bash
python scripts/scan_projects.py --status    # список всех проектов
python scripts/scan_projects.py              # пересканировать
```

---

*Связанные документы: [ARCHITECTURE_PRINCIPLES.md***REMOVED***(ARCHITECTURE_PRINCIPLES.md)*
