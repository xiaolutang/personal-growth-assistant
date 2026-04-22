// ============================================================
// Entry - 条目数据模型
// ============================================================
class Entry {
  final String id;
  final String title;
  final String? content;
  final String category;
  final String? status;
  final String? priority;
  final List<String> tags;
  final String? createdAt;
  final String? updatedAt;
  final String? plannedDate;
  final String? completedAt;
  final String? parentId;
  final String? filePath;

  const Entry({
    required this.id,
    required this.title,
    this.content,
    required this.category,
    this.status,
    this.priority,
    this.tags = const [],
    this.createdAt,
    this.updatedAt,
    this.plannedDate,
    this.completedAt,
    this.parentId,
    this.filePath,
  });

  factory Entry.fromJson(Map<String, dynamic> json) {
    return Entry(
      id: json['id'] as String,
      title: json['title'] as String,
      content: json['content'] as String?,
      category: json['category'] as String,
      status: json['status'] as String?,
      priority: json['priority'] as String?,
      tags: (json['tags'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
      plannedDate: json['planned_date'] as String?,
      completedAt: json['completed_at'] as String?,
      parentId: json['parent_id'] as String?,
      filePath: json['file_path'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'content': content,
      'category': category,
      'status': status,
      'priority': priority,
      'tags': tags,
      'created_at': createdAt,
      'updated_at': updatedAt,
      'planned_date': plannedDate,
      'completed_at': completedAt,
      'parent_id': parentId,
      'file_path': filePath,
    };
  }

  /// 创建任务的请求体
  Map<String, dynamic> toCreateJson() {
    return {
      'category': category,
      'title': title,
      'content': content ?? '',
      'status': status ?? 'todo',
    };
  }
}
