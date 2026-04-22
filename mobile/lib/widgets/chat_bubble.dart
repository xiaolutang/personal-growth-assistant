import 'package:flutter/material.dart';

import '../config/theme.dart';
import '../models/chat_message.dart';

// ============================================================
// ChatBubble - 对话消息气泡
//
// - 用户消息：右对齐，蓝色背景
// - AI 回复：左对齐，灰色背景
// - 加载中：显示打字指示器
// ============================================================
class ChatBubble extends StatelessWidget {
  final ChatMessage message;
  final bool showTypingIndicator;

  const ChatBubble({
    super.key,
    required this.message,
    this.showTypingIndicator = false,
  });

  @override
  Widget build(BuildContext context) {
    if (message.role == ChatMessageRole.user) {
      return _buildUserBubble(context);
    } else {
      return _buildAssistantBubble(context);
    }
  }

  Widget _buildUserBubble(BuildContext context) {
    return Align(
      alignment: Alignment.centerRight,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        margin: const EdgeInsets.only(
          left: AppSpacing.xxl,
          right: AppSpacing.lg,
          top: AppSpacing.xs,
          bottom: AppSpacing.xs,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm + AppSpacing.xs,
        ),
        decoration: const BoxDecoration(
          color: AppColors.primary,
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(AppRadius.card),
            topRight: Radius.circular(AppRadius.card),
            bottomLeft: Radius.circular(AppRadius.card),
            bottomRight: Radius.circular(AppSpacing.xs),
          ),
        ),
        child: Text(
          message.text,
          style: const TextStyle(
            color: Colors.white,
            fontSize: AppFontSize.body,
            height: 1.5,
          ),
        ),
      ),
    );
  }

  Widget _buildAssistantBubble(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        margin: const EdgeInsets.only(
          left: AppSpacing.lg,
          right: AppSpacing.xxl,
          top: AppSpacing.xs,
          bottom: AppSpacing.xs,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm + AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF2C2C2C) : const Color(0xFFF0F0F5),
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(AppRadius.card),
            topRight: Radius.circular(AppRadius.card),
            bottomLeft: Radius.circular(AppSpacing.xs),
            bottomRight: Radius.circular(AppRadius.card),
          ),
        ),
        child: showTypingIndicator && message.text.isEmpty
            ? _buildTypingIndicator(theme)
            : Text(
                message.text,
                style: TextStyle(
                  color: isDark ? Colors.white70 : Colors.black87,
                  fontSize: AppFontSize.body,
                  height: 1.5,
                ),
              ),
      ),
    );
  }

  Widget _buildTypingIndicator(ThemeData theme) {
    return SizedBox(
      height: 20,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildDot(0),
          const SizedBox(width: 4),
          _buildDot(150),
          const SizedBox(width: 4),
          _buildDot(300),
        ],
      ),
    );
  }

  Widget _buildDot(int delay) {
    return _TypingDot(delay: delay);
  }
}

/// 打字动画圆点
class _TypingDot extends StatefulWidget {
  final int delay;

  const _TypingDot({required this.delay});

  @override
  State<_TypingDot> createState() => _TypingDotState();
}

class _TypingDotState extends State<_TypingDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );

    _animation = Tween<double>(begin: 0.4, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );

    Future.delayed(Duration(milliseconds: widget.delay), () {
      if (mounted) {
        _controller.repeat(reverse: true);
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _animation,
      child: Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(
          color: AppColors.primary.withValues(alpha: 0.6),
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}
