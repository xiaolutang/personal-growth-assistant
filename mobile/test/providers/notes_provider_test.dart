import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:growth_assistant/models/entry.dart';
import 'package:growth_assistant/providers/notes_provider.dart';

void main() {
  group('NotesState', () {
    test('initial state has empty entries and no error', () {
      const state = NotesState();

      expect(state.entries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.searchQuery, isEmpty);
    });

    test('copyWith preserves unchanged fields', () {
      const state = NotesState(isLoading: true);
      final copied = state.copyWith(error: 'Connection failed');

      expect(copied.isLoading, true);
      expect(copied.error, 'Connection failed');
      expect(copied.entries, isEmpty);
      expect(copied.searchQuery, isEmpty);
    });

    test('copyWith can update isLoading', () {
      const state = NotesState();
      final copied = state.copyWith(isLoading: true);

      expect(copied.isLoading, true);
      expect(copied.error, isNull);
    });

    test('copyWith can update entries', () {
      const state = NotesState();
      final entries = [
        Entry(
          id: 'e1',
          title: 'My note',
          category: 'note',
          createdAt: '2026-04-27T00:00:00',
        ),
      ];
      final copied = state.copyWith(entries: entries);

      expect(copied.entries, hasLength(1));
      expect(copied.entries.first.id, 'e1');
    });

    test('copyWith can update searchQuery', () {
      const state = NotesState();
      final copied = state.copyWith(searchQuery: 'flutter');

      expect(copied.searchQuery, 'flutter');
    });

    test('copyWith can clear error', () {
      const state = NotesState(error: 'Some error');
      final copied = state.copyWith(error: null);

      expect(copied.error, isNull);
    });

    test('copyWith can clear error while updating other fields', () {
      const state = NotesState(error: 'Error', isLoading: true);
      final copied = state.copyWith(isLoading: false, error: null);

      expect(copied.isLoading, false);
      expect(copied.error, isNull);
    });
  });

  group('NotesNotifier with ProviderContainer', () {
    test('initial build returns default state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(notesProvider);

      expect(state.entries, isEmpty);
      expect(state.isLoading, false);
      expect(state.error, isNull);
      expect(state.searchQuery, isEmpty);
    });
  });
}
