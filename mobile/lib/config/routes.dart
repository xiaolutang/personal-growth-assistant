import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../pages/placeholder_page.dart';
import '../pages/login_page.dart';
import '../widgets/bottom_nav.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginPage(),
      ),
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (context, state, child) {
          return BottomNavShell(child: child);
        },
        routes: [
          GoRoute(
            path: '/',
            name: 'today',
            builder: (context, state) => const PlaceholderPage(title: '今天'),
          ),
          GoRoute(
            path: '/chat',
            name: 'chat',
            builder: (context, state) => const PlaceholderPage(title: '日知'),
          ),
          GoRoute(
            path: '/tasks',
            name: 'tasks',
            builder: (context, state) => const PlaceholderPage(title: '任务'),
          ),
        ],
      ),
      GoRoute(
        path: '/entries/:id',
        builder: (context, state) {
          final id = state.pathParameters['id']!;
          return PlaceholderPage(title: '条目详情 $id');
        },
      ),
    ],
  );
});
