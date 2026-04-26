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
// ============================================================
class ExploreNotifier extends Notifier<ExploreState> {
  @override
  ExploreState build() {
    return const ExploreState();
  }

  /// 加载条目列表（带过滤参数）
  Future<void> loadEntries({
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
      state = state.copyWith(entries: entries, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: ApiClient.errorMessage(e),
      );
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
}

/// 探索页 Provider
final exploreProvider =
    NotifierProvider<ExploreNotifier, ExploreState>(() {
  return ExploreNotifier();
});
