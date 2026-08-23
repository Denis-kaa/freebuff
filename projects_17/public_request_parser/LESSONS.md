# LESSONS — project-local narrow for ROADMAP-PRP-001

> Только находки, подтверждённые при работе над этим проектом. Универсальные платформенные уроки не дублируются здесь.

## Closed findings

- **PRP-1** (Step 1, boundary review): Public Request Parser и Lead Aggregator имеют разные доменные цели: parser нормализует открытые публикации и маршрутизирует их по профилям, Lead Aggregator добавляет прикладные компетенции и коммерческий lead context.
- **PRP-2** (Step 1, source research): публичная доступность URL не является достаточным доказательством разрешённой автоматической агрегации; источник должен пройти policy matrix.
- **PRP-3** (Step 2, product scaffold): Telegram adapter допустимо проектировать технически на fixtures, но live-режим должен оставаться выключенным до отдельного policy/legal approval.
- **PRP-4** (Step 2, retention): полный текст публикации — временное поле с TTL; ссылка, decision snapshot и минимальные технические metadata рассматриваются отдельно.
- **PRP-5** (Step 3, source research): RSS/Atom endpoint подтверждает формат и техническую доступность, но не автоматически разрешает user-facing aggregation; source status должен разделять `technical_candidate`, `conditional`, `manual_review`, `policy_blocked` и `allowed`.
- **PRP-6** (Step 3, source research): Stack Overflow Atom подходит как fixture/parser canary, но его Q&A content не доказывает наличие коммерческих заявок на услуги; техническая готовность и продуктовая пригодность оцениваются отдельно.
- **PRP-7** (Step 4, contract design): `SourcePolicy`, domain rejection, adapter failure и delivery failure нельзя кодировать одним boolean/error path; раздельные типы и outcomes сохраняют explainability и позволяют продолжать обработку других источников.
- **PRP-8** (Step 4, contract design): project-local frozen dataclasses и Protocol-порты позволяют начать P4 без live source approval и без coupling к `lead_aggregator`.
- **PRP-9** (Step 5, parser engineering): тесты на hermetic fixtures ловят реальные дефекты формата (item без `<link>` / невалидная дата) без живого источника; controlled warnings являются частью контракта, а не скрытым fallback.
- **PRP-10** (Step 5, engine boundary): fixture adapter должен явно отвергать `allowed` policy, чтобы offline-срез не превращался в незаметный live polling; HTTP/ETag/SQLite остаются отдельными gates.
- **PRP-11** (Step 6, matcher): жёсткие правила (exclusion/required/intent gate) должны давать REJECT со score 0 и строковую причину — score как шкала вероятности не должен «оправдывать» никогда-не-доставляемый результат.
- **PRP-12** (Step 6, scoring): стоп-слова в `optional_terms` должны исключаться из НОЗНАМЕНАТЕЛЯ ratio, иначе пустой профиль с одним стоп-словом «и» получает ложный 0.0 и никогда не принимается.
- **PRP-13** (Step 6, synonyms): совпадение алиаса синонима должно удовлетворять required canonical вручную (matched_required += canonical), иначе синоним повышает score, но профиль с required остаётся отклонённым — семантическая ловушка.
- **PRP-14** (Step 6, intent gate): маркеры предложения («предлагаю», «оказываю») консервативны и срабатывают только при отсутствии demand-сигнала; выдача явного `OFFER_MARKERS` упрощает policy review.
- **PRP-15** (Step 8, storage): `PRAGMA user_version` не принимает bind-параметры — версия схемы подставляется константой; иначе OperationalError даже при кажущемся корректном SQL.
- **PRP-16** (Step 8, storage): TTL cleanup должен делать UPDATE только `content`/`text_expires_at`, а не DELETE строки — иначе после истечения TTL пропадают title/URL/metadata, необходимые для карточки и dedup.
- **PRP-17** (Step 8, storage): хранилище повторно применяет `max_text_chars`/`allow_full_text` на записи, а не полагается на normalization P4 — контрактная защита от будущих вызовов с разными policy.
- **PRP-18** (Step 9, delivery): HTML-escape — обязательный атрибут карточки из пользовательского контента; Markdown не используется, чтобы канал остался единым форматом.
- **PRP-19** (Step 9, delivery): FK `delivery_attempts → publications` законно блокирует сохранение попытки для несуществующей публикации — порядок вызова (сначала save_publication) зафиксирован тестом.
- **PRP-20** (Step 9, delivery): retry после сбоя должен перезаписывать только `FAILED`-строки; `INSERT OR IGNORE` не даёт этого сам по себе — нужен явный `replace_failed=True`.
- **PRP-21** (Step 10, pipeline): `FixtureFeedAdapter.fetch` — async-генератор: вызывается БЕЗ `await`; Protocol должен описывать `def fetch -> AsyncIterator`, иначе mypy считает тип несовместимым с `Coroutine`.
- **PRP-22** (Step 10, transport): live-адаптер обязан иметь двойной гейт — статус `allowed` И `can_poll=True`; порт `SourcePolicy` уже запрещает can_poll для не-allowed (contract-level).
- **PRP-23** (Step 10, schema v2): миграция v1→v2 аддитивная (только новые таблицы) — это позволяет открывать старые БД без потери данных; ALTER-миграции потребуют отдельную процедуру P11.
- **PRP-24** (Step 10, gates): этапы, требующие внешних допусков (live source, pilot-пользователи, beta), фиксируются как `Blocked (Gx)` с evidence, а не «планируются» — честность статусов обязательна.
- **PRP-25** (Step 11, calibration): оптимальный порог ищется по наблюдаемым score, а не по сетке — иначе «KEEP»-кейс (текущий порог 0.8) давал бы ложный CHANGE при отсутствии сэмпла ровно 0.8.
- **PRP-26** (Step 11, calibration): feedback без сохранённого decision обязан исключаться из выборки; иначе «ghost»-записи раздувают выборку и ломают min_samples.
- **PRP-27** (Step 11, calibration): рекомендации порогов не применяются автоматически — apply всегда через новую версию профиля (откат без изменений старых decisions).
- **PRP-28** (Step 13, G2): «allowed» — это статус с evidence и условиями, а не выключатель трафика: HeadHunter API получил `allowed` (developer agreement + OpenAPI), но live polling остаётся `can_poll=False` до регистрации приложения/ключа и canary-прогона; двойной гейт закрывает разрыв между policy-решением и runtime-активацией.
- **PRP-29** (Step 14, G2): государственные open-data API (например, trudvsem «Работа в России») могут закрывать G2 **безусловно** — официальная формулировка «использование без ограничений» + живая проверка endpoint без ключей сильнее, чем developer agreement с активацией; такие источники проверяются первыми при том же поиске, но всё равно проходят G-SOURCE-1..6.
- **PRP-30** (Step 15, adapter): у трудоустройственных API контактные поля (`contact_list`, `contact_person`, `addresses`) приходят прямо в JSON; адаптер обязан отфильтровывать их на уровне извлечения (а не полагаться на storage) — privacy-инвариант проверяется тестом с подменой полей в fixture.
- **PRP-31** (Step 17, canary): live canary подтверждает не только транспорт, но и семантику: первичные items вакансий REJECT без профиля с demand-маркерами — это здоровое поведение matcher, а не сбой источника; canary-отчёт фиксирует это как evidence, а не как проблему.

## Open questions

- **OQ-PRP-1** (Task 1): ~~какой первый source для live feasibility check?~~ → **решён (ADR-012): Open Data API «Работа в России» (SRC-012, безусловно) + ADR-011 (SRC-011, условно)**; Stack Overflow Atom остаётся fixture/parser canary.
- **OQ-PRP-2** (Task 1): какой default/max TTL утвердить?
- **OQ-PRP-3** (Task 2): как вычислять thresholds accept/pending/reject? P5 fixировал формулу mean-ratio × 0.9 + intent 0.1; калибровка на реальных данных — P10/P14.
- **OQ-PRP-4** (Task 6): есть ли допустимое основание для Telegram web-preview в целевом публичном продукте?
