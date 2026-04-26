import 'package:flutter/material.dart';

import 'theme.dart';
import '../models/entry.dart';

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

  // 搜索历史上限
  static const int searchHistoryLimit = 10;
}

// ============================================================
// CategoryMeta - 分类图标/颜色/标签统一映射
// ============================================================
class CategoryMeta {
  final String value;
  final String label;
  final IconData icon;
  final Color color;

  const CategoryMeta({
    required this.value,
    required this.label,
    required this.icon,
    required this.color,
  });

  static const List<CategoryMeta> all = [
    CategoryMeta(
      value: AppConstants.categoryTask,
      label: '任务',
      icon: Icons.check_circle_outline,
      color: AppColors.primary,
    ),
    CategoryMeta(
      value: AppConstants.categoryNote,
      label: '笔记',
      icon: Icons.note_outlined,
      color: AppColors.completed,
    ),
    CategoryMeta(
      value: AppConstants.categoryInbox,
      label: '灵感',
      icon: Icons.lightbulb_outline,
      color: AppColors.warning,
    ),
    CategoryMeta(
      value: AppConstants.categoryProject,
      label: '项目',
      icon: Icons.folder_outlined,
      color: AppColors.doing,
    ),
  ];

  static CategoryMeta? find(String category) {
    for (final m in all) {
      if (m.value == category) return m;
    }
    return null;
  }

  static IconData iconOf(String category) =>
      find(category)?.icon ?? Icons.article_outlined;

  static Color colorOf(String category) =>
      find(category)?.color ?? AppColors.waitStart;

  static String labelOf(String category) =>
      find(category)?.label ?? '条目';
}

// ============================================================
// parseEntries - API 响应解析共享函数
// ============================================================
List<Entry> parseEntries(Map<String, dynamic>? response) {
  if (response == null) return const [];
  final entriesJson = response['entries'] as List<dynamic>?;
  if (entriesJson == null) return const [];
  return entriesJson
      .map((e) => Entry.fromJson(e as Map<String, dynamic>))
      .toList();
}
