import { BarChart3 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { TaskList } from "@/components/TaskList";
import { statusConfig } from "@/config/constants";
import type { Task } from "@/types/task";
import type { ProjectProgressResponse } from "@/services/api";

export function ProjectSection({
  category,
  projectProgress,
  childTasks,
}: {
  category: string;
  projectProgress: ProjectProgressResponse | null;
  childTasks: Task[];
}) {
  if (category !== "project") return null;

  return (
    <>
      {projectProgress && (
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              项目进度
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>完成进度</span>
                  <span>{projectProgress.progress_percentage}%</span>
                </div>
                <Progress value={projectProgress.progress_percentage} />
              </div>
              <div className="flex gap-4 text-sm text-muted-foreground">
                <span>总任务: {projectProgress.total_tasks}</span>
                <span>已完成: {projectProgress.completed_tasks}</span>
              </div>
              {Object.keys(projectProgress.status_distribution).length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {Object.entries(projectProgress.status_distribution).map(([status, count]) => (
                    <Badge key={status} variant="outline" className="text-xs">
                      {statusConfig[status as keyof typeof statusConfig]?.label || status}: {count}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {childTasks.length > 0 && (
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">子任务 ({childTasks.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList tasks={childTasks} emptyMessage="暂无子任务" />
          </CardContent>
        </Card>
      )}
    </>
  );
}
