# SOURCE_MANIFEST.md — манифест исходного проекта «Калькуляторы»

> Статус: COMPLETE · Дата: 2026-09-07 · Режим: PREPARE (копия на сервере, оригинал нетронут)

## 1. Архив

| Параметр | Значение (проверено командами) |
|---|---|
| Локальный оригинал | `projects_17/админка печатник/Калькуляторы.zip` |
| Размер | 328 236 179 bytes |
| SHA-256 | `0f7e401327b0e06f00fc46a8f62633222b2f25bf91a049f18bae2ba70786dcd2` |
| Целостность | `unzip -t` → `No errors detected` |
| mtime оригинала | 2026-09-07 07:43:24 UTC (не изменён в ходе задачи) |
| Серверная копия | `/opt/freebuff/projects_17/админка печатник/Калькуляторы.source.zip` |
| SHA-256 копии | `0f7e4013…786dcd2` — **совпадает** с оригиналом |
| Распаковка | `/opt/freebuff/projects_17/админка печатник/worktree/Калькуляторы/` |

## 2. Объём распакованного дерева (проверено `find`)

- всего файлов: **130**; каталогов: **36**;
- файлов в `*/build/*`: 84; в `*/dist/*`: 12; в `__pycache__`: 1;
- размер: 326 MB (почти весь объём — бинарные EXE/библиотеки PyInstaller);
- исходников, значимых для аудита: **19 `.py`** (без build/dist), **3 `.json`**, 6 `.spec`, 3 `.ico`, 1 `.png`, 1 файл `python` (0 байт).

## 3. Топ-уровень архива (проверено `find -maxdepth 1`)

```
Калькуляторы/
├── Калькулятор макетов/            # webview-приложение (design_calc.py + settings.json)
├── Калькулятор себестоимости/      # tkinter-приложение (universal_calc.py + equipment.json)
├── Калькулятор фрезерной и лазерной резки/  # webview-приложение (cnc_calc.py + cnc_settings.json)
├── Коды на калькуляторы/           # исходники 4 standalone-калькуляторов (Tkinter)
│   ├── Riso/riso_calc.py
│   ├── Shirokoformat/wide_format.py
│   ├── Tablichki/tablichki.py
│   └── Буквы/sign_calc.py
└── Общий калькулятор печати/       # сборщик + обёртка «Меню_калькуляторов»
    ├── build_exe.py                # генератор: конвертирует Tk->Frame и собирает EXE
    ├── riso_calc.py / tablichki.py / sign_calc.py / wide_format.py / digital_calc.py
    ├── build_all/                  # сгенерированная копия (calc_*.py + all_in_one.py)
    └── dist/, build/               # готовые EXE
```

## 4. Обнаруженные проекты/приложения (точки входа)

| # | Приложение | Точка входа | UI-стек | Конфиг |
|---|---|---|---|---|
| 1 | Калькулятор дизайна и обработки макетов | `design_calc.py` | pywebview + HTML/JS | `settings.json` |
| 2 | Калькулятор ЧПУ резки (лазер/фрезер) | `cnc_calc.py` | pywebview + HTML/JS | `cnc_settings.json` |
| 3 | Калькулятор ризографии RISO RZ300EP | `Коды…/Riso/riso_calc.py` | Tkinter | JSON-конфиг в wrapper-копии |
| 4 | Широкоформатный калькулятор | `Коды…/Shirokoformat/wide_format.py` | Tkinter | JSON-конфиг в wrapper-копии |
| 5 | Калькулятор табличек | `Коды…/Tablichki/tablichki.py` | Tkinter | JSON-конфиг в wrapper-копии |
| 6 | Калькулятор вывесок/букв | `Коды…/Буквы/sign_calc.py` | Tkinter + Pillow | JSON-конфиг в wrapper-копии |
| 7 | Цифровая печать (только в обёртке) | `Общий…/digital_calc.py` | Tkinter | JSON-конфиг |
| 8 | Себестоимость (оборудование) | `universal_calc.py` | Tkinter | `equipment.json` |
| 9 | Меню-обёртка «Производственные калькуляторы» | `build_all/all_in_one.py` (генерируется `build_exe.py`) | Tkinter | — |

## 5. Предполагаемый стек (подтверждён импортами)

- Python 3 (сборки PyInstaller под Windows, `.spec` с `console=False`);
- GUI: **Tkinter/ttk** (6 приложений) и **pywebview + встроенный HTML/JS** (2 приложения);
- библиотеки: `Pillow` (sign_calc), `reportlab` (PDF в design_calc), `webview` (2 приложения);
- данные: JSON-конфиги рядом с exe/скриптом; экспорт CSV (utf-8-sig) и PDF;
- сборка: PyInstaller (`--onefile --windowed`), генератор `build_exe.py` с regex-патчингом исходников.

## 6. DoD этапа

- [x] оригинальный архив не изменён (SHA-256 совпал до и после);
- [x] архив перенесён в разрешённую область (копия);
- [x] архив успешно читается (`unzip -t` OK);
- [x] архив распакован в рабочую копию (130 файлов);
- [x] количество и структура файлов проверены;
- [x] исходник и рабочая копия различаются по назначению (оригинал = неизменяемый источник; worktree = аудит-копия);
- [x] SOURCE_MANIFEST.md создан.
