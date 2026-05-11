import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/theme.dart';
import '../providers/entry_provider.dart';
import '../providers/today_provider.dart';
import 'create_task_sheet.dart' show CreateTaskSheet;

// ============================================================
// QuickCaptureFAB - 全局混合浮动按钮（展开式）
//
// 点击展开为 2 个子按钮：
// 1. 记灵感 — 直接创建 inbox 条目
// 2. 建任务 — 弹出 CreateTaskSheet
//
// 使用方式：放在 Stack 内 DraggableFAB 中。
// onExpandChanged 回调通知 Shell 层展开状态，用于点击空白收起。
// ============================================================
class QuickCaptureFAB extends ConsumerStatefulWidget {
  /// 展开/收起状态变化回调
  final ValueChanged<bool>? onExpandChanged;

  const QuickCaptureFAB({super.key, this.onExpandChanged});

  @override
  ConsumerState<QuickCaptureFAB> createState() => QuickCaptureFABState();
}

class QuickCaptureFABState extends ConsumerState<QuickCaptureFAB>
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

  /// 公开的收起方法，供 Shell 层通过 GlobalKey 调用
  void collapse() => _collapse();

  // ---- 记灵感 ----
  Future<void> _handleInbox() async {
    _collapse();

    // 复用已有的 _CaptureBottomSheet，保持一致的输入体验
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => _CaptureBottomSheet(
        onCapture: (title) async {
          final notifier = ref.read(entryListProvider.notifier);
          final success = await notifier.createInboxEntry(title);
          if (success) {
            // 记灵感成功后刷新 Today 数据（覆盖当前在 Today 和从其他 Tab 返回两种场景）
            ref.read(todayProvider.notifier).loadData();
          }
          return success;
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
        if (success) {
          ref.invalidate(entryListProvider);
          // 建任务成功后刷新 Today 数据（覆盖当前在 Today 和从其他 Tab 返回两种场景）
          ref.read(todayProvider.notifier).loadData();
        }
        if (mounted) {
          final message = success ? '任务已创建' : '创建任务失败，请重试';
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(message),
              duration: const Duration(seconds: 2),
            ),
          );
        }
        return success;
      },
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

  /// 构建子按钮（标签 + 圆形图标）
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
// _InputSheet — 通用输入底部弹窗基类
//
// 提供统一的标题栏 + TextField + 提交按钮布局，
// 子类只需 override _onSubmit 提供差异化提交逻辑。
// ============================================================
abstract class _InputSheet extends ConsumerStatefulWidget {
  final String title;
  final IconData icon;
  final String hintText;
  final String buttonText;

  const _InputSheet({
    required this.title,
    required this.icon,
    required this.hintText,
    required this.buttonText,
  });
}

abstract class _InputSheetState<T extends _InputSheet> extends ConsumerState<T> {
  final _controller = TextEditingController();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  bool get _canSubmit =>
      _controller.text.trim().isNotEmpty && !_isSubmitting;

  /// 子类实现具体提交逻辑
  Future<void> onSubmit(String text);

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isSubmitting) return;

    setState(() => _isSubmitting = true);
    await onSubmit(text);
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
              Icon(widget.icon, size: 20),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Text(
                  widget.title,
                  style: const TextStyle(
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
            decoration: InputDecoration(
              hintText: widget.hintText,
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
                      : Text(widget.buttonText),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

// ---- 记灵感 BottomSheet ----

class _CaptureBottomSheet extends _InputSheet {
  final Future<bool> Function(String title) onCapture;

  const _CaptureBottomSheet({required this.onCapture})
      : super(
          title: '快速捕获灵感',
          icon: Icons.lightbulb_outline,
          hintText: '记下你的想法...',
          buttonText: '保存',
        );

  @override
  ConsumerState<_CaptureBottomSheet> createState() =>
      _CaptureBottomSheetState();
}

class _CaptureBottomSheetState extends _InputSheetState<_CaptureBottomSheet> {
  @override
  Future<void> onSubmit(String text) async {
    final success = await widget.onCapture(text);

    if (!mounted) return;

    if (success) {
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('灵感已保存'), duration: Duration(seconds: 2)),
      );
    } else {
      setState(() => _isSubmitting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('保存失败，请重试'), duration: Duration(seconds: 2)),
      );
    }
  }
}
