import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../providers/today_provider.dart';
import '../widgets/empty_state.dart';
import '../widgets/entry_card.dart';
import '../widgets/error_state.dart';
import '../widgets/morning_digest_card.dart';
import '../widgets/skeleton_loading.dart';
import '../widgets/progress_ring.dart';
// FAB 由 Shell 层全局管理

// ============================================================
// TodayPage - 今天 Tab 页面（纯仪表盘）
//
// 展示晨报、进度、今日任务、最近动态。
// 页面级加载失败时显示标准 ErrorStateWidget（含重试）。
// ============================================================
class TodayPage extends ConsumerStatefulWidget {
  const TodayPage({super.key});

  @override
  ConsumerState<TodayPage> createState() => _TodayPageState();
}

class _TodayPageState extends ConsumerState<TodayPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(todayProvider.notifier).loadData();
    });
  }

  Future<void> _handleRefresh() async {
    await ref.read(todayProvider.notifier).loadData();
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
            ? const SingleChildScrollView(
                child: SkeletonList(itemCount: 3),
              )
            : _buildContent(context, theme, todayState),
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    ThemeData theme,
    TodayState state,
  ) {
    // 错误状态（用 ListView 包裹以保留下拉刷新能力）
    if (state.error != null && state.todayTasks.isEmpty && state.recentEntries.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          SizedBox(
            height: MediaQuery.of(context).size.height * 0.6,
            child: ErrorStateWidget(
              message: state.error ?? '加载失败',
              onRetry: _handleRefresh,
            ),
          ),
        ],
      );
    }

    return ListView(
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
          const Padding(
            padding: EdgeInsets.symmetric(
              vertical: AppSpacing.xl,
              horizontal: AppSpacing.lg,
            ),
            child: EmptyStateWidget(
              icon: Icons.check_circle_outline,
              title: '今天暂无任务，点击 + 创建一个吧',
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
          const Padding(
            padding: EdgeInsets.symmetric(
              vertical: AppSpacing.xl,
              horizontal: AppSpacing.lg,
            ),
            child: EmptyStateWidget(
              icon: Icons.article_outlined,
              title: '暂无动态，开始记录你的成长吧',
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
