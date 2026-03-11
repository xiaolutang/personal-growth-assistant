import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";

export function Inbox() {
  const { getTasksByCategory } = useTaskStore();
  const inboxItems = getTasksByCategory("inbox");

  return (
    <>
      <Header title="灵感收集" />
      <main className="flex-1 p-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              灵感箱 ({inboxItems.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList
              tasks={inboxItems}
              emptyMessage="还没有灵感，去首页快速录入吧"
            />
          </CardContent>
        </Card>
      </main>
    </>
  );
}
