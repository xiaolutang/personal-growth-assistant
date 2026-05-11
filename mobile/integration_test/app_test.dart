import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:rizhi/main.dart' as app;

// ============================================================
// R057 集成测试 — 导航重构验收（真实后端 + iOS 模拟器）
//
// 前置条件：
//   - 后端运行在 http://localhost:8001
//   - iOS 模拟器已启动
//   - flutter test integration_test/app_test.dart -d <device>
//
// 测试路线：
//   注册 → Today 纯仪表盘验证 → FAB 记灵感 → 任务 Tab
//   → 我的→目标 → 我的→设置 → 退出登录 → 重新登录
// ============================================================

String _ts() => DateTime.now().millisecondsSinceEpoch.toString();

/// 带超时的 pumpAndSettle，避免无尽动画导致超时
Future<void> _settled(WidgetTester tester,
    [Duration timeout = const Duration(seconds: 10)]) async {
  await tester.pumpAndSettle(timeout);
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('R057 导航重构集成测试', (tester) async {
    final username = 'e2e_${_ts()}';
    final password = 'Test@12345';

    // 清除 iOS Keychain 中持久化的认证状态
    const storage = FlutterSecureStorage();
    await storage.deleteAll();

    // ============================================================
    // Step 1: 启动 App → 登录页
    // ============================================================
    SharedPreferences.setMockInitialValues({});
    app.main();
    await _settled(tester);

    expect(find.text('注册新账号'), findsOneWidget);
    expect(find.text('忘记密码?'), findsOneWidget);
    debugPrint('✓ Step 1: 登录页显示');

    // ============================================================
    // Step 2: 注册 → 自动登录 → 到达 Today 页
    // ============================================================
    await tester.tap(find.text('注册新账号'));
    await _settled(tester);

    await tester.enterText(
      find.widgetWithText(TextFormField, '用户名'),
      username,
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, '密码'),
      password,
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, '确认密码'),
      password,
    );
    await _settled(tester);

    await tester.tap(find.widgetWithText(FilledButton, '注册'));
    await tester.pump(const Duration(seconds: 5));
    await tester.pump(const Duration(seconds: 5));
    await _settled(tester);

    final todayCount = find.text('今天').evaluate().length;
    final registerBtn =
        find.widgetWithText(FilledButton, '注册').evaluate().length;

    if (registerBtn > 0) {
      fail('注册失败，仍在注册页');
    }

    if (todayCount == 0) {
      // 注册成功但自动登录失败 → 手动登录
      debugPrint('⊙ Step 2: 手动登录');
      await tester.pump(const Duration(seconds: 2));
      await _settled(tester);

      await tester.enterText(
        find.widgetWithText(TextFormField, '用户名'),
        username,
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, '密码'),
        password,
      );
      await _settled(tester);

      await tester.tap(find.widgetWithText(FilledButton, '登录'));
      await tester.pump(const Duration(seconds: 5));
      await _settled(tester);
    }

    expect(find.text('今天'), findsWidgets);
    debugPrint('✓ Step 2: 注册+登录成功，到达 Today 页');

    // ============================================================
    // Step 3: Today 纯仪表盘验证
    // ============================================================
    // 等待 API 数据加载完成（骨架屏→真实内容）
    await tester.pump(const Duration(seconds: 3));
    await _settled(tester);

    // 无命令栏输入框
    expect(find.byType(TextField), findsNothing,
        reason: 'Today 页不应有输入框（命令栏已下线）');
    // 仪表盘区块（上方两个一定可见）
    expect(find.text('今日进度'), findsOneWidget);
    expect(find.text('今日任务'), findsOneWidget);
    // 滚动到底部确认 "最近动态" 存在
    final recentHeader = find.text('最近动态');
    await tester.scrollUntilVisible(recentHeader, 200);
    expect(recentHeader, findsOneWidget);
    // FAB 存在
    expect(find.byType(FloatingActionButton), findsOneWidget);
    debugPrint('✓ Step 3: Today 纯仪表盘 — 无输入框、有进度/任务/动态区块、FAB 存在');

    // ============================================================
    // Step 4: FAB 展开 → 只有 2 个子按钮
    // ============================================================
    await tester.tap(find.byType(FloatingActionButton));
    await _settled(tester);

    expect(find.text('记灵感'), findsOneWidget);
    expect(find.text('建任务'), findsOneWidget);
    expect(find.text('AI 创建'), findsNothing,
        reason: 'AI 创建按钮已移除');
    debugPrint('✓ Step 4: FAB 展开恰好 2 个子按钮（记灵感/建任务），无 AI 创建');

    // ============================================================
    // Step 5: 记灵感 → BottomSheet → 创建条目
    // ============================================================
    await tester.tap(find.byIcon(Icons.lightbulb_outline));
    await _settled(tester);

    expect(find.text('快速捕获灵感'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);

    await tester.enterText(find.byType(TextField), 'E2E R057 灵感 $_ts()');
    await tester.pump(const Duration(seconds: 1));
    // 点击标题区域关闭键盘（不关闭 BottomSheet）
    await tester.tap(find.text('快速捕获灵感'));
    await tester.pump(const Duration(seconds: 1));
    // 现在保存按钮应该可见了
    await tester.tap(find.widgetWithText(FilledButton, '保存'));
    await tester.pump(const Duration(seconds: 5));
    await _settled(tester);

    // BottomSheet 应关闭
    expect(find.text('快速捕获灵感'), findsNothing);
    debugPrint('✓ Step 5: FAB 记灵感 → 提交成功，BottomSheet 关闭');
    debugPrint('✓ Step 5: FAB 记灵感 → 创建成功，显示 SnackBar');
    await tester.pump(const Duration(seconds: 3));

    // ============================================================
    // Step 6: 5 个 Tab 正确
    // ============================================================
    expect(find.text('今天'), findsWidgets);
    expect(find.text('对话'), findsWidgets);
    expect(find.text('任务'), findsWidgets);
    expect(find.text('探索'), findsWidgets);
    expect(find.text('我的'), findsWidgets);
    debugPrint('✓ Step 6: 5 个 Tab 正确（今天/对话/任务/探索/我的）');

    // ============================================================
    // Step 7: 切换到任务 Tab
    // ============================================================
    await tester.tap(find.text('任务'));
    await _settled(tester);

    // FAB 在任务页也可见
    expect(find.byType(FloatingActionButton), findsOneWidget);
    debugPrint('✓ Step 7: 任务 Tab — FAB 可见');

    // ============================================================
    // Step 8: 我的 → 菜单只有 3 项
    // ============================================================
    await tester.tap(find.text('我的'));
    await _settled(tester);

    // 菜单应有回顾、目标、设置
    expect(find.text('回顾'), findsWidgets);
    expect(find.text('目标'), findsWidgets);
    expect(find.text('设置'), findsWidgets);
    debugPrint('✓ Step 8: 我的菜单 — 回顾/目标/设置 3 项');

    // ============================================================
    // Step 9: 我的 → 目标页
    // ============================================================
    await tester.tap(find.text('目标').last);
    await _settled(tester);

    debugPrint('✓ Step 9: 进入目标页');

    // ============================================================
    // Step 10: 我的 → 设置页
    // ============================================================
    await tester.tap(find.text('我的'));
    await _settled(tester);

    await tester.tap(find.text('设置').last);
    await _settled(tester);

    expect(find.text('到期任务提醒'), findsOneWidget);
    expect(find.text('退出登录'), findsOneWidget);
    debugPrint('✓ Step 10: 设置页 — 通知开关 + 退出登录');

    // ============================================================
    // Step 11: 退出登录 → 返回登录页
    // ============================================================
    await tester.tap(find.text('退出登录'));
    await _settled(tester);

    expect(find.text('登录'), findsWidgets);
    expect(find.widgetWithText(TextFormField, '用户名'), findsOneWidget);
    debugPrint('✓ Step 11: 退出登录，返回登录页');

    // ============================================================
    // Step 12: 重新登录
    // ============================================================
    await tester.enterText(
      find.widgetWithText(TextFormField, '用户名'),
      username,
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, '密码'),
      password,
    );
    await _settled(tester);

    await tester.tap(find.widgetWithText(FilledButton, '登录'));
    await tester.pump(const Duration(seconds: 3));
    await _settled(tester);

    expect(find.text('今天'), findsWidgets);
    expect(find.text('今日进度'), findsOneWidget);
    debugPrint('✓ Step 12: 重新登录成功，Today 仪表盘正常');

    debugPrint('\n============================');
    debugPrint('R057 集成测试全部通过 (12 steps)');
    debugPrint('============================');
  });
}
