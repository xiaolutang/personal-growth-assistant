import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/theme.dart';
import '../providers/goals_provider.dart';

// ============================================================
// GoalsPage - 目标管理页
//
// 功能：
// - 展示目标列表，每项显示标题、进度条、截止日期
// - 点击目标展开显示里程碑列表
// - 支持添加里程碑（标题 + 日期）
// - 支持标记里程碑完成 / 删除（删除需确认弹窗）
// - 空标题显示校验提示
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
    final state = ref.read(goalsProvider);
    if (state.selectedGoal?.id == goal.id) {
      // 收起当前目标
      ref.read(goalsProvider.notifier).deselectGoal();
    } else {
      // 展开新目标：加载详情 + 里程碑
      ref.read(goalsProvider.notifier).fetchGoalDetail(goal.id);
      ref.read(goalsProvider.notifier).fetchMilestones(goal.id);
    }
  }

  void _handleToggleMilestone(Milestone milestone) {
    final goalId = ref.read(goalsProvider).selectedGoal?.id;
    if (goalId == null) return;

    final isCompleted = milestone.status == 'completed';
    final newStatus = isCompleted ? 'pending' : 'completed';
    ref.read(goalsProvider.notifier).updateMilestone(
          goalId,
          milestone.id,
          {'status': newStatus},
        );
  }

  void _handleDeleteMilestone(Milestone milestone) {
    final goalId = ref.read(goalsProvider).selectedGoal?.id;
    if (goalId == null) return;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('确认删除'),
        content: Text('确定要删除里程碑「${milestone.title}」吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              ref
                  .read(goalsProvider.notifier)
                  .deleteMilestone(goalId, milestone.id);
            },
            child: const Text('删除'),
          ),
        ],
      ),
    );
  }

  void _showAddMilestoneDialog(String goalId) {
    final titleController = TextEditingController();
    final dateController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('添加里程碑'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: titleController,
              decoration: const InputDecoration(
                labelText: '标题',
                hintText: '输入里程碑标题',
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            TextField(
              controller: dateController,
              decoration: const InputDecoration(
                labelText: '截止日期',
                hintText: 'YYYY-MM-DD',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () {
              if (titleController.text.trim().isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('请输入里程碑标题')),
                );
                return;
              }
              Navigator.pop(ctx);
              ref.read(goalsProvider.notifier).createMilestone(
                    goalId,
                    {
                      'title': titleController.text.trim(),
                      if (dateController.text.isNotEmpty)
                        'due_date': dateController.text.trim(),
                    },
                  );
            },
            child: const Text('添加'),
          ),
        ],
      ),
    );
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
    final isSelected = state.selectedGoal?.id == goal.id;
    final milestones = isSelected ? state.milestones : <Milestone>[];
    final progress = (goal.progress ?? 0.0) / 100.0; // backend returns percentage

    return Card(
      margin: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.xs,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      child: Column(
        children: [
          // Goal header - tappable
          InkWell(
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
                        isSelected
                            ? Icons.expand_less
                            : Icons.expand_more,
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
          // Expanded milestones
          if (isSelected) ...[
            const Divider(height: 1),
            _buildMilestonesList(milestones, theme),
            _buildAddMilestoneButton(goal.id, theme),
            const SizedBox(height: AppSpacing.sm),
          ],
        ],
      ),
    );
  }

  // ----------------------------------------------------------
  // Milestones
  // ----------------------------------------------------------

  Widget _buildMilestonesList(
    List<Milestone> milestones,
    ThemeData theme,
  ) {
    if (milestones.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Text(
          '暂无里程碑',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.outline,
          ),
        ),
      );
    }

    return Column(
      children: milestones.map((m) {
        final isCompleted = m.status == 'completed';
        return ListTile(
          dense: true,
          leading: IconButton(
            icon: Icon(
              isCompleted
                  ? Icons.check_circle
                  : Icons.radio_button_unchecked,
              color: isCompleted ? AppColors.success : theme.colorScheme.outline,
            ),
            onPressed: () => _handleToggleMilestone(m),
          ),
          title: Text(
            m.title,
            style: isCompleted
                ? theme.textTheme.bodyMedium?.copyWith(
                    decoration: TextDecoration.lineThrough,
                    color: theme.colorScheme.outline,
                  )
                : theme.textTheme.bodyMedium,
          ),
          subtitle: m.dueDate != null
              ? Text(
                  _formatDate(m.dueDate!),
                  style: theme.textTheme.bodySmall,
                )
              : null,
          trailing: IconButton(
            icon: const Icon(Icons.delete_outline, size: 20),
            onPressed: () => _handleDeleteMilestone(m),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildAddMilestoneButton(String goalId, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.xs,
      ),
      child: Align(
        alignment: Alignment.centerRight,
        child: TextButton.icon(
          onPressed: () => _showAddMilestoneDialog(goalId),
          icon: const Icon(Icons.add, size: 18),
          label: const Text('添加里程碑'),
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
