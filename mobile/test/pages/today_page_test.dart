import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rizhi/pages/today_page.dart';
import 'package:rizhi/providers/today_provider.dart';

/// Fake TodayNotifier that skips loadData (no API calls)
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
}
