import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/entry.dart';
import '../providers/inbox_provider.dart';

// ============================================================
// InboxPage - 灵感收集页
//
// 功能：
// - 展示灵感列表，每项显示标题和时间
// - 底部快速输入栏支持直接创建灵感
// - 长按条目弹出转换菜单（转为任务/笔记/项目）
// - 空列表引导文案
// - 下拉刷新
// ============================================================

class InboxPage extends ConsumerStatefulWidget {
  const InboxPage({super.key});

  @override
  ConsumerState<InboxPage> createState() => _InboxPageState();
}

class _InboxPageState extends ConsumerState<InboxPage> {
  final _inputController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadInbox();
    });
  }

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  void _loadInbox() {
    ref.read(inboxProvider.notifier).fetchInbox();
  }

  Future<void> _onRefresh() async {
    await ref.read(inboxProvider.notifier).fetchInbox();
  }

  Future<void> _handleCreate() async {
    final text = _inputController.text.trim();
    if (text.isEmpty) return;

    _inputController.clear();
    ref.read(inboxProvider.notifier).setNewEntryText('');

    final success =
        await ref.read(inboxProvider.notifier).createInboxItem(text);

    if (!success && mounted) {
      final error = ref.read(inboxProvider).error ?? '创建失败，请重试';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error)),
      );
    }
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

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(inboxProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('灵感'),
        centerTitle: true,
      ),
      body: Column(
        children: [
          Expanded(child: _buildBody(state, theme)),
          _buildInputBar(theme),
        ],
      ),
    );
  }

  // ---- 三态渲染：加载中 / 错误 / 列表 ----

  Widget _buildBody(InboxState state, ThemeData theme) {
    if (state.isLoading && state.entries.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.entries.isEmpty) {
      return _buildErrorState(state.error!, theme);
    }

    if (state.entries.isEmpty) {
      return _buildEmptyState(theme);
    }

    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: ListView.builder(
        padding: const EdgeInsets.only(bottom: AppSpacing.xl),
        itemCount: state.entries.length,
        itemBuilder: (context, index) {
          final entry = state.entries[index];
          return _buildInboxItem(entry, theme);
        },
      ),
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
                        _formatTime(entry.createdAt!),
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

  // ---- 空状态 ----

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.lightbulb_outline,
              size: 64,
              color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.4),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              '随时记录灵感',
              style: theme.textTheme.titleMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              '在下方输入框快速记录，稍后再整理为任务或笔记',
              style: theme.textTheme.bodySmall?.copyWith(
                color:
                    theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.6),
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  // ---- 错误状态 ----

  Widget _buildErrorState(String error, ThemeData theme) {
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
              onPressed: _loadInbox,
              child: const Text('重试'),
            ),
          ],
        ),
      ),
    );
  }

  // ---- 底部快速输入栏 ----

  Widget _buildInputBar(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          top: BorderSide(color: theme.colorScheme.outlineVariant),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _inputController,
              decoration: InputDecoration(
                hintText: '记录灵感...',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadius.button),
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md,
                  vertical: AppSpacing.sm,
                ),
              ),
              onSubmitted: (_) => _handleCreate(),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          IconButton.filled(
            onPressed: _handleCreate,
            icon: const Icon(Icons.send),
          ),
        ],
      ),
    );
  }

  // ---- 时间格式化 ----

  String _formatTime(String isoString) {
    try {
      final dt = DateTime.parse(isoString).toLocal();
      final now = DateTime.now();
      final diff = now.difference(dt);

      if (diff.inMinutes < 1) return '刚刚';
      if (diff.inHours < 1) return '${diff.inMinutes} 分钟前';
      if (diff.inDays < 1) return '${diff.inHours} 小时前';
      if (diff.inDays < 7) return '${diff.inDays} 天前';

      return '${dt.month}/${dt.day} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return '';
    }
  }
}
