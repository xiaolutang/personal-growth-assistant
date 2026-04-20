import { useState, useEffect } from "react";
import { TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import {
  getReviewTrend,
  type TrendPeriod,
} from "@/services/api";

export type TrendPeriodType = "daily" | "weekly";

interface TrendChartProps {
  footer?: React.ReactNode;
}

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
};

export function TrendChart({ footer }: TrendChartProps = {}) {
  const [trendPeriod, setTrendPeriod] = useState<TrendPeriodType>("daily");
  const [trendData, setTrendData] = useState<TrendPeriod[]>([]);
  const [trendLoading, setTrendLoading] = useState(true);
  const [trendError, setTrendError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchTrend = async () => {
      setTrendLoading(true);
      setTrendError(null);
      try {
        const data = await getReviewTrend(trendPeriod, trendPeriod === "daily" ? 7 : 8);
        if (!cancelled) setTrendData(data.periods ?? []);
      } catch (err) {
        if (!cancelled) {
          console.error("获取趋势数据失败:", err);
          setTrendError("趋势数据加载失败，请稍后重试");
        }
      } finally {
        if (!cancelled) setTrendLoading(false);
      }
    };

    fetchTrend();

    return () => { cancelled = true; };
  }, [trendPeriod]);

  // 日/周切换栏
  const periodSwitcher = (
    <div className="flex gap-1 mb-3">
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
  );

  if (trendLoading) {
    return (
      <>
        {periodSwitcher}
        <div className="flex items-center justify-center h-48">
          <div className="text-muted-foreground text-sm">加载趋势数据...</div>
        </div>
      </>
    );
  }

  if (trendError) {
    return (
      <>
        {periodSwitcher}
        <div className="flex flex-col items-center justify-center h-48 text-center">
          <p className="text-sm text-destructive">{trendError}</p>
        </div>
      </>
    );
  }

  if (trendData.length === 0) {
    return (
      <>
        {periodSwitcher}
        <div className="flex flex-col items-center justify-center h-48 text-center">
          <TrendingUp className="h-8 w-8 text-muted-foreground/40 mb-2" />
          <p className="text-sm text-muted-foreground">暂无趋势数据</p>
          <p className="text-xs text-muted-foreground/70 mt-1">
            持续记录任务完成情况，趋势图将自动生成
          </p>
        </div>
      </>
    );
  }

  return (
    <>
      {periodSwitcher}
      <div className="w-full" style={{ height: 260 }}>
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
              yAxisId="left"
              domain={[0, 100]}
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => `${v}%`}
              width={42}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={32}
            />
            <Tooltip
              formatter={(value, name) => {
                if (name === "完成率") return [`${value}%`, name];
                return [value, name];
              }}
              labelStyle={{ fontSize: 12 }}
            />
            <Legend
              wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="completion_rate"
              stroke="#6366F1"
              strokeWidth={2}
              dot={{ r: 3, fill: "#6366F1" }}
              activeDot={{ r: 5 }}
              name="完成率"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="task_count"
              stroke="#f97316"
              strokeWidth={1.5}
              strokeDasharray="5 3"
              dot={{ r: 2, fill: "#f97316" }}
              name="任务数"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="notes_count"
              stroke="#3b82f6"
              strokeWidth={1.5}
              strokeDasharray="5 3"
              dot={{ r: 2, fill: "#3b82f6" }}
              name="笔记数"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="inbox_count"
              stroke="#a855f7"
              strokeWidth={1.5}
              strokeDasharray="5 3"
              dot={{ r: 2, fill: "#a855f7" }}
              name="灵感数"
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
      {footer}
    </>
  );
}
