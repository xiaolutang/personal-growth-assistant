import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Brain, TrendingUp, TrendingDown, Minus, Lightbulb, BarChart3 } from "lucide-react";
import type { InsightsResponse } from "@/services/api";

type ReportType = "daily" | "weekly" | "monthly" | "trend";

interface InsightCardProps {
  reportType: ReportType;
  insightsData: InsightsResponse | null;
  insightsLoading: boolean;
}

const trendIcon = (trend: string) => {
  switch (trend) {
    case "improving": return <TrendingUp className="h-3 w-3 text-green-500" />;
    case "declining": return <TrendingDown className="h-3 w-3 text-red-500" />;
    default: return <Minus className="h-3 w-3 text-muted-foreground" />;
  }
};

const priorityBadge = (priority: string) => {
  const colors: Record<string, string> = {
    high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    low: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  };
  return colors[priority] || colors.medium;
};

export function InsightCard({ reportType, insightsData: data, insightsLoading: loading }: InsightCardProps) {
  // 日报不显示洞察卡片
  if (reportType === "daily" || reportType === "trend") return null;

  return (
    <Card className="border-l-4 border-l-purple-500 dark:border-l-purple-400">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Brain className="h-4 w-4 text-purple-500" />
          AI 洞察
          {data?.source === "rule_based" && (
            <span className="text-xs font-normal text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              基于数据分析
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-2">
                <div className="h-3 bg-muted rounded animate-pulse w-1/3" />
                <div className="h-4 bg-muted rounded animate-pulse w-full" />
              </div>
            ))}
          </div>
        ) : data ? (
          <div className="space-y-4">
            {/* 行为模式 */}
            {data.insights.behavior_patterns.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                  <BarChart3 className="h-3 w-3" /> 行为模式
                </h4>
                <div className="space-y-1.5">
                  {data.insights.behavior_patterns.map((bp, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      {trendIcon(bp.trend)}
                      <span>{bp.pattern}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 成长建议 */}
            {data.insights.growth_suggestions.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                  <Lightbulb className="h-3 w-3" /> 成长建议
                </h4>
                <div className="space-y-1.5">
                  {data.insights.growth_suggestions.map((gs, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      <span className={`text-xs px-1.5 py-0.5 rounded shrink-0 ${priorityBadge(gs.priority)}`}>
                        {gs.priority === "high" ? "高" : gs.priority === "medium" ? "中" : "低"}
                      </span>
                      <span>{gs.suggestion}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 能力变化 */}
            {data.insights.capability_changes.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                  <TrendingUp className="h-3 w-3" /> 能力变化
                </h4>
                <div className="space-y-1.5">
                  {data.insights.capability_changes.map((cc, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <span className="font-medium">{cc.capability}</span>
                      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${cc.change > 0 ? "bg-green-500" : "bg-red-500"}`}
                          style={{ width: `${Math.round(cc.current_level * 100)}%` }}
                        />
                      </div>
                      <span className={`text-xs ${cc.change > 0 ? "text-green-600" : "text-red-600"}`}>
                        {cc.change > 0 ? "+" : ""}{Math.round(cc.change * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 空数据 */}
            {data.insights.behavior_patterns.length === 0 &&
              data.insights.growth_suggestions.length === 0 &&
              data.insights.capability_changes.length === 0 && (
              <p className="text-sm text-muted-foreground/60 italic">
                数据不足，继续记录以获得个性化洞察
              </p>
            )}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export { InsightCard as default };
