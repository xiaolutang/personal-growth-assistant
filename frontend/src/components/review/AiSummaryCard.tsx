import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, ChevronDown, ChevronUp } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { getInsights, type InsightsResponse } from "@/services/api";

type ReportType = "daily" | "weekly" | "monthly" | "trend";

interface AiSummaryCardProps {
  reportType: ReportType;
  isLoading: boolean;
  aiSummary: string | null;
}

function buildInsightMarkdown(data: InsightsResponse): string {
  const lines: string[] = [];
  const { insights, period } = data;
  const periodLabel = period === "monthly" ? "本月" : "本周";

  if (insights.behavior_patterns.length > 0) {
    lines.push(`### ${periodLabel}行为模式`);
    insights.behavior_patterns.forEach((bp) => {
      const trendLabel = bp.trend === "improving" ? "上升" : bp.trend === "declining" ? "下降" : "稳定";
      lines.push(`- **${bp.pattern}**（趋势：${trendLabel}）`);
    });
  }

  if (insights.growth_suggestions.length > 0) {
    lines.push("");
    lines.push("### 成长建议");
    insights.growth_suggestions.forEach((gs) => {
      const prioLabel = gs.priority === "high" ? "高优先" : gs.priority === "medium" ? "中优先" : "低优先";
      lines.push(`- [${prioLabel}] ${gs.suggestion}`);
    });
  }

  if (insights.capability_changes.length > 0) {
    lines.push("");
    lines.push("### 能力变化");
    insights.capability_changes.forEach((cc) => {
      const changeSign = cc.change > 0 ? "+" : "";
      lines.push(`- **${cc.capability}**：${changeSign}${Math.round(cc.change * 100)}%（当前 ${Math.round(cc.current_level * 100)}%）`);
    });
  }

  return lines.join("\n");
}

export function AiSummaryCard({ reportType, isLoading, aiSummary }: AiSummaryCardProps) {
  const [aiSummaryExpanded, setAiSummaryExpanded] = useState(false);
  const [insightsData, setInsightsData] = useState<InsightsResponse | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);

  // 周报/月报时获取 insights 数据
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

  if (reportType === "trend") return null;

  const hasInsights = insightsData && (
    insightsData.insights.behavior_patterns.length > 0 ||
    insightsData.insights.growth_suggestions.length > 0 ||
    insightsData.insights.capability_changes.length > 0
  );

  const insightMarkdown = hasInsights ? buildInsightMarkdown(insightsData!) : null;

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
            {aiSummaryExpanded && insightMarkdown && (
              <div className="mt-4 pt-4 border-t space-y-1 text-sm leading-relaxed prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown>{insightMarkdown}</ReactMarkdown>
              </div>
            )}
            {(aiSummary.length > 80 || insightMarkdown) && (
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
        {aiSummaryExpanded && insightsLoading && (
          <div className="mt-3 space-y-2">
            <div className="h-3 bg-muted rounded animate-pulse w-2/3" />
            <div className="h-3 bg-muted rounded animate-pulse w-full" />
            <div className="h-3 bg-muted rounded animate-pulse w-4/5" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export { AiSummaryCard as default };
