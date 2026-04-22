import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config/api_config.dart';
import '../models/user.dart';
import 'api_client.dart';

// ============================================================
// AuthService - 认证服务
//
// 负责：登录、注册、获取当前用户、token 存储
// 不持有状态，所有状态由 Provider 管理
// ============================================================

class AuthService {
  final ApiClient _apiClient;
  final FlutterSecureStorage _storage;

  AuthService({
    required ApiClient apiClient,
    FlutterSecureStorage? storage,
  })  : _apiClient = apiClient,
        _storage = storage ?? const FlutterSecureStorage();

  /// 登录：POST /auth/login
  Future<AuthResult> login({
    required String username,
    required String password,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/auth/login',
      data: {
        'username': username,
        'password': password,
      },
    );

    final authResult = AuthResult.fromJson(response.data!);

    // 持久化 token 和用户信息
    await _saveAuthData(authResult);

    return authResult;
  }

  /// 注册：POST /auth/register
  Future<User> register({
    required String username,
    required String password,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/auth/register',
      data: {
        'username': username,
        'password': password,
      },
    );

    return User.fromJson(response.data!);
  }

  /// 获取当前用户：GET /auth/me
  Future<User> getCurrentUser() async {
    final response = await _apiClient.get<Map<String, dynamic>>('/auth/me');
    return User.fromJson(response.data!);
  }

  /// 登出：清除本地存储
  Future<void> logout() async {
    try {
      await _apiClient.post('/auth/logout');
    } catch (_) {
      // 登出 API 失败不影响本地清除
    }
    await _clearAuthData();
  }

  /// 从本地存储读取 token
  Future<String?> getStoredToken() async {
    return _storage.read(key: ApiConfig.keyJwtToken);
  }

  /// 从本地存储读取用户信息
  Future<User?> getStoredUser() async {
    final userId = await _storage.read(key: ApiConfig.keyUserId);
    final username = await _storage.read(key: ApiConfig.keyUsername);

    if (userId == null || username == null) return null;

    return User(id: userId, username: username);
  }

  /// 验证存储的 token 是否有效
  Future<User?> validateStoredToken() async {
    final token = await getStoredToken();
    if (token == null || token.isEmpty) return null;

    try {
      return await getCurrentUser();
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        await _clearAuthData();
        return null;
      }
      rethrow;
    }
  }

  /// 存储会话 ID
  Future<void> saveSessionId(String sessionId) async {
    await _storage.write(key: ApiConfig.keySessionId, value: sessionId);
  }

  /// 读取会话 ID
  Future<String?> getSessionId() async {
    return _storage.read(key: ApiConfig.keySessionId);
  }

  // ---- Private ----

  Future<void> _saveAuthData(AuthResult authResult) async {
    await _storage.write(
      key: ApiConfig.keyJwtToken,
      value: authResult.token,
    );
    await _storage.write(
      key: ApiConfig.keyUserId,
      value: authResult.user.id,
    );
    await _storage.write(
      key: ApiConfig.keyUsername,
      value: authResult.user.username,
    );
  }

  Future<void> _clearAuthData() async {
    await _storage.delete(key: ApiConfig.keyJwtToken);
    await _storage.delete(key: ApiConfig.keyUserId);
    await _storage.delete(key: ApiConfig.keyUsername);
  }
}
