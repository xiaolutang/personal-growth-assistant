import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Header } from "@/components/layout/Header";
import { ActivityHeatmap } from "@/components/ActivityHeatmap";
import {
  CheckCircle,
  FileText,
  TrendingUp,
  BarChart3,
  Calendar,
  Target,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  getDailyReport,
  getWeeklyReport,
  getMonthlyReport,
  getProgressSummary,
  getInsights,
  type DailyReport,
  type WeeklyReport,
  type MonthlyReport,
  type TaskStats,
  type NoteStats,
  type VsLastPeriod,
  type ProgressSummaryResponse,
  type InsightsResponse,
} from "@/services/api";
import { TrendChart } from "@/components/review/TrendChart";
import { MorningDigestCard } from "@/components/review/MorningDigestCard";
import { HeatmapCard } from "@/components/review/HeatmapCard";
import { GrowthCurveCard } from "@/components/review/GrowthCurveCard";
import { AiSummaryCard } from "@/components/review/AiSummaryCard";
import { InsightCard } from "@/components/review/InsightCard";
import { PageChatPanel } from "@/components/PageChatPanel";

type ReportType = "daily" | "weekly" | "monthly" | "trend";

export function Review() {
  const [reportType, setReportType] = useState<ReportType>("daily");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [dailyReport, setDailyReport] = useState<DailyReport | null>(null);
  const [weeklyReport, setWeeklyReport] = useState<WeeklyReport | null>(null);
  const [monthlyReport, setMonthlyReport] = useState<MonthlyReport | null>(null);

  // 目标进展概览
  const [goalSummary, setGoalSummary] = useState<ProgressSummaryResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchReport = async () => {
      setIsLoading(true);
      setError(null);
      try {
        if (reportType === "daily") {
          const data = await getDailyReport();
          if (!cancelled) setDailyReport(data);
        } else if (reportType === "weekly") {
          const data = await getWeeklyReport();
          if (!cancelled) setWeeklyReport(data);
        } else if (reportType === "monthly") {
          const data = await getMonthlyReport();
          if (!cancelled) setMonthlyReport(data);
        }
      } catch (err) {
        if (!cancelled) setError("加载失败，请重试");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    if (reportType !== "trend") {
      fetchReport();
    } else {
      setIsLoading(false);
    }

    return () => { cancelled = true; };
  }, [reportType, retryKey]);

  // 目标进展概览
  useEffect(() => {
    let cancelled = false;
    getProgressSummary(reportType === "monthly" ? "monthly" : "weekly")
      .then((data) => { if (!cancelled) setGoalSummary(data); })
      .catch(() => { if (!cancelled) setGoalSummary(null); });
    return () => { cancelled = true; };
  }, [reportType]);

  // 统一获取 insights 数据（InsightCard + AiSummaryCard 共享）
  const [insightsData, setInsightsData] = useState<InsightsResponse | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);

  useEffect(() => {
    if (reportType !== "weekly" && reportType !== "monthly") {
      setInsightsData(null);
      return;
    }
    let cancelled = false;
    setInsightsLoading(true);
    const period = reportType === "monthly" ? "monthly" : "weekly";
    getInsights(period)
      .then((data) => { if (!cancelled) setInsightsData(data); })
      .catch(() => { if (!cancelled) setInsightsData(null); })
      .finally(() => { if (!cancelled) setInsightsLoading(false); });
    return () => { cancelled = true; };
  }, [reportType]);

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
  };

  const getTaskStats = (): TaskStats | null => {
    if (reportType === "daily") return dailyReport?.task_stats || null;
    if (reportType === "weekly") return weeklyReport?.task_stats || null;
    return monthlyReport?.task_stats || null;
  };

  const getNoteStats = (): NoteStats | null => {
    if (reportType === "daily") return dailyReport?.note_stats || null;
    if (reportType === "weekly") return weeklyReport?.note_stats || null;
    return monthlyReport?.note_stats || null;
  };

  const getAiSummary = (): string | null => {
    if (reportType === "daily") return dailyReport?.ai_summary ?? null;
    if (reportType === "weekly") return weeklyReport?.ai_summary ?? null;
    if (reportType === "monthly") return monthlyReport?.ai_summary ?? null;
    return null;
  };

  const taskStats = getTaskStats();
  const noteStats = getNoteStats();
  const aiSummary = getAiSummary();

  // 环比标签渲染
  const renderDeltaLabel = (label: string, delta: VsLastPeriod | null | undefined) => {
    if (!delta || delta.delta_total === null || delta.delta_completion_rate === null) return null;
    const rateSign = delta.delta_completion_rate >= 0 ? "+" : "";
    const totalSign = delta.delta_total >= 0 ? "+" : "";
    const rateColor = delta.delta_completion_rate >= 0 ? "text-green-600 dark:text-green-400" : "text-red-500";
    const totalColor = delta.delta_total >= 0 ? "text-green-600 dark:text-green-400" : "text-red-500";
    return (
      <div className="flex gap-3 text-xs mt-1">
        <span>vs {label}：</span>
        <span className={rateColor}>完成率 {rateSign}{delta.delta_completion_rate.toFixed(1)}%</span>
        <span className={totalColor}>任务 {totalSign}{delta.delta_total}</span>
      </div>
    );
  };

  return (
    <>
      <Header title="成长回顾" />
      <main className="flex-1 p-4 md:p-6 pb-32 overflow-y-auto">
        {/* 报告类型选择 */}
        <div className="flex gap-2 mb-6">
          {(["daily", "weekly", "monthly", "trend"] as ReportType[]).map((type) => (
            <Badge
              key={type}
              variant={reportType === type ? "default" : "outline"}
              className="cursor-pointer px-4 py-2"
              onClick={() => setReportType(type)}
            >
              {type === "daily" ? "日报" : type === "weekly" ? "周报" : type === "monthly" ? "月报" : "趋势"}
            </Badge>
          ))}
        </div>

        {/* 活动热力图 */}
        <div className="mb-6">
          <ActivityHeatmap />
        </div>

        {/* 趋势标签页内容 */}
        {reportType === "trend" ? (
          <div className="space-y-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  完成率趋势
                </CardTitle>
              </CardHeader>
              <CardContent>
                <TrendChart />
              </CardContent>
            </Card>
            <GrowthCurveCard />
            <HeatmapCard />
          </div>
        ) : (
          <>
            {/* 晨报卡片（仅日报，在顶部） */}
            <MorningDigestCard visible={reportType === "daily"} />

            {/* 趋势折线图卡片 */}
            <Card className="mb-6">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  完成率趋势
                </CardTitle>
              </CardHeader>
              <CardContent>
                <TrendChart
                  footer={
                    <>
                      {reportType === "weekly" && renderDeltaLabel("上周", weeklyReport?.vs_last_week)}
                      {reportType === "monthly" && renderDeltaLabel("上月", monthlyReport?.vs_last_month)}
                    </>
                  }
                />
              </CardContent>
            </Card>

            {/* AI 总结卡片 */}
            <AiSummaryCard reportType={reportType} isLoading={isLoading} aiSummary={aiSummary} insightsData={insightsData} insightsLoading={insightsLoading} />

            {/* AI 深度洞察卡片 — 仅周报/月报 */}
            <InsightCard reportType={reportType} insightsData={insightsData} insightsLoading={insightsLoading} />

            {/* 分析助手 AI */}
            <PageChatPanel
              title="分析助手"
              welcomeMessage="想深入了解哪些数据？我可以帮你分析"
              suggestions={[
                { label: "分析趋势", message: "帮我分析最近的任务完成趋势" },
                { label: "比较环比", message: "这周和上周相比有什么变化？" },
                { label: "学习模式", message: "从数据中能看到什么学习模式？" },
              ]}
              pageContext={{ page: "review" }}
              pageData={{
                report_type: reportType,
                total_tasks: taskStats?.total ?? 0,
                completed: taskStats?.completed ?? 0,
                completion_rate: taskStats?.completion_rate ?? 0,
                doing: taskStats?.doing ?? 0,
                wait_start: taskStats?.wait_start ?? 0,
                note_count: noteStats?.total ?? 0,
                recent_notes: noteStats?.recent_titles?.slice(0, 3).join(", ") ?? "",
                ai_summary_available: aiSummary ? "yes" : "no",
                weekly_delta_completion_rate: weeklyReport?.vs_last_week?.delta_completion_rate ?? "N/A",
                weekly_delta_total: weeklyReport?.vs_last_week?.delta_total ?? "N/A",
                monthly_delta_completion_rate: monthlyReport?.vs_last_month?.delta_completion_rate ?? "N/A",
                monthly_delta_total: monthlyReport?.vs_last_month?.delta_total ?? "N/A",
                goal_active_count: goalSummary?.active_count ?? 0,
                goal_completed_count: goalSummary?.completed_count ?? 0,
              }}
              defaultCollapsed
            />

            {/* 目标进展概览（仅周报/月报） */}
            {(reportType === "weekly" || reportType === "monthly") && goalSummary && (goalSummary.active_count + goalSummary.completed_count > 0) && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    目标进展
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-3 mb-4">
                    <div className="text-center flex-1">
                      <p className="text-2xl font-bold text-primary">{goalSummary.active_count}</p>
                      <p className="text-xs text-muted-foreground">进行中</p>
                    </div>
                    <div className="text-center flex-1">
                      <p className="text-2xl font-bold text-green-600 dark:text-green-400">{goalSummary.completed_count}</p>
                      <p className="text-xs text-muted-foreground">已完成</p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {goalSummary.goals.map(g => (
                      <div key={g.id} className="flex items-center gap-3">
                        <span className="text-sm truncate flex-1">{g.title}</span>
                        {g.progress_delta != null && (
                          <span className={`text-xs font-medium shrink-0 ${g.progress_delta > 0 ? "text-green-600 dark:text-green-400" : g.progress_delta < 0 ? "text-red-500" : "text-muted-foreground"}`}>
                            {g.progress_delta > 0 ? "+" : ""}{g.progress_delta}%
                          </span>
                        )}
                        <div className="w-20 shrink-0">
                          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-primary transition-all" style={{ width: `${g.progress_percentage}%` }} />
                          </div>
                        </div>
                        <span className="text-xs text-muted-foreground w-10 text-right">{Math.round(g.progress_percentage)}%</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {isLoading ? (
              <div className="flex items-center justify-center h-64 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
                <AlertCircle className="h-8 w-8" />
                <p>{error}</p>
                <button
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm"
                  onClick={() => setRetryKey((k) => k + 1)}
                >
                  重试
                </button>
              </div>
            ) : (
              <div className="space-y-6">
                {/* 任务统计卡片 */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <CheckCircle className="h-4 w-4" />
                      任务统计
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {taskStats ? (
                      <div className="space-y-4">
                        <div>
                          <div className="flex justify-between text-sm mb-1">
                            <span>完成率</span>
                            <span className="font-medium">{taskStats.completion_rate}%</span>
                          </div>
                          <Progress value={taskStats.completion_rate} />
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="text-center">
                            <div className="text-2xl font-bold">{taskStats.total}</div>
                            <div className="text-xs text-muted-foreground">总任务</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-green-500 dark:text-green-400">{taskStats.completed}</div>
                            <div className="text-xs text-muted-foreground">已完成</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-yellow-500 dark:text-yellow-400">{taskStats.doing}</div>
                            <div className="text-xs text-muted-foreground">进行中</div>
                          </div>
                          <div className="text-center">
                            <div className="text-2xl font-bold text-gray-400 dark:text-gray-500">{taskStats.wait_start}</div>
                            <div className="text-xs text-muted-foreground">待开始</div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-muted-foreground">暂无数据</div>
                    )}
                  </CardContent>
                </Card>

                {/* 笔记统计卡片 */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      学习内容
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {noteStats ? (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary">{noteStats.total} 篇笔记</Badge>
                        </div>
                        {noteStats.recent_titles.length > 0 && (
                          <div className="space-y-1">
                            <div className="text-xs text-muted-foreground">最近记录：</div>
                            {noteStats.recent_titles.map((title, i) => (
                              <div key={i} className="text-sm truncate">• {title}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-muted-foreground">暂无数据</div>
                    )}
                  </CardContent>
                </Card>

                {/* 每日分解（周报） */}
                {reportType === "weekly" && weeklyReport?.daily_breakdown && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base flex items-center gap-2">
                        <BarChart3 className="h-4 w-4" />
                        每日分解
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {weeklyReport.daily_breakdown.map((day) => (
                          <div key={day.date} className="flex items-center justify-between p-2 rounded-lg bg-muted/30">
                            <div className="flex items-center gap-2">
                              <Calendar className="h-4 w-4 text-muted-foreground" />
                              <span className="text-sm">{formatDate(day.date)}</span>
                            </div>
                            <div className="flex items-center gap-4 text-sm">
                              <span>{day.total} 个任务</span>
                              <span className="text-green-500 dark:text-green-400">{day.completed} 完成</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* 周分解（月报） */}
                {reportType === "monthly" && monthlyReport?.weekly_breakdown && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" />
                        周度分解
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {monthlyReport.weekly_breakdown.map((week) => (
                          <div key={week.week} className="flex items-center justify-between p-2 rounded-lg bg-muted/30">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium">{week.week}</span>
                              <span className="text-xs text-muted-foreground">
                                {formatDate(week.start_date)} - {formatDate(week.end_date)}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-sm">
                              <span>{week.total} 个任务</span>
                              <span className="text-green-500 dark:text-green-400">{week.completed} 完成</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* 已完成任务（日报） */}
                {reportType === "daily" && dailyReport?.completed_tasks && dailyReport.completed_tasks.length > 0 && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-green-500 dark:text-green-400" />
                        今日完成 ({dailyReport.completed_tasks.length})
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {dailyReport.completed_tasks.map((task) => (
                          <div key={task.id} className="flex items-center gap-2 p-2 rounded-lg bg-green-50 dark:bg-green-950/20">
                            <CheckCircle className="h-4 w-4 text-green-500 dark:text-green-400" />
                            <span className="text-sm">{task.title}</span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </>
  );
}
