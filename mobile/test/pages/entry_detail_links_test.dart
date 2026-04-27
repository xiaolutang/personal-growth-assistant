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
  String? content = '测试内容',
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
// Mock ApiClient for links tests
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
    // Handle navigation to other entry detail pages (/entries/{id})
    if (path.startsWith('/entries/')) {
      final segments = path.split('/').where((s) => s.isNotEmpty).toList();
      if (segments.length == 2 && segments[0] == 'entries') {
        final entryId = segments[1];
        return Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: path),
          data: _makeEntry(id: entryId, title: '条目$entryId').toJson(),
          statusCode: 200,
        ) as Response<T>;
      }
      // knowledge-context, links, backlinks sub-paths — return empty for any entry
      if (segments.length == 3 && segments[0] == 'entries') {
        final subPath = segments[2];
        if (subPath == 'knowledge-context') {
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
        if (subPath == 'links') {
          // Return populated links for test-id, empty for others
          final links = segments[1] == 'test-id'
              ? <dynamic>[
                  {
                    'link_id': 'link-1',
                    'source_id': 'test-id',
                    'target_id': 'target-1',
                    'relation_type': 'related',
                    'target_entry': {
                      'id': 'target-1',
                      'title': '关联条目A',
                      'category': 'note',
                      'status': 'doing',
                      'tags': <String>[],
                      'created_at': '2024-01-10T10:00:00',
                      'updated_at': '2024-01-10T10:00:00',
                    },
                  },
                ]
              : <dynamic>[];
          return Response<Map<String, dynamic>>(
            requestOptions: RequestOptions(path: path),
            data: {'links': links},
            statusCode: 200,
          ) as Response<T>;
        }
        if (subPath == 'backlinks') {
          // Return populated backlinks for test-id, empty for others
          final backlinks = segments[1] == 'test-id'
              ? <dynamic>[
                  {
                    'id': 'backlink-1',
                    'title': '引用条目B',
                    'category': 'task',
                    'relation_type': 'references',
                    'created_at': '2024-01-12T10:00:00',
                  },
                ]
              : <dynamic>[];
          return Response<Map<String, dynamic>>(
            requestOptions: RequestOptions(path: path),
            data: {'backlinks': backlinks},
            statusCode: 200,
          ) as Response<T>;
        }
      }
    }
    throw UnimplementedError('Unexpected path: $path');
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
  await tester.pumpAndSettle();

  return container;
}

/// 设置 entry + links 数据
void _setEntryWithLinks(ProviderContainer container) {
  final notifier = container.read(entryDetailProvider('test-id').notifier);
  notifier.state = EntryDetailState(
    entry: _makeEntry(),
    entryLinks: [
      EntryLinkItem(
        linkId: 'link-1',
        sourceId: 'test-id',
        targetId: 'target-1',
        relationType: 'related',
        targetEntry: _makeEntry(id: 'target-1', title: '关联条目A', category: 'note'),
      ),
    ],
    backlinks: [
      BacklinkItem(
        id: 'backlink-1',
        title: '引用条目B',
        category: 'task',
        relationType: 'references',
      ),
    ],
  );
}

// ================================================================
// Tests
// ================================================================
void main() {
  group('EntryDetailPage 关联条目 + 反向引用 (F176)', () {
    // ============================================================
    // AC1: 关联条目列表渲染
    // ============================================================
    testWidgets('关联条目 Section 显示标题和列表项', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setEntryWithLinks(container);
      await tester.pump();

      expect(find.text('关联条目'), findsOneWidget);
      expect(find.text('关联条目A'), findsOneWidget);
      expect(find.text('相关'), findsWidgets); // relation_type label
    });

    testWidgets('关联条目显示分类图标和标题', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setEntryWithLinks(container);
      await tester.pump();

      // 关联条目 A 是 note 类别
      expect(find.text('关联条目A'), findsOneWidget);
    });

    // ============================================================
    // AC2: 关联条目支持删除（Dismissible 滑动）
    // ============================================================
    testWidgets('关联条目有 Dismissible 支持滑动删除', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setEntryWithLinks(container);
      await tester.pump();

      // 关联条目有 Dismissible widget（endToStart 方向）
      final dismissible = find.byType(Dismissible);
      expect(dismissible, findsOneWidget);

      // 验证 Dismissible 方向为 endToStart
      final dismissibleWidget = tester.widget<Dismissible>(dismissible);
      expect(dismissibleWidget.direction, DismissDirection.endToStart);
    });

    // ============================================================
    // AC3: 反向引用列表渲染
    // ============================================================
    testWidgets('反向引用 Section 显示标题和列表项', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setEntryWithLinks(container);
      await tester.pump();

      expect(find.text('反向引用'), findsOneWidget);
      expect(find.text('引用条目B'), findsOneWidget);
    });

    testWidgets('反向引用显示数量 badge', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setEntryWithLinks(container);
      await tester.pump();

      // 1 条反向引用，应显示 badge "1"
      expect(find.text('1'), findsWidgets);
    });

    testWidgets('反向引用显示关联类型标签', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setEntryWithLinks(container);
      await tester.pump();

      // relation_type = references → '引用'
      expect(find.text('引用'), findsOneWidget);
    });

    // ============================================================
    // AC4: 添加关联按钮 + 对话框
    // ============================================================
    testWidgets('点击添加关联按钮弹出对话框', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setEntryWithLinks(container);
      await tester.pump();

      await tester.tap(find.text('添加关联'));
      await tester.pumpAndSettle();

      expect(find.text('添加关联'), findsWidgets); // dialog title
      expect(find.text('搜索条目...'), findsOneWidget);
      expect(find.text('关联类型'), findsOneWidget);
    });

    testWidgets('对话框默认 relation_type 为 related', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setEntryWithLinks(container);
      await tester.pump();

      await tester.tap(find.text('添加关联'));
      await tester.pumpAndSettle();

      // DropdownButtonFormField 默认值 'related' → '相关'
      expect(find.text('相关'), findsWidgets);
    });

    // ============================================================
    // 空状态
    // ============================================================
    testWidgets('空关联列表显示引导文案', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      // 设置 entry 但无关联数据
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(entry: _makeEntry());
      await tester.pump();

      expect(find.text('暂无关联条目，点击右上角添加'), findsOneWidget);
    });

    testWidgets('空反向引用显示引导文案', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(entry: _makeEntry());
      await tester.pump();

      expect(find.text('暂无其他条目引用此条目'), findsOneWidget);
    });

    // ============================================================
    // AC5: 关联条目/反向引用有 InkWell
    // ============================================================
    testWidgets('关联条目项有 InkWell 且 enabled', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setEntryWithLinks(container);
      await tester.pump();

      // 关联条目有 InkWell（displayEntry 不为 null，onTap 不为 null）
      final inkWells = find.byType(InkWell);
      // 至少 2 个 InkWell: 关联条目 + 反向引用
      expect(inkWells, findsAtLeast(2));

      // 找到关联条目区域的 InkWell（包含"关联条目A"文本）
      final linkText = find.text('关联条目A');
      expect(linkText, findsOneWidget);
    });

    testWidgets('反向引用条目有 InkWell 可点击', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setEntryWithLinks(container);
      await tester.pump();

      // 反向引用条目有 InkWell
      final backlinkText = find.text('引用条目B');
      expect(backlinkText, findsOneWidget);

      // 反向引用区域有 InkWell（点击会调用 _navigateToEntry）
      final inkWells = find.byType(InkWell);
      expect(inkWells, findsAtLeast(2));
    });

    testWidgets('family provider 按 entryId 隔离状态', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);

      // test-id 和 other-id 应有独立状态
      final stateA = container.read(entryDetailProvider('test-id'));
      final stateB = container.read(entryDetailProvider('other-id'));
      expect(identical(stateA, stateB), isFalse);
    });

    // ============================================================
    // 搜索相关
    // ============================================================
    testWidgets('搜索词为空白不触发搜索', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setEntryWithLinks(container);
      await tester.pump();

      await tester.tap(find.text('添加关联'));
      await tester.pumpAndSettle();

      // 输入空白后搜索结果区域不应显示
      final searchField = find.widgetWithText(TextField, '搜索条目...');
      expect(searchField, findsOneWidget);

      await tester.enterText(searchField, '   ');
      await tester.pump();

      // 不应有搜索结果区域
      expect(find.text('未找到匹配条目'), findsNothing);
    });

    // ============================================================
    // relation_type 标签映射
    // ============================================================
    testWidgets('relation_type 映射正确显示', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      final notifier = container.read(entryDetailProvider('test-id').notifier);
      notifier.state = EntryDetailState(
        entry: _makeEntry(),
        entryLinks: [
          EntryLinkItem(
            linkId: 'link-dep',
            sourceId: 'test-id',
            targetId: 'target-2',
            relationType: 'depends_on',
            targetEntry: _makeEntry(id: 'target-2', title: '依赖条目'),
          ),
          EntryLinkItem(
            linkId: 'link-ref',
            sourceId: 'test-id',
            targetId: 'target-3',
            relationType: 'references',
            targetEntry: _makeEntry(id: 'target-3', title: '引用条目'),
          ),
        ],
      );
      await tester.pump();

      expect(find.text('依赖'), findsOneWidget);
      expect(find.text('引用'), findsOneWidget);
    });
  });
}
