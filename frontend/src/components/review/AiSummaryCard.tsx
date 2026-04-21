import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, ChevronDown, ChevronUp } from "lucide-react";

type ReportType = "daily" | "weekly" | "monthly" | "trend";

interface AiSummaryCardProps {
  reportType: ReportType;
  isLoading: boolean;
  aiSummary: string | null;
}

export function AiSummaryCard({ reportType, isLoading, aiSummary }: AiSummaryCardProps) {
  const [aiSummaryExpanded, setAiSummaryExpanded] = useState(false);

  if (reportType === "trend") return null;

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
}

export { AiSummaryCard as default };
