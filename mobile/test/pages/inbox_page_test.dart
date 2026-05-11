import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:rizhi/config/constants.dart';
import 'package:rizhi/models/entry.dart';
import 'package:rizhi/pages/inbox_page.dart';
import 'package:rizhi/providers/inbox_provider.dart';
import 'package:rizhi/widgets/skeleton_loading.dart';

// 测试用 Entry 工厂
Entry _makeInboxEntry({
  required String id,
  String title = '灵感',
  String? content,
}) {
  return Entry(
    id: id,
    title: '$title $id',
    category: AppConstants.categoryInbox,
    content: content,
  );
}

// Fake InboxNotifier，直接返回预设状态
class _FakeInboxNotifier extends InboxNotifier {
  final List<Entry> _entries;
  final bool _isLoading;
  final String? _error;

  _FakeInboxNotifier({
    required List<Entry> entries,
    required bool isLoading,
    String? error,
  })  : _entries = entries,
        _isLoading = isLoading,
        _error = error;

  @override
  InboxState build() {
    return InboxState(
      entries: _entries,
      isLoading: _isLoading,
      error: _error,
    );
  }

  @override
  Future<void> fetchInbox() async {}

  @override
  Future<bool> createInboxItem(String title) async => false;

  @override
  Future<bool> convertCategory(String id, String newCategory) async => false;

  @override
  void setNewEntryText(String text) {}
}

// 构建测试用的 GoRouter
GoRouter _testRouter() {
  return GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => const InboxPage(),
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
Future<void> _pumpInboxPage(
  WidgetTester tester, {
  List<Entry> entries = const [],
  bool isLoading = false,
  String? error,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        inboxProvider.overrideWith(
          () => _FakeInboxNotifier(
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
  await tester.pump();
}

// Mutable InboxNotifier for swipe tests
class _MutableInboxNotifier extends InboxNotifier {
  late List<Entry> _entries;
  final List<String> removeEntryLocallyCalls = [];
  final List<String> deleteEntryFromBackendCalls = [];
  final List<(Entry, int)> restoreEntryCalls = [];
  bool deleteBackendSuccess = true;

  _MutableInboxNotifier({required List<Entry> entries}) {
    _entries = List.of(entries);
  }

  @override
  InboxState build() => InboxState(entries: _entries);

  @override
  Future<void> fetchInbox() async {}

  @override
  Future<bool> createInboxItem(String title) async => false;

  @override
  Future<bool> convertCategory(String id, String newCategory) async => false;

  @override
  void setNewEntryText(String text) {}

  @override
  void removeEntryLocally(String entryId) {
    removeEntryLocallyCalls.add(entryId);
    _entries = _entries.where((e) => e.id != entryId).toList();
    state = InboxState(entries: _entries);
  }

  @override
  Future<bool> deleteEntryFromBackend(String entryId) async {
    deleteEntryFromBackendCalls.add(entryId);
    return deleteBackendSuccess;
  }

  @override
  void restoreEntry(Entry entry, int originalIndex) {
    restoreEntryCalls.add((entry, originalIndex));
    final insertAt = originalIndex.clamp(0, _entries.length);
    _entries.insert(insertAt, entry);
    state = InboxState(entries: _entries);
  }
}

Future<_MutableInboxNotifier> _pumpInboxPageTracking(
  WidgetTester tester, {
  List<Entry> entries = const [],
}) async {
  late _MutableInboxNotifier notifier;
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        inboxProvider.overrideWith(() {
          return notifier = _MutableInboxNotifier(entries: entries);
        }),
      ],
      child: MaterialApp.router(
        routerConfig: _testRouter(),
      ),
    ),
  );
  await tester.pump();
  return notifier;
}

void main() {
  group('InboxPage', () {
    testWidgets('空列表显示空状态引导文案', (WidgetTester tester) async {
      await _pumpInboxPage(tester, entries: []);

      expect(find.text('随时记录灵感'), findsOneWidget);
      expect(
        find.text('点击右下角按钮，快速记录灵感'),
        findsOneWidget,
      );
    });

    testWidgets('错误状态显示错误信息和重试按钮', (WidgetTester tester) async {
      await _pumpInboxPage(
        tester,
        entries: [],
        error: '网络连接失败',
      );

      expect(find.text('网络连接失败'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    testWidgets('加载中显示进度指示器', (WidgetTester tester) async {
      await _pumpInboxPage(tester, entries: [], isLoading: true);

      expect(find.byType(SkeletonLoading), findsWidgets);
    });

    testWidgets('灵感列表渲染标题', (WidgetTester tester) async {
      final entries = [
        _makeInboxEntry(id: '1', title: 'Flutter 灵感'),
        _makeInboxEntry(id: '2', title: 'Dart 灵感'),
      ];

      await _pumpInboxPage(tester, entries: entries);

      expect(find.text('Flutter 灵感 1'), findsOneWidget);
      expect(find.text('Dart 灵感 2'), findsOneWidget);
    });

    testWidgets('空状态显示灯泡图标', (WidgetTester tester) async {
      await _pumpInboxPage(tester, entries: []);

      expect(find.byIcon(Icons.lightbulb_outline), findsOneWidget);
    });

    testWidgets('AppBar 标题为"灵感"', (WidgetTester tester) async {
      await _pumpInboxPage(tester, entries: []);

      expect(find.text('灵感'), findsOneWidget);
    });
  });

  group('InboxPage 滑动操作', () {
    testWidgets('左滑删除显示 SnackBar', (tester) async {
      final notifier = await _pumpInboxPageTracking(
        tester,
        entries: [_makeInboxEntry(id: '1')],
      );

      // 左滑（startToEnd = 删除）
      await tester.drag(
        find.byKey(const ValueKey('dismissible_1')),
        const Offset(500, 0),
      );
      await tester.pumpAndSettle();

      // 验证 removeEntryLocally 被调用
      expect(notifier.removeEntryLocallyCalls, ['1']);

      // 验证 SnackBar 显示
      expect(find.text('灵感已删除'), findsOneWidget);
      expect(find.text('撤销'), findsOneWidget);
    });

    testWidgets('撤销删除恢复条目', (tester) async {
      final notifier = await _pumpInboxPageTracking(
        tester,
        entries: [_makeInboxEntry(id: '1'), _makeInboxEntry(id: '2')],
      );

      // 左滑删除第一条
      await tester.drag(
        find.byKey(const ValueKey('dismissible_1')),
        const Offset(500, 0),
      );
      await tester.pumpAndSettle();

      expect(find.text('灵感已删除'), findsOneWidget);

      // 点击撤销
      await tester.tap(find.text('撤销'));
      await tester.pumpAndSettle();

      // 验证条目被恢复
      expect(notifier.restoreEntryCalls, isNotEmpty);
      expect(notifier.restoreEntryCalls.first.$1.id, '1');
    });
  });
}
