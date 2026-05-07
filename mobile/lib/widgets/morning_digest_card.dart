import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../config/theme.dart';
import '../models/morning_digest.dart';
import '../providers/today_provider.dart';

// ============================================================
// MorningDigestCard - 晨报摘要卡片
//
// 三态：loading / loaded / error
// loading: 骨架屏 shimmer 效果
// loaded: 显示日期、AI 摘要、关键建议
// error: 不显示卡片（不阻塞页面）
// ============================================================
class MorningDigestCard extends StatelessWidget {
  final MorningDigestState morningDigest;

  const MorningDigestCard({
    super.key,
    required this.morningDigest,
  });

  @override
  Widget build(BuildContext context) {
    // error 或 initial 或 loaded 但无数据 → 不显示
    if (morningDigest.status == MorningDigestStatus.error) {
      return const SizedBox.shrink();
    }

    if (morningDigest.status == MorningDigestStatus.initial) {
      return const SizedBox.shrink();
    }

    // loading 态 → 骨架屏
    if (morningDigest.status == MorningDigestStatus.loading) {
      return const _DigestSkeleton();
    }

    // loaded 但无数据 → 不显示
    final data = morningDigest.data;
    if (data == null) {
      return const SizedBox.shrink();
    }

    // 有数据，显示卡片
    return _DigestContent(digest: data);
  }
}

// ============================================================
// _DigestContent - 晨报内容
// ============================================================
class _DigestContent extends StatelessWidget {
  final MorningDigest digest;

  const _DigestContent({required this.digest});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.sm,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 顶部：日期 + 连续天数
            _buildHeader(theme),
            const SizedBox(height: AppSpacing.md),

            // AI 建议（Markdown 渲染）
            if (digest.aiSuggestion.isNotEmpty) ...[
              _buildAiSuggestion(context, theme),
              const SizedBox(height: AppSpacing.md),
            ],

            // 待办 + 逾期概要
            if (digest.todos.isNotEmpty || digest.overdue.isNotEmpty)
              _buildTodoSummary(theme),

            // 每日聚焦
            if (digest.dailyFocus != null) ...[
              const SizedBox(height: AppSpacing.md),
              _buildDailyFocus(theme),
            ],

            // 模式洞察
            if (digest.patternInsights.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.md),
              _buildPatternInsights(theme),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(ThemeData theme) {
    return Row(
      children: [
        const Icon(
          Icons.wb_sunny_outlined,
          size: 20,
          color: AppColors.warning,
        ),
        const SizedBox(width: AppSpacing.sm),
        Text(
          '晨报',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const Spacer(),
        Text(
          digest.date,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        if (digest.learningStreak > 0) ...[
          const SizedBox(width: AppSpacing.sm),
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm,
              vertical: 2,
            ),
            decoration: BoxDecoration(
              color: AppColors.success.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(AppRadius.button),
            ),
            child: Text(
              '${digest.learningStreak} 天连续',
              style: const TextStyle(
                fontSize: AppFontSize.caption,
                color: AppColors.success,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildAiSuggestion(BuildContext context, ThemeData theme) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.primary.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(AppRadius.button),
      ),
      child: MarkdownBody(
        data: digest.aiSuggestion,
        styleSheet: MarkdownStyleSheet(
          p: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurface,
            height: 1.5,
          ),
        ),
      ),
    );
  }

  Widget _buildTodoSummary(ThemeData theme) {
    return Row(
      children: [
        if (digest.todos.isNotEmpty)
          _buildChip(
            '${digest.todos.length} 个待办',
            AppColors.primary,
          ),
        if (digest.overdue.isNotEmpty) ...[
          if (digest.todos.isNotEmpty)
            const SizedBox(width: AppSpacing.sm),
          _buildChip(
            '${digest.overdue.length} 个逾期',
            AppColors.error,
          ),
        ],
      ],
    );
  }

  Widget _buildChip(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppRadius.button),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: AppFontSize.caption,
          color: color,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildDailyFocus(ThemeData theme) {
    final focus = digest.dailyFocus!;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        border: Border.all(
          color: AppColors.primary.withValues(alpha: 0.2),
        ),
        borderRadius: BorderRadius.circular(AppRadius.button),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.center_focus_strong,
            size: 18,
            color: AppColors.primary,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  focus.title,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                if (focus.description.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    focus.description,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPatternInsights(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              Icons.insights_outlined,
              size: 16,
              color: theme.colorScheme.onSurfaceVariant,
            ),
            const SizedBox(width: AppSpacing.xs),
            Text(
              '洞察',
              style: theme.textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        ...digest.patternInsights.take(3).map(
              (insight) => Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '  \u2022  ',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    Expanded(
                      child: Text(
                        insight,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
      ],
    );
  }
}

// ============================================================
// _DigestSkeleton - 加载骨架屏
// ============================================================
class _DigestSkeleton extends StatefulWidget {
  const _DigestSkeleton();

  @override
  State<_DigestSkeleton> createState() => _DigestSkeletonState();
}

class _DigestSkeletonState extends State<_DigestSkeleton>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.sm,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题行
            Row(
              children: [
                _shimmerBox(20, 20, const Radius.circular(4)),
                const SizedBox(width: AppSpacing.sm),
                _shimmerBox(40, 16, const Radius.circular(4)),
                const Spacer(),
                _shimmerBox(80, 12, const Radius.circular(4)),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            // 摘要区域
            _shimmerBox(double.infinity, 14, const Radius.circular(4)),
            const SizedBox(height: AppSpacing.sm),
            _shimmerBox(double.infinity, 14, const Radius.circular(4)),
            const SizedBox(height: AppSpacing.sm),
            _shimmerBox(200, 14, const Radius.circular(4)),
            const SizedBox(height: AppSpacing.md),
            // chips
            Row(
              children: [
                _shimmerBox(60, 24, const Radius.circular(AppRadius.button)),
                const SizedBox(width: AppSpacing.sm),
                _shimmerBox(60, 24, const Radius.circular(AppRadius.button)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _shimmerBox(double width, double height, Radius borderRadius) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          width: width,
          height: height,
          decoration: BoxDecoration(
            color: Colors.grey
                .withValues(alpha: 0.15 + 0.1 * _controller.value),
            borderRadius: BorderRadius.all(borderRadius),
          ),
        );
      },
    );
  }
}
