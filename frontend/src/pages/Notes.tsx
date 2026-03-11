import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";

export function Notes() {
  const { getTasksByCategory } = useTaskStore();
  const notes = getTasksByCategory("note");

  return (
    <>
      <Header title="学习笔记" />
      <main className="flex-1 p-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">笔记列表 ({notes.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList
              tasks={notes}
              emptyMessage="还没有笔记，去首页快速录入吧"
            />
          </CardContent>
        </Card>
      </main>
    </>
  );
}
