import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle, Clock, Circle } from "lucide-react";

interface TodayProgressCardProps {
  total: number;
  completed: number;
  doing: number;
  waitStart: number;
  completionRate: number;
}

export function TodayProgressCard({ total, completed, doing, waitStart, completionRate }: TodayProgressCardProps) {
  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        {total > 0 ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">今日进度</span>
              <span className="text-sm text-muted-foreground">
                {completed}/{total} 已完成
              </span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-500 ease-out"
                style={{ width: `${completionRate}%` }}
              />
            </div>
            <div className="flex gap-4 text-xs text-muted-foreground pt-0.5">
              <span className="flex items-center gap-1">
                <CheckCircle className="h-3 w-3 text-green-500 dark:text-green-400" />
                完成 {completed}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3 text-yellow-500 dark:text-yellow-400" />
                进行中 {doing}
              </span>
              <span className="flex items-center gap-1">
                <Circle className="h-3 w-3 text-gray-400 dark:text-gray-500" />
                待开始 {waitStart}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            今天还没有任务，试试在下方输入「明天下午3点开会」
          </p>
        )}
      </CardContent>
    </Card>
  );
}
