

Промт для терминального агента: "Интеграция Lightpanda в экосистему Мобильный ТарминAIтор"

---

Контекст проекта

Я разрабатываю проект "Мобильный ТарминAIтор" — терминальный AI-агент для Android (Termux + proot-distro ubuntu). В экосистеме уже есть:

· Оркестратор (локальная LLM: GLM-5.2 / Qwen 3.5)
· Воркеры: FreeBuff (кодинг), shell_exec (системные команды)
· Flutter-приложение (в планах) с Foreground Service

Теперь нужно интегрировать Lightpanda — headless-браузер для веб-автоматизации.

---

Что такое Lightpanda

Lightpanda — headless-браузер, написанный с нуля на Zig для AI-агентов:

· Не форк Chromium/WebKit, а новый движок
· Потребляет в 16 раз меньше памяти (123MB vs 2GB у Chrome)
· Работает в 9 раз быстрее (5s vs 46s на 100 страниц)
· Поддерживает JavaScript, DOM, Fetch, XHR
· Имеет Agent Mode — управление через LLM (OpenAI, Anthropic, Gemini, Ollama)
· Экспортирует PandaScript — исполняемый JavaScript без LLM
· Поддерживает MCP (Model Context Protocol) с изоляцией сессий
· Работает на Linux ARM64 (ваш случай)

---

Задачи по интеграции

1. Установка и настройка:

Разработай пошаговую инструкцию по установке Lightpanda в окружении Termux + proot-distro ubuntu для ARM64:

· Скачивание бинарника (зависимость от glibc — решается через proot)
· Создание wrapper-скрипта для Termux
· Проверка работы (dump URL, CDP server, Agent Mode)
· Настройка автозапуска через Foreground Service (для Flutter-приложения)

2. Архитектурная интеграция:

Предложи архитектуру, где Lightpanda становится воркером в пайплайне:

· Оркестратор (GLM-5.2) анализирует запрос → определяет, что нужен браузер
· Делегирует задачу воркеру "Lightpanda" через MCP
· Воркер выполняет веб-автоматизацию (поиск, скрапинг, заполнение форм)
· Возвращает результат (JSON, Markdown, PandaScript)
· PandaScript сохраняется для повторного использования без LLM

3. Создание воркера на Python:

Разработай класс LightpandaWorker для оркестратора:

· Метод execute_agent_task(task, provider) — запуск Agent Mode
· Метод run_script(script_path) — запуск PandaScript
· Метод dump_url(url, format) — извлечение контента
· Метод serve_cdp(port) — запуск CDP-сервера для Puppeteer
· Обработка ошибок и логирование

4. Интеграция с MCP-брокером:

Опиши, как подключить Lightpanda MCP-сервер к вашему MCP-брокеру:

· Конфигурация mcpServers для Lightpanda
· Управление сессиями через HTTP (изоляция агентов)
· Использование tools: session_new, session_list, session_close

5. Юзкейсы и сценарии:

Разработай 5-7 практических сценариев использования Lightpanda в вашем проекте:

· Поиск документации по API
· Парсинг статей в Markdown
· Автоматическое тестирование сайта
· Сбор данных с маркетплейсов
· Интерактивный поиск файлов на GitHub
· Заполнение форм и регистрация
· Мониторинг изменений на сайте

6. Экономия ресурсов:

Опиши, как использовать PandaScript для экономии токенов:

· Запись действия через LLM (один раз)
· Сохранение в PandaScript
· Запуск без LLM (бесконечно, бесплатно)

7. Flutter-интеграция:

Предложи, как Lightpanda будет работать в Flutter-приложении:

· Запуск через Process.run() внутри Foreground Service
· Статус-бар с уведомлением о работе браузера
· WebView для отображения результатов
· Кнопки управления (Start/Stop/Pause)

---

Формат ответа

1. Полный гайд по установке (пошагово, с командами)

2. Архитектурная диаграмма (Mermaid) с Lightpanda в пайплайне

3. Код воркера (Python, готовый к использованию)

4. Конфигурация MCP (JSON)

5. 5-7 юзкейсов с примерами команд

6. Инструкция по PandaScript (запись и запуск)

7. Flutter-интеграция (код и настройки)

8. Тесты и диагностика (как проверить работу)

9. Список источников (ссылки на документацию Lightpanda)

---

Документация

Все результаты зафиксировать в:

· docs/LIGHTPANDA_INTEGRATION.md — полный гайд
· docs/WORKERS.md — обновить раздел с воркерами
· docs/ARCHITECTURE.md — обновить архитектурную схему
· src/workers/lightpanda_worker.py — код воркера
· scripts/install_lightpanda.sh — скрипт установки

---

Ссылки на ресурсы

Изучить перед интеграцией:

· GitHub: https://github.com/lightpanda-io/browser
· Agent Mode: https://github.com/lightpanda-io/browser#agent-mode
· MCP Server: https://github.com/lightpanda-io/browser#native-mcp-and-skill
· Пример Puppeteer: https://github.com/lightpanda-io/browser#example-puppeteer-script

---

Важно: Учтите, что Lightpanda требует glibc, но в proot-distro ubuntu это решено. Для ARM64 используйте lightpanda-aarch64-linux. Проверьте, что Docker-образ тоже поддерживает ARM64.
