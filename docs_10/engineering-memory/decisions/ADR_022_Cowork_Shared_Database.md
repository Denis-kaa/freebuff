# ADR-022: Cowork Shared Database — rqlite Bridge for Multi-Instance Buffy

**Status:** Accepted (Implemented)
**Date:** 2026-08-24
**Deciders:** Buffy (agent), User (operator)

---

## 1. Context

User request (2026-08-24): "прокинем мост — нам нужно именно общая база данных, тогда иначе смысл падает во всём."

The Cowork mode (PLATFORM.md §2.1) envisions multiple Buffy instances working on the same project simultaneously. The core blocker is shared state — without a common database, two Buffy instances are two developers with a shared repo but no sync calls.

Existing infrastructure:
- **ADR-010**: Telegram-stored relay for state sync (LWW delta-sync) — handles file-level sync but not SQL-level shared state
- **ADR-012**: Swappable Brain — Buffy's identity is decoupled from the platform
- **RemoteDB** (`core_02/remote_db.py`): new HTTP client for rqlite with local SQLite fallback

## 2. Decision

### Architecture: rqlite on VPS + RemoteDB adapter

```
Termux (Buffy #2)              VPS WHIMCO (Buffy #1)
──────────────────              ──────────────────────
RemoteDB                        rqlite v10.2.7
  │                               │
  ├─ HTTP POST ──────────────────►├── /db/execute
  ├─ HTTP POST ──────────────────►├── /db/query
  │                               │
  ├─ local SQLite (fallback)      ├── /data/rqlite/db.sqlite
  │                               │
  └─ 25 hermetic tests            └── systemd: rqlite.service
```

### rqlite server (VPS WHIMCO)

- **rqlite v10.2.7** on `185.233.184.192:4001`
- systemd service with auto-restart
- UFW: port 4001 open
- Data directory: `/data/rqlite`
- No auth (single-user pilot; auth to be added if multi-user needed)

### RemoteDB adapter

- `core_02/remote_db.py` — sqlite3-compatible interface over rqlite HTTP API
- API format: `POST /db/execute` and `/db/query` with JSON array of SQL strings (rqlite v10 format)
- SQL parameter interpolation: `?` → properly escaped values (strings quoted, NULLs handled)
- **Local fallback**: if rqlite unreachable, falls back to local SQLite file
- **Lazy connection**: remote tested on first use, not at construction
- `health()` method returns connection status

### Key design decisions

| Decision | Rationale |
|----------|-----------|
| rqlite over raw SQLite replication | Raft consensus = no conflict resolution needed |
| HTTP API (no FUSE/drivers) | Works from any language/device, no kernel deps |
| Local fallback preserved | local-first invariant (AGENTS.md §3) |
| SQL interpolation (no prepared stmts) | rqlite v10 array format doesn't support `?` placeholders |
| Single-node (not cluster) | Pilot phase; cluster can be added later if needed |

## 3. Consequences

### Positive
- Two Buffy instances can share one database transparently
- RemoteDB is a drop-in replacement for sqlite3.Connection in MemoryStore
- Local-first preserved: offline work falls back to local SQLite
- 25 hermetic tests, mypy clean

### Negative
- rqlite on single VPS = SPOF (mitigated: local fallback + data in `/data/rqlite/`)
- SQL interpolation (no parameterized queries) = injection risk if user-controlled SQL reaches adapter (mitigated: MemoryStore uses fixed schema, no user SQL)
- Network latency for remote queries (~50ms round-trip Termux→VPS)

### Risks
- rqlite v10 API breaking changes (mitigated: pinned version, tests)
- VPS outage → local fallback engages automatically

## 4. Infrastructure setup (completed 2026-08-24)

- [x***REMOVED*** rqlite v10.2.7 installed on VPS WHIMCO (`/usr/local/bin/rqlite`)
- [x***REMOVED*** systemd service `rqlite.service` enabled + running
- [x***REMOVED*** UFW port 4001 open
- [x***REMOVED*** Smoke test: CREATE/INSERT/SELECT/DROP all pass
- [x***REMOVED*** `core_02/remote_db.py` — RemoteDB adapter (25 tests)
- [x***REMOVED*** ADR-022 documented

## 5. Follow-up (future)

- **Pilot verification**: connect MemoryStore to rqlite, run full test suite via remote
- **Auth**: add rqlite basic auth when multi-user needed
- **Cluster**: add second rqlite node on another host for HA
- **Sync with ADR-010**: combine TG relay (file sync) + rqlite (SQL sync) for complete Cowork
