// ============================================================
// ApiConfig - API 配置常量
// ============================================================
class ApiConfig {
  ApiConfig._();

  /// 后端 API 基础地址
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8001',
  );

  /// 连接超时（毫秒）
  static const int connectTimeout = 30000;

  /// 接收超时（毫秒）
  static const int receiveTimeout = 60000;

  /// Secure Storage key 常量
  static const String keyJwtToken = 'jwt_token';
  static const String keyUserId = 'user_id';
  static const String keyUsername = 'username';
  static const String keySessionId = 'session_id';
}
