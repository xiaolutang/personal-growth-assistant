import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/providers/auth_provider.dart';
import 'package:growth_assistant/providers/explore_provider.dart';
import 'package:growth_assistant/services/api_client.dart';

void main() {
  // ============================================================
  // Per-tab cache tests
  // ============================================================
  group('Per-tab cache: loadEntries with tabIndex', () {
    test('tab 0 first load triggers API', () async {
      final api = _TrackingFakeApiClient(
        entriesResponse: _makeEntriesResponse(['1', '2']),
      );
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(api),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries(tabIndex: 0, type: null);

      expect(notifier.state.entries, hasLength(2));
      expect(api.fetchCallCount, 1);
    });

    test('tab 1 first load triggers API', () async {
      final api = _TrackingFakeApiClient(
        entriesResponse: _makeEntriesResponse(['3']),
      );
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(api),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries(tabIndex: 1, type: 'task');

      expect(notifier.state.entries, hasLength(1));
      expect(api.fetchCallCount, 1);
    });

    test('cache hit: returning to tab 0 does NOT trigger API', () async {
      final api = _TrackingFakeApiClient(
        entriesResponse: _makeEntriesResponse(['1', '2']),
      );
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(api),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);

      // First load tab 0
      await notifier.loadEntries(tabIndex: 0, type: null);
      expect(api.fetchCallCount, 1);

      // Switch to tab 1
      await notifier.loadEntries(tabIndex: 1, type: 'task');
      expect(api.fetchCallCount, 2);

      // Return to tab 0 - should use cache
      await notifier.loadEntries(tabIndex: 0, type: null);
      expect(api.fetchCallCount, 2); // no new API call
      expect(notifier.state.entries, hasLength(2));
    });

    test('tab A and tab B data are isolated', () async {
      final api = _TypeAwareFakeApiClient(
        responses: {
          null: _makeEntriesResponse(['a1', 'a2']),
          'task': _makeEntriesResponse(['b1']),
        },
      );
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(api),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);

      // Load tab 0 (all)
      await notifier.loadEntries(tabIndex: 0, type: null);
      expect(notifier.state.entries, hasLength(2));

      // Load tab 1 (task)
      await notifier.loadEntries(tabIndex: 1, type: 'task');
      expect(notifier.state.entries, hasLength(1));
      expect(notifier.state.entries.first.id, 'b1');

      // Back to tab 0 (cached)
      await notifier.loadEntries(tabIndex: 0, type: null);
      expect(notifier.state.entries, hasLength(2));
      expect(notifier.state.entries.first.id, 'a1');
    });

    test('refresh clears current tab cache and re-fetches', () async {
      final api = _TrackingFakeApiClient(
        entriesResponse: _makeEntriesResponse(['1', '2']),
      );
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(api),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);

      // Load tab 0
      await notifier.loadEntries(tabIndex: 0, type: null);
      expect(api.fetchCallCount, 1);

      // Refresh tab 0
      await notifier.refreshTab(tabIndex: 0, type: null);
      expect(api.fetchCallCount, 2);
      expect(notifier.state.entries, hasLength(2));
    });

    test('loading state is per-tab isolated', () async {
      // We test that switching tabs while one is loading doesn't affect the other
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(_TrackingFakeApiClient(
          entriesResponse: _makeEntriesResponse(['1']),
        )),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);

      // Load tab 0
      await notifier.loadEntries(tabIndex: 0, type: null);
      expect(notifier.state.isLoading, false);

      // Load tab 1 - should set loading for tab 1 only, tab 0 cached data stays
      await notifier.loadEntries(tabIndex: 1, type: 'task');
      expect(notifier.state.isLoading, false);
      expect(notifier.state.entries, hasLength(1));
    });

    test('error on tab 0 does not affect tab 1', () async {
      final api = _TypeAwareFakeApiClient(
        responses: {
          null: null, // will throw
          'task': _makeEntriesResponse(['b1']),
        },
        shouldThrowForNull: true,
      );
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(api),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);

      // Load tab 0 - should fail
      await notifier.loadEntries(tabIndex: 0, type: null);
      expect(notifier.state.error, isNotNull);
      expect(notifier.state.entries, isEmpty);

      // Load tab 1 - should succeed
      await notifier.loadEntries(tabIndex: 1, type: 'task');
      expect(notifier.state.entries, hasLength(1));
      // After loading tab 1, the error from tab 0 should be cleared since
      // we switched active tab context
    });

    test('error recovery: refresh after failure', () async {
      var shouldFail = true;
      final api = _ConditionalFakeApiClient(
        onResponse: () {
          if (shouldFail) {
            throw DioException(
              requestOptions: RequestOptions(path: '/entries'),
              type: DioExceptionType.connectionTimeout,
            );
          }
          return _makeEntriesResponse(['1', '2']);
        },
      );
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(api),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);

      // First load fails
      await notifier.loadEntries(tabIndex: 0, type: null);
      expect(notifier.state.error, isNotNull);
      expect(notifier.state.entries, isEmpty);

      // Fix API and refresh
      shouldFail = false;
      await notifier.refreshTab(tabIndex: 0, type: null);
      expect(notifier.state.error, isNull);
      expect(notifier.state.entries, hasLength(2));
    });

    test('smoke: full tab switch cycle', () async {
      final api = _TypeAwareFakeApiClient(
        responses: {
          null: _makeEntriesResponse(['all-1', 'all-2']),
          'task': _makeEntriesResponse(['task-1']),
          'note': _makeEntriesResponse(['note-1', 'note-2', 'note-3']),
        },
      );
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(api),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);

      // Tab 0 (all) - first load
      await notifier.loadEntries(tabIndex: 0, type: null);
      expect(notifier.state.entries, hasLength(2));

      // Tab 1 (task) - first load
      await notifier.loadEntries(tabIndex: 1, type: 'task');
      expect(notifier.state.entries, hasLength(1));
      expect(notifier.state.entries.first.id, 'task-1');

      // Tab 2 (note) - first load
      await notifier.loadEntries(tabIndex: 2, type: 'note');
      expect(notifier.state.entries, hasLength(3));

      // Back to tab 0 - cached
      await notifier.loadEntries(tabIndex: 0, type: null);
      expect(notifier.state.entries, hasLength(2));
      expect(api.fetchCounts[null], 1); // only called once for type=null

      // Refresh tab 0
      await notifier.refreshTab(tabIndex: 0, type: null);
      expect(notifier.state.entries, hasLength(2));
      expect(api.fetchCounts[null], 2); // now called twice
    });

    test('loadEntries without tabIndex works for backward compatibility', () async {
      final api = _TrackingFakeApiClient(
        entriesResponse: _makeEntriesResponse(['1']),
      );
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(api),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries(type: 'task');

      expect(notifier.state.entries, hasLength(1));
    });
  });
}

// ============================================================
// Helpers
// ============================================================

Entry _makeEntry(String id, {String category = 'task'}) {
  return Entry(id: id, title: 'Entry $id', category: category);
}

Map<String, dynamic> _makeEntriesResponse(List<String> ids) {
  return {
    'entries': ids.map((id) => _makeEntry(id).toJson()).toList(),
  };
}

/// Tracks fetch call count
class _TrackingFakeApiClient implements ApiClient {
  final Map<String, dynamic>? entriesResponse;
  int fetchCallCount = 0;

  _TrackingFakeApiClient({this.entriesResponse});

  @override
  Dio get dio => Dio();

  @override
  Future<Response<T>> fetchEntries<T>({
    String? type,
    String? status,
    String? tags,
    String? startDate,
    String? endDate,
    int? limit,
    int? offset,
  }) async {
    fetchCallCount++;
    return Response<T>(
      data: entriesResponse as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries'),
    );
  }

  @override
  Future<Response<T>> searchEntries<T>({required String query, int? limit}) async {
    return Response<T>(
      data: entriesResponse as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries/search/query'),
    );
  }

  @override
  Future<Response<T>> deleteEntry<T>({required String id}) async {
    return Response<T>(
      data: {'success': true} as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries/$id'),
    );
  }

  @override
  Future<Response<T>> updateEntryCategory<T>({required String id, required String category}) async {
    return Response<T>(
      data: {'success': true} as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries/$id'),
    );
  }

  @override
  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? queryParameters, Options? options}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: path));
  }

  @override
  Future<Response<T>> post<T>(String path, {dynamic data, Options? options, Map<String, dynamic>? queryParameters}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: path));
  }

  @override
  Future<Response<T>> put<T>(String path, {dynamic data, Options? options, Map<String, dynamic>? queryParameters}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: path));
  }

  @override
  Future<Response<T>> delete<T>(String path, {dynamic data, Options? options, Map<String, dynamic>? queryParameters}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: path));
  }

  @override
  Future<Response<T>> createEntry<T>({required Map<String, dynamic> data}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/entries'));
  }

  @override
  Future<Response<T>> fetchGoals<T>({String? status, int? limit}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/goals'));
  }

  @override
  Future<Response<T>> fetchGoal<T>({required String id}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/goals/$id'));
  }

  @override
  Future<Response<T>> fetchMilestones<T>({required String goalId}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/goals/$goalId/milestones'));
  }

  @override
  Future<Response<T>> createMilestone<T>({required String goalId, required Map<String, dynamic> data}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/goals/$goalId/milestones'));
  }

  @override
  Future<Response<T>> updateMilestone<T>({required String goalId, required String milestoneId, required Map<String, dynamic> data}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/goals/$goalId/milestones/$milestoneId'));
  }

  @override
  Future<Response<T>> deleteMilestone<T>({required String goalId, required String milestoneId}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/goals/$goalId/milestones/$milestoneId'));
  }

  @override
  Future<Response<T>> fetchReviewSummary<T>({String? period, String? date}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/review'));
  }

  @override
  Future<Response<T>> fetchTrends<T>({String? period, int? days, int? weeks}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/review/trend'));
  }

  @override
  Future<Response<T>> fetchInsights<T>({required String period}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/review/insights'));
  }

  @override
  Future<Response<T>> updateEntry<T>({required String id, required Map<String, dynamic> data}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/entries/$id'));
  }

  @override
  Future<Response<T>> fetchBacklinks<T>({required String id}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/entries/$id/backlinks'));
  }

  @override
  Future<Response<T>> fetchEntryLinks<T>({required String id, String direction = 'both'}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/entries/$id/links'));
  }

  @override
  Future<Response<T>> createEntryLink<T>({required String id, required String targetId, required String relationType}) async {
    return Response<T>(data: null, statusCode: 201, requestOptions: RequestOptions(path: '/entries/$id/links'));
  }

  @override
  Future<Response<T>> deleteEntryLink<T>({required String id, required String linkId}) async {
    return Response<T>(data: null, statusCode: 204, requestOptions: RequestOptions(path: '/entries/$id/links/$linkId'));
  }

  @override
  Future<Response<T>> fetchKnowledgeContext<T>({required String id}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/entries/$id/knowledge-context'));
  }

  @override
  Future<Response<T>> generateAISummary<T>({required String id}) async {
    return Response<T>(data: null, statusCode: 200, requestOptions: RequestOptions(path: '/entries/$id/ai-summary'));
  }

  @override
  Future<Response<T>> fetchGoalEntries<T>({required String goalId}) async {
    return Response<T>(data: {'entries': <Map<String, dynamic>>[]} as T, statusCode: 200, requestOptions: RequestOptions(path: '/goals/$goalId/entries'));
  }
}

/// Type-aware fake that returns different responses based on type param
class _TypeAwareFakeApiClient extends _TrackingFakeApiClient {
  final Map<String?, Map<String, dynamic>?> responses;
  final bool shouldThrowForNull;
  final Map<String?, int> _fetchCounts = {};

  _TypeAwareFakeApiClient({
    required this.responses,
    this.shouldThrowForNull = false,
  });

  Map<String?, int> get fetchCounts => _fetchCounts;

  @override
  Future<Response<T>> fetchEntries<T>({
    String? type,
    String? status,
    String? tags,
    String? startDate,
    String? endDate,
    int? limit,
    int? offset,
  }) async {
    fetchCallCount++;
    _fetchCounts[type] = (_fetchCounts[type] ?? 0) + 1;

    if (type == null && shouldThrowForNull) {
      throw DioException(
        requestOptions: RequestOptions(path: '/entries'),
        type: DioExceptionType.connectionTimeout,
      );
    }

    final response = responses[type];
    return Response<T>(
      data: response as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries'),
    );
  }
}

/// Conditional fake that can be toggled to throw or succeed
class _ConditionalFakeApiClient extends _TrackingFakeApiClient {
  final Map<String, dynamic> Function() onResponse;

  _ConditionalFakeApiClient({required this.onResponse});

  @override
  Future<Response<T>> fetchEntries<T>({
    String? type,
    String? status,
    String? tags,
    String? startDate,
    String? endDate,
    int? limit,
    int? offset,
  }) async {
    fetchCallCount++;
    final response = onResponse();
    return Response<T>(
      data: response as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries'),
    );
  }
}
