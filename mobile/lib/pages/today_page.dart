import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/command_result.dart';
import '../providers/command_bar_provider.dart';
import '../providers/today_provider.dart';
import '../widgets/empty_state.dart';
import '../widgets/entry_card.dart';
import '../widgets/error_state.dart';
import '../widgets/morning_digest_card.dart';
import '../widgets/skeleton_loading.dart';
import '../widgets/progress_ring.dart';
// FAB 由 Shell 层全局管理

// ============================================================
// TodayPage - 今天 Tab 页面
//
// F02: 底部输入栏改为智能命令栏：
// - 用户输入任意内容，AI 判断意图后内联展示结果
// - 创建/更新 → toast + 刷新
// - 问答 → 内联卡片
// - 闲聊 → 跳转日知链接
// - 错误 → 错误条 + 重试
// 不走聊天气泡，不共享 chatProvider。
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
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(todayProvider.notifier).loadData();

      // 监听 commandBarProvider 结果变化
      ref.listenManual(commandBarProvider, (previous, next) {
        _onCommandResultChanged(previous, next);
      });
    });
  }

  /// 命令结果变化时处理副作用（SnackBar toast、刷新 today 数据、清空输入框）
  void _onCommandResultChanged(CommandBarState? previous, CommandBarState next) {
    final prevResult = previous?.result;
    final nextResult = next.result;

    // 只在 result 从 null/旧值变为新值时触发
    if (nextResult == null || nextResult == prevResult) return;
    if (previous?.isLoading == true && next.isLoading) return;

    // 成功/回答/跳转：清空输入框
    if (nextResult.type != CommandResultType.error) {
      _quickInputController.clear();
    }

    if (nextResult.type == CommandResultType.success) {
      // success → SnackBar + 刷新 today 数据
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(nextResult.message),
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
      ref.read(todayProvider.notifier).loadData();
    }
  }

  @override
  void dispose() {
    _quickInputController.dispose();
    super.dispose();
  }

  Future<void> _handleRefresh() async {
    await ref.read(todayProvider.notifier).loadData();
  }

  /// 命令栏提交：调用 commandBarProvider.executeCommand()
  void _handleQuickSubmit() {
    final text = _quickInputController.text.trim();
    if (text.isEmpty) return;

    ref.read(commandBarProvider.notifier).executeCommand(text);
  }

  /// 重试上次命令
  void _handleRetry() {
    ref.read(commandBarProvider.notifier).retry();
  }

  /// 清除命令结果（关闭内联卡片）
  void _dismissResult() {
    ref.read(commandBarProvider.notifier).clearResult();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final todayState = ref.watch(todayProvider);
    final commandState = ref.watch(commandBarProvider);

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
            : _buildContent(context, theme, todayState, commandState),
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    ThemeData theme,
    TodayState state,
    CommandBarState commandState,
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
        // 命令栏区域：结果展示 + 输入栏
        _buildCommandArea(theme, commandState),
      ],
    );
  }

  /// 命令栏区域：结果展示 + 错误条 + 输入栏
  Widget _buildCommandArea(ThemeData theme, CommandBarState commandState) {
    final result = commandState.result;

    return Container(
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
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // 内联结果展示区
            if (result != null) _buildResultCard(theme, result),
            // 错误条
            if (result?.type == CommandResultType.error)
              _buildCommandErrorBar(theme, result!),
            // 输入栏
            _buildQuickInputBar(theme, commandState),
          ],
        ),
      ),
    );
  }

  /// 内联结果卡片（answer / redirect_chat）
  Widget _buildResultCard(ThemeData theme, CommandResult result) {
    switch (result.type) {
      case CommandResultType.answer:
        return _buildAnswerCard(theme, result);
      case CommandResultType.redirectChat:
        return _buildRedirectCard(theme);
      case CommandResultType.success:
      case CommandResultType.error:
        return const SizedBox.shrink();
    }
  }

  /// AI 回答内联卡片（有关闭按钮）
  Widget _buildAnswerCard(ThemeData theme, CommandResult result) {
    return Container(
      margin: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, 0),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.auto_awesome, size: 18, color: AppColors.primary),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              result.answer ?? result.message,
              style: theme.textTheme.bodyMedium,
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          GestureDetector(
            onTap: _dismissResult,
            child: Icon(
              Icons.close,
              size: 18,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }

  /// 跳转日知提示卡片
  Widget _buildRedirectCard(ThemeData theme) {
    return InkWell(
      onTap: () {
        // 跳转前清除 redirect 结果，避免返回时残留卡片
        ref.read(commandBarProvider.notifier).clearResult();
        context.go('/chat');
      },
      child: Container(
        margin: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, 0),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm + 2,
        ),
        decoration: BoxDecoration(
          color: AppColors.primary.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(AppRadius.card),
        ),
        child: Row(
          children: [
            const Icon(Icons.chat_bubble_outline, size: 18, color: AppColors.primary),
            const SizedBox(width: AppSpacing.sm),
            Text(
              '在日知中继续对话',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: AppColors.primary,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(width: AppSpacing.xs),
            const Icon(Icons.arrow_forward_ios, size: 14, color: AppColors.primary),
          ],
        ),
      ),
    );
  }

  /// 命令错误条（红色 + 重试按钮）
  Widget _buildCommandErrorBar(ThemeData theme, CommandResult result) {
    return Container(
      margin: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.sm, AppSpacing.lg, 0),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppRadius.button),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, size: 16, color: AppColors.error),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              result.message,
              style: const TextStyle(
                fontSize: AppFontSize.caption,
                color: AppColors.error,
              ),
            ),
          ),
          TextButton(
            onPressed: _handleRetry,
            style: TextButton.styleFrom(
              foregroundColor: AppColors.error,
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            child: const Text('重试', style: TextStyle(fontSize: AppFontSize.caption)),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickInputBar(ThemeData theme, CommandBarState commandState) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.sm,
        AppSpacing.sm,
        AppSpacing.sm,
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _quickInputController,
              textInputAction: TextInputAction.send,
              onSubmitted: commandState.isLoading ? null : (_) => _handleQuickSubmit(),
              enabled: !commandState.isLoading,
              decoration: InputDecoration(
                hintText: '输入指令或问题...',
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
          // 发送按钮（loading 时显示进度指示器）
          IconButton(
            onPressed: commandState.isLoading ? null : _handleQuickSubmit,
            icon: commandState.isLoading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: AppColors.primary,
                    ),
                  )
                : const Icon(Icons.send_rounded),
            color: AppColors.primary,
            style: IconButton.styleFrom(
              backgroundColor: AppColors.primary.withValues(alpha: 0.1),
            ),
          ),
        ],
      ),
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
