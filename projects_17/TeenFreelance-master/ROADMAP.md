# ROADMAP — TeenFreelance

> Этапы привязаны к REC-ID реестра `docs_10/RECOMMENDATIONS.md` (Single Source of Truth по состоянию фикс-работ). Статусы этапа: ⬜ не начат / 🟡 в работе / ✅ готов.

## Этап 0 — Деплой MVP на whimco — ✅ готов (2026-09-04)

- [x] Нативный деплой: systemd :8020 + nginx :8021 (ADR-001)
- [x] БД `teenfreelance`, миграции, `fix_enum_cases.py` (CON-01)
- [x] E2E-верификация: регистрация → логин → WS
- [x] Security-аудит: 36 находок, §11 owner-check sweep (сессия 2026-09-04…05)
- [x] Каркас проекта-контейнера (MANIFEST/STEPS/LESSONS/decisions)

## Этап 1 — P0-карантин безопасности — ⬜ не начат (7 задач)

> ADR-002 Волна 1. Блокирует дальнейшую эксплуатацию живого инстанса.

- [ ] REC-001/018: обязательный `SECRET_KEY` + ops-фикс `.env` на whimco (P0)
- [ ] REC-002: TLS + security-заголовки nginx (P0; нужен домен)
- [ ] REC-003/019: auth+ownership на чтение offers; draft-фильтр листинга заказов (P0)
- [ ] REC-004: ownership на `delete_file`, убрать `file_path` из ответа upload (P0)
- [ ] REC-006: убрать публикацию Postgres из docker-compose (P0)

## Этап 2 — P1-закрепление — ⬜ не начат (14 задач; ревизия 2026-09-05)

> ADR-002 Волна 2. Сессии/токены, деньги, PII подростков, модерация, WS, файлы.

- [ ] REC-007: token_version + logout + короткий access-токен
- [ ] REC-008: rate-limit /login /register
- [ ] REC-009: payment-flow integrity
- [ ] REC-010: PII-lifecycle (age required, delete/export, consent)
- [ ] REC-011: first-name+initial в публичных поверхностях
- [ ] REC-012: модерация + контент-фильтры (пересмотр 2026-09-05 P2→P1: grooming-вектор)
- [ ] REC-013: WS-гигиена + ws-ticket вместо query-токена
- [ ] REC-014: create_message-валидация участников
- [ ] REC-015: мелкие auth-фиксы пачкой
- [ ] REC-016: compose-гигиена
- [ ] REC-020: mark_as_read IDOR
- [ ] REC-021: auth на portfolio GET
- [ ] REC-022: rate-limit сообщений WS/REST (antiflood)
- [ ] REC-005: стриминговая загрузка файлов

## Этап 3 — P2-доводка — ⬜ не начат (2 задачи)

- [ ] REC-017: magic-bytes + signed URLs для файлов
- [ ] REC-023: ConnectionManager redesign (Redis pub/sub / шардирование)

## Этап 4 — Продуктовое развитие — ⬜ не спланировано

- Автоматизация деплоя (сейчас — ручные шаги STEPS.md)
- Балансовые операции RUB/tf_coins: аудит целостности не покрывал платёжные интеграции (вне скоупа аудита 2026-09-04) — отдельный аудит перед вводом реальных платежей
