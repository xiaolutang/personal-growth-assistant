import 'package:flutter/material.dart';

import '../config/theme.dart';

// ============================================================
// QuickActions - 快速操作浮动按钮
// ============================================================
class QuickActions extends StatefulWidget {
  /// 「记灵感」回调：跳转到日知 Tab
  final VoidCallback onInbox;

  /// 「建任务」回调：弹出底部输入面板
  final VoidCallback onCreateTask;

  const QuickActions({
    super.key,
    required this.onInbox,
    required this.onCreateTask,
  });

  @override
  State<QuickActions> createState() => _QuickActionsState();
}

class _QuickActionsState extends State<QuickActions>
    with SingleTickerProviderStateMixin {
  bool _isExpanded = false;
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;
  late Animation<double> _rotateAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    );
    _scaleAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutBack,
    );
    _rotateAnimation = Tween<double>(begin: 0, end: 0.75).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _toggle() {
    setState(() {
      _isExpanded = !_isExpanded;
    });
    if (_isExpanded) {
      _controller.forward();
    } else {
      _controller.reverse();
    }
  }

  void _handleInbox() {
    _toggle();
    widget.onInbox();
  }

  void _handleCreateTask() {
    _toggle();
    widget.onCreateTask();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        // 子按钮们（从下往上排列）
        if (_isExpanded) ...[
          _buildSubButton(
            label: '记灵感',
            icon: Icons.lightbulb_outline,
            color: AppColors.warning,
            onPressed: _handleInbox,
          ),
          const SizedBox(height: AppSpacing.sm),
          _buildSubButton(
            label: '建任务',
            icon: Icons.add_task,
            color: AppColors.completed,
            onPressed: _handleCreateTask,
          ),
          const SizedBox(height: AppSpacing.md),
        ],

        // 主 FAB
        FloatingActionButton(
          onPressed: _toggle,
          backgroundColor: AppColors.primary,
          child: RotationTransition(
            turns: _rotateAnimation,
            child: const Icon(Icons.add, color: Colors.white),
          ),
        ),
      ],
    );
  }

  Widget _buildSubButton({
    required String label,
    required IconData icon,
    required Color color,
    required VoidCallback onPressed,
  }) {
    return ScaleTransition(
      scale: _scaleAnimation,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 标签
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.xs + 2,
            ),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.9),
              borderRadius: BorderRadius.circular(AppRadius.button),
            ),
            child: Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: AppFontSize.body,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          // 圆形按钮
          SizedBox(
            width: 48,
            height: 48,
            child: FloatingActionButton(
              heroTag: label,
              mini: true,
              backgroundColor: color,
              onPressed: onPressed,
              child: Icon(icon, color: Colors.white, size: 24),
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================
// CreateTaskSheet - 创建任务底部面板
// ============================================================
class CreateTaskSheet extends StatefulWidget {
  /// 提交回调，返回 true 表示创建成功
  final Future<bool> Function(String title) onSubmit;

  const CreateTaskSheet({super.key, required this.onSubmit});

  /// 显示底部面板
  static Future<void> show(BuildContext context, {
    required Future<bool> Function(String title) onSubmit,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
      ),
      builder: (context) => CreateTaskSheet(onSubmit: onSubmit),
    );
  }

  @override
  State<CreateTaskSheet> createState() => _CreateTaskSheetState();
}

class _CreateTaskSheetState extends State<CreateTaskSheet> {
  final _controller = TextEditingController();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _handleSubmit() async {
    final title = _controller.text.trim();
    if (title.isEmpty) return;

    setState(() => _isSubmitting = true);

    final success = await widget.onSubmit(title);

    if (!mounted) return;

    if (success) {
      Navigator.of(context).pop();
    } else {
      setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Padding(
      padding: EdgeInsets.only(
        left: AppSpacing.lg,
        right: AppSpacing.lg,
        top: AppSpacing.xl,
        bottom: bottomInset + AppSpacing.lg,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 标题
          Text(
            '新建任务',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: AppSpacing.lg),

          // 输入框
          TextField(
            controller: _controller,
            autofocus: true,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => _handleSubmit(),
            decoration: const InputDecoration(
              hintText: '输入任务标题',
              prefixIcon: Icon(Icons.add_task),
            ),
            enabled: !_isSubmitting,
          ),
          const SizedBox(height: AppSpacing.md),

          // 提交按钮
          FilledButton(
            onPressed: _isSubmitting ? null : _handleSubmit,
            child: _isSubmitting
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Text('创建'),
          ),
        ],
      ),
    );
  }
}
