import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../providers/auth_provider.dart';
import '../services/notification_service.dart';

// ============================================================
// NotificationState - 通知开关状态
// ============================================================

class NotificationState {
  final bool enabled;
  final bool permissionGranted;

  const NotificationState({
    this.enabled = false,
    this.permissionGranted = false,
  });

  NotificationState copyWith({
    bool? enabled,
    bool? permissionGranted,
  }) {
    return NotificationState(
      enabled: enabled ?? this.enabled,
      permissionGranted: permissionGranted ?? this.permissionGranted,
    );
  }
}

// ============================================================
// SharedPreferences Provider
// ============================================================

final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPreferencesProvider must be overridden');
});

// ============================================================
// NotificationService Provider
// ============================================================

final notificationServiceProvider = Provider<NotificationService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final prefs = ref.watch(sharedPreferencesProvider);
  return NotificationService(
    apiClient: apiClient,
    prefs: prefs,
  );
});

// ============================================================
// Notification Notifier
// ============================================================

class NotificationNotifier extends StateNotifier<NotificationState> {
  final NotificationService _service;
  final SharedPreferences _prefs;

  static const _prefKey = 'notification_enabled';

  NotificationNotifier({
    required NotificationService service,
    required SharedPreferences prefs,
  })  : _service = service,
        _prefs = prefs,
        super(const NotificationState()) {
    _loadState();
  }

  /// 从 SharedPreferences 加载保存的状态
  void _loadState() {
    final enabled = _prefs.getBool(_prefKey) ?? false;
    state = state.copyWith(enabled: enabled);
  }

  /// 开启通知
  /// 返回 true 表示成功开启
  Future<bool> enableNotifications() async {
    // 请求系统权限
    final granted = await _service.requestPermission();
    state = state.copyWith(permissionGranted: granted);

    if (!granted) {
      // 权限被拒绝，不启用
      return false;
    }

    // 保存设置
    await _prefs.setBool(_prefKey, true);
    state = state.copyWith(enabled: true);

    // 立即检查到期任务
    await _service.scheduleDueTaskCheck();

    return true;
  }

  /// 关闭通知
  Future<void> disableNotifications() async {
    await _prefs.setBool(_prefKey, false);
    await _service.cancelAll();
    state = state.copyWith(enabled: false);
  }

  /// App 启动时调用：如果通知已启用，检查到期任务
  Future<void> checkDueTasksOnStartup() async {
    if (state.enabled) {
      await _service.scheduleDueTaskCheck();
    }
  }

  /// 初始化通知服务
  Future<void> initService() async {
    await _service.init();
  }
}

final notificationProvider =
    StateNotifierProvider<NotificationNotifier, NotificationState>((ref) {
  final service = ref.watch(notificationServiceProvider);
  final prefs = ref.watch(sharedPreferencesProvider);
  return NotificationNotifier(
    service: service,
    prefs: prefs,
  );
});
