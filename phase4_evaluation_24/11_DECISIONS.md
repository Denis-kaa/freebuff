# 11_DECISIONS — архитектурные решения (Phase 4, pomt83)

> Протокол pomt83 §23.7 «architectural decisions».

| # | Decision | Reason | Status |
|---|---|---|---|
| D-01 | **Phase 4 = closed (v5.20.0), REUSE > CREATE** | forensic-аудит: все компоненты Phase 4 исполняемы; параллельная архитектура запрещена (§5) | ✅ |
| D-02 | **Не реализовывать недостающее** — его нет для Phase 4 | gap-анализ: 0 новых модулей | ✅ |
| D-03 | **Теги §7 — proposal, НЕ глобальное внедрение** | механическое тегирование всего repo = чрезмерная сложность; §T anchor index в reality map = minimal PoC | ✅ (proposal) |
| D-04 | **UNFORGED ≠ «не работал»** | Wizard↔Forge orthogonal-STATE (§7.3, Hypothesis C верифицирована) | ✅ (подтверждено кодом) |
| D-05 | **Anchor resolvability — по символу/секции, не по строке** | line-number prohibited (§I.3) | ✅ |
| D-06 | **2 «реальных» фейла не чинить в этой сессии** — уже исправлены v5.189.6/8 | ANTI-5 scope discipline; перепроверены зелёными | ✅ |
| D-07 | **Full-suite запускать через tmux (detached)** | Termux/Android OOM/tmux-kill risk (DEFERRED-7) | ✅ |
| D-08 | **Секция K (Project/Workspace) — deferred, не блокер** | Phase 4 инстансы вне scope Phase 4 архитектуры | ✅ (открыта как OI-07) |

## Непринятые решения (open) — все закрыты (2026-08-16)

- ~~R-1: `record_run` degraded→FAILED маппинг~~ → **принят как D-09** (v5.189.10): degraded сохраняет статус.
- ~~`@pytest.mark.slow` для real-integration~~ → **внедрён** в v5.189.12.

> Открытых непринятых решений не осталось.

## Принятые решения (дополнение 2026-08-16)

| # | Decision | Reason | Status |
|---|---|---|---|
| D-09 | **degraded не меняет статус** (ok→DEPLOYED, degraded→keep, иное→FAILED); UNFORGED+degraded без персиста | R-1 closure v5.189.10: degraded ≠ failed; B10/R-127 инвариант UNFORGED ⇒ пустой last_pipeline | ✅ (v5.189.10, 5 тестов) |
