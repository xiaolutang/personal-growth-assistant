import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rizhi/providers/goals_provider.dart';

void main() {
  group('GoalsState', () {
    test('initial state has empty goals, no error', () {
      const state = GoalsState();

      expect(state.goals, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });

    test('copyWith preserves unchanged fields', () {
      const state = GoalsState(isLoading: true);
      final copied = state.copyWith(error: 'Network error');

      expect(copied.isLoading, true);
      expect(copied.error, 'Network error');
      expect(copied.goals, isEmpty);
    });

    test('copyWith can update goals', () {
      const state = GoalsState();
      final goal = Goal(id: 'g1', title: 'Learn Flutter');
      final copied = state.copyWith(goals: [goal]);

      expect(copied.goals, hasLength(1));
      expect(copied.goals.first.id, 'g1');
      expect(copied.goals.first.title, 'Learn Flutter');
    });

    test('copyWith can update isLoading', () {
      const state = GoalsState();
      final copied = state.copyWith(isLoading: true);

      expect(copied.isLoading, true);
      expect(copied.error, isNull);
    });

    test('copyWith can clear error', () {
      const state = GoalsState(error: 'Some error');
      final copied = state.copyWith(error: null);

      expect(copied.error, isNull);
    });

    test('copyWith can clear error while updating other fields', () {
      const state = GoalsState(error: 'Error', isLoading: true);
      final copied = state.copyWith(isLoading: false, error: null);

      expect(copied.isLoading, false);
      expect(copied.error, isNull);
    });
  });

  group('GoalsNotifier with ProviderContainer', () {
    test('initial build returns default state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(goalsProvider);

      expect(state.goals, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });
  });

  group('GoalsNotifier.updateGoalInList', () {
    test('updates matching goal in list', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(goalsProvider.notifier);
      // Set initial goals
      notifier.state = const GoalsState(goals: [
        Goal(id: 'g1', title: 'Goal 1', progress: 30.0),
        Goal(id: 'g2', title: 'Goal 2', progress: 50.0),
      ]);

      // Update g1
      notifier.updateGoalInList(
        const Goal(id: 'g1', title: 'Goal 1', progress: 75.0),
      );

      final state = container.read(goalsProvider);
      expect(state.goals[0].progress, 75.0);
      expect(state.goals[1].progress, 50.0);
    });

    test('does nothing if goal id not found', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(goalsProvider.notifier);
      notifier.state = const GoalsState(goals: [
        Goal(id: 'g1', title: 'Goal 1'),
      ]);

      notifier.updateGoalInList(
        const Goal(id: 'g999', title: 'Not Found'),
      );

      final state = container.read(goalsProvider);
      expect(state.goals, hasLength(1));
      expect(state.goals.first.id, 'g1');
    });
  });

  group('GoalDetailState', () {
    test('initial state has no goal, no milestones, no entries', () {
      const state = GoalDetailState();

      expect(state.goal, isNull);
      expect(state.milestones, isEmpty);
      expect(state.linkedEntries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });

    test('copyWith preserves unchanged fields', () {
      const state = GoalDetailState(isLoading: true);
      final copied = state.copyWith(error: 'Network error');

      expect(copied.isLoading, true);
      expect(copied.error, 'Network error');
      expect(copied.milestones, isEmpty);
    });

    test('copyWith can clear goal', () {
      const state = GoalDetailState();
      final withGoal = state.copyWith(
        goal: Goal(id: 'g1', title: 'Goal'),
      );
      expect(withGoal.goal, isNotNull);

      final cleared = withGoal.copyWith(goal: null);
      expect(cleared.goal, isNull);
    });

    test('copyWith can clear error', () {
      const state = GoalDetailState(error: 'Some error');
      final copied = state.copyWith(error: null);

      expect(copied.error, isNull);
    });
  });

  group('goalDetailProvider', () {
    test('initial state is default for any goalId', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(goalDetailProvider('g1'));
      expect(state.goal, isNull);
      expect(state.milestones, isEmpty);
      expect(state.linkedEntries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });

    test('different goalId yields independent state', () {
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
}
