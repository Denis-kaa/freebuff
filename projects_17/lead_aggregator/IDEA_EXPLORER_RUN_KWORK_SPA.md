# IDEA EXPLORER v2.0 — Прогон: W-16 (Kwork SPA → как получать заказы)

> **Промт:** `docs_10/templates/PIPELINE_TEMPLATE.md` Приложение B (встроенный IDEA EXPLORER v2.0, источник blob `44f6dd64…` / `pompts_11/071_02_prompt_architect_1_7.md` стр. 373–925)
> **Дата:** 2026-08-10 · **Агент:** Buffy (z-ai/glm-5.2)
> **Цель:** применить pre-flight гейт (W-14) к следующей задаче с развилками — **W-16**: `kwork.ru/projects` стал SPA (живой HTML = скелет с прелоадерами, все JSON-эндпоинты 404) → нужна стратегия получения заказов Kwork. Результат — handoff в ПРОМТ АРХИТЕКТОР 1.7.
> **Эталон прогона:** `projects_17/lead_aggregator/IDEA_EXPLORER_RUN.md` (Attract, 171 стр., 7 веток).

---

## 1. CORE LOOP (выполнен)

```
RAW IDEA → EXTRACT → GENERATE BRANCHES → EVALUATE → PRUNE → DEEPEN
         → CROSS-POLLINATE → SYNTHESIZE → NEXT DIRECTIONS
```

## 2. IDEA EXTRACTION

| Поле | Значение |
|---|---|
| **CORE IDEA** | Вернуть Kwork как источник заказов в lead_aggregator, обойдя SPA-рендеринг (заказы грузятся JS, статичный HTML пуст) |
| **PROBLEM** | `KworkAdapter` на живом HTML даёт 0 заказов: страница — скелет SPA (`js-wants-list-preloaders`/`wants-content`), все публичные JSON-эндпоинты вернули 404 (проверено 2026-08-10) |
| **USER / ACTOR** | Buffy (агент) + пользователь (AI-фрилансер, стек: Python/TG-боты/FastAPI/лендинги) + платформа Workspace OS (Termux/ARM64) |
| **DESIRED OUTCOME** | Kwork-заказы снова в пайплайне: fetched>0, без установки тяжёлых браузеров (W-2), без нарушения юр. гейта (read-only, W-7) |
| **MECHANISM** | (а) headless-рендер SPA; (б) TG-зеркала Kwork-заказов (`@kwork_parsing` и аналоги) через уже работающий `TGChannelAdapter`; (в) поиск скрытого API |
| **CONSTRAINTS** | Termux/ARM64, Python 3.14.6, SQLite-only, без новых зависимостей (W-2), read-only/юр. гейт (W-7), аддитивность (`projects_17/lead_aggregator/`), уже работают: `TGChannelAdapter` (live-классы TG), `TLSClient` (httpx) |
| **ASSUMPTIONS** | TG-каналы-зеркала Kwork публичны и живы; TG-парсинг уже работает (live-verify: 2 блока из freelance_tg); Lightpanda-скрипт (`scripts_01/install_lightpanda.sh`) и ADR-007 существуют как готовый headless-путь |
| **UNKNOWN** | Полнота/задержка зеркал `@kwork_parsing`; реальная возможность установки Lightpanda в proot-Ubuntu на этой машине; анти-бот политика Kwork против headless |

## 3. BRANCH GENERATION (7 веток)

| # | Тип | Ветка |
|---|---|---|
| B1 | **DIRECT** | Headless-рендер: Lightpanda (проект платформы: `scripts_01/install_lightpanda.sh` + ADR-007, Termux+proot-Ubuntu ARM64) рендерит SPA → отдаёт готовый HTML → `KworkAdapter` парсит карточки |
| B2 | **ALTERNATIVE** | TG-зеркала Kwork: каналы вида `@kwork_parsing` (и аналоги) уже постят заказы Kwork в TG → переиспользуем `TGChannelAdapter` (без headless, без новых зависимостей) |
| B3 | **ALTERNATIVE** | Playwright/Chromium headless: полный браузер, JS-рендер из коробки |
| B4 | **ADJACENT** | curl_cffi TLS-impersonation: обойти анти-бот по TLS-отпечатку (не решает SPA-рендер сам по себе, но снимает риск блокировки для B1/B3) |
| B5 | **COMBINATION** | Гибрид «TG-first + headless-fallback»: B2 как дефолт (мгновенно, 0 зависимостей) + B1 как upgrade, когда TG-зеркало не покрывает разделы |
| B6 | **SIMPLIFICATION** | Отказаться от Kwork: только TG-каналы (`freelance_tg`, `proger_orders` уже в `LA_TG_CHANNELS`) + другие биржи (FL.ru/Weblancer из research §6) |
| B7 | **REFRAME** | Проблема не «SPA-рендер», а «доступ к заказам Kwork» → решить на уровне источника: мобильное приложение Kwork / приватный API / встроенные data-скрипты страницы (проверено: JSON-скрипт на 253892 есть, но без карточек) |

## 4. BRANCH DIFFERENTIATION

Ветки различаются по фундаментальным параметрам:
- B1/B3 — **MECHANISM** (headless: лёгкий vs тяжёлый)
- B2/B6 — **SOURCE** (зеркала TG vs отказ от Kwork)
- B4 — **TRANSPORT** (TLS-имперсонация, усилитель)
- B5 — **ARCHITECTURE** (гибрид с fallback-порядком)
- B7 — **PROBLEM** (переформулировка: рендер → доступ)

B1 и B3 не дублируют: B1 — лёгкий headless (Lightpanda, ADR-007, ~80MB), B3 — тяжёлый (Chromium ~300MB+ на ARM64, риск W-2).

## 5. BRANCH SCORE (1–10)

| Ветка | VALUE | FEAS | NOVEL | LEVER | EXPAN | RISK | Σ |
|---|---|---|---|---|---|---|---|
| B1 Lightpanda headless | 9 | 5 | 6 | 9 | 8 | 6 | 43 |
| B2 TG-зеркала Kwork | 8 | 9 | 5 | 7 | 6 | 2 | 37 |
| B3 Playwright/Chromium | 8 | 3 | 3 | 8 | 7 | 8 | 37 (риск высок) |
| B4 curl_cffi TLS | 6 | 5 | 4 | 6 | 5 | 5 | 31 |
| B5 TG-first + headless-fallback | 9 | 8 | 7 | 9 | 8 | 3 | 44 |
| B6 Без Kwork | 5 | 9 | 2 | 4 | 3 | 2 | 25 |
| B7 Мобильный/скрытый API | 8 | 3 | 7 | 8 | 7 | 7 | 40 |

## 6. BRANCH STATUS

- **DEEPEN:** B5 (гибрид — лучший баланс), B1 (Lightpanda — путь к полному доступу)
- **MERGE:** B4 → B1 (TLS-имперсонация усиливает headless), B7 → B1 (мобильный API как будущий upgrade B1)
- **PARK:** B6 (fallback-план, не цель — Kwork остаётся топ-источником из research)
- **DROP:** B3 (Playwright/Chromium: тяжёлый на ARM64, дублирует B1 с худшим риском W-2)

## 7. EXPLORATION BUDGET

4–8 первичных веток ✅ (7) · углубление: 2 (B1, B5) · дочерние: 1–3 на ветку ✅ · глубина: 2 уровня ✅

## 8. DEPTH-2 EXPLORATION

### B1 — Lightpanda headless (DEEPEN)
- **MECHANISM:** `scripts_01/install_lightpanda.sh` ставит Lightpanda в proot-distro Ubuntu (ARM64) → `lightpanda kwork.ru/projects --dump-dom` → stdout-HTML после JS-исполнения → `KworkAdapter.parse_html(rendered)`.
- **VARIANTS:** (a) CLI dump-dom по требованию (просто, медленно); (b) headless-сервер/HTTP-мост (быстрее, сложнее); (c) WS-сессия для постраничной навигации.
- **CONSEQUENCES:** полный доступ к Kwork-разметке; proot-Ubuntu на этой машине ещё не установлен (скрипт существует, установка не проверена — UNKNOWN).
- **SECOND-ORDER:** Lightpanda становится общим сервисом платформы (ADR-007 оживает) → другие SPA-источники (FL.ru, hh) тоже рендерятся.
- **FAILURE MODE:** установка proot+Lightpanda может упасть на ARM64; Kwork анти-бот может распознать headless (нужен B4); скорость dump-dom ниже, чем статический парсинг.

### B5 — Гибрид «TG-first + headless-fallback» (DEEPEN)
- **MECHANISM:** приоритет источников: (1) `TGChannelAdapter` на `@kwork_parsing`+аналоги (работает уже сегодня, 0 новых зависимостей); (2) если зеркало не дало лидов за цикл → поднять Lightpanda (B1) для прямого рендера; (3) конфликт дедуплицируется по `source_id` (kwork-slug vs tg-post).
- **VARIANTS:** (a) параллельный запуск обоих; (b) последовательный fallback; (c) конфиг-переключатель `LA_KWORK_MODE=tg|headless|hybrid`.
- **CONSEQUENCES:** мгновенный деплой (TG-часть работает), headless — опциональный upgrade; сложность — два пути, нужен порядок и дедуп.
- **SECOND-ORDER:** зеркала проверяются эмпирически (полнота/задержка) → если полны, headless может не понадобиться вовсе.
- **FAILURE MODE:** зеркало может постить только часть разделов Kwork; риск дублей между зеркалом и прямым рендером; канал может закрыться (внешний риск).

## 9. CROSS-POLLINATION ENGINE

- **B1 + B2 →** «Что из механизма B1 устраняет ограничение B2?»: зеркало может не покрывать разделы → Lightpanda-рендер даёт полный доступ. **B1+B2 → NEW CONCEPT: гибридный Kwork-мост** (B5).
- **B2 + B6 →** зеркала Kwork + нативные TG-каналы = единый TG-пул источников без единого headless-скрипта — CORRECTIVE (B6 без Kwork слишком беден; B2 возвращает Kwork-спрос в TG-пул).
- **B1 + B4 →** Lightpanda + TLS-impersonation снижает риск анти-бот-блокировки headless — COMPLEMENTARY.
- **B7 + B1 →** скрытый мобильный API как «будущий» канал данных для Lightpanda-сервиса — EMERGENT (доступ без HTML вообще).

## 10. REFRAME ENGINE

- **USER REFRAME:** основной пользователь — не только человек-фрилансер, но и **другие агенты платформы** (Forge/Scenario могут потреблять Kwork-ленду как сервис).
- **PROBLEM REFRAME:** проблема не «рендерить SPA», а **«доступ к данным заказов»** → TG-зеркала уже решают её без рендера (B2).
- **MECHANISM REFRAME:** отказаться от идеи «обязательно парсить kwork.ru» → источником становится «любая зеркальная лента Kwork-заказов» (TG, боты-агрегаторы `@Golubin_bot` из research) — B2.
- **VALUE REFRAME:** ценность — не «HTML-страницы Kwork», а **«поток заказов, релевантных стеку»** — независимо от того, кто и как их публикует.

## 11. BLIND-SPOT DETECTOR

- **HYPOTHESIS 1:** `@kwork_parsing` (и аналоги) постит заказы Kwork в реальном времени — проверка live займёт 5 минут через `TGChannelAdapter` (source в settings.env).
- **HYPOTHESIS 2:** Kwork мобильное приложение использует приватный API (не публичные `/api/v1/…` — все 404) — достойно одного захода с инспекцией мобильного трафика, но низкий приоритет.
- **HYPOTHESIS 3:** встроенный JSON-скрипт страницы (обнаружен на позиции 253892) может содержать карточки заказов при правильном User-Agent/куках — не проверено с TLS-имперсонацией (B4).
- **HYPOTHESIS 4:** боты-агрегаторы (Golubin_bot) отдают заказы через inline-команды — могут быть вторым источником помимо каналов.

## 12. PRUNING

- DROP B3 (тяжёлый, дублирует B1), MERGE B4→B1, MERGE B7→B1 (future), PARK B6 (fallback).
- KEEP B1 (headless-путь, ADR-007 asset), KEEP B2 (мгновенный деплой, 0 зависимостей).

## 13. CONVERGENCE

```
MANY IDEAS (7) → FEWER STRONG (B1, B2) → BEST COMBINATION (B1+B2 = B5)
              → CANDIDATE CONCEPTS → SYNTHESIS
```

## 14. FINAL CANDIDATES

- **CANDIDATE A — PRACTICAL:** **TG-зеркала Kwork** (B2): добавить `kwork_parsing`+аналоги в `LA_TG_CHANNELS`, нулевой новый код (TGChannelAdapter уже работает). Мгновенно деплоится, проверяется live за 15 минут.
- **CANDIDATE B — HIGH UPSIDE:** **Гибридный Kwork-мост** (B5 = B1+B2): TG-зеркало как дефолт + Lightpanda-рендер как опциональный upgrade для полного покрытия разделов. Максимальная ценность при умеренном риске.
- **CANDIDATE C — UNEXPECTED:** **Kwork-as-a-Service** (B1-ядро + B7): Lightpanda-рендер как общий headless-сервис платформы (ADR-007 оживает) → Kwork-ленда + любые SPA-источники для всех агентов. Нестандартно, но создаёт инфраструктурный актив.

## 15. CONCEPT COMPARISON

| Concept | Value | Feas | Novel | Risk | Expansion |
|---|---|---|---|---|---|
| A TG-зеркала Kwork | 8 | 9 | 5 | 2 | 6 |
| B Гибридный мост | 9 | 7 | 7 | 4 | 9 |
| C Kwork-as-a-Service | 8 | 4 | 8 | 7 | 9 |

**BEST PRACTICAL:** A · **BEST UPSIDE:** B · **BEST EXPERIMENT:** A (проверка зеркал live за 15 минут = самый дешёвый эксперимент, данные для C)

## 16. CRITICAL DECISION POINT

«Критическая развилка: **покрывают ли TG-зеркала нужные разделы Kwork?**

Если зеркала постовятся (live-проверка: 5–15 лидов за цикл) → развиваем **A (TG-зеркала)** — без headless, деплой сегодня.
Если зеркала пусты/неполны → развиваем **B (гибрид)** с подъёмом Lightpanda (B1) — headless-рендер для прямого доступа.»

**Решение по данным на 2026-08-10:** зеркала ещё не проверены live; TGChannelAdapter работает (live-verify 2 блока). → **Эксперимент A первым** (проверка зеркал, 15 минут, 0 новых зависимостей); Lightpanda (B) — следующий шаг, если A не даст лидов.

## 17. USER INTERACTION (пропущен — автономный режим, выбор по данным: эксперимент A самый дешёвый и информативный)

## 18. HANDOFF TO PROMPT ARCHITECT

**SELECTED CONCEPT:** Candidate A (TG-зеркала Kwork) с переходом в B (гибрид) при недостатке данных.
**CORE OBJECTIVE:** вернуть Kwork-заказы в lead_aggregator, обойдя SPA-рендеринг минимальной ценой.
**PROBLEM:** kwork.ru/projects — SPA, статичный HTML пуст (W-16, live-verify 2026-08-10).
**TARGET:** lead_aggregator (`projects_17/lead_aggregator/`), платформа Workspace OS (Termux/ARM64).
**MECHANISM:** (1) добавить каналы-зеркала `@kwork_parsing` и аналоги в `LA_TG_CHANNELS` → `TGChannelAdapter` (работает); (2) live-проверка fetched>0; (3) при пустоте — поднять Lightpanda (`scripts_01/install_lightpanda.sh`) как headless-fallback.
**CONSTRAINTS:** без новых зависимостей (W-2), read-only (W-7), аддитивность, SQLite-only; Lightpanda — только через существующий скрипт/ADR-007.
**ASSUMPTIONS:** зеркала публичны и живы; TGChannelAdapter тянет каналы-зеркала так же, как нативные (live-классы regex уже исправлены).
**DECISIONS:** A принят как первый шаг; B (Lightpanda) — гейт после live-проверки A; B3 (Playwright) отклонён; B6 — fallback-план.
**REJECTED ALTERNATIVES:** B3 (тяжёлый, W-2), B7-как-основной (приватный API не найден).
**OPEN QUESTIONS:** полнота и задержка зеркал; установимость Lightpanda в proot-Ubuntu на этой машине; анти-бот Kwork против headless.
**RECOMMENDED APPROACH:** шаг 1 = добавить зеркала в settings.env + live-dry-run (acceptance: fetched>0, 0 ошибок); шаг 2 = при пустоте установить Lightpanda (скрипт платформы) и рендерить `kwork.ru/projects` → расширить `KworkAdapter` на рендеренный HTML.

---

## 19–23. ANTI-ANCHORING / ANTI-HALLUCINATION / OUTPUT / STYLE / GATE

- **ANTI-ANCHORING соблюдён:** исходное «нужен headless-браузер» (W-16 формулировка) оспорено reframe (B2/B7: доступ к данным ≠ рендер) без изменения цели пользователя.
- **FACT vs ASSUMPTION vs HYPOTHESIS разделены:** факты — live-verify 2026-08-10 (SPA, 404 API, 2 TG-блока); гипотезы — H1-H4 явно помечены; зеркала не проверены = UNKNOWN, не FACT.
- **FINAL QUALITY GATE:** ✅ альтернативы реальные (7, механизм/источник/транспорт различаются) · ✅ соседние возможности (ADR-007, Golubin_bot, FL.ru) · ✅ reframe есть (B7: рендер → доступ) · ✅ сильные ветки углублены (B1, B5) · ✅ слабые отброшены (B3, B6 parked) · ✅ комбинации найдены (B1+B2 EMERGENT = B5) · ✅ факты отделены от гипотез · ✅ пространство сужено (7 → 3 кандидата → A) · ✅ понятный следующий шаг (live-проверка зеркал).

**Вывод:** предсказание W-16 «нужен headless» — не единственный путь. IDEA EXPLORER показал: **TG-зеркала Kwork (B2/A) — самый дешёвый первый шаг** (0 зависимостей, деплой сегодня), **Lightpanda (B1/B) — опциональный upgrade** через существующий ADR-007; Playwright отклонён. Эксперимент A (15 минут) даёт данные для решения B/C.
