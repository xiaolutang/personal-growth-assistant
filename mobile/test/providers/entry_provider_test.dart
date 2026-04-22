import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/providers/entry_provider.dart';

void main() {
  group('EntryListState', () {
    test('initial state has empty list and no error', () {
      const state = EntryListState();

      expect(state.entries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });

    test('copyWith preserves unchanged fields', () {
      const state = EntryListState(isLoading: true);
      final copied = state.copyWith(error: 'Network error');

      expect(copied.isLoading, true);
      expect(copied.error, 'Network error');
      expect(copied.entries, isEmpty);
    });

    test('copyWith can update entries', () {
      const state = EntryListState();
      final entries = [_makeEntry('1')];
      final copied = state.copyWith(entries: entries);

      expect(copied.entries, hasLength(1));
      expect(copied.entries.first.id, '1');
    });

    test('copyWith can update isLoading', () {
      const state = EntryListState();
      final copied = state.copyWith(isLoading: true);

      expect(copied.isLoading, true);
      expect(copied.error, isNull);
    });
  });

  group('EntryDetailState', () {
    test('initial state has null entry and no error', () {
      const state = EntryDetailState();

      expect(state.entry, isNull);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.notFound, false);
    });

    test('copyWith preserves unchanged fields', () {
      const state = EntryDetailState(isLoading: true);
      final copied = state.copyWith(notFound: true);

      expect(copied.isLoading, true);
      expect(copied.notFound, true);
      expect(copied.entry, isNull);
    });

    test('copyWith can update entry', () {
      const state = EntryDetailState();
      final entry = _makeEntry('test-id');
      final copied = state.copyWith(entry: entry);

      expect(copied.entry, isNotNull);
      expect(copied.entry!.id, 'test-id');
    });

    test('copyWith can update notFound', () {
      const state = EntryDetailState();
      final copied = state.copyWith(notFound: true);

      expect(copied.notFound, true);
    });
  });

  group('EntryListNotifier', () {
    test('initial build returns default state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(entryListProvider);

      expect(state.entries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
    });
  });

  group('EntryDetailNotifier', () {
    test('initial build returns default state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(entryDetailProvider);

      expect(state.entry, isNull);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.notFound, false);
    });
  });
}

Entry _makeEntry(String id, {String? status, String category = 'task'}) {
  return Entry(
    id: id,
    title: 'Entry $id',
    category: category,
    status: status,
  );
}
