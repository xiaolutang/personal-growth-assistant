import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../providers/entry_provider.dart';
import '../providers/today_provider.dart';
import '../widgets/entry_card.dart';
import '../widgets/morning_digest_card.dart';
import '../widgets/progress_ring.dart';
// FAB 由 Shell 层全局管理

// ============================================================
// TodayPage - 今天 Tab 页面
// ============================================================
class TodayPage extends ConsumerStatefulWidget {
  const TodayPage({super.key});

  @override
  ConsumerState<TodayPage> createState() => _TodayPageState();
}

class _TodayPageState extends ConsumerState<TodayPage> {
  final _quickInputController = TextEditingController();

  @override
  void initState() {
    super.initState();
    // 页面初始化时加载数据
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(todayProvider.notifier).loadData();
    });
  }

  @override
  void dispose() {
    _quickInputController.dispose();
    super.dispose();
  }

  Future<void> _handleRefresh() async {
    await ref.read(todayProvider.notifier).loadData();
  }

  Future<void> _handleQuickSubmit() async {
    final text = _quickInputController.text.trim();
    if (text.isEmpty) return;

    _quickInputController.clear();

    final success = await ref
        .read(entryListProvider.notifier)
        .createInboxEntry(text);

    if (!mounted) return;

    if (success) {
      // 刷新 today 数据以更新"最近动态"列表
      ref.read(todayProvider.notifier).loadData();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('已记录到灵感'),
          duration: Duration(seconds: 1),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('记录失败，请重试'),
          duration: Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final todayState = ref.watch(todayProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('今天'),
        centerTitle: true,
      ),
      body: RefreshIndicator(
        onRefresh: _handleRefresh,
        child: todayState.isLoading && todayState.todayTasks.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : _buildContent(context, theme, todayState),
      ),
    );
  }

  Widget _buildContent(BuildContext context, ThemeData theme, TodayState state) {
    // 错误状态
    if (state.error != null && state.todayTasks.isEmpty && state.recentEntries.isEmpty) {
      return _buildError(state);
    }

    return Column(
      children: [
        Expanded(
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.only(bottom: 16),
            children: [
              // 错误提示条（有数据时用 SnackBar 风格的提示）
              if (state.error != null)
                _buildErrorBanner(state.error!),

              // 晨报卡片（顶部）
              MorningDigestCard(morningDigest: state.morningDigest),

              // 进度卡片
              _buildProgressSection(theme, state),

              const Divider(height: 1, indent: AppSpacing.lg, endIndent: AppSpacing.lg),

              // 今日任务
              _buildTasksSection(theme, state),

              const Divider(height: 1, indent: AppSpacing.lg, endIndent: AppSpacing.lg),

              // 最近动态
              _buildRecentSection(theme, state),
            ],
          ),
        ),
        // 底部快捷录入栏
        _buildQuickInputBar(theme),
      ],
    );
  }

  Widget _buildQuickInputBar(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.sm,
        AppSpacing.sm,
        AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: theme.colorScheme.outlineVariant.withValues(alpha: 0.3),
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: _quickInputController,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _handleQuickSubmit(),
                decoration: InputDecoration(
                  hintText: '记一条灵感...',
                  hintStyle: TextStyle(
                    color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.6),
                    fontSize: AppFontSize.body,
                  ),
                  filled: true,
                  fillColor: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.sm + 2,
                  ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.full),
                    borderSide: BorderSide.none,
                  ),
                  isDense: true,
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            IconButton(
              onPressed: _handleQuickSubmit,
              icon: const Icon(Icons.send_rounded),
              color: AppColors.primary,
              style: IconButton.styleFrom(
                backgroundColor: AppColors.primary.withValues(alpha: 0.1),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildError(TodayState state) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        SizedBox(
          height: MediaQuery.of(context).size.height * 0.5,
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.error_outline,
                  size: 48,
                  color: AppColors.error.withValues(alpha: 0.7),
                ),
                const SizedBox(height: AppSpacing.md),
                Text(
                  state.error ?? '加载失败',
                  style: TextStyle(
                    color: AppColors.error.withValues(alpha: 0.8),
                    fontSize: AppFontSize.body,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.lg),
                FilledButton.tonal(
                  onPressed: _handleRefresh,
                  child: const Text('重试'),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildErrorBanner(String error) {
    return Container(
      margin: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.sm,
      ),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppRadius.button),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, size: 18, color: AppColors.error),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              error,
              style: const TextStyle(fontSize: AppFontSize.caption, color: AppColors.error),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressSection(ThemeData theme, TodayState state) {
    final totalTasks = state.todayTasks.length;
    final doneTasks = state.todayTasks.where(
      (e) => e.status == AppConstants.statusComplete,
    ).length;

    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Row(
        children: [
          // 进度环
          ProgressRing(progress: state.completionRate),
          const SizedBox(width: AppSpacing.xl),
          // 文字描述
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '今日进度',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  totalTasks == 0
                      ? '暂无今日任务'
                      : '已完成 $doneTasks / $totalTasks 个任务',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTasksSection(ThemeData theme, TodayState state) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.sm,
          ),
          child: Text(
            '今日任务',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        if (state.todayTasks.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(
              vertical: AppSpacing.xl,
              horizontal: AppSpacing.lg,
            ),
            child: Center(
              child: Column(
                children: [
                  Icon(
                    Icons.check_circle_outline,
                    size: 40,
                    color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.4),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    '今天暂无任务，点击 + 创建一个吧',
                    style: TextStyle(
                      color: theme.colorScheme.onSurfaceVariant,
                      fontSize: AppFontSize.body,
                    ),
                  ),
                ],
              ),
            ),
          )
        else
          ...state.todayTasks.map(
            (entry) => EntryCard(
              entry: entry,
              onTap: () {
                context.push('/entries/${entry.id}');
              },
            ),
          ),
      ],
    );
  }

  Widget _buildRecentSection(ThemeData theme, TodayState state) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.sm,
          ),
          child: Text(
            '最近动态',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        if (state.recentEntries.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(
              vertical: AppSpacing.xl,
              horizontal: AppSpacing.lg,
            ),
            child: Center(
              child: Column(
                children: [
                  Icon(
                    Icons.article_outlined,
                    size: 40,
                    color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.4),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    '暂无动态，开始记录你的成长吧',
                    style: TextStyle(
                      color: theme.colorScheme.onSurfaceVariant,
                      fontSize: AppFontSize.body,
                    ),
                  ),
                ],
              ),
            ),
          )
        else
          ...state.recentEntries.map(
            (entry) => EntryCard(
              entry: entry,
              onTap: () {
                context.push('/entries/${entry.id}');
              },
            ),
          ),
      ],
    );
  }
}
