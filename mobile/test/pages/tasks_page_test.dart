import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:growth_assistant/config/constants.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/pages/tasks_page.dart';
import 'package:growth_assistant/providers/entry_provider.dart';

// 测试用 Entry 工厂
Entry _makeEntry({
  required String id,
  String title = 'Task',
  String status = 'doing',
}) {
  return Entry(
    id: id,
    title: '$title $id',
    category: AppConstants.categoryTask,
    status: status,
  );
}

// 构建测试用的 GoRouter
GoRouter _testRouter() {
  return GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => const TasksPage(),
      ),
      GoRoute(
        path: '/entries/:id',
        builder: (context, state) => const Scaffold(
          body: Text('Entry Detail'),
        ),
      ),
    ],
  );
}

// 辅助：注入 provider override 后渲染
Future<void> _pumpTasksPage(
  WidgetTester tester, {
  List<Entry> entries = const [],
  bool isLoading = false,
  String? error,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        entryListProvider.overrideWith(
          () => _FakeEntryListNotifier(
            entries: entries,
            isLoading: isLoading,
            error: error,
          ),
        ),
      ],
      child: MaterialApp.router(
        routerConfig: _testRouter(),
      ),
    ),
  );
  // 等待 initState 的 addPostFrameCallback 触发
  await tester.pump();
}

// Fake EntryListNotifier，直接返回预设状态
class _FakeEntryListNotifier extends EntryListNotifier {
  final List<Entry> _entries;
  final bool _isLoading;
  final String? _error;

  _FakeEntryListNotifier({
    required List<Entry> entries,
    required bool isLoading,
    String? error,
  })  : _entries = entries,
        _isLoading = isLoading,
        _error = error;

  @override
  EntryListState build() {
    return EntryListState(
      entries: _entries,
      isLoading: _isLoading,
      error: _error,
    );
  }

  // 阻止 initState 中的 fetchEntries 触发真实 API 调用
  @override
  Future<void> fetchEntries({String? type, String? status}) async {}

  @override
  Future<bool> updateEntryStatus(String entryId, String newStatus) async => true;
}

// 可变的 EntryListNotifier，支持动态更新状态以测试数据刷新
class _MutableEntryListNotifier extends EntryListNotifier {
  @override
  EntryListState build() => const EntryListState();

  @override
  Future<void> fetchEntries({String? type, String? status}) async {}

  @override
  Future<bool> updateEntryStatus(String entryId, String newStatus) async => true;

  void setEntries(List<Entry> entries) {
    state = EntryListState(entries: entries);
  }
}

void main() {
  group('TasksPage', () {
    testWidgets('空列表显示空状态引导文案', (WidgetTester tester) async {
      await _pumpTasksPage(tester, entries: []);

      expect(find.text('暂无任务'), findsOneWidget);
      expect(
        find.text('通过 AI 对话创建任务，或点击首页快速操作添加'),
        findsOneWidget,
      );
    });

    testWidgets('错误状态显示错误信息和重试按钮', (WidgetTester tester) async {
      await _pumpTasksPage(
        tester,
        entries: [],
        error: '网络连接失败',
      );

      expect(find.text('网络连接失败'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    testWidgets('加载中显示进度指示器', (WidgetTester tester) async {
      await _pumpTasksPage(tester, entries: [], isLoading: true);

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('按状态分组显示任务', (WidgetTester tester) async {
      final entries = [
        _makeEntry(id: '1', status: 'doing'),
        _makeEntry(id: '2', status: 'doing'),
        _makeEntry(id: '3', status: 'waitStart'),
        _makeEntry(id: '4', status: 'complete'),
      ];

      await _pumpTasksPage(tester, entries: entries);

      // 验证分组标题
      expect(find.text('进行中 (2)'), findsOneWidget);
      expect(find.text('待开始 (1)'), findsOneWidget);
      expect(find.text('已完成 (1)'), findsOneWidget);
    });

    testWidgets('多条目分组使用 ReorderableListView', (WidgetTester tester) async {
      final entries = [
        _makeEntry(id: '1', status: 'doing'),
        _makeEntry(id: '2', status: 'doing'),
      ];

      await _pumpTasksPage(tester, entries: entries);

      // 应存在 ReorderableListView（进行中组有 2 条）
      expect(find.byType(ReorderableListView), findsOneWidget);
    });

    testWidgets('单条目分组不使用 ReorderableListView', (WidgetTester tester) async {
      final entries = [
        _makeEntry(id: '1', status: 'doing'),
        _makeEntry(id: '2', status: 'waitStart'),
      ];

      await _pumpTasksPage(tester, entries: entries);

      // 进行中（1 条）和待开始（1 条）都不应该有 ReorderableListView
      expect(find.byType(ReorderableListView), findsNothing);
    });

    testWidgets('筛选 Tab 切换', (WidgetTester tester) async {
      final entries = [
        _makeEntry(id: '1', status: 'doing'),
        _makeEntry(id: '2', status: 'complete'),
      ];

      await _pumpTasksPage(tester, entries: entries);

      // 默认"全部"被选中
      expect(find.text('全部'), findsOneWidget);

      // 点击"进行中"
      await tester.tap(find.text('进行中'));
      await tester.pumpAndSettle();

      // 筛选 Tab 应仍然可见
      expect(find.text('全部'), findsOneWidget);
      expect(find.text('进行中'), findsOneWidget);
    });

    testWidgets('渲染 4 个筛选 Tab', (WidgetTester tester) async {
      await _pumpTasksPage(tester, entries: []);

      expect(find.text('全部'), findsOneWidget);
      expect(find.text('进行中'), findsOneWidget);
      expect(find.text('待开始'), findsOneWidget);
      expect(find.text('已完成'), findsOneWidget);
    });

    testWidgets('AppBar 标题为"任务"', (WidgetTester tester) async {
      await _pumpTasksPage(tester, entries: []);

      expect(find.text('任务'), findsOneWidget);
    });

    testWidgets('拖拽重排验证：ID 映射正确', (WidgetTester tester) async {
      // 3 doing + 1 waitStart，测试拖拽只影响 doing 组
      final entries = [
        _makeEntry(id: 'A', status: 'doing'),
        _makeEntry(id: 'D', status: 'waitStart'),
        _makeEntry(id: 'B', status: 'doing'),
        _makeEntry(id: 'C', status: 'doing'),
      ];

      await _pumpTasksPage(tester, entries: entries);

      expect(find.text('进行中 (3)'), findsOneWidget);
      expect(find.text('待开始 (1)'), findsOneWidget);

      // doing 组有 ReorderableListView
      expect(find.byType(ReorderableListView), findsOneWidget);

      // 记录初始顺序：A 在 B 上面
      final aPosBefore = tester.getCenter(find.text('Task A')).dy;
      final bPosBefore = tester.getCenter(find.text('Task B')).dy;
      expect(aPosBefore, lessThan(bPosBefore)); // A 在 B 上面

      // 使用连续手势拖拽：将 B(index 1) 拖到 A(index 0) 前面
      final listeners = find.byType(ReorderableDelayedDragStartListener);
      expect(listeners, findsNWidgets(3)); // 3 doing items

      final gesture = await tester.startGesture(
        tester.getCenter(listeners.at(1)), // B 的位置
      );
      // 等待 ReorderableDelayedDragStartListener 的延迟
      await tester.pump(const Duration(milliseconds: 500));
      // 移动到 A 的位置（向上）
      await gesture.moveTo(tester.getCenter(listeners.at(0)));
      await tester.pump();
      await gesture.up();
      await tester.pumpAndSettle();

      // 重排后 doing 组仍为 3 条，waitStart 不受影响
      expect(find.text('进行中 (3)'), findsOneWidget);
      expect(find.text('待开始 (1)'), findsOneWidget);
      // 所有条目仍然可见
      expect(find.text('Task A'), findsOneWidget);
      expect(find.text('Task B'), findsOneWidget);
      expect(find.text('Task C'), findsOneWidget);
      expect(find.text('Task D'), findsOneWidget);

      // 验证顺序变化：B 现在应该在 A 上面
      final bPosAfter = tester.getCenter(find.text('Task B')).dy;
      final aPosAfter = tester.getCenter(find.text('Task A')).dy;
      expect(bPosAfter, lessThan(aPosAfter)); // B 在 A 上面
    });

    testWidgets('同 ID 数据刷新后分组正确', (WidgetTester tester) async {
      final notifier = _MutableEntryListNotifier();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            entryListProvider.overrideWith(() => notifier),
          ],
          child: MaterialApp.router(routerConfig: _testRouter()),
        ),
      );
      await tester.pump();

      // 初始空状态
      expect(find.text('暂无任务'), findsOneWidget);

      // 第一次渲染：2 doing
      notifier.setEntries([
        _makeEntry(id: '1', status: 'doing'),
        _makeEntry(id: '2', status: 'doing'),
      ]);
      await tester.pump();

      expect(find.text('进行中 (2)'), findsOneWidget);

      // 第二次渲染：同 ID 但 entry 1 状态变为 complete
      notifier.setEntries([
        _makeEntry(id: '1', status: 'complete'),
        _makeEntry(id: '2', status: 'doing'),
      ]);
      await tester.pump();

      // 验证分组已更新（else 分支刷新了 entry 数据）
      expect(find.text('进行中 (1)'), findsOneWidget);
      expect(find.text('已完成 (1)'), findsOneWidget);
    });

    testWidgets('已暂停任务显示在已暂停分组', (WidgetTester tester) async {
      final entries = [
        _makeEntry(id: '1', status: 'paused'),
        _makeEntry(id: '2', status: 'paused'),
      ];

      await _pumpTasksPage(tester, entries: entries);

      expect(find.text('已暂停 (2)'), findsOneWidget);
      expect(find.byType(ReorderableListView), findsOneWidget);
    });
  });
}
