# RUNNABLE.md — PM OS

## Runtime target

- Host: `whimco`
- Root: `/var/www/pm_os`
- Backend: FastAPI on `127.0.0.1:8010`
- Database: PostgreSQL `pmos_db`
- Frontend: Vite build served by backend static mount

## Readiness

- [x] backend service active
- [x] `/api/health` returns 200
- [x] frontend build succeeds
- [x] backend regression passes
- [x] stage 9 acceptance passes
- [x] Playwright smoke has no console/page errors
- [x] RBAC migration applied
- [ ] real authentication (deferred)
- [ ] Teams API/UI (planned)
- [ ] field-level permission enforcement (planned)
