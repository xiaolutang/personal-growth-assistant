import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../config/api_config.dart';
import '../models/chat_message.dart';
import '../models/entry.dart';
import '../models/sse_event.dart';
import '../providers/auth_provider.dart';
import '../services/sse_service.dart';

// ============================================================
// ChatState - 对话状态
// ============================================================
class ChatState {
  final List<ChatMessage> messages;
  final bool isLoading;
  final String? error;

  const ChatState({
    this.messages = const [],
    this.isLoading = false,
    this.error,
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? isLoading,
    Object? error = _sentinel,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      isLoading: isLoading ?? this.isLoading,
      error: identical(error, _sentinel) ? this.error : error as String?,
    );
  }

  static const _sentinel = Object();
}

// ============================================================
// ChatNotifier - 对话 Provider
// ============================================================
class ChatNotifier extends Notifier<ChatState> {
  StreamSubscription<SseEvent>? _currentSubscription;
  late SseService _sseService;
  Map<String, dynamic>? _lastPageContext;

  @override
  ChatState build() {
    // 缓存 SseService 引用（避免 dispose 时 read 已销毁的 container）
    _sseService = ref.read(sseServiceProvider);

    // 清理旧的 SSE 连接和订阅
    ref.onDispose(() {
      _sseService.cancel();
      _currentSubscription?.cancel();
      _currentSubscription = null;
    });
    return const ChatState();
  }

  /// 发送消息并处理 SSE 事件流
  ///
  /// [pageContext] 页面上下文，透传给后端 POST /chat 的 page_context 字段
  /// 例如 {'page_type': 'today'} 或 {'page_type': 'home'}
  Future<void> sendMessage(String text, {Map<String, dynamic>? pageContext}) async {
    _lastPageContext = pageContext;
    if (text.trim().isEmpty) return;

    final authState = ref.read(authProvider);
    final userId = authState.whenOrNull<String>(
      data: (s) => s is AuthAuthenticated ? s.user.id : null,
    );
    if (userId == null) return;

    // 1. 添加用户消息
    final userMessage = ChatMessage(
      id: const Uuid().v4(),
      role: ChatMessageRole.user,
      text: text.trim(),
      createdAt: DateTime.now(),
    );

    // 2. 创建 AI 消息占位
    final aiMessage = ChatMessage(
      id: const Uuid().v4(),
      role: ChatMessageRole.assistant,
      text: '',
      createdAt: DateTime.now(),
    );

    state = state.copyWith(
      messages: [...state.messages, userMessage, aiMessage],
      isLoading: true,
      error: null,
    );

    // 3. 获取或创建 session_id
    final sessionId = await _getOrCreateSessionId();

    // 4. 调用 SseService（使用单例）
    // 取消之前的 SSE 连接和订阅
    _currentSubscription?.cancel();
    _sseService.cancel();

    final stream = _sseService.connect(
      message: text.trim(),
      sessionId: sessionId,
      pageContext: pageContext,
    );

    // 5. 监听 SSE 事件流
    final messages = List<ChatMessage>.from(state.messages);
    final aiIndex = messages.length - 1;

    _currentSubscription = stream.listen(
      (event) {
        _handleEvent(event, messages, aiIndex);
      },
      onError: (error) {
        state = state.copyWith(
          isLoading: false,
          error: '连接异常: $error',
        );
      },
      onDone: () {
        state = state.copyWith(isLoading: false);
      },
      cancelOnError: false,
    );
  }

  /// 处理单个 SSE 事件
  void _handleEvent(
    SseEvent event,
    List<ChatMessage> messages,
    int aiIndex,
  ) {
    switch (event.type) {
      case SseEventType.content:
        // 流式追加 AI 回复文本
        final content = event.contentText ?? '';
        if (aiIndex < messages.length) {
          messages[aiIndex] = messages[aiIndex].copyWith(
            text: messages[aiIndex].text + content,
          );
          state = state.copyWith(messages: List.from(messages));
        }
        break;

      case SseEventType.created:
        // F105: 创建确认卡片
        // 后端可能发送两种格式：
        // 1. {ids: [...], count: N} — chat_service 批量创建
        // 2. 单个 entry 对象（含 id 字段） — 其他来源
        final entryData = event.data;
        if (entryData.containsKey('ids')) {
          // 批量创建：显示简洁确认消息
          final count = entryData['count'] as int? ?? 1;
          final cardMessage = ChatMessage(
            id: const Uuid().v4(),
            role: ChatMessageRole.system,
            text: '创建了 $count 条记录',
            createdAt: DateTime.now(),
          );
          messages.add(cardMessage);
          state = state.copyWith(messages: List.from(messages));
        } else if (entryData.containsKey('id')) {
          // 单个完整 entry 对象
          try {
            final entry = Entry.fromJson(entryData);
            final cardMessage = ChatMessage(
              id: const Uuid().v4(),
              role: ChatMessageRole.system,
              text: '',
              createdAt: DateTime.now(),
              createdEntry: entry,
            );
            messages.add(cardMessage);
            state = state.copyWith(messages: List.from(messages));
          } catch (_) {
            // JSON 解析失败，降级为文本消息
            messages.add(ChatMessage(
              id: const Uuid().v4(),
              role: ChatMessageRole.system,
              text: '创建成功',
              createdAt: DateTime.now(),
            ),);
            state = state.copyWith(messages: List.from(messages));
          }
        } else {
          // 未知格式，降级为文本消息
          messages.add(ChatMessage(
            id: const Uuid().v4(),
            role: ChatMessageRole.system,
            text: '创建成功',
            createdAt: DateTime.now(),
          ),);
          state = state.copyWith(messages: List.from(messages));
        }
        break;

      case SseEventType.error:
        final errorMsg = event.errorMessage ?? '未知错误';
        state = state.copyWith(
          isLoading: false,
          error: errorMsg,
        );
        break;

      case SseEventType.done:
        state = state.copyWith(isLoading: false);
        break;

      // intent, updated, deleted, confirm, results 等
      // 暂不处理，后续迭代
      default:
        break;
    }
  }

  /// 重试上一次发送
  void retry() {
    // 找到最后一条用户消息
    final lastUserMessage = state.messages.lastWhere(
      (m) => m.role == ChatMessageRole.user,
      orElse: () => ChatMessage(
        id: '',
        role: ChatMessageRole.user,
        text: '',
        createdAt: DateTime.now(),
      ),
    );
    if (lastUserMessage.text.isNotEmpty) {
      // 移除最后的错误 AI 回复（如果为空）
      final messages = List<ChatMessage>.from(state.messages);
      if (messages.isNotEmpty &&
          messages.last.role == ChatMessageRole.assistant &&
          messages.last.text.isEmpty) {
        messages.removeLast();
      }
      state = state.copyWith(messages: messages, error: null);
      sendMessage(lastUserMessage.text, pageContext: _lastPageContext);
    }
  }

  /// 获取或创建 session_id
  Future<String> _getOrCreateSessionId() async {
    final storage = ref.read(secureStorageProvider);
    var sessionId = await storage.read(key: ApiConfig.keySessionId);

    if (sessionId == null || sessionId.isEmpty) {
      sessionId = const Uuid().v4();
      await storage.write(key: ApiConfig.keySessionId, value: sessionId);
    }

    return sessionId;
  }

  /// 清空所有消息和错误状态（用于用户切换时重置对话）
  void clearMessages() {
    // 取消正在进行的 SSE 连接
    _currentSubscription?.cancel();
    _currentSubscription = null;
    _sseService.cancel();

    state = const ChatState();
  }

}

/// SseService 单例 Provider
final sseServiceProvider = Provider<SseService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final storage = ref.watch(secureStorageProvider);
  return SseService(apiClient: apiClient, storage: storage);
});

/// 对话状态 Provider
final chatProvider = NotifierProvider<ChatNotifier, ChatState>(() {
  return ChatNotifier();
});
