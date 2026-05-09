import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/entry.dart';
import '../config/constants.dart';
import '../providers/auth_provider.dart';
import '../services/api_client.dart';

// ============================================================
// BatchResult - 批量操作结果
// ============================================================
class BatchResult {
  final List<String> successIds;
  final List<BatchFailureItem> failedItems;

  const BatchResult({
    this.successIds = const [],
    this.failedItems = const [],
  });

  bool get hasFailures => failedItems.isNotEmpty;

  BatchResult copyWith({
    List<String>? successIds,
    List<BatchFailureItem>? failedItems,
  }) {
    return BatchResult(
      successIds: successIds ?? this.successIds,
      failedItems: failedItems ?? this.failedItems,
    );
  }
}

/// 批量操作失败项
class BatchFailureItem {
  final String id;
  final String error;

  const BatchFailureItem({required this.id, required this.error});
}

/// 批量操作内部结果
class _BatchOpResult {
  final String id;
  final bool success;
  final String? error;

  const _BatchOpResult({
    required this.id,
    required this.success,
    this.error,
  });
}

// ============================================================
// ExploreState - 探索页状态
// ============================================================
class ExploreState {
  final List<Entry> entries;
  final bool isLoading;
  final String? error;
  final String searchQuery;
  final List<String> searchHistory;
  final Set<String> selectedIds;
  final bool isMultiSelectMode;

  const ExploreState({
    this.entries = const [],
    this.isLoading = false,
    this.error,
    this.searchQuery = '',
    this.searchHistory = const [],
    this.selectedIds = const {},
    this.isMultiSelectMode = false,
  });

  ExploreState copyWith({
    List<Entry>? entries,
    bool? isLoading,
    Object? error = _sentinel,
    String? searchQuery,
    List<String>? searchHistory,
    Set<String>? selectedIds,
    bool? isMultiSelectMode,
  }) {
    return ExploreState(
      entries: entries ?? this.entries,
      isLoading: isLoading ?? this.isLoading,
      error: identical(error, _sentinel) ? this.error : error as String?,
      searchQuery: searchQuery ?? this.searchQuery,
      searchHistory: searchHistory ?? this.searchHistory,
      selectedIds: selectedIds ?? this.selectedIds,
      isMultiSelectMode: isMultiSelectMode ?? this.isMultiSelectMode,
    );
  }

  static const _sentinel = Object();
}

// ============================================================
// ExploreNotifier - 探索页 Notifier
//
// Per-tab 缓存：内部维护 Map<int, List<Entry>> 缓存，
// 切换 tab 时读缓存，仅首次或 refresh 时请求 API。
// ============================================================
class ExploreNotifier extends Notifier<ExploreState> {
  /// Per-tab entries 缓存
  final Map<int, List<Entry>> _tabCache = {};

  /// Per-tab error 缓存（null = 无错误，有值 = 该 tab 上次加载失败）
  final Map<int, String?> _tabErrors = {};

  /// 当前激活的 tab index（用于判断切换）
  int _activeTabIndex = 0;

  @override
  ExploreState build() {
    return const ExploreState();
  }

  /// 加载条目列表
  ///
  /// [tabIndex] 传入 tab 索引以启用 per-tab 缓存。
  /// - 首次进入 tab：从 API 获取数据并写入缓存
  /// - 再次进入 tab：从缓存读取，不触发重复 API
  /// - 不传 tabIndex：直接请求 API（向后兼容搜索等场景）
  Future<void> loadEntries({
    int? tabIndex,
    String? type,
    String? status,
    String? tags,
    String? startDate,
    String? endDate,
  }) async {
    // 不指定 tabIndex 时，直接请求 API（搜索模式等场景）
    if (tabIndex == null) {
      await _fetchFromApi(
        type: type,
        status: status,
        tags: tags,
        startDate: startDate,
        endDate: endDate,
      );
      return;
    }

    // 切换到同一 tab，不需要操作
    if (tabIndex == _activeTabIndex && _tabCache.containsKey(tabIndex)) {
      // 从缓存恢复 state
      state = state.copyWith(
        entries: _tabCache[tabIndex]!,
        error: _tabErrors[tabIndex],
        isLoading: false,
      );
      return;
    }

    _activeTabIndex = tabIndex;

    // 缓存命中：直接从缓存恢复
    if (_tabCache.containsKey(tabIndex)) {
      state = state.copyWith(
        entries: _tabCache[tabIndex]!,
        error: _tabErrors[tabIndex],
        isLoading: false,
      );
      return;
    }

    // 缓存未命中：从 API 加载
    await _fetchFromApi(
      tabIndex: tabIndex,
      type: type,
      status: status,
      tags: tags,
      startDate: startDate,
      endDate: endDate,
    );
  }

  /// 刷新指定 tab（清空缓存并重新请求）
  Future<void> refreshTab({
    required int tabIndex,
    String? type,
    String? status,
    String? tags,
    String? startDate,
    String? endDate,
  }) async {
    _tabCache.remove(tabIndex);
    _tabErrors.remove(tabIndex);
    _activeTabIndex = tabIndex;

    await _fetchFromApi(
      tabIndex: tabIndex,
      type: type,
      status: status,
      tags: tags,
      startDate: startDate,
      endDate: endDate,
    );
  }

  /// 内部方法：实际请求 API
  ///
  /// 如果指定了 tabIndex，在 API 响应返回后检查用户是否仍在此 tab。
  /// 若已切换到其他 tab，仅更新缓存不更新全局 state（防止慢响应覆盖）。
  Future<void> _fetchFromApi({
    int? tabIndex,
    String? type,
    String? status,
    String? tags,
    String? startDate,
    String? endDate,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.fetchEntries<Map<String, dynamic>>(
        type: type,
        status: status,
        tags: tags,
        startDate: startDate,
        endDate: endDate,
      );

      final entries = parseEntries(response.data);

      // 如果指定了 tabIndex，写入缓存
      if (tabIndex != null) {
        _tabCache[tabIndex] = entries;
        _tabErrors[tabIndex] = null;
      }

      // 仅当用户仍在当前 tab 时更新全局 state
      if (tabIndex == null || tabIndex == _activeTabIndex) {
        state = state.copyWith(entries: entries, isLoading: false);
      } else {
        // 用户已切换到其他 tab，仅清除 loading（不覆盖当前显示内容）
        state = state.copyWith(isLoading: false);
      }
    } catch (e) {
      final errorMsg = ApiClient.errorMessage(e);

      // 如果指定了 tabIndex，写入错误缓存
      if (tabIndex != null) {
        _tabErrors[tabIndex] = errorMsg;
      }

      // 仅当用户仍在当前 tab 时更新全局 state 的 error
      if (tabIndex == null || tabIndex == _activeTabIndex) {
        state = state.copyWith(
          isLoading: false,
          error: errorMsg,
        );
      } else {
        state = state.copyWith(isLoading: false);
      }
    }
  }

  /// 全文搜索条目
  Future<void> searchEntries(String query) async {
    if (query.trim().isEmpty) {
      state = state.copyWith(searchQuery: '');
      return;
    }

    state = state.copyWith(isLoading: true, error: null, searchQuery: query);

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.searchEntries<Map<String, dynamic>>(
        query: query,
      );

      final entries = parseEntries(response.data);
      addSearchHistory(query);
      state = state.copyWith(entries: entries, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: ApiClient.errorMessage(e),
      );
    }
  }

  /// 清空搜索，恢复列表模式
  void clearSearch() {
    state = state.copyWith(searchQuery: '', entries: const []);
  }

  /// 删除单条条目
  Future<bool> deleteEntry(String id) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.deleteEntry<Map<String, dynamic>>(id: id);

      // 从列表中移除
      final updatedEntries =
          state.entries.where((e) => e.id != id).toList();
      state = state.copyWith(entries: updatedEntries);
      // 同步更新当前 tab 缓存
      _syncCacheAfterMutation(updatedEntries);
      return true;
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
      return false;
    }
  }

  /// 更新条目分类
  Future<bool> updateCategory(String id, String category) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.updateEntryCategory<Map<String, dynamic>>(
        id: id,
        category: category,
      );

      // 更新本地列表中对应条目的分类
      final updatedEntries = state.entries.map((e) {
        if (e.id == id) {
          return e.copyWith(category: category);
        }
        return e;
      }).toList();
      state = state.copyWith(entries: updatedEntries);
      // 同步更新当前 tab 缓存
      _syncCacheAfterMutation(updatedEntries);
      return true;
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
      return false;
    }
  }

  /// 添加搜索历史（去重、截断到上限）
  void addSearchHistory(String query) {
    final trimmed = query.trim();
    if (trimmed.isEmpty) return;

    final history = List<String>.from(state.searchHistory);
    // 去重：移除已有的相同项
    history.remove(trimmed);
    // 新增放在前面
    history.insert(0, trimmed);
    // 截断到上限
    if (history.length > AppConstants.searchHistoryLimit) {
      history.removeRange(AppConstants.searchHistoryLimit, history.length);
    }

    state = state.copyWith(searchHistory: history);
  }

  /// 删除单条搜索历史
  void removeSearchHistory(String query) {
    final history = List<String>.from(state.searchHistory);
    history.remove(query);
    state = state.copyWith(searchHistory: history);
  }

  /// 批量删除
  Future<BatchResult> batchDelete(List<String> ids) async {
    final result = await _batchExecute(
      ids,
      (id) => ref.read(apiClientProvider).deleteEntry<Map<String, dynamic>>(id: id),
    );

    // 从列表中移除成功删除的条目
    final successIdSet = result.successIds.toSet();
    final updatedEntries =
        state.entries.where((e) => !successIdSet.contains(e.id)).toList();
    state = state.copyWith(entries: updatedEntries);
    // 同步更新当前 tab 缓存
    _syncCacheAfterMutation(updatedEntries);

    return result;
  }

  /// 批量更新分类
  Future<BatchResult> batchUpdateCategory(
    List<String> ids,
    String category,
  ) async {
    final result = await _batchExecute(
      ids,
      (id) => ref.read(apiClientProvider).updateEntryCategory<Map<String, dynamic>>(
        id: id,
        category: category,
      ),
    );

    // 更新本地列表中成功的条目分类
    final successIdSet = result.successIds.toSet();
    final updatedEntries = state.entries.map((e) {
      if (successIdSet.contains(e.id)) {
        return e.copyWith(category: category);
      }
      return e;
    }).toList();
    state = state.copyWith(entries: updatedEntries);
    // 同步更新当前 tab 缓存
    _syncCacheAfterMutation(updatedEntries);

    return result;
  }

  /// 通用批量执行：并发调用操作，返回成功/失败分组
  Future<BatchResult> _batchExecute(
    List<String> ids,
    Future<dynamic> Function(String id) action,
  ) async {
    final futures = ids.map((id) async {
      try {
        await action(id);
        return _BatchOpResult(id: id, success: true);
      } catch (e) {
        return _BatchOpResult(
          id: id,
          success: false,
          error: ApiClient.errorMessage(e),
        );
      }
    }).toList();

    final results = await Future.wait(futures);

    final successIds = <String>[];
    final failedItems = <BatchFailureItem>[];
    for (final r in results) {
      if (r.success) {
        successIds.add(r.id);
      } else {
        failedItems.add(BatchFailureItem(id: r.id, error: r.error!));
      }
    }

    return BatchResult(successIds: successIds, failedItems: failedItems);
  }

  /// 切换多选模式
  void toggleMultiSelectMode() {
    state = state.copyWith(
      isMultiSelectMode: !state.isMultiSelectMode,
      selectedIds: {},
    );
  }

  /// 切换选中状态
  void toggleSelection(String id) {
    final selected = Set<String>.from(state.selectedIds);
    if (selected.contains(id)) {
      selected.remove(id);
    } else {
      selected.add(id);
    }
    state = state.copyWith(selectedIds: selected);
  }

  /// 全选
  void selectAll() {
    state = state.copyWith(
      selectedIds: Set<String>.from(state.entries.map((e) => e.id)),
    );
  }

  /// 清除选中
  void clearSelection() {
    state = state.copyWith(selectedIds: {});
  }

  /// mutation 后同步更新当前活跃 tab 的缓存
  /// 搜索模式下不更新缓存（搜索结果是临时的，不应污染 tab 缓存）
  void _syncCacheAfterMutation(List<Entry> updatedEntries) {
    if (state.searchQuery.isNotEmpty) return;
    _tabCache[_activeTabIndex] = updatedEntries;
  }
}

/// 探索页 Provider
final exploreProvider =
    NotifierProvider<ExploreNotifier, ExploreState>(() {
  return ExploreNotifier();
});
