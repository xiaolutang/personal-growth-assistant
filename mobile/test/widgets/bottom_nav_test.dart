import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:growth_assistant/widgets/bottom_nav.dart';

// 构建测试用的 GoRouter
GoRouter _testRouter({required Widget child}) {
  return GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => child,
      ),
      GoRoute(
        path: '/chat',
        builder: (context, state) => const Scaffold(body: Text('Chat')),
      ),
      GoRoute(
        path: '/tasks',
        builder: (context, state) => const Scaffold(body: Text('Tasks')),
      ),
      GoRoute(
        path: '/notes',
        builder: (context, state) => const Scaffold(body: Text('Notes')),
      ),
      GoRoute(
        path: '/review',
        builder: (context, state) => const Scaffold(body: Text('Review')),
      ),
      GoRoute(
        path: '/goals',
        builder: (context, state) => const Scaffold(body: Text('Goals')),
      ),
      GoRoute(
        path: '/inbox',
        builder: (context, state) => const Scaffold(body: Text('Inbox')),
      ),
      GoRoute(
        path: '/explore',
        builder: (context, state) => const Scaffold(body: Text('Explore')),
      ),
    ],
  );
}

void main() {
  group('BottomNavShell', () {
    testWidgets('渲染 5 个 NavigationDestination', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp.router(
          routerConfig: _testRouter(
            child: BottomNavShell(child: const SizedBox()),
          ),
        ),
      );

      expect(find.text('今天'), findsOneWidget);
      expect(find.text('日知'), findsOneWidget);
      expect(find.text('任务'), findsOneWidget);
      expect(find.text('笔记'), findsOneWidget);
      expect(find.text('更多'), findsOneWidget);
    });

    testWidgets('默认选中第一个 Tab（今天）', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp.router(
          routerConfig: _testRouter(
            child: BottomNavShell(child: const SizedBox()),
          ),
        ),
      );

      final navBar = tester.widget<NavigationBar>(
        find.byType(NavigationBar),
      );
      expect(navBar.selectedIndex, equals(0));
    });

    testWidgets('点击更多 Tab 弹出底部菜单', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp.router(
          routerConfig: _testRouter(
            child: BottomNavShell(child: const SizedBox()),
          ),
        ),
      );

      // 点击"更多"
      await tester.tap(find.text('更多'));
      await tester.pumpAndSettle();

      // 验证底部菜单项
      expect(find.text('回顾'), findsOneWidget);
      expect(find.text('目标'), findsOneWidget);
      expect(find.text('灵感'), findsOneWidget);
      expect(find.text('探索'), findsOneWidget);
      expect(find.text('对话'), findsOneWidget);
    });

    testWidgets('底部菜单包含正确的图标', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp.router(
          routerConfig: _testRouter(
            child: BottomNavShell(child: const SizedBox()),
          ),
        ),
      );

      await tester.tap(find.text('更多'));
      await tester.pumpAndSettle();

      // 验证菜单项图标
      expect(find.byIcon(Icons.bar_chart), findsOneWidget);
      expect(find.byIcon(Icons.flag), findsOneWidget);
      expect(find.byIcon(Icons.lightbulb), findsOneWidget);
      expect(find.byIcon(Icons.explore), findsOneWidget);
      expect(find.byIcon(Icons.chat_bubble), findsOneWidget);
    });

    testWidgets('渲染 NavigationBar', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp.router(
          routerConfig: _testRouter(
            child: BottomNavShell(child: const SizedBox()),
          ),
        ),
      );

      expect(find.byType(NavigationBar), findsOneWidget);
    });

    testWidgets('子组件正确渲染', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp.router(
          routerConfig: _testRouter(
            child: BottomNavShell(
              child: const Text('Child Content'),
            ),
          ),
        ),
      );

      expect(find.text('Child Content'), findsOneWidget);
    });
  });
}
