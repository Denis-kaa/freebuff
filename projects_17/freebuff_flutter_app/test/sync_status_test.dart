// test/sync_status_test.dart
//
// Phase 5.4 sync-status UI indicator smoke tests.
//
// Structural-assertion style (same discipline as heartbeat_test.dart):
// the Flutter CLI is not present on the Termux build host, so these tests
// pin the wiring contract by asserting source contents + manifest values.
//
// Invariants:
//   1. assets/manifest.json declares `sync_status: /sync/status` endpoint
//      (the FastAPI surface added in v5.69.0) + remote_sync.indicator config.
//   2. lib/sync_status.dart defines the closed-vocab enum (idle/connected/
//      conflict/quarantine) mirroring core_02/remote_sync._SYNC_STATUS_VALUES.
//   3. lib/sync_status_indicator.dart renders the pill widget + polls on a
//      Timer, and main.dart wires the indicator into the placeholder screen.
//   4. The indicator collapses unknown wire tokens to idle (CON-8) and maps
//      network failure to an offline state (CAN-14).

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  // ── 1. Manifest sync-status endpoint invariant ───────────

  test(
    'sync-status: assets/manifest.json declares /sync/status + indicator config',
    () {
      final manifest = File('assets/manifest.json').readAsStringSync();
      expect(
        manifest.contains('"sync_status": "/sync/status"'),
        isTrue,
        reason: 'Manifest must expose the /sync/status endpoint '
                '(added in v5.69.0, scripts_01/mcp_fastapi.py).',
      );
      expect(
        manifest.contains('"poll_interval_sec": 5'),
        isTrue,
        reason: 'Indicator poll cadence pinned to 5s.',
      );
      expect(
        manifest.contains('"status_tokens": ["idle", "connected", "conflict", "quarantine"***REMOVED***'),
        isTrue,
        reason: 'Closed-vocab status tokens must match '
                'core_02/remote_sync._SYNC_STATUS_VALUES.',
      );
    ***REMOVED***,
  );

  // ── 2. Closed-vocab enum invariant ──────────────────────

  test(
    'sync-status: lib/sync_status.dart defines closed-vocab enum + HTTP client',
    () {
      final src = File('lib/sync_status.dart').readAsStringSync();
      expect(src.contains('enum SyncStatus {'), isTrue);
      expect(src.contains('idle,'), isTrue);
      expect(src.contains('connected,'), isTrue);
      expect(src.contains('conflict,'), isTrue);
      expect(src.contains('quarantine,'), isTrue);
      expect(src.contains('SyncStatus.fromWire'), isTrue,
          reason: 'Wire parsing required (unknown → idle per CON-8).');
      expect(src.contains('SyncStatusClient'), isTrue);
      expect(src.contains('http://127.0.0.1:8765'), isTrue,
          reason: 'Default base URL must match the manifest '
                  '(heartbeat_test.dart CON-23 pin).');
      expect(src.contains('HttpClient'), isTrue,
          reason: 'Stdlib dart:io HttpClient — no extra dependency.');
    ***REMOVED***,
  );

  // ── 3. Indicator widget + main.dart wiring invariant ────

  test(
    'sync-status: indicator widget exists and is wired into main.dart',
    () {
      final indicator = File('lib/sync_status_indicator.dart').readAsStringSync();
      expect(indicator.contains('class SyncStatusIndicator extends StatefulWidget'), isTrue);
      expect(indicator.contains('Timer.periodic'), isTrue,
          reason: 'Polling via Timer.periodic (pollInterval).');
      expect(indicator.contains('SyncStatusSnapshot'), isTrue);
      expect(indicator.contains('Sync offline'), isTrue,
          reason: 'Network-failure state (CAN-14 fail-loud).');

      final main = File('lib/main.dart').readAsStringSync();
      expect(main.contains("import 'sync_status_indicator.dart';"), isTrue);
      expect(main.contains('const SyncStatusIndicator()'), isTrue,
          reason: 'Indicator wired into the placeholder screen.');
    ***REMOVED***,
  );
***REMOVED***
