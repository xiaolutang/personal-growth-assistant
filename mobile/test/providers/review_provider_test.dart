import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/providers/review_provider.dart';

void main() {
  group('ReviewState', () {
    test('initial state has default values and selectedPeriod is weekly', () {
      const state = ReviewState();

      expect(state.summary, isNull);
      expect(state.trends, isNull);
      expect(state.insights, isNull);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.selectedPeriod, 'weekly');
    });

    test('copyWith preserves unchanged fields', () {
      const state = ReviewState(isLoading: true, selectedPeriod: 'monthly');
      final copied = state.copyWith(error: 'Failed to load');

      expect(copied.isLoading, true);
      expect(copied.error, 'Failed to load');
      expect(copied.selectedPeriod, 'monthly');
      expect(copied.summary, isNull);
    });

    test('copyWith can update summary', () {
      const state = ReviewState();
      final summary = {'total_entries': 42, 'streak': 7};
      final copied = state.copyWith(summary: summary);

      expect(copied.summary, isNotNull);
      expect(copied.summary!['total_entries'], 42);
    });

    test('copyWith can update trends', () {
      const state = ReviewState();
      final trends = {'period': 'daily', 'data': [1, 2, 3]};
      final copied = state.copyWith(trends: trends);

      expect(copied.trends, isNotNull);
      expect(copied.trends!['period'], 'daily');
    });

    test('copyWith can update insights', () {
      const state = ReviewState();
      final insights = {'top_category': 'note', 'count': 10};
      final copied = state.copyWith(insights: insights);

      expect(copied.insights, isNotNull);
      expect(copied.insights!['top_category'], 'note');
    });

    test('copyWith can update isLoading', () {
      const state = ReviewState();
      final copied = state.copyWith(isLoading: true);

      expect(copied.isLoading, true);
      expect(copied.error, isNull);
    });

    test('copyWith can update selectedPeriod', () {
      const state = ReviewState();
      final copied = state.copyWith(selectedPeriod: 'monthly');

      expect(copied.selectedPeriod, 'monthly');
    });

    test('copyWith can clear error', () {
      const state = ReviewState(error: 'Some error');
      final copied = state.copyWith(error: null);

      expect(copied.error, isNull);
    });

    test('copyWith can clear error while updating other fields', () {
      const state = ReviewState(error: 'Error', isLoading: true);
      final copied = state.copyWith(isLoading: false, error: null);

      expect(copied.isLoading, false);
      expect(copied.error, isNull);
    });
  });

  group('ReviewNotifier with ProviderContainer', () {
    test('initial build returns default state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(reviewProvider);

      expect(state.summary, isNull);
      expect(state.trends, isNull);
      expect(state.insights, isNull);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.selectedPeriod, 'weekly');
    });
  });
}
