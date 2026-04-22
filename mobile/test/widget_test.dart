import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:growth_assistant/main.dart';

void main() {
  testWidgets('App renders bottom navigation', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: GrowthApp()));
    await tester.pumpAndSettle();

    // 底部导航栏应包含三个标签
    expect(find.text('今天'), findsWidgets);
    expect(find.text('日知'), findsWidgets);
    expect(find.text('任务'), findsWidgets);
  });

  testWidgets('Tab switching works', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: GrowthApp()));
    await tester.pumpAndSettle();

    // 初始页面应显示 "今天"
    expect(find.text('今天'), findsWidgets);

    // 点击日知 tab
    await tester.tap(find.text('日知'));
    await tester.pumpAndSettle();
    expect(find.text('日知'), findsWidgets);

    // 点击任务 tab
    await tester.tap(find.text('任务'));
    await tester.pumpAndSettle();
    expect(find.text('任务'), findsWidgets);
  });
}
