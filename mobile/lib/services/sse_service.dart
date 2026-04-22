import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config/api_config.dart';
import '../models/sse_event.dart';
import 'api_client.dart';

// ============================================================
// SseService - SSE 流式客户端
//
// 功能：
// - 连接 POST /chat 端点，返回 Stream<SseEvent>
// - 解析 SSE 格式: event: xxx\ndata: {json}\n\n
// - 自动重连（最多 3 次）
// - JWT token 注入
// - 支持取消订阅（cancel 方法）
// ============================================================

class SseService {
  final ApiClient _apiClient;
  final FlutterSecureStorage _storage;

  /// 最大重连次数
  static const int maxRetries = 3;

  /// 重连间隔基数（毫秒）
  static const int _retryBaseDelay = 1000;

  /// 当前活跃的 ResponseBody 订阅
  StreamSubscription<List<int>>? _responseSubscription;

  /// 重连定时器
  Timer? _retryTimer;

  /// 是否已取消
  bool _cancelled = false;

  SseService({
    required ApiClient apiClient,
    FlutterSecureStorage? storage,
  })  : _apiClient = apiClient,
        _storage = storage ?? const FlutterSecureStorage();

  /// 连接 SSE 流
  ///
  /// [message] 用户输入文本
  /// [sessionId] 会话 ID
  /// [skipIntent] 是否跳过意图检测
  /// [confirm] 确认操作（多选场景）
  /// [pageContext] 页面上下文
  ///
  /// 返回 `Stream<SseEvent>`
  Stream<SseEvent> connect({
    required String message,
    String sessionId = 'default',
    bool skipIntent = false,
    Map<String, dynamic>? confirm,
    Map<String, dynamic>? pageContext,
  }) {
    _cancelled = false;
    final controller = StreamController<SseEvent>();

    _startStream(
      controller: controller,
      message: message,
      sessionId: sessionId,
      skipIntent: skipIntent,
      confirm: confirm,
      pageContext: pageContext,
      retryCount: 0,
    );

    return controller.stream;
  }

  /// 取消当前 SSE 连接
  void cancel() {
    _cancelled = true;
    _retryTimer?.cancel();
    _retryTimer = null;
    _responseSubscription?.cancel();
    _responseSubscription = null;
  }

  void _startStream({
    required StreamController<SseEvent> controller,
    required String message,
    required String sessionId,
    required bool skipIntent,
    Map<String, dynamic>? confirm,
    Map<String, dynamic>? pageContext,
    required int retryCount,
  }) async {
    if (_cancelled || controller.isClosed) return;

    try {
      final token = await _storage.read(key: ApiConfig.keyJwtToken);

      final requestBody = <String, dynamic>{
        'text': message,
        'session_id': sessionId,
        'skip_intent': skipIntent,
      };
      if (confirm != null) requestBody['confirm'] = confirm;
      if (pageContext != null) requestBody['page_context'] = pageContext;

      // 使用 Dio 发送 POST 请求，responseType 为 stream
      final response = await _apiClient.dio.post<dynamic>(
        '/chat',
        data: requestBody,
        options: Options(
          responseType: ResponseType.stream,
          headers: {
            if (token != null) 'Authorization': 'Bearer $token',
            'Accept': 'text/event-stream',
          },
        ),
      );

      if (_cancelled || controller.isClosed) return;

      final responseStream = response.data as ResponseBody; // ignore: unnecessary_cast

      // SSE 解析缓冲区
      final buffer = StringBuffer();
      const String currentEvent = 'message';

      _responseSubscription = responseStream.stream.listen(
        (data) {
          final chunk = utf8.decode(data);
          buffer.write(chunk);

          // 解析 SSE 事件（以 \n\n 分隔）
          final content = buffer.toString();
          final events = content.split('\n\n');

          // 最后一段可能不完整，保留在缓冲区
          if (!content.endsWith('\n\n')) {
            buffer.clear();
            buffer.write(events.removeLast());
          } else {
            buffer.clear();
          }

          for (final eventBlock in events) {
            if (eventBlock.trim().isEmpty) continue;

            final parsed = _parseSseBlock(eventBlock, currentEvent);
            if (parsed != null) {
              if (!controller.isClosed) {
                controller.add(parsed);
              }
              // 检查终止事件
              if (parsed.isDone || parsed.isError) {
                controller.close();
                return;
              }
            }
          }
        },
        onError: (error) {
          _handleStreamError(
            controller: controller,
            error: error,
            message: message,
            sessionId: sessionId,
            skipIntent: skipIntent,
            confirm: confirm,
            pageContext: pageContext,
            retryCount: retryCount,
          );
        },
        onDone: () {
          if (!controller.isClosed) {
            controller.close();
          }
        },
        cancelOnError: false,
      );
    } catch (e) {
      // 请求阶段错误（网络等）
      _handleStreamError(
        controller: controller,
        error: e,
        message: message,
        sessionId: sessionId,
        skipIntent: skipIntent,
        confirm: confirm,
        pageContext: pageContext,
        retryCount: retryCount,
      );
    }
  }

  /// 解析单个 SSE 事件块
  SseEvent? _parseSseBlock(String block, String defaultEvent) {
    String eventType = defaultEvent;
    String? dataStr;

    for (final line in block.split('\n')) {
      final trimmed = line.trim();
      if (trimmed.isEmpty) continue;

      if (trimmed.startsWith('event:')) {
        eventType = trimmed.substring(6).trim();
      } else if (trimmed.startsWith('data:')) {
        dataStr = trimmed.substring(5).trim();
      }
    }

    if (dataStr == null || dataStr.isEmpty) return null;

    try {
      final data = json.decode(dataStr) as Map<String, dynamic>;
      return SseEvent(type: eventType, data: data);
    } catch (_) {
      return SseEvent(type: eventType, data: {'raw': dataStr});
    }
  }

  /// 处理流错误，支持自动重连
  void _handleStreamError({
    required StreamController<SseEvent> controller,
    required dynamic error,
    required String message,
    required String sessionId,
    required bool skipIntent,
    Map<String, dynamic>? confirm,
    Map<String, dynamic>? pageContext,
    required int retryCount,
  }) {
    if (controller.isClosed || _cancelled) return;

    if (retryCount < maxRetries) {
      // 指数退避重连
      final delay = _retryBaseDelay * (1 << retryCount);
      _retryTimer = Timer(Duration(milliseconds: delay), () {
        if (!controller.isClosed && !_cancelled) {
          _startStream(
            controller: controller,
            message: message,
            sessionId: sessionId,
            skipIntent: skipIntent,
            confirm: confirm,
            pageContext: pageContext,
            retryCount: retryCount + 1,
          );
        }
      });
    } else {
      controller.add(const SseEvent(
        type: SseEventType.error,
        data: {'message': '连接失败，已重试 3 次'},
      ),);
      controller.close();
    }
  }
}
