import 'package:flutter/material.dart';

import '../config/constants.dart';
import '../config/theme.dart';

// ============================================================
// BatchActionBar - 批量操作底部浮动操作栏
//
// 选中数量标签 + 批量删除按钮 + 批量转分类按钮 + 取消按钮
// 选中 0 条时操作按钮禁用
// ============================================================

class BatchActionBar extends StatelessWidget {
  /// 当前选中的条目数量
  final int selectedCount;

  /// 批量删除回调
  final VoidCallback onDelete;

  /// 批量转分类回调
  final VoidCallback onMoveCategory;

  /// 取消/退出多选模式回调
  final VoidCallback onCancel;

  /// 全选回调
  final VoidCallback onSelectAll;

  /// 是否已全选
  final bool isAllSelected;

  const BatchActionBar({
    super.key,
    required this.selectedCount,
    required this.onDelete,
    required this.onMoveCategory,
    required this.onCancel,
    required this.onSelectAll,
    required this.isAllSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasSelection = selectedCount > 0;

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 8,
            offset: const Offset(0, -2),
          ),
        ],
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(AppRadius.card),
        ),
      ),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.md,
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // 第一行：选中数量 + 全选/取消
            Row(
              children: [
                // 选中数量标签
                Text(
                  '已选中 $selectedCount 项',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                // 全选按钮
                TextButton.icon(
                  onPressed: onSelectAll,
                  icon: Icon(
                    isAllSelected
                        ? Icons.deselect
                        : Icons.select_all,
                    size: 18,
                  ),
                  label: Text(isAllSelected ? '取消全选' : '全选'),
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                    ),
                  ),
                ),
                // 取消按钮
                TextButton(
                  onPressed: onCancel,
                  child: const Text('取消'),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            // 第二行：操作按钮
            Row(
              children: [
                // 批量删除按钮（红色调）
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: hasSelection ? onDelete : null,
                    icon: Icon(
                      Icons.delete_outline,
                      size: 18,
                      color: hasSelection
                          ? theme.colorScheme.error
                          : null,
                    ),
                    label: Text(
                      '删除',
                      style: TextStyle(
                        color: hasSelection
                            ? theme.colorScheme.error
                            : null,
                      ),
                    ),
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(
                        color: hasSelection
                            ? theme.colorScheme.error
                            : theme.colorScheme.outlineVariant,
                      ),
                      padding: const EdgeInsets.symmetric(
                        vertical: AppSpacing.sm,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                // 批量转分类按钮
                Expanded(
                  child: FilledButton.icon(
                    onPressed: hasSelection ? onMoveCategory : null,
                    icon: const Icon(Icons.drive_file_move_outline, size: 18),
                    label: const Text('转分类'),
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        vertical: AppSpacing.sm,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ============================================================
// BatchDeleteConfirmDialog - 批量删除确认对话框
// ============================================================

/// 显示批量删除确认对话框
/// 返回 true 表示确认删除
Future<bool> showBatchDeleteConfirmDialog(
  BuildContext context, {
  required int count,
}) {
  return showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('确认删除'),
      content: Text('确定要删除选中的 $count 项条目吗？此操作不可撤销。'),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('取消'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(true),
          style: FilledButton.styleFrom(
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
          child: const Text('删除'),
        ),
      ],
    ),
  ).then((value) => value ?? false);
}

// ============================================================
// BatchFailureDialog - 批量操作部分失败提示对话框
// ============================================================

/// 批量操作部分失败信息
class BatchFailureInfo {
  final int failureCount;
  final List<String> failureNames;
  final VoidCallback onRetry;

  const BatchFailureInfo({
    required this.failureCount,
    required this.failureNames,
    required this.onRetry,
  });
}

/// 显示批量操作部分失败对话框
Future<void> showBatchFailureDialog(
  BuildContext context, {
  required BatchFailureInfo info,
  required String operationName,
}) {
  return showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text('$operationName部分失败'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('${info.failureCount} 项$operationName失败：'),
          const SizedBox(height: AppSpacing.sm),
          // 显示失败条目名称（最多 5 条）
          ...info.failureNames.take(5).map(
                (name) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    children: [
                      Icon(
                        Icons.error_outline,
                        size: 14,
                        color: Theme.of(context).colorScheme.error,
                      ),
                      const SizedBox(width: AppSpacing.xs),
                      Expanded(
                        child: Text(
                          name,
                          style: Theme.of(context).textTheme.bodySmall,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          if (info.failureNames.length > 5)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                '...及其他 ${info.failureNames.length - 5} 项',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
            ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('关闭'),
        ),
        FilledButton(
          onPressed: () {
            Navigator.of(context).pop();
            info.onRetry();
          },
          child: const Text('重试失败项'),
        ),
      ],
    ),
  );
}

// ============================================================
// CategoryPickerSheet - 分类选择底部 Sheet
// ============================================================

/// 显示分类选择底部 Sheet
/// 返回选中的分类值（task/note/inbox/project）或 null（取消）
Future<String?> showCategoryPickerSheet(BuildContext context) {
  return showModalBottomSheet<String>(
    context: context,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(
        top: Radius.circular(AppRadius.card),
      ),
    ),
    builder: (context) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 拖拽指示条
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.sm),
            child: Container(
              width: 32,
              height: 4,
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.onSurfaceVariant
                    .withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          // 标题
          Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Text(
              '选择目标分类',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
          const Divider(height: 1),
          // 分类选项列表
          ...CategoryMeta.all.map(
            (opt) => ListTile(
              leading: Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: opt.color.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppRadius.button),
                ),
                child: Icon(opt.icon, size: 20, color: opt.color),
              ),
              title: Text(opt.label),
              trailing: Icon(
                Icons.arrow_forward_ios,
                size: 14,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              onTap: () => Navigator.of(context).pop(opt.value),
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
        ],
      ),
    ),
  );
}
