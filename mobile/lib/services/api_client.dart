import 'package:dio/dio.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';

import '../config/api_config.dart';

// ============================================================
// ApiClient - 基于 Dio 的 HTTP 客户端
//
// - JWT 拦截器：自动注入 Authorization header
// - 401 拦截器：清除 token 并重定向到登录页
// - 统一错误处理：DioException → 用户友好消息
// ============================================================

/// 全局 NavigatorKey，用于 401 重定向（由 routes.dart 注入）
final GlobalKey<NavigatorState> rootNavigatorKey = GlobalKey<NavigatorState>();

class ApiClient {
  late final Dio _dio;
  final FlutterSecureStorage _storage;

  /// 401 未授权回调，由 auth_provider 注册
  /// 用于正确重置内存中的认证状态（而非仅清除 storage）
  static void Function()? onUnauthorized;

  ApiClient({
    FlutterSecureStorage? storage,
    String? baseUrl,
  }) : _storage = storage ?? const FlutterSecureStorage() {
    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl ?? ApiConfig.baseUrl,
        connectTimeout: const Duration(milliseconds: ApiConfig.connectTimeout),
        receiveTimeout: const Duration(milliseconds: ApiConfig.receiveTimeout),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // JWT 拦截器：注入 Authorization header
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: _onRequest,
        onError: _onError,
      ),
    );
  }

  /// 供外部访问 Dio 实例（用于 SSE 等特殊场景）
  Dio get dio => _dio;

  // ---- HTTP Methods ----

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) {
    return _dio.get<T>(
      path,
      queryParameters: queryParameters,
      options: options,
    );
  }

  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) {
    return _dio.post<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
    );
  }

  Future<Response<T>> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) {
    return _dio.put<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
    );
  }

  Future<Response<T>> delete<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) {
    return _dio.delete<T>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: options,
    );
  }

  // ---- Interceptors ----

  /// 请求拦截：注入 JWT token
  Future<void> _onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _storage.read(key: ApiConfig.keyJwtToken);
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  /// 错误拦截：处理 401
  Future<void> _onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode == 401) {
      // 优先通过回调通知 auth_provider 正确登出
      if (onUnauthorized != null) {
        onUnauthorized!();
      } else {
        // 回调未注册时 fallback 到直接清除 storage + 导航
        await _storage.delete(key: ApiConfig.keyJwtToken);
        await _storage.delete(key: ApiConfig.keyUserId);
        await _storage.delete(key: ApiConfig.keyUsername);
        _navigateToLogin();
      }
    }
    handler.next(err);
  }

  /// 导航到登录页（使用 GoRouter）
  void _navigateToLogin() {
    try {
      final context = rootNavigatorKey.currentContext;
      if (context != null && context.mounted) {
        GoRouter.of(context).go('/login');
      }
    } catch (_) {
      // Router 未初始化时忽略
    }
  }

  // ---- 错误处理工具 ----

  /// 将 DioException 转换为用户友好的错误消息
  static String errorMessage(dynamic error) {
    if (error is DioException) {
      switch (error.type) {
        case DioExceptionType.connectionTimeout:
        case DioExceptionType.sendTimeout:
        case DioExceptionType.receiveTimeout:
          return '连接超时，请检查网络后重试';
        case DioExceptionType.connectionError:
          return '网络连接失败，请检查网络设置';
        case DioExceptionType.badResponse:
          final statusCode = error.response?.statusCode;
          final data = error.response?.data;
          if (data is Map && data['detail'] != null) {
            return data['detail'].toString();
          }
          return _httpStatusMessage(statusCode);
        case DioExceptionType.cancel:
          return '请求已取消';
        case DioExceptionType.badCertificate:
          return '证书验证失败';
        case DioExceptionType.unknown:
          return '网络异常，请稍后重试';
      }
    }
    return '未知错误，请稍后重试';
  }

  static String _httpStatusMessage(int? statusCode) {
    switch (statusCode) {
      case 400:
        return '请求参数错误';
      case 401:
        return '登录已过期，请重新登录';
      case 403:
        return '没有权限访问';
      case 404:
        return '请求的资源不存在';
      case 409:
        return '数据冲突';
      case 500:
        return '服务器内部错误';
      case 502:
        return '网关错误';
      case 503:
        return '服务暂不可用';
      default:
        return '请求失败 ($statusCode)';
    }
  }
}
