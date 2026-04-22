import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'config/routes.dart';
import 'config/theme.dart';

void main() {
  runApp(const ProviderScope(child: GrowthApp()));
}

class GrowthApp extends ConsumerWidget {
  const GrowthApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: '个人成长助手',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      routerConfig: router,
    );
  }
}
