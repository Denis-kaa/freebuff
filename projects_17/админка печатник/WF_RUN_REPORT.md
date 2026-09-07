# WF_RUN_REPORT.md — проверка запуска WorkflowForms

> Статус: **BLOCKED — WINDOWS-ONLY BINARY DISTRIBUTION** · Дата: 2026-09-07

## 1. Причина блокировки (фактическая)

- Все 3 исполняемых файла — **PE32+ x86-64 для MS Windows** (`file`: GUI ×2, console ×1); Linux-запуск невозможен без Wine/Windows.
- Клиент требует внешний **WorkflowEngine-сервер** (`ServerUrl http://192.168.0.12:9400`), которого нет в архиве; StartForm `CopyCentreStart.xml` также не приложен.
- UpdateService рассчитан на IIS/Windows hosting (web.config, AspNetCoreModuleV2).

## 2. Что проверено без запуска (факты)

- `file` PE-заголовков всех 3 EXE — подтверждено Windows x64;
- runtimeconfig: netcoreapp3.1, self-contained 3.1.25 (клиент и Updater), UpdateService — framework-dependent (328 libs в deps);
- deps.json: собственные пакеты WorkflowForms/WorkflowFormsUpdateService 1.0.0;
- конфиги читаемы и валидны (XML/JSON);
- версия дистрибутива 3.6.0.345 (UpdateCompatibility.info);
- .db в архиве — Thumbs.db (кэш эскизов Windows), НЕ база данных (проверено: Composite Document File, не SQLite).

## 3. Команды запуска (определены, но не выполнимы здесь)

- Клиент: `WorkflowForms.exe` (Windows, рядом с WorkflowForms.dll.config).
- Updater: `Updater/WorkflowFormsUpdater.exe`.
- UpdateService: IIS-деплой каталога `UpdateService/` (или `WorkflowFormsUpdateService.exe` под Kestrel, порт 5001).

## 4. Smoke-тесты, выполненные вместо запуска

- Структурный парсинг deps/runtimeconfig — OK;
- извлечение строк-ключей платформы и модулей — OK (инвентаризация функций);
- grep по конфигам на секреты — найдены хардкод-credentials (замаскированы; рекомендация ротации);
- проверка отсутствия XML-форм и БД — подтверждено (find: 0 файлов).

## 5. DoD

- [x] команда запуска определена; [x] запуск попытались оценить (PE-проверка, отсутствие зависимостей-сервера); [x] результат зафиксирован; [x] ошибки/блокеры зафиксированы; [ ] endpoints/страницы интерактивно — **невозможно** (Windows-only + нет сервера); [ ] пользовательский сценарий — **невозможно**.
- Статус по критерию промта: **BLOCKED — APPLICATION DOES NOT START (в данной среде)** с конкретной причиной: Windows-only бинарник + отсутствующий WorkflowEngine-сервер + отсутствующие XML-формы.
