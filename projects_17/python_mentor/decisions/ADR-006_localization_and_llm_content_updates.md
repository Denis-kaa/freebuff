# ADR-006 — Локализация learner-контента и LLM-assisted обновления

> **Статус:** Accepted (2026-08-24)
> **Область:** content/localization layer
> **Связанные решения:** [ADR-001***REMOVED***(ADR-001_deterministic_core_first_llm_external_only.md), [ADR-004***REMOVED***(ADR-004_license_gate_approved_only_live.md)
> **Контракт:** [`prompt_localization.md`***REMOVED***(../prompt_localization.md)

## Context

Официальный Exercism Python track является англоязычным upstream-источником. В
текущем клоне обнаружено 432 learner-facing Markdown-документа примерно на
1,022,490 символов: инструкции и вспомогательные тексты упражнений, а также
concept-документы. Переводить только названия или отдельные подсказки
недостаточно; нужен полный learner-facing projection с отслеживанием изменений
upstream.

При этом английский текст должен оставаться проверяемым source-of-truth для
provenance, license audit и change detection. LLM может помочь с большим
объёмом перевода и последующими обновлениями, но не должен напрямую менять
live corpus, curriculum, evidence или learning state.

## Decision

1. Канонический content source остаётся `en` из approved Exercism clone.
2. Основная пользовательская локаль проекта — `ru`; переводы хранятся как
   versioned projection, не поверх upstream-файлов.
3. В локализацию входят learner-facing Markdown:
   `instructions.md`, `introduction.md`, `hints.md`, `about.md`, а позднее
   `blurb` и curriculum text. Код, тесты, reference solutions, identifiers,
   provenance и license evidence не переводятся и не изменяются.
4. Каждый source document получает `document_id`, относительный путь,
   `content_kind` и SHA-256 `source_hash`. Перевод считается актуальным только
   при совпадении sidecar hash; изменение upstream переводит его в `stale`.
5. LLM подключается только через `TranslationProvider` и создаёт
   `TranslationDraft` с provider/model provenance. Draft не является live
   content.
6. Публикация разрешена только для `reviewed` draft после структурной
   валидации Markdown: code fences, inline-code, link targets и heading
   structure должны сохраниться. Публикация пишет source-hash и provenance
   sidecars.
7. Внешний provider не включается в базовый runtime автоматически. Сохраняется
   fail-closed `ExternalLLMTranslationProvider`; дополнительно доступен явно
   выбранный `GeminiTranslationProvider` с локальным трёхключевым pool/failover.
   Он пишет только draft-артефакты в отдельный ignored-каталог.

## Rationale

- Английский source остаётся доступным для аудита и отката.
- Hash-based drift detection не даёт тихо показывать устаревший перевод.
- Структурная валидация защищает runnable examples, ссылки и Markdown.
- Review gate ограничивает hallucinations и сохраняет ответственность за
  публикацию у человека/оператора.
- Optional provider не нарушает детерминированность core: одинаковый source,
  corpus, grading и learning state остаются независимыми от модели.

## Consequences

- `localize scan` и `localize status` становятся частью runbook.
- Полный перевод корпуса является отдельным batch-процессом; до подключения
  provider русский projection будет иметь статус `missing`/`draft`; Gemini по умолчанию создаёт один draft за запуск.
- Upstream refresh требует повторного scan и перевода только changed/stale
  документов.
- Переводы должны сохранять attribution/provenance исходного approved source.
- LLM costs, credentials, provider choice и review policy остаются внешней
  эксплуатационной ответственностью, не частью core requirements.

## Revisit triggers

Пересмотреть ADR при добавлении второй пользовательской локали, изменении
license/content policy, переходе к автоматической публикации, появлении
локального translation model или необходимости переводить code comments/tests.
