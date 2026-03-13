import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

export function Home() {
  const { getTodayTasks, getTasksByCategory } = useTaskStore();
  const todayTasks = getTodayTasks();
  const recentInbox = getTasksByCategory("inbox").slice(0, 3);

  return (
    <>
      <Header title="首页" />
      <main className="flex-1 space-y-6 p-6">
        {/* Today's Tasks */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">
              今日任务 ({todayTasks.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList
              tasks={todayTasks}
              emptyMessage="今天还没有任务，试试在底部输入「明天下午3点开会」"
            />
          </CardContent>
        </Card>

        {/* Recent Inbox */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">
              最近灵感 ({getTasksByCategory("inbox").length})
            </CardTitle>
            <Link
              to="/inbox"
              className="flex items-center text-sm text-muted-foreground hover:text-primary"
            >
              查看全部
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </CardHeader>
          <CardContent>
            <TaskList
              tasks={recentInbox}
              emptyMessage="还没有灵感，试试在底部输入「学习 LangChain 的 Agent 模式」"
            />
          </CardContent>
        </Card>
      </main>
    </>
  );
}
