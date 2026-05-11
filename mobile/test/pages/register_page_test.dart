import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rizhi/pages/register_page.dart';

void main() {
  group('RegisterPage Widget', () {
    testWidgets('renders register form elements', (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: RegisterPage(),
          ),
        ),
      );

      // 验证标题
      expect(find.text('创建账号'), findsOneWidget);

      // 验证输入框：用户名 + 密码 + 确认密码
      expect(find.byType(TextFormField), findsNWidgets(3));

      // 验证注册按钮
      expect(find.text('注册'), findsOneWidget);

      // 验证「去登录」链接
      expect(find.text('去登录'), findsOneWidget);
    });

    testWidgets('shows validation errors on empty submit',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: RegisterPage(),
          ),
        ),
      );

      // 点击注册按钮（空表单）
      await tester.tap(find.text('注册'));
      await tester.pump();

      // 应显示验证错误
      expect(find.text('请输入用户名'), findsOneWidget);
      expect(find.text('请输入密码'), findsOneWidget);
      expect(find.text('请确认密码'), findsOneWidget);
    });

    testWidgets('shows error for short password', (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: RegisterPage(),
          ),
        ),
      );

      // 填写用户名和短密码
      await tester.enterText(
        find.widgetWithText(TextFormField, '用户名'),
        'testuser',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, '密码'),
        '123',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, '确认密码'),
        '123',
      );

      // 点击注册
      await tester.tap(find.text('注册'));
      await tester.pump();

      // 应显示密码长度错误
      expect(find.text('密码长度不能少于6位'), findsOneWidget);
    });

    testWidgets('shows error for mismatched passwords',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: RegisterPage(),
          ),
        ),
      );

      // 填写用户名和不一致的密码
      await tester.enterText(
        find.widgetWithText(TextFormField, '用户名'),
        'testuser',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, '密码'),
        'password123',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, '确认密码'),
        'password456',
      );

      // 点击注册
      await tester.tap(find.text('注册'));
      await tester.pump();

      // 应显示密码不一致错误
      expect(find.text('两次密码输入不一致'), findsOneWidget);
    });

    testWidgets('password fields obscure text by default',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: RegisterPage(),
          ),
        ),
      );

      // 找到所有 TextField
      final textFields = find.byType(TextField);
      expect(textFields, findsNWidgets(3));

      // 密码字段（第二和第三个）应该 obscure
      final passwordWidget = tester.widget<TextField>(textFields.at(1));
      expect(passwordWidget.obscureText, true);

      final confirmPasswordWidget = tester.widget<TextField>(textFields.at(2));
      expect(confirmPasswordWidget.obscureText, true);
    });

    testWidgets('has password visibility toggles',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: RegisterPage(),
          ),
        ),
      );

      // 默认显示两个 visibility_off 图标
      expect(find.byIcon(Icons.visibility_off), findsNWidgets(2));

      // 点击第一个切换（密码）
      await tester.tap(find.byIcon(Icons.visibility_off).first);
      await tester.pump();

      // 应显示一个 visibility 和一个 visibility_off
      expect(find.byIcon(Icons.visibility), findsOneWidget);
      expect(find.byIcon(Icons.visibility_off), findsOneWidget);
    });

    testWidgets('has app icon', (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: RegisterPage(),
          ),
        ),
      );

      expect(find.byIcon(Icons.auto_awesome), findsOneWidget);
    });

    testWidgets('has go-login link', (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: RegisterPage(),
          ),
        ),
      );

      expect(find.text('已有账号？'), findsOneWidget);
      expect(find.text('去登录'), findsOneWidget);
    });

    testWidgets('all form fields have correct labels',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: RegisterPage(),
          ),
        ),
      );

      // 验证所有字段标签
      expect(find.widgetWithText(TextFormField, '用户名'), findsOneWidget);
      expect(find.widgetWithText(TextFormField, '密码'), findsOneWidget);
      expect(find.widgetWithText(TextFormField, '确认密码'), findsOneWidget);
    });

    testWidgets('register button is present and tappable',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: RegisterPage(),
          ),
        ),
      );

      final registerButton = find.widgetWithText(FilledButton, '注册');
      expect(registerButton, findsOneWidget);

      // 验证按钮可点击（空表单触发验证）
      await tester.tap(registerButton);
      await tester.pump();
      expect(find.text('请输入用户名'), findsOneWidget);
    });
  });
}
