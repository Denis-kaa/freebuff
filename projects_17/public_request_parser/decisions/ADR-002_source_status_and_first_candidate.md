# ADR-002: Source status and first technical candidate

**Status:** Accepted
**Date:** 2026-08-23
**Scope:** PROJECT-LOCAL
**Project:** `projects_17/public_request_parser`
**Related:** [`SOURCE_POLICY_MATRIX.md`***REMOVED***(../SOURCE_POLICY_MATRIX.md), [`ROADMAP.md`***REMOVED***(../ROADMAP.md), [`ADR-001_parser_boundary_and_source_gates.md`***REMOVED***(ADR-001_parser_boundary_and_source_gates.md)

## 1. Context

P2 research confirmed real RSS/Atom endpoints, but technical availability does not by itself establish permission for user-facing aggregation. The project also needs to distinguish a technically useful fixture from a source suitable for a public product.

The Stack Overflow Python Atom feed is a stable technical candidate with observable Atom fields. However, it is primarily Q&A content and the applicable Terms, licensing, attribution and storage scope must be respected. Telegram public web-preview has technical parsing precedent, but current project evidence does not approve live aggregation.

## 2. Decision

1. Introduce source statuses: `allowed`, `technical_candidate`, `conditional`, `manual_review`, `policy_blocked`.
2. Use `technical_candidate` for Stack Overflow Python Atom during fixtures and local parser canary only.
3. Keep Stack Exchange API `conditional` until purpose, attribution, quota, field scope, retention and deployment mode are explicitly reviewed.
4. Keep DEV RSS and Reddit Atom `manual_review` until their content-use and retention conditions are verified for the intended product.
5. Keep Telegram web-preview `policy_blocked` for live aggregation until a separate policy/legal decision authorizes the exact mode and scope.
6. Do not mark any source `allowed` without a source record containing evidence, allowed fields, retention, polling floor, attribution, review date and reversible disable behavior.
7. Permit P3 contracts and fixture-based P4 implementation while G2 live-source approval remains open.

## 3. Alternatives

### A. Treat every public RSS/Atom endpoint as `allowed`

**Rejected.** This conflates transport availability with copyright, terms, attribution, purpose and retention requirements.

### B. Stop all engineering until a commercial source is approved

**Rejected.** Domain contracts, parser fixtures, deduplication, TTL and explainability can be developed safely without live user-facing polling.

### C. Use Stack Overflow as the production commercial lead source

**Rejected.** The feed is useful for request-like technical content but does not establish commercial service demand or product fit.

## 4. Consequences

- Source policy becomes explicit and reversible.
- Fixture engineering can proceed without claiming a false production approval.
- The first live pilot remains blocked until G2 is closed.
- Product usefulness for commercial service requests still requires a separate source discovery track.
- Every source adapter carries additional evidence and policy metadata.

## 5. Verification

- [x***REMOVED*** `SOURCE_POLICY_MATRIX.md` contains the source records and evidence.
- [x***REMOVED*** Stack Overflow Atom is marked `technical_candidate`.
- [x***REMOVED*** Stack Exchange API is marked `conditional`.
- [x***REMOVED*** Telegram web-preview is marked `policy_blocked`.
- [x***REMOVED*** P3/P4 are explicitly allowed to proceed without live polling.
- [ ***REMOVED*** A production user-facing source is marked `allowed`.
