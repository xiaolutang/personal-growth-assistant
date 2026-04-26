import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/explore_provider.dart';
import '../widgets/entry_card.dart';

// ============================================================
// ExplorePage - 探索页（View 层，消费 explore_provider 状态）
//
// 搜索栏 + 5 个类型 Tab + 条目列表 + 三态
// 搜索时切换到搜索结果模式，清空搜索恢复 Tab 列表模式
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
    );
  }

  Widget _buildSearchBar(ThemeData theme) {
    return TextField(
      controller: _searchController,
      focusNode: _searchFocusNode,
      decoration: InputDecoration(
        hintText: '搜索条目...',
        prefixIcon: const Icon(Icons.search, size: 20),
        suffixIcon: _searchController.text.isNotEmpty ||
                ref.read(exploreProvider).searchQuery.isNotEmpty
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
        fillColor: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
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
      onRefresh: () async {
        if (state.searchQuery.isNotEmpty) {
          await ref
              .read(exploreProvider.notifier)
              .searchEntries(state.searchQuery);
        } else {
          final tab = _tabs[_tabController.index];
          await ref
              .read(exploreProvider.notifier)
              .loadEntries(type: tab.type);
        }
      },
      child: ListView.builder(
        itemCount: state.entries.length,
        itemBuilder: (context, index) {
          final entry = state.entries[index];
          return EntryCard(
            entry: entry,
            onTap: () => context.go('/entries/${entry.id}'),
          );
        },
      ),
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
