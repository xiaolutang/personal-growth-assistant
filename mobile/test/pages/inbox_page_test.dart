import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:growth_assistant/config/constants.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/pages/inbox_page.dart';
import 'package:growth_assistant/providers/inbox_provider.dart';

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

void main() {
  group('InboxPage', () {
    testWidgets('空列表显示空状态引导文案', (WidgetTester tester) async {
      await _pumpInboxPage(tester, entries: []);

      expect(find.text('随时记录灵感'), findsOneWidget);
      expect(
        find.text('在下方输入框快速记录，稍后再整理为任务或笔记'),
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

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
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

    testWidgets('底部输入栏存在', (WidgetTester tester) async {
      await _pumpInboxPage(tester, entries: []);

      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('记录灵感...'), findsOneWidget);
    });

    testWidgets('AppBar 标题为"灵感"', (WidgetTester tester) async {
      await _pumpInboxPage(tester, entries: []);

      expect(find.text('灵感'), findsOneWidget);
    });
  });
}
