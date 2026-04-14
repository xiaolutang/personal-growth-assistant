import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Header } from "@/components/layout/Header";
import { Calendar, CheckCircle, FileText, TrendingUp, BarChart3 } from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { API_BASE } from "@/config/api";
import { authFetch } from "@/lib/authFetch";
import { getReviewTrend, type TrendPeriod } from "@/services/api";

// 响应类型
interface TaskStats {
  total: number;
  completed: number;
  doing: number;
  wait_start: number;
  completion_rate: number;
}

interface NoteStats {
  total: number;
  recent_titles: string[];
}

interface DailyReport {
  date: string;
  task_stats: TaskStats;
  note_stats: NoteStats;
  completed_tasks: Array<{ id: string; title: string; status: string }>;
}

interface DailyBreakdown {
  date: string;
  total: number;
  completed: number;
}

interface WeeklyReport {
  start_date: string;
  end_date: string;
  task_stats: TaskStats;
  note_stats: NoteStats;
  daily_breakdown: DailyBreakdown[];
}

interface WeeklyBreakdown {
  week: string;
  start_date: string;
  end_date: string;
  total: number;
  completed: number;
}

interface MonthlyReport {
  month: string;
  task_stats: TaskStats;
  note_stats: NoteStats;
  weekly_breakdown: WeeklyBreakdown[];
}

type ReportType = "daily" | "weekly" | "monthly";
type TrendPeriodType = "daily" | "weekly";

export function Review() {
  const [reportType, setReportType] = useState<ReportType>("daily");
  const [isLoading, setIsLoading] = useState(true);
  const [dailyReport, setDailyReport] = useState<DailyReport | null>(null);
  const [weeklyReport, setWeeklyReport] = useState<WeeklyReport | null>(null);
  const [monthlyReport, setMonthlyReport] = useState<MonthlyReport | null>(null);

  // 趋势卡片独立状态
  const [trendPeriod, setTrendPeriod] = useState<TrendPeriodType>("daily");
  const [trendData, setTrendData] = useState<TrendPeriod[]>([]);
  const [trendLoading, setTrendLoading] = useState(true);
  const [trendError, setTrendError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      setIsLoading(true);
      try {
        if (reportType === "daily") {
          const res = await authFetch(`${API_BASE}/review/daily`);
          const data = await res.json();
          setDailyReport(data);
        } else if (reportType === "weekly") {
          const res = await authFetch(`${API_BASE}/review/weekly`);
          const data = await res.json();
          setWeeklyReport(data);
        } else {
          const res = await authFetch(`${API_BASE}/review/monthly`);
          const data = await res.json();
          setMonthlyReport(data);
        }
      } catch (err) {
        console.error("获取报告失败:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchReport();
  }, [reportType]);

  // 趋势数据获取（独立于主报告）
  useEffect(() => {
    const fetchTrend = async () => {
      setTrendLoading(true);
      setTrendError(null);
      try {
        const data = await getReviewTrend(trendPeriod, trendPeriod === "daily" ? 7 : 8);
        setTrendData(data.periods ?? []);
      } catch (err) {
        console.error("获取趋势数据失败:", err);
        setTrendError("趋势数据加载失败，请稍后重试");
      } finally {
        setTrendLoading(false);
      }
    };

    fetchTrend();
  }, [trendPeriod]);

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

  const taskStats = getTaskStats();
  const noteStats = getNoteStats();

  return (
    <>
      <Header title="成长回顾" />
      <main className="flex-1 p-6 pb-32 overflow-y-auto">
        {/* 报告类型选择 */}
        <div className="flex gap-2 mb-6">
          {(["daily", "weekly", "monthly"] as ReportType[]).map((type) => (
            <Badge
              key={type}
              variant={reportType === type ? "default" : "outline"}
              className="cursor-pointer px-4 py-2"
              onClick={() => setReportType(type)}
            >
              {type === "daily" ? "日报" : type === "weekly" ? "周报" : "月报"}
            </Badge>
          ))}
        </div>

        {/* 趋势折线图卡片 */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                完成率趋势
              </CardTitle>
              <div className="flex gap-1">
                {(["daily", "weekly"] as TrendPeriodType[]).map((p) => (
                  <Badge
                    key={p}
                    variant={trendPeriod === p ? "default" : "outline"}
                    className="cursor-pointer px-3 py-1 text-xs"
                    onClick={() => setTrendPeriod(p)}
                  >
                    {p === "daily" ? "日" : "周"}
                  </Badge>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {trendLoading ? (
              <div className="flex items-center justify-center h-48">
                <div className="text-muted-foreground text-sm">加载趋势数据...</div>
              </div>
            ) : trendError ? (
              <div className="flex flex-col items-center justify-center h-48 text-center">
                <p className="text-sm text-destructive">{trendError}</p>
              </div>
            ) : trendData.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-center">
                <TrendingUp className="h-8 w-8 text-muted-foreground/40 mb-2" />
                <p className="text-sm text-muted-foreground">暂无趋势数据</p>
                <p className="text-xs text-muted-foreground/70 mt-1">
                  持续记录任务完成情况，趋势图将自动生成
                </p>
              </div>
            ) : (
              <>
                <div className="w-full" style={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={trendData.map((d) => ({
                        ...d,
                        date: formatDate(d.date),
                        completion_rate: Number(d.completion_rate.toFixed(1)),
                      }))}
                      margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 12 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        domain={[0, 100]}
                        tick={{ fontSize: 12 }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v: number) => `${v}%`}
                        width={42}
                      />
                      <Tooltip
                        formatter={(value) => [`${value}%`, "完成率"]}
                        labelStyle={{ fontSize: 12 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="completion_rate"
                        stroke="#6366F1"
                        strokeWidth={2}
                        dot={{ r: 3, fill: "#6366F1" }}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                {/* 平均完成率摘要 */}
                {trendData.length > 0 && (
                  <div className="mt-3 pt-3 border-t flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      {trendPeriod === "daily" ? "近 7 天" : "近 8 周"}平均完成率
                    </span>
                    <span className="text-sm font-semibold">
                      {(
                        trendData.reduce((sum, d) => sum + d.completion_rate, 0) /
                        trendData.length
                      ).toFixed(1)}
                      %
                    </span>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-muted-foreground">加载中...</div>
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
                    {/* 完成率进度条 */}
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>完成率</span>
                        <span className="font-medium">{taskStats.completion_rate}%</span>
                      </div>
                      <Progress value={taskStats.completion_rate} />
                    </div>

                    {/* 统计数据 */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold">{taskStats.total}</div>
                        <div className="text-xs text-muted-foreground">总任务</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-500">{taskStats.completed}</div>
                        <div className="text-xs text-muted-foreground">已完成</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-yellow-500">{taskStats.doing}</div>
                        <div className="text-xs text-muted-foreground">进行中</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-400">{taskStats.wait_start}</div>
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
                          <div key={i} className="text-sm truncate">
                            • {title}
                          </div>
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
                      <div
                        key={day.date}
                        className="flex items-center justify-between p-2 rounded-lg bg-muted/30"
                      >
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">{formatDate(day.date)}</span>
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                          <span>{day.total} 个任务</span>
                          <span className="text-green-500">{day.completed} 完成</span>
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
                      <div
                        key={week.week}
                        className="flex items-center justify-between p-2 rounded-lg bg-muted/30"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{week.week}</span>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(week.start_date)} - {formatDate(week.end_date)}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                          <span>{week.total} 个任务</span>
                          <span className="text-green-500">{week.completed} 完成</span>
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
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    今日完成 ({dailyReport.completed_tasks.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {dailyReport.completed_tasks.map((task) => (
                      <div
                        key={task.id}
                        className="flex items-center gap-2 p-2 rounded-lg bg-green-50 dark:bg-green-950/20"
                      >
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-sm">{task.title}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </main>
    </>
  );
}
