import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/pages/entry_detail_page.dart';
import 'package:growth_assistant/providers/entry_provider.dart';
import 'package:growth_assistant/providers/auth_provider.dart';
import 'package:growth_assistant/services/api_client.dart';

// ================================================================
// Helper: 创建测试用 Entry
// ================================================================
Entry _makeEntry({
  String id = 'test-id',
  String title = '测试条目',
  String category = 'task',
  String? status = 'doing',
  String? priority = 'medium',
  List<String> tags = const [],
  String? content = '这是一段测试内容',
}) {
  return Entry(
    id: id,
    title: title,
    category: category,
    status: status,
    priority: priority,
    tags: tags,
    content: content,
    createdAt: '2024-01-15T10:00:00',
    updatedAt: '2024-01-16T14:30:00',
  );
}

// ================================================================
// Mock ApiClient for widget tests
// ================================================================
class _MockApiClient extends ApiClient {
  _MockApiClient() : super(baseUrl: 'http://mock.test');

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    dynamic options,
  }) async {
    if (path == '/entries/test-id') {
      return Response<Map<String, dynamic>>(
        requestOptions: RequestOptions(path: path),
        data: _makeEntry().toJson(),
        statusCode: 200,
      ) as Response<T>;
    }
    if (path == '/entries/test-id/knowledge-context') {
      return Response<Map<String, dynamic>>(
        requestOptions: RequestOptions(path: path),
        data: {
          'nodes': <dynamic>[],
          'edges': <dynamic>[],
          'center_concepts': <dynamic>[],
        },
        statusCode: 200,
      ) as Response<T>;
    }
    throw UnimplementedError('Unexpected path: $path');
  }

  @override
  Future<Response<T>> generateAISummary<T>({required String id}) async {
    return Response<Map<String, dynamic>>(
      requestOptions: RequestOptions(path: '/entries/$id/ai-summary'),
      data: {'summary': 'AI generated summary text', 'cached': false},
      statusCode: 200,
    ) as Response<T>;
  }
}

// ================================================================
// Helper: 构建 pump Widget
// ================================================================
Future<ProviderContainer> _pumpDetailPage(
  WidgetTester tester, {
  _MockApiClient? apiClient,
}) async {
  final client = apiClient ?? _MockApiClient();
  final container = ProviderContainer(
    overrides: [
      apiClientProvider.overrideWithValue(client),
    ],
  );

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(
        home: EntryDetailPage(entryId: 'test-id'),
      ),
    ),
  );
  // pumpAndSettle 等待所有异步操作（包括 fetchKnowledgeContext）完成
  await tester.pumpAndSettle();

  return container;
}

// ================================================================
// Tests
// ================================================================
void main() {
  group('EntryDetailPage AI 摘要 + 知识上下文 (F175)', () {
    // ============================================================
    // AC1: AI 摘要 Section 存在
    // ============================================================
    testWidgets('只读模式显示 AI 摘要 Section', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      // 直接设置完整的只读态（带 entry + knowledgeContext）
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(),
        knowledgeContext: KnowledgeContextData(
          nodes: [],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      expect(find.text('AI 摘要'), findsOneWidget);
      expect(find.byIcon(Icons.auto_awesome_outlined), findsOneWidget);
    });

    testWidgets('有内容时显示生成摘要按钮', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(content: '有内容'),
        knowledgeContext: KnowledgeContextData(
          nodes: [],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      expect(find.text('生成摘要'), findsOneWidget);
    });

    // ============================================================
    // AC2: AI 摘要生成失败时展示错误提示+重试按钮
    // ============================================================
    testWidgets('摘要生成失败时显示错误提示和重试按钮',
        (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);

      // 设置错误状态（error != null 且 summaryText == null）
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(content: '有内容'),
        error: '摘要生成失败',
        knowledgeContext: KnowledgeContextData(
          nodes: [],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      expect(find.textContaining('摘要生成失败'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    // ============================================================
    // AC3: 空内容时禁用生成按钮 + 提示
    // ============================================================
    testWidgets('空内容时显示禁用按钮和提示文字', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(content: ''),
        knowledgeContext: KnowledgeContextData(
          nodes: [],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      // 按钮文字应可见
      expect(find.text('生成摘要'), findsOneWidget);
      expect(find.text('内容为空，无法生成摘要'), findsOneWidget);
    });

    testWidgets('null 内容时显示禁用按钮和提示文字',
        (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(content: null),
        knowledgeContext: KnowledgeContextData(
          nodes: [],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      expect(find.text('生成摘要'), findsOneWidget);
      expect(find.text('内容为空，无法生成摘要'), findsOneWidget);
    });

    // ============================================================
    // AC4: 缓存摘要直接展示
    // ============================================================
    testWidgets('缓存摘要直接展示且显示已缓存标签', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(content: '有内容'),
        summaryText: '这是缓存的 AI 摘要',
        summaryCached: true,
        knowledgeContext: KnowledgeContextData(
          nodes: [],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      expect(find.text('这是缓存的 AI 摘要'), findsOneWidget);
      expect(find.text('已缓存'), findsOneWidget);
    });

    // ============================================================
    // AC5: 知识上下文 Section 存在
    // ============================================================
    testWidgets('只读模式显示知识上下文 Section', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(),
        knowledgeContext: KnowledgeContextData(
          nodes: [],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      expect(find.text('知识上下文'), findsOneWidget);
      expect(find.byIcon(Icons.account_tree_outlined), findsOneWidget);
    });

    // ============================================================
    // AC6: mastery 字符串映射
    // ============================================================
    testWidgets('mastery 映射：beginner→入门', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(),
        knowledgeContext: KnowledgeContextData(
          nodes: [
            {'name': 'Flutter', 'mastery': 'beginner', 'entry_count': 2},
          ],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      expect(find.text('Flutter'), findsOneWidget);
      expect(find.text('入门'), findsOneWidget);
      expect(find.text('2 篇'), findsOneWidget);
    });

    testWidgets('mastery 映射：intermediate→进阶', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(),
        knowledgeContext: KnowledgeContextData(
          nodes: [
            {'name': 'Dart', 'mastery': 'intermediate', 'entry_count': 5},
          ],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      expect(find.text('Dart'), findsOneWidget);
      expect(find.text('进阶'), findsOneWidget);
      expect(find.text('5 篇'), findsOneWidget);
    });

    testWidgets('mastery 映射：advanced→精通', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(),
        knowledgeContext: KnowledgeContextData(
          nodes: [
            {'name': 'Test', 'mastery': 'advanced', 'entry_count': 10},
          ],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      expect(find.text('Test'), findsOneWidget);
      expect(find.text('精通'), findsOneWidget);
      expect(find.text('10 篇'), findsOneWidget);
    });

    testWidgets('mastery 映射：null→未评估', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(),
        knowledgeContext: KnowledgeContextData(
          nodes: [
            {'name': 'Unknown', 'mastery': null, 'entry_count': 0},
          ],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      expect(find.text('Unknown'), findsOneWidget);
      expect(find.text('未评估'), findsOneWidget);
    });

    // ============================================================
    // AC7: 无知识上下文数据时展示空提示
    // ============================================================
    testWidgets('无知识上下文数据时显示空提示', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(),
        // knowledgeContext 为 null
      );
      await tester.pump();

      expect(find.text('暂无知识关联'), findsOneWidget);
    });

    testWidgets('知识上下文 nodes 为空列表时显示空提示',
        (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(),
        knowledgeContext: KnowledgeContextData(
          nodes: [],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      expect(find.text('暂无知识关联'), findsOneWidget);
    });

    // ============================================================
    // 多个概念节点渲染
    // ============================================================
    testWidgets('多个知识概念节点同时展示', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(),
        knowledgeContext: KnowledgeContextData(
          nodes: [
            {'name': 'Flutter', 'mastery': 'beginner', 'entry_count': 2},
            {'name': 'Dart', 'mastery': 'advanced', 'entry_count': 8},
            {'name': 'Riverpod', 'mastery': 'intermediate', 'entry_count': 3},
          ],
          edges: [],
          centerConcepts: ['Flutter'],
        ),
      );
      await tester.pump();

      expect(find.text('Flutter'), findsOneWidget);
      expect(find.text('Dart'), findsOneWidget);
      expect(find.text('Riverpod'), findsOneWidget);
      expect(find.text('入门'), findsOneWidget);
      expect(find.text('精通'), findsOneWidget);
      expect(find.text('进阶'), findsOneWidget);
    });

    // ============================================================
    // loading 态
    // ============================================================
    testWidgets('AI 摘要生成中显示 loading 指示器',
        (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(content: '有内容'),
        isGeneratingSummary: true,
        knowledgeContext: KnowledgeContextData(
          nodes: [],
          edges: [],
          centerConcepts: [],
        ),
      );
      await tester.pump();

      // AI 摘要卡片内的 CircularProgressIndicator
      expect(find.byType(CircularProgressIndicator), findsWidgets);
    });
  });
}
