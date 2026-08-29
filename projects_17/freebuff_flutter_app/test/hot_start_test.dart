// test/hot_start_test.dart
//
// Hot-start smoke test (Phase 5.1 A).
//
// Assertions:
//   - App boots and reveals a Scaffold containing Freebuff Mobile title.
//   - Cold-start elapsed < 3s budget.
//
// NOTE: This is a `flutter_test`, not a real perf benchmark. Real perf
// testing deferred to Phase 5.1 B with `cold_start_tracker` integration.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:freebuff_flutter_app/main.dart';

void main() {
  testWidgets(
    'hot-start: FreebuffApp boots within 3s budget',
    (WidgetTester tester) async {
      final start = DateTime.now();
      await tester.pumpWidget(const FreebuffApp());
      // Allow one frame so MaterialApp presents.
      await tester.pump();
      final elapsed = DateTime.now().difference(start);

      expect(
        elapsed.inMilliseconds,
        lessThan(3000),
        reason: 'Cold-start exceeded 3s budget (was ${elapsed.inMilliseconds***REMOVED***ms)',
      );
      expect(find.text('Freebuff Mobile'), findsOneWidget);
      expect(find.byType(Scaffold), findsWidgets);
    ***REMOVED***,
  );
***REMOVED***
