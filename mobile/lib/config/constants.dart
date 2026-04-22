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

  // Status
  static const String statusTodo = 'todo';
  static const String statusDoing = 'doing';
  static const String statusDone = 'done';
  static const String statusWaitStart = 'wait_start';
}
