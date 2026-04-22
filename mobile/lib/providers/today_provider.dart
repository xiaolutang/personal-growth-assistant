import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/constants.dart';
import '../models/entry.dart';
import '../providers/auth_provider.dart';
import '../services/api_client.dart';

// ============================================================
// TodayState - 今日页状态
// ============================================================
class TodayState {
  final List<Entry> todayTasks;
  final List<Entry> recentEntries;
  final bool isLoading;
  final String? error;

  const TodayState({
    this.todayTasks = const [],
    this.recentEntries = const [],
    this.isLoading = false,
    this.error,
  });

  /// 今日完成率 (0.0 ~ 1.0)
  double get completionRate {
    if (todayTasks.isEmpty) return 0.0;
    final done = todayTasks.where(
      (e) => e.status == AppConstants.statusDone,
    ).length;
    return done / todayTasks.length;
  }

  TodayState copyWith({
    List<Entry>? todayTasks,
    List<Entry>? recentEntries,
    bool? isLoading,
    String? error,
  }) {
    return TodayState(
      todayTasks: todayTasks ?? this.todayTasks,
      recentEntries: recentEntries ?? this.recentEntries,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

// ============================================================
// TodayNotifier - 今日页数据 Provider
// ============================================================
class TodayNotifier extends Notifier<TodayState> {
  @override
  TodayState build() {
    return const TodayState();
  }

  /// 加载所有今日页数据
  Future<void> loadData() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final apiClient = ref.read(apiClientProvider);
      final today = _todayDateString();

      final results = await Future.wait([
        // 今日任务：获取所有任务，再按 planned_date 过滤
        apiClient.get<Map<String, dynamic>>(
          '/entries',
          queryParameters: {'type': AppConstants.categoryTask},
        ),
        // 最近 10 条动态（跨类型）
        apiClient.get<Map<String, dynamic>>(
          '/entries',
          queryParameters: {'page_size': 10},
        ),
      ]);

      // 解析任务
      final tasksResponse = results[0].data;
      final allTasks = _parseEntries(tasksResponse);
      final todayTasks = allTasks.where((e) {
        return e.plannedDate == today || e.createdAt?.startsWith(today) == true;
      }).toList();

      // 解析最近动态
      final recentResponse = results[1].data;
      final recentEntries = _parseEntries(recentResponse);

      state = state.copyWith(
        todayTasks: todayTasks,
        recentEntries: recentEntries,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: ApiClient.errorMessage(e),
      );
    }
  }

  /// 快速创建任务
  Future<bool> createTask(String title) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.post<Map<String, dynamic>>(
        '/entries',
        data: {
          'category': AppConstants.categoryTask,
          'title': title,
          'content': '',
          'status': AppConstants.statusTodo,
        },
      );

      // 创建成功后刷新数据
      await loadData();
      return true;
    } catch (e) {
      state = state.copyWith(
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

  String _todayDateString() {
    final now = DateTime.now();
    return '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
  }
}

/// 今日页数据 Provider
final todayProvider = NotifierProvider<TodayNotifier, TodayState>(() {
  return TodayNotifier();
});
