// test/heartbeat_test.dart
//
// Phase 5.1 B heartbeat smoke tests.
//
// Asserts the structural wiring between Android-side heartbeat executor and
// freebuff-core HTTP endpoint. Three invariants:
//
//   1. assets/manifest.json points at the REAL Freebuff core HTTP (port 8765,
//      GET `/`) — Phase 5.1 A scaffold had wrong values, fixed in v5.60.0.
//   2. FreebuffForegroundService.kt uses Stdlib ONLY (no coroutines / OkHttp
//      / Kotlinx-serializable). Locking pin for Termux ARM64 zero-dep footprint.
//   3. Service lifecycle cleans up resources (executor shutdown + wake_lock
//      release) on onDestroy.
//
// Why this test: ensures future refactor doesn't break the kill-protection
// contract for Phantom Reaper (Android 14/15+). Catches drift between
// canonical manifest and Kotlin source.

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  // ── 1. Manifest target invariant ───────────────────────

  test(
    'heartbeat: assets/manifest.json points at REAL Freebuff HTTP (127.0.0.1:8765 /)',
    () {
      final manifest = File('assets/manifest.json').readAsStringSync();
      expect(
        manifest.contains('"base_url": "http://127.0.0.1:8765"'),
        isTrue,
        reason: 'Freebuff core HTTP base URL must be http://127.0.0.1:8765 '
                '(scripts_01/mcp_fastapi.py default port per its argparser). '
                'Phase 5.1 A scaffold wrongly used 8080; v5.60.0 fixed per CON-23.',
      );
      expect(
        manifest.contains('"health": "/"'),
        isTrue,
        reason: 'Health endpoint must be `/` (root, no auth required). '
                'Phase 5.1 A scaffold wrongly used `/v1/health`; v5.60.0 fixed per CON-23.',
      );
      // breathe-keep some legacy fields for backward compat
      expect(
        manifest.contains('"interval_sec": 30'),
        isTrue,
        reason: '30s heartbeat cadence is the architectural pin.',
      );
    ***REMOVED***,
  );

  // ── 2. Kotlin Stdlib-only invariant ───────────────────

  test(
    'heartbeat: FreebuffForegroundService.kt uses Stdlib scheduler '
    '(no coroutines / OkHttp / Ktor)',
    () {
      final kt = File(
        'android/app/src/main/kotlin/com/freebuff/flutterapp/services/FreebuffForegroundService.kt',
      ).readAsStringSync();
      expect(kt.contains('ScheduledExecutorService'), isTrue,
          reason: 'Stdlib ScheduledExecutorService chosen for zero-dependency footprint.');
      expect(kt.contains('HttpURLConnection'), isTrue,
          reason: 'Stdlib HttpURLConnection (no OkHttp dependency).');
      expect(kt.contains('scheduleWithFixedDelay'), isTrue,
          reason: 'scheduleWithFixedDelay (NOT FixedRate) so retries-with-backoff '
                  'do not pile up future ticks.');

      // Negative invariants — these would be architectural drift
      expect(kt.contains('import kotlinx.coroutines'), isFalse,
          reason: 'No kotlinx-coroutines allowed.');
      expect(kt.contains('import okhttp3'), isFalse,
          reason: 'No OkHttp allowed.');
      expect(kt.contains('import io.ktor'), isFalse,
          reason: 'No Ktor allowed.');
    ***REMOVED***,
  );

  // ── 3. Native PARTIAL_WAKE_LOCK (no MethodChannel) ────

  test(
    'heartbeat: PARTIAL_WAKE_LOCK acquired natively (no Dart MethodChannel)',
    () {
      final kt = File(
        'android/app/src/main/kotlin/com/freebuff/flutterapp/services/FreebuffForegroundService.kt',
      ).readAsStringSync();
      expect(kt.contains('PowerManager.PARTIAL_WAKE_LOCK'), isTrue,
          reason: 'Native PARTIAL_WAKE_LOCK required for Phantom Process Killer fix.');
      expect(kt.contains('newWakeLock'), isTrue);
      expect(kt.contains('flutter/platform'), isFalse,
          reason: 'No MethodChannel bridge needed — wake lock is Android-side only.');

      // Cleanup invariants
      expect(kt.contains('shutdownNow'), isTrue,
          reason: 'Executor MUST shutdown on destroy to release thread resources.');
      expect(kt.contains('wakeLock?.release()'), isTrue,
          reason: 'WakeLock MUST release on destroy.');
    ***REMOVED***,
  );

  // ── 4. Heartbeat cadence & retry semantics ────────────

  test(
    'heartbeat: cadence 30s + 3 quick retries + 5s connect timeout (constexpr pins)',
    () {
      final kt = File(
        'android/app/src/main/kotlin/com/freebuff/flutterapp/services/FreebuffForegroundService.kt',
      ).readAsStringSync();
      expect(kt.contains('HEARTBEAT_INTERVAL_SEC = 30L'), isTrue);
      expect(kt.contains('QUICK_RETRY_COUNT = 3'), isTrue);
      expect(kt.contains('QUICK_RETRY_DELAY_MS = 2_000L'), isTrue);
      expect(kt.contains('HTTP_TIMEOUT_CONNECT_MS = 5_000'), isTrue);
      expect(kt.contains('HTTP_TIMEOUT_READ_MS = 2_000'), isTrue);
      expect(kt.contains('HEALTH_BASE_URL = "http://127.0.0.1:8765"'), isTrue);
      expect(kt.contains('HEALTH_PATH = "/"'), isTrue);
      expect(kt.contains('WAKE_LOCK_TAG = "Freebuff:ForegroundService"'), isTrue);
    ***REMOVED***,
  );

  // ── 5. Notification update semantics ──────────────────

  test('heartbeat: notification updates without sound/heads-up (silent content update)',
      () {
    final kt = File(
      'android/app/src/main/kotlin/com/freebuff/flutterapp/services/FreebuffForegroundService.kt',
    ).readAsStringSync();
    expect(kt.contains('setOnlyAlertOnce(true)'), isTrue,
        reason: 'Prevents heads-up re-fires on every heartbeat tick.');
    expect(kt.contains('NotificationManager.notify'), isTrue,
        reason: 'Updates existing notification (NOT a new one).');
  ***REMOVED***);
***REMOVED***
