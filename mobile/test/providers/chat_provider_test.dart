import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/chat_message.dart';
import 'package:growth_assistant/providers/chat_provider.dart';

ChatMessage makeMessage(String id) {
  return ChatMessage(
    id: id,
    role: ChatMessageRole.user,
    text: 'Message $id',
    createdAt: DateTime(2026, 4, 22),
  );
}

void main() {
  group('ChatState', () {
    test('initial state has empty messages and no error', () {
      const state = ChatState();

      expect(state.messages, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });

    test('copyWith preserves unchanged fields', () {
      const state = ChatState(isLoading: true);
      final copied = state.copyWith(error: 'Connection failed');

      expect(copied.isLoading, true);
      expect(copied.error, 'Connection failed');
      expect(copied.messages, isEmpty);
    });

    test('copyWith can update isLoading', () {
      const state = ChatState();
      final copied = state.copyWith(isLoading: true);

      expect(copied.isLoading, true);
      expect(copied.error, isNull);
    });

    test('copyWith can update messages', () {
      const state = ChatState();
      final messages = [
        makeMessage('msg-1'),
      ];
      final copied = state.copyWith(messages: messages);

      expect(copied.messages, hasLength(1));
      expect(copied.messages.first.id, 'msg-1');
    });

    test('copyWith can update error to null', () {
      const state = ChatState(error: 'Some error');
      final copied = state.copyWith(error: null);

      expect(copied.error, isNull);
    });

    test('copyWith can clear error while updating other fields', () {
      const state = ChatState(error: 'Error', isLoading: true);
      final copied = state.copyWith(isLoading: false, error: null);

      expect(copied.isLoading, false);
      expect(copied.error, isNull);
    });
  });

  group('ChatNotifier with ProviderContainer', () {
    test('initial build returns default state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(chatProvider);

      expect(state.messages, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });
  });
}
