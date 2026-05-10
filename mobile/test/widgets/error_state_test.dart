import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rizhi/widgets/error_state.dart';

void main() {
  group('ErrorStateWidget', () {
    testWidgets('renders error message', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ErrorStateWidget(
              message: '加载失败',
            ),
          ),
        ),
      );

      expect(find.text('加载失败'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });

    testWidgets('renders retry button when onRetry provided',
        (WidgetTester tester) async {
      var retryCalled = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ErrorStateWidget(
              message: '网络错误',
              onRetry: () => retryCalled = true,
            ),
          ),
        ),
      );

      expect(find.text('重试'), findsOneWidget);

      await tester.tap(find.text('重试'));
      expect(retryCalled, true);
    });

    testWidgets('does not render retry button when onRetry is null',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ErrorStateWidget(
              message: '出错了',
            ),
          ),
        ),
      );

      expect(find.text('重试'), findsNothing);
    });

    testWidgets('displays different error messages',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ErrorStateWidget(
              message: '服务器连接超时，请稍后重试',
            ),
          ),
        ),
      );

      expect(find.text('服务器连接超时，请稍后重试'), findsOneWidget);
    });

    testWidgets('retry callback fires correctly on multiple taps',
        (WidgetTester tester) async {
      var retryCount = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ErrorStateWidget(
              message: '加载失败',
              onRetry: () => retryCount++,
            ),
          ),
        ),
      );

      await tester.tap(find.text('重试'));
      await tester.tap(find.text('重试'));
      expect(retryCount, 2);
    });
  });
}
