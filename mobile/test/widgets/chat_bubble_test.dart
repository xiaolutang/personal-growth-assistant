import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/config/theme.dart';
import 'package:growth_assistant/models/chat_message.dart';
import 'package:growth_assistant/widgets/chat_bubble.dart';

void main() {
  group('ChatBubble', () {
    testWidgets('user bubble displays text correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChatBubble(
              message: ChatMessage(
                id: 'msg-1',
                role: ChatMessageRole.user,
                text: 'Hello AI',
                createdAt: DateTime.now(),
              ),
            ),
          ),
        ),
      );

      // Should find the text
      expect(find.text('Hello AI'), findsOneWidget);
    });

    testWidgets('user message is right aligned',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChatBubble(
              message: ChatMessage(
                id: 'msg-1',
                role: ChatMessageRole.user,
                text: 'Right aligned',
                createdAt: DateTime.now(),
              ),
            ),
          ),
        ),
      );

      // Find the Align widget and verify alignment
      final alignFinder = find.byType(Align);
      expect(alignFinder, findsOneWidget);

      final align = tester.widget<Align>(alignFinder);
      expect(align.alignment, Alignment.centerRight);

      // Verify text content
      expect(find.text('Right aligned'), findsOneWidget);
    });

    testWidgets('assistant message is left aligned',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChatBubble(
              message: ChatMessage(
                id: 'msg-2',
                role: ChatMessageRole.assistant,
                text: 'Left aligned reply',
                createdAt: DateTime.now(),
              ),
            ),
          ),
        ),
      );

      final alignFinder = find.byType(Align);
      expect(alignFinder, findsOneWidget);

      final align = tester.widget<Align>(alignFinder);
      expect(align.alignment, Alignment.centerLeft);

      // Verify text content
      expect(find.text('Left aligned reply'), findsOneWidget);
    });

    testWidgets('shows typing indicator when enabled and text is empty',
        (WidgetTester tester) async {
      await tester.runAsync(() async {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: ChatBubble(
                message: ChatMessage(
                  id: 'msg-ai',
                  role: ChatMessageRole.assistant,
                  text: '',
                  createdAt: DateTime.now(),
                ),
                showTypingIndicator: true,
              ),
            ),
          ),
        );

        // Wait for the delayed animations to start (max delay is 300ms)
        await Future<void>.delayed(const Duration(milliseconds: 400));
        await tester.pump();
      });

      // Should show typing dots - FadeTransition widgets from _TypingDot
      expect(find.byType(FadeTransition), findsWidgets);
    });

    testWidgets('does not show typing indicator when text is present',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChatBubble(
              message: ChatMessage(
                id: 'msg-ai',
                role: ChatMessageRole.assistant,
                text: 'Some response text',
                createdAt: DateTime.now(),
              ),
              showTypingIndicator: true,
            ),
          ),
        ),
      );

      expect(find.text('Some response text'), findsOneWidget);
      // No FadeTransition for typing indicator
      expect(find.byType(FadeTransition), findsNothing);
    });

    testWidgets('user bubble uses primary color', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChatBubble(
              message: ChatMessage(
                id: 'msg-1',
                role: ChatMessageRole.user,
                text: 'Test',
                createdAt: DateTime.now(),
              ),
            ),
          ),
        ),
      );

      // Find the Container that holds the bubble content
      final containerFinder = find.byType(Container);
      // There should be containers (at least the bubble container)
      expect(containerFinder, findsWidgets);

      // Check that we can find the AppColors.primary color in the decorations
      bool foundPrimaryColor = false;
      for (final container in tester.widgetList<Container>(containerFinder)) {
        final decoration = container.decoration;
        if (decoration is BoxDecoration && decoration.color == AppColors.primary) {
          foundPrimaryColor = true;
          break;
        }
      }
      expect(foundPrimaryColor, true);
    });
  });
}
