import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/widgets/progress_ring.dart';

void main() {
  group('ProgressRing', () {
    testWidgets('renders percentage text', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProgressRing(progress: 0.75),
          ),
        ),
      );

      expect(find.text('75'), findsOneWidget);
      expect(find.text('%'), findsOneWidget);
    });

    testWidgets('renders 0% for zero progress', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProgressRing(progress: 0.0),
          ),
        ),
      );

      expect(find.text('0'), findsOneWidget);
    });

    testWidgets('renders 100% for full progress', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProgressRing(progress: 1.0),
          ),
        ),
      );

      expect(find.text('100'), findsOneWidget);
    });

    testWidgets('clamps progress above 1.0', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProgressRing(progress: 1.5),
          ),
        ),
      );

      expect(find.text('100'), findsOneWidget);
    });

    testWidgets('clamps progress below 0.0', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProgressRing(progress: -0.5),
          ),
        ),
      );

      expect(find.text('0'), findsOneWidget);
    });

    testWidgets('uses CustomPaint for ring drawing', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProgressRing(progress: 0.5),
          ),
        ),
      );

      expect(find.byType(CustomPaint), findsWidgets);
    });
  });
}
