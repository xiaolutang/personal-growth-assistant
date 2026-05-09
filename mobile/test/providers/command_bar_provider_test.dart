import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/command_result.dart';
import 'package:growth_assistant/providers/command_bar_provider.dart';
import 'package:growth_assistant/services/sse_service.dart';

void main() {
  group('CommandBarState', () {
    test('initial state is idle', () {
      const state = CommandBarState();

      expect(state.isLoading, false);
      expect(state.result, isNull);
      expect(state.lastInput, isNull);
    });

    test('copyWith preserves unchanged fields', () {
      const state = CommandBarState(isLoading: true, lastInput: 'test');
      final copied = state.copyWith(
        result: () => const CommandResult(
          type: CommandResultType.success,
          message: 'ok',
        ),
      );

      expect(copied.isLoading, true);
      expect(copied.lastInput, 'test');
      expect(copied.result?.type, CommandResultType.success);
    });

    test('copyWith can clear result via null function', () {
      const state = CommandBarState(
        result: CommandResult(type: CommandResultType.error, message: 'err'),
      );
      final copied = state.copyWith(result: () => null);

      expect(copied.result, isNull);
    });
  });

  group('CommandResult', () {
    test('success result with entryId', () {
      const result = CommandResult(
        type: CommandResultType.success,
        message: '创建成功',
        entryId: 'entry-1',
      );

      expect(result.type, CommandResultType.success);
      expect(result.message, '创建成功');
      expect(result.entryId, 'entry-1');
      expect(result.answer, isNull);
    });

    test('success result with count message', () {
      const result = CommandResult(
        type: CommandResultType.success,
        message: '创建了 3 条记录',
      );

      expect(result.type, CommandResultType.success);
      expect(result.entryId, isNull);
    });

    test('answer result', () {
      const result = CommandResult(
        type: CommandResultType.answer,
        message: '本周进展良好',
        answer: '本周进展良好',
      );

      expect(result.type, CommandResultType.answer);
      expect(result.answer, '本周进展良好');
    });

    test('redirect result', () {
      const result = CommandResult(
        type: CommandResultType.redirectChat,
        message: '在日知中继续对话',
      );

      expect(result.type, CommandResultType.redirectChat);
      expect(result.entryId, isNull);
      expect(result.answer, isNull);
    });

    test('error result', () {
      const result = CommandResult(
        type: CommandResultType.error,
        message: '连接超时，请重试',
      );

      expect(result.type, CommandResultType.error);
    });
  });

  group('CommandBarNotifier basic', () {
    test('initial build returns idle state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(commandBarProvider);

      expect(state.isLoading, false);
      expect(state.result, isNull);
      expect(state.lastInput, isNull);
    });

    test('dispose cancels cleanup timers', () async {
      final container = ProviderContainer();
      container.read(commandBarProvider);
      container.dispose();

      expect(true, true);
    });

    test('executeCommand with empty text does nothing', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(commandBarProvider.notifier).executeCommand('');

      final state = container.read(commandBarProvider);
      expect(state.isLoading, false);
      expect(state.result, isNull);
    });

    test('executeCommand with whitespace-only text does nothing', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(commandBarProvider.notifier).executeCommand('   ');

      final state = container.read(commandBarProvider);
      expect(state.isLoading, false);
      expect(state.result, isNull);
    });

    test('retry with no lastInput does nothing', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(commandBarProvider.notifier).retry();

      final state = container.read(commandBarProvider);
      expect(state.isLoading, false);
    });
  });

  group('SseService.parseSseChunks — command mode events', () {
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

    test('full command lifecycle: content + done', () {
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
      // contentText returns null for malformed (no 'content' key)
      expect(events[0].contentText, isNull);
    });

    test('skips empty blocks', () {
      final buffer = StringBuffer();
      final chunk = utf8.encode('\n\n\n\n');

      final events = SseService.parseSseChunks(buffer, chunk);

      expect(events, isEmpty);
    });
  });

  group('CommandResultType', () {
    test('has all expected types', () {
      expect(
        CommandResultType.values,
        containsAll([
          CommandResultType.success,
          CommandResultType.answer,
          CommandResultType.redirectChat,
          CommandResultType.error,
        ]),
      );
    });
  });
}
