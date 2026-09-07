# WF_SOURCE_MANIFEST.md — манифест исходника WorkflowForms

> Статус: COMPLETE · Дата: 2026-09-07 · Правила: SERVER_ACCESS_WHIMCO.md (прочитаны ранее в сессии)

## 1. Архив

| Параметр | Значение (проверено) |
|---|---|
| Локальный оригинал | `projects_17/админка печатник/WorkflowForms.zip` |
| Размер | 216 233 336 bytes |
| SHA-256 | `31fe7537fa028ccca91f8282f382413f3d07b974e40429bc2f89d04d5dd4eeeb` |
| Целостность | `unzip -t` → No errors detected |
| mtime оригинала | 2026-09-07 11:32:30 UTC (не изменён) |
| Серверная копия | `/opt/freebuff/projects_17/админка печатник/WorkflowForms.source.zip` (SHA совпадает) |
| Распаковка | `/opt/freebuff/projects_17/админка печатник/worktree_wf/WorkflowForms/` |

## 2. Объём (проверено find)

- файлов: **1588**; размер: **498 МБ**;
- по типам: **1557 DLL**, 3 EXE, 9 PDB, 9 JSON, 3 config, 3 md, 1 png, 1 gif, 1 db (Thumbs.db — Windows-кэш эскизов, НЕ база данных);
- **исходного кода нет**: 0 `.cs`, 0 `.csproj`, 0 `.sln`, 0 `.xaml`, 0 форм-XML.

## 3. Состав дистрибутива

```
WorkflowForms/
├── WorkflowForms.exe + WorkflowForms.dll     # главный клиент (WinForms/WPF, .NET Core 3.1.25, win-x64, self-contained)
├── WorkflowForms.dll.config / app.config     # конфиг клиента (2 варианта настроек)
├── WorkflowForms.deps.json / runtimeconfig.json
├── WorkflowServer.dll                        # серверная логика данных (DataConnections)
├── CopyCentre.dll                            # модуль «Копи-центр»: модели расчёта, тиражные диапазоны, импорт из Excel
├── HelpDesk.dll                              # модуль HelpDesk (630 КБ — крупный)
├── Commands.dll / Conditions.dll / DataConnections.dll / FormObjects.dll
├── SimpleControls.dll / ComplexControls.dll / BaseControls.dll / DatabaseTableColumnControls.dll
├── Common.dll / DataTypes.dll / Exceptions.dll / Extensions.dll
├── Updater/          # WorkflowFormsUpdater.exe — автообновление клиента
├── UpdateService/    # WorkflowFormsUpdateService.exe — ASP.NET Core сервис (IIS inprocess, http://localhost:5001)
├── ru/ de/ fr/ …     # 13 локалей × 16 ресурсов (.NET satellite assemblies)
└── Icons/            # splash.png, waiting.gif, Thumbs.db
```

## 4. Идентификация платформы

- Продукт: **Workflow Forms** («Workflow Technology», Copyright Workflow Systems 2011-2023 — из версии DLL).
- Версия дистрибутива: **3.6.0.345** (`UpdateCompatibility.info`).
- Рантайм: .NET Core 3.1.25 (netcoreapp3.1, self-contained win-x64) — 3 приложения из одного решения.
- Архитектура: клиент-серверная low-code платформа форм/воркфлоу: формы описываются XML (формы не приложены), рендерятся клиентом; данные — через DataConnections (SQL); логика — Commands/Conditions; формулы — NCalc; шаблоны — Scriban; Office-файлы — NPOI/OpenXml; графики — LiveCharts/SkiaSharp; обновление — свой Updater + UpdateService.

## 5. Стек (факты)

- .NET Core 3.1 (WinForms + WPF-гибрид), ASP.NET Core (UpdateService), IIS hosting (web.config AspNetCoreModuleV2);
- библиотеки: Newtonsoft.Json, RestSharp, WebSocket4Net/SuperSocket, NCalc, Scriban, NPOI (+OOXML), DocumentFormat.OpenXml, Microsoft.Office.Interop.Word, LiveChartsCore+SkiaSharp, OpenTK (OpenGL), Serilog, ICSharpCode.SharpZipLib;
- 12+1 локалей интерфейса (cs de es fr it ja ko pl pt-BR ru tr zh-Hans zh-Hant) — ресурсы только системных сборок; локализация самой платформы — в ключах-строках.

## 6. DoD

- [x] оригинал не изменён; [x] перенесён в разрешённую область (копия); [x] архив читается; [x] распакован (1588 файлов); [x] структура проверена; [x] исходник/копия разделены; [x] манифест создан.
