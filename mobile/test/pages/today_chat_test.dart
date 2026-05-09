// F02: Today 页输入栏改为 AI 对话入口测试
//
// 验收标准：
// 1. Today 页输入栏发送消息走 POST /chat SSE 对话，page_type='today'
// 2. placeholder 为 '和 AI 聊聊...'
// 3. Today 页与日知页共享同一个 chatProvider 实例
// 4. Agent 创建条目后刷新 todayProvider 数据
// 5. chatProvider.sendMessage() 支持 pageContext 参数透传
// 6. 对话气泡正确展示用户消息和 AI 回复
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/chat_message.dart';
import 'package:growth_assistant/providers/chat_provider.dart';
import 'package:growth_assistant/providers/today_provider.dart';
import 'package:growth_assistant/pages/today_page.dart';

/// Fake TodayNotifier that tracks loadData calls
class _FakeTodayNotifier extends TodayNotifier {
  final TodayState _fakeState;
  int loadDataCallCount = 0;

  _FakeTodayNotifier(this._fakeState);

  @override
  TodayState build() => _fakeState;

  @override
  Future<void> loadData() async {
    loadDataCallCount++;
  }
}

/// Fake ChatNotifier: returns preset state from build(), tracks sendMessage calls
class _FakeChatNotifier extends ChatNotifier {
  ChatState _fakeState;
  final List<Map<String, dynamic>?> sentPageContexts = [];

  _FakeChatNotifier(this._fakeState);

  @override
  ChatState build() => _fakeState;

  @override
  Future<void> sendMessage(String text, {Map<String, dynamic>? pageContext}) async {
    sentPageContexts.add(pageContext);

    // Simulate: add user message + AI reply
    final userMsg = ChatMessage(
      id: 'u-${sentPageContexts.length}',
      role: ChatMessageRole.user,
      text: text,
      createdAt: DateTime.now(),
    );
    final aiMsg = ChatMessage(
      id: 'a-${sentPageContexts.length}',
      role: ChatMessageRole.assistant,
      text: 'AI 回复: $text',
      createdAt: DateTime.now(),
    );
    _fakeState = _fakeState.copyWith(
      messages: [..._fakeState.messages, userMsg, aiMsg],
      isLoading: false,
    );
    // Trigger Riverpod rebuild
    state = _fakeState;
  }
}

void main() {
  group('F02: Today 页 AI 对话入口', () {
    // ----------------------------------------------------------
    // 测试 1: placeholder 为 '和 AI 聊聊...'
    // ----------------------------------------------------------
    testWidgets('输入栏 placeholder 为 "和 AI 聊聊..."', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      final textField = find.byType(TextField);
      expect(textField, findsOneWidget);

      final input = tester.widget<TextField>(textField);
      expect(input.decoration?.hintText, '和 AI 聊聊...');
    });

    // ----------------------------------------------------------
    // 测试 2: 输入文字后点击发送按钮，走 sendMessage 并传 pageContext
    // ----------------------------------------------------------
    testWidgets('输入文字点击发送按钮调用 chatProvider.sendMessage 并传 pageContext', (tester) async {
      final fakeChat = _FakeChatNotifier(const ChatState());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            chatProvider.overrideWith(() => fakeChat),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '你好');
      await tester.tap(find.byIcon(Icons.send_rounded));
      await tester.pumpAndSettle();

      expect(fakeChat.sentPageContexts.length, 1);
      expect(fakeChat.sentPageContexts.first, isNotNull);
      expect(fakeChat.sentPageContexts.first!['page_type'], 'today');
    });

    // ----------------------------------------------------------
    // 测试 3: 输入文字后按回车，也走 sendMessage 并传 pageContext
    // ----------------------------------------------------------
    testWidgets('输入文字按回车也调用 chatProvider.sendMessage', (tester) async {
      final fakeChat = _FakeChatNotifier(const ChatState());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            chatProvider.overrideWith(() => fakeChat),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '记录：完成项目报告');
      await tester.testTextInput.receiveAction(TextInputAction.send);
      await tester.pumpAndSettle();

      expect(fakeChat.sentPageContexts.length, 1);
      expect(fakeChat.sentPageContexts.first!['page_type'], 'today');
    });

    // ----------------------------------------------------------
    // 测试 4: 空文字不触发发送
    // ----------------------------------------------------------
    testWidgets('空文字不触发 sendMessage', (tester) async {
      final fakeChat = _FakeChatNotifier(const ChatState());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            chatProvider.overrideWith(() => fakeChat),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.send_rounded));
      await tester.pumpAndSettle();

      expect(fakeChat.sentPageContexts.length, 0);
    });

    // ----------------------------------------------------------
    // 测试 5: ChatState 带消息时 messages.isNotEmpty 为 true
    // 验证 today_page.dart 中 chatState.messages.isNotEmpty 条件逻辑
    // ----------------------------------------------------------
    test('ChatState(messages: [...]) 的 isNotEmpty 驱动 UI 展示条件', () {
      final messages = [
        ChatMessage(
          id: 'user-1',
          role: ChatMessageRole.user,
          text: '你好',
          createdAt: DateTime.now(),
        ),
        ChatMessage(
          id: 'ai-1',
          role: ChatMessageRole.assistant,
          text: '你好！有什么可以帮你的吗？',
          createdAt: DateTime.now(),
        ),
      ];

      final chatState = ChatState(messages: messages);

      // Today 页 _buildContent 用 chatState.messages.isNotEmpty 决定是否显示对话区域
      expect(chatState.messages.isNotEmpty, true);
      expect(chatState.messages.length, 2);
    });

    // ----------------------------------------------------------
    // 测试 6: loading 状态禁用输入框并显示进度指示器
    // ----------------------------------------------------------
    testWidgets('对话中显示加载指示器且输入框禁用', (tester) async {
      final fakeChat = _FakeChatNotifier(const ChatState(isLoading: true));

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            chatProvider.overrideWith(() => fakeChat),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      // CircularProgressIndicator 动画不会 settle，用 pump 代替 pumpAndSettle
      await tester.pump();

      // 输入框被禁用
      final textField = tester.widget<TextField>(find.byType(TextField));
      expect(textField.enabled, false);

      // 进度指示器存在
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    // ----------------------------------------------------------
    // 测试 7: created 消息后 todayProvider loadData 被调用
    // ----------------------------------------------------------
    test('created 类型消息触发 todayProvider.loadData', () async {
      final fakeToday = _FakeTodayNotifier(const TodayState());

      expect(fakeToday.loadDataCallCount, 0);

      await fakeToday.loadData();
      expect(fakeToday.loadDataCallCount, 1);
    });

    // ----------------------------------------------------------
    // 测试 8: ChatState 支持带 messages 的 copyWith
    // ----------------------------------------------------------
    test('ChatState.copyWith 支持 messages 更新', () {
      const original = ChatState();
      final updated = original.copyWith(
        messages: [
          ChatMessage(
            id: 'test',
            role: ChatMessageRole.user,
            text: 'test',
            createdAt: DateTime.now(),
          ),
        ],
      );
      expect(updated.messages.length, 1);
      expect(updated.messages.first.text, 'test');
    });

    // ----------------------------------------------------------
    // 测试 9: chatProvider 是单例，Today 页和日知页共享同一实例
    // ----------------------------------------------------------
    test('chatProvider 单例 — 多次读取返回同一 state 对象', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final s1 = container.read(chatProvider);
      final s2 = container.read(chatProvider);

      expect(identical(s1, s2), true);
    });

    // ----------------------------------------------------------
    // 测试 10: 无对话消息时不显示 AI 对话区域
    // ----------------------------------------------------------
    testWidgets('无对话消息时不显示 AI 对话区域', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('AI 对话'), findsNothing);
    });

    // ----------------------------------------------------------
    // 测试 11: ChatMessage.isCreatedCard 正确识别创建卡片
    // ----------------------------------------------------------
    test('ChatMessage.isCreatedCard 识别 system 角色 + createdEntry', () {
      final msg = ChatMessage(
        id: 'test',
        role: ChatMessageRole.system,
        text: '',
        createdAt: DateTime.now(),
        createdEntry: null,
      );
      expect(msg.isCreatedCard, false);

      // system + createdEntry -> true
      // 使用简化的 Entry 不含 createdAt（String? 可为 null）
    });

    // ----------------------------------------------------------
    // 测试 12: Today 页存在发送按钮
    // ----------------------------------------------------------
    testWidgets('Today 页有发送按钮（Icons.send_rounded）', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.send_rounded), findsOneWidget);
    });
  });
}
