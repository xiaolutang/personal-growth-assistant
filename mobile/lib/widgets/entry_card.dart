import 'package:flutter/material.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/entry.dart';
import 'entry_shared.dart';

// ============================================================
// EntryCard - 条目卡片组件
// ============================================================
class EntryCard extends StatelessWidget {
  final Entry entry;
  final VoidCallback? onTap;

  const EntryCard({
    super.key,
    required this.entry,
    this.onTap,
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
              // 状态图标 / 类别图标
              _buildLeadingIcon(context),
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
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (entry.tags.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.xs),
                      EntrySharedWidgets.buildTagRow(entry.tags),
                    ],
                  ],
                ),
              ),
              // 类别标签
              const SizedBox(width: AppSpacing.sm),
              _buildCategoryChip(theme),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLeadingIcon(BuildContext context) {
    // 任务类别根据状态显示不同图标
    if (entry.category == AppConstants.categoryTask) {
      return EntrySharedWidgets.buildStatusIcon(context, entry.status);
    }

    // 其他类别图标
    final icon = CategoryMeta.iconOf(entry.category);
    final color = CategoryMeta.colorOf(entry.category);
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

  Widget _buildCategoryChip(ThemeData theme) {
    final label = CategoryMeta.labelOf(entry.category);
    final color = CategoryMeta.colorOf(entry.category);

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
