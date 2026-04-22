import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/entry.dart';

void main() {
  group('Entry', () {
    test('fromJson parses entry data correctly', () {
      final json = {
        'id': 'task-xxx',
        'title': '学习 Flutter',
        'content': '学习 Flutter 框架基础知识',
        'category': 'task',
        'status': 'todo',
        'priority': 'high',
        'tags': ['flutter', 'mobile'],
        'created_at': '2026-04-22T10:00:00',
        'updated_at': '2026-04-22T10:00:00',
        'planned_date': '2026-04-22',
        'completed_at': null,
        'parent_id': null,
        'file_path': 'tasks/task-xxx.md',
      };

      final entry = Entry.fromJson(json);

      expect(entry.id, 'task-xxx');
      expect(entry.title, '学习 Flutter');
      expect(entry.content, '学习 Flutter 框架基础知识');
      expect(entry.category, 'task');
      expect(entry.status, 'todo');
      expect(entry.priority, 'high');
      expect(entry.tags, ['flutter', 'mobile']);
      expect(entry.createdAt, '2026-04-22T10:00:00');
      expect(entry.plannedDate, '2026-04-22');
      expect(entry.completedAt, isNull);
      expect(entry.parentId, isNull);
      expect(entry.filePath, 'tasks/task-xxx.md');
    });

    test('fromJson handles missing optional fields', () {
      final json = {
        'id': 'note-1',
        'title': 'A note',
        'category': 'note',
      };

      final entry = Entry.fromJson(json);

      expect(entry.id, 'note-1');
      expect(entry.title, 'A note');
      expect(entry.content, isNull);
      expect(entry.category, 'note');
      expect(entry.status, isNull);
      expect(entry.priority, isNull);
      expect(entry.tags, isEmpty);
      expect(entry.createdAt, isNull);
      expect(entry.plannedDate, isNull);
    });

    test('toJson produces correct map', () {
      const entry = Entry(
        id: 'task-1',
        title: 'Test task',
        content: 'Some content',
        category: 'task',
        status: 'doing',
        tags: ['test'],
      );

      final json = entry.toJson();

      expect(json['id'], 'task-1');
      expect(json['title'], 'Test task');
      expect(json['content'], 'Some content');
      expect(json['category'], 'task');
      expect(json['status'], 'doing');
      expect(json['tags'], ['test']);
    });

    test('toJson roundtrip preserves data', () {
      final json = {
        'id': 'inbox-1',
        'title': 'An idea',
        'content': 'Good idea',
        'category': 'inbox',
        'status': null,
        'priority': 'medium',
        'tags': ['idea'],
        'created_at': '2026-04-22T08:00:00',
        'updated_at': '2026-04-22T08:00:00',
        'planned_date': null,
        'completed_at': null,
        'parent_id': null,
        'file_path': 'inbox/inbox-1.md',
      };

      final entry = Entry.fromJson(json);
      final output = entry.toJson();

      expect(output['id'], json['id']);
      expect(output['title'], json['title']);
      expect(output['content'], json['content']);
      expect(output['category'], json['category']);
      expect(output['priority'], json['priority']);
      expect(output['tags'], json['tags']);
    });

    test('toCreateJson produces task creation payload', () {
      const entry = Entry(
        id: '',
        title: 'New Task',
        content: 'Task details',
        category: 'task',
        status: 'todo',
      );

      final json = entry.toCreateJson();

      expect(json['category'], 'task');
      expect(json['title'], 'New Task');
      expect(json['content'], 'Task details');
      expect(json['status'], 'todo');
    });

    test('toCreateJson defaults status to todo', () {
      const entry = Entry(
        id: '',
        title: 'Task without status',
        category: 'task',
      );

      final json = entry.toCreateJson();

      expect(json['status'], 'todo');
      expect(json['content'], '');
    });
  });
}
