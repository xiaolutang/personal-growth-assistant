import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/config/api_config.dart';
import 'package:growth_assistant/services/api_client.dart';

/// Mock Dio HttpClientAdapter，拦截请求并返回预设响应
class _MockHttpClientAdapter implements HttpClientAdapter {
  final List<RequestMethod> _requests = [];

  /// 支持自定义状态码：key 为 'METHOD path'，value 为 _MockResponse 或 Map（默认 200）
  final Map<String, _MockResponse> _statusResponses;

  _MockHttpClientAdapter(Map<String, dynamic> responses)
      : _statusResponses = responses.map((key, value) {
          if (value is _MockResponse) {
            return MapEntry(key, value);
          }
          return MapEntry(key, _MockResponse(statusCode: 200, data: value));
        });

  /// 获取记录的请求列表
  List<RequestMethod> get requests => _requests;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    _requests.add(RequestMethod(
      method: options.method,
      path: options.path,
      data: options.data,
      queryParameters: options.queryParameters,
    ),);


    final key = '${options.method} ${options.path}';
    final mockResponse = _statusResponses[key];

    if (mockResponse != null) {
      return ResponseBody.fromString(
        jsonEncode(mockResponse.data),
        mockResponse.statusCode,
        headers: {
          'content-type': ['application/json'],
        },
      );
    }

    return ResponseBody.fromString(
      jsonEncode({'detail': 'not found'}),
      404,
      headers: {
        'content-type': ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

/// Mock 响应，支持自定义状态码
class _MockResponse {
  final int statusCode;
  final dynamic data;

  const _MockResponse({required this.statusCode, this.data});
}

/// 记录一次请求的信息
class RequestMethod {
  final String method;
  final String path;
  final dynamic data;
  final Map<String, dynamic>? queryParameters;

  RequestMethod({
    required this.method,
    required this.path,
    this.data,
    this.queryParameters,
  });
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

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

  // ============================================================
  // F165: 新增 API 方法测试
  // 使用 _MockHttpClientAdapter 拦截 Dio 请求，
  // 验证方法发出正确的 HTTP 请求（路径、方法、参数、请求体）
  // ============================================================

  group('ApiClient Business Methods', () {
    late ApiClient client;
    late _MockHttpClientAdapter adapter;

    /// 创建测试用 ApiClient，注入 mock adapter
    /// 清除拦截器以避免 FlutterSecureStorage platform channel 问题
    ApiClient createTestClient(Map<String, dynamic> responses) {
      adapter = _MockHttpClientAdapter(responses);
      final c = ApiClient(baseUrl: 'http://test-api.local');
      c.dio.httpClientAdapter = adapter;
      c.dio.interceptors.clear();
      return c;
    }

    // ---- createEntry ----

    test('createEntry sends POST /entries with correct data', () async {
      client = createTestClient({
        'POST /entries': {
          'id': 'entry-1',
          'title': 'Test Note',
          'category': 'note',
        },
      });

      final response = await client.createEntry<Map<String, dynamic>>(
        data: {
          'title': 'Test Note',
          'category': 'note',
          'content': 'Hello world',
        },
      );

      expect(response.data!['id'], 'entry-1');
      expect(response.data!['title'], 'Test Note');
      expect(adapter.requests.length, 1);
      expect(adapter.requests[0].method, 'POST');
      expect(adapter.requests[0].path, '/entries');
      expect(adapter.requests[0].data['title'], 'Test Note');
      expect(adapter.requests[0].data['category'], 'note');
    });

    // ---- fetchGoals ----

    test('fetchGoals sends GET /goals without parameters', () async {
      client = createTestClient({
        'GET /goals': {
          'goals': [
            {'id': 'g1', 'title': 'Goal 1'},
          ],
        },
      });

      final response = await client.fetchGoals<Map<String, dynamic>>();

      expect((response.data!['goals'] as List).length, 1);
      expect(adapter.requests[0].method, 'GET');
      expect(adapter.requests[0].path, '/goals');
    });

    test('fetchGoals sends GET /goals with status and limit', () async {
      client = createTestClient({
        'GET /goals': {'goals': []},
      });

      await client.fetchGoals<Map<String, dynamic>>(
        status: 'active',
        limit: 10,
      );

      expect(adapter.requests[0].queryParameters?['status'], 'active');
      expect(adapter.requests[0].queryParameters?['limit'], 10);
    });

    // ---- fetchGoal ----

    test('fetchGoal sends GET /goals/{id}', () async {
      client = createTestClient({
        'GET /goals/g-123': {
          'id': 'g-123',
          'title': 'My Goal',
          'progress': 0.5,
        },
      });

      final response = await client.fetchGoal<Map<String, dynamic>>(
        id: 'g-123',
      );

      expect(response.data!['id'], 'g-123');
      expect(adapter.requests[0].path, '/goals/g-123');
    });

    // ---- fetchMilestones ----

    test('fetchMilestones sends GET /goals/{goalId}/milestones', () async {
      client = createTestClient({
        'GET /goals/g-1/milestones': {
          'milestones': [
            {'id': 'm1', 'title': 'Milestone 1'},
          ],
        },
      });

      final response = await client.fetchMilestones<Map<String, dynamic>>(
        goalId: 'g-1',
      );

      expect((response.data!['milestones'] as List).length, 1);
      expect(adapter.requests[0].path, '/goals/g-1/milestones');
    });

    // ---- createMilestone ----

    test('createMilestone sends POST /goals/{goalId}/milestones', () async {
      client = createTestClient({
        'POST /goals/g-1/milestones': {
          'id': 'm-new',
          'title': 'New Milestone',
          'status': 'pending',
        },
      });

      final response = await client.createMilestone<Map<String, dynamic>>(
        goalId: 'g-1',
        data: {'title': 'New Milestone', 'due_date': '2025-06-01'},
      );

      expect(response.data!['id'], 'm-new');
      expect(adapter.requests[0].method, 'POST');
      expect(adapter.requests[0].path, '/goals/g-1/milestones');
      expect(adapter.requests[0].data['title'], 'New Milestone');
    });

    // ---- updateMilestone ----

    test('updateMilestone sends PUT /goals/{goalId}/milestones/{milestoneId}',
        () async {
      client = createTestClient({
        'PUT /goals/g-1/milestones/m-1': {
          'id': 'm-1',
          'title': 'Updated',
          'status': 'completed',
        },
      });

      final response = await client.updateMilestone<Map<String, dynamic>>(
        goalId: 'g-1',
        milestoneId: 'm-1',
        data: {'status': 'completed'},
      );

      expect(response.data!['status'], 'completed');
      expect(adapter.requests[0].method, 'PUT');
      expect(adapter.requests[0].path, '/goals/g-1/milestones/m-1');
    });

    // ---- deleteMilestone ----

    test('deleteMilestone sends DELETE /goals/{goalId}/milestones/{milestoneId}',
        () async {
      client = createTestClient({
        'DELETE /goals/g-1/milestones/m-1': {'message': 'deleted'},
      });

      await client.deleteMilestone<Map<String, dynamic>>(
        goalId: 'g-1',
        milestoneId: 'm-1',
      );

      expect(adapter.requests[0].method, 'DELETE');
      expect(adapter.requests[0].path, '/goals/g-1/milestones/m-1');
    });

    // ---- fetchReviewSummary ----

    test('fetchReviewSummary defaults to GET /review/weekly', () async {
      client = createTestClient({
        'GET /review/weekly': {
          'period': 'weekly',
          'total_entries': 10,
        },
      });

      final response =
          await client.fetchReviewSummary<Map<String, dynamic>>();

      expect(response.data!['period'], 'weekly');
      expect(adapter.requests[0].path, '/review/weekly');
    });

    test('fetchReviewSummary with daily period calls GET /review/daily',
        () async {
      client = createTestClient({
        'GET /review/daily': {'period': 'daily'},
      });

      await client.fetchReviewSummary<Map<String, dynamic>>(period: 'daily');

      expect(adapter.requests[0].path, '/review/daily');
    });

    test('fetchReviewSummary with monthly period calls GET /review/monthly',
        () async {
      client = createTestClient({
        'GET /review/monthly': {'period': 'monthly'},
      });

      await client.fetchReviewSummary<Map<String, dynamic>>(period: 'monthly');

      expect(adapter.requests[0].path, '/review/monthly');
    });

    test('fetchReviewSummary passes date parameter correctly for weekly',
        () async {
      client = createTestClient({
        'GET /review/weekly': {'period': 'weekly'},
      });

      await client.fetchReviewSummary<Map<String, dynamic>>(
        period: 'weekly',
        date: '2025-04-21',
      );

      expect(adapter.requests[0].queryParameters?['start_date'], '2025-04-21');
    });

    test('fetchReviewSummary passes month parameter for monthly', () async {
      client = createTestClient({
        'GET /review/monthly': {'period': 'monthly'},
      });

      await client.fetchReviewSummary<Map<String, dynamic>>(
        period: 'monthly',
        date: '2025-04',
      );

      expect(adapter.requests[0].queryParameters?['month'], '2025-04');
    });

    // ---- fetchTrends ----

    test('fetchTrends sends GET /review/trend', () async {
      client = createTestClient({
        'GET /review/trend': {
          'period': 'daily',
          'data': [],
        },
      });

      await client.fetchTrends<Map<String, dynamic>>();

      // Verify request path
      expect(adapter.requests[0].path, '/review/trend');
    });

    test('fetchTrends sends period, days and weeks parameters', () async {
      client = createTestClient({
        'GET /review/trend': {'period': 'weekly'},
      });

      await client.fetchTrends<Map<String, dynamic>>(
        period: 'weekly',
        weeks: 12,
      );

      expect(adapter.requests[0].queryParameters?['period'], 'weekly');
      expect(adapter.requests[0].queryParameters?['weeks'], 12);
    });

    // ---- fetchInsights ----

    test('fetchInsights sends GET /review/insights with period', () async {
      client = createTestClient({
        'GET /review/insights': {
          'insights': ['insight 1', 'insight 2'],
        },
      });

      final response = await client.fetchInsights<Map<String, dynamic>>(
        period: 'weekly',
      );

      expect((response.data!['insights'] as List).length, 2);
      expect(adapter.requests[0].path, '/review/insights');
      expect(adapter.requests[0].queryParameters?['period'], 'weekly');
    });

    // ---- Error scenarios ----

    test('API method throws DioException on 404', () async {
      client = createTestClient({});

      expect(
        () => client.fetchGoal<Map<String, dynamic>>(id: 'nonexistent'),
        throwsA(isA<DioException>()),
      );
    });
  });

  // ============================================================
  // F172: Entry Interaction API Methods 测试
  // 覆盖 updateEntry, fetchBacklinks, fetchEntryLinks,
  // createEntryLink, deleteEntryLink, fetchKnowledgeContext,
  // generateAISummary 及各种错误场景
  // ============================================================

  group('F172: Entry Interaction API Methods', () {
    late ApiClient client;
    late _MockHttpClientAdapter adapter;

    ApiClient createTestClient(Map<String, dynamic> responses) {
      adapter = _MockHttpClientAdapter(responses);
      final c = ApiClient(baseUrl: 'http://test-api.local');
      c.dio.httpClientAdapter = adapter;
      c.dio.interceptors.clear();
      return c;
    }

    // ---- updateEntry ----

    test('updateEntry sends PUT /entries/{id} and returns SuccessResponse',
        () async {
      client = createTestClient({
        'PUT /entries/e-1': {
          'success': true,
          'message': 'Entry updated successfully',
        },
      });

      final response = await client.updateEntry<Map<String, dynamic>>(
        id: 'e-1',
        data: {'title': 'Updated Title', 'content': 'New content'},
      );

      expect(response.data!['success'], true);
      expect(response.data!['message'], 'Entry updated successfully');
      expect(adapter.requests[0].method, 'PUT');
      expect(adapter.requests[0].path, '/entries/e-1');
      expect(adapter.requests[0].data['title'], 'Updated Title');
      expect(adapter.requests[0].data['content'], 'New content');
    });

    test('updateEntry returns 404 for nonexistent entry', () async {
      client = createTestClient({
        'PUT /entries/nonexistent': _MockResponse(
          statusCode: 404,
          data: {'detail': 'Entry not found'},
        ),
      });

      expect(
        () => client.updateEntry<Map<String, dynamic>>(
          id: 'nonexistent',
          data: {'title': 'test'},
        ),
        throwsA(isA<DioException>()),
      );
    });

    test('updateEntry returns 500 on server error', () async {
      client = createTestClient({
        'PUT /entries/e-1': _MockResponse(
          statusCode: 500,
          data: {'detail': 'Internal server error'},
        ),
      });

      expect(
        () => client.updateEntry<Map<String, dynamic>>(
          id: 'e-1',
          data: {'title': 'test'},
        ),
        throwsA(isA<DioException>()),
      );
    });

    // ---- fetchBacklinks ----

    test('fetchBacklinks sends GET /entries/{id}/backlinks', () async {
      client = createTestClient({
        'GET /entries/e-1/backlinks': {
          'backlinks': [
            {'entry_id': 'e-2', 'title': 'Related Note', 'relation': 'reference'},
            {'entry_id': 'e-3', 'title': 'Another Note', 'relation': 'mention'},
          ],
        },
      });

      final response = await client.fetchBacklinks<Map<String, dynamic>>(
        id: 'e-1',
      );

      final backlinks = response.data!['backlinks'] as List;
      expect(backlinks.length, 2);
      expect(backlinks[0]['entry_id'], 'e-2');
      expect(adapter.requests[0].method, 'GET');
      expect(adapter.requests[0].path, '/entries/e-1/backlinks');
    });

    test('fetchBacklinks returns empty list when no backlinks', () async {
      client = createTestClient({
        'GET /entries/e-1/backlinks': {'backlinks': []},
      });

      final response = await client.fetchBacklinks<Map<String, dynamic>>(
        id: 'e-1',
      );

      expect((response.data!['backlinks'] as List).length, 0);
    });

    test('fetchBacklinks returns 404 for nonexistent entry', () async {
      client = createTestClient({
        'GET /entries/nonexistent/backlinks': _MockResponse(
          statusCode: 404,
          data: {'detail': 'Entry not found'},
        ),
      });

      expect(
        () => client.fetchBacklinks<Map<String, dynamic>>(id: 'nonexistent'),
        throwsA(isA<DioException>()),
      );
    });

    // ---- fetchEntryLinks ----

    test('fetchEntryLinks sends GET /entries/{id}/links with default direction',
        () async {
      client = createTestClient({
        'GET /entries/e-1/links': {
          'links': [
            {'id': 'l-1', 'target_id': 'e-2', 'relation_type': 'reference'},
          ],
        },
      });

      final response = await client.fetchEntryLinks<Map<String, dynamic>>(
        id: 'e-1',
      );

      final links = response.data!['links'] as List;
      expect(links.length, 1);
      expect(adapter.requests[0].method, 'GET');
      expect(adapter.requests[0].path, '/entries/e-1/links');
      expect(adapter.requests[0].queryParameters?['direction'], 'both');
    });

    test('fetchEntryLinks sends direction=in parameter', () async {
      client = createTestClient({
        'GET /entries/e-1/links': {'links': []},
      });

      await client.fetchEntryLinks<Map<String, dynamic>>(
        id: 'e-1',
        direction: 'in',
      );

      expect(adapter.requests[0].queryParameters?['direction'], 'in');
    });

    test('fetchEntryLinks sends direction=out parameter', () async {
      client = createTestClient({
        'GET /entries/e-1/links': {'links': []},
      });

      await client.fetchEntryLinks<Map<String, dynamic>>(
        id: 'e-1',
        direction: 'out',
      );

      expect(adapter.requests[0].queryParameters?['direction'], 'out');
    });

    test('fetchEntryLinks returns 422 for invalid direction', () async {
      client = createTestClient({
        'GET /entries/e-1/links': _MockResponse(
          statusCode: 422,
          data: {
            'detail': [
              {
                'loc': ['query', 'direction'],
                'msg': 'Value error, direction must be one of: in, out, both',
                'type': 'value_error',
              },
            ],
          },
        ),
      });

      try {
        await client.fetchEntryLinks<Map<String, dynamic>>(
          id: 'e-1',
          direction: 'invalid',
        );
        fail('Expected DioException');
      } on DioException catch (e) {
        expect(e.response?.statusCode, 422);
        // Verify the invalid direction was actually sent
        expect(adapter.requests[0].queryParameters?['direction'], 'invalid');
      }
    });

    test('fetchEntryLinks returns 404 for nonexistent entry', () async {
      client = createTestClient({
        'GET /entries/nonexistent/links': _MockResponse(
          statusCode: 404,
          data: {'detail': 'Entry not found'},
        ),
      });

      expect(
        () => client.fetchEntryLinks<Map<String, dynamic>>(id: 'nonexistent'),
        throwsA(isA<DioException>()),
      );
    });

    // ---- createEntryLink ----

    test('createEntryLink sends POST /entries/{id}/links and returns 201',
        () async {
      client = createTestClient({
        'POST /entries/e-1/links': _MockResponse(
          statusCode: 201,
          data: {
            'id': 'link-1',
            'source_id': 'e-1',
            'target_id': 'e-2',
            'relation_type': 'reference',
          },
        ),
      });

      final response = await client.createEntryLink<Map<String, dynamic>>(
        id: 'e-1',
        targetId: 'e-2',
        relationType: 'reference',
      );

      expect(response.statusCode, 201);
      expect(response.data!['id'], 'link-1');
      expect(response.data!['target_id'], 'e-2');
      expect(adapter.requests[0].method, 'POST');
      expect(adapter.requests[0].path, '/entries/e-1/links');
      expect(adapter.requests[0].data['target_id'], 'e-2');
      expect(adapter.requests[0].data['relation_type'], 'reference');
    });

    test('createEntryLink self-reference returns 400', () async {
      client = createTestClient({
        'POST /entries/e-1/links': _MockResponse(
          statusCode: 400,
          data: {'detail': 'Cannot create self-referencing link'},
        ),
      });

      try {
        await client.createEntryLink<Map<String, dynamic>>(
          id: 'e-1',
          targetId: 'e-1',
          relationType: 'reference',
        );
        fail('Expected DioException');
      } on DioException catch (e) {
        expect(e.response?.statusCode, 400);
        // Verify the request body contained self-referencing target_id
        expect(adapter.requests[0].data['target_id'], 'e-1');
        expect(adapter.requests[0].data['relation_type'], 'reference');
      }
    });

    test('createEntryLink duplicate link returns 409', () async {
      client = createTestClient({
        'POST /entries/e-1/links': _MockResponse(
          statusCode: 409,
          data: {'detail': 'Link already exists'},
        ),
      });

      try {
        await client.createEntryLink<Map<String, dynamic>>(
          id: 'e-1',
          targetId: 'e-2',
          relationType: 'reference',
        );
        fail('Expected DioException');
      } on DioException catch (e) {
        expect(e.response?.statusCode, 409);
        // Verify the duplicate link was for the same target
        expect(adapter.requests[0].data['target_id'], 'e-2');
        expect(adapter.requests[0].data['relation_type'], 'reference');
      }
    });

    test('createEntryLink returns 404 for nonexistent target', () async {
      client = createTestClient({
        'POST /entries/e-1/links': _MockResponse(
          statusCode: 404,
          data: {'detail': 'Target entry not found'},
        ),
      });

      try {
        await client.createEntryLink<Map<String, dynamic>>(
          id: 'e-1',
          targetId: 'nonexistent',
          relationType: 'reference',
        );
        fail('Expected DioException');
      } on DioException catch (e) {
        expect(e.response?.statusCode, 404);
        // Verify the request targeted a nonexistent entry
        expect(adapter.requests[0].data['target_id'], 'nonexistent');
      }
    });

    // ---- deleteEntryLink ----

    test('deleteEntryLink sends DELETE /entries/{id}/links/{linkId}', () async {
      client = createTestClient({
        'DELETE /entries/e-1/links/link-1': _MockResponse(
          statusCode: 204,
          data: null,
        ),
      });

      final response = await client.deleteEntryLink<Map<String, dynamic>>(
        id: 'e-1',
        linkId: 'link-1',
      );

      expect(response.statusCode, 204);
      expect(adapter.requests[0].method, 'DELETE');
      expect(adapter.requests[0].path, '/entries/e-1/links/link-1');
    });

    test('deleteEntryLink returns 404 for nonexistent link', () async {
      client = createTestClient({
        'DELETE /entries/e-1/links/nonexistent': _MockResponse(
          statusCode: 404,
          data: {'detail': 'Link not found'},
        ),
      });

      expect(
        () => client.deleteEntryLink<Map<String, dynamic>>(
          id: 'e-1',
          linkId: 'nonexistent',
        ),
        throwsA(isA<DioException>()),
      );
    });

    // ---- fetchKnowledgeContext ----

    test('fetchKnowledgeContext sends GET /entries/{id}/knowledge-context',
        () async {
      client = createTestClient({
        'GET /entries/e-1/knowledge-context': {
          'nodes': [
            {'id': 'c-1', 'label': 'Flutter', 'type': 'concept'},
            {'id': 'c-2', 'label': 'Dart', 'type': 'concept'},
          ],
          'edges': [
            {'source': 'c-2', 'target': 'c-1', 'relation': 'related_to'},
          ],
          'center_concepts': ['Flutter'],
        },
      });

      final response = await client.fetchKnowledgeContext<Map<String, dynamic>>(
        id: 'e-1',
      );

      final nodes = response.data!['nodes'] as List;
      final edges = response.data!['edges'] as List;
      final centerConcepts = response.data!['center_concepts'] as List;
      expect(nodes.length, 2);
      expect(edges.length, 1);
      expect(centerConcepts, ['Flutter']);
      expect(adapter.requests[0].method, 'GET');
      expect(adapter.requests[0].path, '/entries/e-1/knowledge-context');
    });

    test('fetchKnowledgeContext returns 404 for nonexistent entry', () async {
      client = createTestClient({
        'GET /entries/nonexistent/knowledge-context': _MockResponse(
          statusCode: 404,
          data: {'detail': 'Entry not found'},
        ),
      });

      expect(
        () => client.fetchKnowledgeContext<Map<String, dynamic>>(
          id: 'nonexistent',
        ),
        throwsA(isA<DioException>()),
      );
    });

    test('fetchKnowledgeContext returns 500 on server error', () async {
      client = createTestClient({
        'GET /entries/e-1/knowledge-context': _MockResponse(
          statusCode: 500,
          data: {'detail': 'Internal server error'},
        ),
      });

      expect(
        () => client.fetchKnowledgeContext<Map<String, dynamic>>(id: 'e-1'),
        throwsA(isA<DioException>()),
      );
    });

    // ---- generateAISummary ----

    test('generateAISummary sends POST /entries/{id}/ai-summary', () async {
      client = createTestClient({
        'POST /entries/e-1/ai-summary': {
          'summary': 'This entry discusses Flutter development patterns.',
          'cached': false,
          'generated_at': '2025-06-15T10:30:00Z',
        },
      });

      final response = await client.generateAISummary<Map<String, dynamic>>(
        id: 'e-1',
      );

      expect(response.data!['summary'], 'This entry discusses Flutter development patterns.');
      expect(response.data!['cached'], false);
      expect(response.data!['generated_at'], '2025-06-15T10:30:00Z');
      expect(adapter.requests[0].method, 'POST');
      expect(adapter.requests[0].path, '/entries/e-1/ai-summary');
    });

    test('generateAISummary returns cached summary', () async {
      client = createTestClient({
        'POST /entries/e-1/ai-summary': {
          'summary': 'Cached summary content.',
          'cached': true,
          'generated_at': '2025-06-14T08:00:00Z',
        },
      });

      final response = await client.generateAISummary<Map<String, dynamic>>(
        id: 'e-1',
      );

      expect(response.data!['cached'], true);
    });

    test('generateAISummary empty content returns summary=null', () async {
      client = createTestClient({
        'POST /entries/e-1/ai-summary': {
          'summary': null,
          'cached': false,
          'generated_at': null,
        },
      });

      final response = await client.generateAISummary<Map<String, dynamic>>(
        id: 'e-1',
      );

      expect(response.data!['summary'], isNull);
      expect(response.data!['cached'], false);
    });

    test('generateAISummary returns 404 for nonexistent entry', () async {
      client = createTestClient({
        'POST /entries/nonexistent/ai-summary': _MockResponse(
          statusCode: 404,
          data: {'detail': 'Entry not found'},
        ),
      });

      expect(
        () => client.generateAISummary<Map<String, dynamic>>(id: 'nonexistent'),
        throwsA(isA<DioException>()),
      );
    });

    test('generateAISummary returns 500 on server error', () async {
      client = createTestClient({
        'POST /entries/e-1/ai-summary': _MockResponse(
          statusCode: 500,
          data: {'detail': 'Internal server error'},
        ),
      });

      expect(
        () => client.generateAISummary<Map<String, dynamic>>(id: 'e-1'),
        throwsA(isA<DioException>()),
      );
    });
  });
}
