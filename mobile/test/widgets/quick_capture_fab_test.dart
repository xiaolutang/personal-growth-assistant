import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:growth_assistant/providers/auth_provider.dart';
import 'package:growth_assistant/providers/entry_provider.dart';
import 'package:growth_assistant/services/api_client.dart';
import 'package:growth_assistant/widgets/bottom_nav.dart';
import 'package:growth_assistant/widgets/quick_capture_fab.dart';


/// Fake ApiClient for tests
class _FakeApiClient extends ApiClient {
  _FakeApiClient() : super(baseUrl: 'http://fake.test');

  bool createEntryShouldSucceed = true;
  Map<String, dynamic>? lastCreateEntryData;

  @override
  Future<Response<T>> createEntry<T>({required Map<String, dynamic> data}) {
    lastCreateEntryData = data;
    if (createEntryShouldSucceed) {
      return Future.value(Response<T>(
        requestOptions: RequestOptions(path: '/entries'),
        statusCode: 201,
        data: {'id': 'test-id', 'title': data['title'], 'category': data['category']} as T,
      ));
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
      data: {'entries': <Map<String, dynamic>>[]} as T,
    ));
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

  group('QuickCaptureFAB', () {
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

      // FAB should be visible on tasks page (within ShellRoute, not /)
      expect(find.byType(QuickCaptureFAB), findsOneWidget);
      expect(find.byType(FloatingActionButton), findsOneWidget);
    });

    testWidgets('点击 FAB 弹出 BottomSheet', (WidgetTester tester) async {
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

      // Tap FAB
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // BottomSheet should be visible with title and input
      expect(find.text('快速捕获灵感'), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('保存'), findsOneWidget);
    });

    testWidgets('BottomSheet 关闭交互', (WidgetTester tester) async {
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

      // Open bottom sheet
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      expect(find.text('快速捕获灵感'), findsOneWidget);

      // Close by pressing close button
      await tester.tap(find.byIcon(Icons.close));
      await tester.pumpAndSettle();

      expect(find.text('快速捕获灵感'), findsNothing);
    });

    testWidgets('输入内容提交 -> mock POST /entries -> 验证参数',
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

      // Open bottom sheet
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // Enter text
      await tester.enterText(find.byType(TextField), '我的灵感笔记');
      await tester.pump();

      // Submit
      await tester.tap(find.text('保存'));
      await tester.pumpAndSettle();

      // Verify API was called with correct parameters
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

      // Open bottom sheet
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // Find the save button
      final saveButton = tester.widget<FilledButton>(
        find.byType(FilledButton),
      );
      expect(saveButton.enabled, isFalse);

      // Type something then clear - button should still be disabled for whitespace
      await tester.enterText(find.byType(TextField), '   ');
      await tester.pump();

      final saveButton2 = tester.widget<FilledButton>(
        find.byType(FilledButton),
      );
      expect(saveButton2.enabled, isFalse);

      // Type valid text - button should be enabled
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

      // Open bottom sheet
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // Enter text and submit
      await tester.enterText(find.byType(TextField), '失败的灵感');
      await tester.pump();

      await tester.tap(find.text('保存'));
      await tester.pumpAndSettle();

      // BottomSheet should still be visible (not closed)
      expect(find.text('快速捕获灵感'), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);

      // Error SnackBar should be shown
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

      // Open bottom sheet
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // Enter text and submit
      await tester.enterText(find.byType(TextField), '成功的灵感');
      await tester.pump();

      await tester.tap(find.text('保存'));
      await tester.pumpAndSettle();

      // BottomSheet should be closed
      expect(find.text('快速捕获灵感'), findsNothing);

      // Success SnackBar should be shown
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

    testWidgets('FAB 在 TodayPage (/) 不显示 — TodayPage 有独立 QuickActions',
        (WidgetTester tester) async {
      final router = GoRouter(
        initialLocation: '/',
        routes: [
          ShellRoute(
            builder: (context, state, child) => BottomNavShell(child: child),
            routes: [
              GoRoute(
                path: '/',
                builder: (context, state) =>
                    const Scaffold(body: Text('Today')),
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

      // TodayPage has its own QuickActions, so QuickCaptureFAB should not show
      expect(find.byType(QuickCaptureFAB), findsNothing);
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
