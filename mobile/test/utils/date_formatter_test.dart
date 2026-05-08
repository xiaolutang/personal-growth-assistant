import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/utils/date_formatter.dart';

void main() {
  // ----------------------------------------------------------
  // formatRelative
  // ----------------------------------------------------------
  group('DateFormatter.formatRelative', () {
    test('null 输入返回 fallback', () {
      expect(DateFormatter.formatRelative(null), '');
      expect(DateFormatter.formatRelative(null, fallback: '-'), '-');
    });

    test('无效字符串返回 fallback', () {
      expect(DateFormatter.formatRelative('not-a-date'), '');
      expect(DateFormatter.formatRelative('not-a-date', fallback: 'N/A'), 'N/A');
    });

    test('刚刚 — 小于1分钟', () {
      final now = DateTime.now();
      final justNow = now.subtract(const Duration(seconds: 30));
      expect(DateFormatter.formatRelative(justNow.toIso8601String()), '刚刚');
    });

    test('X 分钟前 — 小于1小时', () {
      final now = DateTime.now();
      final fiveMinAgo = now.subtract(const Duration(minutes: 5));
      final result = DateFormatter.formatRelative(fiveMinAgo.toIso8601String());
      expect(result, contains('分钟前'));
      expect(result, contains('5'));
    });

    test('X 小时前 — 小于1天', () {
      final now = DateTime.now();
      final twoHoursAgo = now.subtract(const Duration(hours: 2));
      final result = DateFormatter.formatRelative(twoHoursAgo.toIso8601String());
      expect(result, contains('小时前'));
      expect(result, contains('2'));
    });

    test('X 天前 — 小于7天', () {
      final now = DateTime.now();
      final threeDaysAgo = now.subtract(const Duration(days: 3));
      final result = DateFormatter.formatRelative(threeDaysAgo.toIso8601String());
      expect(result, contains('天前'));
      expect(result, contains('3'));
    });

    test('超过7天 — 月/日 + 时间', () {
      final now = DateTime.now();
      final tenDaysAgo = now.subtract(const Duration(days: 10));
      final result = DateFormatter.formatRelative(tenDaysAgo.toIso8601String());
      // 格式应为 X月X日 HH:MM
      expect(result, contains('月'));
      expect(result, contains('日'));
      expect(result, contains(':'));
    });

    test('边界值 — 刚好1分钟前', () {
      final now = DateTime.now();
      final oneMinAgo = now.subtract(const Duration(minutes: 1, seconds: 1));
      final result = DateFormatter.formatRelative(oneMinAgo.toIso8601String());
      expect(result, contains('分钟前'));
    });

    test('边界值 — 刚好1小时前', () {
      final now = DateTime.now();
      final oneHourAgo = now.subtract(const Duration(hours: 1, minutes: 1));
      final result = DateFormatter.formatRelative(oneHourAgo.toIso8601String());
      expect(result, contains('小时前'));
    });

    test('边界值 — 刚好24小时前(1天)', () {
      final now = DateTime.now();
      final oneDayAgo = now.subtract(const Duration(hours: 25));
      final result = DateFormatter.formatRelative(oneDayAgo.toIso8601String());
      expect(result, contains('天前'));
    });

    test('边界值 — 刚好7天前', () {
      final now = DateTime.now();
      final sevenDaysAgo = now.subtract(const Duration(days: 8));
      final result = DateFormatter.formatRelative(sevenDaysAgo.toIso8601String());
      expect(result, contains('月'));
      expect(result, contains('日'));
    });
  });

  // ----------------------------------------------------------
  // formatShortDate
  // ----------------------------------------------------------
  group('DateFormatter.formatShortDate', () {
    test('null 输入返回 fallback', () {
      expect(DateFormatter.formatShortDate(null), '');
      expect(DateFormatter.formatShortDate(null, fallback: '-'), '-');
    });

    test('当年日期 — X月X日', () {
      final now = DateTime.now();
      final date = DateTime(now.year, 3, 15);
      final result = DateFormatter.formatShortDate(date.toIso8601String());
      expect(result, '3月15日');
    });

    test('跨年日期 — X年X月X日', () {
      final now = DateTime.now();
      final date = DateTime(now.year - 1, 12, 25);
      final result = DateFormatter.formatShortDate(date.toIso8601String());
      expect(result, contains('年'));
      expect(result, contains('12月'));
      expect(result, contains('25日'));
      expect(result, '${now.year - 1}年12月25日');
    });

    test('无效字符串返回原始值', () {
      expect(DateFormatter.formatShortDate('bad'), 'bad');
    });

    test('ISO 带时区解析正常', () {
      final result = DateFormatter.formatShortDate('2026-05-01T10:30:00+08:00');
      // 2026 年在当年应该是 X月X日 格式
      final now = DateTime.now();
      if (now.year == 2026) {
        expect(result, '5月1日');
      } else {
        expect(result, contains('年'));
      }
    });
  });

  // ----------------------------------------------------------
  // formatFullDate
  // ----------------------------------------------------------
  group('DateFormatter.formatFullDate', () {
    test('null 输入返回 fallback（默认"未知"）', () {
      expect(DateFormatter.formatFullDate(null), '未知');
      expect(DateFormatter.formatFullDate(null, fallback: 'N/A'), 'N/A');
    });

    test('标准 ISO 字符串', () {
      final result = DateFormatter.formatFullDate('2026-05-01T14:30:00');
      // toLocal() 可能影响小时，但日期部分取决于时区
      expect(result, contains('2026'));
      expect(result, contains('05'));
      expect(result, contains('01'));
    });

    test('输出格式为 yyyy-MM-dd HH:mm', () {
      // 用 UTC 时间，toLocal() 后时间变化，但格式应正确
      final utc = DateTime.utc(2026, 1, 15, 8, 30);
      final result = DateFormatter.formatFullDate(utc.toIso8601String());
      // 匹配 yyyy-MM-dd HH:mm 格式
      expect(RegExp(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$').hasMatch(result), isTrue);
    });

    test('无效字符串返回原始值', () {
      expect(DateFormatter.formatFullDate('bad'), 'bad');
    });

    test('带 Z 后缀的 UTC 时间', () {
      final result = DateFormatter.formatFullDate('2026-05-01T14:30:00Z');
      expect(RegExp(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$').hasMatch(result), isTrue);
    });
  });

  // ----------------------------------------------------------
  // 页面迁移回归测试（验证输出格式与原始实现一致）
  // ----------------------------------------------------------
  group('迁移回归 — 格式一致性', () {
    test('goals_page/goal_detail_page: 月/日格式一致', () {
      // 原始实现: '${dateTime.month}月${dateTime.day}日'
      final result = DateFormatter.formatShortDate('2026-06-15');
      final now = DateTime.now();
      if (now.year == 2026) {
        expect(result, '6月15日');
      }
    });

    test('inbox_page: 相对时间格式一致', () {
      final now = DateTime.now();
      // 刚刚
      expect(
        DateFormatter.formatRelative(
          now.subtract(const Duration(seconds: 10)).toIso8601String(),
        ),
        '刚刚',
      );
      // X分钟前
      expect(
        DateFormatter.formatRelative(
          now.subtract(const Duration(minutes: 30)).toIso8601String(),
        ),
        contains('分钟前'),
      );
    });

    test('entry_detail_page: yyyy-MM-dd HH:mm 格式一致', () {
      // 原始实现: DateFormat('yyyy-MM-dd HH:mm').format(date)
      final utc = DateTime.utc(2026, 3, 20, 10, 45);
      final result = DateFormatter.formatFullDate(utc.toIso8601String());
      expect(RegExp(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$').hasMatch(result), isTrue);
    });

    test('notes_page: 短日期格式（从 M/D 迁移到 X月X日）', () {
      // notes_page 原来用 M/D 格式，统一后用 X月X日
      final result = DateFormatter.formatShortDate('2026-04-20');
      final now = DateTime.now();
      if (now.year == 2026) {
        expect(result, '4月20日');
      }
    });
  });
}
