import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/pages/login_page.dart';

void main() {
  group('LoginPage Widget', () {
    testWidgets('renders login form elements', (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: LoginPage(),
          ),
        ),
      );

      // 验证标题
      expect(find.text('个人成长助手'), findsOneWidget);

      // 验证输入框
      expect(find.byType(TextFormField), findsNWidgets(2));

      // 验证登录按钮
      expect(find.text('登录'), findsOneWidget);
    });

    testWidgets('shows validation errors on empty submit',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: LoginPage(),
          ),
        ),
      );

      // 点击登录按钮（空表单）
      await tester.tap(find.text('登录'));
      await tester.pump();

      // 应显示验证错误
      expect(find.text('请输入用户名'), findsOneWidget);
      expect(find.text('请输入密码'), findsOneWidget);
    });

    testWidgets('username field accepts text input',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: LoginPage(),
          ),
        ),
      );

      // 找到用户名输入框
      final usernameField = find.widgetWithText(TextFormField, '用户名');
      expect(usernameField, findsOneWidget);

      // 输入用户名
      await tester.enterText(usernameField, 'testuser');

      // 验证输入
      expect(find.text('testuser'), findsOneWidget);
    });

    testWidgets('password field obscures text by default',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: LoginPage(),
          ),
        ),
      );

      // 找到密码输入框（第二个 TextFormField）
      final textFields = find.byType(TextField);
      expect(textFields, findsNWidgets(2));

      // 获取密码字段（第二个）- TextField 有 obscureText
      final passwordWidget = tester.widget<TextField>(textFields.last);
      expect(passwordWidget.obscureText, true);
    });

    testWidgets('has app icon', (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: LoginPage(),
          ),
        ),
      );

      expect(find.byIcon(Icons.auto_awesome), findsOneWidget);
    });

    testWidgets('has password visibility toggle', (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: LoginPage(),
          ),
        ),
      );

      // 默认显示 visibility_off 图标
      expect(find.byIcon(Icons.visibility_off), findsOneWidget);

      // 点击切换
      await tester.tap(find.byIcon(Icons.visibility_off));
      await tester.pump();

      // 应显示 visibility 图标
      expect(find.byIcon(Icons.visibility), findsOneWidget);
    });
  });
}
