/// CommandResult - 命令栏执行结果
///
/// 后端 SSE 事件到 CommandResult 的映射：
/// - created/updated → success（操作成功）
/// - content → answer（AI 回答）
/// - redirect → redirectChat（跳转日知）
/// - error → error
class CommandResult {
  final CommandResultType type;
  final String message;
  final String? entryId;
  final String? answer;

  const CommandResult({
    required this.type,
    required this.message,
    this.entryId,
    this.answer,
  });

  @override
  String toString() => 'CommandResult(type: $type, message: $message)';
}

/// 命令结果类型
enum CommandResultType {
  /// 创建/更新成功
  success,

  /// AI 直接回答
  answer,

  /// 跳转到日知（闲聊意图）
  redirectChat,

  /// 错误
  error,
}
