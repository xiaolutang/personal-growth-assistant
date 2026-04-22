import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/chat_message.dart';
import 'package:growth_assistant/models/entry.dart';

void main() {
  group('ChatMessage', () {
    test('creates with required fields', () {
      final now = DateTime(2026, 4, 22, 10, 0, 0);
      final message = ChatMessage(
        id: 'msg-1',
        role: ChatMessageRole.user,
        text: 'Hello',
        createdAt: now,
      );

      expect(message.id, 'msg-1');
      expect(message.role, ChatMessageRole.user);
      expect(message.text, 'Hello');
      expect(message.createdAt, now);
      expect(message.createdEntry, isNull);
    });

    test('creates with createdEntry for system messages', () {
      final now = DateTime(2026, 4, 22, 10, 0, 0);
      const entry = Entry(
        id: 'inbox-1',
        title: '学习 Flutter 动画',
        category: 'inbox',
      );
      final message = ChatMessage(
        id: 'msg-sys-1',
        role: ChatMessageRole.system,
        text: '',
        createdAt: now,
        createdEntry: entry,
      );

      expect(message.role, ChatMessageRole.system);
      expect(message.createdEntry, isNotNull);
      expect(message.createdEntry!.id, 'inbox-1');
      expect(message.createdEntry!.title, '学习 Flutter 动画');
      expect(message.isCreatedCard, true);
    });

    test('isCreatedCard is false for non-system messages', () {
      final message = ChatMessage(
        id: 'msg-1',
        role: ChatMessageRole.user,
        text: 'Hello',
        createdAt: DateTime.now(),
      );
      expect(message.isCreatedCard, false);
    });

    test('isCreatedCard is false for system messages without entry', () {
      final message = ChatMessage(
        id: 'msg-1',
        role: ChatMessageRole.system,
        text: 'System message',
        createdAt: DateTime.now(),
      );
      expect(message.isCreatedCard, false);
    });

    test('fromJson parses user message correctly', () {
      final json = {
        'id': 'msg-1',
        'role': 'user',
        'text': 'Hello AI',
        'created_at': '2026-04-22T10:00:00.000',
      };

      final message = ChatMessage.fromJson(json);

      expect(message.id, 'msg-1');
      expect(message.role, ChatMessageRole.user);
      expect(message.text, 'Hello AI');
      expect(message.createdAt, DateTime(2026, 4, 22, 10, 0, 0));
      expect(message.createdEntry, isNull);
    });

    test('fromJson parses assistant message correctly', () {
      final json = {
        'id': 'msg-2',
        'role': 'assistant',
        'text': 'Hello!',
        'created_at': '2026-04-22T10:00:01.000',
      };

      final message = ChatMessage.fromJson(json);

      expect(message.role, ChatMessageRole.assistant);
      expect(message.text, 'Hello!');
    });

    test('fromJson parses system message with created entry', () {
      final json = {
        'id': 'msg-3',
        'role': 'system',
        'text': '',
        'created_at': '2026-04-22T10:00:02.000',
        'created_entry': {
          'id': 'inbox-abc123',
          'title': '学习 Flutter 动画',
          'category': 'inbox',
        },
      };

      final message = ChatMessage.fromJson(json);

      expect(message.role, ChatMessageRole.system);
      expect(message.createdEntry, isNotNull);
      expect(message.createdEntry!.id, 'inbox-abc123');
      expect(message.createdEntry!.title, '学习 Flutter 动画');
      expect(message.createdEntry!.category, 'inbox');
    });

    test('toJson produces correct map for user message', () {
      final message = ChatMessage(
        id: 'msg-1',
        role: ChatMessageRole.user,
        text: 'Hello',
        createdAt: DateTime(2026, 4, 22, 10, 0, 0),
      );

      final json = message.toJson();

      expect(json['id'], 'msg-1');
      expect(json['role'], 'user');
      expect(json['text'], 'Hello');
      expect(json['created_at'], '2026-04-22T10:00:00.000');
      expect(json.containsKey('created_entry'), false);
    });

    test('toJson includes created_entry for system messages', () {
      final message = ChatMessage(
        id: 'msg-sys',
        role: ChatMessageRole.system,
        text: '',
        createdAt: DateTime(2026, 4, 22, 10, 0, 0),
        createdEntry: const Entry(
          id: 'inbox-1',
          title: 'Test',
          category: 'inbox',
        ),
      );

      final json = message.toJson();

      expect(json['created_entry'], isNotNull);
      expect(json['created_entry']['id'], 'inbox-1');
    });

    test('copyWith updates specified fields', () {
      final original = ChatMessage(
        id: 'msg-1',
        role: ChatMessageRole.assistant,
        text: 'Hello',
        createdAt: DateTime(2026, 4, 22, 10, 0, 0),
      );

      final updated = original.copyWith(text: 'Hello World');

      expect(updated.id, 'msg-1');
      expect(updated.text, 'Hello World');
      expect(updated.role, ChatMessageRole.assistant);
    });

    test('fromJson handles unknown role as system', () {
      final json = {
        'id': 'msg-x',
        'role': 'unknown_role',
        'text': 'test',
        'created_at': '2026-04-22T10:00:00.000',
      };

      final message = ChatMessage.fromJson(json);
      expect(message.role, ChatMessageRole.system);
    });
  });
}
