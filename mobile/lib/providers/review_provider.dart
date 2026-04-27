import 'package:dio/dio.dart';
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

  /// 批量加载所有数据（统一管理 isLoading）
  Future<void> loadAll([String? period]) async {
    final p = period ?? state.selectedPeriod;
    state = state.copyWith(
      isLoading: true,
      error: null,
      selectedPeriod: p,
    );

    try {
      final apiClient = ref.read(apiClientProvider);

      final results = await Future.wait([
        apiClient.fetchReviewSummary<Map<String, dynamic>>(period: p),
        _fetchTrends(apiClient, p),
        apiClient.fetchInsights<Map<String, dynamic>>(period: p),
      ]);

      state = state.copyWith(
        summary: results[0].data,
        trends: results[1].data,
        insights: results[2].data,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: ApiClient.errorMessage(e),
      );
    }
  }

  Future<Response<Map<String, dynamic>>> _fetchTrends(
    ApiClient apiClient,
    String period,
  ) {
    if (period == 'monthly') {
      return apiClient.fetchTrends<Map<String, dynamic>>(
        period: 'weekly',
        weeks: 4,
      );
    }
    return apiClient.fetchTrends<Map<String, dynamic>>(
      period: 'daily',
      days: 7,
    );
  }

}

/// 回顾页 Provider
final reviewProvider =
    NotifierProvider<ReviewNotifier, ReviewState>(() {
  return ReviewNotifier();
});
