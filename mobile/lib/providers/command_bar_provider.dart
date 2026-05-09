import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../config/api_config.dart';
import '../models/command_result.dart';
import '../models/sse_event.dart';
import '../providers/auth_provider.dart';
import '../services/sse_service.dart' show SseService;

// ============================================================
// CommandBarState - 命令栏状态
// ============================================================
class CommandBarState {
  final bool isLoading;
  final CommandResult? result;
  final String? lastInput;

  const CommandBarState({
    this.isLoading = false,
    this.result,
    this.lastInput,
  });

  CommandBarState copyWith({
    bool? isLoading,
    CommandResult? Function()? result,
    String? lastInput,
  }) {
    return CommandBarState(
      isLoading: isLoading ?? this.isLoading,
      result: result != null ? result() : this.result,
      lastInput: lastInput ?? this.lastInput,
    );
  }
}

// ============================================================
// CommandBarNotifier - 命令栏 Provider
//
// 独立于 ChatProvider，不共享 SseService。
// 使用 ApiClient.dio 直接发起 SSE 请求。
// 每次命令生成新 session_id，无对话历史。
// ============================================================
class CommandBarNotifier extends Notifier<CommandBarState> {
  StreamSubscription<List<int>>? _responseSubscription;
  CancelToken? _cancelToken;
  Timer? _debounceTimer;

  /// 执行 ID：每次 _doExecute 递增，回调只允许当前 ID 更新 state
  int _executionId = 0;

  static const Duration _debounceDuration = Duration(milliseconds: 300);

  @override
  CommandBarState build() {
    ref.onDispose(() {
      _responseSubscription?.cancel();
      _responseSubscription = null;
      _cancelToken?.cancel();
      _cancelToken = null;
      _debounceTimer?.cancel();
      _debounceTimer = null;
    });
    return const CommandBarState();
  }

  /// 执行命令（带 300ms debounce）
  void executeCommand(String text) {
    if (text.trim().isEmpty) return;

    // 立即作废旧执行，防止 debounce 窗口内旧流回写 state
    _executionId++;
    _cancelPrevious();

    _debounceTimer?.cancel();
    _debounceTimer = Timer(_debounceDuration, () {
      _doExecute(text.trim());
    });
  }

  /// 立即执行（用于重试，不走 debounce）
  void retry() {
    final last = state.lastInput;
    if (last == null || last.isEmpty) return;
    _doExecute(last);
  }

  /// 清除结果（关闭内联卡片）
  void clearResult() {
    state = CommandBarState(lastInput: state.lastInput);
  }

  Future<void> _doExecute(String text) async {
    final authState = ref.read(authProvider);
    final userId = authState.whenOrNull<String>(
      data: (s) => s is AuthAuthenticated ? s.user.id : null,
    );
    if (userId == null) return;

    // 取消上一次未完成的连接
    _cancelPrevious();

    // 绑定本次执行 ID，所有回调只在此 ID 匹配时才更新 state
    final execId = ++_executionId;

    state = CommandBarState(
      isLoading: true,
      lastInput: text,
    );

    // 每次命令生成新 session_id
    final sessionId = const Uuid().v4();

    final token = await ref.read(secureStorageProvider).read(
          key: ApiConfig.keyJwtToken,
        );

    final cancelToken = CancelToken();
    _cancelToken = cancelToken;

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.dio.post<dynamic>(
        '/chat',
        data: {
          'text': text,
          'session_id': sessionId,
          'page_context': {'page_type': 'command'},
        },
        options: Options(
          responseType: ResponseType.stream,
          headers: {
            if (token != null) 'Authorization': 'Bearer $token',
            'Accept': 'text/event-stream',
          },
        ),
        cancelToken: cancelToken,
      );

      // 请求成功后再次确认仍是当前执行
      if (execId != _executionId) return;

      final responseStream = response.data as ResponseBody;
      final buffer = StringBuffer();
      final contentBuffer = StringBuffer();
      var receivedTerminal = false;

      _responseSubscription = responseStream.stream.listen(
        (data) {
          if (execId != _executionId) return;

          // 复用 SseService 的 SSE 分帧逻辑
          final events = SseService.parseSseChunks(buffer, data);
          for (final event in events) {
            if (_handleEvent(event, contentBuffer, execId, text)) {
              receivedTerminal = true;
            }
          }
        },
        onError: (error) {
          if (execId != _executionId) return;
          state = CommandBarState(
            isLoading: false,
            lastInput: text,
            result: CommandResult(
              type: CommandResultType.error,
              message: _errorMessage(error),
            ),
          );
        },
        onDone: () {
          if (execId != _executionId) return;
          if (!state.isLoading) return;

          // 如果已经收到过有效终止事件（created/updated/redirect/done），不做额外处理
          if (receivedTerminal) {
            state = state.copyWith(isLoading: false);
            return;
          }

          // 流结束：如果 content 有内容，产出 answer（content + done 是合法终端路径）
          final content = contentBuffer.toString().trim();
          if (content.isNotEmpty) {
            state = CommandBarState(
              isLoading: false,
              lastInput: text,
              result: CommandResult(
                type: CommandResultType.answer,
                message: content,
                answer: content,
              ),
            );
          } else {
            // 流结束但没有有效终止事件也没有内容 → 连接中断
            state = CommandBarState(
              isLoading: false,
              lastInput: text,
              result: const CommandResult(
                type: CommandResultType.error,
                message: '连接中断，请重试',
              ),
            );
          }
        },
        cancelOnError: false,
      );
    } catch (e) {
      if (execId != _executionId) return;
      state = CommandBarState(
        isLoading: false,
        lastInput: text,
        result: CommandResult(
          type: CommandResultType.error,
          message: _errorMessage(e),
        ),
      );
    }
  }

  /// 处理单个 SSE 事件。返回 true 表示该事件是终止事件。
  bool _handleEvent(SseEvent event, StringBuffer contentBuffer, int execId, String text) {
    if (execId != _executionId) return false;

    switch (event.type) {
      case SseEventType.created:
        if (event.data.containsKey('raw')) {
          state = CommandBarState(
            isLoading: false,
            lastInput: text,
            result: const CommandResult(
              type: CommandResultType.error,
              message: '响应格式异常',
            ),
          );
          return true;
        }
        final entryId = event.data['id']?.toString();
        final count = event.data['count'] as int?;
        state = CommandBarState(
          isLoading: false,
          lastInput: text,
          result: CommandResult(
            type: CommandResultType.success,
            message: count != null ? '创建了 $count 条记录' : '创建成功',
            entryId: entryId,
          ),
        );
        return true;

      case SseEventType.updated:
        if (event.data.containsKey('raw')) {
          state = CommandBarState(
            isLoading: false,
            lastInput: text,
            result: const CommandResult(
              type: CommandResultType.error,
              message: '响应格式异常',
            ),
          );
          return true;
        }
        final entryId = event.data['id']?.toString();
        state = CommandBarState(
          isLoading: false,
          lastInput: text,
          result: CommandResult(
            type: CommandResultType.success,
            message: '更新成功',
            entryId: entryId,
          ),
        );
        return true;

      case SseEventType.redirect:
        if (event.data.containsKey('raw')) {
          state = CommandBarState(
            isLoading: false,
            lastInput: text,
            result: const CommandResult(
              type: CommandResultType.error,
              message: '响应格式异常',
            ),
          );
          return true;
        }
        state = CommandBarState(
          isLoading: false,
          lastInput: text,
          result: const CommandResult(
            type: CommandResultType.redirectChat,
            message: '在日知中继续对话',
          ),
        );
        return true;

      case SseEventType.content:
        if (event.data.containsKey('raw')) {
          // malformed payload → error
          state = CommandBarState(
            isLoading: false,
            lastInput: text,
            result: const CommandResult(
              type: CommandResultType.error,
              message: '响应格式异常',
            ),
          );
          return true;
        }
        final content = event.contentText ?? '';
        if (content.isNotEmpty) {
          contentBuffer.write(content);
        }
        return false;

      case SseEventType.error:
        state = CommandBarState(
          isLoading: false,
          lastInput: text,
          result: CommandResult(
            type: CommandResultType.error,
            message: event.errorMessage ?? '未知错误',
          ),
        );
        return true;

      case SseEventType.done:
        final content = contentBuffer.toString().trim();
        if (content.isNotEmpty && state.isLoading) {
          state = CommandBarState(
            isLoading: false,
            lastInput: text,
            result: CommandResult(
              type: CommandResultType.answer,
              message: content,
              answer: content,
            ),
          );
        } else if (state.isLoading) {
          state = state.copyWith(isLoading: false);
        }
        return true;

      default:
        return false;
    }
  }

  void _cancelPrevious() {
    _responseSubscription?.cancel();
    _responseSubscription = null;
    _cancelToken?.cancel();
    _cancelToken = null;
  }

  String _errorMessage(dynamic error) {
    if (error is DioException) {
      switch (error.type) {
        case DioExceptionType.connectionTimeout:
        case DioExceptionType.sendTimeout:
        case DioExceptionType.receiveTimeout:
          return '连接超时，请重试';
        case DioExceptionType.connectionError:
          return '网络连接失败';
        case DioExceptionType.cancel:
          return '请求已取消';
        default:
          return '请求失败，请重试';
      }
    }
    return '未知错误，请重试';
  }
}

/// 命令栏 Provider
final commandBarProvider = NotifierProvider<CommandBarNotifier, CommandBarState>(() {
  return CommandBarNotifier();
});
