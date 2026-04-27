import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/config/constants.dart';
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
  bool updateEntryCalled = false;
  Map<String, dynamic>? lastUpdateData;
  bool shouldFail = false;

  _MockApiClient() : super(baseUrl: 'http://mock.test');

  @override
  Future<Response<T>> updateEntry<T>({
    required String id,
    required Map<String, dynamic> data,
  }) async {
    updateEntryCalled = true;
    lastUpdateData = data;
    if (shouldFail) {
      throw DioException(
        requestOptions: RequestOptions(path: '/entries/$id'),
        response: Response(
          requestOptions: RequestOptions(path: '/entries/$id'),
          statusCode: 500,
          data: {'detail': 'Internal Server Error'},
        ),
      );
    }
    return Response<Map<String, dynamic>>(
      requestOptions: RequestOptions(path: '/entries/$id'),
      data: {'message': 'success'},
      statusCode: 200,
    ) as Response<T>;
  }

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
  await tester.pump();

  return container;
}

/// 设置 entry 数据（只读态）
void _setReadonlyEntry(ProviderContainer container, Entry entry) {
  container.read(entryDetailProvider('test-id').notifier).state =
      EntryDetailState(entry: entry);
}

/// 进入编辑态（模拟点击编辑按钮的完整流程）
Future<void> _enterEditMode(
  WidgetTester tester,
  ProviderContainer container, {
  Entry? entry,
}) async {
  _setReadonlyEntry(container, entry ?? _makeEntry());
  await tester.pump();
  await tester.tap(find.byIcon(Icons.edit_outlined));
  await tester.pumpAndSettle();
}

// ================================================================
// Tests
// ================================================================
void main() {
  group('EntryDetailPage 编辑模式 (F174)', () {
    // ============================================================
    // AC1: AppBar 右侧添加编辑图标按钮
    // ============================================================
    testWidgets('只读模式显示编辑按钮', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setReadonlyEntry(container, _makeEntry());
      await tester.pump();

      expect(find.byIcon(Icons.edit_outlined), findsOneWidget);
    });

    testWidgets('点击编辑按钮进入编辑态', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(tester, container);

      expect(find.text('保存'), findsOneWidget);
      expect(find.text('取消'), findsOneWidget);
      expect(find.byType(TextField), findsWidgets);
    });

    // ============================================================
    // AC2: 编辑态 UI 元素
    // ============================================================
    testWidgets('编辑态显示标题 TextField（含原始标题）', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(tester, container);

      // TextField 存在且包含原始标题
      expect(find.byType(TextField), findsWidgets);
      expect(find.text('测试条目'), findsOneWidget);
    });

    testWidgets('编辑态显示内容多行 TextField（含原始内容）',
        (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(tester, container);

      expect(find.text('这是一段测试内容'), findsOneWidget);
    });

    testWidgets('编辑态显示状态和优先级 DropdownButtonFormField',
        (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(tester, container);

      // 两个 DropdownButtonFormField（状态 + 优先级）
      expect(find.byType(DropdownButtonFormField<String>), findsNWidgets(2));
      // 编辑态中 "状态" 和 "优先级" label 至少各出现一次
      // (底部 meta info 也会显示，所以用 findsAtLeastNWidgets)
      expect(find.text('状态'), findsAtLeast(1));
      expect(find.text('优先级'), findsAtLeast(1));
    });

    testWidgets('编辑态显示标签区域和添加按钮', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(
        tester,
        container,
        entry: _makeEntry(tags: ['flutter', 'test']),
      );

      expect(find.text('#flutter'), findsOneWidget);
      expect(find.text('#test'), findsOneWidget);
      expect(find.text('添加'), findsOneWidget);
    });

    testWidgets('编辑态标签显示关闭图标', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(
        tester,
        container,
        entry: _makeEntry(tags: ['flutter']),
      );

      expect(find.text('#flutter'), findsOneWidget);
      expect(find.byIcon(Icons.close), findsWidgets);
    });

    testWidgets('编辑态有两个 DropdownButtonFormField',
        (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(tester, container);

      // 两个 DropdownButtonFormField（状态 + 优先级）
      expect(
        find.byType(DropdownButtonFormField<String>),
        findsNWidgets(2),
      );
    });

    testWidgets('编辑态状态下拉框可以点击展开',
        (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(tester, container);

      // 找到第一个 DropdownButtonFormField 并点击展开
      final dropdowns = find.byType(DropdownButtonFormField<String>);
      await tester.tap(dropdowns.first);
      await tester.pumpAndSettle();

      // 展开后应能看到所有状态选项
      expect(find.text('待开始'), findsWidgets);
      expect(find.text('进行中'), findsWidgets);
      expect(find.text('已完成'), findsWidgets);
      expect(find.text('已暂停'), findsWidgets);
      expect(find.text('已取消'), findsWidgets);
    });

    testWidgets('category 不可编辑 - AppBar 显示分类标题',
        (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(
        tester,
        container,
        entry: _makeEntry(category: 'task'),
      );

      expect(find.text('任务详情'), findsOneWidget);
      // 只有 2 个 DropdownButtonFormField（status + priority），没有 category 的
      expect(find.byType(DropdownButtonFormField<String>), findsNWidgets(2));
    });

    // ============================================================
    // AC3: 保存按钮
    // ============================================================
    testWidgets('修改标题后保存按钮可点击', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(tester, container);

      // 修改标题
      final titleField = find.widgetWithText(TextField, '测试条目');
      await tester.enterText(titleField, '修改后的标题');
      await tester.pump();

      // 保存按钮应可点击
      final textButton = tester.widget<TextButton>(find.ancestor(
        of: find.text('保存'),
        matching: find.byType(TextButton),
      ));
      expect(textButton.onPressed, isNotNull);
    });

    testWidgets('保存成功显示 SnackBar', (WidgetTester tester) async {
      final mockClient = _MockApiClient();
      final container = await _pumpDetailPage(tester, apiClient: mockClient);
      await _enterEditMode(tester, container);

      // 修改标题
      final titleField = find.widgetWithText(TextField, '测试条目');
      await tester.enterText(titleField, '新标题');
      await tester.pump();

      // 点击保存
      await tester.tap(find.text('保存'));
      await tester.pumpAndSettle();

      // SnackBar 显示"保存成功"
      expect(find.text('保存成功'), findsOneWidget);
    });

    // ============================================================
    // AC4: 保存失败
    // ============================================================
    testWidgets('保存失败显示错误提示', (WidgetTester tester) async {
      final failClient = _MockApiClient()..shouldFail = true;
      final container = await _pumpDetailPage(tester, apiClient: failClient);
      await _enterEditMode(tester, container);

      // 修改标题
      final titleField = find.widgetWithText(TextField, '测试条目');
      await tester.enterText(titleField, '新标题');
      await tester.pump();

      // 点击保存
      await tester.tap(find.text('保存'));
      await tester.pumpAndSettle();

      // SnackBar 显示错误
      expect(find.textContaining('保存失败'), findsOneWidget);
    });

    // ============================================================
    // AC5: 未修改时保存按钮不可点击
    // ============================================================
    testWidgets('未修改时保存按钮不可点击', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(tester, container);

      // 不修改任何内容，保存按钮 onPressed 应为 null
      final textButton = tester.widget<TextButton>(find.ancestor(
        of: find.text('保存'),
        matching: find.byType(TextButton),
      ));
      expect(textButton.onPressed, isNull);
    });

    // ============================================================
    // 取消按钮
    // ============================================================
    testWidgets('取消按钮退出编辑态', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(tester, container);

      expect(find.text('取消'), findsOneWidget);

      // 点击取消
      await tester.tap(find.text('取消'));
      await tester.pumpAndSettle();

      // 回到只读态
      expect(find.byIcon(Icons.edit_outlined), findsOneWidget);
    });

    // ============================================================
    // 标签输入
    // ============================================================
    testWidgets('编辑态切换标签输入框', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(
        tester,
        container,
        entry: _makeEntry(tags: []),
      );

      expect(find.text('输入标签名'), findsNothing);

      // 点击添加按钮
      await tester.tap(find.text('添加'));
      await tester.pumpAndSettle();

      expect(find.text('输入标签名'), findsOneWidget);
    });

    testWidgets('标签输入后按回车添加', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(
        tester,
        container,
        entry: _makeEntry(tags: []),
      );

      // 打开标签输入
      await tester.tap(find.text('添加'));
      await tester.pumpAndSettle();

      // 输入标签名并提交
      await tester.enterText(
        find.widgetWithText(TextField, '输入标签名'),
        '新标签',
      );
      await tester.testTextInput.receiveAction(TextInputAction.done);
      await tester.pumpAndSettle();

      expect(find.text('#新标签'), findsOneWidget);
    });

    // ============================================================
    // loading / notFound / error
    // ============================================================
    testWidgets('loading 态显示进度指示器', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);

      container.read(entryDetailProvider('test-id').notifier).state =
          const EntryDetailState(isLoading: true);
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('notFound 显示不存在提示', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);

      container.read(entryDetailProvider('test-id').notifier).state =
          const EntryDetailState(notFound: true);
      await tester.pump();

      expect(find.text('条目不存在'), findsOneWidget);
    });

    testWidgets('编辑按钮在 loading 时不显示', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);

      container.read(entryDetailProvider('test-id').notifier).state =
          const EntryDetailState(isLoading: true);
      await tester.pump();

      expect(find.byIcon(Icons.edit_outlined), findsNothing);
    });

    // ============================================================
    // 删除标签 dirty 状态
    // ============================================================
    testWidgets('删除标签后 dirty 状态更新', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(
        tester,
        container,
        entry: _makeEntry(tags: ['flutter']),
      );

      // 初始保存按钮不可点击（未修改）
      var textButton = tester.widget<TextButton>(find.ancestor(
        of: find.text('保存'),
        matching: find.byType(TextButton),
      ));
      expect(textButton.onPressed, isNull);

      // 点击 chip 上的关闭图标删除标签
      final closeIcon = find.byIcon(Icons.close).first;
      await tester.tap(closeIcon);
      await tester.pump();

      // 保存按钮应可点击
      textButton = tester.widget<TextButton>(find.ancestor(
        of: find.text('保存'),
        matching: find.byType(TextButton),
      ));
      expect(textButton.onPressed, isNotNull);

      // 标签已删除
      expect(find.text('#flutter'), findsNothing);
    });

    // ============================================================
    // saving 态
    // ============================================================
    testWidgets('saving 态显示进度指示器替代保存按钮',
        (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      await _enterEditMode(tester, container);

      // 手动设置 saving 状态
      container.read(entryDetailProvider('test-id').notifier).state =
          EntryDetailState(
        entry: _makeEntry(),
        isEditing: true,
        isSaving: true,
      );
      await tester.pump();

      // 保存中应显示 CircularProgressIndicator
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // 保存按钮文字不应可见
      expect(find.text('保存'), findsNothing);
    });

    // ============================================================
    // 错误态
    // ============================================================
    testWidgets('error 且无 entry 显示错误信息', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);

      container.read(entryDetailProvider('test-id').notifier).state =
          const EntryDetailState(error: '网络连接失败');
      await tester.pump();

      expect(find.text('网络连接失败'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    // ============================================================
    // 只读模式正确显示
    // ============================================================
    testWidgets('只读模式显示标签列表', (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setReadonlyEntry(container, _makeEntry(tags: ['dart', 'flutter']));
      await tester.pump();

      expect(find.text('#dart'), findsOneWidget);
      expect(find.text('#flutter'), findsOneWidget);
    });

    testWidgets('只读模式显示元信息（状态、优先级、创建时间）',
        (WidgetTester tester) async {
      final container = await _pumpDetailPage(tester);
      _setReadonlyEntry(container, _makeEntry());
      await tester.pump();

      expect(find.text('状态'), findsOneWidget);
      expect(find.text('进行中'), findsOneWidget);
      expect(find.text('优先级'), findsOneWidget);
      expect(find.text('中'), findsOneWidget);
      expect(find.text('创建时间'), findsOneWidget);
    });
  });
}
