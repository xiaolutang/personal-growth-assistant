import 'package:flutter/material.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/entry.dart';

// ============================================================
// EntrySharedWidgets - EntryCard/TaskCard 共享子组件
//
// 从 EntryCard 和 TaskCard 中提取的重复 _buildStatusIcon
// 和 _buildTagRow 方法，统一为静态工具函数
// ============================================================
class EntrySharedWidgets {
  EntrySharedWidgets._();

  /// 根据任务状态构建状态图标
  /// 与 EntryCard._buildTaskStatusIcon / TaskCard._buildStatusIcon 完全一致
  static Widget buildStatusIcon(BuildContext context, String? status) {
    IconData icon;
    Color color;

    switch (status) {
      case AppConstants.statusComplete:
        icon = Icons.check_circle;
        color = AppColors.completed;
      case AppConstants.statusDoing:
        icon = Icons.pending;
        color = AppColors.doing;
      case AppConstants.statusWaitStart:
        icon = Icons.schedule;
        color = AppColors.waitStart;
      default:
        icon = Icons.radio_button_unchecked;
        color = Theme.of(context).colorScheme.onSurfaceVariant;
    }

    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppRadius.button),
      ),
      child: Icon(icon, size: 20, color: color),
    );
  }

  /// 标签行（最多 3 个标签）
  /// 与 EntryCard._buildTagRow / TaskCard._buildTagRow 完全一致
  static Widget buildTagRow(List<String> tags) {
    return Wrap(
      spacing: AppSpacing.xs,
      children: tags.take(3).map((tag) {
        return Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.sm,
            vertical: 2,
          ),
          decoration: BoxDecoration(
            color: AppColors.primary.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(AppRadius.button),
          ),
          child: Text(
            tag,
            style: const TextStyle(
              fontSize: AppFontSize.caption,
              color: AppColors.primary,
            ),
          ),
        );
      }).toList(),
    );
  }
}
