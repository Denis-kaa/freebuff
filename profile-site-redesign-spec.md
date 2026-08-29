# Спецификация редизайна profile site

## Anti-slop правила (аудит v2)

Основано на исследовании «AI Design Slop: 16 Patterns» (аудит 1590 лендингов, Adrian Krebs; пересказ: developersdigest.tech/blog/ai-design-slop-and-how-to-spot-it, оригинал: adriankrebs.ch/blog/design-slop). Текущая версия сайта попадает в несколько паттернов — устранить:

| Паттерн-маркер | Запрещено | Вместо этого |
|---|---|---|
| Serif-italic акцентное слово в hero | em-курсив внутри рубленого заголовка | цельная типографика Piazzolla (serif с кириллицей) |
| All-caps mono-лейблы секций | `DM Mono` + uppercase eyebrows | подписи в Golos Text, строчный регистр, номер + тире |
| Светящиеся орбы и glow-box-shadow | цветные box-shadow, радиальные glow-поля | плоские цветовые поля, hairline-линии |
| Marquee и ✦-разделители | бегущая строка, спарклы | статичная строка контекста в hero |
| Одинаковые карточки с иконками | сетки повторяющихся card | редакционный индекс-список строк |
| Пронумерованные шаги-карточки | 01/02/03 ring-анимации | нарративный блок «Подход» |
| Стат-баннеры | ряды метрик-чипов | цифры встроены в предложения |
| Стоковые decorative-фото | Unsplash-абстракции | структурная графика, изображения только предметные |
| Fake-статусы «● LIVE/online» | имитация живой системы | честные текстовые статусы |

Шрифтовая система v2 (кириллица): Piazzolla (display serif) + Golos Text (body) + IBM Plex Mono (только реальные технические данные: стек, версии, команды).

Архитектура v2: многостраничность на hash-роутере (`#/project/:id`) — 8 страниц проектов, у каждой свой визуальный мотив (blueprint, pipeline, ledger, terminal, time-ledger, chat, board, cinema) и свой приглушённый акцентный цвет. Общая система: тёплая ivory-бумага, тёплый obsidian, hairline-разделители, асимметричная editorial-сетка.

Видео-поиск: прямые ссылки на YouTube через поиск не стабильно находятся; запросы для самостоятельного поиска: `vibe coded website design fix`, `AI design slop landing page`, `make your ai website not look generic`.

## Решения

- отдельный standalone React-проект;
- один гибридный режим без переключателя;
- позиционирование: AI-инженер, интегратор LLM, creator и Visual Systems Creator;
- визуальный язык: matte obsidian, immersive, editorial, restrained motion;
- смешанный motion: медленный immersive hero + точные быстрые UI-реакции;
- временно допустимы внешние изображения, аккуратно подобранные и задокументированные;
- кейсы: preview при наведении/фокусе + подробности по клику;
- публикация на доступном VPS без домена пока;
- SSH-конфигурацию искать по имени `whimco`, не выводить секреты и приватные ключи.

## Позиционирование

Сайт должен явно демонстрировать две взаимосвязанные способности:

1. **Использование AI для создания работающих систем:** LLM, агенты, RAG, API-интеграции, тестирование, автоматизация и delivery.
2. **Создание визуальных систем:** композиция, дизайн интерфейсов, motion, visual direction, design systems и AI-assisted visual prototyping.

Не заявлять неподтверждённый титул senior UI/UX designer. Использовать доказательное название `Visual Systems Creator` и формулировку «создаю визуальные системы и интерактивные прототипы».

## React MVP

- Vite + React + TypeScript, если локальные конвенции позволяют;
- минимум зависимостей;
- компоненты: `App`, `Hero`, `CaseGrid`, `CaseCard`, `SkillCards`, `InteractiveLab`, `CreativeLab`, `Contact`;
- CSS tokens для obsidian-палитры;
- изображения через локальные asset-пути с remote fallback только для временных placeholders;
- keyboard/focus support;
- `prefers-reduced-motion`;
- SSR не требуется на первом этапе;
- данные кейсов вынести в типизированный массив.

## Визуальная система

- background: obsidian `#0b0d0f`, graphite `#15191c`, mineral light `#e7e5df`;
- accents: muted jade/cyan и редкий amber;
- matte texture через CSS gradients/noise без тяжёлых библиотек;
- скругления умеренные, без повсеместного glassmorphism;
- крупная editorial typography и строгая сетка;
- анимации: opacity/transform/filter, не менять layout на каждом кадре;
- соблюдать контраст текста и не прятать информацию только в hover.

## Case interaction

- hover/focus показывает subtle visual preview;
- click/tap раскрывает problem → solution → result → proof;
- клиентские кейсы остаются анонимными до разрешения;
- изображения не должны выдавать реальные private URLs, имена или данные;
- рядом с визуалом показывать статус `own product`, `anonymous client case` или `prototype`.

## Временные изображения

До создания собственных изображений допускаются remote abstract visuals только в качестве временных placeholders. Не использовать случайные фотографии людей, бренды или изображения с сомнительной лицензией. Источники и rationale фиксировать в `profile-site-design-prompts.md`; перед production заменить на локальные WebP/AVIF.

## VPS

Сначала проверить наличие deploy-скрипта/SSH-конфига. Не выполнять публикацию, перезапуск сервисов или изменение production без явного подтверждения цели и адреса. Для безопасного этапа подготовить build и deployment instructions. Если найден рабочий VPS и подтверждён target, использовать отдельный каталог сайта и backup перед заменой.

## Acceptance criteria

- сайт запускается как React-приложение;
- hero за 5 секунд объясняет AI + visual systems positioning;
- Freebuff, production stabilization и investment analytics представлены как главные кейсы;
- есть видимые motion-переходы, но контент доступен без motion/JS fallback;
- есть визуальные capability-карточки;
- временные изображения не мешают лицензированию и легко заменяются;
- мобильная версия работает от 360 px;
- `npm run build` проходит;
- deployment на VPS не выполняется до подтверждения конкретного target.
