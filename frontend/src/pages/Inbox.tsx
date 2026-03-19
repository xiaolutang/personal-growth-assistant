import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";

export function Inbox() {
  const tasks = useTaskStore((state) => state.tasks);
  const inboxItems = useMemo(
    () => tasks.filter((task) => task.category === "inbox"),
    [tasks]
  );

  return (
    <>
      <Header title="灵感收集" />
      <main className="flex-1 p-6 pb-32 overflow-y-auto">
        {/* 灵感列表 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              灵感箱 ({inboxItems.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList
              tasks={inboxItems}
              emptyMessage="还没有灵感，使用底部 AI 对话框快速记录"
            />
          </CardContent>
        </Card>
      </main>
    </>
  );
}
