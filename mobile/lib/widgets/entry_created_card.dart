import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/entry.dart';

// ============================================================
// EntryCreatedCard - 条目创建确认卡片 (F105)
//
// 显示在对话中，包含：
// - 条目标题
// - 类型标签（inbox/note/task/project）
// - 点击跳转到条目详情页 /entries/:id
// ============================================================
class EntryCreatedCard extends StatelessWidget {
  final Entry entry;

  const EntryCreatedCard({
    super.key,
    required this.entry,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        margin: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.xs,
        ),
        child: Material(
          color: isDark
              ? AppColors.primary.withValues(alpha: 0.15)
              : AppColors.primary.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(AppRadius.card),
          child: InkWell(
            onTap: () => _navigateToDetail(context),
            borderRadius: BorderRadius.circular(AppRadius.card),
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  // 顶部: 类型标签
                  Row(
                    children: [
                      Icon(
                        _categoryIcon,
                        size: 16,
                        color: AppColors.primary,
                      ),
                      const SizedBox(width: AppSpacing.xs),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.sm,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(AppSpacing.xs),
                        ),
                        child: Text(
                          _categoryLabel,
                          style: const TextStyle(
                            fontSize: AppFontSize.caption,
                            color: AppColors.primary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      const Spacer(),
                      Icon(
                        Icons.arrow_forward_ios,
                        size: 12,
                        color: theme.colorScheme.onSurfaceVariant
                            .withValues(alpha: 0.5),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  // 标题
                  Text(
                    entry.title,
                    style: TextStyle(
                      fontSize: AppFontSize.body,
                      fontWeight: FontWeight.w500,
                      color: isDark ? Colors.white : Colors.black87,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  void _navigateToDetail(BuildContext context) {
    context.go('/entries/${entry.id}');
  }

  IconData get _categoryIcon {
    switch (entry.category) {
      case AppConstants.categoryInbox:
        return Icons.lightbulb_outline;
      case AppConstants.categoryNote:
        return Icons.article_outlined;
      case AppConstants.categoryTask:
        return Icons.check_circle_outline;
      case AppConstants.categoryProject:
        return Icons.folder_outlined;
      default:
        return Icons.article_outlined;
    }
  }

  String get _categoryLabel {
    switch (entry.category) {
      case AppConstants.categoryInbox:
        return '灵感';
      case AppConstants.categoryNote:
        return '笔记';
      case AppConstants.categoryTask:
        return '任务';
      case AppConstants.categoryProject:
        return '项目';
      default:
        return entry.category;
    }
  }
}
