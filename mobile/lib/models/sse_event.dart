import 'dart:convert';

import 'package:collection/collection.dart';

// ============================================================
// SseEvent - SSE 事件模型
//
// 后端事件类型：
// - intent  : 意图检测结果
// - content : 流式内容（create 意图）
// - created : 创建成功
// - updated : 更新成功
// - deleted : 删除成功
// - confirm : 需要用户确认（多选场景）
// - results : 搜索结果（read 意图）
// - done    : 完成
// - error   : 错误
// ============================================================

class SseEvent {
  final String type;
  final Map<String, dynamic> data;

  const SseEvent({
    required this.type,
    required this.data,
  });

  /// 从 SSE 原始文本解析事件
  /// 格式: event: xxx\ndata: {json}\n\n
  factory SseEvent.fromRaw(String raw) {
    String eventType = 'message';
    Map<String, dynamic> eventData = {};

    for (final line in raw.split('\n')) {
      final trimmed = line.trim();
      if (trimmed.isEmpty) continue;

      if (trimmed.startsWith('event:')) {
        eventType = trimmed.substring(6).trim();
      } else if (trimmed.startsWith('data:')) {
        final dataStr = trimmed.substring(5).trim();
        if (dataStr.isNotEmpty) {
          try {
            eventData = json.decode(dataStr) as Map<String, dynamic>;
          } catch (_) {
            eventData = {'raw': dataStr};
          }
        }
      }
    }

    return SseEvent(type: eventType, data: eventData);
  }

  /// 是否为终止事件
  bool get isDone => type == 'done';

  /// 是否为错误事件
  bool get isError => type == 'error';

  /// 获取错误消息
  String? get errorMessage {
    if (!isError) return null;
    final msg = data['message'];
    return msg?.toString();
  }

  /// 获取 content 内容
  String? get contentText {
    if (type != 'content') return null;
    final content = data['content'];
    return content?.toString();
  }

  @override
  String toString() => 'SseEvent(type: $type, data: $data)';

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SseEvent &&
          type == other.type &&
          const DeepCollectionEquality().equals(data, other.data);

  @override
  int get hashCode => Object.hash(type, const DeepCollectionEquality().hash(data));
}

/// SSE 事件类型常量
class SseEventType {
  SseEventType._();

  static const String intent = 'intent';
  static const String content = 'content';
  static const String created = 'created';
  static const String updated = 'updated';
  static const String deleted = 'deleted';
  static const String confirm = 'confirm';
  static const String results = 'results';
  static const String done = 'done';
  static const String error = 'error';
}
