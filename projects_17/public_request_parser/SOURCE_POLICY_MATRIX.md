# SOURCE_POLICY_MATRIX — Public Request Parser Bot

> **Версия:** 0.1.0
> **Дата исследования:** 2026-08-23
> **Статус:** P2 partial — технические кандидаты найдены, live product source не утверждён
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
- Первый production `allowed` source пока не утверждён.

**Следствие:** P2 research выполнен частично; G2 для live product source остаётся открытым. P3 domain contracts завершены, а P4 fixture-based engine можно продолжать без live polling.

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

### 4.3. Не выбирать сейчас как MVP source

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

P2 is **partially complete** because a first source suitable for public product aggregation has not been approved. P3 domain contracts are complete; the next engineering stage is the P4 fixture-based engine. Live polling and public pilot remain blocked until an explicit source scope decision closes G2.
