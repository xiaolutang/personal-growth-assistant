import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/constants.dart';
import '../models/entry.dart';
import '../models/morning_digest.dart';
import '../providers/auth_provider.dart';
import '../services/api_client.dart';

// ============================================================
// MorningDigestLoadState - 晨报加载状态
// ============================================================
enum MorningDigestStatus { initial, loading, loaded, error }

class MorningDigestState {
  final MorningDigest? data;
  final MorningDigestStatus status;
  final String? error;

  const MorningDigestState({
    this.data,
    this.status = MorningDigestStatus.initial,
    this.error,
  });

  MorningDigestState copyWith({
    MorningDigest? data,
    MorningDigestStatus? status,
    Object? error = _sentinel,
  }) {
    return MorningDigestState(
      data: data ?? this.data,
      status: status ?? this.status,
      error: identical(error, _sentinel) ? this.error : error as String?,
    );
  }

  static const _sentinel = Object();
}

// ============================================================
// TodayState - 今日页状态
// ============================================================
class TodayState {
  final List<Entry> todayTasks;
  final List<Entry> recentEntries;
  final bool isLoading;
  final String? error;
  final MorningDigestState morningDigest;

  const TodayState({
    this.todayTasks = const [],
    this.recentEntries = const [],
    this.isLoading = false,
    this.error,
    this.morningDigest = const MorningDigestState(),
  });

  /// 已完成任务数
  int get completedTaskCount => todayTasks.where(
        (e) => e.status == AppConstants.statusComplete,
      ).length;

  /// 今日完成率 (0.0 ~ 1.0)
  double get completionRate {
    if (todayTasks.isEmpty) return 0.0;
    return completedTaskCount / todayTasks.length;
  }

  TodayState copyWith({
    List<Entry>? todayTasks,
    List<Entry>? recentEntries,
    bool? isLoading,
    Object? error = _sentinel,
    MorningDigestState? morningDigest,
  }) {
    return TodayState(
      todayTasks: todayTasks ?? this.todayTasks,
      recentEntries: recentEntries ?? this.recentEntries,
      isLoading: isLoading ?? this.isLoading,
      error: identical(error, _sentinel) ? this.error : error as String?,
      morningDigest: morningDigest ?? this.morningDigest,
    );
  }

  static const _sentinel = Object();
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

      // 并行加载：任务列表 + 最近动态 + 晨报
      final results = await Future.wait([
        // 今日任务：获取所有任务，再按 planned_date 过滤
        apiClient.get<Map<String, dynamic>>(
          '/entries',
          queryParameters: {'type': AppConstants.categoryTask},
        ),
        // 最近 10 条动态（跨类型）
        apiClient.get<Map<String, dynamic>>(
          '/entries',
          queryParameters: {'limit': 10},
        ),
      ]);

      // 解析任务
      final tasksResponse = results[0].data;
      final allTasks = parseEntries(tasksResponse);
      final todayTasks = allTasks.where((e) {
        return e.plannedDate == today || e.createdAt?.startsWith(today) == true;
      }).toList();

      // 解析最近动态
      final recentResponse = results[1].data;
      final recentEntries = parseEntries(recentResponse);

      state = state.copyWith(
        todayTasks: todayTasks,
        recentEntries: recentEntries,
        isLoading: false,
      );

      // 晨报独立加载（失败不阻塞主页面）
      loadMorningDigest();
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: ApiClient.errorMessage(e),
      );
    }
  }

  /// 加载晨报数据（独立加载，失败不阻塞主页面）
  Future<void> loadMorningDigest() async {
    state = state.copyWith(
      morningDigest: state.morningDigest.copyWith(
        status: MorningDigestStatus.loading,
      ),
    );

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.get<Map<String, dynamic>>(
        '/review/morning-digest',
      );

      final data = response.data;
      if (data != null) {
        final digest = MorningDigest.fromJson(data);
        state = state.copyWith(
          morningDigest: MorningDigestState(
            data: digest,
            status: MorningDigestStatus.loaded,
          ),
        );
      } else {
        state = state.copyWith(
          morningDigest: const MorningDigestState(
            status: MorningDigestStatus.loaded,
          ),
        );
      }
    } catch (e) {
      // 晨报加载失败不阻塞页面，记录错误即可
      state = state.copyWith(
        morningDigest: MorningDigestState(
          status: MorningDigestStatus.error,
          error: ApiClient.errorMessage(e),
        ),
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
          'status': AppConstants.statusWaitStart,
        },
      );

      return true;
    } catch (e) {
      state = state.copyWith(
        error: ApiClient.errorMessage(e),
      );
      return false;
    }
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
