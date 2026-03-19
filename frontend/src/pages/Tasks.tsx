import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";
import { useMemo } from "react";

export function Tasks() {
  // 直接获取 tasks，然后使用 useMemo 过滤，确保响应式更新
  const tasks = useTaskStore((state) => state.tasks);
  const taskList = useMemo(
    () => tasks.filter((task) => task.category === "task"),
    [tasks]
  );

  return (
    <>
      <Header title="任务列表" />
      <main className="flex-1 p-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">所有任务 ({taskList.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList
              tasks={taskList}
              emptyMessage="还没有任务，去首页快速录入吧"
            />
          </CardContent>
        </Card>
      </main>
    </>
  );
}
