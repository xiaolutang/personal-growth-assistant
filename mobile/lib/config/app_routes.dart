/// 路由路径常量
///
/// routes.dart 和 bottom_nav.dart 共同依赖此类，避免循环依赖。
class AppRoutes {
  AppRoutes._();

  // --- Tab 主路由 ---
  static const String today = '/';
  static const String chat = '/chat';
  static const String tasks = '/tasks';
  static const String explore = '/explore';
  static const String notes = '/notes';
  static const String inbox = '/inbox';

  // --- 我的菜单路由 ---
  static const String review = '/review';
  static const String goals = '/goals';
  static const String settings = '/settings';

  // --- 认证路由 ---
  static const String login = '/login';
  static const String register = '/register';

  // --- 详情路由 ---
  static const String entryDetail = '/entries/:id';

  // --- 路由前缀（用于 startsWith 判断） ---
  static const String _entryDetailPrefix = '/entries/';
  static const String _goalDetailPrefix = '/goals/';

  /// 是否为条目详情路由
  static bool isEntryDetail(String location) =>
      location.startsWith(_entryDetailPrefix);

  /// 是否为目标详情路由（/goals/:id，非 /goals 列表）
  static bool isGoalDetail(String location) =>
      _goalDetailPattern.hasMatch(location);

  static final RegExp _goalDetailPattern = RegExp(r'^/goals/[^/]+$');
}
