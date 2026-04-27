import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/pages/review_page.dart';
import 'package:growth_assistant/providers/review_provider.dart';

// Fake ReviewNotifier，直接返回预设状态
class _FakeReviewNotifier extends ReviewNotifier {
  final Map<String, dynamic>? _summary;
  final Map<String, dynamic>? _trends;
  final Map<String, dynamic>? _insights;
  final bool _isLoading;
  final String? _error;
  final String _selectedPeriod;

  _FakeReviewNotifier({
    Map<String, dynamic>? summary,
    Map<String, dynamic>? trends,
    Map<String, dynamic>? insights,
    bool isLoading = false,
    String? error,
    String selectedPeriod = 'weekly',
  })  : _summary = summary,
        _trends = trends,
        _insights = insights,
        _isLoading = isLoading,
        _error = error,
        _selectedPeriod = selectedPeriod;

  @override
  ReviewState build() {
    return ReviewState(
      summary: _summary,
      trends: _trends,
      insights: _insights,
      isLoading: _isLoading,
      error: _error,
      selectedPeriod: _selectedPeriod,
    );
  }

  @override
  Future<void> loadAll([String? period]) async {}
}

// 辅助：注入 provider override 后渲染
Future<void> _pumpReviewPage(
  WidgetTester tester, {
  Map<String, dynamic>? summary,
  Map<String, dynamic>? trends,
  Map<String, dynamic>? insights,
  bool isLoading = false,
  String? error,
  String selectedPeriod = 'weekly',
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        reviewProvider.overrideWith(
          () => _FakeReviewNotifier(
            summary: summary,
            trends: trends,
            insights: insights,
            isLoading: isLoading,
            error: error,
            selectedPeriod: selectedPeriod,
          ),
        ),
      ],
      child: const MaterialApp(
        home: ReviewPage(),
      ),
    ),
  );
  await tester.pump();
}

void main() {
  group('ReviewPage', () {
    testWidgets('加载中显示进度指示器', (WidgetTester tester) async {
      await _pumpReviewPage(tester, isLoading: true);

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('错误状态显示错误信息和重试按钮', (WidgetTester tester) async {
      await _pumpReviewPage(
        tester,
        error: '加载失败',
      );

      expect(find.text('加载失败'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    testWidgets('显示周期切换按钮 本周/本月', (WidgetTester tester) async {
      await _pumpReviewPage(tester);

      expect(find.text('本周'), findsOneWidget);
      expect(find.text('本月'), findsOneWidget);
    });

    testWidgets('显示概览小节标题', (WidgetTester tester) async {
      await _pumpReviewPage(tester);

      expect(find.text('概览'), findsOneWidget);
    });

    testWidgets('无概览数据显示暂无概览数据提示', (WidgetTester tester) async {
      await _pumpReviewPage(tester);

      expect(find.text('暂无概览数据'), findsOneWidget);
    });

    testWidgets('显示概览数据卡片', (WidgetTester tester) async {
      await _pumpReviewPage(
        tester,
        summary: {
          'task_stats': {
            'total': 10,
            'completed': 6,
            'completion_rate': 60.0,
          },
          'note_stats': {
            'total': 3,
          },
        },
      );

      expect(find.text('总条目'), findsOneWidget);
      expect(find.text('13'), findsOneWidget); // 10 tasks + 3 notes
      expect(find.text('完成率'), findsOneWidget);
      expect(find.text('60%'), findsOneWidget);
      expect(find.text('已完成'), findsOneWidget);
      expect(find.text('6'), findsOneWidget);
    });

    testWidgets('显示活动趋势小节标题', (WidgetTester tester) async {
      await _pumpReviewPage(tester);

      expect(find.text('活动趋势'), findsOneWidget);
    });

    testWidgets('AppBar 标题为"回顾"', (WidgetTester tester) async {
      await _pumpReviewPage(tester);

      expect(find.text('回顾'), findsOneWidget);
    });

    testWidgets('SegmentedButton 渲染正确', (WidgetTester tester) async {
      await _pumpReviewPage(tester);

      expect(find.byType(SegmentedButton<String>), findsOneWidget);
    });
  });
}
