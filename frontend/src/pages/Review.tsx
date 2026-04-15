import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Header } from "@/components/layout/Header";
import {
  Calendar,
  CheckCircle,
  FileText,
  TrendingUp,
  BarChart3,
  Sparkles,
  Brain,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { API_BASE } from "@/config/api";
import { authFetch } from "@/lib/authFetch";
import {
  getReviewTrend,
  getKnowledgeHeatmap,
  getGrowthCurve,
  type TrendPeriod,
  type HeatmapItem,
  type GrowthCurvePoint,
} from "@/services/api";

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
  ai_summary?: string | null;
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
  ai_summary?: string | null;
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

type ReportType = "daily" | "weekly" | "monthly" | "trend";
type TrendPeriodType = "daily" | "weekly";

// 掌握度颜色映射
const MASTERY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  advanced: { bg: "bg-green-100 dark:bg-green-900/30", text: "text-green-700 dark:text-green-300", label: "精通" },
  intermediate: { bg: "bg-blue-100 dark:bg-blue-900/30", text: "text-blue-700 dark:text-blue-300", label: "中级" },
  beginner: { bg: "bg-orange-100 dark:bg-orange-900/30", text: "text-orange-700 dark:text-orange-300", label: "入门" },
  new: { bg: "bg-gray-100 dark:bg-gray-800/30", text: "text-gray-600 dark:text-gray-400", label: "新知" },
};

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

  // AI 总结展开状态
  const [aiSummaryExpanded, setAiSummaryExpanded] = useState(false);

  // 知识热力图状态
  const [heatmapItems, setHeatmapItems] = useState<HeatmapItem[]>([]);
  const [heatmapLoading, setHeatmapLoading] = useState(true);

  // 成长曲线状态
  const [growthCurveData, setGrowthCurveData] = useState<GrowthCurvePoint[]>([]);
  const [growthCurveLoading, setGrowthCurveLoading] = useState(true);

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
        } else if (reportType === "monthly") {
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

    if (reportType !== "trend") {
      fetchReport();
    } else {
      setIsLoading(false);
    }
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

  // 知识热力图数据获取
  useEffect(() => {
    const fetchHeatmap = async () => {
      setHeatmapLoading(true);
      try {
        const data = await getKnowledgeHeatmap();
        setHeatmapItems(data.items ?? []);
      } catch (err) {
        console.error("获取知识热力图失败:", err);
      } finally {
        setHeatmapLoading(false);
      }
    };

    fetchHeatmap();
  }, []);

  // 成长曲线数据获取
  useEffect(() => {
    const fetchGrowthCurve = async () => {
      setGrowthCurveLoading(true);
      try {
        const data = await getGrowthCurve(8);
        setGrowthCurveData(data.points ?? []);
      } catch (err) {
        console.error("获取成长曲线失败:", err);
      } finally {
        setGrowthCurveLoading(false);
      }
    };

    fetchGrowthCurve();
  }, []);

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

  // 获取 AI 总结文本
  const getAiSummary = (): string | null => {
    if (reportType === "daily") return dailyReport?.ai_summary ?? null;
    if (reportType === "weekly") return weeklyReport?.ai_summary ?? null;
    return null;
  };

  const taskStats = getTaskStats();
  const noteStats = getNoteStats();
  const aiSummary = getAiSummary();

  // AI 总结卡片渲染
  const renderAiSummaryCard = () => {
    if (reportType === "monthly" || reportType === "trend") return null;

    return (
      <Card className="border-l-4 border-l-indigo-500 dark:border-l-indigo-400">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-500" />
            AI 总结
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              <div className="h-4 bg-muted rounded animate-pulse w-full" />
              <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
            </div>
          ) : aiSummary ? (
            <div>
              <div className={`text-sm leading-relaxed ${!aiSummaryExpanded ? "line-clamp-2" : ""}`}>
                {aiSummary}
              </div>
              {aiSummary.length > 80 && (
                <button
                  onClick={() => setAiSummaryExpanded(!aiSummaryExpanded)}
                  className="mt-2 text-xs text-indigo-500 dark:text-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-300 flex items-center gap-1"
                >
                  {aiSummaryExpanded ? (
                    <>
                      收起 <ChevronUp className="h-3 w-3" />
                    </>
                  ) : (
                    <>
                      展开全文 <ChevronDown className="h-3 w-3" />
                    </>
                  )}
                </button>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground/60 italic">AI 总结生成中...</p>
          )}
        </CardContent>
      </Card>
    );
  };

  // 知识热力图卡片渲染
  const renderHeatmapCard = () => (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Brain className="h-4 w-4" />
          知识热力图
        </CardTitle>
      </CardHeader>
      <CardContent>
        {heatmapLoading ? (
          <div className="flex flex-wrap gap-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-7 w-20 bg-muted rounded-full animate-pulse" />
            ))}
          </div>
        ) : heatmapItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Brain className="h-8 w-8 text-muted-foreground/40 mb-2" />
            <p className="text-sm text-muted-foreground">记录更多内容，知识图谱将自动丰富</p>
          </div>
        ) : (
          <>
            {/* 掌握度图例 */}
            <div className="flex flex-wrap gap-3 mb-3 text-xs text-muted-foreground">
              {Object.entries(MASTERY_STYLES).map(([key, style]) => (
                <span key={key} className="flex items-center gap-1">
                  <span className={`inline-block w-2.5 h-2.5 rounded-full ${style.bg}`} />
                  {style.label}
                </span>
              ))}
            </div>
            {/* 概念标签 */}
            <div className="flex flex-wrap gap-2">
              {heatmapItems.map((item) => {
                const style = MASTERY_STYLES[item.mastery] || MASTERY_STYLES.new;
                return (
                  <span
                    key={item.concept}
                    className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${style.bg} ${style.text}`}
                  >
                    {item.concept}
                    <span className="opacity-60">({item.entry_count})</span>
                  </span>
                );
              })}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );

  // 成长曲线卡片渲染
  const renderGrowthCurveCard = () => (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp className="h-4 w-4" />
          知识成长曲线
        </CardTitle>
      </CardHeader>
      <CardContent>
        {growthCurveLoading ? (
          <div className="flex items-center justify-center h-48">
            <div className="text-muted-foreground text-sm">加载成长曲线...</div>
          </div>
        ) : growthCurveData.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center">
            <TrendingUp className="h-8 w-8 text-muted-foreground/40 mb-2" />
            <p className="text-sm text-muted-foreground">暂无成长数据</p>
          </div>
        ) : (
          <div className="w-full" style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={growthCurveData}
                margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis
                  dataKey="week"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={32}
                />
                <Tooltip labelStyle={{ fontSize: 12 }} />
                <Area
                  type="monotone"
                  dataKey="beginner_count"
                  stackId="1"
                  stroke="#f97316"
                  fill="#f97316"
                  fillOpacity={0.3}
                  name="入门"
                />
                <Area
                  type="monotone"
                  dataKey="intermediate_count"
                  stackId="1"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.3}
                  name="中级"
                />
                <Area
                  type="monotone"
                  dataKey="advanced_count"
                  stackId="1"
                  stroke="#22c55e"
                  fill="#22c55e"
                  fillOpacity={0.3}
                  name="精通"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );

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
              onClick={() => {
                setReportType(type);
                setAiSummaryExpanded(false);
              }}
            >
              {type === "daily" ? "日报" : type === "weekly" ? "周报" : type === "monthly" ? "月报" : "趋势"}
            </Badge>
          ))}
        </div>

        {/* 趋势标签页内容 */}
        {reportType === "trend" ? (
          <div className="space-y-6">
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

            {/* 成长曲线 */}
            {renderGrowthCurveCard()}

            {/* 知识热力图 */}
            {renderHeatmapCard()}
          </div>
        ) : (
          <>
            {/* 趋势折线图卡片（日报/周报/月报下也保留） */}
            <Card className="mb-6">
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

            {/* AI 总结卡片 */}
            {renderAiSummaryCard()}

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
                          <div
                            key={task.id}
                            className="flex items-center gap-2 p-2 rounded-lg bg-green-50 dark:bg-green-950/20"
                          >
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
