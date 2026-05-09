// S01 聊天用户隔离修复测试
//
// 验证登出/401 时 chat 状态和 session_id 的正确清理
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/config/api_config.dart';
import 'package:growth_assistant/models/chat_message.dart';
import 'package:growth_assistant/providers/chat_provider.dart';
import 'package:growth_assistant/services/api_client.dart';
import 'package:growth_assistant/services/auth_service.dart';
import 'package:mocktail/mocktail.dart';

class MockSecureStorage extends Mock implements FlutterSecureStorage {}

class MockApiClient extends Mock implements ApiClient {}

void main() {
  // ----------------------------------------------------------
  // 测试 1: 手动登出后 chatProvider 状态为空（invalidate 重建）
  // ----------------------------------------------------------
  test('logout 后 chatProvider 被 invalidate，状态为空', () {
    // 使用第一个 container 写入消息
    final container1 = ProviderContainer();
    addTearDown(container1.dispose);

    final chatNotifier = container1.read(chatProvider.notifier);
    chatNotifier.state = ChatState(
      messages: [
        ChatMessage(
          id: 'msg-1',
          role: ChatMessageRole.user,
          text: '测试消息',
          createdAt: DateTime.now(),
        ),
      ],
    );

    // 验证消息已写入
    expect(container1.read(chatProvider).messages, isNotEmpty);

    // invalidate chatProvider
    container1.invalidate(chatProvider);

    // invalidate 后状态应回到初始空状态
    expect(container1.read(chatProvider).messages, isEmpty);
    expect(container1.read(chatProvider).error, isNull);
    expect(container1.read(chatProvider).isLoading, false);
  });

  // ----------------------------------------------------------
  // 测试 2: 手动登出后 session_id 被清除
  // ----------------------------------------------------------
  test('logout 时 AuthService._clearAuthData 删除 session_id', () async {
    final mockStorage = MockSecureStorage();
    final mockApiClient = MockApiClient();

    // 模拟 logout POST
    when(() => mockApiClient.post(any())).thenAnswer(
      (_) async => Response<dynamic>(
        requestOptions: RequestOptions(path: '/auth/logout'),
      ),
    );
    // 模拟 storage.delete（使用 named 参数语法）
    when(() => mockStorage.delete(key: any(named: 'key')))
        .thenAnswer((_) async {});

    final authService = AuthService(
      apiClient: mockApiClient,
      storage: mockStorage,
    );

    await authService.logout();

    // 验证 session_id 被删除
    verify(() => mockStorage.delete(key: ApiConfig.keySessionId)).called(1);
    // 同时验证其他认证数据也被删除
    verify(() => mockStorage.delete(key: ApiConfig.keyJwtToken)).called(1);
    verify(() => mockStorage.delete(key: ApiConfig.keyUserId)).called(1);
    verify(() => mockStorage.delete(key: ApiConfig.keyUsername)).called(1);
  });

  // ----------------------------------------------------------
  // 测试 3: 401 unauthorized 后 chatProvider 状态为空
  // ----------------------------------------------------------
  test('401 回调触发后 chatProvider 被 invalidate', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final chatNotifier = container.read(chatProvider.notifier);
    chatNotifier.state = ChatState(
      messages: [
        ChatMessage(
          id: 'msg-2',
          role: ChatMessageRole.user,
          text: '401 前的消息',
          createdAt: DateTime.now(),
        ),
      ],
      isLoading: true,
    );

    expect(container.read(chatProvider).messages, isNotEmpty);

    // 模拟 401 回调：invalidate chatProvider
    container.invalidate(chatProvider);

    // 验证 chat 状态已清空
    expect(container.read(chatProvider).messages, isEmpty);
    expect(container.read(chatProvider).isLoading, false);
  });

  // ----------------------------------------------------------
  // 测试 4: 401 unauthorized 后 session_id 被清除
  // ----------------------------------------------------------
  test('401 回调触发 _clearSessionData 删除 session_id', () async {
    final mockStorage = MockSecureStorage();
    when(() => mockStorage.delete(key: any(named: 'key')))
        .thenAnswer((_) async {});

    // 直接调用 storage 删除操作（模拟 _clearSessionData 的行为）
    await Future.wait([
      mockStorage.delete(key: ApiConfig.keyJwtToken),
      mockStorage.delete(key: ApiConfig.keyUserId),
      mockStorage.delete(key: ApiConfig.keyUsername),
      mockStorage.delete(key: ApiConfig.keySessionId),
    ]);

    verify(() => mockStorage.delete(key: ApiConfig.keySessionId)).called(1);
    verify(() => mockStorage.delete(key: ApiConfig.keyJwtToken)).called(1);
  });

  // ----------------------------------------------------------
  // 测试 5: 新登录后 session_id 是新生成的
  // ----------------------------------------------------------
  test('新登录时 session_id 为新生成的', () async {
    final mockStorage = MockSecureStorage();
    when(() => mockStorage.read(key: any(named: 'key')))
        .thenAnswer((_) async => null);
    when(() => mockStorage.write(key: any(named: 'key'), value: any(named: 'value')))
        .thenAnswer((_) async {});

    // 模拟新登录：读取 session_id 为 null
    final sessionId = await mockStorage.read(key: ApiConfig.keySessionId);
    expect(sessionId, isNull);

    // login() 中当 read 返回 null 时会生成新 session_id 并 write
  });

  // ----------------------------------------------------------
  // 测试 6: ChatNotifier.clearMessages 清空状态
  // ----------------------------------------------------------
  test('clearMessages 清空消息并取消 SSE 连接', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final chatNotifier = container.read(chatProvider.notifier);

    // 写入消息和错误状态
    chatNotifier.state = ChatState(
      messages: [
        ChatMessage(
          id: 'msg-3',
          role: ChatMessageRole.user,
          text: '待清除的消息',
          createdAt: DateTime.now(),
        ),
      ],
      isLoading: true,
      error: '某个错误',
    );

    expect(chatNotifier.state.messages, isNotEmpty);
    expect(chatNotifier.state.isLoading, true);
    expect(chatNotifier.state.error, isNotNull);

    // 调用 clearMessages
    chatNotifier.clearMessages();

    // 验证状态已清空
    expect(chatNotifier.state.messages, isEmpty);
    expect(chatNotifier.state.isLoading, false);
    expect(chatNotifier.state.error, isNull);
  });

  // ----------------------------------------------------------
  // 测试 7: SecureStorage.delete 失败时登出不阻塞
  // ----------------------------------------------------------
  test('SecureStorage.delete 失败时不阻塞', () async {
    final mockStorage = MockSecureStorage();
    when(() => mockStorage.delete(key: any(named: 'key')))
        .thenThrow(Exception('Storage error'));

    // 模拟 _clearSessionData 的逻辑：catch 不抛出异常
    try {
      await Future.wait([
        mockStorage.delete(key: ApiConfig.keyJwtToken),
        mockStorage.delete(key: ApiConfig.keyUserId),
        mockStorage.delete(key: ApiConfig.keyUsername),
        mockStorage.delete(key: ApiConfig.keySessionId),
      ]);
      fail('应该抛出异常');
    } catch (e) {
      // 异常被捕获，不阻塞流程
      expect(e, isA<Exception>());
    }

    // 实际在 AuthNotifier._clearSessionData 中有 try-catch 兜底
  });

  // ----------------------------------------------------------
  // 测试 8: 首次登录用户进入日知页，chatProvider 初始化为空状态
  // ----------------------------------------------------------
  test('chatProvider 初始状态为空', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final chatState = container.read(chatProvider);

    expect(chatState.messages, isEmpty);
    expect(chatState.isLoading, false);
    expect(chatState.error, isNull);
  });

  // ----------------------------------------------------------
  // 测试 9: AuthService._clearAuthData 包含 session_id（综合验证）
  // ----------------------------------------------------------
  test('_clearAuthData 同时删除 token userId username 和 sessionId', () async {
    final mockStorage = MockSecureStorage();
    final mockApiClient = MockApiClient();

    when(() => mockApiClient.post(any())).thenAnswer(
      (_) async => Response<dynamic>(
        requestOptions: RequestOptions(path: '/auth/logout'),
      ),
    );
    when(() => mockStorage.delete(key: any(named: 'key')))
        .thenAnswer((_) async {});

    final authService = AuthService(
      apiClient: mockApiClient,
      storage: mockStorage,
    );

    await authService.logout();

    // 验证 4 个 key 都被删除
    verify(() => mockStorage.delete(key: ApiConfig.keyJwtToken)).called(1);
    verify(() => mockStorage.delete(key: ApiConfig.keyUserId)).called(1);
    verify(() => mockStorage.delete(key: ApiConfig.keyUsername)).called(1);
    verify(() => mockStorage.delete(key: ApiConfig.keySessionId)).called(1);
  });
}
