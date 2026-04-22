import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:growth_assistant/main.dart';

void main() {
  testWidgets('App redirects to login when unauthenticated',
      (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: GrowthApp()));
    await tester.pumpAndSettle();

    // 未认证时应重定向到登录页
    expect(find.text('个人成长助手'), findsOneWidget);
    expect(find.text('登录'), findsOneWidget);
  });

  testWidgets('Login page has username and password fields',
      (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: GrowthApp()));
    await tester.pumpAndSettle();

    // 登录页应包含用户名和密码输入框
    expect(find.byType(TextField), findsNWidgets(2));
  });
}
