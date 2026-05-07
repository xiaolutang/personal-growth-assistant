import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/models/morning_digest.dart';
import 'package:growth_assistant/providers/today_provider.dart';

void main() {
  group('TodayState', () {
    test('initial state has empty lists and no error', () {
      const state = TodayState();

      expect(state.todayTasks, isEmpty);
      expect(state.recentEntries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.morningDigest.status, MorningDigestStatus.initial);
      expect(state.morningDigest.data, isNull);
    });

    test('completionRate is 0 when no tasks', () {
      const state = TodayState();
      expect(state.completionRate, 0.0);
    });

    test('completionRate calculates done/total', () {
      final state = TodayState(
        todayTasks: [
          _makeEntry('1', status: 'complete'),
          _makeEntry('2', status: 'waitStart'),
          _makeEntry('3', status: 'complete'),
          _makeEntry('4', status: 'doing'),
        ],
      );

      // 2 complete / 4 total = 0.5
      expect(state.completionRate, 0.5);
    });

    test('completionRate is 1.0 when all done', () {
      final state = TodayState(
        todayTasks: [
          _makeEntry('1', status: 'complete'),
          _makeEntry('2', status: 'complete'),
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
      expect(copied.morningDigest.status, MorningDigestStatus.initial);
    });

    test('copyWith can update isLoading', () {
      const state = TodayState();
      final copied = state.copyWith(isLoading: true);

      expect(copied.isLoading, true);
      expect(copied.error, isNull);
    });

    test('copyWith can update todayTasks', () {
      const state = TodayState();
      final tasks = [_makeEntry('1', status: 'complete')];
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

    test('copyWith can update morningDigest', () {
      const state = TodayState();
      final digestState = MorningDigestState(
        status: MorningDigestStatus.loaded,
        data: MorningDigest(
          date: '2026-05-07',
          aiSuggestion: 'Test',
        ),
      );
      final copied = state.copyWith(morningDigest: digestState);

      expect(copied.morningDigest.status, MorningDigestStatus.loaded);
      expect(copied.morningDigest.data, isNotNull);
      expect(copied.morningDigest.data!.date, '2026-05-07');
    });
  });

  group('MorningDigestState', () {
    test('initial state is correct', () {
      const state = MorningDigestState();
      expect(state.status, MorningDigestStatus.initial);
      expect(state.data, isNull);
      expect(state.error, isNull);
    });

    test('copyWith preserves unchanged fields', () {
      const state = MorningDigestState(status: MorningDigestStatus.loading);
      final copied = state.copyWith(error: 'timeout');
      expect(copied.status, MorningDigestStatus.loading);
      expect(copied.error, 'timeout');
    });

    test('copyWith can update status', () {
      const state = MorningDigestState();
      final copied = state.copyWith(status: MorningDigestStatus.loaded);
      expect(copied.status, MorningDigestStatus.loaded);
    });
  });

  group('MorningDigest model', () {
    test('fromJson parses all fields', () {
      final json = {
        'date': '2026-05-07',
        'ai_suggestion': 'Today you have tasks',
        'todos': [
          {'id': '1', 'title': 'Task 1', 'priority': 'high'},
        ],
        'overdue': [
          {'id': '2', 'title': 'Overdue 1', 'planned_date': '2026-05-06'},
        ],
        'stale_inbox': [
          {'id': '3', 'title': 'Inbox 1', 'created_at': '2026-05-04'},
        ],
        'weekly_summary': {
          'new_concepts': ['Flutter', 'Riverpod'],
          'entries_count': 12,
        },
        'learning_streak': 7,
        'daily_focus': {
          'title': 'Focus on tasks',
          'description': 'Complete all overdue items',
        },
        'pattern_insights': ['Insight 1', 'Insight 2'],
        'cached_at': null,
      };

      final digest = MorningDigest.fromJson(json);

      expect(digest.date, '2026-05-07');
      expect(digest.aiSuggestion, 'Today you have tasks');
      expect(digest.todos, hasLength(1));
      expect(digest.todos.first.title, 'Task 1');
      expect(digest.todos.first.priority, 'high');
      expect(digest.overdue, hasLength(1));
      expect(digest.overdue.first.plannedDate, '2026-05-06');
      expect(digest.staleInbox, hasLength(1));
      expect(digest.weeklySummary.newConcepts, ['Flutter', 'Riverpod']);
      expect(digest.weeklySummary.entriesCount, 12);
      expect(digest.learningStreak, 7);
      expect(digest.dailyFocus, isNotNull);
      expect(digest.dailyFocus!.title, 'Focus on tasks');
      expect(digest.patternInsights, ['Insight 1', 'Insight 2']);
      expect(digest.cachedAt, isNull);
    });

    test('fromJson handles missing optional fields', () {
      final json = {
        'date': '2026-05-07',
        'ai_suggestion': 'Summary',
      };

      final digest = MorningDigest.fromJson(json);

      expect(digest.date, '2026-05-07');
      expect(digest.aiSuggestion, 'Summary');
      expect(digest.todos, isEmpty);
      expect(digest.overdue, isEmpty);
      expect(digest.staleInbox, isEmpty);
      expect(digest.weeklySummary.newConcepts, isEmpty);
      expect(digest.learningStreak, 0);
      expect(digest.dailyFocus, isNull);
      expect(digest.patternInsights, isEmpty);
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
      expect(state.morningDigest.status, MorningDigestStatus.initial);
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
