# WF_TECHNICAL_AUDIT.md — технический аудит WorkflowForms

> Статус: COMPLETE (в рамках бинарного аудита) · Дата: 2026-09-07 · Факты — из конфигов, deps.json, строк DLL; гипотезы помечены (Г).

## 1. Архитектура

- Классическая **клиент-серверная low-code платформа** (Workflow Systems, © 2011-2023, v3.6.0.345):
  - клиент WinForms/WPF-гибрид (.NET Core 3.1) рендерит XML-формы;
  - сервер **WorkflowEngine** (отсутствует в архиве) — хранит формы/данные (порт 9400);
  - UpdateService (ASP.NET Core) — доставка обновлений; Updater — их применение.
- Модульность: Commands/Conditions/DataConnections/Controls/FormObjects — расширяемые слои платформы.

## 2. Backend

- Собственной БД в архиве нет; данные — через SQL-DataConnections к внешней БД (Г: MS SQL, типично для WorkflowEngine).
- UpdateService — единственный собственный веб-сервис (обслуживает автообновление, порт 5001, IIS).

## 3. Frontend

- WinForms + WPF-гибрид (PresentationFramework + System.Windows.Forms + WindowsFormsIntegration), OpenTK (OpenGL-контролы), SkiaSharp/LiveCharts для графиков.
- 12+1 локалей системных ресурсов; собственные строки — по ключам (локализация интерфейса платформы возможна).

## 4. API

- Client → WorkflowEngine: HTTP `ServerUrl` (порт 9400, таймаут 1 час) — протокол не задокументирован в архиве (Г: проприетарный REST/свой).
- UpdateService: HTTP 5001 (web.config IIS inprocess).

## 5. Database

- Отсутствует в архиве (0 файлов БД; Thumbs.db — не БД). Схема неизвестна.

## 6. Business logic / Calculator engine

- CopyCentre: модели с параметрами, до 10 тиражных диапазонов цен, до 5 опций услуги, материалы, импорт прайсов из Excel (шаблон + Temp-таблицы), настраиваемые отчёты. **Это ближайший родственник калькуляторов «Калькуляторы.zip»** (тиражные диапазоны, материалы, себестоимость).
- NCalc-формулы + Scriban-шаблоны — вычислимая логика внутри форм.

## 7. Dependencies

- Полный self-contained рантайм 3.1.25 (498 МБ); сторонние: Newtonsoft, RestSharp, WebSocket4Net, NPOI, OpenXml, Office Interop (требует установленный MS Word), LiveCharts, SkiaSharp, OpenTK, Serilog, SharpZipLib, NCalc, Scriban.

## 8. Security

- **Хардкод-credentials в конфигах** (гостевой вход включён, MasterKey в открытом виде) — CRITICAL при внедрении; ротация обязательна.
- `AllowedHosts: *` в UpdateService; HTTP (не HTTPS) для ServerUrl/ServiceUrl — трафик в открытой сети.
- Office Interop на сервере — анти-паттерн (Г: используется в экспорте Word).

## 9. Error handling

- Ключи ошибок форм (`form_load_error` и ~40 других) — централизованная схема; логирование в Windows EventLog + Serilog (UpdateService).

## 10. Performance

- CheckBinaryFiles/UseSourceCache — настройки производительности присутствуют; PerformanceCheckingMode — профилировочный режим. Проблем не зафиксировано.

## 11. Testing

- Тестов в дистрибутиве нет (ожидаемо для бинарной поставки).

## 12. Code duplication

- 3 полные копии рантайма (клиент/Updater/UpdateService — PresentationFramework 15.8 МБ ×3 и т.д.) — раздутый дистрибутив.

## 13. Technical debt

- **EOL-рантайм**: .NET Core 3.1 — поддержка Microsoft закончилась 13.12.2022; сегодня (2026) — уязвимости без патчей.
- Thumbs.db в поставке; 9 PDB-файлов (символы отладки) — утечка внутренней структуры.
- Office Interop-зависимость от установленного MS Office.

## 14. Scalability

- Платформа масштабируема дизайном (модули, XML-формы, SQL-сервер), но требует WorkflowEngine-сервер и Windows-инфраструктуру.

## 15. Реестр проблем

| ID | Проблема | Доказательство | Severity | Влияние | Рекомендация |
|---|---|---|---|---|---|
| W-01 | Нет исходников (только бинарники) | 0 .cs/.csproj на 1588 файлов | CRITICAL | невозможна модификация/аудит логики | получить исходники у поставщика ИЛИ строить целевое на своём стеке |
| W-02 | WorkflowEngine-сервер отсутствует | app.config ServerUrl:9400, нет файлов | CRITICAL | клиент неработоспособен | запросить серверную поставку/доступ |
| W-03 | XML-формы (Start.xml, CopyCentreStart.xml) отсутствуют | StartFormFileName, find=0 | CRITICAL | даже с сервером старт-форма не в архиве | запросить каталог Projects/ |
| W-04 | Хардкод-credentials (гость+MasterKey) | app.config / dll.config | CRITICAL (при внедрении) | несанкционированный доступ | ротация, отключить AnonymousLogin |
| W-05 | .NET Core 3.1 EOL | runtimeconfig 3.1.25 | HIGH | уязвимости, нет патчей | план миграции рантайма или замена продукта |
| W-06 | HTTP вместо HTTPS | ServerUrl/ServiceUrl http:// | HIGH | перехват трафика/данных | TLS |
| W-07 | EOL/устаревшие зависимости (Office Interop) | deps.json | MEDIUM | хрупкость экспорта Word | OpenXml SDK вместо Interop |
| W-08 | Раздутый дистрибутив ×3 рантайма | 498 МБ, 1557 DLL | LOW | вес, обновления | publish-trim в целевом |
| W-09 | PDB-символы в поставке | 9 .pdb | LOW | утечка структуры | удалить из дистрибутива |
| W-10 | HelpDesk-функциональность неизвестна | только identity-строки | MEDIUM | нельзя оценить ценность модуля | декомпиляция/док поставщика (отдельное подтверждение) |

## 16. DoD

- [x] слои проанализированы; [x] проблемы с доказательствами; [x] критические выделены (W-01…W-04); [x] факты/гипотезы разделены; [x] рекомендации привязаны.
