import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/providers/today_provider.dart';

void main() {
  group('TodayState', () {
    test('initial state has empty lists and no error', () {
      const state = TodayState();

      expect(state.todayTasks, isEmpty);
      expect(state.recentEntries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });

    test('completionRate is 0 when no tasks', () {
      const state = TodayState();
      expect(state.completionRate, 0.0);
    });

    test('completionRate calculates done/total', () {
      final state = TodayState(
        todayTasks: [
          _makeEntry('1', status: 'done'),
          _makeEntry('2', status: 'todo'),
          _makeEntry('3', status: 'done'),
          _makeEntry('4', status: 'doing'),
        ],
      );

      // 2 done / 4 total = 0.5
      expect(state.completionRate, 0.5);
    });

    test('completionRate is 1.0 when all done', () {
      final state = TodayState(
        todayTasks: [
          _makeEntry('1', status: 'done'),
          _makeEntry('2', status: 'done'),
        ],
      );

      expect(state.completionRate, 1.0);
    });

    test('copyWith preserves unchanged fields', () {
      const state = TodayState(isLoading: true);
      final copied = state.copyWith(error: 'Network error');

      expect(copied.isLoading, true);
      expect(copied.error, 'Network error');
      expect(copied.todayTasks, isEmpty);
    });

    test('copyWith can update isLoading', () {
      const state = TodayState();
      final copied = state.copyWith(isLoading: true);

      expect(copied.isLoading, true);
      expect(copied.error, isNull);
    });

    test('copyWith can update todayTasks', () {
      const state = TodayState();
      final tasks = [_makeEntry('1', status: 'done')];
      final copied = state.copyWith(todayTasks: tasks);

      expect(copied.todayTasks, hasLength(1));
      expect(copied.todayTasks.first.id, '1');
    });

    test('copyWith can update recentEntries', () {
      const state = TodayState();
      final entries = [_makeEntry('n1', category: 'note')];
      final copied = state.copyWith(recentEntries: entries);

      expect(copied.recentEntries, hasLength(1));
    });
  });

  group('TodayNotifier with ProviderContainer', () {
    test('initial build returns default state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(todayProvider);

      expect(state.todayTasks, isEmpty);
      expect(state.recentEntries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });
  });
}

Entry _makeEntry(String id, {String? status, String category = 'task'}) {
  return Entry(
    id: id,
    title: 'Task $id',
    category: category,
    status: status,
  );
}
