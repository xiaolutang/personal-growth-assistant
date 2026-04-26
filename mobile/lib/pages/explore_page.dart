import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/theme.dart';
import '../models/entry.dart';
import '../providers/explore_provider.dart';
import '../widgets/batch_action_bar.dart';
import '../widgets/entry_card.dart';

// ============================================================
// ExplorePage - 探索页（View 层，消费 explore_provider 状态）
//
// 搜索栏 + 5 个类型 Tab + 条目列表 + 三态 + 批量操作
// 搜索时切换到搜索结果模式，清空搜索恢复 Tab 列表模式
// 多选模式：编辑按钮 → 复选框 → 底部操作栏 → 批量删除/转分类
// ============================================================

/// Tab 定义
class _ExploreTab {
  final String label;
  final String? type; // null = 全部（不传 type 参数）

  const _ExploreTab(this.label, this.type);
}

const _tabs = [
  _ExploreTab('全部', null),
  _ExploreTab('任务', 'task'),
  _ExploreTab('笔记', 'note'),
  _ExploreTab('灵感', 'inbox'),
  _ExploreTab('项目', 'project'),
];

class ExplorePage extends ConsumerStatefulWidget {
  const ExplorePage({super.key});

  @override
  ConsumerState<ExplorePage> createState() => _ExplorePageState();
}

class _ExplorePageState extends ConsumerState<ExplorePage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  final _searchController = TextEditingController();
  final _searchFocusNode = FocusNode();
  bool _isSearchMode = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _tabs.length, vsync: this);
    _tabController.addListener(_onTabChanged);
    _searchFocusNode.addListener(_onSearchFocusChanged);
    // 初始加载
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(exploreProvider.notifier).loadEntries();
    });
  }

  void _onTabChanged() {
    if (!_tabController.indexIsChanging) {
      final tab = _tabs[_tabController.index];
      ref.read(exploreProvider.notifier).loadEntries(type: tab.type);
    }
  }

  void _onSearchFocusChanged() {
    if (_searchFocusNode.hasFocus && !_isSearchMode) {
      setState(() => _isSearchMode = true);
    }
  }

  void _exitSearchMode() {
    setState(() => _isSearchMode = false);
    _searchController.clear();
    _searchFocusNode.unfocus();
    ref.read(exploreProvider.notifier).clearSearch();
    // 恢复当前 Tab 的列表
    final tab = _tabs[_tabController.index];
    ref.read(exploreProvider.notifier).loadEntries(type: tab.type);
  }

  void _submitSearch(String query) {
    if (query.trim().isEmpty) return;
    _searchFocusNode.unfocus();
    setState(() => _isSearchMode = false);
    ref.read(exploreProvider.notifier).searchEntries(query.trim());
  }

  void _fillFromHistory(String query) {
    _searchController.text = query;
    _submitSearch(query);
  }

  // ---- 多选模式 ----

  /// 进入/退出多选模式
  void _toggleMultiSelectMode() {
    ref.read(exploreProvider.notifier).toggleMultiSelectMode();
  }

  /// 切换条目选中状态
  void _toggleSelection(String id) {
    ref.read(exploreProvider.notifier).toggleSelection(id);
  }

  /// 全选/取消全选
  void _selectAll() {
    final state = ref.read(exploreProvider);
    if (state.selectedIds.length == state.entries.length) {
      // 已全选 → 清除选中
      ref.read(exploreProvider.notifier).clearSelection();
    } else {
      ref.read(exploreProvider.notifier).selectAll();
    }
  }

  /// 退出多选模式
  void _cancelMultiSelect() {
    ref.read(exploreProvider.notifier).toggleMultiSelectMode();
  }

  /// 批量删除流程
  Future<void> _handleBatchDelete() async {
    final state = ref.read(exploreProvider);
    final ids = state.selectedIds.toList();
    if (ids.isEmpty) return;

    // 弹出确认对话框
    final confirmed = await showBatchDeleteConfirmDialog(
      context,
      count: ids.length,
    );
    if (!confirmed) return;

    // 执行批量删除
    final result =
        await ref.read(exploreProvider.notifier).batchDelete(ids);

    if (!mounted) return;

    if (result.hasFailures) {
      // 部分失败：保留失败项选中，显示失败对话框
      final failedIds = result.failedItems.map((f) => f.id).toSet();
      // 更新选中为仅失败项
      for (final id in ids) {
        if (!failedIds.contains(id) && state.selectedIds.contains(id)) {
          ref.read(exploreProvider.notifier).toggleSelection(id);
        }
      }

      // 获取失败条目标题
      final failNames = result.failedItems.map((f) {
        final entry = state.entries.firstWhere(
          (e) => e.id == f.id,
          orElse: () => Entry(id: f.id, title: f.id, category: ''),
        );
        return entry.title;
      }).toList();

      await showBatchFailureDialog(
        context,
        info: BatchFailureInfo(
          failureCount: result.failedItems.length,
          failureNames: failNames,
          onRetry: _handleBatchDelete,
        ),
        operationName: '删除',
      );
    } else {
      // 全部成功：退出多选模式并刷新
      ref.read(exploreProvider.notifier).toggleMultiSelectMode();
      await _refreshList();
    }
  }

  /// 批量转分类流程
  Future<void> _handleBatchMoveCategory() async {
    final state = ref.read(exploreProvider);
    final ids = state.selectedIds.toList();
    if (ids.isEmpty) return;

    // 弹出分类选择底部 Sheet
    final category = await showCategoryPickerSheet(context);
    if (category == null) return;

    // 执行批量转分类
    final result = await ref.read(exploreProvider.notifier).batchUpdateCategory(
          ids,
          category,
        );

    if (!mounted) return;

    if (result.hasFailures) {
      // 部分失败：保留失败项选中
      final failedIds = result.failedItems.map((f) => f.id).toSet();
      for (final id in ids) {
        if (!failedIds.contains(id) && state.selectedIds.contains(id)) {
          ref.read(exploreProvider.notifier).toggleSelection(id);
        }
      }

      final failNames = result.failedItems.map((f) {
        final entry = state.entries.firstWhere(
          (e) => e.id == f.id,
          orElse: () => Entry(id: f.id, title: f.id, category: ''),
        );
        return entry.title;
      }).toList();

      await showBatchFailureDialog(
        context,
        info: BatchFailureInfo(
          failureCount: result.failedItems.length,
          failureNames: failNames,
          onRetry: _handleBatchMoveCategory,
        ),
        operationName: '转分类',
      );
    } else {
      // 全部成功：退出多选模式并刷新
      ref.read(exploreProvider.notifier).toggleMultiSelectMode();
      await _refreshList();
    }
  }

  /// 刷新当前列表（搜索模式保留 query）
  Future<void> _refreshList() async {
    final state = ref.read(exploreProvider);
    if (state.searchQuery.isNotEmpty) {
      await ref
          .read(exploreProvider.notifier)
          .searchEntries(state.searchQuery);
    } else {
      final tab = _tabs[_tabController.index];
      await ref.read(exploreProvider.notifier).loadEntries(type: tab.type);
    }
  }

  @override
  void dispose() {
    _tabController.removeListener(_onTabChanged);
    _searchFocusNode.removeListener(_onSearchFocusChanged);
    _tabController.dispose();
    _searchController.dispose();
    _searchFocusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(exploreProvider);
    final theme = Theme.of(context);
    final isSearching = state.searchQuery.isNotEmpty;

    return Scaffold(
      appBar: AppBar(
        title: _buildSearchBar(theme),
        actions: [
          // 多选模式切换按钮
          if (!state.isMultiSelectMode)
            // 非多选模式 → 显示「编辑」按钮
            TextButton.icon(
              onPressed: state.entries.isEmpty ? null : _toggleMultiSelectMode,
              icon: const Icon(Icons.checklist, size: 20),
              label: const Text('编辑'),
            )
          else
            // 多选模式 → 显示「取消」按钮
            TextButton(
              onPressed: _cancelMultiSelect,
              child: const Text('取消'),
            ),
        ],
        bottom: isSearching
            ? null
            : TabBar(
                controller: _tabController,
                isScrollable: true,
                tabAlignment: TabAlignment.start,
                tabs: _tabs.map((t) => Tab(text: t.label)).toList(),
              ),
      ),
      body: isSearching
          ? _buildBody(state, theme)
          : TabBarView(
              controller: _tabController,
              children:
                  List.generate(_tabs.length, (_) => _buildBody(state, theme)),
            ),
      // 多选模式时底部显示操作栏
      bottomNavigationBar:
          state.isMultiSelectMode ? _buildBatchActionBar(state) : null,
    );
  }

  /// 构建底部批量操作栏
  Widget _buildBatchActionBar(ExploreState state) {
    return BatchActionBar(
      selectedCount: state.selectedIds.length,
      onDelete: _handleBatchDelete,
      onMoveCategory: _handleBatchMoveCategory,
      onCancel: _cancelMultiSelect,
      onSelectAll: _selectAll,
      isAllSelected:
          state.entries.isNotEmpty &&
          state.selectedIds.length == state.entries.length,
    );
  }

  Widget _buildSearchBar(ThemeData theme) {
    final exploreState = ref.read(exploreProvider);
    return TextField(
      controller: _searchController,
      focusNode: _searchFocusNode,
      decoration: InputDecoration(
        hintText: '搜索条目...',
        prefixIcon: const Icon(Icons.search, size: 20),
        suffixIcon: _searchController.text.isNotEmpty ||
                exploreState.searchQuery.isNotEmpty
            ? IconButton(
                icon: const Icon(Icons.close, size: 20),
                onPressed: _exitSearchMode,
              )
            : null,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(vertical: 8),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(24),
          borderSide: BorderSide.none,
        ),
        filled: true,
        fillColor:
            theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
      ),
      textInputAction: TextInputAction.search,
      onSubmitted: _submitSearch,
    );
  }

  Widget _buildBody(ExploreState state, ThemeData theme) {
    // 搜索模式下且焦点在搜索栏 → 显示搜索历史
    if (_isSearchMode) {
      return _buildSearchHistory(state, theme);
    }

    // 加载态
    if (state.isLoading && state.entries.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    // 错误态
    if (state.error != null && state.entries.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 48,
              color: theme.colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              state.error!,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.error,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton.tonal(
              onPressed: () {
                if (state.searchQuery.isNotEmpty) {
                  ref
                      .read(exploreProvider.notifier)
                      .searchEntries(state.searchQuery);
                } else {
                  final tab = _tabs[_tabController.index];
                  ref
                      .read(exploreProvider.notifier)
                      .loadEntries(type: tab.type);
                }
              },
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }

    // 空状态
    if (state.entries.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              state.searchQuery.isNotEmpty
                  ? Icons.search_off
                  : Icons.explore_outlined,
              size: 48,
              color: theme.colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              state.searchQuery.isNotEmpty
                  ? '未找到「${state.searchQuery}」相关条目'
                  : '暂无条目',
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
    }

    // 条目列表
    return RefreshIndicator(
      onRefresh: _refreshList,
      child: ListView.builder(
        itemCount: state.entries.length,
        itemBuilder: (context, index) {
          final entry = state.entries[index];
          final isSelected = state.selectedIds.contains(entry.id);

          return _buildEntryItem(
            entry: entry,
            isSelected: isSelected,
            isMultiSelectMode: state.isMultiSelectMode,
            theme: theme,
          );
        },
      ),
    );
  }

  /// 构建单条条目（多选模式下显示复选框）
  Widget _buildEntryItem({
    required Entry entry,
    required bool isSelected,
    required bool isMultiSelectMode,
    required ThemeData theme,
  }) {
    if (isMultiSelectMode) {
      // 多选模式：复选框 + 条目卡片
      return InkWell(
        onTap: () => _toggleSelection(entry.id),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.sm,
            vertical: AppSpacing.xs,
          ),
          child: Row(
            children: [
              // 复选框
              Checkbox(
                value: isSelected,
                onChanged: (_) => _toggleSelection(entry.id),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.button),
                ),
              ),
              // 条目卡片（去掉自身 padding 的左侧）
              Expanded(
                child: EntryCard(
                  entry: entry,
                  onTap: () => _toggleSelection(entry.id),
                ),
              ),
            ],
          ),
        ),
      );
    }

    // 普通模式：直接显示卡片
    return EntryCard(
      entry: entry,
      onTap: () => context.go('/entries/${entry.id}'),
    );
  }

  Widget _buildSearchHistory(ExploreState state, ThemeData theme) {
    if (state.searchHistory.isEmpty) {
      return Center(
        child: Text(
          '暂无搜索历史',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            '搜索历史',
            style: theme.textTheme.labelMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        Expanded(
          child: ListView.builder(
            itemCount: state.searchHistory.length,
            itemBuilder: (context, index) {
              final query = state.searchHistory[index];
              return ListTile(
                leading: const Icon(Icons.history, size: 20),
                title: Text(query),
                trailing: IconButton(
                  icon: const Icon(Icons.close, size: 16),
                  onPressed: () {
                    ref
                        .read(exploreProvider.notifier)
                        .removeSearchHistory(query);
                  },
                ),
                onTap: () => _fillFromHistory(query),
                dense: true,
              );
            },
          ),
        ),
      ],
    );
  }
}
