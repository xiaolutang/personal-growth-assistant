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
      _loadKnowledgeContext();
      _loadLinks();
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

  void _loadKnowledgeContext() {
    ref.read(entryDetailProvider(widget.entryId).notifier).fetchKnowledgeContext();
  }

  void _loadLinks() {
    ref.read(entryDetailProvider(widget.entryId).notifier).loadEntryLinks();
    ref.read(entryDetailProvider(widget.entryId).notifier).loadBacklinks();
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
    final detailState = ref.watch(entryDetailProvider(widget.entryId));

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

          // AI 摘要 Section
          _buildAISummaryCard(entry, detailState, theme),

          const SizedBox(height: AppSpacing.lg),

          // 知识上下文 Section
          _buildKnowledgeContextCard(detailState, theme),

          const SizedBox(height: AppSpacing.lg),

          // 关联条目 Section
          _buildEntryLinksSection(detailState, theme),

          const SizedBox(height: AppSpacing.lg),

          // 反向引用 Section
          _buildBacklinksSection(detailState, theme),

          const SizedBox(height: AppSpacing.lg),

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
  // AI 摘要卡片
  // ============================================================
  Widget _buildAISummaryCard(
      Entry entry,
      EntryDetailState state,
      ThemeData theme,) {
    final hasContent = entry.content != null && entry.content!.isNotEmpty;
    final isLoading = state.isGeneratingSummary;
    final summary = state.summaryText;
    final cached = state.summaryCached;
    final hasError = state.error != null && summary == null;

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Section 标题行
            Row(
              children: [
                const Icon(
                  Icons.auto_awesome_outlined,
                  size: 18,
                  color: AppColors.primary,
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  'AI 摘要',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                if (cached && summary != null)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(AppRadius.button),
                    ),
                    child: const Text(
                      '已缓存',
                      style: TextStyle(
                        fontSize: AppFontSize.caption,
                        color: AppColors.primary,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),

            // Loading 态
            if (isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(AppSpacing.lg),
                  child: CircularProgressIndicator(),
                ),
              )
            // 错误态 + 重试
            else if (hasError) ...[
              Row(
                children: [
                  Icon(
                    Icons.error_outline,
                    size: 16,
                    color: theme.colorScheme.error,
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  Expanded(
                    child: Text(
                      state.error ?? '摘要生成失败',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.error,
                      ),
                    ),
                  ),
                  TextButton.icon(
                    onPressed: () {
                      ref
                          .read(entryDetailProvider(widget.entryId).notifier)
                          .generateSummary();
                    },
                    icon: const Icon(Icons.refresh, size: 16),
                    label: const Text('重试'),
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.primary,
                    ),
                  ),
                ],
              ),
            ]
            // 摘要文本展示
            else if (summary != null)
              MarkdownBody(
                data: summary,
                selectable: true,
              )
            // 空内容 - 禁用生成按钮
            else if (!hasContent)
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ElevatedButton.icon(
                    onPressed: null,
                    icon: const Icon(Icons.auto_awesome, size: 18),
                    label: const Text('生成摘要'),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    '内容为空，无法生成摘要',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              )
            // 生成按钮
            else
              ElevatedButton.icon(
                onPressed: () {
                  ref
                      .read(entryDetailProvider(widget.entryId).notifier)
                      .generateSummary();
                },
                icon: const Icon(Icons.auto_awesome, size: 18),
                label: const Text('生成摘要'),
              ),
          ],
        ),
      ),
    );
  }

  // ============================================================
  // 知识上下文卡片
  // ============================================================
  Widget _buildKnowledgeContextCard(
      EntryDetailState state,
      ThemeData theme,) {
    final context = state.knowledgeContext;

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Section 标题行
            Row(
              children: [
                const Icon(
                  Icons.account_tree_outlined,
                  size: 18,
                  color: AppColors.primary,
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  '知识上下文',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),

            // 概念列表
            if (context == null || context.nodes.isEmpty)
              Text(
                '暂无知识关联',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              )
            else
              ...context.nodes.map((node) => _buildConceptNode(node, theme)),
          ],
        ),
      ),
    );
  }

  // ============================================================
  // 关联条目 Section
  // ============================================================
  Widget _buildEntryLinksSection(EntryDetailState state, ThemeData theme) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Section 标题行 + 添加按钮
            Row(
              children: [
                const Icon(
                  Icons.link_outlined,
                  size: 18,
                  color: AppColors.primary,
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  '关联条目',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                _buildAddLinkButton(theme),
              ],
            ),
            const SizedBox(height: AppSpacing.md),

            // 关联列表
            if (state.entryLinks.isEmpty)
              Text(
                '暂无关联条目，点击右上角添加',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              )
            else
              ...state.entryLinks.map(
                (link) => _buildLinkItem(link, state, theme),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildAddLinkButton(ThemeData theme) {
    return SizedBox(
      height: 32,
      child: TextButton.icon(
        onPressed: () => _showAddLinkDialog(theme),
        icon: const Icon(Icons.add_link, size: 16),
        label: const Text('添加关联', style: TextStyle(fontSize: AppFontSize.caption)),
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primary,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
        ),
      ),
    );
  }

  Widget _buildLinkItem(
      EntryLinkItem link,
      EntryDetailState state,
      ThemeData theme,) {
    // 确定 display entry: 优先用 targetEntry
    final displayEntry = link.targetEntry;
    final displayTitle = displayEntry?.title ?? '已删除的条目';
    final displayCategory = displayEntry?.category;
    final relationLabel = _relationTypeLabel(link.relationType);

    return Dismissible(
      key: ValueKey(link.linkId),
      direction: DismissDirection.endToStart,
      confirmDismiss: (_) => _confirmDeleteLink(link.linkId),
      onDismissed: (_) {
        ref.read(entryDetailProvider(widget.entryId).notifier).deleteLink(
              linkId: link.linkId,
            );
      },
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: AppSpacing.lg),
        decoration: BoxDecoration(
          color: AppColors.error.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(AppRadius.button),
        ),
        child: const Icon(Icons.delete_outline, color: AppColors.error),
      ),
      child: InkWell(
        onTap: displayEntry != null
            ? () => _navigateToEntry(displayEntry.id)
            : null,
        borderRadius: BorderRadius.circular(AppRadius.button),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            vertical: AppSpacing.sm,
            horizontal: AppSpacing.xs,
          ),
          child: Row(
            children: [
              // 分类图标
              if (displayCategory != null)
                Icon(
                  CategoryMeta.iconOf(displayCategory),
                  size: 18,
                  color: CategoryMeta.colorOf(displayCategory),
                )
              else
                const Icon(Icons.article_outlined, size: 18),
              const SizedBox(width: AppSpacing.sm),

              // 标题
              Expanded(
                child: Text(
                  displayTitle,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    decoration: displayEntry == null
                        ? TextDecoration.lineThrough
                        : null,
                    color: displayEntry == null
                        ? theme.colorScheme.onSurfaceVariant
                        : null,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),

              // 关联类型标签
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.sm,
                  vertical: 2,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(AppRadius.button),
                ),
                child: Text(
                  relationLabel,
                  style: const TextStyle(
                    fontSize: AppFontSize.caption,
                    color: AppColors.primary,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ============================================================
  // 反向引用 Section
  // ============================================================
  Widget _buildBacklinksSection(EntryDetailState state, ThemeData theme) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Section 标题行
            Row(
              children: [
                const Icon(
                  Icons.reply_outlined,
                  size: 18,
                  color: AppColors.primary,
                ),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  '反向引用',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (state.backlinks.isNotEmpty) ...[
                  const SizedBox(width: AppSpacing.sm),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(AppRadius.button),
                    ),
                    child: Text(
                      '${state.backlinks.length}',
                      style: TextStyle(
                        fontSize: AppFontSize.caption,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: AppSpacing.md),

            // 反向引用列表
            if (state.backlinks.isEmpty)
              Text(
                '暂无其他条目引用此条目',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              )
            else
              ...state.backlinks.map(
                (backlink) => _buildBacklinkItem(backlink, theme),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildBacklinkItem(BacklinkItem backlink, ThemeData theme) {
    return InkWell(
      onTap: () => _navigateToEntry(backlink.id),
      borderRadius: BorderRadius.circular(AppRadius.button),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          vertical: AppSpacing.sm,
          horizontal: AppSpacing.xs,
        ),
        child: Row(
          children: [
            // 分类图标
            if (backlink.category != null)
              Icon(
                CategoryMeta.iconOf(backlink.category!),
                size: 18,
                color: CategoryMeta.colorOf(backlink.category!),
              )
            else
              const Icon(Icons.article_outlined, size: 18),
            const SizedBox(width: AppSpacing.sm),

            // 标题
            Expanded(
              child: Text(
                backlink.title,
                style: theme.textTheme.bodyMedium,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),

            // 关联类型标签
            if (backlink.relationType != null)
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.sm,
                  vertical: 2,
                ),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(AppRadius.button),
                ),
                child: Text(
                  _relationTypeLabel(backlink.relationType!),
                  style: TextStyle(
                    fontSize: AppFontSize.caption,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  // ============================================================
  // 添加关联对话框
  // ============================================================
  void _showAddLinkDialog(ThemeData theme) {
    final searchController = TextEditingController();
    String selectedRelationType = 'related';

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setDialogState) {
            return AlertDialog(
              title: const Text('添加关联'),
              content: SizedBox(
                width: double.maxFinite,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 搜索框
                    TextField(
                      controller: searchController,
                      decoration: InputDecoration(
                        hintText: '搜索条目...',
                        prefixIcon: const Icon(Icons.search, size: 20),
                        suffixIcon: searchController.text.isNotEmpty
                            ? IconButton(
                                icon: const Icon(Icons.clear, size: 18),
                                onPressed: () {
                                  searchController.clear();
                                  // 清除搜索结果
                                  ref
                                      .read(entryDetailProvider(widget.entryId)
                                          .notifier,)
                                      .searchEntriesForLink(query: '');
                                  setDialogState(() {});
                                },
                              )
                            : null,
                        isDense: true,
                        border: const OutlineInputBorder(),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md,
                          vertical: AppSpacing.sm,
                        ),
                      ),
                      onChanged: (value) {
                        setDialogState(() {});
                        if (value.trim().isNotEmpty) {
                          ref
                              .read(entryDetailProvider(widget.entryId)
                                  .notifier,)
                              .searchEntriesForLink(query: value.trim());
                        }
                      },
                    ),
                    const SizedBox(height: AppSpacing.md),

                    // 关联类型选择
                    Text(
                      '关联类型',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    DropdownButtonFormField<String>(
                      value: selectedRelationType,
                      decoration: const InputDecoration(
                        isDense: true,
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(
                          horizontal: AppSpacing.md,
                          vertical: AppSpacing.sm,
                        ),
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'related',
                          child: Text('相关'),
                        ),
                        DropdownMenuItem(
                          value: 'depends_on',
                          child: Text('依赖'),
                        ),
                        DropdownMenuItem(
                          value: 'derived_from',
                          child: Text('来源'),
                        ),
                        DropdownMenuItem(
                          value: 'references',
                          child: Text('引用'),
                        ),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          selectedRelationType = value;
                          setDialogState(() {});
                        }
                      },
                    ),
                    const SizedBox(height: AppSpacing.md),

                    // 搜索结果列表
                    Consumer(
                      builder: (ctx, ref, _) {
                        final detailState = ref
                            .watch(entryDetailProvider(widget.entryId));
                        if (detailState.isSearching) {
                          return const Padding(
                            padding: EdgeInsets.all(AppSpacing.lg),
                            child: Center(
                              child: SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              ),
                            ),
                          );
                        }
                        if (searchController.text.trim().isEmpty) {
                          return const SizedBox.shrink();
                        }
                        if (detailState.searchResults.isEmpty) {
                          return Padding(
                            padding: const EdgeInsets.all(AppSpacing.md),
                            child: Text(
                              '未找到匹配条目',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                            ),
                          );
                        }
                        return ConstrainedBox(
                          constraints: const BoxConstraints(maxHeight: 200),
                          child: ListView.separated(
                            shrinkWrap: true,
                            itemCount: detailState.searchResults.length,
                            separatorBuilder: (_, __) => const Divider(height: 1),
                            itemBuilder: (ctx, index) {
                              final entry = detailState.searchResults[index];
                              // 排除自身
                              if (entry.id == widget.entryId) {
                                return const SizedBox.shrink();
                              }
                              return ListTile(
                                dense: true,
                                leading: Icon(
                                  CategoryMeta.iconOf(entry.category),
                                  size: 18,
                                  color: CategoryMeta.colorOf(entry.category),
                                ),
                                title: Text(
                                  entry.title,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                trailing: const Icon(Icons.add_circle_outline, size: 20),
                                onTap: () async {
                                  final notifier = ref.read(
                                    entryDetailProvider(widget.entryId)
                                        .notifier,
                                  );
                                  final success = await notifier.createLink(
                                    targetId: entry.id,
                                    relationType: selectedRelationType,
                                  );
                                  if (ctx.mounted) {
                                    Navigator.of(ctx).pop();
                                  }
                                  if (!mounted) return;
                                  if (success) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('关联创建成功'),
                                        duration: Duration(seconds: 2),
                                      ),
                                    );
                                  } else {
                                    final errMsg = ref
                                        .read(entryDetailProvider(widget.entryId))
                                        .error;
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text(errMsg ?? '关联创建失败'),
                                        backgroundColor: AppColors.error,
                                        duration: const Duration(seconds: 3),
                                      ),
                                    );
                                  }
                                },
                              );
                            },
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('取消'),
                ),
              ],
            );
          },
        );
      },
    ).then((_) {
      searchController.dispose();
    });
  }

  /// 跳转到条目详情页
  void _navigateToEntry(String entryId) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => EntryDetailPage(entryId: entryId),
      ),
    );
  }

  /// 确认删除关联
  Future<bool?> _confirmDeleteLink(String linkId) {
    return showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('删除关联'),
        content: const Text('确定删除此关联吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('删除'),
          ),
        ],
      ),
    );
  }

  String _relationTypeLabel(String relationType) {
    switch (relationType) {
      case 'related':
        return '相关';
      case 'depends_on':
        return '依赖';
      case 'derived_from':
        return '来源';
      case 'references':
        return '引用';
      default:
        return relationType;
    }
  }

  Widget _buildConceptNode(Map<String, dynamic> node, ThemeData theme) {
    final name = node['name'] as String? ?? '未知概念';
    final mastery = node['mastery'] as String?;
    final entryCount = node['entry_count'] as int? ?? 0;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        children: [
          // 概念名
          Expanded(
            child: Text(
              name,
              style: theme.textTheme.bodyMedium,
            ),
          ),
          const SizedBox(width: AppSpacing.sm),

          // mastery 等级标签
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm,
              vertical: 2,
            ),
            decoration: BoxDecoration(
              color: _masteryColor(mastery).withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(AppRadius.button),
            ),
            child: Text(
              _masteryLabel(mastery),
              style: TextStyle(
                fontSize: AppFontSize.caption,
                color: _masteryColor(mastery),
              ),
            ),
          ),

          // entry_count 数字
          if (entryCount > 0) ...[
            const SizedBox(width: AppSpacing.xs),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm,
                vertical: 2,
              ),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(AppRadius.button),
              ),
              child: Text(
                '$entryCount 篇',
                style: TextStyle(
                  fontSize: AppFontSize.caption,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _masteryLabel(String? mastery) {
    switch (mastery) {
      case 'beginner':
        return '入门';
      case 'intermediate':
        return '进阶';
      case 'advanced':
        return '精通';
      default:
        return '未评估';
    }
  }

  Color _masteryColor(String? mastery) {
    switch (mastery) {
      case 'beginner':
        return AppColors.waitStart;
      case 'intermediate':
        return AppColors.doing;
      case 'advanced':
        return AppColors.completed;
      default:
        return AppColors.waitStart;
    }
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
