import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:rizhi/services/api_client.dart';
import 'package:rizhi/services/notification_service.dart';

import '../helpers/mock_api_client.dart';

void main() {
  group('NotificationService', () {
    late MockApiClient mockApiClient;
    late SharedPreferences prefs;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      prefs = await SharedPreferences.getInstance();
      mockApiClient = MockApiClient();
    });

    NotificationService createService() {
      return NotificationService(
        apiClient: mockApiClient,
        prefs: prefs,
      );
    }

    test('scheduleDueTaskCheck returns 0 when response data is null',
        () async {
      when(() => mockApiClient.get<Map<String, dynamic>>(
            '/entries',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: '/entries'),
                data: null,
                statusCode: 200,
              ));

      final service = createService();
      final count = await service.scheduleDueTaskCheck();
      expect(count, 0);
    });

    test('scheduleDueTaskCheck returns 0 when response has no items',
        () async {
      when(() => mockApiClient.get<Map<String, dynamic>>(
            '/entries',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: '/entries'),
                data: <String, dynamic>{},
                statusCode: 200,
              ));

      final service = createService();
      final count = await service.scheduleDueTaskCheck();
      expect(count, 0);
    });

    test('scheduleDueTaskCheck processes items with valid structure',
        () async {
      when(() => mockApiClient.get<Map<String, dynamic>>(
            '/entries',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: '/entries'),
                data: <String, dynamic>{
                  'items': [
                    {'id': 'task-1', 'title': '买牛奶'},
                    {'id': 'task-2', 'title': '写周报'},
                  ],
                },
                statusCode: 200,
              ));

      final service = createService();
      final count = await service.scheduleDueTaskCheck();
      expect(count, 2);
    });

    test('scheduleDueTaskCheck deduplicates already notified tasks',
        () async {
      // 预设已通知记录
      final now = DateTime.now();
      final dateStr =
          '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';

      await prefs.setStringList('notified_due_tasks_$dateStr', [
        '$dateStr:task-1',
      ]);

      when(() => mockApiClient.get<Map<String, dynamic>>(
            '/entries',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: '/entries'),
                data: <String, dynamic>{
                  'items': [
                    {'id': 'task-1', 'title': '买牛奶'},
                    {'id': 'task-2', 'title': '写周报'},
                  ],
                },
                statusCode: 200,
              ));

      final service = createService();
      final count = await service.scheduleDueTaskCheck();
      // task-1 已通知过，只有 task-2 是新的
      expect(count, 1);
    });

    test('scheduleDueTaskCheck skips items without id', () async {
      when(() => mockApiClient.get<Map<String, dynamic>>(
            '/entries',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: '/entries'),
                data: <String, dynamic>{
                  'items': [
                    {'title': '没有 id 的任务'},
                    {'id': 'task-2', 'title': '正常任务'},
                  ],
                },
                statusCode: 200,
              ));

      final service = createService();
      final count = await service.scheduleDueTaskCheck();
      expect(count, 1);
    });

    test('scheduleDueTaskCheck handles entries format', () async {
      when(() => mockApiClient.get<Map<String, dynamic>>(
            '/entries',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: '/entries'),
                data: <String, dynamic>{
                  'entries': [
                    {'id': 'task-1', 'title': '测试任务'},
                  ],
                },
                statusCode: 200,
              ));

      final service = createService();
      final count = await service.scheduleDueTaskCheck();
      expect(count, 1);
    });

    test('scheduleDueTaskCheck returns 0 on API error', () async {
      when(() => mockApiClient.get<Map<String, dynamic>>(
            '/entries',
            queryParameters: any(named: 'queryParameters'),
          )).thenThrow(Exception('Network error'));

      final service = createService();
      final count = await service.scheduleDueTaskCheck();
      expect(count, 0);
    });

    test('clearNotifiedRecords removes all notification records', () async {
      await prefs.setStringList('notified_due_tasks_2026-05-07', [
        '2026-05-07:task-1',
      ]);
      await prefs.setString('some_other_key', 'value');

      final service = createService();
      await service.clearNotifiedRecords();

      expect(
          prefs.getStringList('notified_due_tasks_2026-05-07'), isNull);
      expect(prefs.getString('some_other_key'), 'value');
    });

    test('second call on same day deduplicates previously notified', () async {
      when(() => mockApiClient.get<Map<String, dynamic>>(
            '/entries',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => Response(
                requestOptions: RequestOptions(path: '/entries'),
                data: <String, dynamic>{
                  'items': [
                    {'id': 'task-1', 'title': '买牛奶'},
                  ],
                },
                statusCode: 200,
              ));

      final service = createService();

      // 第一次调用：应通知
      final count1 = await service.scheduleDueTaskCheck();
      expect(count1, 1);

      // 第二次调用：已通知过，应跳过
      final count2 = await service.scheduleDueTaskCheck();
      expect(count2, 0);
    });
  });
}
