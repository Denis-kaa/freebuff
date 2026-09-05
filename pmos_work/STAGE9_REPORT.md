# Этап 9 — Users / Roles / Permissions / Workspace Access
## Финальный отчёт (§53)

> Дата: 2026-09-01 · Сервер: whimco (`/var/www/pm_os`) · База: `pmos_db`
> Статус этапа: **реализован, развёрнут, принят** (22/22 acceptance + 118 регрессия + 8/8 UI-flow)

---

## 1. Архитектура Authentication

- **Подход:** для MVP — идентификация по заголовку `X-User-Id` (FastAPI dependency `get_current_user` в `app/rbac.py`).
- **Demo-fallback:** без заголовка система работает как демо-админ (полный доступ) — так сохраняется работа существующих цепочек (этапы 1–8) без обязательного логина.
- **Правила:**
  - `X-User-Id` + `X-Workspace-Id` → `UserContext` (`user_id`, `workspace_id`, `role_code`, `permissions`, `display_name`).
  - Если реальный `user_id` указан, но membership нет/не ACTIVE → **доступ запрещён** (нет demo-fallback для реальных id).
  - Деактивированный пользователь (membership `DEACTIVATED`) → 403.
- **Не реализовано (осталось):** Login/Logout/Session/Refresh/Password reset. Пароли не хранятся; при подключении внешнего Auth Provider (Supabase/внешний OIDC) достаточно прокинуть identity в тот же `get_current_user`.

## 2. Архитектура Authorization

- **Модель:** `User → WorkspaceMembership → Role → Permissions → Resources` (§1).
- **Permission Engine** (`app/rbac.py`):
  - `require_permission("project.update")` — FastAPI dependency, проверяет наличие кода у роли текущего пользователя в активном workspace.
  - `check_workspace_access(ctx, resource_workspace_id)` — изоляция workspace (IDOR-защита).
  - `mask_finance()` — удаляет финансовые поля из payload, если нет `finance.read`.
  - Роли загружаются из БД (не хардкод `if role == "admin"`).
- **Принцип:** безопасность только на backend; frontend лишь отражает доступы (UX).

## 3. Users

- Таблица `users` апгрейджена: `name`, `avatar_url`, `timezone`, `language`, `is_active`.
- В демо-workspace — 27 участников (реальные люди + тестовые роли).
- Удаление не ломает историю: статусы membership `ACTIVE | INVITED | SUSPENDED | DEACTIVATED` (soft).

## 4. Workspace Membership

- Таблица `workspace_members`: `workspace_id`, `user_id`, `role_id`, `status`, `joined_at`, `created_at`.
- Уникальность `(workspace_id, user_id)`; FK `ON DELETE CASCADE`.
- Backfill: существующие пользователи переведены в membership при миграции.
- Защита последнего OWNER: нельзя понизить/удалить единственного владельца.

## 5. Roles

- Таблица `roles`: системные роли (`workspace_id IS NULL`) + кастомные (по workspace).
- 5 системных ролей: **OWNER, ADMIN, MANAGER, MEMBER, VIEWER**.

## 6. Permissions

- **34 permission-кода**, каталог в `permissions` + связи в `role_permissions` (**97 связей** для системных ролей).
- Группы: `project.*` (read/create/update/delete/import/bulk_update), `task.*`, `production.*`, `finance.*`, `document.*`, `automation.*`, `view.*`, `workspace.*`, `member.*`, `role.manage`.
- `GET /permissions` возвращает полную карту `{code: bool}` + роль + workspace (используется frontend).

## 7. Custom Roles

- API: `POST/PATCH /workspaces/{id}/roles`, `POST .../roles/{id}/duplicate`.
- UI: экран «Роли» (`RolesView.jsx`) — создание/редактирование кастомных ролей с чекбоксами по группам прав, Duplicate; системные роли — только копированием (permissions системных нельзя менять).

## 8. Teams

- **Модели** `Team`, `TeamMember` созданы (§12) — архитектурно подготовлено.
- API/UI **не реализованы** (осталось): team-based access будет слоем поверх `field_permissions`.

## 9. Invitations

- Таблица `workspace_invitations`: `email`, `role_id`, `token_hash` (SHA-256, raw token не хранится), `expires_at` (7 дней), `invited_by`, `accepted_at`, `revoked_at`.
- API: `POST .../members/invite`, `GET .../invitations`, `DELETE .../invitations/{id}` (revoke).
- UI: «Команда» → «+ Пригласить» (email + роль), список приглашений со статусом/отзывом.
- `POST /api/invitations/accept` реализован для уже идентифицированного пользователя: проверяет одноразовый token hash, expiry/revoke, совпадение email, создаёт ACTIVE membership и помечает invitation accepted.
- Полностью unauthenticated accept (с созданием/логином аккаунта) намеренно отложен до real authentication; bearer token не используется как identity.

## 10. Workspace switching

- Backend: заголовок `X-Workspace-Id`; все роутеры фильтруют по `ctx.workspace_id`.
- UI: `WorkspaceSwitcher` в навигации — список workspace, галочка на активном, **«Создать workspace»** (название, TZ, валюта; создатель автоматически OWNER).
- `POST /workspaces` возвращает `owner_id` + `my_role: OWNER` → авто-переключение.
- Проверено: смена workspace реально меняет данные (изоляция проектов).

## 11. Field-level permissions

- Модель `field_permissions` создана (§14) — **архитектурно подготовлено**.
- Для MVP финансовый блок реализован жёстко через permission `finance.read` (см. п. 12); точечные field-level правила — осталось.

## 12. Finance security

- **API:** без `finance.read` финансовые поля (`payment_percent`, `currency`, `advance_date`, `final_payment_date`) маскируются в `None` в ответах проектов.
- **Dashboard:** `/dashboard-data/finance` → **403** без `finance.read`.
- Проверено acceptance-тестом (viewer/роль без finance).

## 13. Export security

- `exports.py` требует `project.read`.
- Без `finance.read` Excel/CSV экспорт **не содержит** финансовые колонки (даже при экспорте всей таблицы, §47).

## 14. Import security

- Permission `project.import` проверяется на всех import API endpoints: upload, mapping, save-mapping, history, job/preview/errors, confirm, cancel, templates.
- Viewer/роль без `project.import` получает **403** до обработки файла.
- Import job и mapping используют `ctx.workspace_id`; cross-workspace job access защищён 404.
- Preview/confirm передают workspace в import service; импорт не использует demo workspace для данных выбранного workspace.

## 15. Automation security

- CRUD автоматизаций: `automation.read/create/update/delete` + `check_workspace_access` на каждый объект.
- Runs/events/notifications/risk — тоже под workspace-изоляцией.
- Выполнение автоматизаций — в системном контексте scheduler'а (без пользовательских прав); per §41 MVP.

## 16. API (итого)

| Группа | Endpoint'ы |
|---|---|
| Me | `GET/PATCH /me` |
| Permissions | `GET /permissions`, `GET /permissions/list` |
| Workspaces | `GET/POST /workspaces`, `GET/PATCH /workspaces/{id}` |
| Members | `GET /workspaces/{id}/members`, `PATCH/DELETE .../members/{member_id}`, `POST .../members/invite` |
| Invitations | `GET .../invitations`, `DELETE .../invitations/{id}` |
| Roles | `GET/POST .../roles`, `PATCH .../roles/{role_id}`, `POST .../roles/{role_id}/duplicate` |

Защищены permission'ами: projects, tasks, views, automations, dashboard-data, exports, custom-fields, calendar.

## 17. Database migrations

- **`migrate_v9.sql`** (применён к `pmos_db`, идемпотентен):
  - таблицы `roles`, `permissions`, `role_permissions`, `workspace_members`, `teams`, `team_members`, `field_permissions`, `workspace_invitations`;
  - апгрейд `users` и `workspaces` (timezone, default_currency, working_days/hours);
  - seed: 5 ролей, 34 permission, 97 связей;
  - backfill существующих пользователей в memberships.
- `app/seed_rbac.py` — идемпотентный self-healing seed при старте приложения и в `conftest.py` (для тестовой БД `pmos_test`).

## 18. Security tests (backend)

- **`acceptance_v9.py`** (live API, 22 проверки):
  - permission map, список ролей;
  - viewer → 403 на PATCH/DELETE проекта;
  - finance masking через API;
  - dashboard `/finance` → 403;
  - export без финансовых полей;
  - **IDOR** cross-workspace → 403/404;
  - деактивированный пользователь → доступ запрещён;
  - invite flow, revoke, duplicate role;
  - manager создаёт проекты; demo-admin регрессия.
- **`ui_acceptance_v9.py`** (live, 8 проверок): создание роли, правка прав, invite/list/revoke, PATCH /me реального пользователя, смена роли участника, permission map.
- **Регрессия:** `pytest tests/` → **118 passed** (включая IDOR/workspace isolation в `test_stage9`).

## 19. Frontend permission tests

- **Выполнены** — `vitest` + `@testing-library/react` (jsdom), `npm test`.
- **`src/rbac/permissions.test.jsx` — 11 тестов (§43/§45):**
  - Create: viewer не видит «+ Новый проект», «+ Новая задача», «+ Добавить позицию», «+ Добавить документ»; manager — видит;
  - Edit/Delete: viewer не видит «Сохранить»/«Архивировать» и удаление сохранённых представлений; manager — видит;
  - Finance: manager без `finance.read` не видит встроенное представление «Финансы»; с правом — видит;
  - Nav (§45): viewer не видит Автоматизации/Настройки/Команду/Роли; manager с правами — видит.
- Добавлен `can()`-гейтинг в ProjectsView («+ Новый проект», импорт, bulk-архив, удаление/создание представлений, builtin «Финансы» только с `finance.read`) и ProjectDetail (Сохранить/Архивировать/Новая задача/Добавить позицию/Добавить документ).

## 20. Acceptance Test results

| Проверка | Результат |
|---|---|
| stage9 acceptance (`acceptance_v9.py`) | **22/22 passed** |
| UI flows (`ui_acceptance_v9.py`) | **8/8 passed** |
| Backend regression (`pytest tests/`) | **118 passed** |
| Frontend build | **✓ 436.70 kB, 4.40s** |
| Frontend tests (`npm test`) | **11/11 passed** |
| `/api/health`, `/api/me`, `/api/permissions` | **200** |
| pmos-backend service | **active** |

## 21. Что осталось

1. **Real Authentication** — login/logout/session/refresh/password reset или интеграция внешнего Auth Provider.
2. ~~Frontend §43-тесты~~ — **сделано** (11 тестов, `npm test`). Осталось при желании: расширить на DashboardWidgets/Export/Import кнопки.
3. ~~Import security~~ — **сделано**: все import endpoints требуют `project.import`, включая шаблон и историю (§48).
4. **Teams** — API/UI команд и team-based access (§12–13).
5. **Field-level permissions** — применение `field_permissions` (сейчас только жёсткий finance-блок, §14).
6. ~~Ownership transfer~~ — **сделано**: `POST /workspaces/{id}/ownership/transfer`, только OWNER, новый владелец ACTIVE, прежний становится ADMIN; UI в «Команда».
7. **Invitation accept flow** — безопасный accept для уже authenticated user сделан; ссылка → создание/логин и resend ожидают real authentication.
8. **Frontend real-user mode** — убрать demo-admin fallback при наличии сессии (сейчас без `X-User-Id` frontend работает как ADMIN).
9. **Object-level access** — архитектурно подготовить (в модели уже есть задел), для MVP — workspace-wide.
