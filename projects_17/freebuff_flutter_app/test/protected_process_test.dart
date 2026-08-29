// test/protected_process_test.dart
//
// Protected-process smoke test (Phase 5.1 A).
//
// Validates AndroidManifest.xml invariants needed to keep the Freebuff
// core process alive across Android Phantom Reaper process kill.
//
// Required invariants (Phantom Process Killer workaround per promt39 §8):
//   - foregroundServiceType="connectedDevice" (NOT dataSync — deprecated)
//   - FOREGROUND_SERVICE permission
//   - FOREGROUND_SERVICE_CONNECTED_DEVICE permission (Android 14+)
//   - WAKE_LOCK permission
//   - POST_NOTIFICATIONS permission (Android 13+ runtime)
//   - FreebuffForegroundService class reference
//
// NOTE: implementation via dart:io File.readAsStringSync — fast,
// no Android SDK required. Mimics what `apkanalyzer` would catch,
// but doesn't require device or build tools.

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  const manifestPath = 'android/app/src/main/AndroidManifest.xml';

  late String manifest;

  setUpAll(() {
    manifest = File(manifestPath).readAsStringSync();
  ***REMOVED***);

  test('protected-process: foregroundServiceType is connectedDevice (Phantom Reaper fix)', () {
    expect(
      manifest.contains('android:foregroundServiceType="connectedDevice"'),
      isTrue,
      reason: 'AndroidManifest.xml MUST declare foregroundServiceType="connectedDevice" '
              'to survive Phantom Process Killer on Android 14/15+ '
              '(dataSync is deprecated; only connectedDevice fits Termux-style '
              'long-bridge use case).',
    );
  ***REMOVED***);

  test('protected-process: critical foreground-service permissions declared', () {
    expect(
      manifest.contains('android.permission.FOREGROUND_SERVICE'),
      isTrue,
      reason: 'Missing FOREGROUND_SERVICE permission',
    );
    expect(
      manifest.contains('android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE'),
      isTrue,
      reason: 'Missing FOREGROUND_SERVICE_CONNECTED_DEVICE permission (Android 14+)',
    );
    expect(
      manifest.contains('android.permission.WAKE_LOCK'),
      isTrue,
      reason: 'Missing WAKE_LOCK permission',
    );
    expect(
      manifest.contains('android.permission.POST_NOTIFICATIONS'),
      isTrue,
      reason: 'Missing POST_NOTIFICATIONS permission (Android 13+)',
    );
  ***REMOVED***);

  test('protected-process: service class declaration present', () {
    expect(
      manifest.contains('.services.FreebuffForegroundService'),
      isTrue,
      reason: 'FreebuffForegroundService class reference missing from AndroidManifest.xml',
    );
  ***REMOVED***);

  test('protected-process: tools:targetApi="34" namespace present on foreground service', () {
    // Allow either: on the `<service>` directly OR on any inner element.
    final hasTargetApiAnnotation = manifest.contains('tools:targetApi="34"');
    expect(
      hasTargetApiAnnotation,
      isTrue,
      reason: 'Missing tools:targetApi="34" annotation (required for API 34+ fg-service types '
              'when minSdk is < 34 — otherwise lint/manifest-merger fails).',
    );
  ***REMOVED***);
***REMOVED***
