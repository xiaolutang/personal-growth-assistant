import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/config/constants.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/widgets/task_card.dart';

void main() {
  group('TaskCard', () {
    testWidgets('renders task title', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: '学习 Flutter',
        category: AppConstants.categoryTask,
        status: AppConstants.statusWaitStart,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(entry: entry),
          ),
        ),
      );

      expect(find.text('学习 Flutter'), findsOneWidget);
    });

    testWidgets('renders todo status with schedule icon',
        (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: 'Todo task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusWaitStart,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(entry: entry),
          ),
        ),
      );

      // statusTodo = 'waitStart', maps to schedule icon
      expect(find.byIcon(Icons.schedule), findsOneWidget);
    });

    testWidgets('renders done status with check icon',
        (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-2',
        title: 'Done task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusComplete,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.check_circle), findsOneWidget);
    });

    testWidgets('renders doing status with pending icon',
        (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-3',
        title: 'Doing task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusDoing,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.pending), findsOneWidget);
    });

    testWidgets('renders wait_start status with schedule icon',
        (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-4',
        title: 'Waiting task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusWaitStart,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.schedule), findsOneWidget);
    });

    testWidgets('renders high priority chip', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: 'High priority task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusWaitStart,
        priority: 'high',
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(entry: entry),
          ),
        ),
      );

      expect(find.text('高'), findsOneWidget);
    });

    testWidgets('renders medium priority chip', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: 'Medium priority task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusWaitStart,
        priority: 'medium',
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(entry: entry),
          ),
        ),
      );

      expect(find.text('中'), findsOneWidget);
    });

    testWidgets('renders low priority chip', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: 'Low priority task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusWaitStart,
        priority: 'low',
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(entry: entry),
          ),
        ),
      );

      expect(find.text('低'), findsOneWidget);
    });

    testWidgets('does not render priority chip when null',
        (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: 'No priority task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusWaitStart,
        priority: null,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(entry: entry),
          ),
        ),
      );

      expect(find.text('高'), findsNothing);
      expect(find.text('中'), findsNothing);
      expect(find.text('低'), findsNothing);
    });

    testWidgets('renders tags when present', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: 'Tagged task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusWaitStart,
        tags: ['flutter', 'test'],
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(entry: entry),
          ),
        ),
      );

      expect(find.text('flutter'), findsOneWidget);
      expect(find.text('test'), findsOneWidget);
    });

    testWidgets('shows line-through for done task title',
        (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-done',
        title: 'Completed',
        category: AppConstants.categoryTask,
        status: AppConstants.statusComplete,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TaskCard(entry: entry),
          ),
        ),
      );

      final titleWidget = tester.widget<Text>(find.text('Completed'));
      expect(titleWidget.style?.decoration, TextDecoration.lineThrough);
    });

    testWidgets('calls onTap when card tapped', (WidgetTester tester) async {
      var tapped = false;
      const entry = Entry(
        id: 'task-1',
        title: 'Tappable',
        category: AppConstants.categoryTask,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TaskCard(
              entry: entry,
              onTap: () => tapped = true,
            ),
          ),
        ),
      );

      await tester.tap(find.text('Tappable'));
      expect(tapped, true);
    });

    testWidgets('cycles status from todo to doing on icon tap',
        (WidgetTester tester) async {
      String? changedStatus;
      const entry = Entry(
        id: 'task-1',
        title: 'Status cycle',
        category: AppConstants.categoryTask,
        status: AppConstants.statusWaitStart,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TaskCard(
              entry: entry,
              onStatusChanged: (status) => changedStatus = status,
            ),
          ),
        ),
      );

      // statusTodo = 'waitStart', shows schedule icon
      await tester.tap(find.byIcon(Icons.schedule));
      expect(changedStatus, AppConstants.statusDoing);
    });

    testWidgets('cycles status from doing to done on icon tap',
        (WidgetTester tester) async {
      String? changedStatus;
      const entry = Entry(
        id: 'task-1',
        title: 'Status cycle',
        category: AppConstants.categoryTask,
        status: AppConstants.statusDoing,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TaskCard(
              entry: entry,
              onStatusChanged: (status) => changedStatus = status,
            ),
          ),
        ),
      );

      await tester.tap(find.byIcon(Icons.pending));
      expect(changedStatus, AppConstants.statusComplete);
    });

    testWidgets('cycles status from done to todo on icon tap',
        (WidgetTester tester) async {
      String? changedStatus;
      const entry = Entry(
        id: 'task-1',
        title: 'Status cycle',
        category: AppConstants.categoryTask,
        status: AppConstants.statusComplete,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TaskCard(
              entry: entry,
              onStatusChanged: (status) => changedStatus = status,
            ),
          ),
        ),
      );

      await tester.tap(find.byIcon(Icons.check_circle));
      expect(changedStatus, AppConstants.statusWaitStart);
    });
  });
}
