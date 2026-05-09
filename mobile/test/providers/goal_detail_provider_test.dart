import 'package:dio/dio.dart' hide Response;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/providers/goals_provider.dart';

import '../../lib/providers/auth_provider.dart' show apiClientProvider;

// ============================================================
// Fake ApiClient helpers
// ============================================================

/// Minimal Response-like class for test doubles
class _FakeResponse<T> {
  final T? data;
  _FakeResponse(this.data);
}

/// A stub ApiClient that returns preset data for goal detail operations.
/// We use a simple approach: override the provider with a test notifier.
// ============================================================
// Test 1: goalDetailProvider 创建和销毁测试
// ============================================================

void main() {
  group('goalDetailProvider lifecycle', () {
    test('initial state has no goal, no milestones, no entries', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(goalDetailProvider('g1'));
      expect(state.goal, isNull);
      expect(state.milestones, isEmpty);
      expect(state.linkedEntries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });

    test('different goalId yields independent state objects', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      // Set one provider's state
      container.read(goalDetailProvider('g1').notifier).state =
          const GoalDetailState(
        goal: Goal(id: 'g1', title: 'Goal 1'),
      );

      // The other should still be default
      final state1 = container.read(goalDetailProvider('g1'));
      final state2 = container.read(goalDetailProvider('g2'));

      expect(state1.goal, isNotNull);
      expect(state1.goal!.id, 'g1');
      expect(state2.goal, isNull);
    });
  });

  // ============================================================
  // 2. GoalsPage loading 状态不受 GoalDetailPage fetchGoalDetail 影响
  // ============================================================
  group('error-isolation: GoalsProvider unaffected by detail fetches', () {
    test(
        'goalsProvider isLoading stays false when goalDetailProvider sets isLoading',
        () async {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      // Pre-set goalsProvider with some goals
      final goalsNotifier = container.read(goalsProvider.notifier);
      goalsNotifier.state = const GoalsState(
        goals: [Goal(id: 'g1', title: 'Test')],
      );

      // Set detail provider to loading state directly
      final detailNotifier =
          container.read(goalDetailProvider('g1').notifier);
      detailNotifier.state = const GoalDetailState(isLoading: true);

      // goalsProvider should still not be loading
      expect(container.read(goalsProvider).isLoading, false);
      // goalsProvider should still have its goals
      expect(container.read(goalsProvider).goals, isNotEmpty);
      // detailProvider should be loading
      expect(container.read(goalDetailProvider('g1')).isLoading, true);
    });
  });

  // ============================================================
  // 3. GoalsPage error 状态不受 GoalDetailPage 错误影响
  // ============================================================
  group('error-isolation: GoalsProvider error unaffected by detail errors', () {
    test('goalsProvider error stays null when goalDetailProvider has error',
        () async {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      // Pre-set goalsProvider with some goals, no error
      final goalsNotifier = container.read(goalsProvider.notifier);
      goalsNotifier.state = const GoalsState(
        goals: [Goal(id: 'g1', title: 'Test')],
      );

      expect(container.read(goalsProvider).error, isNull);

      // Set detail provider error
      final detailNotifier =
          container.read(goalDetailProvider('g1').notifier);
      detailNotifier.state =
          const GoalDetailState(error: 'Detail fetch failed');

      // goalsProvider error should remain null
      expect(container.read(goalsProvider).error, isNull);
      // goalDetailProvider should have the error
      expect(container.read(goalDetailProvider('g1')).error, 'Detail fetch failed');
    });
  });

  // ============================================================
  // 4. goalDetailProvider state management
  // ============================================================
  group('goalDetailProvider state management', () {
    test('state can be set with goal data', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(goalDetailProvider('g1').notifier);
      notifier.state = GoalDetailState(
        goal: const Goal(id: 'g1', title: 'Test', progress: 50.0),
        milestones: [
          const Milestone(id: 'm1', goalId: 'g1', title: 'Step 1'),
        ],
        linkedEntries: const [],
      );

      final state = container.read(goalDetailProvider('g1'));
      expect(state.goal, isNotNull);
      expect(state.goal!.id, 'g1');
      expect(state.goal!.progress, 50.0);
      expect(state.milestones, hasLength(1));
      expect(state.milestones[0].title, 'Step 1');
    });
  });

  // ============================================================
  // 5. 详情页变更后，GoalsPage 列表同步更新（mutation-sync-back）
  // ============================================================
  group('mutation-sync-back: detail changes sync to goals list', () {
    test('syncGoalBackToList updates matching goal in goals list', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      // Pre-set goalsProvider with an old-progress goal
      final goalsNotifier = container.read(goalsProvider.notifier);
      goalsNotifier.state = const GoalsState(
        goals: [Goal(id: 'g1', title: 'Learn Flutter', progress: 30.0)],
      );

      // Set detail provider with updated goal
      final detailNotifier =
          container.read(goalDetailProvider('g1').notifier);
      detailNotifier.state = const GoalDetailState(
        goal: Goal(id: 'g1', title: 'Learn Flutter', progress: 75.0),
      );

      // Sync back to goals list
      detailNotifier.syncGoalBackToList();

      // Check goals list is updated
      final goalsState = container.read(goalsProvider);
      expect(goalsState.goals, hasLength(1));
      expect(goalsState.goals.first.progress, 75.0);
    });

    test('sync back does not affect other goals in the list', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      // Pre-set goalsProvider with two goals
      final goalsNotifier = container.read(goalsProvider.notifier);
      goalsNotifier.state = const GoalsState(
        goals: [
          Goal(id: 'g1', title: 'Goal 1', progress: 30.0),
          Goal(id: 'g2', title: 'Goal 2', progress: 50.0),
        ],
      );

      // Set detail provider for g1
      final detailNotifier =
          container.read(goalDetailProvider('g1').notifier);
      detailNotifier.state = const GoalDetailState(
        goal: Goal(id: 'g1', title: 'Goal 1', progress: 90.0),
      );
      detailNotifier.syncGoalBackToList();

      // Check g2 is untouched
      final goalsState = container.read(goalsProvider);
      expect(goalsState.goals[0].progress, 90.0);
      expect(goalsState.goals[1].progress, 50.0);
    });

    test('sync back does nothing when goal is null', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      // Pre-set goalsProvider
      final goalsNotifier = container.read(goalsProvider.notifier);
      goalsNotifier.state = const GoalsState(
        goals: [Goal(id: 'g1', title: 'Goal 1', progress: 30.0)],
      );

      // Detail provider with null goal
      final detailNotifier =
          container.read(goalDetailProvider('g1').notifier);
      detailNotifier.state = const GoalDetailState();
      detailNotifier.syncGoalBackToList();

      // Goals list unchanged
      final goalsState = container.read(goalsProvider);
      expect(goalsState.goals.first.progress, 30.0);
    });
  });
}
