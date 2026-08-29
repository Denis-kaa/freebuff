# LESSONS — project-local narrow для ROADMAP-LA-001 (промт 69 × 70)

> **Узкий файл** (per промт 70 шаблон): только находки, всплывшие ПРИ РАБОТЕ над этой задачей.
> Cross-cutting платформенные находки — ОДНОЙ строкой в `core_02/LESSONS.md`, не здесь.

---

## Closed findings

- **LA-1** (Step 1, исследование стека): реальный стек пользователя невозможно вывести из README — файлы пишутся агентами; выводить из живых артефактов (резюме, ledger, portfolio meta, bash_history). Подтверждено: `KWORK/projects_ledger.md` дал реальные цены заказов, которых нет в README.
- **LA-2** (Step 1, Attract): Attract-модуль **не инверсия** LDE промта 69, а переиспользование с query-driven доработкой — полярность L2 («ищу исполнителя» = лид) уже совпадает. Урок: не усложнять терминологией то, что является reuse.
- **LA-3** (Step 1, audit): факты из MANIFEST/README агентских проектов могут расходиться с реальностью (`chaos_monkey_parser` vs реальный `gemini_chaos_parser.py`) — проверять файлы `ls`-ом перед утверждением.
- **LA-4** (Step 2, шаблон): 3 precedents ROADMAP сходятся на ~11 общих секциях (explain-first, roll-up, границы, capability-check, gates, карта файлов, atomic-шаги, риски, acceptance, вопросы, cross-links) — это и есть устойчивый шаблон платформы.
- **LA-5** (Step 4, circuit breaker): размыкание по порогу без учёта `max_attempts` делает circuit breaker недостижимым в `run()` (threshold>attempts → никогда не открывается). Урок: threshold ≤ max_attempts; обязателен cooldown-механизм (half-open probe), иначе breaker «залипает» открытым навсегда.
- **LA-6** (Step 4, изоляция): один общий RetryPolicy на все адаптеры ломает изоляцию источников — сбой одного фида размыкает breaker для остальных. Урок: per-adapter экземпляр (`clone()` от шаблона), не общий объект.
- **LA-7** (Step 4, resume): строковое сравнение id источников ломается на границе разрядности (99999 < 100000). Урок: числовой хвост id сравнивать как int с приоритетом над строковым fallback; resume по id — только для упорядоченных фидов (`ordered=True`), неупорядоченные (Kwork) — через Deduplicator.
- **LA-8** (Step 5, live-verify W-16): dry-run на реальных источниках вскрыл, что **тест-фикстуры расходились с живым HTML**: (a) t.me/s блоки имеют доп. классы (`tgme_widget_message text_not_supported_wrap service_message js-widget_message`) — строгий regex давал 0 лидов; (b) kwork.ru/projects стал **SPA** (статичный HTML = скелет, заказы грузятся JS; все JSON-эндпоинты 404). Урок: при Deploy всегда прогонять dry-run на живых данных и обновлять фикстуры по реальному HTML; SPA-источник без headless — честная диагностика (warning + [***REMOVED***), а не молчаливый 0.
- **LA-9** (Step 5, config): env-поля Config через `os.getenv()` в dataclass-default вычисляются ОДИН РАЗ при импорте — settings.env, загруженный позже, до полей не доходит. Урок: env-поля — через `field(default_factory=...)` (читается при каждом инстанцировании), а файл env грузить на уровне модуля ДО класса.
## Открытые вопросы

- ⏳ **OQ-LA-1** (raised at Task 4 / IDEA EXPLORER W-16): покрывают ли TG-зеркала `@kwork_parsing` и аналоги все нужные разделы Kwork и с какой задержкой? Проверка live — первый шаг Candidate A.
- ⏳ **OQ-LA-2** (raised at Task 4): установим ли Lightpanda в proot-Ubuntu на этой машине (скрипт существует, установка не проверена)? Гейт для Candidate B.
- ✅ **OQ-LA-1†** (raised at Step 2): какой первый источник реализовать в Фазе 3 — Kwork-парсер или TG-агрегатор (по образцу @Golubin_bot)? → **Закрыт (Step 4):** Kwork первым (рекомендация PHASE2 §8), TG-каналы — следом (`tg_channels` из конфига). [closed***REMOVED***
- ✅ **OQ-LA-2†** (raised at Step 2): юр. периметр Attract — какие запросы исключаем (спам-рассылки из `/ВАКАНСИИ/5.md` — красная зона)? Требуется решение пользователя (W-7 policy-гейт). → **Закрыт (Step 4):** спам-зоны исключены L1 policy-гейтом (stopwords казино/реклама/накрутка в `keywords.yaml`). [closed***REMOVED*** 