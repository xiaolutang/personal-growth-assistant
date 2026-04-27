import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/auth_provider.dart';
import '../services/api_client.dart';

// ============================================================
// ReviewState - 回顾页状态
// ============================================================
class ReviewState {
  final Map<String, dynamic>? summary;
  final Map<String, dynamic>? trends;
  final Map<String, dynamic>? insights;
  final bool isLoading;
  final String? error;
  final String selectedPeriod;

  const ReviewState({
    this.summary,
    this.trends,
    this.insights,
    this.isLoading = false,
    this.error,
    this.selectedPeriod = 'weekly',
  });

  ReviewState copyWith({
    Map<String, dynamic>? summary,
    Object? summaryClear = _sentinel,
    Map<String, dynamic>? trends,
    Object? trendsClear = _sentinel,
    Map<String, dynamic>? insights,
    Object? insightsClear = _sentinel,
    bool? isLoading,
    Object? error = _sentinel,
    String? selectedPeriod,
  }) {
    return ReviewState(
      summary: identical(summaryClear, _sentinel)
          ? (summary ?? this.summary)
          : null,
      trends: identical(trendsClear, _sentinel)
          ? (trends ?? this.trends)
          : null,
      insights: identical(insightsClear, _sentinel)
          ? (insights ?? this.insights)
          : null,
      isLoading: isLoading ?? this.isLoading,
      error: identical(error, _sentinel) ? this.error : error as String?,
      selectedPeriod: selectedPeriod ?? this.selectedPeriod,
    );
  }

  static const _sentinel = Object();
}

// ============================================================
// ReviewNotifier - 回顾页 Notifier
// ============================================================
class ReviewNotifier extends Notifier<ReviewState> {
  @override
  ReviewState build() {
    return const ReviewState();
  }

  /// 加载回顾报告
  Future<void> loadSummary([String? period]) async {
    final p = period ?? state.selectedPeriod;
    state = state.copyWith(isLoading: true, error: null, selectedPeriod: p);

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.fetchReviewSummary<Map<String, dynamic>>(
        period: p,
      );

      state = state.copyWith(
        summary: response.data,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: ApiClient.errorMessage(e),
      );
    }
  }

  /// 加载趋势数据
  Future<void> loadTrends([String? period]) async {
    final p = period ?? state.selectedPeriod;

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.fetchTrends<Map<String, dynamic>>(
        period: p == 'daily' ? 'daily' : 'weekly',
      );

      state = state.copyWith(trends: response.data);
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
    }
  }

  /// 加载 AI 深度洞察
  Future<void> loadInsights() async {
    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.fetchInsights<Map<String, dynamic>>(
        period: state.selectedPeriod,
      );

      state = state.copyWith(insights: response.data);
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
    }
  }

  /// 设置统计周期
  void setPeriod(String period) {
    state = state.copyWith(selectedPeriod: period);
  }
}

/// 回顾页 Provider
final reviewProvider =
    NotifierProvider<ReviewNotifier, ReviewState>(() {
  return ReviewNotifier();
});
