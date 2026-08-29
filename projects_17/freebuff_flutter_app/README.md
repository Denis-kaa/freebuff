# freebuff_flutter_app

> **Статус:** Phase 5.1 A — scaffold (Android shell + lifecycle + smoke test structure).
> См. также: [`TASK.md`***REMOVED***(../../TASK.md) §5.1, [`pompts_11/039_12_terminal_ai_studio_mobile.md`***REMOVED***(../../pompts_11/039_12_terminal_ai_studio_mobile.md).

## Что это

Мобильное приложение Freebuff на Flutter (Android). Цель — держать
Freebuff core процесс живым в фоне после сворачивания (Phantom Process Killer
workaround для Android 14/15+).

**Основные механизмы:**

- **Foreground Service** (`FreebuffForegroundService.kt`) с `foregroundServiceType=connectedDevice`
  — единственный надёжный тип, оставшийся после ужесточения политики
  dataSync в Android 15+.
- **Wake Lock** (`wakelock_plus`) — предотвращает doze-mode sleep.
- **Hot-Start budget** (`cold_start_tracker`) — cold-launch должен быть < 3s.

## Структура

```
freebuff_flutter_app/
├── pubspec.yaml                       # SDK / зависимости
├── lib/
│   └── main.dart                      # FreebuffApp entry (skeleton)
├── android/app/src/main/
│   ├── AndroidManifest.xml            # foreground service type
│   └── kotlin/.../FreebuffForegroundService.kt   # stub service
├── test/
│   ├── hot_start_test.dart
│   ├── wake_lock_test.dart
│   ├── protected_process_test.dart
│   └── README.md                      # объясняет как запустить
└── assets/manifest.json               # Freebuff core endpoints
```

## Hot-Start smoke tests (smoke-style, не реальные perf-тесты)

3 автономных теста (запускаются через `flutter test`):

| Тест | Что проверяет |
|------|---------------|
| `hot_start_test.dart` | App boots ≤ 3s, базовый widget жив |
| `wake_lock_test.dart` | `wakelock_plus` API surface компилируется |
| `protected_process_test.dart` | AndroidManifest declares fg-service + permissions |

> ⚠️ **В этой среде (Termux ARM64) Flutter SDK может быть не установлен.**
> Запустите локально: `flutter pub get && flutter test`.

## Сборка

```bash
flutter pub get
flutter build apk --release --target-platform android-arm64
flutter install --use-application-binary=$(pwd)/build/app/outputs/flutter-apk/app-release.apk
```

## Forward path

- **Phase 5.1 B (Foreground Service body):** Real `FreebuffForegroundService` kotlin-impl,
  `/opt/freebuff/start.sh` subprocess под управлением сервиса.
- **Phase 5.1 C (Wake lock + heartbeat):** Real `WakelockPlus.enable()` + periodic
  Gradle `adb shell ping` к Freebuff core.
- **§5.2 Remote Sync:** OAuth client для TG.
