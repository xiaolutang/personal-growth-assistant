import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/sse_event.dart';

void main() {
  group('SseEvent', () {
    test('parses complete SSE event from raw text', () {
      const raw = 'event: intent\ndata: {"intent":"create","confidence":0.95}\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.type, 'intent');
      expect(event.data['intent'], 'create');
      expect(event.data['confidence'], 0.95);
    });

    test('parses content event with message', () {
      const raw = 'event: content\ndata: {"content":"创建任务：学习 Flutter"}\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.type, 'content');
      expect(event.contentText, '创建任务：学习 Flutter');
    });

    test('parses done event with empty data', () {
      const raw = 'event: done\ndata: {}\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.type, 'done');
      expect(event.isDone, isTrue);
      expect(event.isError, isFalse);
    });

    test('parses error event and provides errorMessage', () {
      const raw = 'event: error\ndata: {"message":"服务未初始化"}\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.type, 'error');
      expect(event.isError, isTrue);
      expect(event.errorMessage, '服务未初始化');
    });

    test('parses created event with entry data', () {
      const raw = 'event: created\ndata: {"id":"entry-123","category":"task"}\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.type, 'created');
      expect(event.data['id'], 'entry-123');
      expect(event.data['category'], 'task');
    });

    test('parses results event for search', () {
      const raw = 'event: results\ndata: {"items":[],"total":0}\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.type, 'results');
      expect(event.data['total'], 0);
    });

    test('parses confirm event', () {
      const raw = 'event: confirm\ndata: {"items":[{"id":"1"},{"id":"2"}]}\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.type, 'confirm');
      expect((event.data['items'] as List).length, 2);
    });

    test('handles event without event field (defaults to message)', () {
      const raw = 'data: {"some":"data"}\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.type, 'message');
      expect(event.data['some'], 'data');
    });

    test('handles malformed JSON gracefully', () {
      const raw = 'event: content\ndata: not-json\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.type, 'content');
      expect(event.data['raw'], 'not-json');
    });

    test('handles empty data gracefully', () {
      const raw = 'event: done\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.type, 'done');
      expect(event.data, isEmpty);
    });

    test('contentText returns null for non-content events', () {
      const raw = 'event: intent\ndata: {"intent":"create"}\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.contentText, isNull);
    });

    test('errorMessage returns null for non-error events', () {
      const raw = 'event: done\ndata: {}\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.errorMessage, isNull);
    });

    test('equality works correctly', () {
      const a = SseEvent(type: 'done', data: {});
      const b = SseEvent(type: 'done', data: {});

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('inequality for different types', () {
      const a = SseEvent(type: 'done', data: {});
      const b = SseEvent(type: 'error', data: {});

      expect(a, isNot(equals(b)));
    });

    test('toString provides readable output', () {
      const event = SseEvent(type: 'intent', data: {'key': 'value'});

      expect(event.toString(), contains('intent'));
      expect(event.toString(), contains('key'));
    });
  });

  group('SseEventType', () {
    test('all event types are defined', () {
      expect(SseEventType.intent, 'intent');
      expect(SseEventType.content, 'content');
      expect(SseEventType.created, 'created');
      expect(SseEventType.updated, 'updated');
      expect(SseEventType.deleted, 'deleted');
      expect(SseEventType.confirm, 'confirm');
      expect(SseEventType.results, 'results');
      expect(SseEventType.done, 'done');
      expect(SseEventType.error, 'error');
    });
  });

  group('SseEvent error handling', () {
    test('error event triggers error state correctly', () {
      const raw = 'event: error\ndata: {"message":"连接超时"}\n\n';

      final event = SseEvent.fromRaw(raw);

      expect(event.isError, isTrue);
      expect(event.isDone, isFalse);
      expect(event.errorMessage, '连接超时');
    });
  });
}
