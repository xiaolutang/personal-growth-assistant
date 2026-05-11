import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rizhi/config/theme.dart';
import 'package:rizhi/widgets/skeleton_loading.dart';

/// 辅助函数：找到所有 shimmer Container（有 BoxDecoration 且 color 非 null）
Iterable<Container> _findShimmerContainers(WidgetTester tester) {
  return tester.widgetList<Container>(find.byType(Container)).where((c) {
    final decoration = c.decoration;
    if (decoration is BoxDecoration) {
      return decoration.color != null;
    }
    return false;
  });
}

void main() {
  group('SkeletonLoading', () {
    // --------------------------------------------------------
    // list-card 模式
    // --------------------------------------------------------
    testWidgets('list-card mode renders 8 shimmer blocks',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonLoading(layout: SkeletonLayout.listCard),
          ),
        ),
      );
      await tester.pump();

      // list-card: 标题行 3 + 摘要 3 + chips 2 = 8 shimmer boxes
      final shimmerContainers = _findShimmerContainers(tester);
      expect(shimmerContainers.length, equals(8));
    });

    testWidgets('list-card mode renders a Card widget',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonLoading(layout: SkeletonLayout.listCard),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(Card), findsOneWidget);
    });

    // --------------------------------------------------------
    // text-line 模式
    // --------------------------------------------------------
    testWidgets('text-line mode renders 3 shimmer blocks',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonLoading(layout: SkeletonLayout.textLine),
          ),
        ),
      );
      await tester.pump();

      // text-line: 3 行文本 shimmer
      final shimmerContainers = _findShimmerContainers(tester);
      expect(shimmerContainers.length, equals(3));
    });

    testWidgets('text-line mode does not render Card',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonLoading(layout: SkeletonLayout.textLine),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(Card), findsNothing);
    });

    // --------------------------------------------------------
    // 主题颜色：使用 surfaceContainerHighest 而非硬编码灰色
    // --------------------------------------------------------
    testWidgets(
        'shimmer color comes from theme surfaceContainerHighest, not Colors.grey',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonLoading(layout: SkeletonLayout.textLine),
          ),
        ),
      );
      await tester.pump();

      final surfaceColor =
          AppTheme.lightTheme.colorScheme.surfaceContainerHighest;
      final shimmerContainers = _findShimmerContainers(tester);

      for (final container in shimmerContainers) {
        final decoration = container.decoration as BoxDecoration;
        final color = decoration.color!;
        // 基础色的 RGB 应来自 theme 的 surfaceContainerHighest
        expect(color.r, closeTo(surfaceColor.r, 0.001));
        expect(color.g, closeTo(surfaceColor.g, 0.001));
        expect(color.b, closeTo(surfaceColor.b, 0.001));
        // alpha 应在 0.15 ~ 0.25 范围内（shimmer 范围）
        expect(color.a, inInclusiveRange(0.14, 0.26));
      }
    });

    // --------------------------------------------------------
    // 深色模式：实际使用 dark theme 的 surfaceContainerHighest
    // --------------------------------------------------------
    testWidgets('dark mode renders with dark theme surfaceContainerHighest',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.darkTheme,
          home: const Scaffold(
            body: SkeletonLoading(layout: SkeletonLayout.textLine),
          ),
        ),
      );
      await tester.pump();

      final darkSurface =
          AppTheme.darkTheme.colorScheme.surfaceContainerHighest;
      final lightSurface =
          AppTheme.lightTheme.colorScheme.surfaceContainerHighest;

      // 确认两个主题的 surface 色确实不同
      expect(
        (darkSurface.r, darkSurface.g, darkSurface.b),
        isNot(equals((lightSurface.r, lightSurface.g, lightSurface.b))),
      );

      // 验证实际渲染的 shimmer 使用了 dark theme 的颜色
      final shimmerContainers = _findShimmerContainers(tester);
      for (final container in shimmerContainers) {
        final decoration = container.decoration as BoxDecoration;
        final color = decoration.color!;
        expect(color.r, closeTo(darkSurface.r, 0.001));
        expect(color.g, closeTo(darkSurface.g, 0.001));
        expect(color.b, closeTo(darkSurface.b, 0.001));
      }
    });

    // --------------------------------------------------------
    // shimmer 动画 1500ms 周期验证
    // --------------------------------------------------------
    testWidgets('shimmer animation oscillates with 1500ms period',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonLoading(layout: SkeletonLayout.textLine),
          ),
        ),
      );
      await tester.pump();

      // 记录初始 alpha
      double? initialAlpha;
      for (final container in _findShimmerContainers(tester)) {
        initialAlpha = (container.decoration as BoxDecoration).color!.a;
        break;
      }
      expect(initialAlpha, isNotNull);

      // 推进 750ms（半个周期）→ alpha 应该在最高点（0.25）
      await tester.pump(const Duration(milliseconds: 750));
      double? midAlpha;
      for (final container in _findShimmerContainers(tester)) {
        midAlpha = (container.decoration as BoxDecoration).color!.a;
        break;
      }
      expect(midAlpha, isNotNull);
      expect(
        midAlpha,
        isNot(equals(initialAlpha)),
        reason: 'Alpha should change after 750ms',
      );

      // 推进到 1500ms 完整周期 → alpha 应回到初始值
      await tester.pump(const Duration(milliseconds: 750));
      double? fullCycleAlpha;
      for (final container in _findShimmerContainers(tester)) {
        fullCycleAlpha = (container.decoration as BoxDecoration).color!.a;
        break;
      }
      expect(
        fullCycleAlpha,
        closeTo(initialAlpha!, 0.01),
        reason: 'After full 1500ms cycle, alpha should return to initial value',
      );
    });

    testWidgets('animation runs continuously without errors',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonLoading(layout: SkeletonLayout.listCard),
          ),
        ),
      );

      for (int i = 0; i < 5; i++) {
        await tester.pump(const Duration(milliseconds: 300));
      }

      expect(find.byType(SkeletonLoading), findsOneWidget);
    });
  });

  group('SkeletonList', () {
    testWidgets('generates specified number of skeleton items',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonList(
              itemCount: 3,
              layout: SkeletonLayout.listCard,
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(SkeletonLoading), findsNWidgets(3));
    });

    testWidgets('generates text-line items', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonList(
              itemCount: 5,
              layout: SkeletonLayout.textLine,
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(SkeletonLoading), findsNWidgets(5));
    });

    testWidgets('defaults to listCard layout', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonList(itemCount: 2),
          ),
        ),
      );
      await tester.pump();

      // 默认 listCard，每个 SkeletonLoading 包含一个 Card
      expect(find.byType(Card), findsNWidgets(2));
    });

    testWidgets('with itemCount 0 renders nothing',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonList(itemCount: 0),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(SkeletonLoading), findsNothing);
    });

    testWidgets('shares single AnimationController across items',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SkeletonList(
              itemCount: 3,
              layout: SkeletonLayout.textLine,
            ),
          ),
        ),
      );
      await tester.pump();

      // SkeletonList 自身是 StatefulWidget，应该有且仅有一个 AnimationController
      // 所有子 SkeletonLoading 的 shimmer 同步变化
      final shimmerContainers = _findShimmerContainers(tester);
      expect(shimmerContainers.length, equals(9)); // 3 items * 3 shimmer boxes

      // 推进动画
      await tester.pump(const Duration(milliseconds: 750));

      // 所有 shimmer 的 alpha 应该相同（共享 controller）
      final updatedContainers = _findShimmerContainers(tester);
      double? firstAlpha;
      for (final container in updatedContainers) {
        final alpha = (container.decoration as BoxDecoration).color!.a;
        if (firstAlpha == null) {
          firstAlpha = alpha;
        } else {
          expect(
            alpha,
            closeTo(firstAlpha, 0.001),
            reason:
                'All shimmer blocks should have synchronized alpha when sharing controller',
          );
        }
      }
    });
  });
}
