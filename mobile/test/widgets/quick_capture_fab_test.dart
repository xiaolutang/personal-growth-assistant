import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:rizhi/providers/auth_provider.dart';
import 'package:rizhi/providers/entry_provider.dart';
import 'package:rizhi/services/api_client.dart';
import 'package:rizhi/widgets/bottom_nav.dart';
import 'package:rizhi/widgets/quick_capture_fab.dart';


/// Fake ApiClient for tests
class _FakeApiClient extends ApiClient {
  _FakeApiClient() : super(baseUrl: 'http://fake.test');

  bool createEntryShouldSucceed = true;
  Map<String, dynamic>? lastCreateEntryData;

  @override
  Future<Response<T>> createEntry<T>({
    required Map<String, dynamic> data,
  }) {
    lastCreateEntryData = data;
    if (createEntryShouldSucceed) {
      return Future.value(Response<T>(
        requestOptions: RequestOptions(path: '/entries'),
        statusCode: 201,
        data: <String, dynamic>{
          'id': 'test-id',
          'title': data['title'],
          'category': data['category'],
        } as T,
      ),);
    }
    throw DioException(
      requestOptions: RequestOptions(path: '/entries'),
      type: DioExceptionType.badResponse,
      response: Response(
        requestOptions: RequestOptions(path: '/entries'),
        statusCode: 500,
      ),
    );
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
  }) {
    return Future.value(Response<T>(
      requestOptions: RequestOptions(path: '/entries'),
      statusCode: 200,
      data: <String, dynamic>{'entries': <Map<String, dynamic>>[]} as T,
    ),);
  }
}

/// Build test GoRouter with BottomNavShell wrapping a child page
GoRouter _testRouter({
  required Widget child,
  String initialLocation = '/tasks',
}) {
  return GoRouter(
    initialLocation: initialLocation,
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const Scaffold(body: Text('LoginPage')),
      ),
      ShellRoute(
        builder: (context, state, child) => BottomNavShell(child: child),
        routes: [
          GoRoute(
            path: '/',
            builder: (context, state) => child,
          ),
          GoRoute(
            path: '/tasks',
            builder: (context, state) => child,
          ),
          GoRoute(
            path: '/entries/:id',
            builder: (context, state) =>
                const Scaffold(body: Text('EntryDetail')),
          ),
        ],
      ),
    ],
  );
}

void main() {
  late _FakeApiClient fakeApiClient;

  setUp(() {
    fakeApiClient = _FakeApiClient();
  });

  group('QuickCaptureFAB 展开收起', () {
    testWidgets('FAB 在 ShellRoute 子页面可见', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: const Scaffold(body: Text('Tasks')),
            ),
          ),
        ),
      );

      expect(find.byType(QuickCaptureFAB), findsOneWidget);
      // 主 FAB 按钮（hybrid_fab）
      expect(find.byType(FloatingActionButton), findsOneWidget);
    });

    testWidgets('点击 FAB 展开三个子按钮', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: const Scaffold(body: Text('Tasks')),
            ),
          ),
        ),
      );

      // 初始状态：子按钮不可见
      expect(find.text('记灵感'), findsNothing);
      expect(find.text('建任务'), findsNothing);
      expect(find.text('AI 创建'), findsNothing);

      // 点击主 FAB 展开
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // 展开后：三个子按钮可见
      expect(find.text('记灵感'), findsOneWidget);
      expect(find.text('建任务'), findsOneWidget);
      expect(find.text('AI 创建'), findsOneWidget);
    });

    testWidgets('再次点击 FAB 收起子按钮', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: const Scaffold(body: Text('Tasks')),
            ),
          ),
        ),
      );

      // 展开
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      expect(find.text('记灵感'), findsOneWidget);

      // 再次点击收起（使用 heroTag 定位主 FAB）
      await tester.tap(find.byWidgetPredicate(
        (w) => w is FloatingActionButton && w.heroTag == 'hybrid_fab',
      ));
      await tester.pumpAndSettle();
      expect(find.text('记灵感'), findsNothing);
    });

    testWidgets('点击空白区域收起 FAB', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: const Scaffold(body: Text('Tasks')),
            ),
          ),
        ),
      );

      // 展开
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      expect(find.text('记灵感'), findsOneWidget);

      // 点击空白区域（屏幕左上角）
      await tester.tapAt(Offset.zero);
      await tester.pumpAndSettle();

      // FAB 应收起
      expect(find.text('记灵感'), findsNothing);
    });
  });

  group('记灵感入口', () {
    testWidgets('点击「记灵感」弹出灵感 BottomSheet',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: const Scaffold(body: Text('Tasks')),
            ),
          ),
        ),
      );

      // 展开 FAB
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // 点击「记灵感」子按钮
      await tester.tap(find.byIcon(Icons.lightbulb_outline));
      await tester.pumpAndSettle();

      // BottomSheet 应该弹出
      expect(find.text('快速捕获灵感'), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('保存'), findsOneWidget);
    });

    testWidgets('灵感 BottomSheet 关闭交互', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: const Scaffold(body: Text('Tasks')),
            ),
          ),
        ),
      );

      // 展开并点击记灵感
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.lightbulb_outline));
      await tester.pumpAndSettle();

      expect(find.text('快速捕获灵感'), findsOneWidget);

      // 关闭
      await tester.tap(find.byIcon(Icons.close));
      await tester.pumpAndSettle();

      expect(find.text('快速捕获灵感'), findsNothing);
    });

    testWidgets('输入内容提交 -> 创建 inbox 条目',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: const Scaffold(body: Text('Tasks')),
            ),
          ),
        ),
      );

      // 展开并点击记灵感
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.lightbulb_outline));
      await tester.pumpAndSettle();

      // 输入并提交
      await tester.enterText(find.byType(TextField), '我的灵感笔记');
      await tester.pump();
      await tester.tap(find.text('保存'));
      await tester.pumpAndSettle();

      // 验证 API 调用
      expect(fakeApiClient.lastCreateEntryData, isNotNull);
      expect(fakeApiClient.lastCreateEntryData!['category'], 'inbox');
      expect(fakeApiClient.lastCreateEntryData!['title'], '我的灵感笔记');
    });

    testWidgets('空输入时提交按钮禁用', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: const Scaffold(body: Text('Tasks')),
            ),
          ),
        ),
      );

      // 展开并点击记灵感
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.lightbulb_outline));
      await tester.pumpAndSettle();

      // 保存按钮应禁用
      final saveButton = tester.widget<FilledButton>(
        find.byType(FilledButton),
      );
      expect(saveButton.enabled, isFalse);

      // 输入空格仍禁用
      await tester.enterText(find.byType(TextField), '   ');
      await tester.pump();
      final saveButton2 = tester.widget<FilledButton>(
        find.byType(FilledButton),
      );
      expect(saveButton2.enabled, isFalse);

      // 输入有效内容启用
      await tester.enterText(find.byType(TextField), 'hello');
      await tester.pump();
      final saveButton3 = tester.widget<FilledButton>(
        find.byType(FilledButton),
      );
      expect(saveButton3.enabled, isTrue);
    });

    testWidgets('API 失败 -> 错误提示 + 弹窗保持打开',
        (WidgetTester tester) async {
      fakeApiClient.createEntryShouldSucceed = false;

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: const Scaffold(body: Text('Tasks')),
            ),
          ),
        ),
      );

      // 展开并点击记灵感
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.lightbulb_outline));
      await tester.pumpAndSettle();

      // 输入并提交
      await tester.enterText(find.byType(TextField), '失败的灵感');
      await tester.pump();
      await tester.tap(find.text('保存'));
      await tester.pumpAndSettle();

      // BottomSheet 应保持打开
      expect(find.text('快速捕获灵感'), findsOneWidget);
      // 错误 SnackBar
      expect(find.text('保存失败，请重试'), findsOneWidget);
    });

    testWidgets('成功提交后关闭弹窗并显示 SnackBar',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: const Scaffold(body: Text('Tasks')),
            ),
          ),
        ),
      );

      // 展开并点击记灵感
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      await tester.tap(find.byIcon(Icons.lightbulb_outline));
      await tester.pumpAndSettle();

      // 输入并提交
      await tester.enterText(find.byType(TextField), '成功的灵感');
      await tester.pump();
      await tester.tap(find.text('保存'));
      await tester.pumpAndSettle();

      // BottomSheet 关闭
      expect(find.text('快速捕获灵感'), findsNothing);
      // 成功 SnackBar
      expect(find.text('灵感已保存'), findsOneWidget);
    });
  });

  group('BottomNavShell FAB visibility', () {
    testWidgets('FAB 在条目详情页不显示', (WidgetTester tester) async {
      final router = GoRouter(
        initialLocation: '/tasks',
        routes: [
          ShellRoute(
            builder: (context, state, child) => BottomNavShell(child: child),
            routes: [
              GoRoute(
                path: '/tasks',
                builder: (context, state) =>
                    const Scaffold(body: Text('Tasks')),
              ),
              GoRoute(
                path: '/entries/:id',
                builder: (context, state) =>
                    const Scaffold(body: Text('EntryDetail')),
              ),
            ],
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(routerConfig: router),
        ),
      );

      // On tasks page - FAB visible
      expect(find.byType(QuickCaptureFAB), findsOneWidget);

      // Navigate to entry detail
      router.go('/entries/123');
      await tester.pumpAndSettle();

      // FAB should not be visible on entry detail page
      expect(find.byType(QuickCaptureFAB), findsNothing);
    });

    testWidgets('TodayPage 显示全局 FAB', (WidgetTester tester) async {
      final router = GoRouter(
        initialLocation: '/',
        routes: [
          ShellRoute(
            builder: (context, state, child) => BottomNavShell(child: child),
            routes: [
              GoRoute(
                path: '/',
                builder: (context, state) => const Scaffold(
                  body: Text('Today'),
                ),
              ),
            ],
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            apiClientProvider.overrideWithValue(fakeApiClient),
          ],
          child: MaterialApp.router(routerConfig: router),
        ),
      );

      // 全局唯一 FAB（由 Shell 层 DraggableFAB 管理）
      expect(find.byType(QuickCaptureFAB), findsOneWidget);
    });
  });

  group('EntryListNotifier.createInboxEntry', () {
    test('成功创建返回 true', () async {
      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(fakeApiClient),
        ],
      );
      addTearDown(container.dispose);

      final result = await container
          .read(entryListProvider.notifier)
          .createInboxEntry('测试灵感');

      expect(result, true);
      expect(fakeApiClient.lastCreateEntryData!['category'], 'inbox');
      expect(fakeApiClient.lastCreateEntryData!['title'], '测试灵感');
    });

    test('API 失败返回 false', () async {
      fakeApiClient.createEntryShouldSucceed = false;

      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(fakeApiClient),
        ],
      );
      addTearDown(container.dispose);

      final result = await container
          .read(entryListProvider.notifier)
          .createInboxEntry('失败测试');

      expect(result, false);
    });

    test('标题会被 trim', () async {
      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(fakeApiClient),
        ],
      );
      addTearDown(container.dispose);

      await container
          .read(entryListProvider.notifier)
          .createInboxEntry('  前后有空格  ');

      expect(fakeApiClient.lastCreateEntryData!['title'], '前后有空格');
    });
  });
}
