import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  getGrowthCurve,
  type GrowthCurvePoint,
} from "@/services/api";

export function GrowthCurveCard() {
  const [growthCurveData, setGrowthCurveData] = useState<GrowthCurvePoint[]>([]);
  const [growthCurveLoading, setGrowthCurveLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const fetchGrowthCurve = async () => {
      setGrowthCurveLoading(true);
      try {
        const data = await getGrowthCurve(8);
        if (!cancelled) setGrowthCurveData(data.points ?? []);
      } catch (err) {
        if (!cancelled) console.error("获取成长曲线失败:", err);
      } finally {
        if (!cancelled) setGrowthCurveLoading(false);
      }
    };

    fetchGrowthCurve();

    return () => { cancelled = true; };
  }, []);

  return (
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
}

export { GrowthCurveCard as default };
