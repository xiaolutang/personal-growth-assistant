import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { Task } from "@/types/task";
import type { TaskStatus } from "@/types/task";
import { TodayTaskItem } from "./TodayTaskItem";

interface TodayTasksCardProps {
  todayTasks: Task[];
  togglingTaskId: string | null;
  onToggle: (taskId: string, status: TaskStatus) => void;
}

export function TodayTasksCard({ todayTasks, togglingTaskId, onToggle }: TodayTasksCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base">
          今日任务 ({todayTasks.length})
        </CardTitle>
        {todayTasks.length > 0 && (
          <Link
            to="/tasks"
            className="flex items-center text-xs text-muted-foreground hover:text-primary transition-colors"
          >
            查看全部
            <ArrowRight className="ml-0.5 h-3 w-3" />
          </Link>
        )}
      </CardHeader>
      <CardContent>
        {todayTasks.length > 0 ? (
          <div className="space-y-1">
            {todayTasks.map((task) => (
              <TodayTaskItem
                key={task.id}
                task={task}
                isToggling={togglingTaskId === task.id}
                onToggle={onToggle}
              />
            ))}
          </div>
        ) : (
          <p className="py-6 text-center text-sm text-muted-foreground">
            今天暂无任务
          </p>
        )}
      </CardContent>
    </Card>
  );
}
