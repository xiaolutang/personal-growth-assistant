import 'entry.dart';

// ============================================================
// ChatMessage - 对话消息模型
//
// 支持三种角色：
// - user: 用户发送的消息
// - assistant: AI 回复消息
// - system: 系统消息（如创建确认卡片）
// ============================================================

/// 消息角色
enum ChatMessageRole {
  user,
  assistant,
  system,
}

class ChatMessage {
  final String id;
  final ChatMessageRole role;
  final String text;
  final DateTime createdAt;

  /// F105: 创建确认卡片的条目数据（仅 system 角色使用）
  final Entry? createdEntry;

  const ChatMessage({
    required this.id,
    required this.role,
    required this.text,
    required this.createdAt,
    this.createdEntry,
  });

  /// 是否为创建确认卡片消息
  bool get isCreatedCard => role == ChatMessageRole.system && createdEntry != null;

  /// 从 JSON 创建（用于测试和序列化）
  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] as String,
      role: _parseRole(json['role'] as String),
      text: json['text'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      createdEntry: json['created_entry'] != null
          ? Entry.fromJson(json['created_entry'] as Map<String, dynamic>)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'role': role.name,
      'text': text,
      'created_at': createdAt.toIso8601String(),
      if (createdEntry != null) 'created_entry': createdEntry!.toJson(),
    };
  }

  ChatMessage copyWith({
    String? id,
    ChatMessageRole? role,
    String? text,
    DateTime? createdAt,
    Entry? createdEntry,
  }) {
    return ChatMessage(
      id: id ?? this.id,
      role: role ?? this.role,
      text: text ?? this.text,
      createdAt: createdAt ?? this.createdAt,
      createdEntry: createdEntry ?? this.createdEntry,
    );
  }

  static ChatMessageRole _parseRole(String role) {
    switch (role) {
      case 'user':
        return ChatMessageRole.user;
      case 'assistant':
        return ChatMessageRole.assistant;
      case 'system':
        return ChatMessageRole.system;
      default:
        return ChatMessageRole.system;
    }
  }
}
