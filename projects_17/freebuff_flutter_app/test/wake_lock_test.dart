// test/wake_lock_test.dart
//
// Wake-lock smoke test (Phase 5.1 A).
//
// The real flutter wakelock_plus requires platform binding (MethodChannel)
// and real device hardware. In this scaffold we only assert that the
// dependency surface compiles and exposes the expected API.
//
// When the Android service handshake is implemented (Phase 5.1 B), add:
//   - test('wakelock_plus.enable() flips Android WakeLock state', ...)
//   - test('wakelock_plus.disable() releases wake lock', ...)

import 'package:flutter_test/flutter_test.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

void main() {
  test('wake-lock: wakelock_plus package surface compiles', () {
    expect(WakelockPlus, isNotNull);
    expect(WakelockPlus.enable, isNotNull);
    expect(WakelockPlus.disable, isNotNull);
  ***REMOVED***);

  test('wake-lock: current wakelock state is queryable', () {
    expect(WakelockPlus.enabled, isNotNull);
  ***REMOVED***);
***REMOVED***
