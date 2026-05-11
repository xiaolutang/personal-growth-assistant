// F02: Today 页智能命令栏测试
//
// 验收标准：
// 1. Today 页输入栏使用 commandBarProvider（不使用 chatProvider）
// 2. placeholder 为 '输入指令或问题...'
// 3. 发送按钮点击调用 commandBarProvider.executeCommand()
// 4. success 结果 → SnackBar toast + todayProvider 刷新
// 5. answer 结果 → 内联卡片展示 AI 回答，有关闭按钮
// 6. redirectChat 结果 → 展示跳转日知链接
// 7. error 结果 → 红色错误条 + 重试按钮
// 8. loading 时输入框禁用 + 进度指示器
// 9. 空输入不触发发送
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rizhi/models/command_result.dart';
import 'package:rizhi/providers/command_bar_provider.dart';
import 'package:rizhi/providers/today_provider.dart';
import 'package:rizhi/pages/today_page.dart';

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

/// Fake CommandBarNotifier: tracks executeCommand calls
class _FakeCommandBarNotifier extends CommandBarNotifier {
  CommandBarState _fakeState;
  final List<String> executedCommands = [];
  int clearResultCallCount = 0;

  _FakeCommandBarNotifier(this._fakeState);

  @override
  CommandBarState build() => _fakeState;

  @override
  void executeCommand(String text) {
    executedCommands.add(text);
  }

  @override
  void retry() {
    if (_fakeState.lastInput != null) {
      executedCommands.add(_fakeState.lastInput!);
    }
  }

  @override
  void clearResult() {
    clearResultCallCount++;
    _fakeState = CommandBarState(lastInput: _fakeState.lastInput);
    state = _fakeState;
  }
}

void main() {
  group('F02: Today 页智能命令栏', () {
    // ----------------------------------------------------------
    // 测试 1: placeholder 为 '输入指令或问题...'
    // ----------------------------------------------------------
    testWidgets('输入栏 placeholder 为 "输入指令或问题..."', (tester) async {
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
      expect(input.decoration?.hintText, '输入指令或问题...');
    });

    // ----------------------------------------------------------
    // 测试 2: 输入文字后点击发送按钮调用 executeCommand
    // ----------------------------------------------------------
    testWidgets('输入文字点击发送按钮调用 commandBarProvider.executeCommand', (tester) async {
      final fakeCommandBar = _FakeCommandBarNotifier(const CommandBarState());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            commandBarProvider.overrideWith(() => fakeCommandBar),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '完成报告');
      await tester.tap(find.byIcon(Icons.send_rounded));
      await tester.pumpAndSettle();

      expect(fakeCommandBar.executedCommands.length, 1);
      expect(fakeCommandBar.executedCommands.first, '完成报告');
    });

    // ----------------------------------------------------------
    // 测试 3: 输入文字后按回车也调用 executeCommand
    // ----------------------------------------------------------
    testWidgets('输入文字按回车也调用 commandBarProvider.executeCommand', (tester) async {
      final fakeCommandBar = _FakeCommandBarNotifier(const CommandBarState());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            commandBarProvider.overrideWith(() => fakeCommandBar),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '记录：完成项目报告');
      await tester.testTextInput.receiveAction(TextInputAction.send);
      await tester.pumpAndSettle();

      expect(fakeCommandBar.executedCommands.length, 1);
      expect(fakeCommandBar.executedCommands.first, '记录：完成项目报告');
    });

    // ----------------------------------------------------------
    // 测试 4: 空文字不触发发送
    // ----------------------------------------------------------
    testWidgets('空文字不触发 executeCommand', (tester) async {
      final fakeCommandBar = _FakeCommandBarNotifier(const CommandBarState());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            commandBarProvider.overrideWith(() => fakeCommandBar),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.send_rounded));
      await tester.pumpAndSettle();

      expect(fakeCommandBar.executedCommands.length, 0);
    });

    // ----------------------------------------------------------
    // 测试 5: loading 时输入框禁用并显示进度指示器
    // ----------------------------------------------------------
    testWidgets('loading 时输入框禁用且显示进度指示器', (tester) async {
      final fakeCommandBar = _FakeCommandBarNotifier(
        const CommandBarState(isLoading: true),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            commandBarProvider.overrideWith(() => fakeCommandBar),
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
    // 测试 6: answer 结果显示内联卡片
    // ----------------------------------------------------------
    testWidgets('answer 结果显示内联卡片有关闭按钮', (tester) async {
      final fakeCommandBar = _FakeCommandBarNotifier(
        const CommandBarState(
          isLoading: false,
          lastInput: '本周进展',
          result: CommandResult(
            type: CommandResultType.answer,
            message: '本周进展良好',
            answer: '本周进展良好',
          ),
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            commandBarProvider.overrideWith(() => fakeCommandBar),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // 内联卡片显示回答文本
      expect(find.text('本周进展良好'), findsOneWidget);
      // 有关闭按钮
      expect(find.byIcon(Icons.close), findsOneWidget);
    });

    // ----------------------------------------------------------
    // 测试 6.5: 点击 answer-card 关闭按钮清除结果
    // ----------------------------------------------------------
    testWidgets('点击 answer-card 关闭按钮调用 clearResult', (tester) async {
      final fakeCommandBar = _FakeCommandBarNotifier(
        const CommandBarState(
          isLoading: false,
          lastInput: '本周进展',
          result: CommandResult(
            type: CommandResultType.answer,
            message: '本周进展良好',
            answer: '本周进展良好',
          ),
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            commandBarProvider.overrideWith(() => fakeCommandBar),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // 验证初始有结果卡片
      expect(find.text('本周进展良好'), findsOneWidget);

      // 点击关闭按钮
      await tester.tap(find.byIcon(Icons.close));
      await tester.pumpAndSettle();

      // clearResult 被调用（_FakeCommandBarNotifier 的 clearResult 会重置 state）
      expect(fakeCommandBar.clearResultCallCount, 1);
    });

    // ----------------------------------------------------------
    // 测试 7: redirectChat 结果显示跳转日知链接
    // ----------------------------------------------------------
    testWidgets('redirectChat 结果显示跳转日知链接', (tester) async {
      final fakeCommandBar = _FakeCommandBarNotifier(
        const CommandBarState(
          isLoading: false,
          lastInput: '你好',
          result: CommandResult(
            type: CommandResultType.redirectChat,
            message: '在日知中继续对话',
          ),
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            commandBarProvider.overrideWith(() => fakeCommandBar),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // 跳转链接文本
      expect(find.text('在日知中继续对话'), findsOneWidget);
      // 箭头图标
      expect(find.byIcon(Icons.arrow_forward_ios), findsOneWidget);
      // 跳转区域可点击（至少包含一个 InkWell）
      expect(find.byType(InkWell), findsWidgets);
    });

    // ----------------------------------------------------------
    // 测试 8: error 结果显示错误条 + 重试按钮
    // ----------------------------------------------------------
    testWidgets('error 结果显示红色错误条和重试按钮', (tester) async {
      final fakeCommandBar = _FakeCommandBarNotifier(
        const CommandBarState(
          isLoading: false,
          lastInput: '完成报告',
          result: CommandResult(
            type: CommandResultType.error,
            message: '连接超时，请重试',
          ),
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            commandBarProvider.overrideWith(() => fakeCommandBar),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // 错误消息文本
      expect(find.text('连接超时，请重试'), findsOneWidget);
      // 重试按钮
      expect(find.text('重试'), findsOneWidget);
    });

    // ----------------------------------------------------------
    // 测试 9: 点击重试按钮触发 retry
    // ----------------------------------------------------------
    testWidgets('点击重试按钮触发 commandBarProvider.retry', (tester) async {
      final fakeCommandBar = _FakeCommandBarNotifier(
        const CommandBarState(
          isLoading: false,
          lastInput: '完成报告',
          result: CommandResult(
            type: CommandResultType.error,
            message: '连接超时，请重试',
          ),
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            commandBarProvider.overrideWith(() => fakeCommandBar),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('重试'));
      await tester.pumpAndSettle();

      expect(fakeCommandBar.executedCommands.length, 1);
      expect(fakeCommandBar.executedCommands.first, '完成报告');
    });

    // ----------------------------------------------------------
    // 测试 10: todayProvider.loadData 可被调用
    // ----------------------------------------------------------
    test('todayProvider.loadData 被调用', () async {
      final fakeToday = _FakeTodayNotifier(const TodayState());

      expect(fakeToday.loadDataCallCount, 0);

      await fakeToday.loadData();
      expect(fakeToday.loadDataCallCount, 1);
    });

    // ----------------------------------------------------------
    // 测试 11: Today 页不导入 chatProvider（不显示 AI 对话区域）
    // ----------------------------------------------------------
    testWidgets('不显示 AI 对话区域', (tester) async {
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

    // ----------------------------------------------------------
    // 测试 13: success 结果触发 SnackBar + todayProvider 刷新
    // ----------------------------------------------------------
    testWidgets('success 结果显示 SnackBar 并刷新 todayProvider', (tester) async {
      final fakeToday = _FakeTodayNotifier(const TodayState());

      // 先设置 loading 状态，然后模拟变为 success
      final fakeCommandBar = _FakeCommandBarNotifier(
        const CommandBarState(isLoading: true, lastInput: '完成报告'),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(() => fakeToday),
            commandBarProvider.overrideWith(() => fakeCommandBar),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pump();

      // 记录当前 loadData 调用次数
      final beforeCount = fakeToday.loadDataCallCount;

      // 模拟状态变为 success（isLoading: true → result: success）
      fakeCommandBar._fakeState = const CommandBarState(
        isLoading: false,
        lastInput: '完成报告',
        result: CommandResult(
          type: CommandResultType.success,
          message: '创建成功',
        ),
      );
      fakeCommandBar.state = fakeCommandBar._fakeState;
      // SnackBar 动画无法 settle，用 pump 代替 pumpAndSettle
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      // SnackBar 显示成功消息
      expect(find.text('创建成功'), findsOneWidget);
      // todayProvider 被刷新（至少增加 1 次）
      expect(fakeToday.loadDataCallCount, greaterThan(beforeCount));
    });

    // ----------------------------------------------------------
    // 测试 14: error 后输入框保留文本
    // ----------------------------------------------------------
    testWidgets('error 结果后输入框保留用户输入的文本', (tester) async {
      final fakeCommandBar = _FakeCommandBarNotifier(const CommandBarState());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            commandBarProvider.overrideWith(() => fakeCommandBar),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // 先输入文本（idle 状态）
      await tester.enterText(find.byType(TextField), '完成报告');

      // 模拟 loading（用户点发送）
      fakeCommandBar._fakeState = const CommandBarState(isLoading: true, lastInput: '完成报告');
      fakeCommandBar.state = fakeCommandBar._fakeState;
      await tester.pump();

      // 模拟 loading → error
      fakeCommandBar._fakeState = const CommandBarState(
        isLoading: false,
        lastInput: '完成报告',
        result: CommandResult(
          type: CommandResultType.error,
          message: '连接超时，请重试',
        ),
      );
      fakeCommandBar.state = fakeCommandBar._fakeState;
      await tester.pump();

      // 错误条显示
      expect(find.text('连接超时，请重试'), findsOneWidget);
      // 输入框文本保留
      final textField = tester.widget<TextField>(find.byType(TextField));
      expect(textField.controller?.text, '完成报告');
    });

    // ----------------------------------------------------------
    // 测试 15: success 后输入框被清空
    // ----------------------------------------------------------
    testWidgets('success 结果后输入框被清空', (tester) async {
      final fakeCommandBar = _FakeCommandBarNotifier(const CommandBarState());

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            todayProvider.overrideWith(
              () => _FakeTodayNotifier(const TodayState()),
            ),
            commandBarProvider.overrideWith(() => fakeCommandBar),
          ],
          child: const MaterialApp(home: TodayPage()),
        ),
      );
      await tester.pumpAndSettle();

      // 先输入文本（idle 状态）
      await tester.enterText(find.byType(TextField), '完成报告');

      // 模拟 loading（用户点发送）
      fakeCommandBar._fakeState = const CommandBarState(isLoading: true, lastInput: '完成报告');
      fakeCommandBar.state = fakeCommandBar._fakeState;
      await tester.pump();

      // 模拟 loading → success
      fakeCommandBar._fakeState = const CommandBarState(
        isLoading: false,
        lastInput: '完成报告',
        result: CommandResult(
          type: CommandResultType.success,
          message: '创建成功',
        ),
      );
      fakeCommandBar.state = fakeCommandBar._fakeState;
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      // 输入框被清空
      final textField = tester.widget<TextField>(find.byType(TextField));
      expect(textField.controller?.text, '');
    });
  });
}
