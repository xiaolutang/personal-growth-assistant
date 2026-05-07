import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/pages/goal_detail_page.dart';
import 'package:growth_assistant/providers/goals_provider.dart';
import 'package:growth_assistant/widgets/progress_ring.dart';

// Fake GoalsNotifier for testing
class _FakeGoalsNotifier extends GoalsNotifier {
  final List<Goal> _goals;
  final bool _isLoading;
  final String? _error;
  final Goal? _selectedGoal;
  final List<Milestone> _milestones;
  final List<Entry> _linkedEntries;

  _FakeGoalsNotifier({
    List<Goal> goals = const [],
    bool isLoading = false,
    String? error,
    Goal? selectedGoal,
    List<Milestone> milestones = const [],
    List<Entry> linkedEntries = const [],
  })  : _goals = goals,
        _isLoading = isLoading,
        _error = error,
        _selectedGoal = selectedGoal,
        _milestones = milestones,
        _linkedEntries = linkedEntries;

  @override
  GoalsState build() {
    return GoalsState(
      goals: _goals,
      isLoading: _isLoading,
      error: _error,
      selectedGoal: _selectedGoal,
      milestones: _milestones,
      linkedEntries: _linkedEntries,
    );
  }

  @override
  Future<void> fetchGoals({String? status}) async {}

  @override
  Future<void> fetchGoalDetail(String id) async {}

  @override
  Future<void> fetchMilestones(String goalId) async {}

  @override
  Future<void> fetchLinkedEntries(String goalId) async {}

  @override
  void deselectGoal() {}
}

// Helper: pump GoalDetailPage with provider overrides
Future<void> _pumpGoalDetailPage(
  WidgetTester tester, {
  required String goalId,
  List<Goal> goals = const [],
  bool isLoading = false,
  String? error,
  Goal? selectedGoal,
  List<Milestone> milestones = const [],
  List<Entry> linkedEntries = const [],
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
            linkedEntries: linkedEntries,
          ),
        ),
      ],
      child: MaterialApp(
        home: GoalDetailPage(goalId: goalId),
      ),
    ),
  );
  // Wait for initState addPostFrameCallback
  await tester.pump();
}

Goal _makeGoal({
  required String id,
  String title = 'Test Goal',
  String? description,
  double? progress,
  String? startDate,
  String? endDate,
}) {
  return Goal(
    id: id,
    title: title,
    description: description,
    progress: progress,
    startDate: startDate,
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

Entry _makeEntry({
  required String id,
  required String title,
  String category = 'task',
  String? content,
}) {
  return Entry(
    id: id,
    title: title,
    category: category,
    content: content,
  );
}

void main() {
  group('GoalDetailPage', () {
    const goalId = 'g1';

    testWidgets('加载中显示进度指示器', (WidgetTester tester) async {
      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        isLoading: true,
        selectedGoal: null,
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('错误状态显示错误信息和重试按钮', (WidgetTester tester) async {
      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        error: '网络连接失败',
        selectedGoal: null,
      );

      expect(find.text('网络连接失败'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    testWidgets('显示目标标题、描述和进度环', (WidgetTester tester) async {
      final goal = _makeGoal(
        id: goalId,
        title: '学习 Flutter',
        description: '掌握 Flutter 开发',
        progress: 75.0,
      );

      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        selectedGoal: goal,
      );

      expect(find.text('学习 Flutter'), findsOneWidget);
      expect(find.text('掌握 Flutter 开发'), findsOneWidget);
      // Progress ring is present
      expect(find.byType(ProgressRing), findsOneWidget);
    });

    testWidgets('显示日期范围', (WidgetTester tester) async {
      final goal = _makeGoal(
        id: goalId,
        title: 'Goal',
        startDate: '2026-01-01',
        endDate: '2026-06-30',
      );

      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        selectedGoal: goal,
      );

      expect(find.text('1月1日'), findsOneWidget);
      expect(find.text('6月30日'), findsOneWidget);
    });

    testWidgets('显示里程碑列表', (WidgetTester tester) async {
      final goal = _makeGoal(id: goalId, title: 'Goal');
      final milestones = [
        _makeMilestone(id: 'm1', goalId: goalId, title: 'First step'),
        _makeMilestone(
          id: 'm2',
          goalId: goalId,
          title: 'Second step',
          status: 'completed',
        ),
      ];

      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        selectedGoal: goal,
        milestones: milestones,
      );

      expect(find.text('First step'), findsOneWidget);
      expect(find.text('Second step'), findsOneWidget);
      // Section header
      expect(find.text('里程碑'), findsOneWidget);
      // Count
      expect(find.text('2'), findsOneWidget);
    });

    testWidgets('空里程碑显示空态文案', (WidgetTester tester) async {
      final goal = _makeGoal(id: goalId, title: 'Goal');

      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        selectedGoal: goal,
        milestones: [],
      );

      expect(find.text('暂无里程碑，点击右下角按钮添加'), findsOneWidget);
    });

    testWidgets('显示关联条目列表', (WidgetTester tester) async {
      final goal = _makeGoal(id: goalId, title: 'Goal');
      final entries = [
        _makeEntry(id: 'e1', title: 'Entry 1', content: 'Content 1'),
        _makeEntry(id: 'e2', title: 'Entry 2', content: 'Content 2'),
      ];

      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        selectedGoal: goal,
        linkedEntries: entries,
      );

      expect(find.text('Entry 1'), findsOneWidget);
      expect(find.text('Entry 2'), findsOneWidget);
      // Section header
      expect(find.text('关联条目'), findsOneWidget);
    });

    testWidgets('空关联条目显示空态文案', (WidgetTester tester) async {
      final goal = _makeGoal(id: goalId, title: 'Goal');

      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        selectedGoal: goal,
        linkedEntries: [],
      );

      expect(find.text('暂无关联条目'), findsOneWidget);
    });

    testWidgets('空目标（无里程碑无关联条目）的三态展示',
        (WidgetTester tester) async {
      final goal = _makeGoal(
        id: goalId,
        title: 'Empty Goal',
        description: 'No data',
      );

      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        selectedGoal: goal,
        milestones: [],
        linkedEntries: [],
      );

      expect(find.text('Empty Goal'), findsOneWidget);
      expect(find.text('No data'), findsOneWidget);
      expect(find.text('暂无里程碑，点击右下角按钮添加'), findsOneWidget);
      expect(find.text('暂无关联条目'), findsOneWidget);
    });

    testWidgets('FAB 存在且点击弹出添加里程碑对话框',
        (WidgetTester tester) async {
      final goal = _makeGoal(id: goalId, title: 'Goal');

      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        selectedGoal: goal,
      );

      // FAB exists
      expect(find.byType(FloatingActionButton), findsOneWidget);

      // Tap FAB
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // Dialog shows
      expect(find.text('添加里程碑'), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);
    });

    testWidgets('已完成的里程碑有删除线样式', (WidgetTester tester) async {
      final goal = _makeGoal(id: goalId, title: 'Goal');
      final milestones = [
        _makeMilestone(
          id: 'm1',
          goalId: goalId,
          title: 'Completed item',
          status: 'completed',
        ),
      ];

      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        selectedGoal: goal,
        milestones: milestones,
      );

      // Find the Text widget for the completed milestone and verify lineThrough
      final textFinder = find.text('Completed item');
      expect(textFinder, findsOneWidget);
      final textWidget = tester.widget<Text>(textFinder);
      expect(textWidget.style?.decoration, TextDecoration.lineThrough);
    });

    testWidgets('里程碑有到期日期', (WidgetTester tester) async {
      final goal = _makeGoal(id: goalId, title: 'Goal');
      final milestones = [
        _makeMilestone(
          id: 'm1',
          goalId: goalId,
          title: 'With date',
          dueDate: '2026-06-15',
        ),
      ];

      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        selectedGoal: goal,
        milestones: milestones,
      );

      expect(find.text('6月15日'), findsOneWidget);
    });

    testWidgets('AppBar 标题为"目标详情"', (WidgetTester tester) async {
      await _pumpGoalDetailPage(
        tester,
        goalId: goalId,
        selectedGoal: _makeGoal(id: goalId),
      );

      expect(find.text('目标详情'), findsOneWidget);
    });
  });
}
