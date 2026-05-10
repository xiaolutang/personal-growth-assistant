import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/entry.dart';
import '../providers/inbox_provider.dart';
import '../utils/date_formatter.dart';
import '../widgets/empty_state.dart';
import '../widgets/error_state.dart';
import '../widgets/skeleton_loading.dart';

// ============================================================
// InboxPage - 灵感收集页
//
// 功能：
// - 展示灵感列表，每项显示标题和时间
// - 长按条目弹出转换菜单（转为任务/笔记/项目）
// - 左滑删除（Dismissible + 乐观更新 + SnackBar 撤销）
// - 空列表引导文案（引导使用全局 FAB 创建灵感）
// - 下拉刷新
// ============================================================

class InboxPage extends ConsumerStatefulWidget {
  const InboxPage({super.key});

  @override
  ConsumerState<InboxPage> createState() => _InboxPageState();
}

class _InboxPageState extends ConsumerState<InboxPage> {
  // 延迟删除的 Timer（用于撤销取消）
  Timer? _pendingDeleteTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadInbox();
    });
  }

  @override
  void dispose() {
    _pendingDeleteTimer?.cancel();
    super.dispose();
  }

  void _loadInbox() {
    ref.read(inboxProvider.notifier).fetchInbox();
  }

  Future<void> _onRefresh() async {
    await ref.read(inboxProvider.notifier).fetchInbox();
  }

  void _showConvertMenu(Entry entry) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Text(
                '转换灵感',
                style: Theme.of(context).textTheme.titleSmall,
              ),
            ),
            const Divider(height: 1),
            ListTile(
              leading: const Icon(Icons.check_circle),
              title: const Text('转为任务'),
              onTap: () => _handleConvert(entry.id, 'task'),
            ),
            ListTile(
              leading: const Icon(Icons.note),
              title: const Text('转为笔记'),
              onTap: () => _handleConvert(entry.id, 'note'),
            ),
            ListTile(
              leading: const Icon(Icons.folder),
              title: const Text('转为项目'),
              onTap: () => _handleConvert(entry.id, 'project'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleConvert(String entryId, String category) async {
    Navigator.pop(context); // 关闭底部菜单
    try {
      final success = await ref
          .read(inboxProvider.notifier)
          .convertCategory(entryId, category);

      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('已转为${CategoryMeta.labelOf(category)}')),
        );
      } else if (!success && mounted) {
        final error = ref.read(inboxProvider).error ?? '转换失败';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('转换失败: $error')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('转换失败: $e')),
        );
      }
    }
  }

  // ---- 滑动删除操作 ----

  /// 处理左滑删除（延迟删除 + SnackBar 撤销）
  /// 撤销期内不调用后端 API，撤销只是取消延迟删除
  void _handleDeleteDismiss(Entry entry, int index) {
    final originalEntry = entry;
    final originalIndex = index;

    // 取消前一个待删除 Timer
    _pendingDeleteTimer?.cancel();

    // 延迟 4 秒后才真正调用删除 API
    _pendingDeleteTimer = Timer(const Duration(seconds: 4), () async {
      final success =
          await ref.read(inboxProvider.notifier).deleteEntry(entry.id);
      if (!success && mounted) {
        // API 失败：provider 会自动回滚
        ScaffoldMessenger.of(context).clearSnackBars();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('删除失败，请重试')),
        );
      }
    });

    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('灵感已删除'),
        duration: const Duration(seconds: 4),
        action: SnackBarAction(
          label: '撤销',
          onPressed: () {
            // 撤销：取消延迟删除 + 恢复到 provider 列表原位
            _pendingDeleteTimer?.cancel();
            _pendingDeleteTimer = null;
            ref.read(inboxProvider.notifier).restoreEntry(originalEntry, originalIndex);
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(inboxProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('灵感'),
        centerTitle: true,
      ),
      body: _buildBody(state, theme),
    );
  }

  // ---- 三态渲染：加载中 / 错误 / 列表 ----

  Widget _buildBody(InboxState state, ThemeData theme) {
    if (state.isLoading && state.entries.isEmpty) {
      return const SingleChildScrollView(
        child: SkeletonList(itemCount: 3),
      );
    }

    if (state.error != null && state.entries.isEmpty) {
      return ErrorStateWidget(
        message: state.error!,
        onRetry: _loadInbox,
      );
    }

    if (state.entries.isEmpty) {
      return const EmptyStateWidget(
        icon: Icons.lightbulb_outline,
        title: '随时记录灵感',
        subtitle: '点击右下角按钮，快速记录灵感',
      );
    }

    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: ListView.builder(
        padding: const EdgeInsets.only(bottom: AppSpacing.xl),
        itemCount: state.entries.length,
        itemBuilder: (context, index) {
          final entry = state.entries[index];
          return _buildDismissibleInboxItem(entry, index, theme);
        },
      ),
    );
  }

  /// 构建包裹 Dismissible 的收件箱条目
  Widget _buildDismissibleInboxItem(Entry entry, int index, ThemeData theme) {
    return Dismissible(
      key: ValueKey('dismissible_${entry.id}'),
      // 只支持左滑删除
      direction: DismissDirection.startToEnd,
      background: Container(
        margin: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: AppColors.error,
          borderRadius: BorderRadius.circular(AppRadius.card),
        ),
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.only(left: AppSpacing.xl),
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      onDismissed: (direction) {
        _handleDeleteDismiss(entry, index);
      },
      child: _buildInboxItem(entry, theme),
    );
  }

  Widget _buildInboxItem(Entry entry, ThemeData theme) {
    return Card(
      margin: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.xs,
      ),
      child: InkWell(
        onTap: () => context.push('/entries/${entry.id}'),
        onLongPress: () => _showConvertMenu(entry),
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            children: [
              const Icon(
                Icons.lightbulb_outline,
                color: AppColors.warning,
                size: 20,
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.title,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w500,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (entry.createdAt != null) ...[
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        DateFormatter.formatRelative(entry.createdAt!),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant
                              .withValues(alpha: 0.6),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right,
                color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.4),
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
