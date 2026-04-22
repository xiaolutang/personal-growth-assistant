import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../pages/login_page.dart';
import '../pages/placeholder_page.dart';
import '../pages/today_page.dart';
import '../providers/auth_provider.dart';
import '../services/api_client.dart';
import '../widgets/bottom_nav.dart';

final _shellNavigatorKey = GlobalKey<NavigatorState>();

/// Redirect 逻辑：检查认证状态
String? _authRedirect(Ref ref, GoRouterState state) {
  final authState = ref.read(authProvider);

  final isAuthenticated = authState.whenOrNull<AuthState>(
        data: (s) => s,
      ) is AuthAuthenticated;

  final isLoggingIn = state.uri.path == '/login';

  // 未认证且不在登录页 → 重定向到登录页
  if (!isAuthenticated && !isLoggingIn) {
    return '/login';
  }

  // 已认证且在登录页 → 重定向到首页
  if (isAuthenticated && isLoggingIn) {
    return '/';
  }

  return null;
}

final routerProvider = Provider<GoRouter>((ref) {
  // 监听认证状态变化
  ref.listen<AsyncValue<AuthState>>(authProvider, (_, __) {
    // 当认证状态变化时，GoRouter 会通过 refreshListenable 重建
  });

  return GoRouter(
    navigatorKey: rootNavigatorKey,
    initialLocation: '/',
    refreshListenable: _AuthStateListener(ref),
    redirect: (context, state) => _authRedirect(ref, state),
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
            builder: (context, state) => const TodayPage(),
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

/// ValueNotifier 监听 auth 状态变化，触发 GoRouter 刷新
class _AuthStateListener extends ChangeNotifier {
  _AuthStateListener(Ref ref) {
    _subscription = ref.listen<AsyncValue<AuthState>>(
      authProvider,
      (_, __) {
        notifyListeners();
      },
    );
  }

  // ignore: unused_field
  late final ProviderSubscription<AsyncValue<AuthState>> _subscription;
}
