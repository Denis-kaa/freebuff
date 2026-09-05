# ADR-002 — Defer production authentication

## Context

Stage 9 requires authorization behavior, but this environment is not production and the current MVP uses `X-User-Id` plus a demo fallback.

## Decision

Keep the authentication seam (`get_current_user` / `UserContext`) and defer Login/Logout/Session/Refresh/Password reset. Authorization and workspace isolation remain enforced now.

## Rationale

Authentication provider choice is a separate integration decision. Implementing it prematurely would increase coupling and obscure the RBAC contracts.

## Consequences

- Current MVP is suitable for controlled development/demo use, not public production.
- Future JWT/session/OIDC integration replaces identity resolution without rewriting permission checks.
