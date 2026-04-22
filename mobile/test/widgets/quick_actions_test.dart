import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/widgets/quick_actions.dart';

/// Find the main FAB by looking for the one containing the add icon.
Finder _findMainFab() {
  return find.ancestor(
    of: find.byIcon(Icons.add),
    matching: find.byType(FloatingActionButton),
  );
}

/// Find the inbox sub-button (mini FAB with lightbulb icon)
Finder _findInboxButton() {
  return find.ancestor(
    of: find.byIcon(Icons.lightbulb_outline),
    matching: find.byType(FloatingActionButton),
  );
}

/// Find the create-task sub-button (mini FAB with add_task icon)
Finder _findCreateTaskButton() {
  return find.ancestor(
    of: find.byIcon(Icons.add_task),
    matching: find.byType(FloatingActionButton),
  );
}

void main() {
  group('QuickActions', () {
    testWidgets('renders FAB with add icon', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            floatingActionButton: QuickActions(
              onInbox: () {},
              onCreateTask: () {},
            ),
          ),
        ),
      );

      expect(find.byIcon(Icons.add), findsOneWidget);
    });

    testWidgets('tapping FAB shows sub-buttons', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            floatingActionButton: QuickActions(
              onInbox: () {},
              onCreateTask: () {},
            ),
          ),
        ),
      );

      // Initially no sub-buttons visible
      expect(find.text('记灵感'), findsNothing);
      expect(find.text('建任务'), findsNothing);

      // Tap main FAB
      await tester.tap(_findMainFab());
      await tester.pumpAndSettle();

      // Sub-buttons should appear
      expect(find.text('记灵感'), findsOneWidget);
      expect(find.text('建任务'), findsOneWidget);
      expect(find.byIcon(Icons.lightbulb_outline), findsOneWidget);
      expect(find.byIcon(Icons.add_task), findsOneWidget);
    });

    testWidgets('tapping FAB again hides sub-buttons', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            floatingActionButton: QuickActions(
              onInbox: () {},
              onCreateTask: () {},
            ),
          ),
        ),
      );

      // Open
      await tester.tap(_findMainFab());
      await tester.pumpAndSettle();
      expect(find.text('记灵感'), findsOneWidget);

      // Close
      await tester.tap(_findMainFab());
      await tester.pumpAndSettle();
      expect(find.text('记灵感'), findsNothing);
    });

    testWidgets('tapping inbox button calls onInbox', (WidgetTester tester) async {
      var inboxCalled = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            floatingActionButton: QuickActions(
              onInbox: () => inboxCalled = true,
              onCreateTask: () {},
            ),
          ),
        ),
      );

      // Open FAB
      await tester.tap(_findMainFab());
      await tester.pumpAndSettle();

      // Tap inbox mini FAB
      await tester.tap(_findInboxButton());
      await tester.pumpAndSettle();

      expect(inboxCalled, true);
    });

    testWidgets('tapping create task button calls onCreateTask', (WidgetTester tester) async {
      var taskCalled = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            floatingActionButton: QuickActions(
              onInbox: () {},
              onCreateTask: () => taskCalled = true,
            ),
          ),
        ),
      );

      // Open FAB
      await tester.tap(_findMainFab());
      await tester.pumpAndSettle();

      // Tap create-task mini FAB
      await tester.tap(_findCreateTaskButton());
      await tester.pumpAndSettle();

      expect(taskCalled, true);
    });
  });

  group('CreateTaskSheet', () {
    testWidgets('renders title and input field', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () {
                  CreateTaskSheet.show(
                    context,
                    onSubmit: (_) async => true,
                  );
                },
                child: const Text('Show'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Show'));
      await tester.pumpAndSettle();

      expect(find.text('新建任务'), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('创建'), findsOneWidget);
    });

    testWidgets('entering text and tapping create calls onSubmit', (WidgetTester tester) async {
      String? submittedTitle;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () {
                  CreateTaskSheet.show(
                    context,
                    onSubmit: (title) async {
                      submittedTitle = title;
                      return true;
                    },
                  );
                },
                child: const Text('Show'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Show'));
      await tester.pumpAndSettle();

      // Enter title
      await tester.enterText(find.byType(TextField), 'New task title');
      await tester.pump();

      // Tap create
      await tester.tap(find.text('创建'));
      await tester.pumpAndSettle();

      expect(submittedTitle, 'New task title');
    });
  });
}
