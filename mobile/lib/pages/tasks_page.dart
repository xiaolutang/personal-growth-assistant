import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/entry.dart';
import '../providers/entry_provider.dart';
import '../widgets/empty_state.dart';
import '../widgets/error_state.dart';
import '../widgets/skeleton_loading.dart';
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
// - 左滑完成、右滑删除（Dismissible + 乐观更新）
// ============================================================

/// 筛选 Tab 枚举
enum TaskFilter { all, doing, waitStart, complete }

class TasksPage extends ConsumerStatefulWidget {
  const TasksPage({super.key});

  @override
  ConsumerState<TasksPage> createState() => _TasksPageState();
}

class _TasksPageState extends ConsumerState<TasksPage> {
  TaskFilter _currentFilter = TaskFilter.all;
  // 本地拖拽排序状态（不持久化）
  List<Entry> _reorderedEntries = [];
  // 延迟删除的 Timer Map（per-entry，支持多条目并行删除）
  final Map<String, Timer> _pendingDeleteTimers = {};
  // 待删除的 entry ID 集合（sync 时过滤掉，避免被 provider 数据覆盖回来）
  final Set<String> _pendingDeleteIds = {};

  @override
  void initState() {
    super.initState();
    // 页面初始化时加载任务
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadTasks();
    });
  }

  @override
  void dispose() {
    for (final timer in _pendingDeleteTimers.values) {
      timer.cancel();
    }
    super.dispose();
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
      case TaskFilter.waitStart:
        return AppConstants.statusWaitStart;
      case TaskFilter.complete:
        return AppConstants.statusComplete;
    }
  }

  Future<void> _onRefresh() async {
    await ref.read(entryListProvider.notifier).fetchEntries(
          type: AppConstants.categoryTask,
          status: _statusFilter,
        );
  }

  void _onFilterChanged(TaskFilter filter) {
    setState(() {
      _currentFilter = filter;
      _reorderedEntries = []; // 切换筛选时重置排序
    });
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

  // ---- 滑动操作 ----

  /// 左滑完成（乐观更新 + SnackBar 撤销）
  void _handleCompleteDismiss(Entry entry, int globalIndex) {
    final originalEntry = entry;
    final originalIndex = globalIndex;

    // 从本地列表移除
    setState(() {
      _reorderedEntries.removeAt(globalIndex);
    });

    // 后台调用 API
    _performCompleteWithUndo(originalEntry, originalIndex);
  }

  Future<void> _performCompleteWithUndo(
      Entry entry,
      int originalIndex,) async {
    final success = await ref
        .read(entryListProvider.notifier)
        .updateEntryStatus(entry.id, AppConstants.statusComplete);

    if (!mounted) return;

    if (success) {
      // 刷新 provider 状态以反映完成
      ref.read(entryListProvider.notifier).fetchEntries(
            type: AppConstants.categoryTask,
            status: _statusFilter,
          );
      ScaffoldMessenger.of(context).clearSnackBars();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('任务已完成'),
          duration: const Duration(seconds: 4),
          action: SnackBarAction(
            label: '撤销',
            onPressed: () async {
              // 撤销：恢复到原状态并刷新列表
              final originalStatus = entry.status ?? AppConstants.statusWaitStart;
              await ref
                  .read(entryListProvider.notifier)
                  .updateEntryStatus(entry.id, originalStatus);
              if (mounted) {
                // 重新插入到本地列表原位
                _rollbackEntry(entry, originalIndex);
                // 刷新 provider 以同步最新数据
                ref.read(entryListProvider.notifier).fetchEntries(
                      type: AppConstants.categoryTask,
                      status: _statusFilter,
                    );
              }
            },
          ),
        ),
      );
    } else {
      // API 失败：回滚本地列表
      _rollbackEntry(entry, originalIndex);
      ScaffoldMessenger.of(context).clearSnackBars();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('完成操作失败，请重试')),
      );
    }
  }

  /// 右滑删除（延迟删除 + SnackBar 撤销）
  /// 撤销期内不调用后端 API，撤销只是取消延迟删除
  void _handleDeleteDismiss(Entry entry, int globalIndex) {
    // 取消该条目的前一个待删除 Timer（如有）
    _pendingDeleteTimers[entry.id]?.cancel();

    // 标记为待删除（防止 sync 逻辑用 provider 数据覆盖回来）
    _pendingDeleteIds.add(entry.id);

    // 从本地列表移除
    setState(() {
      _reorderedEntries.removeAt(globalIndex);
    });

    // 延迟 4 秒后才真正调用删除 API
    _pendingDeleteTimers[entry.id] = Timer(const Duration(seconds: 4), () async {
      _pendingDeleteTimers.remove(entry.id);
      _pendingDeleteIds.remove(entry.id);
      final success =
          await ref.read(entryListProvider.notifier).deleteEntry(entry.id);
      if (!success && mounted) {
        // API 失败：回滚本地列表
        _rollbackEntry(entry, globalIndex);
        ScaffoldMessenger.of(context).clearSnackBars();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('删除失败，请重试')),
        );
      }
    });

    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('任务已删除'),
        duration: const Duration(seconds: 4),
        action: SnackBarAction(
          label: '撤销',
          onPressed: () {
            // 撤销：取消延迟删除 + 恢复到本地列表原位
            _pendingDeleteTimers[entry.id]?.cancel();
            _pendingDeleteTimers.remove(entry.id);
            _pendingDeleteIds.remove(entry.id);
            _rollbackEntry(entry, globalIndex);
          },
        ),
      ),
    );
  }

  /// 回滚条目到本地列表原位
  void _rollbackEntry(Entry entry, int originalIndex) {
    setState(() {
      final insertAt = originalIndex.clamp(0, _reorderedEntries.length);
      _reorderedEntries.insert(insertAt, entry);
    });
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
      return const SingleChildScrollView(
        child: SkeletonList(itemCount: 3),
      );
    }

    if (state.error != null && state.entries.isEmpty) {
      return ErrorStateWidget(
        message: state.error!,
        onRetry: _loadTasks,
      );
    }

    if (state.entries.isEmpty) {
      return const EmptyStateWidget(
        icon: Icons.check_circle_outline,
        title: '暂无任务',
        subtitle: '通过 AI 对话创建任务，或点击首页快速操作添加',
      );
    }

    // 数据刷新时同步本地排序（保留已有排序或重置）
    // 过滤掉待删除的 entry（延迟删除模式下 provider 尚未移除）
    final providerEntries =
        state.entries.where((e) => !_pendingDeleteIds.contains(e.id)).toList();

    if (_reorderedEntries.isEmpty ||
        _reorderedEntries.length != providerEntries.length ||
        !_sameEntryIds(_reorderedEntries, providerEntries)) {
      _reorderedEntries = List.of(providerEntries);
    } else {
      // IDs 相同但 entry 数据可能已变（如乐观状态更新），保留排序但刷新数据
      _reorderedEntries = _reorderedEntries
          .map((local) => state.entries.firstWhere((e) => e.id == local.id))
          .toList();
    }

    // 按状态分组
    final grouped = _groupByStatus(_reorderedEntries);

    return RefreshIndicator(
      onRefresh: () async {
        setState(() => _reorderedEntries = []);
        await _onRefresh();
      },
      child: ListView(
        padding: const EdgeInsets.only(bottom: AppSpacing.xl),
        children: [
          // 进行中
          if (grouped['doing'] != null && grouped['doing']!.isNotEmpty)
            _buildGroup('进行中', grouped['doing']!),
          // 待开始
          if (grouped['waitStart'] != null && grouped['waitStart']!.isNotEmpty)
            _buildGroup('待开始', grouped['waitStart']!),
          // 已暂停
          if (grouped['paused'] != null && grouped['paused']!.isNotEmpty)
            _buildGroup('已暂停', grouped['paused']!),
          // 已完成
          if (grouped['complete'] != null && grouped['complete']!.isNotEmpty)
            _buildGroup('已完成', grouped['complete']!),
        ],
      ),
    );
  }

  bool _sameEntryIds(List<Entry> a, List<Entry> b) {
    final idsA = a.map((e) => e.id).toSet();
    final idsB = b.map((e) => e.id).toSet();
    return idsA.length == idsB.length && idsA.containsAll(idsB);
  }

  /// 查找条目在 _reorderedEntries 中的全局索引
  int _globalIndexOf(String entryId) {
    return _reorderedEntries.indexWhere((e) => e.id == entryId);
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
        if (entries.length == 1)
          // 单条目：用 Dismissible 包裹
          _buildDismissibleTaskCard(entries.first)
        else
          ReorderableListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: entries.length,
            onReorder: (oldIndex, newIndex) {
              setState(() {
                if (newIndex > oldIndex) newIndex--;
                // 用 ID 映射重排，不依赖条目在全局列表中的连续性
                final groupIds = entries.map((e) => e.id).toList();
                final movedId = groupIds.removeAt(oldIndex);
                groupIds.insert(newIndex, movedId);
                final groupIdSet = groupIds.toSet();
                final groupEntryMap = {for (var e in entries) e.id: e};
                final reorderedGroup = groupIds.map((id) => groupEntryMap[id]!).toList();
                var gi = 0;
                _reorderedEntries = _reorderedEntries.map((e) {
                  if (groupIdSet.contains(e.id)) {
                    return reorderedGroup[gi++];
                  }
                  return e;
                }).toList();
              });
            },
            proxyDecorator: (child, index, animation) {
              // 拖拽时的视觉效果
              return AnimatedBuilder(
                animation: animation,
                builder: (context, child) {
                  final t = Curves.easeInOut.transform(animation.value);
                  return Transform.scale(
                    scale: 1.0 + 0.05 * t,
                    child: child,
                  );
                },
                child: child,
              );
            },
            itemBuilder: (context, index) {
              final entry = entries[index];
              return KeyedSubtree(
                key: ValueKey(entry.id),
                child: _buildDismissibleTaskCard(entry),
              );
            },
          ),
      ],
    );
  }

  /// 构建包裹 Dismissible 的 TaskCard
  Widget _buildDismissibleTaskCard(Entry entry) {
    final globalIndex = _globalIndexOf(entry.id);

    return Dismissible(
      key: ValueKey('dismissible_${entry.id}'),
      // 左滑：完成（绿色背景）
      background: Container(
        margin: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: AppColors.success,
          borderRadius: BorderRadius.circular(AppRadius.card),
        ),
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.only(left: AppSpacing.xl),
        child: const Icon(Icons.check, color: Colors.white),
      ),
      // 右滑：删除（红色背景）
      secondaryBackground: Container(
        margin: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: AppColors.error,
          borderRadius: BorderRadius.circular(AppRadius.card),
        ),
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: AppSpacing.xl),
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      confirmDismiss: (direction) async {
        // 防止对已完成的任务再次左滑完成
        if (direction == DismissDirection.startToEnd &&
            entry.status == AppConstants.statusComplete) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('任务已完成，无需重复操作')),
            );
          }
          return false;
        }
        return true;
      },
      onDismissed: (direction) {
        if (direction == DismissDirection.startToEnd) {
          // 左滑 → 完成
          _handleCompleteDismiss(entry, globalIndex);
        } else {
          // 右滑 → 删除
          _handleDeleteDismiss(entry, globalIndex);
        }
      },
      child: TaskCard(
        entry: entry,
        onTap: () => context.push('/entries/${entry.id}'),
        onStatusChanged: (newStatus) =>
            _onStatusChanged(entry, newStatus),
      ),
    );
  }

  String _filterLabel(TaskFilter filter) {
    switch (filter) {
      case TaskFilter.all:
        return '全部';
      case TaskFilter.doing:
        return '进行中';
      case TaskFilter.waitStart:
        return '待开始';
      case TaskFilter.complete:
        return '已完成';
    }
  }

  Map<String, List<Entry>> _groupByStatus(List<Entry> entries) {
    final result = <String, List<Entry>>{};
    for (final entry in entries) {
      final status = entry.status ?? 'waitStart';
      result.putIfAbsent(status, () => []).add(entry);
    }
    return result;
  }
}
