import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/constants.dart';
import '../config/theme.dart';
import '../models/chat_message.dart';
import '../providers/chat_provider.dart';
import '../providers/today_provider.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/empty_state.dart';
import '../widgets/entry_card.dart';
import '../widgets/entry_created_card.dart';
import '../widgets/error_state.dart';
import '../widgets/morning_digest_card.dart';
import '../widgets/progress_ring.dart';
// FAB 由 Shell 层全局管理

// ============================================================
// TodayPage - 今天 Tab 页面
//
// F02: 底部输入栏改为 AI 对话入口：
// - 闲聊 → AI 回复（不创建条目）
// - 灵感/任务 → 后端 Agent 判断后创建条目
// - 复用 chatProvider 的 SSE 对话能力（POST /chat）
// - page_context.page_type 传 'today'
// ============================================================
class TodayPage extends ConsumerStatefulWidget {
  const TodayPage({super.key});

  @override
  ConsumerState<TodayPage> createState() => _TodayPageState();
}

class _TodayPageState extends ConsumerState<TodayPage> {
  final _quickInputController = TextEditingController();
  final _chatScrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    // 页面初始化时加载数据
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(todayProvider.notifier).loadData();

      // F02: 监听 chatProvider 消息变化，检测 created 事件刷新 today 数据
      ref.listenManual(chatProvider, (previous, next) {
        _onChatStateChanged(previous, next);
      });
    });
  }

  /// 检测 chatProvider 中新增的 created 类型系统消息，触发 today 刷新
  void _onChatStateChanged(ChatState? previous, ChatState next) {
    final prevCount = previous?.messages.length ?? 0;
    final nextCount = next.messages.length;

    // 只在消息数量增加时检查（避免重复刷新）
    if (nextCount > prevCount) {
      // 检查新增消息中是否有 created 类型（system 角色且含创建关键字）
      final newMessages = next.messages.sublist(prevCount);
      final hasCreated = newMessages.any(
        (m) => m.role == ChatMessageRole.system && (m.isCreatedCard || m.text.contains('创建')),
      );
      if (hasCreated) {
        // Agent 创建条目后刷新 today 数据以更新最近动态
        ref.read(todayProvider.notifier).loadData();
      }
    }
  }

  @override
  void dispose() {
    _quickInputController.dispose();
    _chatScrollController.dispose();
    super.dispose();
  }

  Future<void> _handleRefresh() async {
    await ref.read(todayProvider.notifier).loadData();
  }

  /// F02: 发送消息走 POST /chat SSE 对话（page_type='today'）
  Future<void> _handleQuickSubmit() async {
    final text = _quickInputController.text.trim();
    if (text.isEmpty) return;

    _quickInputController.clear();

    // 调用 chatProvider.sendMessage()，传入 page_context
    ref.read(chatProvider.notifier).sendMessage(
          text,
          pageContext: const {'page_type': 'today'},
        );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final todayState = ref.watch(todayProvider);
    final chatState = ref.watch(chatProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('今天'),
        centerTitle: true,
      ),
      body: RefreshIndicator(
        onRefresh: _handleRefresh,
        child: todayState.isLoading && todayState.todayTasks.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : _buildContent(context, theme, todayState, chatState),
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    ThemeData theme,
    TodayState state,
    ChatState chatState,
  ) {
    // 错误状态（用 ListView 包裹以保留下拉刷新能力）
    if (state.error != null && state.todayTasks.isEmpty && state.recentEntries.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          SizedBox(
            height: MediaQuery.of(context).size.height * 0.6,
            child: ErrorStateWidget(
              message: state.error ?? '加载失败',
              onRetry: _handleRefresh,
            ),
          ),
        ],
      );
    }

    return Column(
      children: [
        Expanded(
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.only(bottom: 16),
            children: [
              // 错误提示条（有数据时用 SnackBar 风格的提示）
              if (state.error != null)
                _buildErrorBanner(state.error!),

              // 晨报卡片（顶部）
              MorningDigestCard(morningDigest: state.morningDigest),

              // 进度卡片
              _buildProgressSection(theme, state),

              const Divider(height: 1, indent: AppSpacing.lg, endIndent: AppSpacing.lg),

              // 今日任务
              _buildTasksSection(theme, state),

              const Divider(height: 1, indent: AppSpacing.lg, endIndent: AppSpacing.lg),

              // 最近动态
              _buildRecentSection(theme, state),

              // F02: 对话气泡区域（嵌入在主列表下方）
              if (chatState.messages.isNotEmpty) ...[
                const Divider(height: 1, indent: AppSpacing.lg, endIndent: AppSpacing.lg),
                _buildChatSection(theme, chatState),
              ],
            ],
          ),
        ),
        // 底部快捷录入栏（改为 AI 对话入口）
        _buildQuickInputBar(theme, chatState),
      ],
    );
  }

  /// F02: 对话气泡区域（嵌入在内容列表底部）
  Widget _buildChatSection(ThemeData theme, ChatState chatState) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.sm,
          ),
          child: Text(
            'AI 对话',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        ...chatState.messages.map((message) {
          // 创建确认卡片
          if (message.isCreatedCard) {
            return EntryCreatedCard(entry: message.createdEntry!);
          }

          // AI 消息 + 打字指示器
          final isLastMessage = message == chatState.messages.last;
          final showTyping = chatState.isLoading &&
              message.role == ChatMessageRole.assistant &&
              isLastMessage;

          return ChatBubble(
            message: message,
            showTypingIndicator: showTyping,
          );
        }),
      ],
    );
  }

  Widget _buildQuickInputBar(ThemeData theme, ChatState chatState) {
    return Container(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.sm,
        AppSpacing.sm,
        AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: theme.colorScheme.outlineVariant.withValues(alpha: 0.3),
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: _quickInputController,
                textInputAction: TextInputAction.send,
                onSubmitted: chatState.isLoading ? null : (_) => _handleQuickSubmit(),
                enabled: !chatState.isLoading,
                decoration: InputDecoration(
                  hintText: '和 AI 聊聊...',
                  hintStyle: TextStyle(
                    color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.6),
                    fontSize: AppFontSize.body,
                  ),
                  filled: true,
                  fillColor: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.sm + 2,
                  ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(AppRadius.full),
                    borderSide: BorderSide.none,
                  ),
                  isDense: true,
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            // 发送按钮（对话中显示加载指示器）
            IconButton(
              onPressed: chatState.isLoading ? null : _handleQuickSubmit,
              icon: chatState.isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: AppColors.primary,
                      ),
                    )
                  : const Icon(Icons.send_rounded),
              color: AppColors.primary,
              style: IconButton.styleFrom(
                backgroundColor: AppColors.primary.withValues(alpha: 0.1),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorBanner(String error) {
    return Container(
      margin: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.sm,
      ),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppRadius.button),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, size: 18, color: AppColors.error),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              error,
              style: const TextStyle(fontSize: AppFontSize.caption, color: AppColors.error),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressSection(ThemeData theme, TodayState state) {
    final totalTasks = state.todayTasks.length;
    final doneTasks = state.todayTasks.where(
      (e) => e.status == AppConstants.statusComplete,
    ).length;

    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Row(
        children: [
          // 进度环
          ProgressRing(progress: state.completionRate),
          const SizedBox(width: AppSpacing.xl),
          // 文字描述
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '今日进度',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  totalTasks == 0
                      ? '暂无今日任务'
                      : '已完成 $doneTasks / $totalTasks 个任务',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTasksSection(ThemeData theme, TodayState state) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.sm,
          ),
          child: Text(
            '今日任务',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        if (state.todayTasks.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(
              vertical: AppSpacing.xl,
              horizontal: AppSpacing.lg,
            ),
            child: EmptyStateWidget(
              icon: Icons.check_circle_outline,
              title: '今天暂无任务，点击 + 创建一个吧',
            ),
          )
        else
          ...state.todayTasks.map(
            (entry) => EntryCard(
              entry: entry,
              onTap: () {
                context.push('/entries/${entry.id}');
              },
            ),
          ),
      ],
    );
  }

  Widget _buildRecentSection(ThemeData theme, TodayState state) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.lg,
            AppSpacing.sm,
          ),
          child: Text(
            '最近动态',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        if (state.recentEntries.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(
              vertical: AppSpacing.xl,
              horizontal: AppSpacing.lg,
            ),
            child: EmptyStateWidget(
              icon: Icons.article_outlined,
              title: '暂无动态，开始记录你的成长吧',
            ),
          )
        else
          ...state.recentEntries.map(
            (entry) => EntryCard(
              entry: entry,
              onTap: () {
                context.push('/entries/${entry.id}');
              },
            ),
          ),
      ],
    );
  }
}
