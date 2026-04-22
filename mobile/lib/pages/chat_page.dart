import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/theme.dart';
import '../models/chat_message.dart';
import '../providers/chat_provider.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/entry_created_card.dart';

// ============================================================
// ChatPage - 日知 Tab 对话页面
//
// 功能：
// - 消息气泡列表（用户右蓝/AI左灰）
// - SSE 流式输出（逐字出现动画）
// - 打字指示器
// - 发送消息
// - 错误提示 + 重试
// - 自动滚动到最新消息
// - F105: 创建确认卡片
// ============================================================
class ChatPage extends ConsumerStatefulWidget {
  const ChatPage({super.key});

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> {
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _inputFocusNode = FocusNode();

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    _inputFocusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('日知'),
        centerTitle: true,
      ),
      body: Column(
        children: [
          // 消息列表
          Expanded(
            child: _buildMessageList(context, theme, chatState),
          ),
          // 错误提示条
          if (chatState.error != null)
            _buildErrorBanner(chatState),
          // 输入框区域
          _buildInputArea(chatState),
        ],
      ),
    );
  }

  Widget _buildMessageList(
    BuildContext context,
    ThemeData theme,
    ChatState chatState,
  ) {
    if (chatState.messages.isEmpty) {
      return _buildEmptyState(theme);
    }

    // 监听消息变化，自动滚动
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _scrollToBottom();
    });

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      itemCount: chatState.messages.length,
      itemBuilder: (context, index) {
        final message = chatState.messages[index];

        // F105: 创建确认卡片
        if (message.isCreatedCard) {
          return EntryCreatedCard(entry: message.createdEntry!);
        }

        // AI 消息 + 正在加载
        final showTyping = chatState.isLoading &&
            message.role == ChatMessageRole.assistant &&
            index == chatState.messages.length - 1;

        return ChatBubble(
          message: message,
          showTypingIndicator: showTyping,
        );
      },
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.chat_bubble_outline,
            size: 56,
            color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.3),
          ),
          const SizedBox(height: AppSpacing.lg),
          Text(
            '开始和 AI 对话吧',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            '记录灵感、管理任务、整理笔记...',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.6),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorBanner(ChatState chatState) {
    return Container(
      margin: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.xs,
      ),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppRadius.button),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, size: 16, color: AppColors.error),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              chatState.error!,
              style: const TextStyle(
                fontSize: AppFontSize.caption,
                color: AppColors.error,
              ),
            ),
          ),
          TextButton(
            onPressed: () => ref.read(chatProvider.notifier).retry(),
            style: TextButton.styleFrom(
              foregroundColor: AppColors.error,
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            child: const Text('重试', style: TextStyle(fontSize: AppFontSize.caption)),
          ),
        ],
      ),
    );
  }

  Widget _buildInputArea(ChatState chatState) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: Theme.of(context).colorScheme.outlineVariant.withValues(alpha: 0.3),
          ),
        ),
      ),
      padding: EdgeInsets.only(
        left: AppSpacing.lg,
        right: AppSpacing.sm,
        top: AppSpacing.sm,
        bottom: MediaQuery.of(context).padding.bottom + AppSpacing.sm,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          // 输入框
          Expanded(
            child: TextField(
              controller: _inputController,
              focusNode: _inputFocusNode,
              enabled: !chatState.isLoading,
              maxLines: 4,
              minLines: 1,
              textInputAction: TextInputAction.send,
              onSubmitted: chatState.isLoading ? null : _handleSend,
              decoration: InputDecoration(
                hintText: '记录灵感、想法...',
                hintStyle: TextStyle(
                  color: Theme.of(context).colorScheme.onSurfaceVariant.withValues(alpha: 0.5),
                ),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadius.button),
                  borderSide: BorderSide.none,
                ),
                filled: true,
                fillColor: Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md,
                  vertical: AppSpacing.sm + AppSpacing.xs,
                ),
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.xs),
          // 发送按钮
          IconButton.filled(
            onPressed: chatState.isLoading ? null : _handleSend,
            icon: chatState.isLoading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.send, size: 20),
            style: IconButton.styleFrom(
              backgroundColor: AppColors.primary,
              disabledBackgroundColor: AppColors.primary.withValues(alpha: 0.4),
            ),
          ),
        ],
      ),
    );
  }

  void _handleSend([String? text]) {
    final message = text ?? _inputController.text.trim();
    if (message.isEmpty) return;

    _inputController.clear();
    ref.read(chatProvider.notifier).sendMessage(message);

    // 保持输入框焦点
    _inputFocusNode.requestFocus();
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }
}
