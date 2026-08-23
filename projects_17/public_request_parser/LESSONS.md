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

## Open questions

- **OQ-PRP-1** (Task 1): какой первый RSS/Atom feed использовать для live feasibility check? Technical fixture candidate = Stack Overflow Atom; user-facing source не утверждён.
- **OQ-PRP-2** (Task 1): какой default/max TTL утвердить?
- **OQ-PRP-3** (Task 2): как вычислять thresholds accept/pending/reject? P5 fixировал формулу mean-ratio × 0.9 + intent 0.1; калибровка на реальных данных — P10/P14.
- **OQ-PRP-4** (Task 6): есть ли допустимое основание для Telegram web-preview в целевом публичном продукте?
