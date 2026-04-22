import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../providers/entry_provider.dart';

// ============================================================
// EntryDetailPage - 条目详情页
//
// 功能：
// - 只读展示条目内容（Markdown 渲染）
// - 标题、分类图标、标签列表
// - 底部状态、优先级、创建时间
// - 顶部 AppBar 返回按钮
// - 404 提示、loading 态
// ============================================================
class EntryDetailPage extends ConsumerStatefulWidget {
  final String entryId;

  const EntryDetailPage({super.key, required this.entryId});

  @override
  ConsumerState<EntryDetailPage> createState() => _EntryDetailPageState();
}

class _EntryDetailPageState extends ConsumerState<EntryDetailPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadEntry();
    });
  }

  void _loadEntry() {
    ref.read(entryDetailProvider.notifier).fetchEntry(widget.entryId);
  }

  @override
  Widget build(BuildContext context) {
    final detailState = ref.watch(entryDetailProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Text(_categoryLabel(detailState.entry?.category)),
        centerTitle: true,
      ),
      body: _buildBody(detailState, theme),
    );
  }

  Widget _buildBody(EntryDetailState state, ThemeData theme) {
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.notFound) {
      return _buildNotFound(theme);
    }

    if (state.error != null && state.entry == null) {
      return _buildError(state.error!, theme);
    }

    final entry = state.entry;
    if (entry == null) {
      return const SizedBox.shrink();
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题
          Text(
            entry.title,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: AppSpacing.md),

          // 标签列表
          if (entry.tags.isNotEmpty) ...[
            _buildTagList(entry.tags, theme),
            const SizedBox(height: AppSpacing.md),
          ],

          // 分割线
          const Divider(),
          const SizedBox(height: AppSpacing.md),

          // Markdown 内容
          if (entry.content != null && entry.content!.isNotEmpty)
            MarkdownBody(
              data: entry.content!,
              selectable: true,
            )
          else
            Text(
              '暂无内容',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),

          const SizedBox(height: AppSpacing.xl),

          // 底部元信息
          _buildMetaInfo(entry, theme),
        ],
      ),
    );
  }

  Widget _buildTagList(List<String> tags, ThemeData theme) {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.xs,
      children: tags.map((tag) {
        return Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.xs,
          ),
          decoration: BoxDecoration(
            color: AppColors.primary.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(AppRadius.button),
          ),
          child: Text(
            '#$tag',
            style: const TextStyle(
              fontSize: AppFontSize.caption,
              color: AppColors.primary,
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildMetaInfo(dynamic entry, ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      child: Column(
        children: [
          if (entry.status != null)
            _buildMetaRow('状态', _statusLabel(entry.status), theme),
          if (entry.priority != null && entry.priority!.isNotEmpty)
            _buildMetaRow('优先级', _priorityLabel(entry.priority), theme),
          if (entry.createdAt != null)
            _buildMetaRow('创建时间', _formatDate(entry.createdAt), theme),
          if (entry.updatedAt != null)
            _buildMetaRow('更新时间', _formatDate(entry.updatedAt), theme),
        ],
      ),
    );
  }

  Widget _buildMetaRow(String label, String value, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          Text(
            value,
            style: theme.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNotFound(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.search_off,
              size: 64,
              color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.4),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              '条目不存在',
              style: theme.textTheme.titleMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              '该条目可能已被删除或链接无效',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.6),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildError(String error, ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: theme.colorScheme.error.withValues(alpha: 0.6),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              error,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.error,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.lg),
            ElevatedButton(
              onPressed: _loadEntry,
              child: const Text('重试'),
            ),
          ],
        ),
      ),
    );
  }

  String _categoryLabel(String? category) {
    switch (category) {
      case AppConstants.categoryTask:
        return '任务详情';
      case AppConstants.categoryNote:
        return '笔记详情';
      case AppConstants.categoryInbox:
        return '灵感详情';
      case AppConstants.categoryProject:
        return '项目详情';
      default:
        return '条目详情';
    }
  }

  String _statusLabel(String? status) {
    switch (status) {
      case AppConstants.statusWaitStart:
        return '待开始';
      case AppConstants.statusDoing:
        return '进行中';
      case AppConstants.statusComplete:
        return '已完成';
      case AppConstants.statusPaused:
        return '已暂停';
      case AppConstants.statusCancelled:
        return '已取消';
      default:
        return status ?? '未知';
    }
  }

  String _priorityLabel(String? priority) {
    switch (priority) {
      case 'high':
        return '高';
      case 'medium':
        return '中';
      case 'low':
        return '低';
      default:
        return priority ?? '未知';
    }
  }

  String _formatDate(String? dateStr) {
    if (dateStr == null) return '未知';
    try {
      final date = DateTime.parse(dateStr);
      return DateFormat('yyyy-MM-dd HH:mm').format(date);
    } catch (_) {
      return dateStr;
    }
  }
}
