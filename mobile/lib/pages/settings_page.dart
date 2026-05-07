import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/theme.dart';
import '../providers/auth_provider.dart';
import '../providers/notification_provider.dart';

class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  bool _isLoggingOut = false;

  Future<void> _handleLogout() async {
    setState(() => _isLoggingOut = true);

    try {
      await ref.read(authProvider.notifier).logout();

      if (!mounted) return;
      context.go('/login');
    } finally {
      if (mounted) {
        setState(() => _isLoggingOut = false);
      }
    }
  }

  Future<void> _handleNotificationToggle(bool value) async {
    if (value) {
      // 开启通知 → 请求权限
      final success =
          await ref.read(notificationProvider.notifier).enableNotifications();

      if (!mounted) return;

      if (!success) {
        // 权限被拒绝，显示提示
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('通知权限被拒绝，请在系统设置中开启通知权限'),
            duration: Duration(seconds: 3),
          ),
        );
      }
    } else {
      // 关闭通知
      await ref.read(notificationProvider.notifier).disableNotifications();
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final notificationState = ref.watch(notificationProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('设置'),
      ),
      body: ListView(
        children: [
          // 通知设置
          _buildSectionHeader(theme, '通知'),
          SwitchListTile(
            secondary: const Icon(Icons.notifications_outlined),
            title: const Text('到期任务提醒'),
            subtitle: Text(
              notificationState.enabled ? '已开启' : '已关闭',
              style: TextStyle(
                color: notificationState.enabled
                    ? AppColors.success
                    : theme.colorScheme.onSurfaceVariant,
                fontSize: AppFontSize.caption,
              ),
            ),
            value: notificationState.enabled,
            onChanged: _handleNotificationToggle,
          ),

          const Divider(),

          // 账户设置
          _buildSectionHeader(theme, '账户'),
          ListTile(
            leading: const Icon(
              Icons.logout,
              color: AppColors.error,
            ),
            title: const Text(
              '退出登录',
              style: TextStyle(color: AppColors.error),
            ),
            onTap: _isLoggingOut ? null : _handleLogout,
            trailing: _isLoggingOut
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : null,
          ),

          const Divider(),

          // 关于
          _buildSectionHeader(theme, '关于'),
          const ListTile(
            leading: Icon(Icons.info_outline),
            title: Text('版本'),
            subtitle: Text('1.0.0'),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(ThemeData theme, String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.xs,
      ),
      child: Text(
        title,
        style: theme.textTheme.titleSmall?.copyWith(
          color: theme.colorScheme.primary,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
