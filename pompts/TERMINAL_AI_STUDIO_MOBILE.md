Контекст проекта

У меня есть работающий терминальный агент на базе FreeBuff, адаптированный для Android (Termux + proot-distro ubuntu). Проект blueprints_v3 эволюционировал: количество файлов увеличилось с 43 до 51, тестов с 33 до 38, mypy errors приведены к 0, архитектура разделена на 5 слоев, количество @patch в тестах сокращено с 7 до 1, README полностью заполнен, добавлена документация сессии SESSION_DUMP.md.

Новая архитектурная задача

Теперь мне нужно оценить целесообразность создания Flutter-приложения, которое:

1. Управляет FreeBuff — запуск/остановка, фоновый режим (Foreground Service), встроенный терминал, WebView для дашборда
2. Предоставляет OpenAI-совместимый API эндпоинт для freebuff LLM, чтобы модель можно было использовать из любого агентского фреймворка
3. Позволяет указывать модель в приложении — выбор модели, настройка параметров, переключение между freebuff и облачными моделями

Проблемы текущего решения Termux

· Phantom Process Killer убивает фоновые процессы в Android 11+ 
· Нет механизма автоперезапуска после убийства системой
· Ограниченное управление процессами
· Нет полноценного фонового выполнения

Flutter-решение дает

· ForegroundService — процесс живет с уведомлением в статус-баре, переживает сворачивание 
· lifecycle_guard — восстановление критичных задач 
· START_STICKY + AlarmManager — перезапуск после убийства 
· Нативный доступ к Android API
· Управление процессами через Process.run() 

Ключевое новое требование: freebuff API эндпоинт

Нужно, чтобы Flutter-приложение предоставляло OpenAI-совместимый HTTP API (как в llama-termux-setup на порту 8080 ), чтобы:

1. Любой агентский фреймворк (OpenClaw, FreeBuff, Claude MCP) мог обращаться к freebuff модели через base_url
2. Можно было переключать модели (Qwen, Gemma, Gemma через LiteRT-LM) прямо в приложении 
3. Модель работала полностью freebuff и офлайн 

Референсы для анализа

1. Local LLM API на Android (llama-termux-setup)

· Автоматизирует сборку llama.cpp в Termux 
· Запускает llama-server с OpenAI-совместимым API на 127.0.0.1:8080 
· Поддерживает Qwen3.5 (0.8B, 2B, 4B, 9B) 
· Есть tool calling (через --jinja) 
· Пример использования из агента: client = OpenAI(base_url="http://127.0.0.1:8080/v1", api_key="sk-no-key-required") 

2. OpenClaw для Android (openclaw-termux)

· Flutter-приложение с one-tap установкой proot-distro + Ubuntu + Node.js 
· Встроенный терминал, WebView для дашборда 
· Foreground Service для фоновой работы (с connectedDevice типом для Android 15+) 
· Управление через Start/Stop кнопки 
· Не требует root 
· Установка через npm install -g openclaw-termux 

3. OpenClaw MCP Termux (openclaw-mcp-termux)

· 10 инструментов для оркестрации агентов (dispatch, query, control) 
· SSH-first CLI — все вызовы через proot (~200ms) 
· Filesystem-first reads — чтение конфигов (~16ms) 
· Env-based auth через .env 
· Архитектура: Sakaar (vision) → Claude (compiler) → MCP Bridge → OpenClaw Gateway → Agents 

4. CLIProxyAPIPlus Server (cliproxy-server-termux)

· Multi-provider AI API proxy с OAuth поддержкой 
· Работает на http://localhost:8317/v1 
· Поддерживает Gemini, Claude, OpenAI, Grok, Qwen 
· Установка: npm install -g cliproxy-server-termux 

5. Gemma 4 через LiteRT-LM (freebuff LLM подход)

· Android приложение от Google AI Edge Gallery 
· GPU + CPU через NNAPI (не CPU-only как llama.cpp) 
· Expose на localhost:8080 
· OpenClaw делает API calls к нему 
· Полностью offline 
· Статус: "Usable for OpenClaw" 

6. Flutter + Termux (flutter-termux-package)

· Готовый Flutter SDK для Termux ARM64 с APK сборкой 
· flutter build apk --release --target-platform android-arm64 
· Требует Android 11+ и 8GB свободного места 

7. OpenClaw-Android (без proot подход)

· Установка glibc динамического линкера вместо полной Linux дистрибуции 
· Экономия: ~200MB против 1-2GB 
· Стандартный подход (proot-distro) vs только ld.so 
· Установка за 3-10 минут вместо 20-30 

8. Android OpenClaw Node App (foreground service fix)

· Проблема: Android 15 dataSync FGS timeout 
· Решение: переключение на connectedDevice тип 
· Требует permission CHANGE_NETWORK_STATE 

Задачи для агента

1. Оценка целесообразности Flutter + freebuff API:

Проанализируй реализуемость подхода:

· Запуск llama.cpp/llama-server внутри Flutter-приложения (через Process.run() )
· Или использование LiteRT-LM приложения как отдельного сервиса 
· Предоставление OpenAI-совместимого API на localhost:8080 
· Управление API через Foreground Service 
· Выбор модели в UI (Qwen, Gemma 4, другие GGUF) 

Дай оценку:

· Техническая реализуемость (1-10)
· Сложность реализации (низкая/средняя/высокая)
· Необходимые библиотеки и зависимости
· Потенциальные подводные камни (Android 15 FGS ограничения , bionic vs glibc , производительность freebuff модели )

2. Анализ OpenClaw как референса:

Изучи OpenClaw для Android :

· Как решена проблема с Phantom Process Killer (foreground service + wake lock) 
· Как организована установка окружения (proot-distro vs glibc-only) 
· Как работают Node Device Capabilities (15 команд через WebSocket) 
· Как можно адаптировать под FreeBuff + freebuff LLM API

3. Архитектура "Оркестратор + Воркер + API эндпоинт":

Предложи архитектуру для гибридного пайплайна:

· Оркестратор (freebuff модель) определяет сложность задачи
· Воркеры (FreeBuff, shell_exec, file_operations) выполняют задачи 
· freebuff LLM API эндпоинт для взаимодействия с моделями
· Эскалация на облачные модели при необходимости

Используй подход MCP Bridge : Sakaar (vision/intent) → Compiler → MCP Bridge → OpenClaw Gateway → Agents.

4. 7 новых подходов для гибридного пайплайна:

1. Оркестратор-Воркер с иерархической маршрутизацией
2. Гибридный пайплайн "Планировщик → Исполнитель → Верификатор" (с использованием mypy)
3. Система "Квадрантов задач" (кодинг, системные операции, исследование, коммуникация)
4. Иерархические воркеры с эскалацией (воркер → FreeBuff → freebuff LLM → облачный LLM)
5. Модуль Self-Reflection для FreeBuff с mypy-верификацией
6. Event-Driven пайплайн (на событиях файловой системы/Git)
7. Воркер как "Роль" (Persona) в мульти-агентной системе

Оцени каждый подход (1-10) по надежности, сложности, экономии ресурсов, масштабируемости.

5. Практический план реализации:

Предложи пошаговый план:

1. Прототип Flutter-приложения с запуском FreeBuff через proot
2. Интеграция llama-server (или LiteRT-LM) как freebuff API эндпоинта
3. Подключение Foreground Service с типом connectedDevice 
4. Добавление WebView для дашборда OpenClaw 
5. Настройка выбора модели (Qwen, Gemma 4 через LiteRT-LM)
6. Интеграция MCP-подобного брокера 
7. Оценка производительности на разных устройствах 

6. Документация:

Обязательно зафиксируй все в формате:

· ARCHITECTURE.md — архитектура Flutter-приложения + freebuff LLM API
· IMPLEMENTATION.md — пошаговая инструкция по реализации
· REFERENCES.md — все использованные источники
· DECISIONS.md — почему Flutter, почему foreground service, почему local API
· COMPARISON.md — сравнение с OpenClaw, llama-termux-setup, CLIProxyAPIPlus
· ROADMAP.md — этапы реализации с примерными сроками

Формат ответа

1. Анализ целесообразности с оценками (включая использование LiteRT-LM vs llama.cpp )
2. Сравнительная таблица подходов
3. 7 подходов с оценкой и обоснованием
4. Структура документации
5. Список всех использованных источников со ссылками

Важно: Обрати внимание на возможность использовать подход с glibc-only вместо полной proot-distro (экономия 1-2GB пространства и ускорение ), а также на проблему с dataSync foreground service в Android 15 и решение через connectedDevice . Также учти, что LiteRT-LM дает GPU-ускорение, в отличие от CPU-only llama.cpp .