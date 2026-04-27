import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/providers/goals_provider.dart';

void main() {
  group('GoalsState', () {
    test('initial state has empty goals, no selectedGoal, no error', () {
      const state = GoalsState();

      expect(state.goals, isEmpty);
      expect(state.selectedGoal, isNull);
      expect(state.milestones, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });

    test('copyWith preserves unchanged fields', () {
      const state = GoalsState(isLoading: true);
      final copied = state.copyWith(error: 'Network error');

      expect(copied.isLoading, true);
      expect(copied.error, 'Network error');
      expect(copied.goals, isEmpty);
      expect(copied.selectedGoal, isNull);
      expect(copied.milestones, isEmpty);
    });

    test('copyWith can update goals', () {
      const state = GoalsState();
      final goal = Goal(id: 'g1', title: 'Learn Flutter');
      final copied = state.copyWith(goals: [goal]);

      expect(copied.goals, hasLength(1));
      expect(copied.goals.first.id, 'g1');
      expect(copied.goals.first.title, 'Learn Flutter');
    });

    test('copyWith can update selectedGoal', () {
      const state = GoalsState();
      final goal = Goal(id: 'g1', title: 'Learn Flutter');
      final copied = state.copyWith(selectedGoal: goal);

      expect(copied.selectedGoal, isNotNull);
      expect(copied.selectedGoal!.id, 'g1');
    });

    test('copyWith can update milestones', () {
      const state = GoalsState();
      final milestone = Milestone(
        id: 'm1',
        goalId: 'g1',
        title: 'Complete chapter 1',
      );
      final copied = state.copyWith(milestones: [milestone]);

      expect(copied.milestones, hasLength(1));
      expect(copied.milestones.first.id, 'm1');
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

    test('copyWith can clear selectedGoal', () {
      const state = GoalsState();
      final withGoal = state.copyWith(
        selectedGoal: Goal(id: 'g1', title: 'Goal'),
      );
      expect(withGoal.selectedGoal, isNotNull);

      final cleared = withGoal.copyWith(selectedGoal: null);
      expect(cleared.selectedGoal, isNull);
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
      expect(state.selectedGoal, isNull);
      expect(state.milestones, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });
  });
}
