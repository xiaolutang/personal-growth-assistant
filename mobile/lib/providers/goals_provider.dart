import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/auth_provider.dart';
import '../services/api_client.dart';

// ============================================================
// Goal - 目标数据模型
// ============================================================
class Goal {
  final String id;
  final String title;
  final String? description;
  final String? status;
  final String? startDate;
  final String? endDate;
  final double? progress;
  final String? createdAt;
  final String? updatedAt;

  const Goal({
    required this.id,
    required this.title,
    this.description,
    this.status,
    this.startDate,
    this.endDate,
    this.progress,
    this.createdAt,
    this.updatedAt,
  });

  factory Goal.fromJson(Map<String, dynamic> json) {
    return Goal(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String?,
      status: json['status'] as String?,
      startDate: json['start_date'] as String?,
      endDate: json['end_date'] as String?,
      progress: (json['progress'] as num?)?.toDouble(),
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );
  }
}

// ============================================================
// Milestone - 里程碑数据模型
// ============================================================
class Milestone {
  final String id;
  final String goalId;
  final String title;
  final String? description;
  final String? status;
  final String? dueDate;
  final String? completedAt;
  final String? createdAt;
  final String? updatedAt;

  const Milestone({
    required this.id,
    required this.goalId,
    required this.title,
    this.description,
    this.status,
    this.dueDate,
    this.completedAt,
    this.createdAt,
    this.updatedAt,
  });

  factory Milestone.fromJson(Map<String, dynamic> json) {
    return Milestone(
      id: json['id'] as String,
      goalId: json['goal_id'] as String? ?? '',
      title: json['title'] as String,
      description: json['description'] as String?,
      status: json['status'] as String?,
      dueDate: json['due_date'] as String?,
      completedAt: json['completed_at'] as String?,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );
  }
}

// ============================================================
// GoalsState - 目标页状态
// ============================================================
class GoalsState {
  final List<Goal> goals;
  final Goal? selectedGoal;
  final List<Milestone> milestones;
  final bool isLoading;
  final String? error;

  const GoalsState({
    this.goals = const [],
    this.selectedGoal,
    this.milestones = const [],
    this.isLoading = false,
    this.error,
  });

  GoalsState copyWith({
    List<Goal>? goals,
    Object? selectedGoal = _sentinel,
    List<Milestone>? milestones,
    bool? isLoading,
    Object? error = _sentinel,
  }) {
    return GoalsState(
      goals: goals ?? this.goals,
      selectedGoal: identical(selectedGoal, _sentinel)
          ? this.selectedGoal
          : selectedGoal as Goal?,
      milestones: milestones ?? this.milestones,
      isLoading: isLoading ?? this.isLoading,
      error: identical(error, _sentinel) ? this.error : error as String?,
    );
  }

  static const _sentinel = Object();
}

// ============================================================
// GoalsNotifier - 目标页 Notifier
// ============================================================
class GoalsNotifier extends Notifier<GoalsState> {
  @override
  GoalsState build() {
    return const GoalsState();
  }

  /// 收起选中的目标（清空 selectedGoal 和 milestones）
  void deselectGoal() {
    state = state.copyWith(
      selectedGoal: null,
      milestones: const [],
    );
  }

  /// 获取目标列表
  Future<void> fetchGoals({String? status}) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.fetchGoals<Map<String, dynamic>>(
        status: status,
      );

      final data = response.data;
      final items = (data?['items'] as List<dynamic>?)
              ?.map((e) => Goal.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [];

      state = state.copyWith(goals: items, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: ApiClient.errorMessage(e),
      );
    }
  }

  /// 获取目标详情
  Future<void> fetchGoalDetail(String id) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.fetchGoal<Map<String, dynamic>>(id: id);

      final goal = Goal.fromJson(response.data!);
      state = state.copyWith(selectedGoal: goal, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: ApiClient.errorMessage(e),
      );
    }
  }

  /// 获取里程碑列表
  Future<void> fetchMilestones(String goalId) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.fetchMilestones<Map<String, dynamic>>(
        goalId: goalId,
      );

      final data = response.data;
      final items = (data?['items'] as List<dynamic>?)
              ?.map((e) => Milestone.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [];

      state = state.copyWith(milestones: items);
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
    }
  }

  /// 创建里程碑
  Future<bool> createMilestone(
    String goalId,
    Map<String, dynamic> data,
  ) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.createMilestone<Map<String, dynamic>>(
        goalId: goalId,
        data: data,
      );

      // 刷新里程碑列表
      await fetchMilestones(goalId);
      return true;
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
      return false;
    }
  }

  /// 更新里程碑
  Future<bool> updateMilestone(
    String goalId,
    String milestoneId,
    Map<String, dynamic> data,
  ) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.updateMilestone<Map<String, dynamic>>(
        goalId: goalId,
        milestoneId: milestoneId,
        data: data,
      );

      // 刷新里程碑列表
      await fetchMilestones(goalId);
      return true;
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
      return false;
    }
  }

  /// 删除里程碑
  Future<bool> deleteMilestone(String goalId, String milestoneId) async {
    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.deleteMilestone<Map<String, dynamic>>(
        goalId: goalId,
        milestoneId: milestoneId,
      );

      // 从列表中移除已删除的里程碑
      final updated =
          state.milestones.where((m) => m.id != milestoneId).toList();
      state = state.copyWith(milestones: updated);
      return true;
    } catch (e) {
      state = state.copyWith(error: ApiClient.errorMessage(e));
      return false;
    }
  }
}

/// 目标页 Provider
final goalsProvider =
    NotifierProvider<GoalsNotifier, GoalsState>(() {
  return GoalsNotifier();
});
