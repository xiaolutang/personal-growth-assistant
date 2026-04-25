import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Target } from "lucide-react";
import type { ProgressSummaryResponse } from "@/services/api";

interface GoalProgressCardProps {
  goalSummary: ProgressSummaryResponse;
}

export function GoalProgressCard({ goalSummary }: GoalProgressCardProps) {
  return (
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
  );
}
