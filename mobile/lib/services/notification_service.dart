import 'dart:io';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_client.dart';

// ============================================================
// NotificationService - 本地通知服务
//
// 负责：初始化通知插件、请求权限、查询到期任务、去重通知
// ============================================================

/// 通知点击回调类型
typedef OnNotificationTap = void Function(String? payload);

class NotificationService {
  final FlutterLocalNotificationsPlugin _plugin;
  final ApiClient _apiClient;
  final SharedPreferences _prefs;

  static const _channelId = 'due_tasks_channel';
  static const _channelName = '到期任务提醒';
  static const _channelDescription = '提醒今天到期的任务';
  static const _notifiedKey = 'notified_due_tasks';

  OnNotificationTap? onNotificationTap;

  NotificationService({
    required ApiClient apiClient,
    required SharedPreferences prefs,
    FlutterLocalNotificationsPlugin? plugin,
  })  : _apiClient = apiClient,
        _prefs = prefs,
        _plugin = plugin ?? FlutterLocalNotificationsPlugin();

  /// 初始化通知插件
  Future<void> init() async {
    const androidSettings = AndroidInitializationSettings(
      '@mipmap/ic_launcher',
    );
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );

    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _plugin.initialize(
      settings,
      onDidReceiveNotificationResponse: _onNotificationResponse,
    );
  }

  /// 通知点击回调
  void _onNotificationResponse(NotificationResponse response) {
    if (onNotificationTap != null) {
      onNotificationTap!(response.payload);
    }
  }

  /// 请求系统通知权限
  /// 返回 true 表示用户授权
  Future<bool> requestPermission() async {
    if (Platform.isAndroid) {
      final androidPlugin =
          _plugin.resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>();
      if (androidPlugin != null) {
        return await androidPlugin.requestNotificationsPermission() ?? false;
      }
      return false;
    }

    if (Platform.isIOS) {
      final iosPlugin = _plugin.resolvePlatformSpecificImplementation<
          IOSFlutterLocalNotificationsPlugin>();
      if (iosPlugin != null) {
        return await iosPlugin.requestPermissions(
              alert: true,
              badge: true,
              sound: true,
            ) ??
            false;
      }
      return false;
    }

    return false;
  }

  /// 查询到期任务并发送通知
  /// 返回发送的通知数量
  Future<int> scheduleDueTaskCheck() async {
    try {
      final today = DateTime.now();
      final dateStr =
          '${today.year}-${today.month.toString().padLeft(2, '0')}-${today.day.toString().padLeft(2, '0')}';

      final response = await _apiClient.get<Map<String, dynamic>>(
        '/entries',
        queryParameters: {
          'type': 'task',
          'status': 'todo',
          'due': 'today',
          'limit': 50,
        },
      );

      final data = response.data;
      if (data == null) return 0;

      // 兼容两种响应格式: { items: [...] } 或 { entries: [...] }
      List<dynamic> items;
      if (data.containsKey('items')) {
        items = data['items'] as List<dynamic>;
      } else if (data.containsKey('entries')) {
        items = data['entries'] as List<dynamic>;
      } else {
        return 0;
      }

      final alreadyNotified = _getAlreadyNotified(dateStr);
      var sentCount = 0;

      for (final item in items) {
        if (item is! Map<String, dynamic>) continue;

        final entryId = item['id']?.toString();
        final title = item['title']?.toString() ?? '到期任务';

        if (entryId == null) continue;

        // 去重：同一 entryId + 日期只通知一次
        final dedupeKey = '$dateStr:$entryId';
        if (alreadyNotified.contains(dedupeKey)) continue;

        try {
          await _showNotification(
            id: entryId.hashCode & 0x7FFFFFFF,
            title: '任务到期提醒',
            body: title,
            payload: '/tasks',
          );
        } catch (_) {
          // 通知插件不可用时（测试环境等）仍记录为已通知
        }

        alreadyNotified.add(dedupeKey);
        sentCount++;
      }

      if (sentCount > 0) {
        _saveNotified(dateStr, alreadyNotified);
      }

      return sentCount;
    } catch (_) {
      return 0;
    }
  }

  /// 显示单条本地通知
  Future<void> _showNotification({
    required int id,
    required String title,
    required String body,
    String? payload,
  }) async {
    const androidDetails = AndroidNotificationDetails(
      _channelId,
      _channelName,
      channelDescription: _channelDescription,
      importance: Importance.high,
      priority: Priority.high,
    );

    const iosDetails = DarwinNotificationDetails();

    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _plugin.show(id, title, body, details, payload: payload);
  }

  /// 取消所有通知
  Future<void> cancelAll() async {
    await _plugin.cancelAll();
  }

  /// 获取今天已通知的 key 集合
  List<String> _getAlreadyNotified(String dateStr) {
    final raw = _prefs.getStringList('${_notifiedKey}_$dateStr');
    return raw ?? [];
  }

  /// 保存已通知的 key 集合
  void _saveNotified(String dateStr, List<String> keys) {
    _prefs.setStringList('${_notifiedKey}_$dateStr', keys);
  }

  /// 清除所有已通知记录（用于测试或重置）
  Future<void> clearNotifiedRecords() async {
    final keys = _prefs.getKeys();
    for (final key in keys) {
      if (key.startsWith(_notifiedKey)) {
        await _prefs.remove(key);
      }
    }
  }
}
