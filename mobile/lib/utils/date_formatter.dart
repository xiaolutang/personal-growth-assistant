/// 统一日期格式化工具类
///
/// 提供全局一致的日期展示格式，替代各页面中重复且不一致的 _formatDate 实现。
///
/// 格式说明：
/// - [formatRelative]  — 相对时间（刚刚 / X分钟前 / X小时前 / X天前），超过阈值后回退到月/日+时间
/// - [formatShortDate] — 月/日中文格式（X月X日），适合目标卡片、里程碑等场景
/// - [formatFullDate]  — 年-月-日 时:分（yyyy-MM-dd HH:mm），适合详情页元信息
class DateFormatter {
  DateFormatter._();

  // ----------------------------------------------------------
  // 相对时间格式（灵感列表、消息时间等）
  // ----------------------------------------------------------

  /// 相对时间格式化，用于时间戳展示。
  ///
  /// - <1 分钟 → 刚刚
  /// - <1 小时 → X 分钟前
  /// - <1 天   → X 小时前
  /// - <7 天   → X 天前
  /// - >=7 天  → M月D日 HH:mm
  ///
  /// [isoString] ISO 8601 日期字符串。
  /// [fallback] 解析失败时的返回值，默认空字符串。
  static String formatRelative(String? isoString, {String fallback = ''}) {
    if (isoString == null) return fallback;
    try {
      final dt = DateTime.parse(isoString).toLocal();
      final now = DateTime.now();
      final diff = now.difference(dt);

      if (diff.inMinutes < 1) return '刚刚';
      if (diff.inHours < 1) return '${diff.inMinutes} 分钟前';
      if (diff.inDays < 1) return '${diff.inHours} 小时前';
      if (diff.inDays < 7) return '${diff.inDays} 天前';

      return '${dt.month}月${dt.day}日 '
          '${dt.hour.toString().padLeft(2, '0')}:'
          '${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return fallback;
    }
  }

  // ----------------------------------------------------------
  // 月/日中文格式（目标卡片、里程碑）
  // ----------------------------------------------------------

  /// 短日期格式：X月X日。
  ///
  /// 适合目标截止日期、里程碑到期日等不需要显示年份的场景。
  /// 如果年份与当前不同，则自动带上年份：X年X月X日。
  static String formatShortDate(String? isoString, {String fallback = ''}) {
    if (isoString == null) return fallback;
    try {
      final dateTime = DateTime.parse(isoString).toLocal();
      final now = DateTime.now();
      if (dateTime.year != now.year) {
        return '${dateTime.year}年${dateTime.month}月${dateTime.day}日';
      }
      return '${dateTime.month}月${dateTime.day}日';
    } catch (_) {
      return isoString;
    }
  }

  // ----------------------------------------------------------
  // 完整日期时间格式（详情页元信息）
  // ----------------------------------------------------------

  /// 完整日期时间格式：yyyy-MM-dd HH:mm。
  ///
  /// 适合条目详情页的创建时间、更新时间展示。
  static String formatFullDate(String? isoString, {String fallback = '未知'}) {
    if (isoString == null) return fallback;
    try {
      final date = DateTime.parse(isoString).toLocal();
      final y = date.year.toString();
      final mo = date.month.toString().padLeft(2, '0');
      final d = date.day.toString().padLeft(2, '0');
      final h = date.hour.toString().padLeft(2, '0');
      final mi = date.minute.toString().padLeft(2, '0');
      return '$y-$mo-$d $h:$mi';
    } catch (_) {
      return isoString;
    }
  }
}
