import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/config/constants.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/widgets/entry_created_card.dart';

void main() {
  group('EntryCreatedCard', () {
    testWidgets('renders inbox entry title and category label',
        (WidgetTester tester) async {
      const entry = Entry(
        id: 'inbox-abc123',
        title: '学习 Flutter 动画',
        category: AppConstants.categoryInbox,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCreatedCard(entry: entry),
          ),
        ),
      );

      expect(find.text('学习 Flutter 动画'), findsOneWidget);
      expect(find.text('灵感'), findsOneWidget);
    });

    testWidgets('renders task category label', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: '完成项目报告',
        category: AppConstants.categoryTask,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCreatedCard(entry: entry),
          ),
        ),
      );

      expect(find.text('完成项目报告'), findsOneWidget);
      expect(find.text('任务'), findsOneWidget);
    });

    testWidgets('renders note category label', (WidgetTester tester) async {
      const entry = Entry(
        id: 'note-1',
        title: '学习心得',
        category: AppConstants.categoryNote,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCreatedCard(entry: entry),
          ),
        ),
      );

      expect(find.text('学习心得'), findsOneWidget);
      expect(find.text('笔记'), findsOneWidget);
    });

    testWidgets('renders project category label', (WidgetTester tester) async {
      const entry = Entry(
        id: 'project-1',
        title: '个人网站重构',
        category: AppConstants.categoryProject,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCreatedCard(entry: entry),
          ),
        ),
      );

      expect(find.text('个人网站重构'), findsOneWidget);
      expect(find.text('项目'), findsOneWidget);
    });

    testWidgets('shows category icon for inbox', (WidgetTester tester) async {
      const entry = Entry(
        id: 'inbox-1',
        title: 'Idea',
        category: AppConstants.categoryInbox,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCreatedCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.lightbulb_outline), findsOneWidget);
    });

    testWidgets('shows category icon for task', (WidgetTester tester) async {
      const entry = Entry(
        id: 'task-1',
        title: 'Task',
        category: AppConstants.categoryTask,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCreatedCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.check_circle_outline), findsOneWidget);
    });

    testWidgets('shows arrow icon for navigation hint',
        (WidgetTester tester) async {
      const entry = Entry(
        id: 'inbox-1',
        title: 'Test',
        category: AppConstants.categoryInbox,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCreatedCard(entry: entry),
          ),
        ),
      );

      expect(find.byIcon(Icons.arrow_forward_ios), findsOneWidget);
    });

    testWidgets('card is left aligned', (WidgetTester tester) async {
      const entry = Entry(
        id: 'inbox-1',
        title: 'Test',
        category: AppConstants.categoryInbox,
      );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntryCreatedCard(entry: entry),
          ),
        ),
      );

      final align = tester.widget<Align>(find.byType(Align).first);
      expect(align.alignment, Alignment.centerLeft);
    });
  });
}
