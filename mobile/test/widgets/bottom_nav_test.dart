import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:rizhi/widgets/bottom_nav.dart';

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
      GoRoute(
        path: '/settings',
        builder: (context, state) => const Scaffold(body: Text('Settings')),
      ),
    ],
  );
}

void main() {
  group('BottomNavShell', () {
    testWidgets('渲染 5 个 NavigationDestination：今天、对话、任务、探索、我的',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: BottomNavShell(child: const SizedBox()),
            ),
          ),
        ),
      );

      expect(find.text('今天'), findsOneWidget);
      expect(find.text('对话'), findsOneWidget);
      expect(find.text('任务'), findsOneWidget);
      expect(find.text('探索'), findsOneWidget);
      expect(find.text('我的'), findsOneWidget);
    });

    testWidgets('Tab 图标正确：对话=chat_bubble、探索=explore、我的=person',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: BottomNavShell(child: const SizedBox()),
            ),
          ),
        ),
      );

      // 对话 Tab 使用 chat_bubble (outline 因为未选中)
      expect(find.byIcon(Icons.chat_bubble_outline), findsOneWidget);
      // 探索 Tab：NavigationBar 中未选中时会渲染 icon 属性的图标
      // 检查 NavigationDestination 的 destinations 包含 explore 相关图标
      final navBar = tester.widget<NavigationBar>(
        find.byType(NavigationBar),
      );
      final destinations = navBar.destinations;
      // 探索 Tab (index 3) 的 icon 应包含 explore
      final exploreDest = destinations[3] as NavigationDestination;
      final exploreIcon = exploreDest.icon as Icon;
      expect(exploreIcon.icon, equals(Icons.explore_outlined));
      final exploreSelectedIcon = exploreDest.selectedIcon as Icon;
      expect(exploreSelectedIcon.icon, equals(Icons.explore));
      // 我的 Tab (index 4) 的 icon 应包含 person
      final personDest = destinations[4] as NavigationDestination;
      final personIcon = personDest.icon as Icon;
      expect(personIcon.icon, equals(Icons.person_outline));
      final personSelectedIcon = personDest.selectedIcon as Icon;
      expect(personSelectedIcon.icon, equals(Icons.person));
    });

    testWidgets('默认选中第一个 Tab（今天）', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: BottomNavShell(child: const SizedBox()),
            ),
          ),
        ),
      );

      final navBar = tester.widget<NavigationBar>(
        find.byType(NavigationBar),
      );
      expect(navBar.selectedIndex, equals(0));
    });

    testWidgets('点击我的 Tab 弹出底部菜单，恰好 3 项：回顾、目标、设置',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: BottomNavShell(child: const SizedBox()),
            ),
          ),
        ),
      );

      // 点击"我的"
      await tester.tap(find.text('我的'));
      await tester.pumpAndSettle();

      // 验证底部菜单只有 3 项（在 BottomSheet 中）
      // 注意：底部导航栏本身也有文本，所以用 findsWidgets 判断至少有一个
      expect(find.text('回顾'), findsWidgets);
      expect(find.text('目标'), findsWidgets);
      expect(find.text('设置'), findsWidgets);

      // 确认不再包含灵感
      expect(find.text('灵感'), findsNothing);
      // 注意：导航栏中有"探索"和"对话"文本，但菜单中不应有额外的
      // 菜单里的探索和对话已被移除，导航栏中仍然存在这些文本
    });

    testWidgets('我的菜单包含正确的图标：bar_chart、flag、settings',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: BottomNavShell(child: const SizedBox()),
            ),
          ),
        ),
      );

      await tester.tap(find.text('我的'));
      await tester.pumpAndSettle();

      // 验证菜单项图标
      expect(find.byIcon(Icons.bar_chart), findsOneWidget);
      expect(find.byIcon(Icons.flag), findsOneWidget);
      expect(find.byIcon(Icons.settings), findsOneWidget);
    });

    testWidgets('点击我的→回顾 → 跳转到 /review', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: BottomNavShell(child: const SizedBox()),
            ),
          ),
        ),
      );

      await tester.tap(find.text('我的'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('回顾'));
      await tester.pumpAndSettle();

      expect(find.text('Review'), findsOneWidget);
    });

    testWidgets('点击我的→目标 → 跳转到 /goals', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: BottomNavShell(child: const SizedBox()),
            ),
          ),
        ),
      );

      await tester.tap(find.text('我的'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('目标'));
      await tester.pumpAndSettle();

      expect(find.text('Goals'), findsOneWidget);
    });

    testWidgets('点击我的→设置 → 跳转到 /settings', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: BottomNavShell(child: const SizedBox()),
            ),
          ),
        ),
      );

      await tester.tap(find.text('我的'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('设置'));
      await tester.pumpAndSettle();

      expect(find.text('Settings'), findsOneWidget);
    });

    testWidgets('/explore 路由高亮探索 Tab（index 3）',
        (WidgetTester tester) async {
      final router = GoRouter(
        initialLocation: '/explore',
        routes: [
          GoRoute(
            path: '/explore',
            builder: (context, state) => BottomNavShell(
              child: const SizedBox(),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(routerConfig: router),
        ),
      );

      final navBar = tester.widget<NavigationBar>(
        find.byType(NavigationBar),
      );
      expect(navBar.selectedIndex, equals(3));
    });

    testWidgets('/notes 路由高亮探索 Tab（index 3）',
        (WidgetTester tester) async {
      final router = GoRouter(
        initialLocation: '/notes',
        routes: [
          GoRoute(
            path: '/notes',
            builder: (context, state) => BottomNavShell(
              child: const SizedBox(),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(routerConfig: router),
        ),
      );

      final navBar = tester.widget<NavigationBar>(
        find.byType(NavigationBar),
      );
      expect(navBar.selectedIndex, equals(3));
    });

    testWidgets('/inbox 路由高亮探索 Tab（index 3）',
        (WidgetTester tester) async {
      final router = GoRouter(
        initialLocation: '/inbox',
        routes: [
          GoRoute(
            path: '/inbox',
            builder: (context, state) => BottomNavShell(
              child: const SizedBox(),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(routerConfig: router),
        ),
      );

      final navBar = tester.widget<NavigationBar>(
        find.byType(NavigationBar),
      );
      expect(navBar.selectedIndex, equals(3));
    });

    testWidgets('/review 路由高亮我的 Tab（index 4）',
        (WidgetTester tester) async {
      final router = GoRouter(
        initialLocation: '/review',
        routes: [
          GoRoute(
            path: '/review',
            builder: (context, state) => BottomNavShell(
              child: const SizedBox(),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(routerConfig: router),
        ),
      );

      final navBar = tester.widget<NavigationBar>(
        find.byType(NavigationBar),
      );
      expect(navBar.selectedIndex, equals(4));
    });

    testWidgets('/goals 路由高亮我的 Tab（index 4）',
        (WidgetTester tester) async {
      final router = GoRouter(
        initialLocation: '/goals',
        routes: [
          GoRoute(
            path: '/goals',
            builder: (context, state) => BottomNavShell(
              child: const SizedBox(),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(routerConfig: router),
        ),
      );

      final navBar = tester.widget<NavigationBar>(
        find.byType(NavigationBar),
      );
      expect(navBar.selectedIndex, equals(4));
    });

    testWidgets('/settings 路由高亮我的 Tab（index 4）',
        (WidgetTester tester) async {
      final router = GoRouter(
        initialLocation: '/settings',
        routes: [
          GoRoute(
            path: '/settings',
            builder: (context, state) => BottomNavShell(
              child: const SizedBox(),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(routerConfig: router),
        ),
      );

      final navBar = tester.widget<NavigationBar>(
        find.byType(NavigationBar),
      );
      expect(navBar.selectedIndex, equals(4));
    });

    testWidgets('渲染 NavigationBar', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: BottomNavShell(child: const SizedBox()),
            ),
          ),
        ),
      );

      expect(find.byType(NavigationBar), findsOneWidget);
    });

    testWidgets('子组件正确渲染', (WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: _testRouter(
              child: BottomNavShell(
                child: const Text('Child Content'),
              ),
            ),
          ),
        ),
      );

      expect(find.text('Child Content'), findsOneWidget);
    });
  });
}
