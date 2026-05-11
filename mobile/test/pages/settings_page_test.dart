import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:rizhi/pages/settings_page.dart';
import 'package:rizhi/providers/auth_provider.dart';
import 'package:rizhi/providers/notification_provider.dart';
import 'package:rizhi/services/api_client.dart';
import 'package:rizhi/services/notification_service.dart';

import '../helpers/mock_api_client.dart';

class MockNotificationService extends Mock implements NotificationService {}

class MockAuthNotifier extends Mock implements AuthNotifier {}

void main() {
  group('SettingsPage', () {
    late MockApiClient mockApiClient;
    late SharedPreferences prefs;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      prefs = await SharedPreferences.getInstance();
      mockApiClient = MockApiClient();
    });

    Widget createTestWidget() {
      return ProviderScope(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
        child: const MaterialApp(
          home: SettingsPage(),
        ),
      );
    }

    testWidgets('renders page title and key elements',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      // 验证标题
      expect(find.text('设置'), findsOneWidget);

      // 验证通知开关
      expect(find.text('到期任务提醒'), findsOneWidget);

      // 验证退出登录按钮
      expect(find.text('退出登录'), findsOneWidget);

      // 验证应用名称显示
      expect(find.text('日知'), findsOneWidget);
    });

    testWidgets('notification switch shows correct initial state',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      // 默认关闭
      final switchWidget = tester.widget<SwitchListTile>(
        find.byType(SwitchListTile),
      );
      expect(switchWidget.value, false);

      // 显示「已关闭」
      expect(find.text('已关闭'), findsOneWidget);
    });

    testWidgets('notification switch reflects enabled state from prefs',
        (WidgetTester tester) async {
      // 模拟已启用
      await prefs.setBool('notification_enabled', true);

      await tester.pumpWidget(createTestWidget());

      // 显示「已开启」
      expect(find.text('已开启'), findsOneWidget);
    });

    testWidgets('logout button is present and tappable',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      // 验证退出登录按钮存在
      final logoutTile = find.byType(ListTile);
      final logoutTiles = tester.widgetList<ListTile>(logoutTile).where(
        (tile) =>
            tile.leading != null &&
            tile.leading is Icon &&
            (tile.leading as Icon).icon == Icons.logout,
      );
      expect(logoutTiles.length, 1);
    });

    testWidgets('shows version info', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      expect(find.text('版本'), findsOneWidget);
      expect(find.text('1.0.0'), findsOneWidget);
    });

    testWidgets('shows section headers', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      expect(find.text('通知'), findsOneWidget);
      expect(find.text('账户'), findsOneWidget);
      expect(find.text('关于'), findsOneWidget);
    });

    testWidgets('notification switch is a SwitchListTile',
        (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      expect(find.byType(SwitchListTile), findsOneWidget);
    });

    testWidgets('has notification icon', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      expect(find.byIcon(Icons.notifications_outlined), findsOneWidget);
    });

    testWidgets('has logout icon', (WidgetTester tester) async {
      await tester.pumpWidget(createTestWidget());

      expect(find.byIcon(Icons.logout), findsOneWidget);
    });
  });
}
