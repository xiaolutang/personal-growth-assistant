import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";

export function Tasks() {
  const { getTasksByCategory } = useTaskStore();
  const tasks = getTasksByCategory("task");

  return (
    <>
      <Header title="任务列表" />
      <main className="flex-1 p-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">所有任务 ({tasks.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList
              tasks={tasks}
              emptyMessage="还没有任务，去首页快速录入吧"
            />
          </CardContent>
        </Card>
      </main>
    </>
  );
}
