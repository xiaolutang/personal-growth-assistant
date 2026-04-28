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
  Loader2,
  Inbox,
} from "lucide-react";
import type { VsLastPeriod } from "@/services/api";
import { TrendChart } from "@/components/review/TrendChart";
import { MorningDigestCard } from "@/components/review/MorningDigestCard";
import { HeatmapCard } from "@/components/review/HeatmapCard";
import { GrowthCurveCard } from "@/components/review/GrowthCurveCard";
import { AiSummaryCard } from "@/components/review/AiSummaryCard";
import { InsightCard } from "@/components/review/InsightCard";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { ErrorState } from "@/components/ErrorState";

// Hooks
import { useReportData } from "./review/useReportData";
import { useInsights } from "./review/useInsights";

// Sub-components
import { ReportHeader } from "./review/ReportHeader";
import { GoalProgressCard } from "./review/GoalProgressCard";

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}

export function Review() {
  const {
    reportType, setReportType,
    isLoading, error, setRetryKey,
    dailyReport, weeklyReport, monthlyReport,
    taskStats, noteStats, aiSummary, goalSummary,
    serviceUnavailable, isEmpty,
  } = useReportData();

  const { insightsData, insightsLoading } = useInsights(reportType);

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
        {serviceUnavailable ? (
          <ServiceUnavailable onRetry={() => { setRetryKey((k) => k + 1); }} />
        ) : (
        <>
        <ReportHeader reportType={reportType} onReportTypeChange={setReportType} />

        <div className="mb-6"><ActivityHeatmap /></div>

        {reportType === "trend" ? (
          <div className="space-y-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2"><TrendingUp className="h-4 w-4" />完成率趋势</CardTitle>
              </CardHeader>
              <CardContent><TrendChart /></CardContent>
            </Card>
            <GrowthCurveCard />
            <HeatmapCard />
          </div>
        ) : (
          <>
            <MorningDigestCard visible={reportType === "daily"} />

            <Card className="mb-6">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2"><TrendingUp className="h-4 w-4" />完成率趋势</CardTitle>
              </CardHeader>
              <CardContent>
                <TrendChart footer={<>{reportType === "weekly" && renderDeltaLabel("上周", weeklyReport?.vs_last_week)}{reportType === "monthly" && renderDeltaLabel("上月", monthlyReport?.vs_last_month)}</>} />
              </CardContent>
            </Card>

            <AiSummaryCard reportType={reportType} isLoading={isLoading} aiSummary={aiSummary} insightsData={insightsData} insightsLoading={insightsLoading} />
            <InsightCard reportType={reportType} insightsData={insightsData} insightsLoading={insightsLoading} />

            {(reportType === "weekly" || reportType === "monthly") && goalSummary && (goalSummary.active_count + goalSummary.completed_count > 0) && (
              <GoalProgressCard goalSummary={goalSummary} />
            )}

            {isLoading ? (
              <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm">加载报告数据...</p>
              </div>
            ) : error ? (
              <ErrorState message={error} onRetry={() => setRetryKey((k) => k + 1)} />
            ) : isEmpty ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
                  <Inbox className="h-8 w-8 text-primary" />
                </div>
                <h3 className="text-lg font-semibold mb-2">暂无报告数据</h3>
                <p className="text-sm text-muted-foreground max-w-xs">
                  开始记录任务和笔记后，这里会显示你的成长报告
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {taskStats && (
                  <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><CheckCircle className="h-4 w-4" />任务统计</CardTitle></CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div>
                          <div className="flex justify-between text-sm mb-1"><span>完成率</span><span className="font-medium">{taskStats.completion_rate}%</span></div>
                          <Progress value={taskStats.completion_rate} />
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="text-center"><div className="text-2xl font-bold">{taskStats.total}</div><div className="text-xs text-muted-foreground">总任务</div></div>
                          <div className="text-center"><div className="text-2xl font-bold text-green-500 dark:text-green-400">{taskStats.completed}</div><div className="text-xs text-muted-foreground">已完成</div></div>
                          <div className="text-center"><div className="text-2xl font-bold text-yellow-500 dark:text-yellow-400">{taskStats.doing}</div><div className="text-xs text-muted-foreground">进行中</div></div>
                          <div className="text-center"><div className="text-2xl font-bold text-gray-400 dark:text-gray-500">{taskStats.wait_start}</div><div className="text-xs text-muted-foreground">待开始</div></div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {noteStats && (
                  <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><FileText className="h-4 w-4" />学习内容</CardTitle></CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="flex items-center gap-2"><Badge variant="secondary">{noteStats.total} 篇笔记</Badge></div>
                        {noteStats.recent_titles.length > 0 && (
                          <div className="space-y-1">
                            <div className="text-xs text-muted-foreground">最近记录：</div>
                            {noteStats.recent_titles.map((title, i) => (
                              <div key={i} className="text-sm truncate">• {title}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {reportType === "weekly" && weeklyReport?.daily_breakdown && (
                  <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><BarChart3 className="h-4 w-4" />每日分解</CardTitle></CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {weeklyReport.daily_breakdown.map((day) => (
                          <div key={day.date} className="flex items-center justify-between p-2 rounded-lg bg-muted/30">
                            <div className="flex items-center gap-2"><Calendar className="h-4 w-4 text-muted-foreground" /><span className="text-sm">{formatDate(day.date)}</span></div>
                            <div className="flex items-center gap-4 text-sm"><span>{day.total} 个任务</span><span className="text-green-500 dark:text-green-400">{day.completed} 完成</span></div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {reportType === "monthly" && monthlyReport?.weekly_breakdown && (
                  <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><TrendingUp className="h-4 w-4" />周度分解</CardTitle></CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {monthlyReport.weekly_breakdown.map((week) => (
                          <div key={week.week} className="flex items-center justify-between p-2 rounded-lg bg-muted/30">
                            <div className="flex items-center gap-2"><span className="text-sm font-medium">{week.week}</span><span className="text-xs text-muted-foreground">{formatDate(week.start_date)} - {formatDate(week.end_date)}</span></div>
                            <div className="flex items-center gap-4 text-sm"><span>{week.total} 个任务</span><span className="text-green-500 dark:text-green-400">{week.completed} 完成</span></div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {reportType === "daily" && dailyReport?.completed_tasks && dailyReport.completed_tasks.length > 0 && (
                  <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-base flex items-center gap-2"><CheckCircle className="h-4 w-4 text-green-500 dark:text-green-400" />今日完成 ({dailyReport.completed_tasks.length})</CardTitle></CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {dailyReport.completed_tasks.map((task) => (
                          <div key={task.id} className="flex items-center gap-2 p-2 rounded-lg bg-green-50 dark:bg-green-950/20"><CheckCircle className="h-4 w-4 text-green-500 dark:text-green-400" /><span className="text-sm">{task.title}</span></div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </>
        )}
        </>
        )}
      </main>
    </>
  );
}
