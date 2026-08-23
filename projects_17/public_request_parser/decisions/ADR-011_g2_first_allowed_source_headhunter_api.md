# ADR-011 — G2: first `allowed` source = HeadHunter API (SRC-011)

> **Статус:** Accepted (conditional activation)
> **Дата:** 2026-08-23
> **Связано:** `SOURCE_POLICY_MATRIX.md` SRC-011, `ROADMAP.md` G2, `POST_MVP_GATES.md`

## Контекст

G2 требует минимум один RSS/Atom/API-источник со статусом `allowed` для
live product. Исследование at найти источник, где пользователи ищут услуги
(спрос), с официальным механизмом доступа и прозрачными условиями.

## Решение

**HeadHunter API — публичный поиск вакансий** (`api.hh.ru/vacancies`) выбран
первым источником со статусом `allowed` (условно):

- официальный механизм: регистрация Приложения на `dev.hh.ru` → уникальный
  API-ключ (§1.1 developer agreement);
- соответствие цели: вакансии = «работодатель ищет исполнителя» (спрос на
  услугу/работу); разрешено использование в целях тематики Сайта
  (§1.5/1.6, §3.3 — поиск работы/сотрудников/рынок труда);
- поля ограничены: id, name, description, alternate_url, published_at,
  employment, experience, salary, area; **резюме/соискатели/контакты — никогда**;
- запрещено изменять материалы (§3.11) — карточка показывает title/описание
  как есть + canonical `alternate_url`;
- запрещено использовать товарные знаки (§3.4) и собирать учётные данные (§3.6);
- TTL текста ограничен (default 7 дней) — согласуется с нашим storage/retention.

**Условия активации** (не выполнены в этом документе, отдельный шаг):
1. регистрация приложения + API-ключ (secret storage);
2. конфиг-включение источника с `policy=allowed+can_poll` (это должен
   использовать `HttpFeedAdapter`/новый HH-adapter);
3. canary-запуск с малым polling и проверкой полей;
4. занесение в `data`/env без коммита секретов.

## Альтернативы (отклонены/отложены)

- Stack Exchange API (SRC-002) — conditional; Q&A, слабее product fit.
- Stack Overflow Atom (SRC-001) — technical candidate; не «ищу услугу».
- DEV/Reddit — manual_review из-за user-content/policy.
- Telegram web-preview — live блок (политика Telegram).
- Kwork и др. фриланс-биржи — hidden/private API; policy blocked.

## Последствия

- G2 формально закрыт: мотивированные evidence и условия; live-код не включён
  до активации (сегреш-safe).
- P10 pilot готов к запуску после получения ключа (без изменения кода —
  только конфиг/адapter).
- При несоблюдении условий источник не включается; enable/disable reversible
  (у нас — gate `allowed + can_poll`).
- Новые отсутствующие элементов для HH-integration (например, HH-vacancy
  adapter) — register-first через MissingRegistry по правилам платформы, если
  потребуется capability.