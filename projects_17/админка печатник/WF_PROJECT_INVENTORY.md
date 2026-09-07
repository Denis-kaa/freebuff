# WF_PROJECT_INVENTORY.md — инвентаризация WorkflowForms

> Статус: PARTIAL (бинарная дистрибуция: инвентаризация по метаданным/строкам/конфигам; декомпиляция кода не выполнялась) · Дата: 2026-09-07

## 1. Таблица модулей

| ID | Модуль | Назначение (доказательство) | Стек | Точка входа | Статус |
|---|---|---|---|---|---|
| W1 | WorkflowForms (клиент) | рендер XML-форм, события форм, формулы, команды | .NET Core 3.1 WinForms/WPF | `WorkflowForms.exe` | не запускался (Windows-only) |
| W2 | WorkflowServer | серверная часть DataConnections: запросы, фильтры, кэш | .NET Core 3.1 lib | — | — |
| W3 | CopyCentre | модуль расчёта копицентра: модели, тиражные диапазоны 1–10, импорт Excel, шаблоны | .NET Core 3.1 lib | `CopyCentre\Forms\CopyCentreStart.xml` (файл НЕ приложен) | — |
| W4 | HelpDesk | модуль HelpDesk (крупнейший own-модуль 630 КБ) | .NET Core 3.1 lib | — | — |
| W5 | Commands | библиотека команд (SMTP-рассылка, экспорт, работа с файлами, SQL) | lib | — | — |
| W6 | Conditions | условия/правила (regex, comparison, hotkeys) | lib | — | — |
| W7 | DataConnections | соединения данных (SQL, массивы, деревья Parent/Child, refresh-интервалы) | lib | — | — |
| W8 | Controls (Simple/Complex/Base/DBColumn) | контролы форм (таблицы с фильтрами/суммами, комбо, календари и т.д.) | lib | — | — |
| W9 | FormObjects | объекты форм (графика, агрегаты AVERAGE/COUNT, авторизация) | lib | — | — |
| W10 | Updater | автообновление клиента | .NET Core 3.1 | `Updater/WorkflowFormsUpdater.exe` | — |
| W11 | UpdateService | сервис обновлений (ASP.NET Core, IIS inprocess) | ASP.NET Core 3.1 | `UpdateService/WorkflowFormsUpdateService.exe`, `http://localhost:5001` | — |

## 2. Функциональный инвентарь (по строкам/типам из DLL)

### Платформа форм (W1)
- XML-схема форм: `Form/Includes/Include`, `Form/MyObjects/MyObject`, атрибуты FormTitle/FormState/FormBorderStyle; события: Click/DoubleClick/KeyDown/KeyPress/Resize/VisibleChanged/FormClosed; состояние: RestoreLastFormState, SaveOnFormClose; сообщения об ошибках — ключи (`form_load_error`, `cant_load_start_form`).
- Механика include-форм, формул NCalc, шаблонов Scriban, логирования в Windows EventLog («Workflow Technology» / «Workflow Forms»).

### CopyCentre (W3) — ключевой для объединения
- Модели расчёта: `ModelId`, `ModelTitle`, `ModelParameterId`, `ParameterTypeName/Hint`, `ModelQuantityRangeId`;
- тиражные диапазоны: `QuantityRange1..10Cost` — до 10 ценовых диапазонов на услугу;
- `ServiceOptionTitle1..5` — до 5 опций услуги; `MaterialExpense`, категории/единицы материалов;
- импорт из Excel: `ImportFile`, `TemplateFileName`, `TempInsertSqlQuery`, парсер чисел с диапазонами (regex `(?<min>…)( (?<max>…))?`), промежуточные таблицы `TempModel/TempInsert`, отчёт Success/Failed;
- экспорт отчётов: `OptionHeaders/CostHeaders/MaterialExpenseHeaders/MaterialInfoHeaders`, колонки/заголовки настраиваемые.

### HelpDesk (W4)
- Содержимое по строкам не раскрыто (только identity-строки) — **неизвестно**, помечено.

### Commands (W5) — обнаружены возможности
- Email (SMTP: сервер/порт/SSL/автор/копии), экспорт файлов (ExportFileName/Path, FilterIndex), работа с буфером, SQL-команды (DataSqlQuery), копирование файлов, управление формами (ChangeForm/HideThisForm/Exit), таймеры/подписки (SimpleControls: Interval/Subscribe/Start/Stop).

### DataConnections (W7)
- SQL-запросы с фильтрами (Filter/FilterField/FilterValue, FilterByNullValue), поля и под-поля, деревья (Parent/Child/Ancestor/Descendant/HasChildren), автообновление по интервалу (Hours/Minutes), ручное обновление, зависимые соединения (DependOn), форматирование полей.

### Conditions (W6)
- Сравнения, regex, выражения, клавиши-модификаторы, счётчики (Min/MaxCount), реакции на закрытие форм.

### Controls (W8)
- Таблицы: вставка/удаление строк, фильтры по колонкам, сортировка, суммы по колонкам (ColumnSum), уникальные значения, комбо-колонки, контекстные меню, настройки вида (белая/чёрная тема колонок);
- агрегаты в FormObjects: AVERAGE, COUNT, Calculate.

## 3. Конфигурация (факты, секреты замаскированы)

- `app.config` (шаблон разработчика): ServerUrl `http://localhost:49707`, StartForm `C:\Inetpub\wwwroot\WorkflowEngine\Projects\Start.xml`, AnonymousLogin=True (гостевой доступ **включён**, пароль-заглушка), SystemLocale en-US.
- `WorkflowForms.dll.config` (боевой): ServerUrl `http://192.168.0.12:9400`, StartForm `1. CopyCentre\Forms\CopyCentreStart.xml`, AppDataFolder `WorkflowForms\CopyCentre`, SystemLocale ru-RU, UseSourceCache=True, CheckBinaryFiles=True, обновление каждые 5 минут.
- **WorkflowEngine-сервер (порт 9400) в архиве ОТСУТСТВУЕТ** — клиент без него неработоспособен (проверка запуска невозможна по определению).
- UpdateService: Serilog (файлы+консоль+EventLog), `AllowedHosts: *`, hosting 5001, IIS inprocess.
- ⚠️ В конфигах найдены **хардкоженные учётные данные** (AnonymousUserName/AnonymousPassword/MasterKey) — в отчётах не раскрываются; рекомендация: ротация при внедрении.

## 4. Неизвестные элементы (явно)

- Внутренняя логика всех модулей (только компилированный IL) — декомпиляция не выполнялась (вне рамок READ-ONLY аудита; при необходимости — отдельным шагом с подтверждением).
- Формы XML (Start.xml, CopyCentreStart.xml), база данных WorkflowEngine, схема БД — **не приложены** в архиве.
- Реальная функциональность HelpDesk — неизвестна.
- Лицензия/владелец платформы Workflow Systems — неизвестен (© 2011-2023 в метаданных).

## 5. DoD

- [x] каталоги просмотрены; [x] точки входа найдены (3 exe); [x] стек определён; [x] модули перечислены; [x] API-слой описан (ServerUrl/ServiceUrl); [x] сценарии — по строкам; [x] неизвестное помечено явно.
