import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/entry_provider.dart';

// ============================================================
// QuickCaptureFAB - 全局快速捕获浮动按钮
//
// 点击弹出 BottomSheet，输入内容后创建 inbox 类型条目。
// 使用方式：放在 Scaffold.floatingActionButton 中。
// ============================================================
class QuickCaptureFAB extends ConsumerWidget {
  const QuickCaptureFAB({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return FloatingActionButton(
      heroTag: 'quick_capture',
      onPressed: () => _showCaptureSheet(context, ref),
      tooltip: '快速捕获',
      child: const Icon(Icons.add),
    );
  }

  void _showCaptureSheet(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => _CaptureBottomSheet(ref: ref),
    );
  }
}

// ============================================================
// _CaptureBottomSheet - 底部输入弹窗
// ============================================================
class _CaptureBottomSheet extends StatefulWidget {
  final WidgetRef ref;

  const _CaptureBottomSheet({required this.ref});

  @override
  State<_CaptureBottomSheet> createState() => _CaptureBottomSheetState();
}

class _CaptureBottomSheetState extends State<_CaptureBottomSheet> {
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

    final notifier = widget.ref.read(entryListProvider.notifier);
    final success = await notifier.createInboxEntry(title);

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
    // 适配软键盘弹出
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 16,
        bottom: bottomInset + 16,
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
                    fontSize: 16,
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
          const SizedBox(height: 12),
          TextField(
            controller: _controller,
            autofocus: true,
            maxLines: 3,
            minLines: 1,
            textInputAction: TextInputAction.newline,
            decoration: const InputDecoration(
              hintText: '记下你的想法...',
              border: OutlineInputBorder(),
            ),
            onChanged: (_) => setState(() {}),
            onSubmitted: (_) {
              if (_canSubmit) _submit();
            },
          ),
          const SizedBox(height: 12),
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
