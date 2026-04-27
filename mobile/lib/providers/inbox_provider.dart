import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../models/entry.dart';
import '../config/constants.dart';
import '../providers/auth_provider.dart';
import '../services/api_client.dart';

// ============================================================
// InboxState - 收件箱页状态
// ============================================================
class InboxState {
  final List<Entry> entries;
  final bool isLoading;
  final String? error;
  final String newEntryText;

  const InboxState({
    this.entries = const [],
    this.isLoading = false,
    this.error,
    this.newEntryText = '',
  });

  InboxState copyWith({
    List<Entry>? entries,
    bool? isLoading,
    Object? error = _sentinel,
    String? newEntryText,
  }) {
    return InboxState(
      entries: entries ?? this.entries,
      isLoading: isLoading ?? this.isLoading,
      error: identical(error, _sentinel) ? this.error : error as String?,
      newEntryText: newEntryText ?? this.newEntryText,
    );
  }

  static const _sentinel = Object();
}

// ============================================================
// InboxNotifier - 收件箱页 Notifier
// ============================================================
class InboxNotifier extends Notifier<InboxState> {
  @override
  InboxState build() {
    return const InboxState();
  }

  /// 获取收件箱列表
  Future<void> fetchInbox() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.fetchEntries<Map<String, dynamic>>(
        type: 'inbox',
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

  /// 创建收件箱条目
  Future<bool> createInboxItem(String title) async {
    if (title.trim().isEmpty) return false;

    try {
      final apiClient = ref.read(apiClientProvider);
      final id = const Uuid().v4();

      await apiClient.createEntry<Map<String, dynamic>>(
        data: {
          'id': id,
          'category': 'inbox',
          'title': title.trim(),
        },
      );

      // 刷新列表
      await fetchInbox();
      return true;
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
      return false;
    }
  }

  /// 转换条目分类（inbox → task/note/project）
  Future<bool> convertCategory(String id, String newCategory) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.updateEntryCategory<Map<String, dynamic>>(
        id: id,
        category: newCategory,
      );

      // 从列表中移除已转换的条目
      final updatedEntries =
          state.entries.where((e) => e.id != id).toList();
      state = state.copyWith(entries: updatedEntries);
      return true;
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
      return false;
    }
  }

  /// 设置新建条目文本
  void setNewEntryText(String text) {
    state = state.copyWith(newEntryText: text);
  }
}

/// 收件箱页 Provider
final inboxProvider =
    NotifierProvider<InboxNotifier, InboxState>(() {
  return InboxNotifier();
});
