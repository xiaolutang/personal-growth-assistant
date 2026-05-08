import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/config/constants.dart';
import 'package:growth_assistant/widgets/entry_shared.dart';

/// Helper to pump EntrySharedWidgets.buildStatusIcon in a testable way
Future<void> _pumpStatusIcon(WidgetTester tester, String? status) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Builder(
          builder: (context) {
            return EntrySharedWidgets.buildStatusIcon(context, status);
          },
        ),
      ),
    ),
  );
}

void main() {
  group('EntrySharedWidgets', () {
    group('buildStatusIcon', () {
      testWidgets('renders check_circle for complete status',
          (WidgetTester tester) async {
        await _pumpStatusIcon(tester, AppConstants.statusComplete);
        expect(find.byIcon(Icons.check_circle), findsOneWidget);
      });

      testWidgets('renders pending for doing status',
          (WidgetTester tester) async {
        await _pumpStatusIcon(tester, AppConstants.statusDoing);
        expect(find.byIcon(Icons.pending), findsOneWidget);
      });

      testWidgets('renders schedule for waitStart status',
          (WidgetTester tester) async {
        await _pumpStatusIcon(tester, AppConstants.statusWaitStart);
        expect(find.byIcon(Icons.schedule), findsOneWidget);
      });

      testWidgets('renders radio_button_unchecked for unknown status',
          (WidgetTester tester) async {
        await _pumpStatusIcon(tester, 'unknown');
        expect(find.byIcon(Icons.radio_button_unchecked), findsOneWidget);
      });

      testWidgets('renders radio_button_unchecked for null status',
          (WidgetTester tester) async {
        await _pumpStatusIcon(tester, null);
        expect(find.byIcon(Icons.radio_button_unchecked), findsOneWidget);
      });
    });

    group('buildTagRow', () {
      testWidgets('renders tags', (WidgetTester tester) async {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: EntrySharedWidgets.buildTagRow(['flutter', 'dart']),
            ),
          ),
        );

        expect(find.text('flutter'), findsOneWidget);
        expect(find.text('dart'), findsOneWidget);
      });

      testWidgets('renders at most 3 tags', (WidgetTester tester) async {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: EntrySharedWidgets.buildTagRow(
                ['tag1', 'tag2', 'tag3', 'tag4'],
              ),
            ),
          ),
        );

        expect(find.text('tag1'), findsOneWidget);
        expect(find.text('tag2'), findsOneWidget);
        expect(find.text('tag3'), findsOneWidget);
        expect(find.text('tag4'), findsNothing);
      });

      testWidgets('renders empty list without errors',
          (WidgetTester tester) async {
        await tester.pumpWidget(
          const MaterialApp(
            home: Scaffold(
              body: SizedBox(),
            ),
          ),
        );

        // buildTagRow with empty list should not throw
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: EntrySharedWidgets.buildTagRow([]),
            ),
          ),
        );

        expect(find.byType(Wrap), findsOneWidget);
      });
    });
  });
}
