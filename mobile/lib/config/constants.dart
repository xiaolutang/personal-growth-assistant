// ============================================================
// AppConstants - 全局常量
// ============================================================
class AppConstants {
  AppConstants._();

  static const String appName = '个人成长助手';
  static const String apiBaseUrl = 'http://localhost:8001';

  // Category types
  static const String categoryTask = 'task';
  static const String categoryNote = 'note';
  static const String categoryInbox = 'inbox';
  static const String categoryProject = 'project';

  // Status - 与后端 entry_mapper.py 保持一致
  static const String statusWaitStart = 'waitStart';
  static const String statusDoing = 'doing';
  static const String statusComplete = 'complete';
  static const String statusPaused = 'paused';
  static const String statusCancelled = 'cancelled';

}
