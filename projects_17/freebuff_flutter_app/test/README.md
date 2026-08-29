# Freebuff Flutter — Test Surface (Phase 5.1 A + B)

4 smoke-теста, Phase 5.1 A scaffold + Phase 5.1 B heartbeat executor.

## Что такое "smoke-тест" в этом контексте

Smoke-test — структурный тест на готовность (compile-time correctness +
manifest invariants + Kotlin source invariants), а НЕ реальный performance /
hardware тест. Можно запустить в `flutter test` ИЛИ просто grep-аудит.

| Файл | Что проверяет | Запускается |
|------|---------------|-------------|
| `hot_start_test.dart` | App boots, MaterialApp scaffold, ≤ 3s budget | `flutter test` |
| `wake_lock_test.dart` | `wakelock_plus` API surface компилируется | `flutter test` |
| `protected_process_test.dart` | AndroidManifest.xml invariants (5 проверок) | `flutter test` |
| `heartbeat_test.dart` | Phase 5.1 B heartbeat executor + manifest.json wire-up (5 проверок) | `flutter test` |

## heartheat_test.dart — что покрывает (Phase 5.1 B)

1. **manifest.json target invariant** — base_url = `http://127.0.0.1:8765`, health = `/`. Защищает от phantom Phase 5.1 A scaffold guess (8080 + /v1/health).
2. **Kotlin Stdlib-only invariant** — `ScheduledExecutorService` + `HttpURLConnection`. Negative test: запрет kotlinx-coroutines / okhttp3 / io.ktor.
3. **Native PARTIAL_WAKE_LOCK** — PowerManager без MethodChannel bridge. Cleanup invariant: executor.shutdownNow() + wakeLock?.release().
4. **Constexpr Pins** — heartbeat interval 30s, 3 retries × 2s, 5s connect timeout, "Freebuff:ForegroundService" tag.
5. **Notification semantics** — silent content update через `setOnlyAlertOnce(true)` + `NotificationManager.notify` (а не heads-up re-fire).

## Запуск (нужен Flutter SDK на хост-машине)

```bash
flutter pub get
flutter test
```

> Если в Termux установлен Flutter SDK (см. `pompts_11/007_04_lightpanda_integration.md`
> часть 6 — "Flutter + Termux"), тесты можно запустить здесь. На данный
> момент Flutter SDK может отсутствовать → структура + assertions присутствуют,
> реальный прогон отложен на фазу C (добавить `flutter create . --platforms=android`
> + `flutter test` integration в CI).

## Что НЕ проверено (вынесено в Phase 5.2/5.3 follow-ups)

| Gap | Phase follow-up |
|-----|-----------------|
| Реальный wakelock_plus device test | `WakelockPlus.toggle()` test с mocked MethodChannel |
| Реальный foreground-service notification appearance | Integration test: foregroundService.startForeground → verify notification rendered |
| Реальный cold-start benchmark | `cold_start_tracker` integration с trace-points |
| Phantom Reaper resilience | Manual device test: виджет активный, процесс держится > 60 минут |
| Реальный HTTP heartbeat loop | device test: mcp_fastapi.py on Termux запущен, Flutter-сервис держит kill-protection |
| Notification update visually | device test: foreground-service notification показывает `Last ping 14:32:05 • healthy` каждый цикл |
