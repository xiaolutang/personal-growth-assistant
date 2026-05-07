// ============================================================
// MorningDigest - 晨报数据模型
// 对应后端 GET /review/morning-digest 的响应
// ============================================================

/// 每日聚焦建议
class DailyFocus {
  final String title;
  final String description;
  final String? targetEntryId;

  const DailyFocus({
    required this.title,
    required this.description,
    this.targetEntryId,
  });

  factory DailyFocus.fromJson(Map<String, dynamic> json) {
    return DailyFocus(
      title: json['title'] as String,
      description: json['description'] as String,
      targetEntryId: json['target_entry_id'] as String?,
    );
  }
}

/// 晨报待办项
class MorningDigestTodo {
  final String id;
  final String title;
  final String priority;
  final String? plannedDate;

  const MorningDigestTodo({
    required this.id,
    required this.title,
    this.priority = 'medium',
    this.plannedDate,
  });

  factory MorningDigestTodo.fromJson(Map<String, dynamic> json) {
    return MorningDigestTodo(
      id: json['id'] as String,
      title: json['title'] as String,
      priority: json['priority'] as String? ?? 'medium',
      plannedDate: json['planned_date'] as String?,
    );
  }
}

/// 晨报拖延项
class MorningDigestOverdue {
  final String id;
  final String title;
  final String priority;
  final String? plannedDate;

  const MorningDigestOverdue({
    required this.id,
    required this.title,
    this.priority = 'medium',
    this.plannedDate,
  });

  factory MorningDigestOverdue.fromJson(Map<String, dynamic> json) {
    return MorningDigestOverdue(
      id: json['id'] as String,
      title: json['title'] as String,
      priority: json['priority'] as String? ?? 'medium',
      plannedDate: json['planned_date'] as String?,
    );
  }
}

/// 晨报未跟进灵感
class MorningDigestStaleInbox {
  final String id;
  final String title;
  final String createdAt;

  const MorningDigestStaleInbox({
    required this.id,
    required this.title,
    required this.createdAt,
  });

  factory MorningDigestStaleInbox.fromJson(Map<String, dynamic> json) {
    return MorningDigestStaleInbox(
      id: json['id'] as String,
      title: json['title'] as String,
      createdAt: json['created_at'] as String,
    );
  }
}

/// 晨报本周学习摘要
class MorningDigestWeeklySummary {
  final List<String> newConcepts;
  final int entriesCount;

  const MorningDigestWeeklySummary({
    this.newConcepts = const [],
    this.entriesCount = 0,
  });

  factory MorningDigestWeeklySummary.fromJson(Map<String, dynamic> json) {
    return MorningDigestWeeklySummary(
      newConcepts: (json['new_concepts'] as List<dynamic>?)
              ?.map((e) => e as String,)
              .toList() ??
          const [],
      entriesCount: json['entries_count'] as int? ?? 0,
    );
  }
}

/// AI 晨报响应
class MorningDigest {
  final String date;
  final String aiSuggestion;
  final List<MorningDigestTodo> todos;
  final List<MorningDigestOverdue> overdue;
  final List<MorningDigestStaleInbox> staleInbox;
  final MorningDigestWeeklySummary weeklySummary;
  final int learningStreak;
  final DailyFocus? dailyFocus;
  final List<String> patternInsights;
  final String? cachedAt;

  const MorningDigest({
    required this.date,
    required this.aiSuggestion,
    this.todos = const [],
    this.overdue = const [],
    this.staleInbox = const [],
    this.weeklySummary = const MorningDigestWeeklySummary(),
    this.learningStreak = 0,
    this.dailyFocus,
    this.patternInsights = const [],
    this.cachedAt,
  });

  factory MorningDigest.fromJson(Map<String, dynamic> json) {
    return MorningDigest(
      date: json['date'] as String,
      aiSuggestion: json['ai_suggestion'] as String? ?? '',
      todos: (json['todos'] as List<dynamic>?)
              ?.map((e) => MorningDigestTodo.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      overdue: (json['overdue'] as List<dynamic>?)
              ?.map((e) => MorningDigestOverdue.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      staleInbox: (json['stale_inbox'] as List<dynamic>?)
              ?.map((e) => MorningDigestStaleInbox.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      weeklySummary: json['weekly_summary'] != null
          ? MorningDigestWeeklySummary.fromJson(
              json['weekly_summary'] as Map<String, dynamic>,)
          : const MorningDigestWeeklySummary(),
      learningStreak: json['learning_streak'] as int? ?? 0,
      dailyFocus: json['daily_focus'] != null
          ? DailyFocus.fromJson(json['daily_focus'] as Map<String, dynamic>)
          : null,
      patternInsights: (json['pattern_insights'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      cachedAt: json['cached_at'] as String?,
    );
  }
}
