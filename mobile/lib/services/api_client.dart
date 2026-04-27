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

  // ---- Explore API Methods ----

  /// 获取条目列表（支持过滤参数）
  /// [type] 条目类型：inbox/task/note/project
  /// [status] 状态过滤
  /// [tags] 标签过滤
  /// [startDate] 起始日期 (ISO 格式)
  /// [endDate] 结束日期 (ISO 格式)
  /// [limit] 分页大小
  /// [offset] 分页偏移
  Future<Response<T>> fetchEntries<T>({
    String? type,
    String? status,
    String? tags,
    String? startDate,
    String? endDate,
    int? limit,
    int? offset,
  }) {
    final queryParams = <String, dynamic>{};
    if (type != null) queryParams['type'] = type;
    if (status != null) queryParams['status'] = status;
    if (tags != null) queryParams['tags'] = tags;
    if (startDate != null) queryParams['start_date'] = startDate;
    if (endDate != null) queryParams['end_date'] = endDate;
    if (limit != null) queryParams['limit'] = limit;
    if (offset != null) queryParams['offset'] = offset;

    return _dio.get<T>(
      '/entries',
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );
  }

  /// 全文搜索条目
  Future<Response<T>> searchEntries<T>({
    required String query,
    int? limit,
  }) {
    final queryParams = <String, dynamic>{
      'q': query,
    };
    if (limit != null) queryParams['limit'] = limit;

    return _dio.get<T>(
      '/entries/search/query',
      queryParameters: queryParams,
    );
  }

  /// 删除条目
  Future<Response<T>> deleteEntry<T>({required String id}) {
    return _dio.delete<T>('/entries/$id');
  }

  /// 更新条目分类
  Future<Response<T>> updateEntryCategory<T>({
    required String id,
    required String category,
  }) {
    return _dio.put<T>(
      '/entries/$id',
      data: {'category': category},
    );
  }

  // ---- Entries API Methods ----

  /// 创建条目
  /// [data] 条目数据（title, content, category, tags 等）
  Future<Response<T>> createEntry<T>({required Map<String, dynamic> data}) {
    return _dio.post<T>('/entries', data: data);
  }

  // ---- Goals API Methods ----

  /// 获取目标列表
  /// [status] 按状态过滤: active/completed/abandoned
  /// [limit] 每页数量
  Future<Response<T>> fetchGoals<T>({
    String? status,
    int? limit,
  }) {
    final queryParams = <String, dynamic>{};
    if (status != null) queryParams['status'] = status;
    if (limit != null) queryParams['limit'] = limit;

    return _dio.get<T>(
      '/goals',
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );
  }

  /// 获取目标详情
  /// [id] 目标 ID
  Future<Response<T>> fetchGoal<T>({required String id}) {
    return _dio.get<T>('/goals/$id');
  }

  /// 获取目标下的里程碑列表
  /// [goalId] 目标 ID
  Future<Response<T>> fetchMilestones<T>({required String goalId}) {
    return _dio.get<T>('/goals/$goalId/milestones');
  }

  /// 创建里程碑
  /// [goalId] 目标 ID
  /// [data] 里程碑数据（title, due_date, description 等）
  Future<Response<T>> createMilestone<T>({
    required String goalId,
    required Map<String, dynamic> data,
  }) {
    return _dio.post<T>('/goals/$goalId/milestones', data: data);
  }

  /// 更新里程碑
  /// [goalId] 目标 ID
  /// [milestoneId] 里程碑 ID
  /// [data] 更新数据（title, status, due_date 等）
  Future<Response<T>> updateMilestone<T>({
    required String goalId,
    required String milestoneId,
    required Map<String, dynamic> data,
  }) {
    return _dio.put<T>('/goals/$goalId/milestones/$milestoneId', data: data);
  }

  /// 删除里程碑
  /// [goalId] 目标 ID
  /// [milestoneId] 里程碑 ID
  Future<Response<T>> deleteMilestone<T>({
    required String goalId,
    required String milestoneId,
  }) {
    return _dio.delete<T>('/goals/$goalId/milestones/$milestoneId');
  }

  // ---- Review API Methods ----

  /// 获取回顾报告（日报/周报/月报）
  /// [period] 统计周期: daily/weekly/monthly，默认 weekly
  /// [date] 日期参数（daily 时为 YYYY-MM-DD，weekly 时为 start_date，monthly 时为 YYYY-MM）
  Future<Response<T>> fetchReviewSummary<T>({
    String? period,
    String? date,
  }) {
    // 根据周期选择不同端点
    final path = switch (period) {
      'daily' => '/review/daily',
      'monthly' => '/review/monthly',
      _ => '/review/weekly',
    };

    final queryParams = <String, dynamic>{};
    if (date != null) {
      if (period == 'monthly') {
        queryParams['month'] = date;
      } else if (period == 'daily') {
        queryParams['date'] = date;
      } else {
        queryParams['start_date'] = date;
      }
    }

    return _dio.get<T>(
      path,
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );
  }

  /// 获取趋势数据
  /// [period] 统计周期: daily 或 weekly
  /// [days] daily 模式天数
  /// [weeks] weekly 模式周数
  Future<Response<T>> fetchTrends<T>({
    String? period,
    int? days,
    int? weeks,
  }) {
    final queryParams = <String, dynamic>{};
    if (period != null) queryParams['period'] = period;
    if (days != null) queryParams['days'] = days;
    if (weeks != null) queryParams['weeks'] = weeks;

    return _dio.get<T>(
      '/review/trend',
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );
  }

  /// 获取 AI 深度洞察
  /// [period] 统计周期: weekly 或 monthly（必填）
  Future<Response<T>> fetchInsights<T>({required String period}) {
    return _dio.get<T>(
      '/review/insights',
      queryParameters: {'period': period},
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
