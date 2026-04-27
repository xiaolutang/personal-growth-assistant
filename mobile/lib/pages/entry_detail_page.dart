import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/entry.dart';
import '../providers/entry_provider.dart';

// ============================================================
// EntryDetailPage - 条目详情页
//
// 功能：
// - 只读/编辑双模式展示条目内容
// - AppBar 编辑/保存按钮切换
// - 编辑态：标题 TextField、内容多行 TextField、状态/优先级 DropdownButton、标签 Chip 增删
// - 保存调用 provider.updateEntry，成功后退出编辑+SnackBar
// - category 不可编辑
// - dirty 检测：未修改时保存按钮不可点击
// ============================================================
class EntryDetailPage extends ConsumerStatefulWidget {
  final String entryId;

  const EntryDetailPage({super.key, required this.entryId});

  @override
  ConsumerState<EntryDetailPage> createState() => _EntryDetailPageState();
}

class _EntryDetailPageState extends ConsumerState<EntryDetailPage> {
  // 编辑态本地控制器
  late TextEditingController _titleController;
  late TextEditingController _contentController;
  String? _selectedStatus;
  String? _selectedPriority;
  List<String> _editedTags = [];

  // dirty 追踪
  bool _isDirty = false;

  // 标签输入
  final TextEditingController _tagInputController = TextEditingController();
  bool _showTagInput = false;

  @override
  void initState() {
    super.initState();
    _titleController = TextEditingController();
    _contentController = TextEditingController();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadEntry();
    });
  }

  @override
  void dispose() {
    _titleController.dispose();
    _contentController.dispose();
    _tagInputController.dispose();
    super.dispose();
  }

  void _loadEntry() {
    ref.read(entryDetailProvider(widget.entryId).notifier).fetchEntry();
  }

  /// 进入编辑模式：初始化本地控制器
  void _enterEditMode() {
    final entry = ref.read(entryDetailProvider(widget.entryId)).entry;
    if (entry == null) return;

    _titleController.text = entry.title;
    _contentController.text = entry.content ?? '';
    _selectedStatus = entry.status;
    _selectedPriority = entry.priority;
    _editedTags = List<String>.from(entry.tags);
    _isDirty = false;
    _showTagInput = false;
    _tagInputController.clear();

    ref.read(entryDetailProvider(widget.entryId).notifier).toggleEdit();
  }

  /// 取消编辑
  void _cancelEdit() {
    _isDirty = false;
    _showTagInput = false;
    _tagInputController.clear();
    ref.read(entryDetailProvider(widget.entryId).notifier).toggleEdit();
  }

  /// 保存编辑
  Future<void> _saveEdit() async {
    if (!_isDirty) return;

    final data = <String, dynamic>{};
    final entry = ref.read(entryDetailProvider(widget.entryId)).entry;
    if (entry == null) return;

    if (_titleController.text != entry.title) {
      data['title'] = _titleController.text;
    }
    if (_contentController.text != (entry.content ?? '')) {
      data['content'] = _contentController.text;
    }
    if (_selectedStatus != entry.status) {
      data['status'] = _selectedStatus;
    }
    if (_selectedPriority != entry.priority) {
      data['priority'] = _selectedPriority;
    }
    if (!_listEquals(_editedTags, entry.tags)) {
      data['tags'] = _editedTags;
    }

    if (data.isEmpty) return;

    final notifier =
        ref.read(entryDetailProvider(widget.entryId).notifier);
    await notifier.updateEntry(data);

    if (!mounted) return;

    final state = ref.read(entryDetailProvider(widget.entryId));
    if (state.error == null) {
      // 保存成功
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('保存成功'),
          duration: Duration(seconds: 2),
        ),
      );
    } else {
      // 保存失败 - 保持编辑态
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('保存失败: ${state.error}'),
          backgroundColor: AppColors.error,
          duration: const Duration(seconds: 3),
        ),
      );
    }
  }

  /// 检测 dirty 状态
  void _checkDirty() {
    final entry = ref.read(entryDetailProvider(widget.entryId)).entry;
    if (entry == null) return;

    final wasDirty = _isDirty;
    _isDirty = _titleController.text != entry.title ||
        _contentController.text != (entry.content ?? '') ||
        _selectedStatus != entry.status ||
        _selectedPriority != entry.priority ||
        !_listEquals(_editedTags, entry.tags);

    if (wasDirty != _isDirty) {
      setState(() {});
    }
  }

  bool _listEquals(List<String> a, List<String> b) {
    if (a.length != b.length) return false;
    for (int i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }

  void _addTag(String tag) {
    final trimmed = tag.trim();
    if (trimmed.isEmpty || _editedTags.contains(trimmed)) return;
    setState(() {
      _editedTags = [..._editedTags, trimmed];
      _tagInputController.clear();
      _showTagInput = false;
    });
    _checkDirty();
  }

  void _removeTag(String tag) {
    setState(() {
      _editedTags = _editedTags.where((t) => t != tag).toList();
    });
    _checkDirty();
  }

  @override
  Widget build(BuildContext context) {
    final detailState = ref.watch(entryDetailProvider(widget.entryId));
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Text(_categoryLabel(detailState.entry?.category)),
        centerTitle: true,
        actions: _buildAppBarActions(detailState),
      ),
      body: _buildBody(detailState, theme),
    );
  }

  List<Widget>? _buildAppBarActions(EntryDetailState state) {
    if (state.entry == null || state.isLoading) return null;

    if (state.isEditing) {
      return [
        if (state.isSaving)
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            child: SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          )
        else ...[
          TextButton(
            onPressed: _cancelEdit,
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: _isDirty ? _saveEdit : null,
            child: Text(
              '保存',
              style: TextStyle(
                color: _isDirty ? AppColors.primary : Colors.grey,
              ),
            ),
          ),
        ],
      ];
    } else {
      return [
        IconButton(
          icon: const Icon(Icons.edit_outlined),
          onPressed: _enterEditMode,
          tooltip: '编辑',
        ),
      ];
    }
  }

  Widget _buildBody(EntryDetailState state, ThemeData theme) {
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.notFound) {
      return _buildNotFound(theme);
    }

    if (state.error != null && state.entry == null) {
      return _buildError(state.error!, theme);
    }

    final entry = state.entry;
    if (entry == null) {
      return const SizedBox.shrink();
    }

    if (state.isEditing) {
      return _buildEditingBody(entry, state, theme);
    }

    return _buildReadOnlyBody(entry, theme);
  }

  // ============================================================
  // 只读模式
  // ============================================================
  Widget _buildReadOnlyBody(Entry entry, ThemeData theme) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题
          Text(
            entry.title,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: AppSpacing.md),

          // 标签列表
          if (entry.tags.isNotEmpty) ...[
            _buildTagList(entry.tags, theme),
            const SizedBox(height: AppSpacing.md),
          ],

          // 分割线
          const Divider(),
          const SizedBox(height: AppSpacing.md),

          // Markdown 内容
          if (entry.content != null && entry.content!.isNotEmpty)
            MarkdownBody(
              data: entry.content!,
              selectable: true,
            )
          else
            Text(
              '暂无内容',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),

          const SizedBox(height: AppSpacing.xl),

          // 底部元信息
          _buildMetaInfo(entry, theme),
        ],
      ),
    );
  }

  // ============================================================
  // 编辑模式
  // ============================================================
  Widget _buildEditingBody(
      Entry entry,
      EntryDetailState state,
      ThemeData theme,) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题编辑
          TextField(
            controller: _titleController,
            decoration: const InputDecoration(
              labelText: '标题',
              border: OutlineInputBorder(),
            ),
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
            onChanged: (_) => _checkDirty(),
          ),
          const SizedBox(height: AppSpacing.md),

          // 标签编辑
          _buildEditableTags(theme),
          const SizedBox(height: AppSpacing.md),

          // 分割线
          const Divider(),
          const SizedBox(height: AppSpacing.md),

          // 内容编辑
          TextField(
            controller: _contentController,
            decoration: const InputDecoration(
              labelText: '内容',
              border: OutlineInputBorder(),
              alignLabelWithHint: true,
            ),
            maxLines: null,
            minLines: 8,
            onChanged: (_) => _checkDirty(),
          ),
          const SizedBox(height: AppSpacing.xl),

          // 状态和优先级
          Row(
            children: [
              Expanded(
                child: _buildStatusDropdown(theme),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: _buildPriorityDropdown(theme),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),

          // 底部元信息（只读）
          _buildMetaInfo(entry, theme),
        ],
      ),
    );
  }

  Widget _buildEditableTags(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '标签',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.xs,
          children: [
            ..._editedTags.map((tag) => _buildEditableChip(tag, theme)),
            // 添加标签按钮
            if (!_showTagInput)
              GestureDetector(
                onTap: () {
                  setState(() {
                    _showTagInput = true;
                  });
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.xs,
                  ),
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: theme.colorScheme.outline.withValues(alpha: 0.3),
                    ),
                    borderRadius: BorderRadius.circular(AppRadius.button),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.add,
                        size: 14,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                      const SizedBox(width: 2),
                      Text(
                        '添加',
                        style: TextStyle(
                          fontSize: AppFontSize.caption,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
        if (_showTagInput) ...[
          const SizedBox(height: AppSpacing.xs),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _tagInputController,
                  decoration: const InputDecoration(
                    hintText: '输入标签名',
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                      vertical: AppSpacing.xs,
                    ),
                    border: OutlineInputBorder(),
                  ),
                  style: const TextStyle(fontSize: AppFontSize.caption),
                  autofocus: true,
                  onSubmitted: _addTag,
                ),
              ),
              const SizedBox(width: AppSpacing.xs),
              IconButton(
                icon: const Icon(Icons.check, size: 20),
                onPressed: () => _addTag(_tagInputController.text),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(
                  minWidth: 32,
                  minHeight: 32,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 20),
                onPressed: () {
                  setState(() {
                    _showTagInput = false;
                    _tagInputController.clear();
                  });
                },
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(
                  minWidth: 32,
                  minHeight: 32,
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildEditableChip(String tag, ThemeData theme) {
    return GestureDetector(
      onLongPress: () => _confirmDeleteTag(tag),
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: AppColors.primary.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(AppRadius.button),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '#$tag',
              style: const TextStyle(
                fontSize: AppFontSize.caption,
                color: AppColors.primary,
              ),
            ),
            const SizedBox(width: 4),
            GestureDetector(
              onTap: () => _removeTag(tag),
              child: Icon(
                Icons.close,
                size: 14,
                color: AppColors.primary.withValues(alpha: 0.7),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _confirmDeleteTag(String tag) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('删除标签'),
        content: Text('确定删除标签 "#$tag" 吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              _removeTag(tag);
            },
            child: const Text('删除'),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusDropdown(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '状态',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        DropdownButtonFormField<String>(
          value: _selectedStatus,
          decoration: const InputDecoration(
            isDense: true,
            border: OutlineInputBorder(),
            contentPadding: EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.sm,
            ),
          ),
          items: [
            DropdownMenuItem(
              value: AppConstants.statusWaitStart,
              child: Text(_statusLabel(AppConstants.statusWaitStart)),
            ),
            DropdownMenuItem(
              value: AppConstants.statusDoing,
              child: Text(_statusLabel(AppConstants.statusDoing)),
            ),
            DropdownMenuItem(
              value: AppConstants.statusComplete,
              child: Text(_statusLabel(AppConstants.statusComplete)),
            ),
            DropdownMenuItem(
              value: AppConstants.statusPaused,
              child: Text(_statusLabel(AppConstants.statusPaused)),
            ),
            DropdownMenuItem(
              value: AppConstants.statusCancelled,
              child: Text(_statusLabel(AppConstants.statusCancelled)),
            ),
          ],
          onChanged: (value) {
            setState(() {
              _selectedStatus = value;
            });
            _checkDirty();
          },
        ),
      ],
    );
  }

  Widget _buildPriorityDropdown(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '优先级',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        DropdownButtonFormField<String>(
          value: _selectedPriority,
          decoration: const InputDecoration(
            isDense: true,
            border: OutlineInputBorder(),
            contentPadding: EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.sm,
            ),
          ),
          items: [
            const DropdownMenuItem(
              value: null,
              child: Text('未设置'),
            ),
            DropdownMenuItem(
              value: 'high',
              child: Text(_priorityLabel('high')),
            ),
            DropdownMenuItem(
              value: 'medium',
              child: Text(_priorityLabel('medium')),
            ),
            DropdownMenuItem(
              value: 'low',
              child: Text(_priorityLabel('low')),
            ),
          ],
          onChanged: (value) {
            setState(() {
              _selectedPriority = value;
            });
            _checkDirty();
          },
        ),
      ],
    );
  }

  // ============================================================
  // 只读模式下的标签列表
  // ============================================================
  Widget _buildTagList(List<String> tags, ThemeData theme) {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.xs,
      children: tags.map((tag) {
        return Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.xs,
          ),
          decoration: BoxDecoration(
            color: AppColors.primary.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(AppRadius.button),
          ),
          child: Text(
            '#$tag',
            style: const TextStyle(
              fontSize: AppFontSize.caption,
              color: AppColors.primary,
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildMetaInfo(dynamic entry, ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      child: Column(
        children: [
          if (entry.status != null)
            _buildMetaRow('状态', _statusLabel(entry.status), theme),
          if (entry.priority != null && entry.priority!.isNotEmpty)
            _buildMetaRow('优先级', _priorityLabel(entry.priority), theme),
          if (entry.createdAt != null)
            _buildMetaRow('创建时间', _formatDate(entry.createdAt), theme),
          if (entry.updatedAt != null)
            _buildMetaRow('更新时间', _formatDate(entry.updatedAt), theme),
        ],
      ),
    );
  }

  Widget _buildMetaRow(String label, String value, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          Text(
            value,
            style: theme.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNotFound(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.search_off,
              size: 64,
              color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.4),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              '条目不存在',
              style: theme.textTheme.titleMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              '该条目可能已被删除或链接无效',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.6),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildError(String error, ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xxl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: theme.colorScheme.error.withValues(alpha: 0.6),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              error,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.error,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.lg),
            ElevatedButton(
              onPressed: _loadEntry,
              child: const Text('重试'),
            ),
          ],
        ),
      ),
    );
  }

  String _categoryLabel(String? category) {
    switch (category) {
      case AppConstants.categoryTask:
        return '任务详情';
      case AppConstants.categoryNote:
        return '笔记详情';
      case AppConstants.categoryInbox:
        return '灵感详情';
      case AppConstants.categoryProject:
        return '项目详情';
      default:
        return '条目详情';
    }
  }

  String _statusLabel(String? status) {
    switch (status) {
      case AppConstants.statusWaitStart:
        return '待开始';
      case AppConstants.statusDoing:
        return '进行中';
      case AppConstants.statusComplete:
        return '已完成';
      case AppConstants.statusPaused:
        return '已暂停';
      case AppConstants.statusCancelled:
        return '已取消';
      default:
        return status ?? '未知';
    }
  }

  String _priorityLabel(String? priority) {
    switch (priority) {
      case 'high':
        return '高';
      case 'medium':
        return '中';
      case 'low':
        return '低';
      default:
        return priority ?? '未知';
    }
  }

  String _formatDate(String? dateStr) {
    if (dateStr == null) return '未知';
    try {
      final date = DateTime.parse(dateStr);
      return DateFormat('yyyy-MM-dd HH:mm').format(date);
    } catch (_) {
      return dateStr;
    }
  }
}
