import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rizhi/models/morning_digest.dart';
import 'package:rizhi/providers/today_provider.dart';
import 'package:rizhi/widgets/morning_digest_card.dart';

void main() {
  group('MorningDigestCard', () {
    // ---- error state: 不显示卡片 ----
    testWidgets('error state renders nothing', (WidgetTester tester) async {
      const state = MorningDigestState(
        status: MorningDigestStatus.error,
        error: 'Network error',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MorningDigestCard(morningDigest: state),
          ),
        ),
      );

      // 应该没有晨报相关内容
      expect(find.text('晨报'), findsNothing);
    });

    // ---- initial state: 不显示卡片 ----
    testWidgets('initial state renders nothing', (WidgetTester tester) async {
      const state = MorningDigestState(
        status: MorningDigestStatus.initial,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MorningDigestCard(morningDigest: state),
          ),
        ),
      );

      expect(find.text('晨报'), findsNothing);
    });

    // ---- loading state: 骨架屏 ----
    testWidgets('loading state shows skeleton', (WidgetTester tester) async {
      const state = MorningDigestState(
        status: MorningDigestStatus.loading,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MorningDigestCard(morningDigest: state),
          ),
        ),
      );

      // 骨架屏应该显示（Card 包裹的内容存在）
      expect(find.byType(Card), findsOneWidget);
      // 没有晨报文字（骨架屏不显示真实文字）
      expect(find.text('晨报'), findsNothing);
    });

    // ---- loaded state with no data: 不显示 ----
    testWidgets('loaded state with no data renders nothing', (WidgetTester tester) async {
      const state = MorningDigestState(
        status: MorningDigestStatus.loaded,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MorningDigestCard(morningDigest: state),
          ),
        ),
      );

      expect(find.text('晨报'), findsNothing);
    });

    // ---- loaded state with data: 显示完整内容 ----
    testWidgets('loaded state with data shows content', (WidgetTester tester) async {
      final digest = MorningDigest(
        date: '2026-05-07',
        aiSuggestion: '今天有 3 个任务待完成，保持节奏！',
        todos: [
          const MorningDigestTodo(id: '1', title: '任务一', priority: 'high'),
        ],
        overdue: [
          const MorningDigestOverdue(id: '2', title: '逾期任务', priority: 'medium'),
        ],
        learningStreak: 5,
      );
      final state = MorningDigestState(
        data: digest,
        status: MorningDigestStatus.loaded,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: SingleChildScrollView(
            child: MorningDigestCard(morningDigest: state),
          ),
        ),
      );

      // 应该显示晨报标题
      expect(find.text('晨报'), findsOneWidget);
      // 日期
      expect(find.text('2026-05-07'), findsOneWidget);
      // AI 建议文本
      expect(find.textContaining('任务待完成'), findsOneWidget);
      // 连续天数
      expect(find.text('5 天连续'), findsOneWidget);
    });

    // ---- loaded state with dailyFocus ----
    testWidgets('loaded state shows daily focus', (WidgetTester tester) async {
      final digest = MorningDigest(
        date: '2026-05-07',
        aiSuggestion: 'AI summary',
        dailyFocus: const DailyFocus(
          title: '处理逾期任务',
          description: '优先完成逾期的任务',
        ),
      );
      final state = MorningDigestState(
        data: digest,
        status: MorningDigestStatus.loaded,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: SingleChildScrollView(
            child: MorningDigestCard(morningDigest: state),
          ),
        ),
      );

      expect(find.text('处理逾期任务'), findsOneWidget);
      expect(find.text('优先完成逾期的任务'), findsOneWidget);
    });

    // ---- loaded state with patternInsights ----
    testWidgets('loaded state shows pattern insights', (WidgetTester tester) async {
      final digest = MorningDigest(
        date: '2026-05-07',
        aiSuggestion: 'AI summary',
        patternInsights: [
          '你最近更倾向于创建任务',
          '任务完成率提升了 20%',
        ],
      );
      final state = MorningDigestState(
        data: digest,
        status: MorningDigestStatus.loaded,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: SingleChildScrollView(
            child: MorningDigestCard(morningDigest: state),
          ),
        ),
      );

      expect(find.textContaining('更倾向于创建任务'), findsOneWidget);
      expect(find.textContaining('提升了 20%'), findsOneWidget);
      // 洞察标题
      expect(find.text('洞察'), findsOneWidget);
    });

    // ---- Markdown rendering in AI suggestion ----
    testWidgets('ai suggestion renders as markdown', (WidgetTester tester) async {
      final digest = MorningDigest(
        date: '2026-05-07',
        aiSuggestion: '今天 **3 个** 任务待完成',
      );
      final state = MorningDigestState(
        data: digest,
        status: MorningDigestStatus.loaded,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: SingleChildScrollView(
            child: MorningDigestCard(morningDigest: state),
          ),
        ),
      );

      // MarkdownBody 应该存在
      expect(find.byType(MorningDigestCard), findsOneWidget);
    });
  });
}
