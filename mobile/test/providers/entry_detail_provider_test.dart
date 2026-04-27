import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/providers/auth_provider.dart';
import 'package:growth_assistant/providers/entry_provider.dart';
import 'package:growth_assistant/services/api_client.dart';

void main() {
  // ================================================================
  // EntryDetailState 新增字段测试
  // ================================================================
  group('EntryDetailState (F173)', () {
    test('initial state has all new fields with correct defaults', () {
      const state = EntryDetailState();

      // 原有字段
      expect(state.entry, isNull);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.notFound, false);

      // 新增字段
      expect(state.isEditing, false);
      expect(state.isSaving, false);
      expect(state.isGeneratingSummary, false);
      expect(state.summaryText, isNull);
      expect(state.summaryCached, false);
      expect(state.backlinks, isEmpty);
      expect(state.entryLinks, isEmpty);
      expect(state.knowledgeContext, isNull);
      expect(state.searchResults, isEmpty);
      expect(state.isSearching, false);
    });

    test('copyWith preserves unchanged fields', () {
      const state = EntryDetailState(
        isEditing: true,
        isSaving: true,
      );
      final copied = state.copyWith(isGeneratingSummary: true);

      expect(copied.isEditing, true);
      expect(copied.isSaving, true);
      expect(copied.isGeneratingSummary, true);
      expect(copied.isSearching, false);
    });

    test('copyWith can update all new fields', () {
      const state = EntryDetailState();
      final backlinks = [
        BacklinkItem(id: 'b1', title: 'Backlink 1'),
      ];
      final links = [
        EntryLinkItem(
          linkId: 'l1',
          sourceId: 's1',
          targetId: 't1',
          relationType: 'related',
        ),
      ];
      final searchResults = [_makeEntry('sr1')];
      final knowledgeCtx = KnowledgeContextData(
        nodes: [{'id': 'n1'}],
        edges: [],
        centerConcepts: ['concept1'],
      );

      final copied = state.copyWith(
        isEditing: true,
        isSaving: true,
        isGeneratingSummary: true,
        summaryText: 'AI summary text',
        summaryCached: true,
        backlinks: backlinks,
        entryLinks: links,
        knowledgeContext: knowledgeCtx,
        searchResults: searchResults,
        isSearching: true,
      );

      expect(copied.isEditing, true);
      expect(copied.isSaving, true);
      expect(copied.isGeneratingSummary, true);
      expect(copied.summaryText, 'AI summary text');
      expect(copied.summaryCached, true);
      expect(copied.backlinks, hasLength(1));
      expect(copied.entryLinks, hasLength(1));
      expect(copied.knowledgeContext, isNotNull);
      expect(copied.knowledgeContext!.centerConcepts, ['concept1']);
      expect(copied.searchResults, hasLength(1));
      expect(copied.isSearching, true);
    });

    test('copyWith clearError flag clears error', () {
      const state = EntryDetailState(error: 'some error');
      final copied = state.copyWith(clearError: true);

      expect(copied.error, isNull);
    });

    test('copyWith clearSummaryText flag clears summaryText', () {
      const state = EntryDetailState(summaryText: 'old summary');
      final copied = state.copyWith(clearSummaryText: true);

      expect(copied.summaryText, isNull);
    });

    test('copyWith clearKnowledgeContext flag clears knowledgeContext', () {
      final ctx = KnowledgeContextData(
        nodes: [],
        edges: [],
        centerConcepts: [],
      );
      final state = EntryDetailState(knowledgeContext: ctx);
      final copied = state.copyWith(clearKnowledgeContext: true);

      expect(copied.knowledgeContext, isNull);
    });

    test('copyWith creates new list instances (immutable replacement)', () {
      const state = EntryDetailState();
      final newBacklinks = [BacklinkItem(id: 'b1', title: 'B1')];
      final copied = state.copyWith(backlinks: newBacklinks);

      expect(identical(copied.backlinks, state.backlinks), false);
      expect(copied.backlinks, isNot(same(state.backlinks)));
    });
  });

  // ================================================================
  // BacklinkItem 模型测试
  // ================================================================
  group('BacklinkItem', () {
    test('fromJson parses correctly', () {
      final item = BacklinkItem.fromJson({
        'id': 'b1',
        'title': 'Test Backlink',
        'category': 'task',
        'relation_type': 'related',
        'created_at': '2024-01-01',
      });

      expect(item.id, 'b1');
      expect(item.title, 'Test Backlink');
      expect(item.category, 'task');
      expect(item.relationType, 'related');
      expect(item.createdAt, '2024-01-01');
    });

    test('fromJson handles missing optional fields', () {
      final item = BacklinkItem.fromJson({
        'id': 'b2',
        'title': 'Minimal',
      });

      expect(item.id, 'b2');
      expect(item.category, isNull);
      expect(item.relationType, isNull);
      expect(item.createdAt, isNull);
    });
  });

  // ================================================================
  // EntryLinkItem 模型测试
  // ================================================================
  group('EntryLinkItem', () {
    test('fromJson parses with target_entry', () {
      final item = EntryLinkItem.fromJson({
        'link_id': 'l1',
        'source_id': 's1',
        'target_id': 't1',
        'relation_type': 'related',
        'target_entry': {
          'id': 't1',
          'title': 'Target',
          'category': 'task',
        },
      });

      expect(item.linkId, 'l1');
      expect(item.sourceId, 's1');
      expect(item.targetId, 't1');
      expect(item.relationType, 'related');
      expect(item.targetEntry, isNotNull);
      expect(item.targetEntry!.id, 't1');
      expect(item.sourceEntry, isNull);
    });

    test('fromJson uses id as fallback for link_id', () {
      final item = EntryLinkItem.fromJson({
        'id': 'fallback-id',
        'source_id': 's1',
        'target_id': 't1',
        'relation_type': 'related',
      });

      expect(item.linkId, 'fallback-id');
    });
  });

  // ================================================================
  // KnowledgeContextData 模型测试
  // ================================================================
  group('KnowledgeContextData', () {
    test('fromJson parses correctly', () {
      final ctx = KnowledgeContextData.fromJson({
        'nodes': [{'id': 'n1', 'label': 'Node 1'}],
        'edges': [{'source': 'n1', 'target': 'n2'}],
        'center_concepts': ['concept1', 'concept2'],
      });

      expect(ctx.nodes, hasLength(1));
      expect(ctx.edges, hasLength(1));
      expect(ctx.centerConcepts, ['concept1', 'concept2']);
    });

    test('fromJson handles null/empty data', () {
      final ctx = KnowledgeContextData.fromJson({});

      expect(ctx.nodes, isEmpty);
      expect(ctx.edges, isEmpty);
      expect(ctx.centerConcepts, isEmpty);
    });
  });

  // ================================================================
  // Family Provider 隔离测试
  // ================================================================
  group('EntryDetailProvider family isolation', () {
    late ProviderContainer container;

    setUp(() {
      container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(MockApiClient()),
        ],
      );
    });

    tearDown(() {
      container.dispose();
    });

    test('different entryId creates independent state instances', () {
      final stateA = container.read(entryDetailProvider('entry-a'));
      final stateB = container.read(entryDetailProvider('entry-b'));

      // Both start with default values
      expect(stateA.entry, isNull);
      expect(stateB.entry, isNull);
      expect(stateA.isEditing, false);
      expect(stateB.isEditing, false);

      // 修改其中一个不应影响另一个
      container
          .read(entryDetailProvider('entry-a').notifier)
          .state = const EntryDetailState(isEditing: true);

      expect(container.read(entryDetailProvider('entry-a')).isEditing, true);
      expect(container.read(entryDetailProvider('entry-b')).isEditing, false);
    });

    test('same entryId returns same state', () {
      // family provider 用相同 arg 多次 read 返回同一个 state
      container
          .read(entryDetailProvider('entry-x').notifier)
          .state = const EntryDetailState(isEditing: true);

      final state1 = container.read(entryDetailProvider('entry-x'));
      final state2 = container.read(entryDetailProvider('entry-x'));

      expect(identical(state1, state2), true);
      expect(state1.isEditing, true);
    });

    test('nested navigation: detail A -> detail B -> back to A, states independent', () {
      // 设置详情 A 为编辑模式
      container
          .read(entryDetailProvider('entry-a').notifier)
          .toggleEdit();
      expect(container.read(entryDetailProvider('entry-a')).isEditing, true);

      // 导航到详情 B，修改其状态
      container
          .read(entryDetailProvider('entry-b').notifier)
          .state = const EntryDetailState(isGeneratingSummary: true);

      // 详情 A 的状态不应被影响
      expect(container.read(entryDetailProvider('entry-a')).isEditing, true);
      expect(
        container.read(entryDetailProvider('entry-b')).isGeneratingSummary,
        true,
      );

      // 详情 B 的 isEditing 应保持默认
      expect(container.read(entryDetailProvider('entry-b')).isEditing, false);
    });
  });

  // ================================================================
  // EntryDetailNotifier 方法测试（使用 mock override）
  // ================================================================
  group('EntryDetailNotifier methods', () {
    late ProviderContainer container;
    late MockApiClient mockApiClient;

    setUp(() {
      mockApiClient = MockApiClient();
      container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );
      addTearDown(container.dispose);
    });

    // ---- toggleEdit ----
    test('toggleEdit switches isEditing state', () {
      expect(
        container.read(entryDetailProvider('test-id')).isEditing,
        false,
      );

      container
          .read(entryDetailProvider('test-id').notifier)
          .toggleEdit();

      expect(
        container.read(entryDetailProvider('test-id')).isEditing,
        true,
      );

      container
          .read(entryDetailProvider('test-id').notifier)
          .toggleEdit();

      expect(
        container.read(entryDetailProvider('test-id')).isEditing,
        false,
      );
    });

    // ---- updateEntry 成功后 GET 刷新 + invalidate EntryListProvider ----
    test('updateEntry success: PUT then GET refreshes entry + invalidates list', () async {
      final entry = _makeEntry('test-id', title: 'Original');

      // 模拟 PUT 成功（返回 SuccessResponse）
      mockApiClient.updateEntryFn = ({required id, required data}) async {
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/$id'),
          data: {'message': 'success'},
          statusCode: 200,
        );
      };

      // 模拟 GET 返回更新后的 entry
      mockApiClient.getFn = (path, {queryParameters, options}) async {
        if (path == '/entries/test-id') {
          return Response<Map<String, dynamic>>(
            requestOptions: RequestOptions(path: path),
            data: {
              'id': 'test-id',
              'title': 'Updated Title',
              'category': 'task',
              'status': 'doing',
            },
            statusCode: 200,
          );
        }
        throw Exception('Unexpected path: $path');
      };

      // 设置初始 entry
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(entry: entry);

      await container
          .read(entryDetailProvider('test-id').notifier)
          .updateEntry({'title': 'Updated Title'});

      final state = container.read(entryDetailProvider('test-id'));
      expect(state.isSaving, false);
      expect(state.isEditing, false);
      expect(state.entry, isNotNull);
      expect(state.entry!.title, 'Updated Title');
      expect(state.error, isNull);
    });

    // ---- updateEntry 失败状态转换 ----
    test('updateEntry failure sets error and stops saving', () async {
      mockApiClient.updateEntryFn = ({required id, required data}) async {
        throw DioException(
          requestOptions: RequestOptions(path: '/entries/$id'),
          response: Response(
            requestOptions: RequestOptions(path: '/entries/$id'),
            statusCode: 500,
            data: {'detail': 'Internal Server Error'},
          ),
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .updateEntry({'title': 'Fail'});

      final state = container.read(entryDetailProvider('test-id'));
      expect(state.isSaving, false);
      expect(state.error, isNotNull);
    });

    // ---- generateSummary 成功 ----
    test('generateSummary success updates summaryText', () async {
      mockApiClient.generateAISummaryFn = ({required id}) async {
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/$id/ai-summary'),
          data: {
            'summary': 'This is an AI-generated summary',
            'cached': false,
          },
          statusCode: 200,
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .generateSummary();

      final state = container.read(entryDetailProvider('test-id'));
      expect(state.isGeneratingSummary, false);
      expect(state.summaryText, 'This is an AI-generated summary');
      expect(state.summaryCached, false);
    });

    // ---- generateSummary 失败 ----
    test('generateSummary failure sets error', () async {
      mockApiClient.generateAISummaryFn = ({required id}) async {
        throw DioException(
          requestOptions: RequestOptions(path: '/entries/$id/ai-summary'),
          response: Response(
            requestOptions: RequestOptions(path: '/entries/$id/ai-summary'),
            statusCode: 500,
            data: {'detail': 'Server Error'},
          ),
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .generateSummary();

      final state = container.read(entryDetailProvider('test-id'));
      expect(state.isGeneratingSummary, false);
      expect(state.error, isNotNull);
      expect(state.summaryText, isNull);
    });

    // ---- generateSummary summary=null ----
    test('generateSummary with null summary sets error', () async {
      mockApiClient.generateAISummaryFn = ({required id}) async {
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/$id/ai-summary'),
          data: {'summary': null, 'cached': false},
          statusCode: 200,
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .generateSummary();

      final state = container.read(entryDetailProvider('test-id'));
      expect(state.isGeneratingSummary, false);
      expect(state.error, 'AI 摘要生成返回空结果');
    });

    // ---- loadBacklinks ----
    test('loadBacklinks loads data into state', () async {
      mockApiClient.fetchBacklinksFn = ({required id}) async {
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/$id/backlinks'),
          data: {
            'backlinks': [
              {
                'id': 'bl1',
                'title': 'Linked Entry',
                'category': 'task',
                'relation_type': 'related',
              },
            ],
          },
          statusCode: 200,
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .loadBacklinks();

      final state = container.read(entryDetailProvider('test-id'));
      expect(state.backlinks, hasLength(1));
      expect(state.backlinks.first.id, 'bl1');
      expect(state.backlinks.first.title, 'Linked Entry');
    });

    // ---- loadEntryLinks ----
    test('loadEntryLinks loads data into state', () async {
      mockApiClient.fetchEntryLinksFn = ({required id, direction = 'both'}) async {
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/$id/links'),
          data: {
            'links': [
              {
                'link_id': 'lk1',
                'source_id': 'test-id',
                'target_id': 'target1',
                'relation_type': 'related',
              },
            ],
          },
          statusCode: 200,
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .loadEntryLinks();

      final state = container.read(entryDetailProvider('test-id'));
      expect(state.entryLinks, hasLength(1));
      expect(state.entryLinks.first.linkId, 'lk1');
      expect(state.entryLinks.first.targetId, 'target1');
    });

    // ---- createLink 成功 ----
    test('createLink success refreshes entryLinks', () async {
      var createLinkCalled = false;

      mockApiClient.createEntryLinkFn =
          ({required id, required targetId, required relationType}) async {
        createLinkCalled = true;
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/$id/links'),
          statusCode: 201,
          data: {
            'link_id': 'new-link',
            'source_id': id,
            'target_id': targetId,
            'relation_type': relationType,
          },
        );
      };

      // fetchEntryLinks 在 createLink 后被调用
      mockApiClient.fetchEntryLinksFn =
          ({required id, direction = 'both'}) async {
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/$id/links'),
          data: {
            'links': [
              {
                'link_id': 'new-link',
                'source_id': 'test-id',
                'target_id': 'target-id',
                'relation_type': 'related',
              },
            ],
          },
          statusCode: 200,
        );
      };

      final result = await container
          .read(entryDetailProvider('test-id').notifier)
          .createLink(targetId: 'target-id', relationType: 'related');

      expect(result, true);
      expect(createLinkCalled, true);
      final state = container.read(entryDetailProvider('test-id'));
      expect(state.entryLinks, hasLength(1));
      expect(state.error, isNull);
    });

    // ---- createLink 400 自关联 ----
    test('createLink 400 self-link error message', () async {
      mockApiClient.createEntryLinkFn =
          ({required id, required targetId, required relationType}) async {
        throw DioException(
          requestOptions: RequestOptions(path: '/entries/$id/links'),
          response: Response(
            requestOptions: RequestOptions(path: '/entries/$id/links'),
            statusCode: 400,
            data: {'detail': 'Cannot link to self'},
          ),
        );
      };

      final result = await container
          .read(entryDetailProvider('test-id').notifier)
          .createLink(targetId: 'test-id', relationType: 'related');

      expect(result, false);
      final state = container.read(entryDetailProvider('test-id'));
      expect(state.error, '不能关联自身');
    });

    // ---- createLink 409 重复关联 ----
    test('createLink 409 duplicate link error message', () async {
      mockApiClient.createEntryLinkFn =
          ({required id, required targetId, required relationType}) async {
        throw DioException(
          requestOptions: RequestOptions(path: '/entries/$id/links'),
          response: Response(
            requestOptions: RequestOptions(path: '/entries/$id/links'),
            statusCode: 409,
            data: {'detail': 'Link already exists'},
          ),
        );
      };

      final result = await container
          .read(entryDetailProvider('test-id').notifier)
          .createLink(targetId: 'target-id', relationType: 'related');

      expect(result, false);
      final state = container.read(entryDetailProvider('test-id'));
      expect(state.error, '关联已存在');
    });

    // ---- createLink 参数验证 ----
    test('createLink passes correct target_id and relation_type', () async {
      String? capturedTargetId;
      String? capturedRelationType;

      mockApiClient.createEntryLinkFn =
          ({required id, required targetId, required relationType}) async {
        capturedTargetId = targetId;
        capturedRelationType = relationType;
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/$id/links'),
          statusCode: 201,
          data: {},
        );
      };

      mockApiClient.fetchEntryLinksFn =
          ({required id, direction = 'both'}) async {
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/$id/links'),
          data: {'links': <dynamic>[]},
          statusCode: 200,
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .createLink(targetId: 'target-xyz', relationType: 'prerequisite');

      expect(capturedTargetId, 'target-xyz');
      expect(capturedRelationType, 'prerequisite');
    });

    // ---- deleteLink ----
    test('deleteLink refreshes entryLinks after deletion', () async {
      var deleteCalled = false;

      mockApiClient.deleteEntryLinkFn =
          ({required id, required linkId}) async {
        deleteCalled = true;
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/$id/links/$linkId'),
          statusCode: 204,
          data: null,
        );
      };

      // 先设置初始的 entryLinks
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entryLinks: [
          EntryLinkItem(
            linkId: 'link-to-delete',
            sourceId: 'test-id',
            targetId: 'target1',
            relationType: 'related',
          ),
        ],
      );

      mockApiClient.fetchEntryLinksFn =
          ({required id, direction = 'both'}) async {
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/$id/links'),
          data: {'links': <dynamic>[]},
          statusCode: 200,
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .deleteLink(linkId: 'link-to-delete');

      expect(deleteCalled, true);
      final state = container.read(entryDetailProvider('test-id'));
      expect(state.entryLinks, isEmpty);
    });

    // ---- fetchKnowledgeContext ----
    test('fetchKnowledgeContext loads data into state', () async {
      mockApiClient.fetchKnowledgeContextFn = ({required id}) async {
        return Response<Map<String, dynamic>>(
          requestOptions:
              RequestOptions(path: '/entries/$id/knowledge-context'),
          data: {
            'nodes': [
              {'name': 'Flutter', 'mastery': 'intermediate', 'entry_count': 5},
              {'name': 'Dart', 'mastery': 'advanced', 'entry_count': 3},
            ],
            'edges': [
              {'source': 'Flutter', 'target': 'Dart', 'type': 'related'},
            ],
            'center_concepts': ['Flutter'],
          },
          statusCode: 200,
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .fetchKnowledgeContext();

      final state = container.read(entryDetailProvider('test-id'));
      expect(state.knowledgeContext, isNotNull);
      expect(state.knowledgeContext!.nodes, hasLength(2));
      expect(state.knowledgeContext!.edges, hasLength(1));
      expect(state.knowledgeContext!.centerConcepts, ['Flutter']);
    });

    test('fetchKnowledgeContext failure sets error', () async {
      mockApiClient.fetchKnowledgeContextFn = ({required id}) async {
        throw DioException(
          requestOptions:
              RequestOptions(path: '/entries/$id/knowledge-context'),
          response: Response(
            requestOptions:
                RequestOptions(path: '/entries/$id/knowledge-context'),
            statusCode: 500,
            data: {'detail': 'Server Error'},
          ),
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .fetchKnowledgeContext();

      final state = container.read(entryDetailProvider('test-id'));
      expect(state.error, isNotNull);
    });

    // ---- searchEntriesForLink ----
    test('searchEntriesForLink writes results to searchResults state', () async {
      mockApiClient.searchEntriesFn = ({required query, int? limit}) async {
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/entries/search/query'),
          data: {
            'entries': [
              {
                'id': 'result-1',
                'title': 'Search Result 1',
                'category': 'task',
              },
              {
                'id': 'result-2',
                'title': 'Search Result 2',
                'category': 'note',
              },
            ],
          },
          statusCode: 200,
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .searchEntriesForLink(query: 'test query');

      final state = container.read(entryDetailProvider('test-id'));
      expect(state.isSearching, false);
      expect(state.searchResults, hasLength(2));
      expect(state.searchResults.first.id, 'result-1');
      expect(state.searchResults.last.id, 'result-2');
    });

    test('searchEntriesForLink failure stops searching and sets error', () async {
      mockApiClient.searchEntriesFn = ({required query, int? limit}) async {
        throw DioException(
          requestOptions: RequestOptions(path: '/entries/search/query'),
          response: Response(
            requestOptions: RequestOptions(path: '/entries/search/query'),
            statusCode: 500,
            data: {'detail': 'Server Error'},
          ),
        );
      };

      await container
          .read(entryDetailProvider('test-id').notifier)
          .searchEntriesForLink(query: 'fail query');

      final state = container.read(entryDetailProvider('test-id'));
      expect(state.isSearching, false);
      expect(state.error, isNotNull);
      expect(state.searchResults, isEmpty);
    });
  });
}

// ================================================================
// Helper
// ================================================================
Entry _makeEntry(String id, {String? status, String category = 'task', String? title}) {
  return Entry(
    id: id,
    title: title ?? 'Entry $id',
    category: category,
    status: status,
  );
}

// ================================================================
// Mock ApiClient
// ================================================================
class MockApiClient extends ApiClient {
  // Function fields for each API method used by EntryDetailNotifier
  Future<Response<Map<String, dynamic>>> Function({
    required String id,
    required Map<String, dynamic> data,
  })? updateEntryFn;

  Future<Response<Map<String, dynamic>>> Function(
    String path, {
    Map<String, dynamic>? queryParameters,
    dynamic options,
  })? getFn;

  Future<Response<Map<String, dynamic>>> Function({required String id})?
      generateAISummaryFn;

  Future<Response<Map<String, dynamic>>> Function({required String id})?
      fetchBacklinksFn;

  Future<Response<Map<String, dynamic>>> Function({required String id})?
      fetchKnowledgeContextFn;

  Future<Response<Map<String, dynamic>>> Function({
    required String id,
    String direction,
  })? fetchEntryLinksFn;

  Future<Response<Map<String, dynamic>>> Function({
    required String id,
    required String targetId,
    required String relationType,
  })? createEntryLinkFn;

  Future<Response<Map<String, dynamic>>> Function({
    required String id,
    required String linkId,
  })? deleteEntryLinkFn;

  Future<Response<Map<String, dynamic>>> Function({
    required String query,
    int? limit,
  })? searchEntriesFn;

  MockApiClient() : super(baseUrl: 'http://mock.test');

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    dynamic options,
  }) async {
    if (getFn != null) {
      return (await getFn!(
        path,
        queryParameters: queryParameters,
        options: options,
      )) as Response<T>;
    }
    throw UnimplementedError('MockApiClient.get not configured for $path');
  }

  @override
  Future<Response<T>> updateEntry<T>({
    required String id,
    required Map<String, dynamic> data,
  }) async {
    if (updateEntryFn != null) {
      return (await updateEntryFn!(id: id, data: data)) as Response<T>;
    }
    throw UnimplementedError('MockApiClient.updateEntry not configured');
  }

  @override
  Future<Response<T>> generateAISummary<T>({required String id}) async {
    if (generateAISummaryFn != null) {
      return (await generateAISummaryFn!(id: id)) as Response<T>;
    }
    throw UnimplementedError('MockApiClient.generateAISummary not configured');
  }

  @override
  Future<Response<T>> fetchBacklinks<T>({required String id}) async {
    if (fetchBacklinksFn != null) {
      return (await fetchBacklinksFn!(id: id)) as Response<T>;
    }
    throw UnimplementedError('MockApiClient.fetchBacklinks not configured');
  }

  @override
  Future<Response<T>> fetchKnowledgeContext<T>({required String id}) async {
    if (fetchKnowledgeContextFn != null) {
      return (await fetchKnowledgeContextFn!(id: id)) as Response<T>;
    }
    throw UnimplementedError(
        'MockApiClient.fetchKnowledgeContext not configured');
  }

  @override
  Future<Response<T>> fetchEntryLinks<T>({
    required String id,
    String direction = 'both',
  }) async {
    if (fetchEntryLinksFn != null) {
      return (await fetchEntryLinksFn!(id: id, direction: direction))
          as Response<T>;
    }
    throw UnimplementedError('MockApiClient.fetchEntryLinks not configured');
  }

  @override
  Future<Response<T>> createEntryLink<T>({
    required String id,
    required String targetId,
    required String relationType,
  }) async {
    if (createEntryLinkFn != null) {
      return (await createEntryLinkFn!(
        id: id,
        targetId: targetId,
        relationType: relationType,
      )) as Response<T>;
    }
    throw UnimplementedError('MockApiClient.createEntryLink not configured');
  }

  @override
  Future<Response<T>> deleteEntryLink<T>({
    required String id,
    required String linkId,
  }) async {
    if (deleteEntryLinkFn != null) {
      return (await deleteEntryLinkFn!(id: id, linkId: linkId)) as Response<T>;
    }
    throw UnimplementedError('MockApiClient.deleteEntryLink not configured');
  }

  @override
  Future<Response<T>> searchEntries<T>({
    required String query,
    int? limit,
  }) async {
    if (searchEntriesFn != null) {
      return (await searchEntriesFn!(query: query, limit: limit)) as Response<T>;
    }
    throw UnimplementedError('MockApiClient.searchEntries not configured');
  }
}
