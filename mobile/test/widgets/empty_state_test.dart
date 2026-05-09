import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/widgets/empty_state.dart';

void main() {
  group('EmptyStateWidget', () {
    testWidgets('renders icon and title', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyStateWidget(
              icon: Icons.inbox,
              title: '暂无数据',
            ),
          ),
        ),
      );

      expect(find.byIcon(Icons.inbox), findsOneWidget);
      expect(find.text('暂无数据'), findsOneWidget);
    });

    testWidgets('renders subtitle when provided', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyStateWidget(
              icon: Icons.inbox,
              title: '暂无数据',
              subtitle: '点击按钮添加一条',
            ),
          ),
        ),
      );

      expect(find.text('暂无数据'), findsOneWidget);
      expect(find.text('点击按钮添加一条'), findsOneWidget);
    });

    testWidgets('does not render subtitle when null', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyStateWidget(
              icon: Icons.search,
              title: '无结果',
            ),
          ),
        ),
      );

      expect(find.text('无结果'), findsOneWidget);
      // Only 1 Text widget (title), no subtitle
      expect(find.byType(Text), findsOneWidget);
    });

    testWidgets('renders with different icons', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyStateWidget(
              icon: Icons.check_circle_outline,
              title: '暂无任务',
              subtitle: '创建你的第一个任务',
            ),
          ),
        ),
      );

      expect(find.byIcon(Icons.check_circle_outline), findsOneWidget);
      expect(find.text('暂无任务'), findsOneWidget);
      expect(find.text('创建你的第一个任务'), findsOneWidget);
    });

    testWidgets('renders with explore icon', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyStateWidget(
              icon: Icons.explore_outlined,
              title: '暂无条目',
            ),
          ),
        ),
      );

      expect(find.byIcon(Icons.explore_outlined), findsOneWidget);
      expect(find.text('暂无条目'), findsOneWidget);
    });
  });
}
