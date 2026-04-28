import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/notes_provider.dart';
import '../config/theme.dart';
import '../models/entry.dart';

class NotesPage extends ConsumerStatefulWidget {
  const NotesPage({super.key});

  @override
  ConsumerState<NotesPage> createState() => _NotesPageState();
}

class _NotesPageState extends ConsumerState<NotesPage> {
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(notesProvider.notifier).fetchNotes();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _handleRefresh() async {
    await ref.read(notesProvider.notifier).fetchNotes();
  }

  void _handleSearch(String query) {
    if (query.isEmpty) {
      ref.read(notesProvider.notifier).fetchNotes();
    } else {
      ref.read(notesProvider.notifier).searchNotes(query);
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(notesProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('笔记'),
        centerTitle: true,
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: '搜索笔记...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          ref.read(notesProvider.notifier).fetchNotes();
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(AppRadius.card),
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md,
                  vertical: AppSpacing.sm,
                ),
              ),
              onChanged: _handleSearch,
            ),
          ),
          // Content area
          Expanded(child: _buildBody(state, theme)),
        ],
      ),
    );
  }

  Widget _buildBody(NotesState state, ThemeData theme) {
    // 1. Loading
    if (state.isLoading && state.entries.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    // 2. Error
    if (state.error != null && state.entries.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
            const SizedBox(height: AppSpacing.md),
            Text(state.error!, style: TextStyle(color: theme.colorScheme.error)),
            const SizedBox(height: AppSpacing.md),
            FilledButton.tonal(
              onPressed: () => ref.read(notesProvider.notifier).fetchNotes(),
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }
    // 3. Empty
    if (state.entries.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.note_alt_outlined, size: 64, color: theme.colorScheme.outline),
            const SizedBox(height: AppSpacing.lg),
            Text(
              '暂无笔记',
              style: theme.textTheme.titleMedium?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              '记录你的学习心得和思考',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
          ],
        ),
      );
    }
    // 4. Data
    return RefreshIndicator(
      onRefresh: _handleRefresh,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
        itemCount: state.entries.length,
        itemBuilder: (context, index) {
          final entry = state.entries[index];
          return _buildNoteCard(entry, theme);
        },
      ),
    );
  }

  Widget _buildNoteCard(Entry entry, ThemeData theme) {
    // Use content as summary preview (first 100 chars)
    final contentPreview = entry.content != null && entry.content!.isNotEmpty
        ? (entry.content!.length > 100
            ? '${entry.content!.substring(0, 100)}...'
            : entry.content!)
        : null;

    return Card(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      child: ListTile(
        title: Text(
          entry.title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (contentPreview != null)
              Text(
                contentPreview,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            const SizedBox(height: AppSpacing.xs),
            Row(
              children: [
                if (entry.tags.isNotEmpty)
                  ...entry.tags.take(3).map(
                        (tag) => Padding(
                          padding: const EdgeInsets.only(right: AppSpacing.xs),
                          child: Chip(
                            label: Text(tag, style: const TextStyle(fontSize: 11)),
                            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            visualDensity: VisualDensity.compact,
                          ),
                        ),
                      ),
                const Spacer(),
                Text(
                  _formatDate(entry.createdAt),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.outline,
                  ),
                ),
              ],
            ),
          ],
        ),
        onTap: () => context.push('/entries/${entry.id}'),
      ),
    );
  }

  String _formatDate(String? dateStr) {
    if (dateStr == null) return '';
    try {
      final date = DateTime.parse(dateStr);
      return '${date.month}/${date.day}';
    } catch (_) {
      return dateStr;
    }
  }
}
