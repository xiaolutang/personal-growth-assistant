import 'package:flutter/material.dart';

// ============================================================
// DraggableFAB - 可拖动的浮动按钮
//
// 放在 Stack 内使用，FAB 可自由拖动，松手时吸附到最近的左右边缘。
// 用法:
//   Stack(children: [
//     Scaffold(...),
//     DraggableFAB(child: const QuickCaptureFAB()),
//   ])
// ============================================================

class DraggableFAB extends StatefulWidget {
  final Widget child;
  final double initialRight;
  final double initialBottom;
  final double bottomMargin;

  const DraggableFAB({
    super.key,
    required this.child,
    this.initialRight = 16,
    this.initialBottom = 100,
    this.bottomMargin = 80,
  });

  @override
  State<DraggableFAB> createState() => _DraggableFABState();
}

class _DraggableFABState extends State<DraggableFAB> {
  late double _right;
  late double _bottom;
  bool _isDragging = false;

  static const _fabSize = 56.0;
  static const _padding = 16.0;

  @override
  void initState() {
    super.initState();
    _right = widget.initialRight;
    _bottom = widget.initialBottom;
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final maxY = size.height - _fabSize - widget.bottomMargin;

    return Positioned(
      right: _right.clamp(0.0, size.width - _fabSize),
      bottom: _bottom.clamp(0.0, maxY),
      child: AnimatedContainer(
        duration: _isDragging ? Duration.zero : const Duration(milliseconds: 250),
        curve: Curves.easeOut,
        child: GestureDetector(
          onPanStart: (_) => setState(() => _isDragging = true),
          onPanUpdate: (details) {
            setState(() {
              _right -= details.delta.dx;
              _bottom -= details.delta.dy;
            });
          },
          onPanEnd: (_) {
            setState(() {
              _isDragging = false;
              // 吸附到最近的水平边缘
              final fabCenterX = size.width - _right - _fabSize / 2;
              if (fabCenterX < size.width / 2) {
                _right = size.width - _fabSize - _padding; // 吸附左边
              } else {
                _right = _padding; // 吸附右边（默认）
              }
            });
          },
          child: widget.child,
        ),
      ),
    );
  }
}
