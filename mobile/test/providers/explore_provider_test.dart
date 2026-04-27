import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/providers/auth_provider.dart';
import 'package:growth_assistant/providers/explore_provider.dart';
import 'package:growth_assistant/services/api_client.dart';

void main() {
  // ============================================================
  // ExploreState tests
  // ============================================================
  group('ExploreState', () {
    test('initial state has defaults', () {
      const state = ExploreState();

      expect(state.entries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.searchQuery, '');
      expect(state.searchHistory, isEmpty);
      expect(state.selectedIds, isEmpty);
      expect(state.isMultiSelectMode, false);
    });

    test('copyWith preserves unchanged fields', () {
      const state = ExploreState(isLoading: true);
      final copied = state.copyWith(error: 'Network error');

      expect(copied.isLoading, true);
      expect(copied.error, 'Network error');
      expect(copied.entries, isEmpty);
      expect(copied.searchQuery, '');
    });

    test('copyWith can update entries', () {
      const state = ExploreState();
      final entries = [_makeEntry('1')];
      final copied = state.copyWith(entries: entries);

      expect(copied.entries, hasLength(1));
      expect(copied.entries.first.id, '1');
    });
  });

  // ============================================================
  // BatchResult tests
  // ============================================================
  group('BatchResult', () {
    test('initial state has empty lists', () {
      const result = BatchResult();

      expect(result.successIds, isEmpty);
      expect(result.failedItems, isEmpty);
      expect(result.hasFailures, false);
    });

    test('hasFailures is true when there are failed items', () {
      const result = BatchResult(
        failedItems: [BatchFailureItem(id: '1', error: 'not found')],
      );

      expect(result.hasFailures, true);
    });

    test('copyWith preserves unchanged fields', () {
      const result = BatchResult(successIds: ['a']);
      final copied = result.copyWith(failedItems: [
        const BatchFailureItem(id: 'b', error: 'error'),
      ]);

      expect(copied.successIds, ['a']);
      expect(copied.failedItems, hasLength(1));
      expect(copied.hasFailures, true);
    });
  });

  // ============================================================
  // ExploreNotifier — state initialization
  // ============================================================
  group('ExploreNotifier', () {
    test('initial build returns default state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(exploreProvider);

      expect(state.entries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.searchQuery, '');
      expect(state.searchHistory, isEmpty);
      expect(state.selectedIds, isEmpty);
      expect(state.isMultiSelectMode, false);
    });
  });

  // ============================================================
  // Search history logic (no API needed)
  // ============================================================
  group('Search History', () {
    late ProviderContainer container;

    setUp(() {
      container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(_FakeApiClient()),
      ]);
    });

    tearDown(() => container.dispose());

    test('addSearchHistory adds to front', () {
      final notifier = container.read(exploreProvider.notifier);
      notifier.addSearchHistory('flutter');
      notifier.addSearchHistory('dart');

      expect(notifier.state.searchHistory, ['dart', 'flutter']);
    });

    test('addSearchHistory deduplicates', () {
      final notifier = container.read(exploreProvider.notifier);
      notifier.addSearchHistory('flutter');
      notifier.addSearchHistory('dart');
      notifier.addSearchHistory('flutter');

      expect(notifier.state.searchHistory, ['flutter', 'dart']);
    });

    test('addSearchHistory truncates to 10 items', () {
      final notifier = container.read(exploreProvider.notifier);
      for (var i = 0; i < 15; i++) {
        notifier.addSearchHistory('query-$i');
      }

      expect(notifier.state.searchHistory, hasLength(10));
      expect(notifier.state.searchHistory.first, 'query-14');
    });

    test('addSearchHistory ignores empty query', () {
      final notifier = container.read(exploreProvider.notifier);
      notifier.addSearchHistory('');

      expect(notifier.state.searchHistory, isEmpty);
    });

    test('addSearchHistory ignores whitespace-only query', () {
      final notifier = container.read(exploreProvider.notifier);
      notifier.addSearchHistory('   ');

      expect(notifier.state.searchHistory, isEmpty);
    });

    test('removeSearchHistory removes item', () {
      final notifier = container.read(exploreProvider.notifier);
      notifier.addSearchHistory('flutter');
      notifier.addSearchHistory('dart');
      notifier.removeSearchHistory('flutter');

      expect(notifier.state.searchHistory, ['dart']);
    });

    test('empty search history does not crash on remove', () {
      final notifier = container.read(exploreProvider.notifier);
      notifier.removeSearchHistory('nonexistent');

      expect(notifier.state.searchHistory, isEmpty);
    });
  });

  // ============================================================
  // Multi-select logic (no API needed)
  // ============================================================
  group('Multi-select', () {
    late ProviderContainer container;

    setUp(() {
      container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(_FakeApiClient()),
      ]);
    });

    tearDown(() => container.dispose());

    test('toggleMultiSelectMode switches mode', () {
      final notifier = container.read(exploreProvider.notifier);
      expect(notifier.state.isMultiSelectMode, false);

      notifier.toggleMultiSelectMode();
      expect(notifier.state.isMultiSelectMode, true);

      notifier.toggleMultiSelectMode();
      expect(notifier.state.isMultiSelectMode, false);
    });

    test('toggleMultiSelectMode clears selection', () {
      final notifier = container.read(exploreProvider.notifier);
      // Enter multi-select
      notifier.toggleMultiSelectMode();
      notifier.toggleSelection('id-1');
      expect(notifier.state.selectedIds, isNotEmpty);

      // Exit multi-select clears selection
      notifier.toggleMultiSelectMode();
      expect(notifier.state.selectedIds, isEmpty);
    });

    test('toggleSelection adds and removes', () {
      final notifier = container.read(exploreProvider.notifier);
      notifier.toggleSelection('id-1');
      expect(notifier.state.selectedIds.contains('id-1'), true);

      notifier.toggleSelection('id-1');
      expect(notifier.state.selectedIds.contains('id-1'), false);
    });

    test('selectAll selects all entries', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(entriesResponse: _makeEntriesResponse(['1', '2', '3'])),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries();
      notifier.selectAll();

      expect(notifier.state.selectedIds, hasLength(3));
    });

    test('clearSelection clears all', () {
      final notifier = container.read(exploreProvider.notifier);
      notifier.toggleSelection('id-1');
      notifier.toggleSelection('id-2');
      notifier.clearSelection();

      expect(notifier.state.selectedIds, isEmpty);
    });
  });

  // ============================================================
  // API-backed tests with mock
  // ============================================================
  group('API Integration', () {
    test('loadEntries success populates entries', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(entriesResponse: _makeEntriesResponse(['1', '2'])),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries();

      expect(notifier.state.entries, hasLength(2));
      expect(notifier.state.isLoading, false);
      expect(notifier.state.error, isNull);
    });

    test('loadEntries with type filter', () async {
      final api = _FakeApiClient(
        entriesResponse: _makeEntriesResponse(['1']),
        expectedQueryParams: {'type': 'inbox'},
      );
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(api),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries(type: 'inbox');

      expect(notifier.state.entries, hasLength(1));
    });

    test('loadEntries error sets error message', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(shouldThrow: true),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries();

      expect(notifier.state.entries, isEmpty);
      expect(notifier.state.error, isNotNull);
      expect(notifier.state.isLoading, false);
    });

    test('searchEntries success populates entries', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(searchResponse: _makeEntriesResponse(['1'])),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.searchEntries('test');

      expect(notifier.state.entries, hasLength(1));
      expect(notifier.state.searchQuery, 'test');
      expect(notifier.state.searchHistory, ['test']);
    });

    test('searchEntries with empty query does nothing', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(_FakeApiClient()),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.searchEntries('');

      expect(notifier.state.searchQuery, '');
      expect(notifier.state.searchHistory, isEmpty);
    });

    test('searchEntries failure does not add to history', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(shouldThrow: true),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.searchEntries('test');

      expect(notifier.state.searchHistory, isEmpty);
      expect(notifier.state.error, isNotNull);
    });

    test('clearSearch resets search query', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(searchResponse: _makeEntriesResponse(['1'])),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.searchEntries('test');
      notifier.clearSearch();

      expect(notifier.state.searchQuery, '');
      expect(notifier.state.entries, isEmpty);
    });

    test('deleteEntry removes from list', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(entriesResponse: _makeEntriesResponse(['1', '2'])),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries();
      expect(notifier.state.entries, hasLength(2));

      final success = await notifier.deleteEntry('1');
      expect(success, true);
      expect(notifier.state.entries, hasLength(1));
      expect(notifier.state.entries.first.id, '2');
    });

    test('deleteEntry failure returns false', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(shouldThrow: true),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      final success = await notifier.deleteEntry('nonexistent');

      expect(success, false);
      expect(notifier.state.error, isNotNull);
    });

    test('updateCategory updates local entry', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(entriesResponse: _makeEntriesResponse(['1'])),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries();

      final success = await notifier.updateCategory('1', 'note');
      expect(success, true);
      expect(notifier.state.entries.first.category, 'note');
    });

    test('batchDelete success removes all', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(entriesResponse: _makeEntriesResponse(['1', '2', '3'])),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries();

      final result = await notifier.batchDelete(['1', '2', '3']);
      expect(result.successIds, hasLength(3));
      expect(result.hasFailures, false);
      expect(notifier.state.entries, isEmpty);
    });

    test('batchDelete partial failure preserves failed items', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(
            entriesResponse: _makeEntriesResponse(['1', '2', '3']),
            failOnIds: {'2'},
          ),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries();

      final result = await notifier.batchDelete(['1', '2', '3']);
      expect(result.successIds, hasLength(2));
      expect(result.failedItems, hasLength(1));
      expect(result.failedItems.first.id, '2');
      expect(notifier.state.entries, hasLength(1));
      expect(notifier.state.entries.first.id, '2');
    });

    test('batchUpdateCategory success updates all', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(entriesResponse: _makeEntriesResponse(['1', '2'])),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries();

      final result =
          await notifier.batchUpdateCategory(['1', '2'], 'project');
      expect(result.successIds, hasLength(2));
      expect(result.hasFailures, false);
      expect(notifier.state.entries.every((e) => e.category == 'project'), true);
    });

    test('batchUpdateCategory partial failure', () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(
          _FakeApiClient(
            entriesResponse: _makeEntriesResponse(['1', '2']),
            failOnIds: {'1'},
          ),
        ),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);
      await notifier.loadEntries();

      final result =
          await notifier.batchUpdateCategory(['1', '2'], 'note');
      expect(result.successIds, ['2']);
      expect(result.failedItems, hasLength(1));
      expect(result.failedItems.first.id, '1');
      // Only '2' was updated locally
      expect(
        notifier.state.entries.firstWhere((e) => e.id == '2').category,
        'note',
      );
    });
  });

  // ============================================================
  // Smoke: full flow
  // ============================================================
  group('Smoke: Full Flow', () {
    test('load → search → delete → refresh', () async {
      final api = _FakeApiClient(
        entriesResponse: _makeEntriesResponse(['1', '2', '3']),
        searchResponse: _makeEntriesResponse(['1', '2']),
      );
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(api),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(exploreProvider.notifier);

      // 1. Load entries
      await notifier.loadEntries();
      expect(notifier.state.entries, hasLength(3));

      // 2. Search
      await notifier.searchEntries('test');
      expect(notifier.state.entries, hasLength(2));
      expect(notifier.state.searchHistory, ['test']);

      // 3. Delete
      final deleted = await notifier.deleteEntry('1');
      expect(deleted, true);
      expect(notifier.state.entries, hasLength(1));

      // 4. Clear search → reload
      notifier.clearSearch();
      expect(notifier.state.searchQuery, '');

      // 5. Reload
      await notifier.loadEntries();
      expect(notifier.state.entries, hasLength(3));
    });
  });
}

// ============================================================
// Helpers
// ============================================================

Entry _makeEntry(String id, {String category = 'task'}) {
  return Entry(
    id: id,
    title: 'Entry $id',
    category: category,
  );
}

Map<String, dynamic> _makeEntriesResponse(List<String> ids) {
  return {
    'entries': ids
        .map((id) => _makeEntry(id).toJson())
        .toList(),
  };
}

/// Fake ApiClient for testing
class _FakeApiClient implements ApiClient {
  final Map<String, dynamic>? entriesResponse;
  final Map<String, dynamic>? searchResponse;
  final bool shouldThrow;
  final Set<String>? failOnIds;
  final Map<String, String>? expectedQueryParams;

  _FakeApiClient({
    this.entriesResponse,
    this.searchResponse,
    this.shouldThrow = false,
    this.failOnIds,
    this.expectedQueryParams,
  });

  @override
  Dio get dio => Dio();

  void _checkParams(Map<String, String> actual) {
    if (expectedQueryParams == null) return;
    for (final entry in expectedQueryParams!.entries) {
      expect(actual[entry.key], entry.value,
          reason: 'Query param "${entry.key}" mismatch');
    }
  }

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
    if (shouldThrow) {
      throw DioException(
        requestOptions: RequestOptions(path: '/entries'),
        type: DioExceptionType.connectionTimeout,
      );
    }
    // 验证传入的参数
    final params = <String, String>{};
    if (type != null) params['type'] = type;
    if (status != null) params['status'] = status;
    if (tags != null) params['tags'] = tags;
    if (startDate != null) params['start_date'] = startDate;
    if (endDate != null) params['end_date'] = endDate;
    _checkParams(params);

    return Response<T>(
      data: entriesResponse as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries'),
    );
  }

  @override
  Future<Response<T>> searchEntries<T>({
    required String query,
    int? limit,
  }) async {
    if (shouldThrow) {
      throw DioException(
        requestOptions: RequestOptions(path: '/entries/search/query'),
        type: DioExceptionType.connectionTimeout,
      );
    }
    return Response<T>(
      data: (searchResponse ?? entriesResponse) as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries/search/query'),
    );
  }

  @override
  Future<Response<T>> deleteEntry<T>({required String id}) async {
    if (failOnIds != null && failOnIds!.contains(id)) {
      throw DioException(
        requestOptions: RequestOptions(path: '/entries/$id'),
        response: Response(
          statusCode: 404,
          requestOptions: RequestOptions(path: '/entries/$id'),
          data: {'detail': 'Not found'},
        ),
        type: DioExceptionType.badResponse,
      );
    }
    if (shouldThrow) {
      throw DioException(
        requestOptions: RequestOptions(path: '/entries/$id'),
        type: DioExceptionType.connectionTimeout,
      );
    }
    return Response<T>(
      data: {'success': true, 'message': 'Deleted'} as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries/$id'),
    );
  }

  @override
  Future<Response<T>> updateEntryCategory<T>({
    required String id,
    required String category,
  }) async {
    if (failOnIds != null && failOnIds!.contains(id)) {
      throw DioException(
        requestOptions: RequestOptions(path: '/entries/$id'),
        response: Response(
          statusCode: 404,
          requestOptions: RequestOptions(path: '/entries/$id'),
          data: {'detail': 'Not found'},
        ),
        type: DioExceptionType.badResponse,
      );
    }
    if (shouldThrow) {
      throw DioException(
        requestOptions: RequestOptions(path: '/entries/$id'),
        type: DioExceptionType.connectionTimeout,
      );
    }
    return Response<T>(
      data: {'success': true, 'message': 'Updated'} as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries/$id'),
    );
  }

  // ---- 实现 ApiClient 接口的通用方法 ----
  @override
  Future<Response<T>> get<T>(String path,
      {Map<String, dynamic>? queryParameters, Options? options}) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: path),
    );
  }

  @override
  Future<Response<T>> post<T>(String path,
      {dynamic data, Options? options,
      Map<String, dynamic>? queryParameters}) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: path),
    );
  }

  @override
  Future<Response<T>> put<T>(String path,
      {dynamic data, Options? options,
      Map<String, dynamic>? queryParameters}) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: path),
    );
  }

  @override
  Future<Response<T>> delete<T>(String path,
      {dynamic data, Options? options,
      Map<String, dynamic>? queryParameters}) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: path),
    );
  }

  // ---- F165: 新增 API 方法的 mock 实现 ----

  @override
  Future<Response<T>> createEntry<T>({required Map<String, dynamic> data}) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries'),
    );
  }

  @override
  Future<Response<T>> fetchGoals<T>({
    String? status,
    int? limit,
  }) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/goals'),
    );
  }

  @override
  Future<Response<T>> fetchGoal<T>({required String id}) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/goals/$id'),
    );
  }

  @override
  Future<Response<T>> fetchMilestones<T>({required String goalId}) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/goals/$goalId/milestones'),
    );
  }

  @override
  Future<Response<T>> createMilestone<T>({
    required String goalId,
    required Map<String, dynamic> data,
  }) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/goals/$goalId/milestones'),
    );
  }

  @override
  Future<Response<T>> updateMilestone<T>({
    required String goalId,
    required String milestoneId,
    required Map<String, dynamic> data,
  }) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/goals/$goalId/milestones/$milestoneId'),
    );
  }

  @override
  Future<Response<T>> deleteMilestone<T>({
    required String goalId,
    required String milestoneId,
  }) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/goals/$goalId/milestones/$milestoneId'),
    );
  }

  @override
  Future<Response<T>> fetchReviewSummary<T>({
    String? period,
    String? date,
  }) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/review/${period ?? 'weekly'}'),
    );
  }

  @override
  Future<Response<T>> fetchTrends<T>({
    String? period,
    int? days,
    int? weeks,
  }) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/review/trend'),
    );
  }

  @override
  Future<Response<T>> fetchInsights<T>({required String period}) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/review/insights'),
    );
  }

  // ---- F172: Entry Interaction API Methods mock ----

  @override
  Future<Response<T>> updateEntry<T>({
    required String id,
    required Map<String, dynamic> data,
  }) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries/$id'),
    );
  }

  @override
  Future<Response<T>> fetchBacklinks<T>({required String id}) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries/$id/backlinks'),
    );
  }

  @override
  Future<Response<T>> fetchEntryLinks<T>({
    required String id,
    String direction = 'both',
  }) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries/$id/links'),
    );
  }

  @override
  Future<Response<T>> createEntryLink<T>({
    required String id,
    required String targetId,
    required String relationType,
  }) async {
    return Response<T>(
      data: null,
      statusCode: 201,
      requestOptions: RequestOptions(path: '/entries/$id/links'),
    );
  }

  @override
  Future<Response<T>> deleteEntryLink<T>({
    required String id,
    required String linkId,
  }) async {
    return Response<T>(
      data: null,
      statusCode: 204,
      requestOptions: RequestOptions(path: '/entries/$id/links/$linkId'),
    );
  }

  @override
  Future<Response<T>> fetchKnowledgeContext<T>({required String id}) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries/$id/knowledge-context'),
    );
  }

  @override
  Future<Response<T>> generateAISummary<T>({required String id}) async {
    return Response<T>(
      data: null,
      statusCode: 200,
      requestOptions: RequestOptions(path: '/entries/$id/ai-summary'),
    );
  }
}
