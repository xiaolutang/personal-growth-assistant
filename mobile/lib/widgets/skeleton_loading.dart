import 'package:flutter/material.dart';
import 'package:rizhi/config/theme.dart';

// ============================================================
// SkeletonLayout - 骨架屏布局模式
// ============================================================

/// 预设骨架屏布局模式
enum SkeletonLayout {
  /// 列表卡片：标题行 + 多行文本 + 底部 chips
  listCard,

  /// 纯文本行：3 行不等宽文本块
  textLine,
}

// ============================================================
// SkeletonLoading - 通用骨架屏 Widget
// ============================================================

/// 通用骨架屏加载组件
///
/// 支持 [SkeletonLayout.listCard] 和 [SkeletonLayout.textLine] 两种预设布局。
/// shimmer 动画使用纯 AnimationController 实现，周期 1500ms，自动适配深色模式。
///
/// 当独立使用时，组件自行管理 AnimationController。
/// 当作为 [SkeletonList] 子项时，共享父级提供的 controller。
///
/// ```dart
/// SkeletonLoading(layout: SkeletonLayout.listCard)
/// SkeletonLoading(layout: SkeletonLayout.textLine)
/// ```
class SkeletonLoading extends StatefulWidget {
  const SkeletonLoading({
    super.key,
    required this.layout,
    this.controller,
  });

  /// 骨架屏布局模式
  final SkeletonLayout layout;

  /// 可选的外部 AnimationController。
  /// 传入时由调用方管理生命周期（如 SkeletonList 共享）；
  /// 不传入时组件自行创建并管理。
  final AnimationController? controller;

  @override
  State<SkeletonLoading> createState() => _SkeletonLoadingState();
}

class _SkeletonLoadingState extends State<SkeletonLoading>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  bool _ownsController = false;

  @override
  void initState() {
    super.initState();
    if (widget.controller != null) {
      _controller = widget.controller!;
      _ownsController = false;
    } else {
      _controller = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 1500),
      )..repeat();
      _ownsController = true;
    }
  }

  @override
  void didUpdateWidget(SkeletonLoading oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.controller != oldWidget.controller) {
      if (_ownsController) {
        _controller.dispose();
        _ownsController = false;
      }
      if (widget.controller != null) {
        _controller = widget.controller!;
      } else {
        _controller = AnimationController(
          vsync: this,
          duration: const Duration(milliseconds: 1500),
        )..repeat();
        _ownsController = true;
      }
    }
  }

  @override
  void dispose() {
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    switch (widget.layout) {
      case SkeletonLayout.listCard:
        return _buildListCard(context);
      case SkeletonLayout.textLine:
        return _buildTextLine(context);
    }
  }

  // ----------------------------------------------------------
  // list-card 布局：标题行 + 摘要区域 + chips
  // ----------------------------------------------------------
  Widget _buildListCard(BuildContext context) {
    return Card(
      margin: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.sm,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题行
            Row(
              children: [
                _shimmerBox(20, 20, const Radius.circular(4)),
                const SizedBox(width: AppSpacing.sm),
                _shimmerBox(40, 16, const Radius.circular(4)),
                const Spacer(),
                _shimmerBox(80, 12, const Radius.circular(4)),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            // 摘要区域
            _shimmerBox(double.infinity, 14, const Radius.circular(4)),
            const SizedBox(height: AppSpacing.sm),
            _shimmerBox(double.infinity, 14, const Radius.circular(4)),
            const SizedBox(height: AppSpacing.sm),
            _shimmerBox(200, 14, const Radius.circular(4)),
            const SizedBox(height: AppSpacing.md),
            // chips
            Row(
              children: [
                _shimmerBox(60, 24, const Radius.circular(AppRadius.button)),
                const SizedBox(width: AppSpacing.sm),
                _shimmerBox(60, 24, const Radius.circular(AppRadius.button)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // ----------------------------------------------------------
  // text-line 布局：3 行不等宽文本块
  // ----------------------------------------------------------
  Widget _buildTextLine(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _shimmerBox(double.infinity, 14, const Radius.circular(4)),
          const SizedBox(height: AppSpacing.sm),
          _shimmerBox(double.infinity, 14, const Radius.circular(4)),
          const SizedBox(height: AppSpacing.sm),
          _shimmerBox(200, 14, const Radius.circular(4)),
        ],
      ),
    );
  }

  // ----------------------------------------------------------
  // _shimmerBox - 单个闪烁块
  // ----------------------------------------------------------
  Widget _shimmerBox(double width, double height, Radius borderRadius) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final baseColor =
            Theme.of(context).colorScheme.surfaceContainerHighest;
        final alpha = 0.15 + 0.1 * _controller.value;
        return Container(
          width: width,
          height: height,
          decoration: BoxDecoration(
            color: baseColor.withValues(alpha: alpha),
            borderRadius: BorderRadius.all(borderRadius),
          ),
        );
      },
    );
  }
}

// ============================================================
// SkeletonList - 便捷列表骨架屏
// ============================================================

/// 便捷骨架屏列表组件
///
/// 根据 [itemCount] 批量生成 [SkeletonLoading] 列表。
/// 共享单个 AnimationController，避免列表中每个骨架项各自持有独立动画驱动。
///
/// ```dart
/// SkeletonList(itemCount: 3, layout: SkeletonLayout.listCard)
/// SkeletonList(itemCount: 5, layout: SkeletonLayout.textLine)
/// ```
class SkeletonList extends StatefulWidget {
  const SkeletonList({
    super.key,
    required this.itemCount,
    this.layout = SkeletonLayout.listCard,
  });

  /// 骨架项数量
  final int itemCount;

  /// 骨架屏布局模式，默认 [SkeletonLayout.listCard]
  final SkeletonLayout layout;

  @override
  State<SkeletonList> createState() => _SkeletonListState();
}

class _SkeletonListState extends State<SkeletonList>
    with SingleTickerProviderStateMixin {
  late AnimationController _sharedController;

  @override
  void initState() {
    super.initState();
    _sharedController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat();
  }

  @override
  void dispose() {
    _sharedController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: List.generate(
        widget.itemCount,
        (_) => SkeletonLoading(
          layout: widget.layout,
          controller: _sharedController,
        ),
      ),
    );
  }
}
