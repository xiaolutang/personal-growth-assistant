import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";

export function Projects() {
  const { getTasksByCategory } = useTaskStore();
  const projects = getTasksByCategory("project");

  return (
    <>
      <Header title="项目管理" />
      <main className="flex-1 p-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              项目列表 ({projects.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList
              tasks={projects}
              emptyMessage="还没有项目，去首页快速录入吧"
            />
          </CardContent>
        </Card>
      </main>
    </>
  );
}
