# LISA-3 COMPLEXITY REPORT

## Project: tg-terminal-toolkit
## Date: 2026-07-27
## Evaluator: LISA Estimator

## 1. ENGINEERING COMPLEXITY (EC)

| Parameter | Score (1-10) | Justification |
|-----------|--------------|---------------|
| L (Logic) | 4 | CRUD-подобная логика: авторизация, навигация по чатам, отправка сообщений/медиа. Нет сложных алгоритмов, ML или state-machine. Валидация файлов, обработка FloodWait — moderate complexity. 17 MUST требований, но каждое по отдельности простое. |
| I (Integration) | 6 | Одна главная интеграция — Telethon MTProto (сложный протокол: 2FA, сессии, FloodWait, updates). Вторая — Textual TUI framework. Третья — файловая система (async I/O). MTProto нетривиален: требует понимания MTProto protocol, handling session files, update handlers. |
| S (Scale) | 3 | Single-user desktop/terminal client. Локальное хранилище SQLite. До 10k сообщений в памяти (NFR-003: <200MB). Нет многопользовательского режима, нет серверной части. Масштаб минимальный. |
| A (Async) | 7 | **Критический параметр.** Строгий async (NFR-001): UI не должен блокироваться. Event-driven архитектура: Textual event loop + Telethon updates handler параллельно. Async file I/O (aiofiles). Concurrent operations: загрузка сообщений при скролле, отправка медиа, обработка FloodWait с паузой. Race conditions возможны между UI и network layers. |
| U (UI) | 6 | TUI двухпанельный интерфейс (чаты слева, сообщения справа). FilePicker — встроенный файловый менеджер с навигацией. Горячие клавиши (Ctrl+F). Индикаторы непрочитанных, статусы онлайн. Async loading при скролле. Textual framework — не самый простой для сложных интерактивных интерфейсов. |
| C (Compliance) | 4 | Базовая безопасность: права 600 на файл сессии (NFR-004), запрет логирования конфиденциальных данных (NFR-005), поддержка 2FA. Нет encryption at rest, нет audit logs, нет compliance стандартов. Graceful shutdown (SIGINT/SIGTERM). |
| **EC Average** | **5.0** | (4+6+3+7+6+4)/6 = 30/6 = 5.0 |

## 2. AI DELIVERY COMPLEXITY (ADC)

| Parameter | Score (1-10) | Justification |
|-----------|--------------|---------------|
| P (Predictability) | 3 | Требования чётко формализованы в brief.md и parsed_requirements.md. 27 требований с приоритетами (MUST/SHOULD/COULD). Dependency graph построен. Acceptance criteria определены. Мало неопределённости в бизнес-логике. |
| D (Dependencies) | 5 | 5 основных зависимостей: telethon 1.34+, textual 0.40+, rich 13.0+, aiofiles 23.0+, sqlite3 (stdlib). Telethon — критичная зависимость с MTProto API (может меняться). Textual — активно развивающийся фреймворк (API может меняться). Среднее количество зависимостей, но все стабильные. |
| R (Risk) | 5 | **Технические риски:** FloodWait (Telegram API limits), кроссплатформенность терминалов (Linux/macOS/Windows), async race conditions, MTProto protocol changes. **Бизнес-риски:** low (single-user tool). **Операционные риски:** medium (session file security, network errors). Kitty/Sixel протоколы — uncertain support. |
| X (X-factor) | 4 | Неизвестные факторы: поведение терминалов (xterm, tmux, screen) может отличаться, FilePicker в TUI — неочевидный UX, рендеринг превью картинок (Kitty/Sixel) — зависит от терминала, memory management при 10k сообщений. Есть вопросы, но не критичные. |
| V (Verification) | 6 | **Сложность тестирования:** async операции сложно тестировать (timing issues). Telethon интеграция требует mocking MTProto responses. Textual UI testing — нужно тестировать виджеты и события. Mutation testing для async кода. Integration tests с реальным Telegram API сложно автоматизировать. Performance tests (memory <200MB, response <100ms). |
| **ADC Average** | **4.6** | (3+5+5+4+6)/5 = 23/5 = 4.6 |

## 3. TOTAL COMPLEXITY SCORE

**TC_base = (EC × 0.65) + (ADC × 0.35)**

**TC_base = (5.0 × 0.65) + (4.6 × 0.35) = 3.25 + 1.61 = 4.86**

**k_cal = 1.0** (default, no previous data from LESSONS.md)

**TC_quote = TC_base × k_cal = 4.86 × 1.0 = 4.86**

## 4. COMPLEXITY LEVEL

| TC Range | Level | Description |
|----------|-------|-------------|
| 0-4 | SMALL | Simple task |
| 4-6 | MEDIUM | Standard project |
| 6-8 | LARGE | Complex project |
| 8-10 | COMPLEX | Enterprise system |

**Current Project: MEDIUM (TC = 4.86)**

**Обоснование:** Проект находится в верхней границе MEDIUM. Высокая сложность async операций (A=7) и интеграции с MTProto (I=6) компенсируется простым масштабированием (S=3) и чёткими требованиями (P=3). AI delivery complexity умеренная из-за сложностей тестирования async кода и интеграции с Telegram API.

## 5. TIMELINE ESTIMATE

| Phase | Hours | Days | Justification |
|-------|-------|------|---------------|
| Decomposition | 3 | 0.4 | Skip для MEDIUM (per routing), но рекомендуем для clarity |
| Architecture | 5 | 0.6 | ADR для async patterns, error handling, FilePicker design |
| Implementation | 24 | 3.0 | 5 модулей (auth, tg_client, ui/app, ui/widgets, storage), ~1500 LOC |
| Verification | 8 | 1.0 | Unit tests (>80%), integration tests, mutation testing |
| **Total** | **40** | **5.0** | |

**Timeline Formula:** Total Days = (Decompose + Architecture + Implementation + Verification) / 8 hours

**Total Days = 40 / 8 = 5 days**

**Breakdown by role:**
- Orchestrator: 0.5h
- Explainer: 1.5h (✅ done)
- LISA: 2h (✅ done)
- Risk Manager: 1.5h
- Architect: 5h
- Developer: 24h (3 days)
- Tester: 6h
- Fixer: 2h (если нужны баги)
- Acceptance: 1h
- Documenter: 2h
- Retrospective: 1h

## 6. BUDGET ESTIMATE

**Hourly Rate:** $50/hour (AI-assisted development)

**Total Hours:** 40 hours

**Base Budget:** 40 × $50 = $2,000

**Buffer (20%):** $2,000 × 1.2 = $2,400

**Budget Range:** $2,000 - $2,800

**Calculation:** Total Hours × $50/hour × 1.2 (buffer)

**Breakdown:**
- Analysis & Estimation: 4h × $50 = $200
- Architecture: 5h × $50 = $250
- Implementation: 24h × $50 = $1,200
- Verification: 8h × $50 = $400
- Buffer (20%): $410

**Total:** $2,460 ≈ $2,500

## 7. REQUIRED ROLES (based on TC_quote)

**Project Type:** script (TUI CLI application)

**Complexity:** MEDIUM (TC = 4.86)

**Routing Logic:**
- Project Type: script → skip frontend, devops
- Complexity: MEDIUM (4-6) → skip decomposer, auditor (per kwork_roadmap.md)
- Response Writer: skip (not presale project)

**Active Roles:**
1. ✅ Orchestrator (✅ done)
2. ✅ Context Keeper (implicit)
3. ✅ Explainer (✅ done)
4. ✅ LISA Estimator (✅ done)
5. ⏳ Risk Manager
6. ⏳ Architect
7. ⏳ Developer
8. ⏳ Tester
9. ⏳ Fixer (if needed)
10. ⏳ Acceptance Agent
11. ⏳ Documenter
12. ⏳ Retrospective Agent

**Skipped Roles:**
- ❌ Decomposer (skip for MEDIUM complexity)
- ❌ Auditor (skip for MEDIUM complexity)
- ❌ Response Writer (skip for MEDIUM complexity)
- ❌ Frontend Dev (skip for script type)
- ❌ DevOps/SRE (skip for script type)

**Total Active Roles:** 12 out of 17

**Note:** Рекомендуем добавить Decomposer и Auditor, если проект будет расширяться (например, добавление серверной синхронизации, multi-user support).

## 8. RISK FACTORS

**High Risk Areas:**

1. **Async Race Conditions (Severity: High, Probability: Medium)**
   - Telethon updates и Textual events могут конфликтовать
   - Concurrent file operations могут привести к data corruption
   - **Mitigation:** Использовать asyncio.Lock для критических секций, тестировать под нагрузкой

2. **FloodWait Handling (Severity: Medium, Probability: High)**
   - Telegram API может блокировать при частых запросах
   - Массовая загрузка истории чата может триггерить FloodWait
   - **Mitigation:** Exponential backoff, user notification, queue system

3. **Cross-Platform Terminal Compatibility (Severity: Medium, Probability: Medium)**
   - Различия в поддержке ANSI escape codes между терминалами
   - Kitty/Sixel протоколы поддерживаются не всеми терминалами
   - **Mitigation:** Fallback на текстовый режим, feature detection

4. **Memory Management (Severity: Medium, Probability: Low)**
   - 10k сообщений могут превысить лимит 200MB
   - Утечки памяти при длительной работе
   - **Mitigation:** Lazy loading, pagination, memory profiling

5. **Session File Security (Severity: High, Probability: Low)**
   - Session file содержит credentials
   - Неправильные права доступа могут привести к утечке
   - **Mitigation:** Strict permission checks (600), warning on insecure permissions

6. **Telethon API Changes (Severity: Medium, Probability: Low)**
   - Telethon может обновить API в будущих версиях
   - MTProto protocol changes
   - **Mitigation:** Pin telethon version, abstraction layer (tg_client.py)

**Mitigation Strategies:**
- Extra testing для async operations (stress tests, race condition detection)
- Load testing перед production use
- Feature detection для terminal capabilities
- Memory profiling и optimization
- Security audit для session handling
- Version pinning и abstraction layers

## 9. RECOMMENDATIONS

**For Orchestrator:**
- ✅ Project classified as MEDIUM (TC = 4.86)
- ✅ Skip Decomposer, Auditor, Response Writer (per MEDIUM routing)
- ✅ Skip Frontend, DevOps (per script type)
- ⚠️ Recommend adding Decomposer if project scope expands
- ⚠️ Monitor async complexity — may escalate to LARGE if issues arise

**For Architect:**
- **Critical ADRs needed:**
  1. Async architecture: Telethon + Textual event loop integration
  2. Error handling strategy: FloodWait, network errors, file I/O errors
  3. FilePicker design: navigation, file validation, async loading
  4. Session management: security, auto-reconnect, 2FA flow
  5. Memory management: pagination, lazy loading, cleanup
- **Patterns to use:**
  - Event-driven architecture (Textual events + Telethon updates)
  - Observer pattern (UI updates from network events)
  - Strategy pattern (different message types: text, image, video, document)
  - Factory pattern (FilePicker, message rendering)
- **Failure scenarios to document:**
  - Network disconnection during file upload
  - FloodWait during mass download
  - Session file corruption
  - Terminal resize during operation
  - Memory overflow with large chat history

**For Developer:**
- **Priority order:**
  1. auth.py (FR-001 to FR-004) — foundation
  2. tg_client.py (Telethon wrapper) — core integration
  3. ui/app.py (main TUI) — user interface
  4. ui/chat_list.py, ui/message_view.py (widgets) — UI components
  5. ui/file_picker.py (FilePicker) — media selection
  6. storage/archive.py (optional, SHOULD have)
- **Critical implementation details:**
  - Strict async/await (no blocking calls in event loop)
  - Type hints mandatory (NFR requirement)
  - Error handling with retry logic
  - Session file permissions (chmod 600)
  - Logging without sensitive data
- **Testing requirements:**
  - Unit tests >80% coverage
  - Integration tests for Telethon mocking
  - UI tests for Textual widgets
  - Async tests with pytest-asyncio
  - Performance tests (memory <200MB, response <100ms)
- **Atomic commits:**
  - feat(auth): implement phone authorization with 2FA
  - feat(tg_client): wrap Telethon with error handling
  - feat(ui): create two-panel TUI layout
  - feat(file_picker): implement file navigation widget
  - feat(messaging): add text and media sending
  - fix(flood_wait): implement auto-pause on FloodWaitError

**For Tester:**
- **Test strategy:**
  - Unit tests: auth, tg_client, utils
  - Integration tests: Telethon mocking, file I/O
  - UI tests: Textual widget testing
  - Async tests: race conditions, concurrent operations
  - Performance tests: memory usage, response time
  - Security tests: session file permissions, data leakage
- **Mutation testing focus:**
  - Async error handling paths
  - FloodWait retry logic
  - File validation
  - Session management
- **Edge cases:**
  - Network disconnection during operation
  - FloodWait with long pause (e.g., 24 hours)
  - Large files (>100MB) upload
  - 10k+ messages in chat
  - Terminal resize during operation
  - Invalid session file

**For Risk Manager:**
- **VERDICT recommendation:** 🟢 GO
- **Conditions:**
  - Extra testing for async operations
  - Load testing before production use
  - Security audit for session handling
  - Cross-platform testing (Linux, macOS, Windows)

---

**SUMMARY:**

**Project:** tg-terminal-toolkit
**Complexity:** MEDIUM (TC = 4.86)
**Timeline:** 5 days
**Budget:** $2,000 - $2,800
**Active Roles:** 12/17
**Risk Level:** Medium (manageable with proper testing)
**AI Suitability:** High (ASI = 7-8) — well-suited for AI-assisted delivery

**Next Steps:**
1. Risk Manager → risk assessment
2. Architect → architecture design + ADRs
3. Developer → implementation (5 modules)
4. Tester → comprehensive testing
5. Acceptance → final QA
6. Documenter → documentation
7. Retrospective → lessons learned

---

**Report generated:** 2026-07-27
**Evaluator:** LISA-3 AI-Native Complexity Estimator
**Status:** ✅ COMPLETE