import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/config/api_config.dart';
import 'package:growth_assistant/services/api_client.dart';

void main() {
  group('ApiClient', () {
    test('JWT interceptor is configured', () async {
      final client = ApiClient();

      // 验证至少有自定义的 InterceptorsWrapper
      final hasWrapper = client.dio.interceptors
          .any((i) => i is InterceptorsWrapper);
      expect(hasWrapper, isTrue);
    });

    test('No token does not crash - Dio instance created successfully', () {
      final client = ApiClient();

      expect(client.dio, isNotNull);
      expect(client.dio.options.baseUrl, ApiConfig.baseUrl);
    });

    test('Dio configured with correct timeouts', () {
      final client = ApiClient();

      expect(
        client.dio.options.connectTimeout,
        const Duration(milliseconds: ApiConfig.connectTimeout),
      );
      expect(
        client.dio.options.receiveTimeout,
        const Duration(milliseconds: ApiConfig.receiveTimeout),
      );
    });

    test('Dio configured with correct headers', () {
      final client = ApiClient();

      expect(client.dio.options.headers['Content-Type'], 'application/json');
      expect(client.dio.options.headers['Accept'], 'application/json');
    });
  });

  group('ApiClient.errorMessage', () {
    test('Network timeout returns friendly error message', () {
      final timeoutError = DioException(
        type: DioExceptionType.connectionTimeout,
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(timeoutError);
      expect(message, contains('超时'));
    });

    test('Receive timeout returns friendly error message', () {
      final timeoutError = DioException(
        type: DioExceptionType.receiveTimeout,
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(timeoutError);
      expect(message, contains('超时'));
    });

    test('Connection error returns friendly error message', () {
      final connError = DioException(
        type: DioExceptionType.connectionError,
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(connError);
      expect(message, contains('网络'));
    });

    test('Send timeout returns friendly error message', () {
      final timeoutError = DioException(
        type: DioExceptionType.sendTimeout,
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(timeoutError);
      expect(message, contains('超时'));
    });

    test('Bad response with detail returns server error message', () {
      final badResponse = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 400,
          data: {'detail': '用户名或密码错误'},
          requestOptions: RequestOptions(path: '/auth/login'),
        ),
        requestOptions: RequestOptions(path: '/auth/login'),
      );

      final message = ApiClient.errorMessage(badResponse);
      expect(message, '用户名或密码错误');
    });

    test('Bad response without detail returns status message', () {
      final badResponse = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 400,
          data: null,
          requestOptions: RequestOptions(path: '/test'),
        ),
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(badResponse);
      expect(message, contains('参数'));
    });

    test('Server error returns appropriate message', () {
      final serverError = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 500,
          requestOptions: RequestOptions(path: '/test'),
        ),
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(serverError);
      expect(message, contains('服务器'));
    });

    test('502 returns gateway error', () {
      final error = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 502,
          requestOptions: RequestOptions(path: '/test'),
        ),
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(error);
      expect(message, contains('网关'));
    });

    test('503 returns service unavailable', () {
      final error = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 503,
          requestOptions: RequestOptions(path: '/test'),
        ),
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(error);
      expect(message, contains('服务'));
    });

    test('401 returns auth expired message', () {
      final error = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 401,
          data: null,
          requestOptions: RequestOptions(path: '/test'),
        ),
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(error);
      expect(message, contains('登录'));
    });

    test('403 returns permission denied', () {
      final error = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 403,
          requestOptions: RequestOptions(path: '/test'),
        ),
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(error);
      expect(message, contains('权限'));
    });

    test('404 returns not found', () {
      final error = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 404,
          requestOptions: RequestOptions(path: '/test'),
        ),
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(error);
      expect(message, contains('不存在'));
    });

    test('409 returns conflict', () {
      final error = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 409,
          requestOptions: RequestOptions(path: '/test'),
        ),
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(error);
      expect(message, contains('冲突'));
    });

    test('Cancel error returns cancel message', () {
      final cancelError = DioException(
        type: DioExceptionType.cancel,
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(cancelError);
      expect(message, contains('取消'));
    });

    test('Bad certificate returns certificate error', () {
      final error = DioException(
        type: DioExceptionType.badCertificate,
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(error);
      expect(message, contains('证书'));
    });

    test('Unknown error returns generic message', () {
      final error = DioException(
        type: DioExceptionType.unknown,
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(error);
      expect(message, contains('网络异常'));
    });

    test('Non-Dio error returns unknown error message', () {
      final message = ApiClient.errorMessage(Exception('oops'));
      expect(message, contains('未知错误'));
    });

    test('Other status code returns generic failure', () {
      final error = DioException(
        type: DioExceptionType.badResponse,
        response: Response<dynamic>(
          statusCode: 418,
          requestOptions: RequestOptions(path: '/test'),
        ),
        requestOptions: RequestOptions(path: '/test'),
      );

      final message = ApiClient.errorMessage(error);
      expect(message, contains('418'));
    });
  });
}
