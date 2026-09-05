# ADR-003 — Teams/RBAC as a portable contract module

## Context

PM OS needs teams, memberships and field-level access. Workspace OS may later reuse these mechanisms as platform capabilities.

## Decision

Implement Teams/RBAC inside PM OS first, behind explicit API/data contracts. Do not import PM OS domain models into `core_02` during this stage.

## Rationale

The feature is compatible with the project model and can provide evidence for a future platform primitive, while preserving additive architecture and low coupling.

## Consequences

- PM OS can evolve independently.
- A future extraction can compare contracts and lifecycle boundaries.
- Platform integration remains a separate review gate, not an implicit refactor.
