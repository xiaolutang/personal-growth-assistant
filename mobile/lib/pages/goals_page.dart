import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/theme.dart';
import '../providers/goals_provider.dart';

// ============================================================
// GoalsPage - 目标管理页
//
// 功能：
// - 展示目标列表，每项显示标题、进度条、截止日期
// - 点击目标卡片 → push 到 GoalDetailPage
// - 空列表引导文案
// ============================================================

class GoalsPage extends ConsumerStatefulWidget {
  const GoalsPage({super.key});

  @override
  ConsumerState<GoalsPage> createState() => _GoalsPageState();
}

class _GoalsPageState extends ConsumerState<GoalsPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(goalsProvider.notifier).fetchGoals();
    });
  }

  // ----------------------------------------------------------
  // Handlers
  // ----------------------------------------------------------

  void _handleGoalTap(Goal goal) {
    context.push('/goals/${goal.id}');
  }

  // ----------------------------------------------------------
  // Build
  // ----------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(goalsProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('目标'),
        centerTitle: true,
      ),
      body: _buildBody(state, theme),
    );
  }

  Widget _buildBody(GoalsState state, ThemeData theme) {
    if (state.isLoading && state.goals.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.goals.isEmpty) {
      return _buildErrorState(state.error!, theme);
    }

    if (state.goals.isEmpty) {
      return _buildEmptyState(theme);
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(goalsProvider.notifier).fetchGoals(),
      child: ListView(
        padding: const EdgeInsets.only(
          top: AppSpacing.sm,
          bottom: AppSpacing.xl,
        ),
        children: state.goals
            .map((goal) => _buildGoalCard(goal, state, theme))
            .toList(),
      ),
    );
  }

  // ----------------------------------------------------------
  // Goal Card
  // ----------------------------------------------------------

  Widget _buildGoalCard(Goal goal, GoalsState state, ThemeData theme) {
    final progress = (goal.progress ?? 0.0) / 100.0; // backend returns percentage

    return Card(
      margin: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.xs,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      child: InkWell(
        onTap: () => _handleGoalTap(goal),
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      goal.title,
                      style: theme.textTheme.titleSmall,
                    ),
                  ),
                  if (goal.endDate != null)
                    Padding(
                      padding: const EdgeInsets.only(right: AppSpacing.sm),
                      child: Text(
                        _formatDate(goal.endDate!),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.outline,
                        ),
                      ),
                    ),
                  Icon(
                    Icons.chevron_right,
                    color: theme.colorScheme.outline,
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              // Progress bar
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: progress.clamp(0.0, 1.0),
                  minHeight: 6,
                  backgroundColor: theme.colorScheme.surfaceContainerHighest,
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                '${(progress * 100).toStringAsFixed(0)}% 完成',
                style: theme.textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ----------------------------------------------------------
  // Empty & Error
  // ----------------------------------------------------------

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.flag_outlined,
              size: 64,
              color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.4),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              '暂无目标',
              style: theme.textTheme.titleMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              '设定目标并拆解为里程碑，追踪你的成长进度',
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
              onPressed: () => ref.read(goalsProvider.notifier).fetchGoals(),
              child: const Text('重试'),
            ),
          ],
        ),
      ),
    );
  }

  // ----------------------------------------------------------
  // Helpers
  // ----------------------------------------------------------

  String _formatDate(String dateStr) {
    try {
      final dateTime = DateTime.parse(dateStr);
      return '${dateTime.month}月${dateTime.day}日';
    } catch (_) {
      return dateStr;
    }
  }
}
