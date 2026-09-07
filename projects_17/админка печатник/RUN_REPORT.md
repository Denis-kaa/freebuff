# RUN_REPORT.md — проверка запуска приложений «Калькуляторы»

> Статус: **PARTIAL — BLOCKED BY ENVIRONMENT** · Дата: 2026-09-07
> Все пробы выполнены в изолированной копии на whimco; ни один системный пакет не устанавливался (правило ACCESS_SCOPE §3).

## 1. Окружение сервера (проверено фактически)

| Компонент | Результат |
|---|---|
| Python | 3.12.3 (`/usr/bin/python3`) |
| `xvfb-run` | доступен (виртуальный X-сервер есть) |
| `wish` | отсутствует |
| `DISPLAY` | не установлен |
| tkinter | **ModuleNotFoundError** |
| PIL (Pillow) | **ModuleNotFoundError** |
| webview (pywebview) | **ModuleNotFoundError** |
| reportlab | **ModuleNotFoundError** |

## 2. Команды запуска (определены из кода)

- Каждое приложение: `python3 <entry.py>` (GUI запускается в `__main__`).
- Обёртка: `python3 build_all/all_in_one.py`; сборка EXE: `python3 build_exe.py` (требует PyInstaller, Windows-пути в spec).

## 3. Результаты launch-проб (каждая — отдельным процессом, `timeout 5s`)

| # | Точка входа | EXIT | Ошибка |
|---|---|---|---|
| 1 | `Калькулятор макетов/design_calc.py` | 1 | `ModuleNotFoundError: No module named 'webview'` (строка 5) |
| 2 | `Калькулятор фрезерной и лазерной резки/cnc_calc.py` | 1 | `ModuleNotFoundError: No module named 'webview'` (строка 5) |
| 3 | `Коды…/Riso/riso_calc.py` | 1 | `ModuleNotFoundError: No module named 'tkinter'` (строка 1) |
| 4 | `Коды…/Tablichki/tablichki.py` | 1 | `ModuleNotFoundError: No module named 'tkinter'` |
| 5 | `Коды…/Буквы/sign_calc.py` | 1 | `ModuleNotFoundError: No module named 'tkinter'` |
| 6 | `Коды…/Shirokoformat/wide_format.py` | 1 | `ModuleNotFoundError: No module named 'tkinter'` |
| 7 | `Общий…/build_all/all_in_one.py` | 1 | `ModuleNotFoundError: No module named 'tkinter'` |
| 8 | `Калькулятор себестоимости/universal_calc.py` | 1 | `ModuleNotFoundError: No module named 'tkinter'` |

## 4. Что проверено БЕЗ GUI (фактически пройдено)

- AST-парсинг всех 19 исходников — **19/19 OK** (0 синтаксических ошибок);
- JSON-валидация всех 3 конфигов — **3/3 OK**;
- импорт-проба: `build_exe.py` — **OK** (единственный модуль без GUI-зависимостей);
- smoke-статика: точки входа (`if __name__ == "__main__"` — во всех 8), mainloop/create_window присутствуют;
- `unzip -t` архива — OK; SHA-256 копии = оригиналу.

## 5. Интерпретация (честная фиксация)

- **Ни одно приложение не было запущено до работающего GUI** — причина: отсутствие `tkinter`/`webview`/`Pillow`/`reportlab` на сервере, а не доказанная ошибка приложения.
- Статус по критерию промта: **BLOCKED — APPLICATION DOES NOT START (в данной среде)** с конкретной причиной: недостающие зависимости + отсутствие X-дисплея для headless-пробы Tk (xvfb-run есть, но tkinter отсутствует — установка запрещена правилами).
- Утверждение «приложения работают на Windows-машине пользователя» — **не проверено и не утверждается**; косвенные признаки (собранные EXE в `dist/`, `C:/Users/777` в spec, `notepad`/`os.startfile`) указывают, что автор запускал их на Windows.

## 6. Endpoints/страницы

- Сетевых endpoints нет (offline-приложения). «Страницы» = окна GUI: меню обёртки + 5 вкладок-модулей; 2 webview-окна (макеты, ЧПУ) с вкладками «Расчёт/Справочники/Форма».

## 7. Базовый пользовательский сценарий

- Не выполнен (блокер §5). Запланирован на этап реализации: запуск обёртки под Windows/X11 с установленными зависимостями и прогон «расчёт → в смету → CSV».

## 8. DoD этапа

- [x] команда запуска определена для каждого приложения;
- [x] приложение попытались запустить (8/8);
- [x] результат зафиксирован;
- [x] ошибки зафиксированы (все — env-блокеры);
- [ ] основные endpoints/страницы проверены интерактивно — **не выполнено** (блокер);
- [ ] базовый пользовательский сценарий выполнен — **не выполнено** (блокер).
