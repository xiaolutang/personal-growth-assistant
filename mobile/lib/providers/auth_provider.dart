import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';

import '../config/api_config.dart';
import '../models/user.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';

// ============================================================
// AuthState - 认证状态
// ============================================================

sealed class AuthState {
  const AuthState();
}

class AuthAuthenticated extends AuthState {
  final User user;
  final String token;
  final String sessionId;

  const AuthAuthenticated({
    required this.user,
    required this.token,
    required this.sessionId,
  });
}

class AuthUnauthenticated extends AuthState {
  const AuthUnauthenticated();
}

class AuthLoading extends AuthState {
  const AuthLoading();
}

// ============================================================
// Providers
// ============================================================

/// ApiClient 单例
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

/// AuthService 单例
final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(apiClient: ref.watch(apiClientProvider));
});

/// FlutterSecureStorage 单例
final secureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage();
});

/// 认证状态 Notifier
class AuthNotifier extends AsyncNotifier<AuthState> {
  @override
  Future<AuthState> build() async {
    // 注册 401 回调，使 api_client 能正确触发 logout
    ApiClient.onUnauthorized = _onApiUnauthorized;

    final authService = ref.watch(authServiceProvider);
    final storage = ref.watch(secureStorageProvider);

    // 检查本地存储的 token
    final token = await storage.read(key: ApiConfig.keyJwtToken);
    if (token == null || token.isEmpty) {
      return const AuthUnauthenticated();
    }

    // 验证 token 是否有效
    try {
      final user = await authService.validateStoredToken();
      if (user == null) {
        return const AuthUnauthenticated();
      }

      // 获取或创建 session_id
      var sessionId = await storage.read(key: ApiConfig.keySessionId);
      if (sessionId == null || sessionId.isEmpty) {
        sessionId = const Uuid().v4();
        await storage.write(key: ApiConfig.keySessionId, value: sessionId);
      }

      return AuthAuthenticated(
        user: user,
        token: token,
        sessionId: sessionId,
      );
    } catch (_) {
      return const AuthUnauthenticated();
    }
  }

  /// 登录
  Future<void> login({
    required String username,
    required String password,
  }) async {
    state = const AsyncLoading<AuthState>();

    try {
      final authService = ref.read(authServiceProvider);
      final storage = ref.read(secureStorageProvider);

      final authResult = await authService.login(
        username: username,
        password: password,
      );

      // 生成或获取 session_id
      var sessionId = await storage.read(key: ApiConfig.keySessionId);
      if (sessionId == null || sessionId.isEmpty) {
        sessionId = const Uuid().v4();
        await storage.write(key: ApiConfig.keySessionId, value: sessionId);
      }

      state = AsyncData<AuthState>(AuthAuthenticated(
        user: authResult.user,
        token: authResult.token,
        sessionId: sessionId,
      ),);
    } catch (e, st) {
      state = AsyncError<AuthState>(e, st);
    }
  }

  /// 登出
  Future<void> logout() async {
    try {
      final authService = ref.read(authServiceProvider);
      await authService.logout();
    } catch (_) {
      // 登出失败不影响本地状态清除
    }

    state = const AsyncData<AuthState>(AuthUnauthenticated());
  }

  /// 401 回调：清除内存状态 + storage，不调用后端 logout 接口
  void _onApiUnauthorized() {
    // 直接重置内存状态
    state = const AsyncData<AuthState>(AuthUnauthenticated());
  }

  /// 获取当前 session_id
  Future<String> getOrCreateSessionId() async {
    final storage = ref.read(secureStorageProvider);
    var sessionId = await storage.read(key: ApiConfig.keySessionId);

    if (sessionId == null || sessionId.isEmpty) {
      sessionId = const Uuid().v4();
      await storage.write(key: ApiConfig.keySessionId, value: sessionId);
    }

    return sessionId;
  }
}

/// 认证状态 Provider
final authProvider = AsyncNotifierProvider<AuthNotifier, AuthState>(() {
  return AuthNotifier();
});
