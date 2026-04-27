import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/theme.dart';
import '../providers/review_provider.dart';

// ============================================================
// ReviewPage - 统计回顾页
//
// 功能：
// - 周报/月报切换（SegmentedButton）
// - 概览卡片：条目数、完成率、学习天数
// - 趋势折线图（CustomPainter，无第三方图表库）
// - AI 洞察卡片列表
// ============================================================

class ReviewPage extends ConsumerStatefulWidget {
  const ReviewPage({super.key});

  @override
  ConsumerState<ReviewPage> createState() => _ReviewPageState();
}

class _ReviewPageState extends ConsumerState<ReviewPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadAll();
    });
  }

  Future<void> _loadAll() {
    final notifier = ref.read(reviewProvider.notifier);
    return notifier.loadAll();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(reviewProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('回顾'),
        centerTitle: true,
      ),
      body: Column(
        children: [
          _buildPeriodToggle(state, theme),
          Expanded(child: _buildBody(state, theme)),
        ],
      ),
    );
  }

  // ----------------------------------------------------------
  // 周期切换
  // ----------------------------------------------------------
  Widget _buildPeriodToggle(ReviewState state, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: SegmentedButton<String>(
        segments: const [
          ButtonSegment(value: 'weekly', label: Text('本周')),
          ButtonSegment(value: 'monthly', label: Text('本月')),
        ],
        selected: {state.selectedPeriod},
        onSelectionChanged: (selected) {
          final notifier = ref.read(reviewProvider.notifier);
          notifier.loadAll(selected.first);
        },
      ),
    );
  }

  // ----------------------------------------------------------
  // 主体内容：加载中 / 错误 / 数据
  // ----------------------------------------------------------
  Widget _buildBody(ReviewState state, ThemeData theme) {
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline,
                size: 48, color: theme.colorScheme.error,),
            const SizedBox(height: AppSpacing.md),
            Text(state.error!,
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.error),),
            const SizedBox(height: AppSpacing.lg),
            FilledButton.tonal(
              onPressed: _loadAll,
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async => _loadAll(),
      child: ListView(
        padding: const EdgeInsets.only(bottom: AppSpacing.xxl),
        children: [
          // 概览
          _buildSectionTitle('概览', theme),
          if (state.summary != null)
            _buildOverview(state.summary!, theme)
          else
            _buildEmptyHint('暂无概览数据', theme),

          const SizedBox(height: AppSpacing.lg),

          // 趋势图
          _buildSectionTitle('活动趋势', theme),
          if (state.trends != null)
            _buildTrendChart(state.trends!, theme)
          else
            _buildEmptyHint('暂无趋势数据', theme),

          const SizedBox(height: AppSpacing.lg),

          // AI 洞察
          if (state.insights != null)
            _buildInsights(state.insights!, theme)
          else
            _buildEmptyHint('暂无洞察', theme),
        ],
      ),
    );
  }

  // ----------------------------------------------------------
  // 小节标题
  // ----------------------------------------------------------
  Widget _buildSectionTitle(String title, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md, vertical: AppSpacing.sm,),
      child: Text(title, style: theme.textTheme.titleMedium),
    );
  }

  // ----------------------------------------------------------
  // 空提示
  // ----------------------------------------------------------
  Widget _buildEmptyHint(String text, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Text(
        text,
        style: theme.textTheme.bodyMedium
            ?.copyWith(color: theme.colorScheme.outline),
      ),
    );
  }

  // ----------------------------------------------------------
  // 概览卡片行
  // ----------------------------------------------------------
  Widget _buildOverview(Map<String, dynamic> summary, ThemeData theme) {
    // 后端 WeeklyReport / MonthlyReport 结构：
    //   task_stats: { total, completed, doing, wait_start, completion_rate }
    //   note_stats: { total, recent_titles }
    //   start_date / end_date / month / ai_summary
    final taskStats =
        summary['task_stats'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final noteStats =
        summary['note_stats'] as Map<String, dynamic>? ?? <String, dynamic>{};

    final totalEntries =
        ((taskStats['total'] as num?)?.toInt() ?? 0) +
            ((noteStats['total'] as num?)?.toInt() ?? 0);
    final completionRate =
        (taskStats['completion_rate'] as num?)?.toDouble() ?? 0.0;

    return Row(
      children: [
        _buildStatCard(
          '总条目',
          '$totalEntries',
          Icons.article_outlined,
          theme,
        ),
        _buildStatCard(
          '完成率',
          '${completionRate.toStringAsFixed(0)}%',
          Icons.check_circle_outline,
          theme,
        ),
        _buildStatCard(
          '已完成',
          '${taskStats['completed'] ?? 0}',
          Icons.task_alt_outlined,
          theme,
        ),
      ],
    );
  }

  Widget _buildStatCard(
      String label, String value, IconData icon, ThemeData theme,) {
    return Expanded(
      child: Card(
        margin: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            children: [
              Icon(icon, color: theme.colorScheme.primary, size: 24),
              const SizedBox(height: AppSpacing.sm),
              Text(value, style: theme.textTheme.headlineMedium),
              const SizedBox(height: AppSpacing.xs),
              Text(label, style: theme.textTheme.bodySmall),
            ],
          ),
        ),
      ),
    );
  }

  // ----------------------------------------------------------
  // 趋势折线图
  // ----------------------------------------------------------
  Widget _buildTrendChart(Map<String, dynamic> trendsData, ThemeData theme) {
    // 后端 TrendResponse 结构：
    //   periods: [ { date, total, completed, completion_rate, notes_count, task_count, inbox_count } ]
    final periods = trendsData['periods'] as List<dynamic>? ?? [];
    if (periods.isEmpty) {
      return _buildEmptyHint('暂无趋势数据', theme);
    }

    final values = <double>[];
    final labels = <String>[];
    for (final p in periods) {
      final map = p as Map<String, dynamic>;
      values.add((map['total'] as num?)?.toDouble() ?? 0.0);
      // date 格式: "2026-04-27" 或 "2026-W17"，取最后部分作为标签
      final rawDate = '${map['date'] ?? ''}';
      final shortLabel = rawDate.length >= 10
          ? rawDate.substring(5) // "04-27"
          : rawDate;
      labels.add(shortLabel);
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: SizedBox(
          height: 180,
          child: CustomPaint(
            size: Size.infinite,
            painter: _TrendChartPainter(
              values: values,
              labels: labels,
              lineColor: theme.colorScheme.primary,
              dotColor: theme.colorScheme.primary,
            ),
          ),
        ),
      ),
    );
  }

  // ----------------------------------------------------------
  // AI 洞察卡片
  // ----------------------------------------------------------
  Widget _buildInsights(Map<String, dynamic> insightsData, ThemeData theme) {
    // 后端 InsightsResponse 结构：
    //   insights: {
    //     behavior_patterns: [ { pattern, frequency, trend } ],
    //     growth_suggestions: [ { suggestion, priority, related_area } ],
    //     capability_changes: [ { capability, previous_level, current_level, change } ],
    //   }
    final deepInsights =
        insightsData['insights'] as Map<String, dynamic>? ?? <String, dynamic>{};

    final behaviorPatterns =
        deepInsights['behavior_patterns'] as List<dynamic>? ?? [];
    final growthSuggestions =
        deepInsights['growth_suggestions'] as List<dynamic>? ?? [];
    final capabilityChanges =
        deepInsights['capability_changes'] as List<dynamic>? ?? [];

    if (behaviorPatterns.isEmpty &&
        growthSuggestions.isEmpty &&
        capabilityChanges.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Text(
          '暂无洞察',
          style: theme.textTheme.bodyMedium
              ?.copyWith(color: theme.colorScheme.outline),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionTitle('AI 洞察', theme),
        // 行为模式
        ...behaviorPatterns.map(
          (item) {
            final map = item as Map<String, dynamic>;
            final trendEmoji = switch (map['trend']) {
              'improving' => '↑',
              'declining' => '↓',
              _ => '→',
            };
            return Card(
              margin: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md, vertical: AppSpacing.xs,),
              child: ListTile(
                leading: const Icon(Icons.psychology_outlined,
                    color: Colors.deepPurple,),
                title: Text(
                  '${map['pattern'] ?? ''}',
                  style: theme.textTheme.bodyMedium,
                ),
                subtitle: Text(
                  '频率: ${map['frequency'] ?? 0}  $trendEmoji',
                  style: theme.textTheme.bodySmall,
                ),
              ),
            );
          },
        ),
        // 成长建议
        ...growthSuggestions.map(
          (item) {
            final map = item as Map<String, dynamic>;
            return Card(
              margin: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md, vertical: AppSpacing.xs,),
              child: ListTile(
                leading: const Icon(Icons.lightbulb_outline,
                    color: Colors.amber,),
                title: Text(
                  '${map['suggestion'] ?? ''}',
                  style: theme.textTheme.bodyMedium,
                ),
                subtitle: Text(
                  '优先级: ${map['priority'] ?? 'medium'}  领域: ${map['related_area'] ?? ''}',
                  style: theme.textTheme.bodySmall,
                ),
              ),
            );
          },
        ),
        // 能力变化
        ...capabilityChanges.map(
          (item) {
            final map = item as Map<String, dynamic>;
            final change = (map['change'] as num?)?.toDouble() ?? 0.0;
            final arrow = change >= 0 ? '+' : '';
            return Card(
              margin: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md, vertical: AppSpacing.xs,),
              child: ListTile(
                leading: const Icon(Icons.trending_up,
                    color: Colors.green,),
                title: Text(
                  '${map['capability'] ?? ''}',
                  style: theme.textTheme.bodyMedium,
                ),
                subtitle: Text(
                  '$arrow${change.toStringAsFixed(2)} (${(map['previous_level'] as num?)?.toDouble().toStringAsFixed(2) ?? '0.00'} → ${(map['current_level'] as num?)?.toDouble().toStringAsFixed(2) ?? '0.00'})',
                  style: theme.textTheme.bodySmall,
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}

// ============================================================
// _TrendChartPainter - 纯 CustomPainter 折线图
//
// 绘制：网格线 + 折线 + 数据点 + 底部标签
// ============================================================
class _TrendChartPainter extends CustomPainter {
  final List<double> values;
  final List<String> labels;
  final Color lineColor;
  final Color dotColor;

  _TrendChartPainter({
    required this.values,
    required this.labels,
    required this.lineColor,
    required this.dotColor,
  });

  static const double _labelHeight = 20.0;
  static const double _horizontalPadding = 16.0;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;

    final chartWidth = size.width - _horizontalPadding * 2;
    final chartHeight = size.height - _labelHeight;

    // 网格线
    final gridPaint = Paint()
      ..color = Colors.grey.withValues(alpha: 0.2)
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;

    for (int i = 0; i <= 4; i++) {
      final y = chartHeight * i / 4;
      canvas.drawLine(
        Offset(_horizontalPadding, y),
        Offset(_horizontalPadding + chartWidth, y),
        gridPaint,
      );
    }

    final maxVal = values.reduce(math.max);
    if (maxVal == 0) {
      // 画标签但不画线
      _drawLabels(canvas, size, chartWidth, chartHeight);
      return;
    }

    final stepX =
        values.length > 1 ? chartWidth / (values.length - 1) : chartWidth;

    // 填充区域
    final fillPaint = Paint()
      ..color = lineColor.withValues(alpha: 0.1)
      ..style = PaintingStyle.fill;

    final fillPath = Path();
    for (int i = 0; i < values.length; i++) {
      final x = _horizontalPadding + i * stepX;
      final y = chartHeight - (values[i] / maxVal) * (chartHeight - 8);
      if (i == 0) {
        fillPath.moveTo(x, y);
      } else {
        fillPath.lineTo(x, y);
      }
    }
    fillPath.lineTo(
        _horizontalPadding + (values.length - 1) * stepX, chartHeight,);
    fillPath.lineTo(_horizontalPadding, chartHeight);
    fillPath.close();
    canvas.drawPath(fillPath, fillPaint);

    // 折线
    final linePaint = Paint()
      ..color = lineColor
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final path = Path();
    for (int i = 0; i < values.length; i++) {
      final x = _horizontalPadding + i * stepX;
      final y = chartHeight - (values[i] / maxVal) * (chartHeight - 8);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    canvas.drawPath(path, linePaint);

    // 数据点
    final dotPaint = Paint()
      ..color = dotColor
      ..style = PaintingStyle.fill;

    final dotBorderPaint = Paint()
      ..color = Colors.white
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    for (int i = 0; i < values.length; i++) {
      final x = _horizontalPadding + i * stepX;
      final y = chartHeight - (values[i] / maxVal) * (chartHeight - 8);
      canvas.drawCircle(Offset(x, y), 4, dotPaint);
      canvas.drawCircle(Offset(x, y), 4, dotBorderPaint);
    }

    // 底部标签
    _drawLabels(canvas, size, chartWidth, chartHeight);
  }

  void _drawLabels(
      Canvas canvas, Size size, double chartWidth, double chartHeight,) {
    if (labels.isEmpty) return;

    final stepX =
        values.length > 1 ? chartWidth / (values.length - 1) : chartWidth;

    final textStyle = TextStyle(
      color: Colors.grey.withValues(alpha: 0.7),
      fontSize: 10,
    );

    for (int i = 0; i < labels.length; i++) {
      final x = _horizontalPadding + i * stepX;
      final tp = TextPainter(
        text: TextSpan(text: labels[i], style: textStyle),
        textDirection: TextDirection.ltr,
      );
      tp.layout();
      tp.paint(canvas, Offset(x - tp.width / 2, chartHeight + 4));
    }
  }

  @override
  bool shouldRepaint(covariant _TrendChartPainter oldDelegate) =>
      values != oldDelegate.values ||
      labels != oldDelegate.labels ||
      lineColor != oldDelegate.lineColor ||
      dotColor != oldDelegate.dotColor;
}
