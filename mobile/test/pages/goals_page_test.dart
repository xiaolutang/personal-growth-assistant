import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/pages/goals_page.dart';
import 'package:growth_assistant/providers/goals_provider.dart';

// Fake GoalsNotifier，直接返回预设状态
class _FakeGoalsNotifier extends GoalsNotifier {
  final List<Goal> _goals;
  final bool _isLoading;
  final String? _error;
  final Goal? _selectedGoal;
  final List<Milestone> _milestones;

  _FakeGoalsNotifier({
    List<Goal> goals = const [],
    bool isLoading = false,
    String? error,
    Goal? selectedGoal,
    List<Milestone> milestones = const [],
  })  : _goals = goals,
        _isLoading = isLoading,
        _error = error,
        _selectedGoal = selectedGoal,
        _milestones = milestones;

  @override
  GoalsState build() {
    return GoalsState(
      goals: _goals,
      isLoading: _isLoading,
      error: _error,
      selectedGoal: _selectedGoal,
      milestones: _milestones,
    );
  }

  @override
  Future<void> fetchGoals({String? status}) async {}

  @override
  Future<void> fetchGoalDetail(String id) async {}

  @override
  Future<void> fetchMilestones(String goalId) async {}

  @override
  void deselectGoal() {}
}

// 辅助：注入 provider override 后渲染
Future<void> _pumpGoalsPage(
  WidgetTester tester, {
  List<Goal> goals = const [],
  bool isLoading = false,
  String? error,
  Goal? selectedGoal,
  List<Milestone> milestones = const [],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        goalsProvider.overrideWith(
          () => _FakeGoalsNotifier(
            goals: goals,
            isLoading: isLoading,
            error: error,
            selectedGoal: selectedGoal,
            milestones: milestones,
          ),
        ),
      ],
      child: const MaterialApp(
        home: GoalsPage(),
      ),
    ),
  );
  // 等待 initState 的 addPostFrameCallback 触发
  await tester.pump();
}

Goal _makeGoal({
  required String id,
  String title = 'Test Goal',
  double? progress,
  String? endDate,
}) {
  return Goal(
    id: id,
    title: title,
    progress: progress,
    endDate: endDate,
  );
}

Milestone _makeMilestone({
  required String id,
  required String goalId,
  String title = 'Milestone',
  String? status,
  String? dueDate,
}) {
  return Milestone(
    id: id,
    goalId: goalId,
    title: title,
    status: status,
    dueDate: dueDate,
  );
}

void main() {
  group('GoalsPage', () {
    testWidgets('空列表显示空状态引导文案', (WidgetTester tester) async {
      await _pumpGoalsPage(tester, goals: []);

      expect(find.text('暂无目标'), findsOneWidget);
      expect(
        find.text('设定目标并拆解为里程碑，追踪你的成长进度'),
        findsOneWidget,
      );
    });

    testWidgets('错误状态显示错误信息和重试按钮', (WidgetTester tester) async {
      await _pumpGoalsPage(
        tester,
        goals: [],
        error: '网络连接失败',
      );

      expect(find.text('网络连接失败'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    testWidgets('加载中显示进度指示器', (WidgetTester tester) async {
      await _pumpGoalsPage(tester, goals: [], isLoading: true);

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('目标列表渲染标题和进度条', (WidgetTester tester) async {
      final goals = [
        _makeGoal(id: '1', title: '学习 Flutter', progress: 50.0),
        _makeGoal(id: '2', title: '健身计划', progress: 80.0),
      ];

      await _pumpGoalsPage(tester, goals: goals);

      expect(find.text('学习 Flutter'), findsOneWidget);
      expect(find.text('健身计划'), findsOneWidget);
      // 验证进度条存在
      expect(find.byType(LinearProgressIndicator), findsNWidgets(2));
      // 验证进度百分比文案
      expect(find.text('50% 完成'), findsOneWidget);
      expect(find.text('80% 完成'), findsOneWidget);
    });

    testWidgets('目标显示截止日期', (WidgetTester tester) async {
      final goals = [
        _makeGoal(id: '1', title: 'Goal 1', endDate: '2026-06-30'),
      ];

      await _pumpGoalsPage(tester, goals: goals);

      expect(find.text('6月30日'), findsOneWidget);
    });

    testWidgets('点击目标展开里程碑区域', (WidgetTester tester) async {
      final goal = _makeGoal(id: 'g1', title: 'Expandable Goal');
      final milestones = [
        _makeMilestone(
          id: 'm1',
          goalId: 'g1',
          title: 'First milestone',
        ),
      ];

      await _pumpGoalsPage(
        tester,
        goals: [goal],
        selectedGoal: goal,
        milestones: milestones,
      );

      // 里程碑标题可见
      expect(find.text('First milestone'), findsOneWidget);
      // 添加里程碑按钮可见
      expect(find.text('添加里程碑'), findsOneWidget);
    });

    testWidgets('展开目标但无里程碑显示暂无里程碑', (WidgetTester tester) async {
      final goal = _makeGoal(id: 'g1', title: 'Empty Milestones Goal');

      await _pumpGoalsPage(
        tester,
        goals: [goal],
        selectedGoal: goal,
        milestones: [],
      );

      expect(find.text('暂无里程碑'), findsOneWidget);
    });

    testWidgets('AppBar 标题为"目标"', (WidgetTester tester) async {
      await _pumpGoalsPage(tester, goals: []);

      expect(find.text('目标'), findsOneWidget);
    });
  });
}
