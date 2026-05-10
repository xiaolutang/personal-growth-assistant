import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/theme.dart';
import '../providers/command_bar_provider.dart';
import '../providers/entry_provider.dart';
import '../providers/today_provider.dart';
import 'quick_actions.dart' show CreateTaskSheet;

// ============================================================
// QuickCaptureFAB - 全局混合浮动按钮（展开式）
//
// 点击展开为 3 个子按钮：
// 1. 记灵感 — 直接创建 inbox 条目
// 2. 建任务 — 弹出 CreateTaskSheet
// 3. AI 智能创建 — 弹出输入框，调用 commandBarProvider
//
// 使用方式：放在 Stack 内 DraggableFAB 中。
// onExpandChanged 回调通知 Shell 层展开状态，用于点击空白收起。
// ============================================================
class QuickCaptureFAB extends ConsumerStatefulWidget {
  /// 展开/收起状态变化回调
  final ValueChanged<bool>? onExpandChanged;

  const QuickCaptureFAB({super.key, this.onExpandChanged});

  @override
  ConsumerState<QuickCaptureFAB> createState() => _QuickCaptureFABState();
}

class _QuickCaptureFABState extends ConsumerState<QuickCaptureFAB>
    with SingleTickerProviderStateMixin {
  bool _isExpanded = false;
  late AnimationController _animController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _rotateAnimation;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    );
    _scaleAnimation = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOutBack,
    );
    _rotateAnimation = Tween<double>(begin: 0, end: 0.75).animate(
      CurvedAnimation(parent: _animController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  void _toggle() {
    setState(() => _isExpanded = !_isExpanded);
    if (_isExpanded) {
      _animController.forward();
    } else {
      _animController.reverse();
    }
    widget.onExpandChanged?.call(_isExpanded);
  }

  void _collapse() {
    if (!_isExpanded) return;
    setState(() => _isExpanded = false);
    _animController.reverse();
    widget.onExpandChanged?.call(false);
  }

  // ---- 记灵感 ----
  Future<void> _handleInbox() async {
    _collapse();

    // 复用已有的 _CaptureBottomSheet，保持一致的输入体验
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => _CaptureBottomSheet(
        onSubmit: (title) async {
          final notifier = ref.read(entryListProvider.notifier);
          return notifier.createInboxEntry(title);
        },
      ),
    );
  }

  // ---- 建任务 ----
  void _handleCreateTask() {
    _collapse();
    CreateTaskSheet.show(
      context,
      onSubmit: (title) async {
        final notifier = ref.read(todayProvider.notifier);
        final success = await notifier.createTask(title);
        // 同步刷新 entryListProvider，保证 Tasks 页立即可见
        if (success) {
          ref.invalidate(entryListProvider);
        }
        if (!success) {
          // CreateTaskSheet 内部会显示错误
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('创建任务失败，请重试'),
                duration: Duration(seconds: 2),
              ),
            );
          }
        } else {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('任务已创建'),
                duration: Duration(seconds: 2),
              ),
            );
          }
        }
        return success;
      },
    );
  }

  // ---- AI 智能创建 ----
  void _handleAICommand() {
    _collapse();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
      ),
      builder: (sheetContext) => _AICommandSheet(ref: ref),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        // 子按钮们（从下往上排列）
        if (_isExpanded) ...[
          // 3. AI 智能创建
          _buildSubButton(
            label: 'AI 创建',
            icon: Icons.auto_awesome,
            color: AppColors.primary,
            onPressed: _handleAICommand,
          ),
          const SizedBox(height: AppSpacing.sm),
          // 2. 建任务
          _buildSubButton(
            label: '建任务',
            icon: Icons.add_task,
            color: AppColors.completed,
            onPressed: _handleCreateTask,
          ),
          const SizedBox(height: AppSpacing.sm),
          // 1. 记灵感
          _buildSubButton(
            label: '记灵感',
            icon: Icons.lightbulb_outline,
            color: AppColors.warning,
            onPressed: _handleInbox,
          ),
          const SizedBox(height: AppSpacing.md),
        ],

        // 主 FAB 按钮
        FloatingActionButton(
          heroTag: 'hybrid_fab',
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

  /// 构建子按钮（标签 + 圆形图标），参考 QuickActions._buildSubButton
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
// _CaptureBottomSheet - 灵感捕获底部弹窗
//
// 复用原有逻辑，通过 onSubmit 回调创建 inbox 条目。
// ============================================================
class _CaptureBottomSheet extends ConsumerStatefulWidget {
  final Future<bool> Function(String title) onSubmit;

  const _CaptureBottomSheet({required this.onSubmit});

  @override
  ConsumerState<_CaptureBottomSheet> createState() => _CaptureBottomSheetState();
}

class _CaptureBottomSheetState extends ConsumerState<_CaptureBottomSheet> {
  final _controller = TextEditingController();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  bool get _canSubmit =>
      _controller.text.trim().isNotEmpty && !_isSubmitting;

  Future<void> _submit() async {
    final title = _controller.text.trim();
    if (title.isEmpty || _isSubmitting) return;

    setState(() => _isSubmitting = true);

    final success = await widget.onSubmit(title);

    if (!mounted) return;

    if (success) {
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('灵感已保存'),
          duration: Duration(seconds: 2),
        ),
      );
    } else {
      setState(() => _isSubmitting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('保存失败，请重试'),
          duration: Duration(seconds: 2),
        ),
      );
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
        children: [
          Row(
            children: [
              const Icon(Icons.lightbulb_outline, size: 20),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  '快速捕获灵感',
                  style: TextStyle(
                    fontSize: AppFontSize.title,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          TextField(
            controller: _controller,
            autofocus: true,
            maxLines: 3,
            minLines: 1,
            textInputAction: TextInputAction.newline,
            decoration: const InputDecoration(
              hintText: '记下你的想法...',
            ),
            onSubmitted: (_) {
              if (_canSubmit) _submit();
            },
          ),
          const SizedBox(height: AppSpacing.md),
          SizedBox(
            width: double.infinity,
            child: ListenableBuilder(
              listenable: _controller,
              builder: (context, _) {
                return FilledButton(
                  onPressed: _canSubmit ? _submit : null,
                  child: _isSubmitting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('保存'),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

// ============================================================
// _AICommandSheet - AI 智能创建底部弹窗
//
// 弹出输入框，提交后调用 commandBarProvider.executeCommand，
// 内联展示结果（成功 toast / AI 回答 / redirect 跳转链接）。
// ============================================================
class _AICommandSheet extends ConsumerStatefulWidget {
  const _AICommandSheet({required this.ref});

  final WidgetRef ref;

  @override
  ConsumerState<_AICommandSheet> createState() => _AICommandSheetState();
}

class _AICommandSheetState extends ConsumerState<_AICommandSheet> {
  final _controller = TextEditingController();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isSubmitting) return;

    setState(() => _isSubmitting = true);

    // 调用 commandBarProvider 执行命令
    widget.ref.read(commandBarProvider.notifier).executeCommand(text);

    // 关闭 BottomSheet，结果由内联卡片展示（commandBarProvider 的 state 变化）
    if (mounted) {
      Navigator.of(context).pop();
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
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, size: 20),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'AI 智能创建',
                  style: TextStyle(
                    fontSize: AppFontSize.title,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          TextField(
            controller: _controller,
            autofocus: true,
            maxLines: 3,
            minLines: 1,
            textInputAction: TextInputAction.newline,
            decoration: const InputDecoration(
              hintText: '告诉 AI 你想做什么...',
              prefixIcon: Icon(Icons.auto_awesome, size: 20),
            ),
            onSubmitted: (_) {
              if (_controller.text.trim().isNotEmpty && !_isSubmitting) {
                _submit();
              }
            },
          ),
          const SizedBox(height: AppSpacing.md),
          SizedBox(
            width: double.infinity,
            child: ListenableBuilder(
              listenable: _controller,
              builder: (context, _) {
                final canSubmit =
                    _controller.text.trim().isNotEmpty && !_isSubmitting;
                return FilledButton(
                  onPressed: canSubmit ? _submit : null,
                  child: _isSubmitting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('发送'),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
