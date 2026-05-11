import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../config/theme.dart';

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
      context.pop();
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
