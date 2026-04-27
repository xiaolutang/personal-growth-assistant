import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/entry.dart';
import '../config/constants.dart';
import '../providers/auth_provider.dart';
import '../services/api_client.dart';

// ============================================================
// NotesState - 笔记页状态
// ============================================================
class NotesState {
  final List<Entry> entries;
  final bool isLoading;
  final String? error;
  final String searchQuery;

  const NotesState({
    this.entries = const [],
    this.isLoading = false,
    this.error,
    this.searchQuery = '',
  });

  NotesState copyWith({
    List<Entry>? entries,
    bool? isLoading,
    Object? error = _sentinel,
    String? searchQuery,
  }) {
    return NotesState(
      entries: entries ?? this.entries,
      isLoading: isLoading ?? this.isLoading,
      error: identical(error, _sentinel) ? this.error : error as String?,
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }

  static const _sentinel = Object();
}

// ============================================================
// NotesNotifier - 笔记页 Notifier
// ============================================================
class NotesNotifier extends Notifier<NotesState> {
  @override
  NotesState build() {
    return const NotesState();
  }

  /// 获取笔记列表
  Future<void> fetchNotes() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.fetchEntries<Map<String, dynamic>>(
        type: 'note',
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

  /// 搜索笔记
  Future<void> searchNotes(String query) async {
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

      // 过滤只保留 note 类型
      final allEntries = parseEntries(response.data);
      final notes = allEntries
          .where((e) => e.category == 'note')
          .toList();

      state = state.copyWith(entries: notes, isLoading: false);
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
}

/// 笔记页 Provider
final notesProvider =
    NotifierProvider<NotesNotifier, NotesState>(() {
  return NotesNotifier();
});
