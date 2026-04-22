import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/entry.dart';
import '../providers/auth_provider.dart';
import '../services/api_client.dart';

// ============================================================
// EntryListState - 条目列表状态
// ============================================================
class EntryListState {
  final List<Entry> entries;
  final bool isLoading;
  final String? error;

  const EntryListState({
    this.entries = const [],
    this.isLoading = false,
    this.error,
  });

  EntryListState copyWith({
    List<Entry>? entries,
    bool? isLoading,
    String? error,
  }) {
    return EntryListState(
      entries: entries ?? this.entries,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

// ============================================================
// EntryListNotifier - 条目列表 Notifier
// ============================================================
class EntryListNotifier extends Notifier<EntryListState> {
  @override
  EntryListState build() {
    return const EntryListState();
  }

  /// 获取条目列表
  Future<void> fetchEntries({
    String? type,
    String? status,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final apiClient = ref.read(apiClientProvider);
      final queryParams = <String, dynamic>{};
      if (type != null) queryParams['type'] = type;
      if (status != null) queryParams['status'] = status;

      final response = await apiClient.get<Map<String, dynamic>>(
        '/entries',
        queryParameters: queryParams.isNotEmpty ? queryParams : null,
      );

      final entries = _parseEntries(response.data);
      state = state.copyWith(entries: entries, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: ApiClient.errorMessage(e),
      );
    }
  }

  /// 更新条目状态（本地乐观更新 + API 调用）
  Future<bool> updateEntryStatus(String entryId, String newStatus) async {
    // 乐观更新：先在本地切换状态
    final originalEntries = state.entries;
    final updatedEntries = originalEntries.map((e) {
      if (e.id == entryId) {
        return e.copyWith(status: newStatus);
      }
      return e;
    }).toList();

    state = state.copyWith(entries: updatedEntries);

    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.put<Map<String, dynamic>>(
        '/entries/$entryId',
        data: {'status': newStatus},
      );
      return true;
    } catch (e) {
      // 回滚
      state = state.copyWith(
        entries: originalEntries,
        error: ApiClient.errorMessage(e),
      );
      return false;
    }
  }

  List<Entry> _parseEntries(Map<String, dynamic>? response) {
    if (response == null) return const [];
    final entriesJson = response['entries'] as List<dynamic>?;
    if (entriesJson == null) return const [];
    return entriesJson
        .map((e) => Entry.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

/// 条目列表 Provider
final entryListProvider =
    NotifierProvider<EntryListNotifier, EntryListState>(() {
  return EntryListNotifier();
});

// ============================================================
// EntryDetailState - 条目详情状态
// ============================================================
class EntryDetailState {
  final Entry? entry;
  final bool isLoading;
  final String? error;
  final bool notFound;

  const EntryDetailState({
    this.entry,
    this.isLoading = false,
    this.error,
    this.notFound = false,
  });

  EntryDetailState copyWith({
    Entry? entry,
    bool? isLoading,
    String? error,
    bool? notFound,
  }) {
    return EntryDetailState(
      entry: entry ?? this.entry,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      notFound: notFound ?? this.notFound,
    );
  }
}

// ============================================================
// EntryDetailNotifier - 条目详情 Notifier
// ============================================================
class EntryDetailNotifier extends Notifier<EntryDetailState> {
  @override
  EntryDetailState build() {
    return const EntryDetailState();
  }

  /// 获取单个条目
  Future<void> fetchEntry(String entryId) async {
    state = state.copyWith(isLoading: true, error: null, notFound: false);

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.get<Map<String, dynamic>>(
        '/entries/$entryId',
      );

      final entry = Entry.fromJson(response.data!);
      state = state.copyWith(entry: entry, isLoading: false);
    } catch (e) {
      final errorMsg = ApiClient.errorMessage(e);
      final isNotFound = errorMsg.contains('不存在');
      state = state.copyWith(
        isLoading: false,
        error: errorMsg,
        notFound: isNotFound,
      );
    }
  }
}

/// 条目详情 Provider（每个 ID 创建独立实例）
final entryDetailProvider =
    NotifierProvider<EntryDetailNotifier, EntryDetailState>(() {
  return EntryDetailNotifier();
});
