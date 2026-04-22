import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/entry.dart';
import '../providers/entry_provider.dart';
import '../widgets/task_card.dart';

// ============================================================
// TasksPage - 任务列表页
//
// 功能：
// - 按状态分组显示任务（进行中、待开始、已完成）
// - 顶部筛选 Tab：全部/进行中/已完成
// - 点击任务跳转到条目详情页
// - 点击状态图标切换任务状态
// - 下拉刷新
// - 空列表引导文案
// ============================================================

/// 筛选 Tab 枚举
enum TaskFilter { all, doing, done }

class TasksPage extends ConsumerStatefulWidget {
  const TasksPage({super.key});

  @override
  ConsumerState<TasksPage> createState() => _TasksPageState();
}

class _TasksPageState extends ConsumerState<TasksPage> {
  TaskFilter _currentFilter = TaskFilter.all;

  @override
  void initState() {
    super.initState();
    // 页面初始化时加载任务
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadTasks();
    });
  }

  void _loadTasks() {
    ref.read(entryListProvider.notifier).fetchEntries(
          type: AppConstants.categoryTask,
          status: _statusFilter,
        );
  }

  String? get _statusFilter {
    switch (_currentFilter) {
      case TaskFilter.all:
        return null;
      case TaskFilter.doing:
        return AppConstants.statusDoing;
      case TaskFilter.done:
        return AppConstants.statusDone;
    }
  }

  Future<void> _onRefresh() async {
    await ref.read(entryListProvider.notifier).fetchEntries(
          type: AppConstants.categoryTask,
          status: _statusFilter,
        );
  }

  void _onFilterChanged(TaskFilter filter) {
    setState(() => _currentFilter = filter);
    ref.read(entryListProvider.notifier).fetchEntries(
          type: AppConstants.categoryTask,
          status: _statusFilter,
        );
  }

  Future<void> _onStatusChanged(Entry entry, String newStatus) async {
    final success = await ref
        .read(entryListProvider.notifier)
        .updateEntryStatus(entry.id, newStatus);

    if (!success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('状态更新失败，请重试')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final entryState = ref.watch(entryListProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('任务'),
        centerTitle: true,
      ),
      body: Column(
        children: [
          // 筛选 Tab
          _buildFilterTabs(theme),
          // 任务列表
          Expanded(
            child: _buildBody(entryState, theme),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterTabs(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.sm,
      ),
      child: Row(
        children: TaskFilter.values.map((filter) {
          final isSelected = _currentFilter == filter;
          return Padding(
            padding: const EdgeInsets.only(right: AppSpacing.sm),
            child: FilterChip(
              selected: isSelected,
              label: Text(_filterLabel(filter)),
              onSelected: (_) => _onFilterChanged(filter),
              backgroundColor: theme.colorScheme.surfaceContainerHighest,
              selectedColor: AppColors.primary.withValues(alpha: 0.15),
              labelStyle: TextStyle(
                color: isSelected ? AppColors.primary : theme.colorScheme.onSurfaceVariant,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
              ),
              showCheckmark: false,
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildBody(EntryListState state, ThemeData theme) {
    if (state.isLoading && state.entries.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.entries.isEmpty) {
      return _buildErrorState(state.error!, theme);
    }

    if (state.entries.isEmpty) {
      return _buildEmptyState(theme);
    }

    // 按状态分组
    final grouped = _groupByStatus(state.entries);

    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: ListView(
        padding: const EdgeInsets.only(bottom: AppSpacing.xl),
        children: [
          // 进行中
          if (grouped['doing'] != null && grouped['doing']!.isNotEmpty)
            _buildGroup('进行中', grouped['doing']!),
          // 待开始
          if (grouped['todo'] != null && grouped['todo']!.isNotEmpty)
            _buildGroup('待开始', grouped['todo']!),
          // 等待开始
          if (grouped['wait_start'] != null && grouped['wait_start']!.isNotEmpty)
            _buildGroup('待开始', grouped['wait_start']!),
          // 已完成
          if (grouped['done'] != null && grouped['done']!.isNotEmpty)
            _buildGroup('已完成', grouped['done']!),
        ],
      ),
    );
  }

  Widget _buildGroup(String label, List<Entry> entries) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.md,
            AppSpacing.lg,
            AppSpacing.xs,
          ),
          child: Text(
            '$label (${entries.length})',
            style: TextStyle(
              fontSize: AppFontSize.caption,
              fontWeight: FontWeight.w600,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        ...entries.map((entry) {
              return TaskCard(
                entry: entry,
                onTap: () => context.push('/entries/${entry.id}'),
                onStatusChanged: (newStatus) =>
                    _onStatusChanged(entry, newStatus),
              );
            }),
      ],
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.check_circle_outline,
              size: 64,
              color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.4),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              '暂无任务',
              style: theme.textTheme.titleMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              '通过 AI 对话创建任务，或点击首页快速操作添加',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.6),
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
              onPressed: _loadTasks,
              child: const Text('重试'),
            ),
          ],
        ),
      ),
    );
  }

  String _filterLabel(TaskFilter filter) {
    switch (filter) {
      case TaskFilter.all:
        return '全部';
      case TaskFilter.doing:
        return '进行中';
      case TaskFilter.done:
        return '已完成';
    }
  }

  Map<String, List<Entry>> _groupByStatus(List<Entry> entries) {
    final result = <String, List<Entry>>{};
    for (final entry in entries) {
      final status = entry.status ?? 'todo';
      result.putIfAbsent(status, () => []).add(entry);
    }
    return result;
  }
}
