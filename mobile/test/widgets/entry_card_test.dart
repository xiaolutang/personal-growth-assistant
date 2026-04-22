import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/config/constants.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/widgets/entry_card.dart';

void main() {
  group('EntryCard', () {
    testWidgets('renders task title', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: '学习 Flutter',
        category: AppConstants.categoryTask,
        status: AppConstants.statusTodo,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCard(entry: entry),
          ),
        ),
      );

      expect(find.text('学习 Flutter'), findsOneWidget);
    });

    testWidgets('renders todo status with radio icon', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: 'Todo task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusTodo,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.radio_button_unchecked), findsOneWidget);
    });

    testWidgets('renders done status with check icon', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-2',
        title: 'Done task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusDone,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.check_circle), findsOneWidget);
    });

    testWidgets('renders doing status with pending icon', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-3',
        title: 'Doing task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusDoing,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.pending), findsOneWidget);
    });

    testWidgets('renders wait_start status with schedule icon', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-4',
        title: 'Waiting task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusWaitStart,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.schedule), findsOneWidget);
    });

    testWidgets('renders note category with note icon', (WidgetTester tester) async {
      const entry = Entry(
        id: 'note-1',
        title: 'My note',
        category: AppConstants.categoryNote,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.note_outlined), findsOneWidget);
      expect(find.text('笔记'), findsOneWidget);
    });

    testWidgets('renders inbox category with lightbulb icon', (WidgetTester tester) async {
      const entry = Entry(
        id: 'inbox-1',
        title: 'An idea',
        category: AppConstants.categoryInbox,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.lightbulb_outline), findsOneWidget);
      expect(find.text('灵感'), findsOneWidget);
    });

    testWidgets('renders tags when present', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: 'Tagged task',
        category: AppConstants.categoryTask,
        status: AppConstants.statusTodo,
        tags: ['flutter', 'test'],
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCard(entry: entry),
          ),
        ),
      );

      expect(find.text('flutter'), findsOneWidget);
      expect(find.text('test'), findsOneWidget);
    });

    testWidgets('shows line-through for done task title', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-done',
        title: 'Completed',
        category: AppConstants.categoryTask,
        status: AppConstants.statusDone,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCard(entry: entry),
          ),
        ),
      );

      final titleWidget = tester.widget<Text>(find.text('Completed'));
      expect(titleWidget.style?.decoration, TextDecoration.lineThrough);
    });

    testWidgets('calls onTap when tapped', (WidgetTester tester) async {
      var tapped = false;
      const entry = Entry(
        id: 'task-1',
        title: 'Tappable',
        category: AppConstants.categoryTask,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EntryCard(
              entry: entry,
              onTap: () => tapped = true,
            ),
          ),
        ),
      );

      await tester.tap(find.text('Tappable'));
      expect(tapped, true);
    });
  });
}
