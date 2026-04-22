import 'package:flutter/material.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/entry.dart';

// ============================================================
// TaskCard - 任务卡片组件
//
// 与 EntryCard 不同：
// - 点击状态图标切换状态（todo→doing→done→todo 循环）
// - 点击卡片其他区域跳转详情
// - 显示优先级标签
// ============================================================
class TaskCard extends StatelessWidget {
  final Entry entry;
  final VoidCallback? onTap;
  final ValueChanged<String>? onStatusChanged;

  const TaskCard({
    super.key,
    required this.entry,
    this.onTap,
    this.onStatusChanged,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.xs,
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            children: [
              // 状态图标（可点击切换）
              GestureDetector(
                onTap: () => _cycleStatus(),
                behavior: HitTestBehavior.opaque,
                child: _buildStatusIcon(context),
              ),
              const SizedBox(width: AppSpacing.md),
              // 内容区
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.title,
                      style: theme.textTheme.bodyLarge?.copyWith(
                        fontWeight: FontWeight.w500,
                        decoration: entry.status == AppConstants.statusComplete
                            ? TextDecoration.lineThrough
                            : null,
                        color: entry.status == AppConstants.statusComplete
                            ? theme.colorScheme.onSurfaceVariant
                            : theme.colorScheme.onSurface,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (entry.tags.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.xs),
                      _buildTagRow(theme),
                    ],
                  ],
                ),
              ),
              // 优先级标签
              if (entry.priority != null && entry.priority!.isNotEmpty) ...[
                const SizedBox(width: AppSpacing.sm),
                _buildPriorityChip(theme),
              ],
            ],
          ),
        ),
      ),
    );
  }

  /// 状态循环切换：waitStart → doing → complete → waitStart
  void _cycleStatus() {
    final currentStatus = entry.status ?? AppConstants.statusWaitStart;
    String nextStatus;
    switch (currentStatus) {
      case AppConstants.statusWaitStart:
        nextStatus = AppConstants.statusDoing;
      case AppConstants.statusDoing:
        nextStatus = AppConstants.statusComplete;
      case AppConstants.statusComplete:
        nextStatus = AppConstants.statusWaitStart;
      default:
        nextStatus = AppConstants.statusDoing;
    }
    onStatusChanged?.call(nextStatus);
  }

  Widget _buildStatusIcon(BuildContext context) {
    final status = entry.status;
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

  Widget _buildTagRow(ThemeData theme) {
    return Wrap(
      spacing: AppSpacing.xs,
      children: entry.tags.take(3).map((tag) {
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

  Widget _buildPriorityChip(ThemeData theme) {
    final priority = entry.priority!;
    Color color;
    String label;

    switch (priority) {
      case 'high':
        color = AppColors.error;
        label = '高';
      case 'medium':
        color = AppColors.warning;
        label = '中';
      case 'low':
        color = AppColors.waitStart;
        label = '低';
      default:
        color = AppColors.waitStart;
        label = priority;
    }

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppRadius.button),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: AppFontSize.caption,
          color: color,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}
