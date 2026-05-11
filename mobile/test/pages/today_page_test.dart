import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rizhi/models/entry.dart';
import 'package:rizhi/pages/today_page.dart';
import 'package:rizhi/providers/auth_provider.dart';
import 'package:rizhi/providers/today_provider.dart';
import 'package:rizhi/services/api_client.dart';

/// Fake TodayNotifier that tracks loadData calls
class _FakeTodayNotifier extends TodayNotifier {
  final TodayState _fakeState;

  _FakeTodayNotifier(this._fakeState);

  @override
  TodayState build() => _fakeState;

  @override
  Future<void> loadData() async {
    // no-op: skip API calls in tests
  }
}

/// Tracking TodayNotifier that records loadData call count
class _TrackingTodayNotifier extends TodayNotifier {
  int loadDataCallCount = 0;

  @override
  TodayState build() => const TodayState();

  @override
  Future<void> loadData() async {
    loadDataCallCount++;
  }
}

/// Mutable TodayNotifier that allows state updates for testing refresh behavior
class _MutableTodayNotifier extends TodayNotifier {
  TodayState _state;

  _MutableTodayNotifier(this._state);

  @override
  TodayState build() => _state;

  void updateState(TodayState newState) {
    _state = newState;
    state = newState;
  }

  @override
  Future<void> loadData() async {
    // no-op in tests
  }
}

/// Fake ApiClient for provider-level tests
class _FakeApiClient extends ApiClient {
  _FakeApiClient() : super(baseUrl: 'http://fake.test');

  @override
  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) {
    return Future.value(Response<T>(
      requestOptions: RequestOptions(path: path),
      statusCode: 201,
      data: <String, dynamic>{
        'id': 'test-id',
        'title': 'test',
      } as T,
    ),);
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

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) {
    return Future.value(Response<T>(
      requestOptions: RequestOptions(path: path),
      statusCode: 200,
      data: <String, dynamic>{'entries': <Map<String, dynamic>>[]} as T,
    ),);
  }
}

void main() {
  group('TodayPage error state', () {
    testWidgets('shows error state with retry button when load fails', (
      tester,
    ) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(
                const TodayState(error: '加载失败', isLoading: false),
              ),
            ),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // Should show error message
      expect(find.text('加载失败'), findsOneWidget);
      // Should show retry button
      expect(find.text('重试'), findsOneWidget);
    });

    testWidgets('error state is scrollable (supports pull-to-refresh)', (
      tester,
    ) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(
                const TodayState(error: '加载失败', isLoading: false),
              ),
            ),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // The error state should be wrapped in a ListView (scrollable)
      // so RefreshIndicator can work
      expect(find.byType(ListView), findsOneWidget);
      expect(find.byType(RefreshIndicator), findsOneWidget);
    });

    testWidgets('shows content when loaded successfully', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(
                const TodayState(isLoading: false),
              ),
            ),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // Should NOT show error state
      expect(find.text('加载失败'), findsNothing);
      // Should have RefreshIndicator
      expect(find.byType(RefreshIndicator), findsOneWidget);
    });
  });

  group('TodayPage pure dashboard', () {
    testWidgets('no command bar input field', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // No TextField (command bar input)
      expect(find.byType(TextField), findsNothing);
      // No send button
      expect(find.byIcon(Icons.send_rounded), findsNothing);
    });

    testWidgets('no command result cards', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // No AI command result UI elements
      expect(find.text('输入指令或问题...'), findsNothing);
      expect(find.text('在日知中继续对话'), findsNothing);
      expect(find.byIcon(Icons.auto_awesome), findsNothing);
    });

    testWidgets('empty state shows dashboard sections', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // Dashboard sections visible
      expect(find.text('今日进度'), findsOneWidget);
      expect(find.text('今日任务'), findsOneWidget);
      expect(find.text('最近动态'), findsOneWidget);
    });

    testWidgets('dashboard has pull-to-refresh', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(RefreshIndicator), findsOneWidget);
    });

    testWidgets('pull-to-refresh triggers loadData and updates UI', (tester) async {
      // Use a mutable notifier to simulate data change after refresh
      final notifier = _MutableTodayNotifier(const TodayState());
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(() => notifier),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // Initially empty state
      expect(find.text('暂无动态，开始记录你的成长吧'), findsOneWidget);

      // Simulate data loaded after refresh
      notifier.updateState(TodayState(
        recentEntries: [
          Entry(
            id: 'entry-1',
            title: '测试动态',
            category: 'inbox',
            status: 'active',
            createdAt: '2026-05-11T10:00:00',
          ),
        ],
      ));
      await tester.pumpAndSettle();

      // After data update, should show the entry
      expect(find.text('测试动态'), findsOneWidget);
      expect(find.text('暂无动态，开始记录你的成长吧'), findsNothing);
    });
  });

  group('Today refresh on action success', () {
    test('createTask success triggers loadData via FAB callback', () async {
      final fakeApiClient = _FakeApiClient();
      final trackingNotifier = _TrackingTodayNotifier();

      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(fakeApiClient),
          todayProvider.overrideWith(() => trackingNotifier),
        ],
      );
      addTearDown(container.dispose);

      // Simulate createTask success
      final success = await container.read(todayProvider.notifier).createTask('测试任务');
      expect(success, true);

      // createTask itself does NOT call loadData (refresh is caller's responsibility)
      expect(trackingNotifier.loadDataCallCount, 0);

      // Simulate FAB callback explicitly calling loadData after success
      await container.read(todayProvider.notifier).loadData();
      expect(trackingNotifier.loadDataCallCount, 1);
    });

    test('loadData is callable independently', () async {
      final trackingNotifier = _TrackingTodayNotifier();
      final container = ProviderContainer(
        overrides: [
          todayProvider.overrideWith(() => trackingNotifier),
        ],
      );
      addTearDown(container.dispose);

      expect(trackingNotifier.loadDataCallCount, 0);

      await container.read(todayProvider.notifier).loadData();
      expect(trackingNotifier.loadDataCallCount, 1);

      await container.read(todayProvider.notifier).loadData();
      expect(trackingNotifier.loadDataCallCount, 2);
    });
  });
}
