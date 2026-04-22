import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/config/api_config.dart';
import 'package:growth_assistant/models/user.dart';
import 'package:growth_assistant/providers/auth_provider.dart';
import 'package:growth_assistant/services/api_client.dart';
import 'package:growth_assistant/services/auth_service.dart';
import 'package:mocktail/mocktail.dart';

class MockSecureStorage extends Mock implements FlutterSecureStorage {}

class MockApiClient extends Mock implements ApiClient {}

class MockAuthService extends Mock implements AuthService {}

void main() {
  group('AuthState', () {
    test('AuthAuthenticated holds user, token and sessionId', () {
      const state = AuthAuthenticated(
        user: User(id: 'user-1', username: 'test'),
        token: 'jwt-token',
        sessionId: 'session-1',
      );

      expect(state.user.id, 'user-1');
      expect(state.user.username, 'test');
      expect(state.token, 'jwt-token');
      expect(state.sessionId, 'session-1');
    });

    test('AuthUnauthenticated is const', () {
      const state = AuthUnauthenticated();
      expect(state, isA<AuthUnauthenticated>());
    });

    test('AuthLoading is const', () {
      const state = AuthLoading();
      expect(state, isA<AuthLoading>());
    });
  });

  group('AuthResult', () {
    test('fromJson parses login response correctly', () {
      final json = {
        'access_token': 'test-token',
        'token_type': 'bearer',
        'expires_in': 86400,
        'user': {
          'id': 'user-1',
          'username': 'testuser',
          'email': 'test@example.com',
          'is_active': true,
          'onboarding_completed': false,
          'created_at': '2024-01-01T00:00:00',
        },
      };

      final result = AuthResult.fromJson(json);

      expect(result.token, 'test-token');
      expect(result.tokenType, 'bearer');
      expect(result.expiresIn, 86400);
      expect(result.user.id, 'user-1');
      expect(result.user.username, 'testuser');
      expect(result.user.email, 'test@example.com');
      expect(result.user.isActive, true);
      expect(result.user.onboardingCompleted, false);
    });
  });

  group('User', () {
    test('fromJson parses user data', () {
      final json = {
        'id': 'user-123',
        'username': 'john',
        'email': null,
        'is_active': true,
        'onboarding_completed': true,
        'created_at': '2024-06-01T12:00:00',
      };

      final user = User.fromJson(json);

      expect(user.id, 'user-123');
      expect(user.username, 'john');
      expect(user.email, isNull);
      expect(user.isActive, true);
      expect(user.onboardingCompleted, true);
    });

    test('toJson produces correct map', () {
      const user = User(id: 'user-1', username: 'test', isActive: true);

      final json = user.toJson();

      expect(json['id'], 'user-1');
      expect(json['username'], 'test');
      expect(json['is_active'], true);
    });

    test('default isActive is true', () {
      const user = User(id: 'u', username: 'n');
      expect(user.isActive, true);
    });
  });

  group('ApiConfig', () {
    test('has correct storage keys', () {
      expect(ApiConfig.keyJwtToken, 'jwt_token');
      expect(ApiConfig.keyUserId, 'user_id');
      expect(ApiConfig.keyUsername, 'username');
      expect(ApiConfig.keySessionId, 'session_id');
    });

    test('has correct timeouts', () {
      expect(ApiConfig.connectTimeout, 30000);
      expect(ApiConfig.receiveTimeout, 60000);
    });

    test('has default baseUrl', () {
      expect(ApiConfig.baseUrl, isNotEmpty);
    });
  });

  group('ApiClient.errorMessage', () {
    test('connection timeout returns timeout message', () {
      final error = DioException(
        type: DioExceptionType.connectionTimeout,
        requestOptions: RequestOptions(path: '/test'),
      );
      expect(ApiClient.errorMessage(error), contains('超时'));
    });

    test('connection error returns network message', () {
      final error = DioException(
        type: DioExceptionType.connectionError,
        requestOptions: RequestOptions(path: '/test'),
      );
      expect(ApiClient.errorMessage(error), contains('网络'));
    });

    test('401 with detail returns detail', () {
      final error = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 401,
          data: {'detail': '用户名或密码错误'},
          requestOptions: RequestOptions(path: '/auth/login'),
        ),
        requestOptions: RequestOptions(path: '/auth/login'),
      );
      expect(ApiClient.errorMessage(error), '用户名或密码错误');
    });

    test('500 returns server error message', () {
      final error = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 500,
          data: null,
          requestOptions: RequestOptions(path: '/test'),
        ),
        requestOptions: RequestOptions(path: '/test'),
      );
      expect(ApiClient.errorMessage(error), contains('服务器'));
    });

    test('cancel returns cancel message', () {
      final error = DioException(
        type: DioExceptionType.cancel,
        requestOptions: RequestOptions(path: '/test'),
      );
      expect(ApiClient.errorMessage(error), contains('取消'));
    });

    test('unknown error returns generic message', () {
      expect(ApiClient.errorMessage(Exception('oops')), contains('未知错误'));
    });
  });
}
