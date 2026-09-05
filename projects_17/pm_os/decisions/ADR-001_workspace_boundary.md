# ADR-001 — Workspace OS project versus PM OS runtime workspace

## Context

PM OS is developed inside the Workspace OS repository, but PM OS itself contains runtime workspaces with user projects.

## Decision

Treat `projects_17/pm_os` as the development project/context container. Treat PM OS runtime workspaces as a separate product-level tenant entity. Do not merge their state, namespace, lifecycle, or ownership.

## Rationale

This preserves B1/B2 boundaries and keeps platform evolution additive. Generic capabilities may later be extracted only after an explicit architecture review.

## Consequences

- Development tasks and acceptance live in this project.
- Runtime data remains in PM OS backend/database.
- Future integration uses explicit contracts, not direct shared state.
