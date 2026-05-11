import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:rizhi/models/sse_event.dart';
import 'package:rizhi/services/sse_service.dart';

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

  group('SseService.parseSseChunks — streaming event parsing', () {
    test('parses created event with entry id', () {
      final buffer = StringBuffer();
      final chunk = utf8.encode(
        'event: created\n'
        'data: {"id":"e1","title":"报告"}\n\n',
      );

      final events = SseService.parseSseChunks(buffer, chunk);

      expect(events, hasLength(1));
      expect(events[0].type, 'created');
      expect(events[0].data['id'], 'e1');
    });

    test('parses updated event', () {
      final buffer = StringBuffer();
      final chunk = utf8.encode(
        'event: updated\n'
        'data: {"id":"e2"}\n\n',
      );

      final events = SseService.parseSseChunks(buffer, chunk);

      expect(events, hasLength(1));
      expect(events[0].type, 'updated');
    });

    test('parses content event', () {
      final buffer = StringBuffer();
      final chunk = utf8.encode(
        'event: content\n'
        'data: {"content":"本周进展良好"}\n\n',
      );

      final events = SseService.parseSseChunks(buffer, chunk);

      expect(events, hasLength(1));
      expect(events[0].type, 'content');
      expect(events[0].contentText, '本周进展良好');
    });

    test('parses redirect event', () {
      final buffer = StringBuffer();
      final chunk = utf8.encode(
        'event: redirect\n'
        'data: {"reason":"conversational","target":"chat"}\n\n',
      );

      final events = SseService.parseSseChunks(buffer, chunk);

      expect(events, hasLength(1));
      expect(events[0].type, 'redirect');
      expect(events[0].data['reason'], 'conversational');
      expect(events[0].data['target'], 'chat');
    });

    test('parses done event', () {
      final buffer = StringBuffer();
      final chunk = utf8.encode('event: done\ndata: {}\n\n');

      final events = SseService.parseSseChunks(buffer, chunk);

      expect(events, hasLength(1));
      expect(events[0].isDone, true);
    });

    test('parses error event', () {
      final buffer = StringBuffer();
      final chunk = utf8.encode(
        'event: error\n'
        'data: {"message":"服务不可用"}\n\n',
      );

      final events = SseService.parseSseChunks(buffer, chunk);

      expect(events, hasLength(1));
      expect(events[0].isError, true);
      expect(events[0].errorMessage, '服务不可用');
    });

    test('full lifecycle: content + done', () {
      final buffer = StringBuffer();
      final chunk = utf8.encode(
        'event: content\n'
        'data: {"content":"hello"}\n\n'
        'event: done\n'
        'data: {}\n\n',
      );

      final events = SseService.parseSseChunks(buffer, chunk);

      expect(events, hasLength(2));
      expect(events[0].type, 'content');
      expect(events[1].isDone, true);
    });

    test('buffers incomplete event across chunks', () {
      final buffer = StringBuffer();
      final chunk1 = utf8.encode('event: content\ndata: {"content":"hel');
      final chunk2 = utf8.encode('lo"}\n\n');

      final events1 = SseService.parseSseChunks(buffer, chunk1);
      expect(events1, isEmpty);

      final events2 = SseService.parseSseChunks(buffer, chunk2);
      expect(events2, hasLength(1));
      expect(events2[0].contentText, 'hello');
    });

    test('handles malformed JSON as raw data', () {
      final buffer = StringBuffer();
      final chunk = utf8.encode(
        'event: content\n'
        'data: {invalid json}\n\n',
      );

      final events = SseService.parseSseChunks(buffer, chunk);

      expect(events, hasLength(1));
      expect(events[0].data['raw'], '{invalid json}');
      expect(events[0].contentText, isNull);
    });

    test('skips empty blocks', () {
      final buffer = StringBuffer();
      final chunk = utf8.encode('\n\n\n\n');

      final events = SseService.parseSseChunks(buffer, chunk);

      expect(events, isEmpty);
    });
  });
}
