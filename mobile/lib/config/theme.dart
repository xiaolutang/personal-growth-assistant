import 'package:flutter/material.dart';

// ============================================================
// AppColors - 项目级颜色定义
// ============================================================
class AppColors {
  AppColors._();

  // Primary - 靛蓝 #6366F1
  static const primary = Color(0xFF6366F1);
  static const primaryLight = Color(0xFF818CF8);
  static const primaryDark = Color(0xFF4F46E5);

  // Semantic
  static const success = Color(0xFF22C55E);
  static const warning = Color(0xFFF59E0B);
  static const error = Color(0xFFEF4444);

  // Status colors
  static const completed = Color(0xFF22C55E);
  static const doing = Color(0xFFEAB308);
  static const waitStart = Color(0xFF9CA3AF);
}

// ============================================================
// AppSpacing - 间距基准（4px 基准）
// ============================================================
class AppSpacing {
  AppSpacing._();

  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 12.0;
  static const double lg = 16.0;
  static const double xl = 24.0;
  static const double xxl = 32.0;
}

// ============================================================
// AppRadius - 圆角：按钮 8px / 卡片 12px
// ============================================================
class AppRadius {
  AppRadius._();

  static const double button = 8.0;
  static const double card = 12.0;
  static const double full = 999.0;
}

// ============================================================
// AppFontSize - 字号：正文 14px / 标题 16-24px
// ============================================================
class AppFontSize {
  AppFontSize._();

  static const double caption = 12.0;
  static const double body = 14.0;
  static const double title = 16.0;
  static const double headline = 20.0;
  static const double display = 24.0;
}

// ============================================================
// AppTheme - Material 3 亮色 & 暗色主题
// ============================================================
class AppTheme {
  AppTheme._();

  static ThemeData get lightTheme => ThemeData(
        useMaterial3: true,
        colorSchemeSeed: AppColors.primary,
        brightness: Brightness.light,
        cardTheme: CardThemeData(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.card),
          ),
          elevation: 1,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.button),
            ),
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.sm + AppSpacing.xs,
            ),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadius.button),
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.sm + AppSpacing.xs,
          ),
        ),
      );

  static ThemeData get darkTheme => ThemeData(
        useMaterial3: true,
        colorSchemeSeed: AppColors.primary,
        brightness: Brightness.dark,
        cardTheme: CardThemeData(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.card),
          ),
          elevation: 1,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.button),
            ),
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.sm + AppSpacing.xs,
            ),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadius.button),
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.sm + AppSpacing.xs,
          ),
        ),
      );
}
