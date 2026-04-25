import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Target, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { Goal } from "@/services/api";

interface GoalsCardProps {
  goals: Goal[];
  loading: boolean;
}

export function GoalsCard({ goals, loading }: GoalsCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Target className="h-4 w-4 text-primary" />
          我的目标
        </CardTitle>
        <Link
          to="/goals"
          className="flex items-center text-xs text-muted-foreground hover:text-primary transition-colors"
        >
          查看全部
          <ArrowRight className="ml-0.5 h-3 w-3" />
        </Link>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="text-center py-4 text-sm text-muted-foreground">加载中...</div>
        ) : goals.length > 0 ? (
          <div className="space-y-2">
            {goals.map((goal) => (
              <Link
                key={goal.id}
                to={`/goals/${goal.id}`}
                className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-accent/50 transition-colors"
              >
                <Target className="h-4 w-4 text-primary shrink-0" />
                <span className="text-sm truncate flex-1">{goal.title}</span>
                <div className="w-16 shrink-0">
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{ width: `${goal.progress_percentage}%` }}
                    />
                  </div>
                </div>
                <span className="text-xs text-muted-foreground shrink-0 w-8 text-right">
                  {Math.round(goal.progress_percentage)}%
                </span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="py-4 text-center text-sm text-muted-foreground">
            设定一个目标开始追踪
          </p>
        )}
      </CardContent>
    </Card>
  );
}
