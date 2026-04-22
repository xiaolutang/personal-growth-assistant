import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../config/theme.dart';

// ============================================================
// ProgressRing - 今日进度环形图
// ============================================================
class ProgressRing extends StatelessWidget {
  /// 完成进度，范围 0.0 ~ 1.0
  final double progress;

  /// 环形图尺寸
  final double size;

  /// 线宽
  final double strokeWidth;

  const ProgressRing({
    super.key,
    required this.progress,
    this.size = 100.0,
    this.strokeWidth = 8.0,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    // 将进度值限制在 0.0 ~ 1.0 范围
    final clampedProgress = progress.clamp(0.0, 1.0);
    final percent = (clampedProgress * 100).round();

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // 环形图
          CustomPaint(
            size: Size(size, size),
            painter: _RingPainter(
              progress: clampedProgress,
              backgroundColor: theme.colorScheme.surfaceContainerHighest,
              foregroundColor: AppColors.primary,
              strokeWidth: strokeWidth,
            ),
          ),
          // 中间数字
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '$percent',
                style: const TextStyle(
                  fontSize: AppFontSize.display,
                  fontWeight: FontWeight.bold,
                  color: AppColors.primary,
                ),
              ),
              Text(
                '%',
                style: TextStyle(
                  fontSize: AppFontSize.caption,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  final double progress;
  final Color backgroundColor;
  final Color foregroundColor;
  final double strokeWidth;

  _RingPainter({
    required this.progress,
    required this.backgroundColor,
    required this.foregroundColor,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - strokeWidth) / 2;

    // 背景环
    final bgPaint = Paint()
      ..color = backgroundColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, bgPaint);

    // 前景弧
    if (progress > 0) {
      final fgPaint = Paint()
        ..color = foregroundColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.round;

      const startAngle = -math.pi / 2;
      final sweepAngle = 2 * math.pi * progress;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweepAngle,
        false,
        fgPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _RingPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.backgroundColor != backgroundColor ||
        oldDelegate.foregroundColor != foregroundColor ||
        oldDelegate.strokeWidth != strokeWidth;
  }
}
