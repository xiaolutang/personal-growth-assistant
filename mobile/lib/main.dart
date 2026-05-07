import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'config/routes.dart';
import 'config/theme.dart';
import 'providers/notification_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final sharedPreferences = await SharedPreferences.getInstance();

  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(sharedPreferences),
      ],
      child: const GrowthApp(),
    ),
  );
}

class GrowthApp extends ConsumerStatefulWidget {
  const GrowthApp({super.key});

  @override
  ConsumerState<GrowthApp> createState() => _GrowthAppState();
}

class _GrowthAppState extends ConsumerState<GrowthApp> {
  @override
  void initState() {
    super.initState();
    // 初始化通知服务并检查到期任务
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initNotifications();
    });
  }

  Future<void> _initNotifications() async {
    try {
      await ref.read(notificationProvider.notifier).initService();
      await ref.read(notificationProvider.notifier).checkDueTasksOnStartup();
    } catch (_) {
      // 通知初始化失败不影响 App 启动
    }
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: '个人成长助手',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      routerConfig: router,
    );
  }
}
