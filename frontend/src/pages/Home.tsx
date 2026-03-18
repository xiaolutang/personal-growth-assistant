import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";
import { useStreamParse } from "@/hooks/useStreamParse";
import {
  ArrowRight,
  Plus,
  Loader2,
  CheckCircle,
  Circle,
  Clock,
  TrendingUp,
  Lightbulb,
} from "lucide-react";
import { Link } from "react-router-dom";
import type { Task, Category, TaskStatus } from "@/types/task";
import { statusConfig, categoryConfig, categoryBgColors } from "@/config/constants";

export function Home() {
  const { tasks, getTodayTasks, getTasksByCategory, fetchEntries, createEntry } = useTaskStore();
  const [quickInput, setQuickInput] = useState("");

  const todayTasks = getTodayTasks();
  const inboxItems = getTasksByCategory("inbox");

  // 使用 useMemo 优化计算
  const recentEntries = useMemo(() => {
    return [...tasks]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5);
  }, [tasks]);

  // 今日统计 - 单次遍历计算
  const todayStats = useMemo(() => {
    const stats = { total: todayTasks.length, completed: 0, doing: 0, waitStart: 0 };
    for (const task of todayTasks) {
      if (task.status === "complete") stats.completed++;
      else if (task.status === "doing") stats.doing++;
      else if (task.status === "waitStart") stats.waitStart++;
    }
    return stats;
  }, [todayTasks]);

  // 整体统计 - 单次遍历计算
  const overallStats = useMemo(() => {
    const stats = { total: tasks.length, completed: 0, tasks: 0, projects: 0, notes: 0, inbox: 0 };
    for (const task of tasks) {
      if (task.status === "complete") stats.completed++;
      if (task.category === "task") stats.tasks++;
      else if (task.category === "project") stats.projects++;
      else if (task.category === "note") stats.notes++;
      else if (task.category === "inbox") stats.inbox++;
    }
    return stats;
  }, [tasks]);

  // 流式解析 Hook
  const { result, isLoading: isParsing, parse } = useStreamParse({
    onComplete: async (data) => {
      if (data.tasks.length > 0) {
        // 并行创建条目
        await Promise.all(
          data.tasks.map((task) =>
            createEntry({
              type: task.category,
              title: task.title || "",
              content: task.content || "",
              tags: task.tags || [],
              status: task.status,
              planned_date: task.planned_date,
            })
          )
        );
        setQuickInput("");
      }
    },
  });

  // 初始化加载数据
  useEffect(() => {
    fetchEntries({ limit: 100 });
  }, [fetchEntries]);

  // 快速记录提交
  const handleQuickSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickInput.trim() || isParsing) return;
    await parse(quickInput.trim());
  };

  // 计算今日完成率
  const todayCompletionRate = todayStats.total > 0
    ? Math.round((todayStats.completed / todayStats.total) * 100)
    : 0;

  return (
    <>
      <Header title="首页" />
      <main className="flex-1 space-y-6 p-6 pb-32 overflow-y-auto">
        {/* 快速记录 */}
        <Card className="border-dashed">
          <CardContent className="pt-4">
            <form onSubmit={handleQuickSubmit} className="flex gap-2">
              <div className="relative flex-1">
                <Lightbulb className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  value={quickInput}
                  onChange={(e) => setQuickInput(e.target.value)}
                  placeholder="快速记录：明天下午3点开会 / 学习 RAG 技术..."
                  className="pl-10"
                  disabled={isParsing}
                />
              </div>
              <Button type="submit" disabled={!quickInput.trim() || isParsing}>
                {isParsing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
              </Button>
            </form>
            {isParsing && result && result.tasks.length > 0 && (
              <div className="mt-2 text-sm text-muted-foreground">
                已识别 {result.tasks.length} 个条目，正在创建...
              </div>
            )}
          </CardContent>
        </Card>

        {/* 进度概览 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 今日进度 */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Clock className="h-4 w-4" />
                今日进度
              </CardTitle>
            </CardHeader>
            <CardContent>
              {todayStats.total > 0 ? (
                <div className="space-y-3">
                  {/* 完成率进度条 */}
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>完成率</span>
                      <span className="font-medium">{todayCompletionRate}%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500 transition-all duration-300"
                        style={{ width: `${todayCompletionRate}%` }}
                      />
                    </div>
                  </div>

                  {/* 状态分布 */}
                  <div className="flex gap-4 text-sm">
                    <div className="flex items-center gap-1">
                      <CheckCircle className="h-3 w-3 text-green-500" />
                      <span>完成 {todayStats.completed}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Circle className="h-3 w-3 text-yellow-500" />
                      <span>进行中 {todayStats.doing}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Circle className="h-3 w-3 text-gray-400" />
                      <span>待开始 {todayStats.waitStart}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  今天还没有任务，试试在上方输入「明天下午3点开会」
                </p>
              )}
            </CardContent>
          </Card>

          {/* 整体统计 */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                整体统计
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">任务</Badge>
                  <span className="text-sm">{overallStats.tasks}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">项目</Badge>
                  <span className="text-sm">{overallStats.projects}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">笔记</Badge>
                  <span className="text-sm">{overallStats.notes}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">灵感</Badge>
                  <span className="text-sm">{overallStats.inbox}</span>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t flex justify-between text-sm">
                <span className="text-muted-foreground">总计</span>
                <span className="font-medium">{overallStats.total} 条记录</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 今日任务 */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">
              今日任务 ({todayTasks.length})
            </CardTitle>
            <Link
              to="/tasks"
              className="flex items-center text-sm text-muted-foreground hover:text-primary"
            >
              查看全部
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </CardHeader>
          <CardContent>
            <TaskList
              tasks={todayTasks}
              emptyMessage="今天还没有任务，试试在上方输入「明天下午3点开会」"
            />
          </CardContent>
        </Card>

        {/* 最近记录 */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">
              最近记录
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recentEntries.length > 0 ? (
              <div className="space-y-2">
                {recentEntries.map((entry) => (
                  <RecentEntryItem key={entry.id} entry={entry} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">还没有记录</p>
            )}
          </CardContent>
        </Card>

        {/* 最近灵感 */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">
              最近灵感 ({inboxItems.length})
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
              tasks={inboxItems.slice(0, 3)}
              emptyMessage="还没有灵感，试试在上方输入「学习 LangChain 的 Agent 模式」"
            />
          </CardContent>
        </Card>
      </main>
    </>
  );
}

// 最近记录项组件 - 使用统一的配置
function RecentEntryItem({ entry }: { entry: Task }) {
  return (
    <Link
      to={`/entry/${entry.id}`}
      className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors"
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <span className={`text-xs px-2 py-0.5 rounded ${categoryBgColors[entry.category as Category]}`}>
          {categoryConfig[entry.category as Category]?.label || entry.category}
        </span>
        <span className="truncate text-sm">{entry.title}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-muted-foreground">
          {statusConfig[entry.status as TaskStatus]?.label || entry.status}
        </span>
        <span className="text-xs text-muted-foreground">
          {new Date(entry.created_at).toLocaleDateString()}
        </span>
      </div>
    </Link>
  );
}
