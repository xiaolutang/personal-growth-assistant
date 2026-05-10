import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/entry.dart';
import '../providers/goals_provider.dart';
import '../utils/date_formatter.dart';
import '../widgets/error_state.dart';
import '../widgets/progress_ring.dart';
import '../widgets/skeleton_loading.dart';

// ============================================================
// GoalDetailPage - 目标详情独立页
//
// 功能：
// - 展示目标标题、描述、进度环
// - 里程碑列表：显示所有里程碑，可勾选完成/取消完成
// - 添加里程碑：底部弹窗输入标题
// - 删除里程碑：滑动删除确认
// - 关联条目列表
// - loading/empty/error 三态处理
//
// 使用独立的 goalDetailProvider(goalId)，
// 与 GoalsPage 的 goalsProvider 完全隔离
// ============================================================

class GoalDetailPage extends ConsumerStatefulWidget {
  final String goalId;

  const GoalDetailPage({super.key, required this.goalId});

  @override
  ConsumerState<GoalDetailPage> createState() => _GoalDetailPageState();
}

class _GoalDetailPageState extends ConsumerState<GoalDetailPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadData();
    });
  }

  Future<void> _loadData() async {
    final notifier = ref.read(goalDetailProvider(widget.goalId).notifier);
    await Future.wait([
      notifier.fetchGoalDetail(widget.goalId),
      notifier.fetchMilestones(widget.goalId),
      notifier.fetchLinkedEntries(widget.goalId),
    ]);
  }

  // ----------------------------------------------------------
  // Handlers
  // ----------------------------------------------------------

  void _handleToggleMilestone(Milestone milestone) {
    final goalId = widget.goalId;
    final isCompleted = milestone.status == 'completed';
    final newStatus = isCompleted ? 'pending' : 'completed';
    ref.read(goalDetailProvider(goalId).notifier).updateMilestone(
          goalId,
          milestone.id,
          {'status': newStatus},
        );
  }

  void _showAddMilestoneDialog() {
    final titleController = TextEditingController();

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
              autofocus: true,
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
              ref.read(goalDetailProvider(widget.goalId).notifier).createMilestone(
                    widget.goalId,
                    {'title': titleController.text.trim()},
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
    final state = ref.watch(goalDetailProvider(widget.goalId));
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('目标详情'),
        centerTitle: true,
      ),
      body: _buildBody(state, theme),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddMilestoneDialog,
        tooltip: '添加里程碑',
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody(GoalDetailState state, ThemeData theme) {
    // Loading state (initial load)
    if (state.isLoading && state.goal == null) {
      return const SingleChildScrollView(
        child: SkeletonLoading(layout: SkeletonLayout.listCard),
      );
    }

    // Error state (no goal loaded)
    if (state.error != null && state.goal == null) {
      return ErrorStateWidget(
        message: state.error!,
        onRetry: _loadData,
      );
    }

    final goal = state.goal;
    if (goal == null) {
      return const SizedBox.shrink();
    }

    return RefreshIndicator(
      onRefresh: () async => _loadData(),
      child: ListView(
        padding: const EdgeInsets.only(
          top: AppSpacing.sm,
          bottom: 80, // space for FAB
        ),
        children: [
          _buildGoalHeader(goal, theme),
          const Divider(height: 1),
          _buildMilestoneSection(state.milestones, theme),
          const Divider(height: 1),
          _buildLinkedEntriesSection(state.linkedEntries, theme),
        ],
      ),
    );
  }

  // ----------------------------------------------------------
  // Goal Header
  // ----------------------------------------------------------

  Widget _buildGoalHeader(Goal goal, ThemeData theme) {
    final progress = (goal.progress ?? 0.0) / 100.0;

    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  goal.title,
                  style: theme.textTheme.titleLarge,
                ),
                if (goal.description != null &&
                    goal.description!.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    goal.description!,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
                if (goal.startDate != null || goal.endDate != null) ...[
                  const SizedBox(height: AppSpacing.sm),
                  _buildDateRange(goal, theme),
                ],
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          ProgressRing(progress: progress.clamp(0.0, 1.0), size: 80),
        ],
      ),
    );
  }

  Widget _buildDateRange(Goal goal, ThemeData theme) {
    return Row(
      children: [
        if (goal.startDate != null)
          Text(
            DateFormatter.formatShortDate(goal.startDate!),
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.outline,
            ),
          ),
        if (goal.startDate != null && goal.endDate != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
            child: Text(
              '-',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
          ),
        if (goal.endDate != null)
          Text(
            DateFormatter.formatShortDate(goal.endDate!),
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.outline,
            ),
          ),
      ],
    );
  }

  // ----------------------------------------------------------
  // Milestones Section
  // ----------------------------------------------------------

  Widget _buildMilestoneSection(
    List<Milestone> milestones,
    ThemeData theme,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.md,
            AppSpacing.md,
            AppSpacing.md,
            AppSpacing.sm,
          ),
          child: Row(
            children: [
              Icon(
                Icons.flag_outlined,
                size: 20,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: AppSpacing.xs),
              Text(
                '里程碑',
                style: theme.textTheme.titleSmall?.copyWith(
                  color: theme.colorScheme.primary,
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Text(
                '${milestones.length}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
            ],
          ),
        ),
        if (milestones.isEmpty)
          _buildMilestoneEmpty(theme)
        else
          ...milestones.map((m) => _buildMilestoneItem(m, theme)),
        const SizedBox(height: AppSpacing.sm),
      ],
    );
  }

  Widget _buildMilestoneEmpty(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Center(
        child: Text(
          '暂无里程碑，点击右下角按钮添加',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.outline,
          ),
        ),
      ),
    );
  }

  Widget _buildMilestoneItem(Milestone milestone, ThemeData theme) {
    final isCompleted = milestone.status == 'completed';

    return Dismissible(
      key: ValueKey(milestone.id),
      direction: DismissDirection.endToStart,
      confirmDismiss: (direction) async {
        final confirmed = await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('确认删除'),
            content: Text('确定要删除里程碑「${milestone.title}」吗？'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('取消'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('删除'),
              ),
            ],
          ),
        );
        return confirmed ?? false;
      },
      onDismissed: (direction) {
        ref
            .read(goalDetailProvider(widget.goalId).notifier)
            .deleteMilestone(widget.goalId, milestone.id);
      },
      background: Container(
        color: theme.colorScheme.error,
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: AppSpacing.lg),
        child: Icon(Icons.delete, color: theme.colorScheme.onError),
      ),
      child: ListTile(
        leading: IconButton(
          icon: Icon(
            isCompleted
                ? Icons.check_circle
                : Icons.radio_button_unchecked,
            color: isCompleted ? AppColors.success : theme.colorScheme.outline,
          ),
          onPressed: () => _handleToggleMilestone(milestone),
        ),
        title: Text(
          milestone.title,
          style: isCompleted
              ? theme.textTheme.bodyMedium?.copyWith(
                  decoration: TextDecoration.lineThrough,
                  color: theme.colorScheme.outline,
                )
              : theme.textTheme.bodyMedium,
        ),
        subtitle: milestone.dueDate != null
            ? Text(
                DateFormatter.formatShortDate(milestone.dueDate!),
                style: theme.textTheme.bodySmall,
              )
            : null,
      ),
    );
  }

  // ----------------------------------------------------------
  // Linked Entries Section
  // ----------------------------------------------------------

  Widget _buildLinkedEntriesSection(
    List<Entry> entries,
    ThemeData theme,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.md,
            AppSpacing.md,
            AppSpacing.md,
            AppSpacing.sm,
          ),
          child: Row(
            children: [
              Icon(
                Icons.link,
                size: 20,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: AppSpacing.xs),
              Text(
                '关联条目',
                style: theme.textTheme.titleSmall?.copyWith(
                  color: theme.colorScheme.primary,
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Text(
                '${entries.length}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
            ],
          ),
        ),
        if (entries.isEmpty)
          _buildLinkedEntriesEmpty(theme)
        else
          ...entries.map((e) => _buildLinkedEntryItem(e, theme)),
        const SizedBox(height: AppSpacing.lg),
      ],
    );
  }

  Widget _buildLinkedEntriesEmpty(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Center(
        child: Text(
          '暂无关联条目',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.outline,
          ),
        ),
      ),
    );
  }

  Widget _buildLinkedEntryItem(Entry entry, ThemeData theme) {
    return ListTile(
      leading: Icon(
        CategoryMeta.iconOf(entry.category),
        size: 20,
        color: theme.colorScheme.primary,
      ),
      title: Text(
        entry.title,
        style: theme.textTheme.bodyMedium,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: entry.content != null && entry.content!.isNotEmpty
          ? Text(
              entry.content!,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            )
          : null,
    );
  }
}

