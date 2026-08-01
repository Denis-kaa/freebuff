Создаю полную оценку рисков для проекта tg-terminal-toolkit.

```markdown
# RISK MATRIX: tg-terminal-toolkit
## Date: 2026-07-27
## Evaluator: Risk Manager
## Project Type: script (TUI CLI application)
## LISA TC: 4.86 (MEDIUM)
## Timeline: 5 days
## Budget: $2,000 - $2,800

---

## 1. RISK ASSESSMENT

### 1.1 Technical Risks

| ID | Risk | Severity | Probability | Score | Mitigation | Owner |
|----|------|----------|-------------|-------|------------|-------|
| T-01 | Async race conditions (Telethon + Textual event loops) | 4 | 4 | 16 | Separate event loops, asyncio.Lock, stress tests | Developer |
| T-02 | FloodWait blocking UI during mass operations | 3 | 5 | 15 | Exponential backoff, user notification, queue system | Developer |
| T-03 | Cross-platform terminal rendering issues | 3 | 3 | 9 | Feature detection, fallback modes, test matrix | Developer |
| T-04 | Memory overflow with large chat histories | 3 | 2 | 6 | Lazy loading, pagination, streaming | Developer |
| T-05 | Telethon/Textual API breaking changes | 2 | 2 | 4 | Version pinning, abstraction layer | Developer |
| T-06 | FilePicker performance with large directories | 3 | 3 | 9 | Async file scanning, virtual scrolling | Developer |
| T-07 | Message rendering latency (>100ms target) | 3 | 3 | 9 | Virtual list, message batching, profiling | Developer |

### 1.2 Business Risks

| ID | Risk | Severity | Probability | Score | Mitigation | Owner |
|----|------|----------|-------------|-------|------------|-------|
| B-01 | Scope creep (FilePicker complexity, archive features) | 3 | 3 | 9 | Strict DoD, MVP-first approach | Orchestrator |
| B-02 | Timeline slip due to async complexity | 3 | 3 | 9 | Daily manifest updates, buffer 20% | Orchestrator |
| B-03 | Budget overrun from unexpected issues | 2 | 2 | 4 | Contingency buffer, daily tracking | Orchestrator |
| B-04 | Feature requests during development | 2 | 3 | 6 | Change request process, scope freeze | Orchestrator |

### 1.3 Operational Risks

| ID | Risk | Severity | Probability | Score | Mitigation | Owner |
|----|------|----------|-------------|-------|------------|-------|
| O-01 | Session file security breach (credentials exposure) | 4 | 2 | 8 | chmod 600, permission check, .gitignore | Developer |
| O-02 | Network errors during message send/receive | 3 | 4 | 12 | Retry logic, user notification, offline queue | Developer |
| O-03 | Terminal compatibility (xterm, tmux, screen) | 2 | 3 | 6 | Test matrix, graceful degradation | Tester |
| O-04 | Graceful shutdown failures (data loss) | 3 | 2 | 6 | SIGINT/SIGTERM handlers, state persistence | Developer |
| O-05 | Logging sensitive data (phone numbers, codes) | 4 | 2 | 8 | Log sanitization, security review | Developer |

### 1.4 External Risks

| ID | Risk | Severity | Probability | Score | Mitigation | Owner |
|----|------|----------|-------------|-------|------------|-------|
| E-01 | Telegram API rate limits (FloodWait) | 4 | 4 | 16 | Rate limiting, user warning, queue system | Developer |
| E-02 | Telethon library deprecation/breaking changes | 2 | 2 | 4 | Version pinning (1.34+), abstraction layer | Developer |
| E-03 | Textual framework instability | 2 | 2 | 4 | Version pinning (0.40+), minimal feature use | Developer |
| E-04 | Telegram server downtime | 3 | 2 | 6 | Connection retry, user notification | Developer |

---

## 2. RISK HEATMAP

| Severity ↓ / Probability → | 1 | 2 | 3 | 4 | 5 |
|-----------------------------|---|---|---|---|---|
| 5 (Critical)                |   |   |   |   |   |
| 4 (High)                    |   |O-01,O-05|   |T-01,E-01|   |
| 3 (Medium)                  |   |T-04,O-04|B-01,B-02,T-03,T-06,T-07,O-03|O-02|T-02|
| 2 (Low)                     |   |   |B-04|E-04|   |
| 1 (Minimal)                 |   |B-03|E-02,E-03|   |   |

**Legend:**
- 🔴 **Critical (Score ≥ 20):** STOP project, redesign required
- 🟠 **High (Score 15-19):** Extra checks required, mitigation mandatory
- 🟡 **Medium (Score 10-14):** Monitor closely, mitigation recommended
- 🟢 **Low (Score < 10):** Acceptable, standard practices

**Risk Distribution:**
- 🔴 Critical: 0 risks
- 🟠 High: 3 risks (T-01, T-02, E-01)
- 🟡 Medium: 5 risks (O-02, B-01, B-02, T-03, T-06, T-07)
- 🟢 Low: 10 risks

---

## 3. CRITICAL RISKS ANALYSIS

### 3.1 T-01: Async Race Conditions (Score: 16)

**Description:**  
Telethon runs in its own event loop for handling updates, while Textual has its own async event loop for UI rendering. These two loops may conflict when accessing shared state (e.g., message list, chat selection), leading to:
- Data corruption (messages displayed incorrectly)
- UI freeze (event loop blocked)
- Race conditions (state inconsistencies)
- Crashes under load

**Impact:**  
- User experience degradation (UI freeze, incorrect display)
- Potential data loss (unsent messages)
- Debugging complexity (race conditions are hard to reproduce)

**Probability:**  
**High (4/5)** — Async code with multiple event loops is notoriously difficult to get right. Issues often appear only under specific timing conditions.

**Mitigation Plan:**
1. **Architecture:** Use separate asyncio tasks for Telethon and Textual, communicate via asyncio.Queue
2. **Synchronization:** Implement asyncio.Lock for all shared state access
3. **Testing:** Write stress tests with concurrent operations (100+ messages/sec)
4. **Monitoring:** Add logging for race condition detection (timestamp analysis)
5. **Fallback:** Implement graceful degradation if lock contention detected

**Owner:** Developer  
**Cost:** +2h (implementation + testing)  
**Risk Reduction:** Score 16 → 8 (after mitigation)

---

### 3.2 T-02: FloodWait Blocking UI (Score: 15)

**Description:**  
When performing mass operations (downloading chat history, sending multiple files), Telegram API may return `FloodWaitError` with wait times from seconds to hours. If not handled properly:
- UI freezes while waiting
- User has no visibility into progress
- Operations cannot be cancelled
- User frustration and abandonment

**Impact:**  
- Poor user experience (UI unresponsive)
- Lost productivity (user blocked from other operations)
- Potential data loss (interrupted downloads)

**Probability:**  
**Very High (5/5)** — Telegram API actively rate-limits aggressive clients. Mass operations (archive feature) will definitely trigger FloodWait.

**Mitigation Plan:**
1. **Exponential Backoff:** Implement 2^n seconds retry with jitter
2. **User Notification:** Show countdown timer with estimated wait time
3. **Queue System:** Background processing for mass operations
4. **Cancellation:** Allow user to cancel long-running operations
5. **Resume:** Save progress, resume from last successful point
6. **Rate Limiting:** Client-side throttling (max 1 request/second)

**Owner:** Developer  
**Cost:** +3h (implementation + testing)  
**Risk Reduction:** Score 15 → 6 (after mitigation)

---

### 3.3 E-01: Telegram API Rate Limits (Score: 16)

**Description:**  
Telegram enforces strict rate limits on MTProto API:
- Message sending: ~1 msg/sec per chat
- History download: ~200 msgs/batch with delays
- Media upload: size and frequency limits
- Authentication: strict limits on login attempts

Exceeding these limits results in FloodWait, which can block operations for minutes to hours.

**Impact:**  
- Operations paused unexpectedly
- User workflow interrupted
- Archive feature becomes unusable for large chats
- Poor perception of tool reliability

**Probability:**  
**High (4/5)** — Rate limits are well-documented but easy to hit with aggressive usage patterns. Archive feature (FR-018-021) will definitely trigger limits.

**Mitigation Plan:**
1. **Rate Limiter:** Implement token bucket algorithm (1 req/sec baseline)
2. **User Warning:** Notify user before starting mass operations
3. **Progress Tracking:** Show real-time progress with ETA
4. **Batch Processing:** Process in small batches with delays
5. **Queue Priority:** Allow user to prioritize urgent operations
6. **Documentation:** Clear warnings in UI about rate limits

**Owner:** Developer  
**Cost:** +3h (implementation + testing)  
**Risk Reduction:** Score 16 → 7 (after mitigation)

---

## 4. RISK MITIGATION BUDGET

| Risk ID | Risk Description | Mitigation Activities | Cost (hours) | Cost ($) |
|---------|------------------|----------------------|--------------|----------|
| T-01 | Async race conditions | Lock implementation, stress tests, logging | +2h | $100 |
| T-02 | FloodWait blocking UI | Backoff, queue, cancellation, resume | +3h | $150 |
| E-01 | Telegram API limits | Rate limiter, batching, user warnings | +3h | $150 |
| O-02 | Network errors | Retry logic, offline queue, notifications | +1h | $50 |
| **Total** | | | **+9h** | **$450** |

**Original Budget:** $2,000 - $2,800  
**Mitigation Cost:** +$450  
**Adjusted Budget:** $2,450 - $3,250

**Budget Feasibility:** ✅ Within acceptable range (+16-23% buffer)

---

## 5. AI DELIVERY RISK ASSESSMENT

| Area | Risk | Why | Mitigation |
|------|------|-----|------------|
| Async Complexity | 🟠 High | Telethon + Textual async integration is non-trivial | Extra testing, architectural review |
| API Stability | 🟢 Low | Telethon/Textual are mature, version-pinned | Abstraction layer |
| Testing Difficulty | 🟡 Medium | Async race conditions hard to test deterministically | Stress tests, mutation testing |
| Context Window | 🟢 Low | Project scope well-defined, modular | Standard practices |
| Hallucination Risk | 🟢 Low | Well-documented APIs, clear requirements | Knowledge verification chain |

**AI Delivery Feasibility:** ✅ HIGH  
**Overall AI Risk:** 🟡 MEDIUM (manageable with proper testing)

---

## 6. ARCHITECTURAL FRAGILITY ANALYSIS

| Area | Fragility | Consequence | Recommendation |
|------|-----------|-------------|----------------|
| Event Loop Integration | 🟠 High | Race conditions, UI freeze | Separate loops, queue communication |
| Error Handling | 🟡 Medium | Silent failures, data loss | Centralized error handler, logging |
| State Management | 🟡 Medium | Inconsistent UI, crashes | Single source of truth, reactive updates |
| File I/O | 🟢 Low | Blocking operations | Async file operations (aiofiles) |
| Network Layer | 🟡 Medium | Connection drops, retries | Reconnection logic, offline queue |

**Overall Architectural Risk:** 🟡 MEDIUM  
**Recommendation:** Architect must design clear separation between Telethon and Textual event loops

---

## 7. OPERATIONAL RISK ASSESSMENT

| Area | Risk | Production Impact | Mitigation |
|------|------|-------------------|------------|
| Session Security | 🟡 Medium | Credential exposure | chmod 600, .gitignore, permission check |
| Logging Security | 🟡 Medium | Sensitive data in logs | Log sanitization, security review |
| Terminal Compatibility | 🟢 Low | Rendering issues on some terminals | Test matrix, graceful degradation |
| Resource Usage | 🟢 Low | High memory/CPU usage | Lazy loading, profiling |
| Graceful Shutdown | 🟡 Medium | Data loss on interrupt | SIGINT/SIGTERM handlers, state save |

**Overall Operational Risk:** 🟢 LOW  
**Production Survivability:** ✅ HIGH

---

## 8. MANDATORY MITIGATIONS

### 8.1 Technical Safeguards
1. ✅ **Async Architecture Review** — Architect must design clear event loop separation
2. ✅ **Stress Testing** — Developer must write concurrent operation tests
3. ✅ **Rate Limiting** — Implement client-side throttling before API calls
4. ✅ **Error Handling** — Centralized handler with retry logic for all network operations

### 8.2 Verification Stages
1. ✅ **Architectural Audit** — Auditor must verify async design (Phase 2)
2. ✅ **Mutation Testing** — Tester must verify async code quality (Phase 5)
3. ✅ **Cross-Platform Testing** — Test on Linux, macOS, Windows (Phase 5)
4. ✅ **Security Review** — Verify session file handling (Phase 5)

### 8.3 Architectural Controls
1. ✅ **Event Loop Separation** — Telethon and Textual must run in separate tasks
2. ✅ **Queue Communication** — Use asyncio.Queue for inter-loop communication
3. ✅ **Lock Protection** — All shared state must be protected by asyncio.Lock
4. ✅ **Graceful Degradation** — UI must remain responsive during network operations

---

## 9. RESIDUAL RISKS

Even after mitigation, the following risks remain:

| Risk | Residual Score | Acceptance |
|------|----------------|------------|
| T-01: Async race conditions | 8 | ✅ Acceptable (well-tested) |
| T-02: FloodWait blocking | 6 | ✅ Acceptable (user notified) |
| E-01: API rate limits | 7 | ✅ Acceptable (rate limited) |
| O-02: Network errors | 6 | ✅ Acceptable (retry logic) |
| T-03: Terminal compatibility | 9 | ✅ Acceptable (test matrix) |

**Total Residual Risk:** 🟢 LOW  
**Risk Acceptance:** ✅ All residual risks within acceptable bounds

---

## 10. FINAL VERDICT

### 🟢 GO

**Justification:**

1. ✅ **No Critical Risks** — No risks with Score ≥ 20
2. ✅ **Manageable High Risks** — All 3 high-risk areas (T-01, T-02, E-01) have concrete mitigation plans
3. ✅ **Budget Feasibility** — Adjusted budget ($2,450-$3,250) within acceptable range (+16-23%)
4. ✅ **Timeline Feasibility** — 5 days realistic with proper planning
5. ✅ **AI Delivery Feasibility** — Project well-suited for AI-assisted development
6. ✅ **Production Survivability** — Low operational risk, good maintainability

**Conditions:**

1. ✅ **Extra Testing** — +2h for async stress tests (T-01 mitigation)
2. ✅ **Rate Limiting** — +3h for FloodWait handling (T-02, E-01 mitigation)
3. ✅ **Security Review** — Session file handling verification (O-01, O-05)
4. ✅ **Cross-Platform Testing** — Linux, macOS, Windows test matrix (O-03)
5. ✅ **Architectural Audit** — Verify async design in Phase 2

**Recommendations:**

- Monitor async complexity — may escalate to LARGE if issues arise
- Daily manifest updates for timeline variance tracking
- Consider adding Decomposer if project scope expands
- Prioritize MVP features (FR-001 to FR-017) before SHOULD/COULD features

---

## 11. NEXT STEPS

### Phase 2: Architecture (Next)
1. ✅ Risk assessment complete → VERDICT: **GO**
2. → Activate **Architect** role
3. → Design async architecture (Telethon + Textual separation)
4. → Design error handling strategy (FloodWait, network errors)
5. → Design FilePicker architecture (async file scanning)
6. → Create contracts.yaml for module interfaces

### Phase 4: Implementation
1. → Activate **Developer** role
2. → Implement with extra testing for async operations
3. → Implement rate limiting and FloodWait handling
4. → Implement security measures (session file, logging)

### Phase 5: Validation
1. → Activate **Tester** role
2. → Conduct stress tests for async operations
3. → Conduct cross-platform testing
4. → Conduct mutation testing for async code
5. → Conduct security review

---

**Report generated:** 2026-07-27  
**Evaluator:** Risk Manager  
**Status:** ✅ COMPLETE  
**Verdict:** 🟢 GO  
**Confidence:** 85%

---

## APPENDIX A: RISK SCORING METHODOLOGY

**Severity Scale (1-5):**
- 1 (Minimal): Negligible impact, cosmetic issue
- 2 (Low): Minor impact, workaround available
- 3 (Medium): Moderate impact, feature degradation
- 4 (High): Major impact, feature unavailable
- 5 (Critical): Catastrophic impact, project failure

**Probability Scale (1-5):**
- 1 (Rare): <10% chance of occurrence
- 2 (Unlikely): 10-30% chance
- 3 (Possible): 30-50% chance
- 4 (Likely): 50-80% chance
- 5 (Almost Certain): >80% chance

**Risk Score = Severity × Probability**

**Risk Levels:**
- 1-9: 🟢 Low (Acceptable)
- 10-14: 🟡 Medium (Monitor)
- 15-19: 🟠 High (Mitigate)
- 20+: 🔴 Critical (Stop/Redesign)

---

## APPENDIX B: ASSUMPTIONS

1. ✅ Stable internet connection available
2. ✅ Valid Telegram account for testing
3. ✅ Python 3.10+ environment
4. ✅ Terminal with UTF-8 support
5. ✅ No major Telegram API changes during development
6. ✅ Telethon 1.34+ and Textual 0.40+ remain stable
7. ✅ User has basic terminal proficiency

---

## APPENDIX C: CONSTRAINTS

1. ⚠️ Telegram API rate limits (FloodWait)
2. ⚠️ Terminal rendering capabilities vary
3. ⚠️ Session file must be secured (chmod 600)
4. ⚠️ No Bot API allowed (MTProto only)
5. ⚠️ All I/O must be async (no blocking operations)
6. ⚠️ Memory usage < 200MB for 10k messages

---

**END OF RISK ASSESSMENT**
```

✅ **Risk assessment complete**

**Summary:**
- **Verdict:** 🟢 GO
- **Critical Risks:** 0
- **High Risks:** 3 (T-01, T-02, E-01) — all manageable
- **Adjusted Budget:** $2,450-$3,250 (+$450 for mitigation)
- **Timeline:** 5 days (feasible)
- **AI Delivery Feasibility:** HIGH

**Next:** Move to Phase 2 — Architecture (Architect role)