import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:rizhi/config/constants.dart';
import 'package:rizhi/models/entry.dart';
import 'package:rizhi/pages/notes_page.dart';
import 'package:rizhi/providers/notes_provider.dart';
import 'package:rizhi/widgets/skeleton_loading.dart';

// 测试用 Entry 工厂
Entry _makeNote({
  required String id,
  String title = 'Note',
  String? content,
}) {
  return Entry(
    id: id,
    title: '$title $id',
    category: AppConstants.categoryNote,
    content: content,
  );
}

// Fake NotesNotifier，直接返回预设状态
class _FakeNotesNotifier extends NotesNotifier {
  final List<Entry> _entries;
  final bool _isLoading;
  final String? _error;

  _FakeNotesNotifier({
    required List<Entry> entries,
    required bool isLoading,
    String? error,
  })  : _entries = entries,
        _isLoading = isLoading,
        _error = error;

  @override
  NotesState build() {
    return NotesState(
      entries: _entries,
      isLoading: _isLoading,
      error: _error,
    );
  }

  @override
  Future<void> fetchNotes() async {}

  @override
  Future<void> searchNotes(String query) async {}
}

// 构建测试用的 GoRouter
GoRouter _testRouter() {
  return GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => const NotesPage(),
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
Future<void> _pumpNotesPage(
  WidgetTester tester, {
  List<Entry> entries = const [],
  bool isLoading = false,
  String? error,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        notesProvider.overrideWith(
          () => _FakeNotesNotifier(
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

// Tracking NotesNotifier for debounce tests
class _TrackingNotesNotifier extends NotesNotifier {
  final List<Entry> _entries;
  int fetchNotesCallCount = 0;
  final List<String> searchNotesCalls = [];

  _TrackingNotesNotifier({required List<Entry> entries})
      : _entries = entries;

  @override
  NotesState build() => NotesState(entries: _entries);

  @override
  Future<void> fetchNotes() async {
    fetchNotesCallCount++;
  }

  @override
  Future<void> searchNotes(String query) async {
    searchNotesCalls.add(query);
  }
}

Future<_TrackingNotesNotifier> _pumpNotesPageTracking(
  WidgetTester tester, {
  List<Entry> entries = const [],
}) async {
  late _TrackingNotesNotifier notifier;
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        notesProvider.overrideWith(() {
          return notifier = _TrackingNotesNotifier(entries: entries);
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
  group('NotesPage', () {
    testWidgets('空列表显示空状态引导文案', (WidgetTester tester) async {
      await _pumpNotesPage(tester, entries: []);

      expect(find.text('暂无笔记'), findsOneWidget);
      expect(
        find.text('记录你的学习心得和思考'),
        findsOneWidget,
      );
    });

    testWidgets('错误状态显示错误信息和重试按钮', (WidgetTester tester) async {
      await _pumpNotesPage(
        tester,
        entries: [],
        error: '网络连接失败',
      );

      expect(find.text('网络连接失败'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    testWidgets('加载中显示进度指示器', (WidgetTester tester) async {
      await _pumpNotesPage(tester, entries: [], isLoading: true);

      expect(find.byType(SkeletonLoading), findsWidgets);
    });

    testWidgets('笔记列表渲染标题', (WidgetTester tester) async {
      final notes = [
        _makeNote(id: '1', title: 'Flutter 笔记'),
        _makeNote(id: '2', title: 'Dart 笔记'),
      ];

      await _pumpNotesPage(tester, entries: notes);

      expect(find.text('Flutter 笔记 1'), findsOneWidget);
      expect(find.text('Dart 笔记 2'), findsOneWidget);
    });

    testWidgets('显示搜索框', (WidgetTester tester) async {
      await _pumpNotesPage(tester, entries: []);

      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('搜索笔记...'), findsOneWidget);
    });

    testWidgets('笔记内容预览显示', (WidgetTester tester) async {
      final notes = [
        _makeNote(
          id: '1',
          title: 'Long Note',
          content: '这是一篇很长的笔记内容，用来测试内容预览是否正确显示',
        ),
      ];

      await _pumpNotesPage(tester, entries: notes);

      expect(find.text('这是一篇很长的笔记内容，用来测试内容预览是否正确显示'), findsOneWidget);
    });

    testWidgets('AppBar 标题为"笔记"', (WidgetTester tester) async {
      await _pumpNotesPage(tester, entries: []);

      expect(find.text('笔记'), findsOneWidget);
    });
  });

  group('NotesPage 搜索防抖', () {
    testWidgets('输入搜索文字 300ms 后触发 searchNotes', (tester) async {
      final notifier = await _pumpNotesPageTracking(
        tester,
        entries: [_makeNote(id: '1')],
      );

      await tester.enterText(find.byType(TextField), 'Flutter');

      // 300ms 内不应触发
      await tester.pump(const Duration(milliseconds: 100));
      expect(notifier.searchNotesCalls, isEmpty);

      // 300ms 后触发
      await tester.pump(const Duration(milliseconds: 300));
      expect(notifier.searchNotesCalls, ['Flutter']);
    });

    testWidgets('清空搜索框立即触发 fetchNotes', (tester) async {
      final notifier = await _pumpNotesPageTracking(
        tester,
        entries: [_makeNote(id: '1')],
      );

      // 输入搜索文字
      await tester.enterText(find.byType(TextField), 'Flutter');
      await tester.pump();

      // 清空搜索框 → onChanged('') → immediateRun → fetchNotes
      await tester.enterText(find.byType(TextField), '');
      await tester.pump();

      // fetchNotes: 1 from initState + 1 from clear
      expect(notifier.fetchNotesCallCount, 2);
    });

    testWidgets('快速连续输入只触发最后一次 searchNotes', (tester) async {
      final notifier = await _pumpNotesPageTracking(
        tester,
        entries: [_makeNote(id: '1')],
      );

      await tester.enterText(find.byType(TextField), 'F');
      await tester.pump(const Duration(milliseconds: 100));
      await tester.enterText(find.byType(TextField), 'Fl');
      await tester.pump(const Duration(milliseconds: 100));
      await tester.enterText(find.byType(TextField), 'Flu');
      await tester.pump(const Duration(milliseconds: 100));

      // debounce 还未触发
      expect(notifier.searchNotesCalls, isEmpty);

      // 等 300ms 让最后一次 debounce 触发
      await tester.pump(const Duration(milliseconds: 300));
      expect(notifier.searchNotesCalls, ['Flu']);
    });
  });
}
