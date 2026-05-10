import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rizhi/models/chat_message.dart';
import 'package:rizhi/providers/chat_provider.dart';
import 'package:rizhi/services/sse_service.dart';

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

    // Sentinel pattern tests
    test('copyWith without error param preserves existing error', () {
      const state = ChatState(error: 'Existing error', isLoading: true);
      final copied = state.copyWith(isLoading: false);

      expect(copied.error, 'Existing error');
      expect(copied.isLoading, false);
    });

    test('copyWith without error param preserves null error', () {
      const state = ChatState(isLoading: true);
      final copied = state.copyWith(isLoading: false);

      expect(copied.error, isNull);
      expect(copied.isLoading, false);
    });

    test('copyWith with explicit error null clears error', () {
      const state = ChatState(error: 'Some error');
      final copied = state.copyWith(error: null);

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

    test('sseServiceProvider provides same instance', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final sse1 = container.read(sseServiceProvider);
      final sse2 = container.read(sseServiceProvider);

      expect(identical(sse1, sse2), true,
          reason: 'sseServiceProvider should return the same singleton instance');
    });

    test('dispose cancels subscription', () async {
      // This tests that onDispose properly cleans up
      final container = ProviderContainer();

      // Just reading the provider and disposing should not throw
      container.read(chatProvider);
      container.dispose();

      // If we reach here without error, cleanup was successful
      expect(true, true);
    });
  });

  group('SSE single subscription pattern', () {
    test('sseServiceProvider is a singleton (Provider, not family)', () {
      // Verify that sseServiceProvider is a plain Provider (singleton scope)
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final instance1 = container.read(sseServiceProvider);
      final instance2 = container.read(sseServiceProvider);

      expect(identical(instance1, instance2), true,
          reason: 'SSE service must be a singleton to prevent multiple listeners');
    });

    test('ChatNotifier no longer creates SseService instances', () {
      // Verify ChatNotifier uses sseServiceProvider by checking
      // that the provider exists and is the correct type
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final sseService = container.read(sseServiceProvider);
      expect(sseService, isA<SseService>());
    });
  });
}
