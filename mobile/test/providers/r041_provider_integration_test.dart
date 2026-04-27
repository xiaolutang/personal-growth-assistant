import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/providers/auth_provider.dart';
import 'package:growth_assistant/providers/goals_provider.dart';
import 'package:growth_assistant/providers/review_provider.dart';
import 'package:growth_assistant/providers/notes_provider.dart';
import 'package:growth_assistant/providers/inbox_provider.dart';
import 'package:growth_assistant/services/api_client.dart';

// ============================================================
// Mock Dio HttpClientAdapter - 拦截 HTTP 请求并返回预设响应
// ============================================================
class _MockHttpClientAdapter implements HttpClientAdapter {
  final Map<String, dynamic> _responses;

  _MockHttpClientAdapter(this._responses);

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final key = '${options.method} ${options.path}';
    final mockResponse = _responses[key];

    if (mockResponse != null) {
      return ResponseBody.fromString(
        jsonEncode(mockResponse),
        200,
        headers: {
          'content-type': ['application/json'],
        },
      );
    }

    return ResponseBody.fromString(
      jsonEncode({'error': 'not found'}),
      404,
      headers: {
        'content-type': ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

/// 创建带 mock adapter 的 ApiClient，清除拦截器避免 platform channel 问题
ApiClient _createMockClient(Map<String, dynamic> responses) {
  final adapter = _MockHttpClientAdapter(responses);
  final client = ApiClient(baseUrl: 'http://test-api.local');
  client.dio.httpClientAdapter = adapter;
  client.dio.interceptors.clear();
  return client;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // ============================================================
  // GoalsNotifier Integration Tests
  // ============================================================
  group('GoalsNotifier integration', () {
    test('fetchGoals populates goals list from mock API', () async {
      final mockClient = _createMockClient({
        'GET /goals': {
          'goals': [
            {
              'id': 'g1',
              'title': 'Learn Dart',
              'status': 'active',
              'progress_percentage': 30.0,
            },
            {
              'id': 'g2',
              'title': 'Build App',
              'status': 'active',
              'progress_percentage': 60.0,
            },
          ],
        },
      });

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      // Trigger fetchGoals and await the returned Future
      await container.read(goalsProvider.notifier).fetchGoals();

      final state = container.read(goalsProvider);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.goals, hasLength(2));
      expect(state.goals[0].id, 'g1');
      expect(state.goals[0].title, 'Learn Dart');
      expect(state.goals[0].progress, 30.0);
      expect(state.goals[1].id, 'g2');
      expect(state.goals[1].title, 'Build App');
    });

    test('fetchGoalDetail sets selectedGoal from mock API', () async {
      final mockClient = _createMockClient({
        'GET /goals/g-999': {
          'id': 'g-999',
          'title': 'Deep Dive Flutter',
          'description': 'Master Flutter framework',
          'status': 'active',
          'progress_percentage': 45.0,
          'start_date': '2025-01-01',
          'end_date': '2025-12-31',
        },
      });

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container.read(goalsProvider.notifier).fetchGoalDetail('g-999');

      final state = container.read(goalsProvider);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.selectedGoal, isNotNull);
      expect(state.selectedGoal!.id, 'g-999');
      expect(state.selectedGoal!.title, 'Deep Dive Flutter');
      expect(state.selectedGoal!.progress, 45.0);
    });

    test('createMilestone refreshes milestones and goal detail', () async {
      final mockClient = _createMockClient({
        'POST /goals/g-1/milestones': {
          'id': 'm-new',
          'title': 'New Milestone',
          'status': 'pending',
        },
        'GET /goals/g-1/milestones': {
          'milestones': [
            {
              'id': 'm-new',
              'goal_id': 'g-1',
              'title': 'New Milestone',
              'status': 'pending',
            },
            {
              'id': 'm-old',
              'goal_id': 'g-1',
              'title': 'Old Milestone',
              'status': 'completed',
            },
          ],
        },
        'GET /goals/g-1': {
          'id': 'g-1',
          'title': 'My Goal',
          'status': 'active',
          'progress_percentage': 50.0,
        },
      });

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      // Set initial state with a goal in the list so _refreshGoalInList works
      container.read(goalsProvider.notifier).state = GoalsState(
        goals: [const Goal(id: 'g-1', title: 'My Goal')],
      );

      final result = await container
          .read(goalsProvider.notifier)
          .createMilestone('g-1', {'title': 'New Milestone'});

      expect(result, true);
      final state = container.read(goalsProvider);
      expect(state.error, isNull);
      // Milestones list should be refreshed
      expect(state.milestones, hasLength(2));
      expect(state.milestones[0].id, 'm-new');
      // selectedGoal should be refreshed
      expect(state.selectedGoal, isNotNull);
      expect(state.selectedGoal!.id, 'g-1');
      expect(state.selectedGoal!.progress, 50.0);
      // Goal in list should also be refreshed
      expect(state.goals[0].progress, 50.0);
    });

    test('fetchGoals handles API error gracefully', () async {
      // Empty responses map -> all requests return 404
      final mockClient = _createMockClient({});

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container.read(goalsProvider.notifier).fetchGoals();

      final state = container.read(goalsProvider);
      expect(state.isLoading, false);
      expect(state.error, isNotNull);
      expect(state.goals, isEmpty);
    });

    test('fetchGoalDetail handles API error gracefully', () async {
      final mockClient = _createMockClient({});

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container
          .read(goalsProvider.notifier)
          .fetchGoalDetail('nonexistent');

      final state = container.read(goalsProvider);
      expect(state.isLoading, false);
      expect(state.error, isNotNull);
      expect(state.selectedGoal, isNull);
    });
  });

  // ============================================================
  // ReviewNotifier Integration Tests
  // ============================================================
  group('ReviewNotifier integration', () {
    test('loadAll populates summary, trends, and insights concurrently',
        () async {
      final mockClient = _createMockClient({
        'GET /review/weekly': {
          'period': 'weekly',
          'total_entries': 15,
          'tasks_completed': 8,
        },
        'GET /review/trend': {
          'period': 'daily',
          'days': 7,
          'data': [
            {'date': '2025-04-21', 'count': 3},
            {'date': '2025-04-22', 'count': 5},
          ],
        },
        'GET /review/insights': {
          'period': 'weekly',
          'insights': [
            'Productivity peaked on Tuesday',
            'Most tasks were development-related',
          ],
        },
      });

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container.read(reviewProvider.notifier).loadAll('weekly');

      final state = container.read(reviewProvider);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      // Summary populated
      expect(state.summary, isNotNull);
      expect(state.summary!['total_entries'], 15);
      expect(state.summary!['tasks_completed'], 8);
      // Trends populated
      expect(state.trends, isNotNull);
      expect((state.trends!['data'] as List).length, 2);
      // Insights populated
      expect(state.insights, isNotNull);
      expect((state.insights!['insights'] as List).length, 2);
    });

    test('loadAll with monthly period uses weekly trends with weeks=4',
        () async {
      final mockClient = _createMockClient({
        'GET /review/monthly': {
          'period': 'monthly',
          'total_entries': 60,
        },
        'GET /review/trend': {
          'period': 'weekly',
          'weeks': 4,
          'data': [],
        },
        'GET /review/insights': {
          'period': 'monthly',
          'insights': ['Month summary'],
        },
      });

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container.read(reviewProvider.notifier).loadAll('monthly');

      final state = container.read(reviewProvider);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.selectedPeriod, 'monthly');
      expect(state.summary, isNotNull);
      expect(state.summary!['total_entries'], 60);
    });

    test('loadAll handles API error gracefully', () async {
      final mockClient = _createMockClient({});

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container.read(reviewProvider.notifier).loadAll();

      final state = container.read(reviewProvider);
      expect(state.isLoading, false);
      expect(state.error, isNotNull);
      // None of the data should be populated on error
      expect(state.summary, isNull);
      expect(state.trends, isNull);
      expect(state.insights, isNull);
    });
  });

  // ============================================================
  // NotesNotifier Integration Tests
  // ============================================================
  group('NotesNotifier integration', () {
    test('fetchNotes populates entries from mock API', () async {
      final mockClient = _createMockClient({
        'GET /entries': {
          'entries': [
            {
              'id': 'n1',
              'title': 'Flutter Tips',
              'category': 'note',
              'content': 'Use const constructors',
              'tags': ['flutter', 'dart'],
              'created_at': '2025-04-20T10:00:00',
            },
            {
              'id': 'n2',
              'title': 'Riverpod Patterns',
              'category': 'note',
              'content': 'Use Notifier for complex state',
              'tags': ['riverpod'],
              'created_at': '2025-04-21T14:30:00',
            },
          ],
        },
      });

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container.read(notesProvider.notifier).fetchNotes();

      final state = container.read(notesProvider);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.entries, hasLength(2));
      expect(state.entries[0].id, 'n1');
      expect(state.entries[0].title, 'Flutter Tips');
      expect(state.entries[0].category, 'note');
      expect(state.entries[0].tags, ['flutter', 'dart']);
      expect(state.entries[1].id, 'n2');
      expect(state.entries[1].title, 'Riverpod Patterns');
    });

    test('fetchNotes handles API error gracefully', () async {
      final mockClient = _createMockClient({});

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container.read(notesProvider.notifier).fetchNotes();

      final state = container.read(notesProvider);
      expect(state.isLoading, false);
      expect(state.error, isNotNull);
      expect(state.entries, isEmpty);
    });

    test('fetchNotes handles empty response', () async {
      final mockClient = _createMockClient({
        'GET /entries': {'entries': []},
      });

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container.read(notesProvider.notifier).fetchNotes();

      final state = container.read(notesProvider);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.entries, isEmpty);
    });

    test('fetchNotes handles null entries gracefully', () async {
      final mockClient = _createMockClient({
        'GET /entries': {'total': 0},
      });

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container.read(notesProvider.notifier).fetchNotes();

      final state = container.read(notesProvider);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.entries, isEmpty);
    });
  });

  // ============================================================
  // InboxNotifier Integration Tests
  // ============================================================
  group('InboxNotifier integration', () {
    test('fetchInbox populates entries from mock API', () async {
      final mockClient = _createMockClient({
        'GET /entries': {
          'entries': [
            {
              'id': 'i1',
              'title': 'Idea: AI-powered todo',
              'category': 'inbox',
              'created_at': '2025-04-19T08:00:00',
            },
            {
              'id': 'i2',
              'title': 'Book recommendation',
              'category': 'inbox',
              'created_at': '2025-04-20T12:00:00',
            },
            {
              'id': 'i3',
              'title': 'Blog post topic',
              'category': 'inbox',
              'created_at': '2025-04-21T09:30:00',
            },
          ],
        },
      });

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container.read(inboxProvider.notifier).fetchInbox();

      final state = container.read(inboxProvider);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.entries, hasLength(3));
      expect(state.entries[0].id, 'i1');
      expect(state.entries[0].title, 'Idea: AI-powered todo');
      expect(state.entries[0].category, 'inbox');
      expect(state.entries[2].id, 'i3');
      expect(state.entries[2].title, 'Blog post topic');
    });

    test('fetchInbox handles API error gracefully', () async {
      final mockClient = _createMockClient({});

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      await container.read(inboxProvider.notifier).fetchInbox();

      final state = container.read(inboxProvider);
      expect(state.isLoading, false);
      expect(state.error, isNotNull);
      expect(state.entries, isEmpty);
    });

    test('createInboxItem creates entry and refreshes list', () async {
      final mockClient = _createMockClient({
        'POST /entries': {
          'id': 'new-id',
          'title': 'New Idea',
          'category': 'inbox',
        },
        'GET /entries': {
          'entries': [
            {
              'id': 'new-id',
              'title': 'New Idea',
              'category': 'inbox',
              'created_at': '2025-04-22T10:00:00',
            },
            {
              'id': 'existing-id',
              'title': 'Existing Idea',
              'category': 'inbox',
              'created_at': '2025-04-20T10:00:00',
            },
          ],
        },
      });

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      final result = await container
          .read(inboxProvider.notifier)
          .createInboxItem('New Idea');

      expect(result, true);
      final state = container.read(inboxProvider);
      expect(state.error, isNull);
      // List should be refreshed with both old and new entries
      expect(state.entries, hasLength(2));
      expect(state.entries.any((e) => e.id == 'new-id'), true);
    });

    test('createInboxItem returns false for empty title', () async {
      final mockClient = _createMockClient({});

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      final result = await container
          .read(inboxProvider.notifier)
          .createInboxItem('   ');

      expect(result, false);
      final state = container.read(inboxProvider);
      expect(state.entries, isEmpty);
      // No API calls should have been made
      expect(state.error, isNull);
    });

    test('convertCategory removes entry from list', () async {
      final mockClient = _createMockClient({
        'PUT /entries/i1': {
          'id': 'i1',
          'category': 'task',
          'title': 'Converted Item',
        },
      });

      final container = ProviderContainer(
        overrides: [apiClientProvider.overrideWithValue(mockClient)],
      );
      addTearDown(container.dispose);

      // Pre-populate state with entries (Entry constructor is not const due to List default)
      container.read(inboxProvider.notifier).state = InboxState(
        entries: [
          Entry(id: 'i1', title: 'Item 1', category: 'inbox'),
          Entry(id: 'i2', title: 'Item 2', category: 'inbox'),
        ],
      );

      final result = await container
          .read(inboxProvider.notifier)
          .convertCategory('i1', 'task');

      expect(result, true);
      final state = container.read(inboxProvider);
      expect(state.error, isNull);
      // i1 should be removed from the list
      expect(state.entries, hasLength(1));
      expect(state.entries[0].id, 'i2');
    });
  });
}
