import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/entry.dart';
import '../config/constants.dart';
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

      final entries = parseEntries(response.data);
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
}

/// 条目列表 Provider
final entryListProvider =
    NotifierProvider<EntryListNotifier, EntryListState>(() {
  return EntryListNotifier();
});

// ============================================================
// BacklinkItem - 反向引用数据模型
// ============================================================
class BacklinkItem {
  final String id;
  final String title;
  final String? category;
  final String? relationType;
  final String? createdAt;

  const BacklinkItem({
    required this.id,
    required this.title,
    this.category,
    this.relationType,
    this.createdAt,
  });

  factory BacklinkItem.fromJson(Map<String, dynamic> json) {
    return BacklinkItem(
      id: json['id'] as String,
      title: json['title'] as String,
      category: json['category'] as String?,
      relationType: json['relation_type'] as String?,
      createdAt: json['created_at'] as String?,
    );
  }
}

// ============================================================
// EntryLinkItem - 条目关联链接数据模型
// ============================================================
class EntryLinkItem {
  final String linkId;
  final String sourceId;
  final String targetId;
  final String relationType;
  final Entry? targetEntry;
  final Entry? sourceEntry;

  const EntryLinkItem({
    required this.linkId,
    required this.sourceId,
    required this.targetId,
    required this.relationType,
    this.targetEntry,
    this.sourceEntry,
  });

  factory EntryLinkItem.fromJson(Map<String, dynamic> json) {
    return EntryLinkItem(
      linkId: json['link_id'] as String? ?? json['id'] as String,
      sourceId: json['source_id'] as String,
      targetId: json['target_id'] as String,
      relationType: json['relation_type'] as String,
      targetEntry: json['target_entry'] != null
          ? Entry.fromJson(json['target_entry'] as Map<String, dynamic>)
          : null,
      sourceEntry: json['source_entry'] != null
          ? Entry.fromJson(json['source_entry'] as Map<String, dynamic>)
          : null,
    );
  }
}

// ============================================================
// KnowledgeContextData - 知识上下文数据模型
// ============================================================
class KnowledgeContextData {
  final List<Map<String, dynamic>> nodes;
  final List<Map<String, dynamic>> edges;
  final List<String> centerConcepts;

  const KnowledgeContextData({
    this.nodes = const [],
    this.edges = const [],
    this.centerConcepts = const [],
  });

  factory KnowledgeContextData.fromJson(Map<String, dynamic> json) {
    return KnowledgeContextData(
      nodes: (json['nodes'] as List<dynamic>?)
              ?.map((e) => e as Map<String, dynamic>)
              .toList() ??
          const [],
      edges: (json['edges'] as List<dynamic>?)
              ?.map((e) => e as Map<String, dynamic>)
              .toList() ??
          const [],
      centerConcepts: (json['center_concepts'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
    );
  }
}

// ============================================================
// EntryDetailState - 条目详情状态（F173 扩展）
// ============================================================
class EntryDetailState {
  final Entry? entry;
  final bool isLoading;
  final String? error;
  final bool notFound;

  // 编辑相关
  final bool isEditing;
  final bool isSaving;

  // AI 摘要
  final bool isGeneratingSummary;
  final String? summaryText;
  final bool summaryCached;

  // 反向引用
  final List<BacklinkItem> backlinks;

  // 关联链接
  final List<EntryLinkItem> entryLinks;

  // 知识上下文
  final KnowledgeContextData? knowledgeContext;

  // 搜索
  final List<Entry> searchResults;
  final bool isSearching;

  const EntryDetailState({
    this.entry,
    this.isLoading = false,
    this.error,
    this.notFound = false,
    this.isEditing = false,
    this.isSaving = false,
    this.isGeneratingSummary = false,
    this.summaryText,
    this.summaryCached = false,
    this.backlinks = const [],
    this.entryLinks = const [],
    this.knowledgeContext,
    this.searchResults = const [],
    this.isSearching = false,
  });

  EntryDetailState copyWith({
    Entry? entry,
    bool? isLoading,
    String? error,
    bool? notFound,
    bool? isEditing,
    bool? isSaving,
    bool? isGeneratingSummary,
    String? summaryText,
    bool? summaryCached,
    List<BacklinkItem>? backlinks,
    List<EntryLinkItem>? entryLinks,
    KnowledgeContextData? knowledgeContext,
    List<Entry>? searchResults,
    bool? isSearching,
    bool clearError = false,
    bool clearSummaryText = false,
    bool clearKnowledgeContext = false,
  }) {
    return EntryDetailState(
      entry: entry ?? this.entry,
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      notFound: notFound ?? this.notFound,
      isEditing: isEditing ?? this.isEditing,
      isSaving: isSaving ?? this.isSaving,
      isGeneratingSummary:
          isGeneratingSummary ?? this.isGeneratingSummary,
      summaryText:
          clearSummaryText ? null : (summaryText ?? this.summaryText),
      summaryCached: summaryCached ?? this.summaryCached,
      backlinks: backlinks ?? this.backlinks,
      entryLinks: entryLinks ?? this.entryLinks,
      knowledgeContext: clearKnowledgeContext
          ? null
          : (knowledgeContext ?? this.knowledgeContext),
      searchResults: searchResults ?? this.searchResults,
      isSearching: isSearching ?? this.isSearching,
    );
  }
}

// ============================================================
// EntryDetailNotifier - 条目详情 Notifier（F173 family 模式）
// ============================================================
class EntryDetailNotifier extends FamilyNotifier<EntryDetailState, String> {
  late String _entryId;

  @override
  EntryDetailState build(String arg) {
    _entryId = arg;
    return const EntryDetailState();
  }

  ApiClient get _apiClient => ref.read(apiClientProvider);

  /// 获取单个条目
  Future<void> fetchEntry() async {
    state = state.copyWith(
      isLoading: true,
      clearError: true,
      notFound: false,
    );

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        '/entries/$_entryId',
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

  /// 切换编辑状态
  void toggleEdit() {
    state = state.copyWith(isEditing: !state.isEditing);
  }

  /// 更新条目（PUT 返回 SuccessResponse，需额外 GET 刷新）
  Future<void> updateEntry(Map<String, dynamic> data) async {
    state = state.copyWith(isSaving: true, clearError: true);

    try {
      // PUT 返回 SuccessResponse，不包含完整 entry 数据
      await _apiClient.updateEntry<Map<String, dynamic>>(
        id: _entryId,
        data: data,
      );

      // 额外 GET 刷新 entry 数据
      final response = await _apiClient.get<Map<String, dynamic>>(
        '/entries/$_entryId',
      );
      final refreshedEntry = Entry.fromJson(response.data!);

      state = state.copyWith(
        entry: refreshedEntry,
        isSaving: false,
        isEditing: false,
      );

      // 通知 EntryListProvider 刷新列表
      ref.invalidate(entryListProvider);
    } catch (e) {
      state = state.copyWith(
        isSaving: false,
        error: ApiClient.errorMessage(e),
      );
    }
  }

  /// 生成 AI 摘要
  Future<void> generateSummary() async {
    state = state.copyWith(isGeneratingSummary: true, clearError: true);

    try {
      final response =
          await _apiClient.generateAISummary<Map<String, dynamic>>(
        id: _entryId,
      );
      final data = response.data;
      final summary = data?['summary'] as String?;
      final cached = data?['cached'] as bool? ?? false;

      if (summary != null) {
        state = state.copyWith(
          isGeneratingSummary: false,
          summaryText: summary,
          summaryCached: cached,
        );
      } else {
        state = state.copyWith(
          isGeneratingSummary: false,
          error: 'AI 摘要生成返回空结果',
        );
      }
    } catch (e) {
      state = state.copyWith(
        isGeneratingSummary: false,
        error: ApiClient.errorMessage(e),
      );
    }
  }

  /// 加载反向引用
  Future<void> loadBacklinks() async {
    try {
      final response =
          await _apiClient.fetchBacklinks<Map<String, dynamic>>(
        id: _entryId,
      );
      final data = response.data;
      final items = (data?['backlinks'] as List<dynamic>?)
              ?.map(
                  (e) => BacklinkItem.fromJson(e as Map<String, dynamic>),)
              .toList() ??
          <BacklinkItem>[];

      state = state.copyWith(backlinks: items);
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
    }
  }

  /// 加载关联链接
  Future<void> loadEntryLinks({String direction = 'both'}) async {
    try {
      final response =
          await _apiClient.fetchEntryLinks<Map<String, dynamic>>(
        id: _entryId,
        direction: direction,
      );
      final data = response.data;
      final items = (data?['links'] as List<dynamic>?)
              ?.map(
                  (e) => EntryLinkItem.fromJson(e as Map<String, dynamic>),)
              .toList() ??
          <EntryLinkItem>[];

      state = state.copyWith(entryLinks: items);
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
    }
  }

  /// 创建关联链接
  Future<bool> createLink({
    required String targetId,
    required String relationType,
  }) async {
    state = state.copyWith(clearError: true);

    try {
      await _apiClient.createEntryLink<Map<String, dynamic>>(
        id: _entryId,
        targetId: targetId,
        relationType: relationType,
      );

      // 刷新关联链接列表
      await loadEntryLinks();
      return true;
    } on DioException catch (e) {
      final statusCode = e.response?.statusCode;
      String? errorMsg;
      if (statusCode == 400) {
        errorMsg = '不能关联自身';
      } else if (statusCode == 409) {
        errorMsg = '关联已存在';
      } else {
        errorMsg = ApiClient.errorMessage(e);
      }
      state = state.copyWith(error: errorMsg);
      return false;
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
      return false;
    }
  }

  /// 删除关联链接
  Future<void> deleteLink({required String linkId}) async {
    try {
      await _apiClient.deleteEntryLink<Map<String, dynamic>>(
        id: _entryId,
        linkId: linkId,
      );

      // 刷新关联链接列表
      await loadEntryLinks();
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
    }
  }

  /// 搜索条目用于关联
  Future<void> searchEntriesForLink({required String query}) async {
    state = state.copyWith(isSearching: true, clearError: true);

    try {
      final response =
          await _apiClient.searchEntries<Map<String, dynamic>>(
        query: query,
      );
      final results = parseEntries(response.data);
      state = state.copyWith(searchResults: results, isSearching: false);
    } catch (e) {
      state = state.copyWith(
        isSearching: false,
        error: ApiClient.errorMessage(e),
      );
    }
  }
}

/// 条目详情 Family Provider（按 entryId 隔离状态）
final entryDetailProvider =
    NotifierProvider.family<EntryDetailNotifier, EntryDetailState, String>(
  EntryDetailNotifier.new,
);
