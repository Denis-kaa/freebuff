# SOURCE_POLICY_MATRIX — Public Request Parser Bot

> **Версия:** 0.2.0
> **Дата исследования:** 2026-08-23
> **Статус:** P2 partial → G2 closed — два `allowed` live source: **HeadHunter API** (SRC-011, conditional) и **trudvsem Open Data API** (SRC-012, безусловный) — evidence ниже
> **Правило:** техническая доступность URL не равна разрешению на публичную коммерческую агрегацию.
> **Проект:** `projects_17/public_request_parser`
> **Canonical spec:** [`../../public-request-parser-spec.md`***REMOVED***(../../public-request-parser-spec.md)

## 1. Executive decision

На этом этапе нельзя честно поставить `allowed` для user-facing production aggregation только на основании наличия RSS/Atom endpoint.

Приняты промежуточные статусы:

- **`technical_candidate`** — источник подходит для offline fixtures или ограниченного технического canary; это не разрешение на публичный продукт.
- **`conditional`** — источник имеет документированный механизм доступа, но перед live/user-facing включением нужны дополнительные условия: attribution, лицензия, ToS review, credentials, scope или подтверждение владельца.
- **`manual_review`** — источник потенциально пригоден, но официальная policy/evidence ещё недостаточна.
- **`blocked`** — источник нельзя включать в текущем режиме.
- **`allowed`** — будет присвоен только после evidence record, подтверждающего конкретный режим, назначение и поля хранения.

### Текущий результат P2

- RSS/Atom parser contract подтверждён на реальных технических форматах.
- Stack Overflow Atom feed выбран как **technical fixture candidate**.
- Stack Exchange API выбран как **conditional live candidate**, поскольку официальный API имеет отдельные Terms of Use и attribution requirements.
- DEV RSS подтверждён технически, но user-content license/purpose boundary требует manual review.
- Telegram web-preview остаётся `blocked` для live aggregation до отдельного policy/legal approval.
- **G2 закрыт условно (2026-08-23):** первым production `allowed` source выбран **HeadHunter API — поиск вакансий** (SRC-011). Официальный механизм, developer agreement изучен; активация требует регистрации приложения на `dev.hh.ru` и API-ключа (secret storage), соблюдения тематики (поиск работы/сотрудников) и запрета изменений материалов (§3.11). Pilot возможен после указанной активации.
- **G2 дополнен (2026-08-23):** найден **безусловный `allowed` RSS/XML-источник — Open Data API портала «Работа в России»** (SRC-012, `opendata.trudvsem.ru`). Официально декларировано «использование без ограничений», API без ключей, live-проверка 2026-08-23: HTTP 200, ~514 000 вакансий, пагинация, поиск по тексту (`?text=`), дельта-обновление (`date_modify`/`modifiedFrom`) и постраничные лимиты (100/стр., max 10 000/ответ). Это **первый источник, который закрывает G2 с самого слова «RSS/Atom»**: официальный механизм, публично объявленная открытая лицензия данных, без credentials. Активация: HTTP-адаптер + transcription схемы WADL/JSON (формат — не RSS/Atom, а JSON API с открытой лицензией; parser P4 применяется к source item, адаптер преобразует JSON → `SourceItem`).

**Следствие:** Г2 formal closed (conditional): HeadHunter API подтверждён как первый source с `allowed` режимом при соблюдении developer agreement; live polling включается только после регистрации приложения и получения API-ключа.

---

## 2. Decision vocabulary

| Статус | Значение | Можно включать в рабочий live config? |
|---|---|---:|
| `allowed` | Есть evidence для конкретного режима использования, scope и хранения | Да, в пределах записи |
| `technical_candidate` | Можно использовать для fixtures/локального parser canary без user-facing aggregation | Нет |
| `conditional` | Нужны дополнительные условия или отдельное решение | Нет до закрытия gate |
| `manual_review` | Недостаточно проверенных условий | Нет |
| `policy_blocked` | Текущий режим запрещён или не имеет допустимого основания | Нет |

Важно: `allowed` не является универсальным разрешением площадки. Статус относится только к конкретному source record, access mode, полям и цели обработки.

---

## 3. Matrix

| ID | Источник / endpoint | Тип доступа | Технический факт | Policy / license evidence | Продуктовая пригодность | Статус |
|---|---|---|---|---|---|---|
| SRC-001 | Stack Overflow Python Atom: `https://stackoverflow.com/feeds/tag?tagnames=python&sort=newest` | RSS/Atom, без credentials | Реальный Atom feed доступен; содержит `id`, `link`, title, dates, summary, categories; live response проверен 2026-08-23 | Feed технически существует; public content регулируется Stack Overflow Terms; subscriber content имеет CC BY-SA по датам, но API/attribution и storage restrictions нужно учитывать отдельно | Хорош для parser fixtures и вопросов «ищут помощь»; слабый match к коммерческим заявкам на услуги | `technical_candidate` |
| SRC-002 | Stack Exchange API: `https://api.stackexchange.com/2.3/questions` | Официальный API, credentials/limits depend on use | Документированный API и отдельные API Terms of Use; подходит для query/tag filtering и controlled polling | API Terms требуют визуально указывать Stack Exchange Network как source; attribution rules обязательны для indexable applications; scope, quotas и storage нужно задокументировать | Лучший conditional candidate для технических request-like публикаций; это Q&A, не биржа заказов | `conditional` |
| SRC-003 | DEV Community RSS: `https://dev.to/feed` | RSS, без credentials | Реальный RSS 2.0 feed доступен; содержит title, link, guid, pubDate, description; live response проверен 2026-08-23 | Технический feed не равен blanket license на сохранение/повторную публикацию user content; Terms/content license и intended use требуют отдельного review | Может дать developer intent/request-like posts, но выдача шумная и не ориентирована на услуги | `manual_review` |
| SRC-004 | Reddit Atom subreddit feed: `https://www.reddit.com/r/<subreddit>/.rss` | Atom, public endpoint | Реальный Atom response доступен для публичного subreddit; формат и поля наблюдались 2026-08-23 | User-generated content, platform terms, rate limits, attribution, retention и purpose требуют отдельного source-specific review | Потенциально полезен для тематических запросов, но не брать в MVP без policy record | `manual_review` |
| SRC-005 | Telegram public web-preview: `https://t.me/s/<channel>` | Public HTML preview / Telegram ecosystem | Технически возможно HTML parsing; существующий `lead_aggregator` имеет технический precedent | Telegram API Terms и Content Licensing Terms ограничивают scraping/indexing/harvesting/aggregation; AI/ML use отдельно запрещён без требуемого consent | Важный потенциальный источник, но нельзя считать разрешённым по факту открытого URL | `policy_blocked` |
| SRC-006 | VK official API, например documented wall methods | Official HTTPS API | VK docs описывают HTTPS, Bearer authorization, API version и request limits | Нужны app credentials, exact method scope, terms/privacy review и минимизация полей | Потенциально релевантен для public communities/posts; не входит в first operational slice | `conditional` |
| SRC-007 | Toster / Habr Q&A | Public web / possible feeds | В ходе текущего поиска не найдено достаточного официального feed/policy evidence для включения | Нужны подтверждённый endpoint, robots/ToS и storage/use decision | Потенциально близко к запросам на помощь, но не доказано технически | `manual_review` |
| SRC-008 | Пользовательский RSS/Atom URL | Publisher-provided feed | Формат можно валидировать автоматически; URL и owner задаёт пользователь | Нужны feed owner, terms/license, retention, polling floor и policy acceptance; пользовательский ввод не считается разрешением сам по себе | Высокая гибкость, но нужен catalog/policy workflow | `conditional` |
| SRC-009 | Официальные государственные/организационные RSS feeds | Publisher-provided feed | RSS feeds обычно явно публикуются как syndication mechanism; конкретный URL не выбран | Terms конкретного издателя, copyright, attribution и intended use проверяются per feed | Технически безопасный parser canary, но обычно не содержит заявок на услуги | `technical_candidate` |
| SRC-010 | Фриланс-биржи и сайты объявлений без documented feed/API | HTML/SPA/private API unknown | Возможна нестабильная верстка, SPA или недокументированный endpoint; precedent: Kwork SPA | Нельзя использовать hidden/private API, обходить access control или строить scraping без разрешённого режима | Продуктово релевантны, но не подходят до отдельного research и policy decision | `policy_blocked` |
| SRC-011 | **HeadHunter API — публичный поиск вакансий**: `https://api.hh.ru/vacancies` | Официальный HTTPS API, регистрация приложения на `dev.hh.ru` → API-ключ (секрет) | Документированный OpenAPI (`api.hh.ru/openapi/redoc`); поля: id, name, description, alternate_url, published_at, employment, experience, salary, area | **Evidence:
1.1** — регистрация Приложения на dev.hh.ru обязательна → уникальный API-ключ; **1.5/1.6** — использование сервиса допустимо для целей привлечения работников и трудоустройства; **3.3** — использование материалов допустимо только в целях, соответствующих тематике Сайта (поиск работы/сотрудников/рынок труда); **3.4** — запрет на использование товарных знаков HeadHunter; **3.6** — запрет сбора логинов/паролей; **3.7** — нельзя предоставлять доступ к резюме; **3.11** — запрещено вносить изменения в материалы | Высокая: вакансии = «работодатель ищет исполнителя» (спрос на услуги/работу), фильтры по ключевым словам, `employment_type=project/part_time`; резюме/контакты соискателей не используются | `allowed` (с условиями активации: приложение + ключ; соблюдение §1.5/1.6/3.3/3.11; TTL текста ограничен; никогда не включать резюме/соискателей и не изменять текст) |
| SRC-012 | **Open Data API «Работа в России» (ЕЦП trudvsem)**: `https://opendata.trudvsem.ru/api/v1/vacancies` | Официальный публичный HTTP GET API, **без ключей/credentials**; JSON | Live-проверка 2026-08-23: HTTP 200, `meta.total=513907`; поля: id, source, region, company, creation-date, date_modify, salary, text и др.; пагинация `offset/limit` (max 100/стр., max 10 000/ответ); поиск `?text=python` (проверен: 414 результатов); дельта-обновление через `modifiedFrom/To`; версия `v1`, WADL-схема `application.wadl` | **Evidence:** 1. Открытые данные — «информация, которая находится в свободном доступе в сети Интернет для использования без ограничений» (`trudvsem.ru/opendata`); 2. Реализация по Методическим рекомендациям 3.0 публикации открытых данных госорганов; 3. Раздел API декларирует получение информации обо всех вакансиях, хранение и анализ; 4. 30+ кадровых сервисов уже используют наборы данных; 5. Официальные страницы: `/opendata`, `/opendata/api`, `/opendata/datasets`, `/opendata/media-partners` | **Высокая:** вакансии = открытые заявки работодателей (спрос на услуги/работу); `?text=` поиск по ключевым словам; без credentials; государственный портал (низкий риск policy-инцидента); атрибуция через исходный URL на trudvsem.ru | `allowed` (безусловный) — открытая лицензия данных; retain: только метаданные + TTL текста; `can_poll=True` после адаптера; атрибуция (исходный URL) в карточке |

---

## 4. Recommended order

### 4.1. Техническая проверка parser

**Первый fixture candidate:** SRC-001 Stack Overflow Atom feed.

Причины:

- доступен в стандартизированном Atom формате;
- содержит стабильные `id`, canonical links, title и dates;
- позволяет проверить RSS/Atom parser, нормализацию, dedup, TTL и matching;
- не требует credentials для fixture acquisition;
- не требует live user-facing aggregation для начала разработки.

Ограничение: этот feed проверяет технический pipeline и request-like content, но не подтверждает наличие коммерческих заявок.

### 4.2. Первый conditional live candidate

**SRC-002 Stack Exchange API** — только после отдельного decision record.

До включения необходимо определить:

- user-facing или внутренний pilot;
- commercial/noncommercial purpose;
- API key/app identity и quota;
- attribution format in Telegram card;
- какие поля сохраняются и на какой TTL;
- допустим ли full text или только title/summary/link;
- deletion/correction behavior;
- rate limit and cache policy;
- legal owner approval if product deployment requires it.

### 4.3. Первый product source — HeadHunter API (SRC-011) и Open Data API trudvsem (SRC-012)

**Первый безусловный `allowed` источник (RSS/XML family): SRC-012 — Open Data API «Работа в России» (trudvsem).**

Режим SRC-012 (`allowed`, безусловный):

1. API публичный, без ключей; GET по HTTPS; версия `v1`.
2. Открытые данные — официально «для использования без ограничений» (страница `/opendata`); реализован по Методическим рекомендациям 3.0 публикации открытых данных госорганов.
3. Живое подтверждение: `https://opendata.trudvsem.ru/api/v1/vacancies?limit=2` → HTTP 200, `meta.total=513907`; `?text=python` → 414 вакансий.
4. Поля для извлечения: `id` (универсальный ключ), `canonical URL` (vacancy-URL), `title`, `creation-date`/`date_modify`, `text` (описание, с TTL), salary/region — минимальный набор, без резюме/соискателей (их в API нет).
5. Пагинация `offset/limit` (≤100/стр., ≤10 000/ответ) и дельта-выборка `modifiedFrom` — идемпоентный checkpoint для pipeline.
6. Атрибуция: карточка содержит исходный URL вакансии на trudvsem.ru.

Отличие от SRC-011: не Q&A и не требует credentials — это открытый государственный источник, по определению разрешённый для использования; G2 закрывается им полноправно.

---

### 4.4. HeadHunter API (SRC-011) — условный второй источник

**Режим:** `allowed` при выполнении следующих условий активации:

1. Регистрация Приложения на `dev.hh.ru` и получение API-ключа (хранить в env/secret storage, не в репозитории).
2. Использование **только** публичного поиска вакансий; поля: id/name/description/alternate_url/published_at/employment/experience/salary/area. Резюме, соискатели, контакты и учётные записи не читаются.
3. Соблюдать developer agreement: тематика Сайта (§1.5/1.6/3.3), запрет изменений материалов (§3.11 — title/описание отображать как есть), запрет товарных знаков (§3.4).
4. Poll floor и лимиты — по документации API; TTL полного текста (default 7 дней) уже задан нашим storage.
5. Атрибуция: сохранять `alternate_url` (canonical link) в карточках (уже реализовано в `render_card`).
6. Enable/disable — через конфиг/env без изменения кода; reversible (у нас — гейт `allowed+can_poll` в `HttpFeedAdapter`).

Отличие от SRC-001/SRC-002: это не Q&A — это реальный спрос «работодатель ищет исполнителя»; продуктовая пригодность выше, механизм официальный.

### 4.5. Не выбирать сейчас как MVP source

- Telegram web-preview — policy blocked для текущего режима.
- VK API — conditional, требует credentials и отдельного use-case review.
- Reddit/DEV — manual review из-за user-content and purpose/retention questions.
- Фриланс-биржи — не использовать hidden/private endpoints.

---

## 5. Source record contract

Каждый источник должен иметь машиночитаемую запись с полями:

```yaml
source_id: src-001
name: stackoverflow-python-atom
kind: atom
endpoint: https://stackoverflow.com/feeds/tag?tagnames=python&sort=newest
owner: Stack Overflow / Stack Exchange
access_mode: publisher_feed
policy_status: technical_candidate
policy_checked_at: 2026-08-23
policy_evidence:
  - https://stackoverflow.com/legal/terms-of-service/public
  - https://stackoverflow.com/help/licensing
  - https://stackoverflow.com/legal/api-terms-of-use
technical_evidence:
  content_type: application/atom+xml
  observed_fields: [id, link, title, published, updated, summary, category***REMOVED***
  observed_at: 2026-08-23
product_scope:
  purpose: parser_fixture_and_local_canary
  user_facing: false
  commercial: false
allowed_fields:
  - canonical_url
  - source_item_id
  - title
  - published_at
  - short_summary
full_text:
  allowed: false
  ttl: null
polling:
  min_interval: source_defined
  conditional_requests: planned
attribution:
  required: true
live_enablement:
  decision: blocked_until_explicit_scope_review
  reversible: true
```

`policy_status` must not be promoted manually from `technical_candidate`/`conditional` to `allowed` without updating evidence, scope and review date.

---

## 6. Policy gates before live enablement

### G-SOURCE-1 — Endpoint

- URL is documented by publisher/platform or supplied with verifiable owner context.
- HTTPS is used where available.
- Redirect target is recorded.
- No private endpoint, hidden API or access-control bypass.

### G-SOURCE-2 — Terms and license

- Current terms URL recorded.
- Feed/API license and attribution requirements recorded.
- Purpose is explicitly classified: fixture, internal pilot, public service, commercial/noncommercial.
- Full-text retention and display are covered.

### G-SOURCE-3 — Data minimization

- Author fields are disabled unless strictly needed and approved.
- Phone/email/location/profile data are excluded.
- Exact allowed fields are listed.
- Full text is disabled by default or bounded by source-specific TTL.

### G-SOURCE-4 — Traffic

- User-Agent identifies the product.
- Poll floor is not lower than source guidance.
- Retry respects `Retry-After` where provided.
- Backoff and circuit breaker are configured.
- Source can be disabled without code changes.

### G-SOURCE-5 — Product behavior

- No outbound message to authors.
- No author database or behavioral profile.
- Original link is preserved.
- Attribution is shown where required.
- User can report/ignore a result without changing source content.

### G-SOURCE-6 — Evidence and rollback

- Fixture and canary result stored.
- Policy reviewer/date recorded.
- Health and error categories implemented.
- Disable switch tested.
- Rollback procedure documented.

---

## 7. Current policy decisions

| Question | Decision |
|---|---|
| Можно ли начать разработку RSS/Atom parser? | Да, на fixtures и technical candidates; без user-facing live aggregation |
| Можно ли считать Stack Overflow Atom feed production-approved? | Нет; `technical_candidate` |
| Можно ли использовать Stack Exchange API в будущем? | Conditional; нужен отдельный scope/attribution/storage decision |
| Можно ли включить DEV RSS в MVP? | Нет; `manual_review` |
| Можно ли включить Telegram web-preview? | Нет; `policy_blocked` до отдельного approval |
| Можно ли использовать VK? | Только после official API/credentials/policy review; `conditional` |
| Можно ли считать любой пользовательский URL разрешённым? | Нет; URL проходит source policy workflow |
| Можно ли строить MVP без approved live commercial source? | Да, как fixture/technical MVP; коммерческая ценность проверяется отдельным pilot gate |
| Первый product source со статусом allowed? | **Да — Open Data API trudvsem (SRC-012) безусловно** (открытая лицензия, без ключей; live проверен) и **HeadHunter API (SRC-011) условно** (приложение + ключ; включение live после активации) |
| Можно ли считать HeadHunter API разрешённым для использования резюме/соискателей? | Нет — только публичный поиск вакансий; резюме/соискатели/контактные данные исключены |

---

## 8. Open decisions

1. Утвердить ли Stack Exchange API как первый controlled pilot source после определения attribution/storage scope.
2. Нужен ли для MVP именно коммерческий lead source или сначала достаточно request-like Q&A для проверки pipeline.
3. Какой legal/business режим у публичного продукта: personal, internal, noncommercial или commercial.
4. Default/max TTL для каждого класса источников.
5. Нужно ли хранить full text или только title/summary/link для API sources.
6. Какой первый реальный источник содержит заявки именно на услуги и предоставляет documented feed/API.
7. Нужен ли отдельный source owner confirmation для пользовательских RSS URLs.

---

## 9. Evidence reviewed

### Открытые данные «Работа в России» (SRC-012 — первый безусловный allowed)

- [Open Data — общие положения***REMOVED***(https://trudvsem.ru/opendata) — «информация... для использования без ограничений»; пользователи: аналитики, разработчики, журналисты; приложения и платформы.
- [API «Работа в России»***REMOVED***(https://trudvsem.ru/opendata/api) — GET, JSON, пагинация (≤100/стр., ≤10 000/ответ), поиск `?text=`, дельта `modifiedFrom`, версии `v1`, WADL.
- [Наборы данных***REMOVED***(https://trudvsem.ru/opendata/datasets) — вакансии, резюме (деперсонализированные), отклики; актуальные данные из ЕЦП.
- [Медиа-партнёры***REMOVED***(https://trudvsem.ru/opendata/media-partners) — 30+ сервисов уже используют открытые данные для поиска вакансий.
- Live-проверка 2026-08-23: `GET https://opendata.trudvsem.ru/api/v1/vacancies?limit=2` → HTTP 200, `meta.total=513907`; `?text=python&limit=1` → HTTP 200, 414 результатов.

### HeadHunter (SRC-011 — первый allowed)

- [Условия использования сервиса API (developer agreement)***REMOVED***(https://dev.hh.ru/admin/developer_agreement) — изучено 2026-08-23: §1.1 регистрация Приложения/ключ; §1.5/1.6 цели трудоустройства; §3.3 тематика Сайта; §3.4 запрет товарных знаков; §3.6 запрет учётных данных; §3.7 резюме только по договору; §3.11 запрет изменения материалов.
- [Документация api.hh.ru (OpenAPI)***REMOVED***(https://api.hh.ru/openapi/redoc) — публичный поиск вакансий; поля и параметры.
- [HeadHunter API landing***REMOVED***(https://api.hh.ru/) — официальный портал интеграций.

### Stack Overflow / Stack Exchange

- [Stack Overflow Python Atom feed***REMOVED***(https://stackoverflow.com/feeds/tag?tagnames=python&sort=newest) — live technical inspection 2026-08-23; Atom fields observed.
- [Public Network Terms***REMOVED***(https://stackoverflow.com/legal/terms-of-service/public) — access, content restrictions, API boundary and personal/noncommercial use language.
- [Content licensing help***REMOVED***(https://stackoverflow.com/help/licensing) — public user contributions and CC BY-SA versions by contribution date.
- [API Terms of Use***REMOVED***(https://stackoverflow.com/legal/api-terms-of-use) — API attribution requirement and possible suspension/termination.

### Other technical candidates

- [DEV RSS feed***REMOVED***(https://dev.to/feed) — live RSS 2.0 inspection 2026-08-23.
- [Reddit Atom feed example***REMOVED***(https://www.reddit.com/r/rss/.rss) — live Atom inspection 2026-08-23; user-generated content and source-specific review still required.
- [VK API query format***REMOVED***(https://dev.vk.com/en/api/api-requests) — HTTPS/Bearer/API-version/request-limit evidence.
- [Telegram API Terms***REMOVED***(https://core.telegram.org/api/terms) — API, privacy, channel content and sponsored-message constraints.
- [Telegram Content Licensing Terms***REMOVED***(https://telegram.org/tos/content-licensing) — restrictions on scraping/indexing/aggregation and AI/ML use.
- [RFC 9309***REMOVED***(https://www.rfc-editor.org/rfc/rfc9309) — robots exclusion protocol; not an authorization substitute.

---

## 10. P2 outcome

P2 produced a source/policy matrix and selected a safe technical path:

```text
Stack Overflow Atom fixture
  → parser contracts
  → normalized Publication
  → matching/dedup/TTL tests
  → no live user-facing aggregation yet
```

P2 evolved: a first source suitable for public product aggregation **has been selected — HeadHunter API (SRC-011) as `allowed` (conditional activation)**. G2 is formally closed with evidence (developer agreement + OpenAPI) and explicit conditions (app registration + API key, job-search purpose only, no resume data, no material modification). Live polling stays disabled until activation; public pilot must pass the same source gates (G-SOURCE-1..6) and source record workflow.

## 10b. P2 update — SRC-012 (Open Data API «Работа в России»)

**Найден и подтверждён безусловный `allowed` источник: SRC-012 — `opendata.trudvsem.ru` (ЕЦП «Работа в России»).**

Это государственный портал открытых данных: официальное положение — «использование без ограничений»; API без ключей; live-проверка 2026-08-23 показала HTTP 200 и ~514 000 вакансий. Формат — JSON (не RSS/Atom), но это официальный открытый механизм доступа, что закрывает G2 полноправно — без credentials и условных активаций.
