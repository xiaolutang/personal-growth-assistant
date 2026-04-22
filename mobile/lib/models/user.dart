// ============================================================
// User - 用户模型
// ============================================================
class User {
  final String id;
  final String username;
  final String? email;
  final bool isActive;
  final bool? onboardingCompleted;
  final String? createdAt;

  const User({
    required this.id,
    required this.username,
    this.email,
    this.isActive = true,
    this.onboardingCompleted,
    this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as String,
      username: json['username'] as String,
      email: json['email'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      onboardingCompleted: json['onboarding_completed'] as bool?,
      createdAt: json['created_at'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'email': email,
      'is_active': isActive,
      'onboarding_completed': onboardingCompleted,
      'created_at': createdAt,
    };
  }
}

// ============================================================
// AuthResult - 认证结果
// ============================================================
class AuthResult {
  final String token;
  final String tokenType;
  final int? expiresIn;
  final User user;

  const AuthResult({
    required this.token,
    this.tokenType = 'bearer',
    this.expiresIn,
    required this.user,
  });

  factory AuthResult.fromJson(Map<String, dynamic> json) {
    return AuthResult(
      token: json['access_token'] as String,
      tokenType: json['token_type'] as String? ?? 'bearer',
      expiresIn: json['expires_in'] as int?,
      user: User.fromJson(json['user'] as Map<String, dynamic>),
    );
  }
}
