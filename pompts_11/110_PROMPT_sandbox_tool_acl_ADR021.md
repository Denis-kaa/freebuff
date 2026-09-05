# ЗАДАЧА: Trust Boundary / Tool-ACL для ShellTool и внешних мостов (рабочий номер ADR-021 — проверить и скорректировать по docs_10/decisions/DECISIONS.md)

## РОЛЬ

Ты работаешь в той же кодовой базе Buffy/Freebuff/Workspace OS, что и закрытые ADR-017/018/019/020. Тот же режим работы: forensic → design → additive implementation → hermetic tests → verification → реестры. Не переписывай существующий код, не делай глобальный рефакторинг, не трогай ничего за пределами периметра ниже.

## КОНТЕКСТ (уже установлено — не передоказывать, но ПРОВЕРИТЬ, что всё ещё так)

- Последний открытый P0-блокер по UNIFIED_CONCLUSIONS: sandbox/tool-ACL для внешних мостов — «ShellTool без ограничений для локальных вызывающих».
- Evidence (EVIDENCE_LEDGER_MERGED, Task/Tool/Memory): `scripts_01/tool_runtime.py::ShellTool.run` → `subprocess.run(cmd)`, без sandbox.
- Отдельно, по 107 §L: `core_02/telegram_contract.py`, `scripts_01/phone_control_mcp.py` описаны как «вшиты в ядро, нет adapter-границы». Но с тех пор реализован ADR-020 (`core_02/integration_base.py::IntegrationAdapter`, `AuthSpec` с 5 методами включая `chat_id_scope`/`phone_scope`, закрытый `INTENT_CAPABILITY_MAP`). Не предполагай, что эти мосты уже переведены на IntegrationAdapter — это первое, что нужно проверить.
- ADR-017/018/019/020 закрыты одним и тем же паттерном: additive (CAN-16), hermetic-тесты в `tests_09/`, обновление `docs_10/decisions/DECISIONS.md` + `DOCUMENT_REGISTRY.md` + `ARCHITECTURAL_BASELINE_V1.md` §4 + запись в CHANGELOG с блоком Verification. Следуй тому же формату отчёта.

## ЭТАП 1 — FORENSIC (обязателен до дизайна, не пропускать)

Установи с evidence (CLAIM / FILE / SYMBOL / CONFIDENCE, как в 104–107):

1. Кто фактически вызывает `ShellTool.run` сегодня? Перечисли все call sites.
2. Есть ли уже в коде (не в документации) хоть какое-то различие «локальный доверенный вызывающий» vs «внешний мост» на пути к ShellTool?
3. Мосты (`telegram_contract.py`, `phone_control_mcp.py`, MCP-серверы) — проходят ли они сегодня через `IntegrationAdapter`/`AuthSpec` (ADR-020), или это отдельная, ещё не подключённая труба?
4. Если проходят через AuthSpec — доходит ли `chat_id_scope`/`phone_scope` до диспетчера тулов (`ToolRegistry`), или обрывается на границе адаптера?
5. Есть ли уже closed-set/allowlist паттерн, пригодный для переиспользования (`KNOWN_CAPABILITIES`, `INTENT_CAPABILITY_MAP` — ANTI-6b style), а не только внутри Agent/Integration?
6. Другие тулы с похожим риском — File/HTTP/Git из `ToolRegistry`, `McpTool` из `mcp_server.py` (напомню: «MCP server без auth — диспатч без auth, stdio-local», 107) — та же дыра или нет?

Если что-то не подтверждается — фиксируй `UNKNOWN — NOT VERIFIED`, не додумывай за код.

## ЭТАП 2 — ДИЗАЙН (только после Этапа 1, только additive)

Гипотеза для проверки, не готовое решение: если внешние мосты уже проходят через `AuthSpec` (ADR-020), минимальный фикс — прокинуть scope до `ToolRegistry`/`ShellTool` и завести closed-dict allowlist (по образцу `INTENT_CAPABILITY_MAP`): какие capability/scope разрешают вызов ShellTool и с каким ограниченным набором команд — а не изобретать новый механизм авторизации с нуля.

Если Этап 1 покажет, что мосты НЕ подключены к AuthSpec — зафиксируй это честно как отдельный, более крупный P0-подпункт и не пытайся закрыть оба сразу в одном ADR.

## ЭТАП 3 — РЕАЛИЗАЦИЯ

- CAN-16: существующий вызов `ShellTool.run(cmd)` не ломается для уже доверенных локальных путей.
- Allowlist/scope-check оборачивает или гейтит вызов — не переписывает `subprocess.run` и не меняет сигнатуру существующего API.
- Fail-closed по умолчанию: неизвестный или непроверенный caller → отказ, не «пропустить с warning».

## ЭТАП 4 — ТЕСТЫ (hermetic, по образцу `test_workspace_registry_sync.py`)

- Разрешённый локальный путь проходит без изменений.
- Внешний/неизвестный caller без scope — блокируется.
- Мост с валидным `chat_id_scope`/`phone_scope`, но capability вне allowlist — блокируется.
- No-regression: полный `tests_09/` прогон, `mypy`, `consistency_check`.

## ЭТАП 5 — РЕЕСТРЫ

`DECISIONS.md`, `DOCUMENT_REGISTRY.md`, `ARCHITECTURAL_BASELINE_V1.md` §4 (P0 «sandbox/tool-ACL»: design → IMPLEMENTED), запись в CHANGELOG — тот же формат, что ADR-017 (Задача / Что сделано / Тесты / Реестры / Verification).

## ЗАПРЕТЫ

НЕ: трогать Task ×2 / Tool ×2 / Memory ×4 (это P2, отдельный ADR); рефакторить `ShellTool` целиком; проектировать OS-level sandbox (seccomp/контейнер) — на Termux это, вероятно, недостижимо и не нужно, если Этап 1 не покажет обратного; трогать репозиторную структуру (P3); переименовывать существующие сущности; создавать новую параллельную архитектуру.

## ГЛАВНЫЙ ВОПРОС

Не «как спроектировать идеальный sandbox», а: «кто сегодня реально может выполнить произвольный shell-вызов через какой мост, и какой минимальный additive-гейт закрывает именно этот путь — переиспользуя уже существующий AuthSpec/capability-паттерн, а не создавая новый».
