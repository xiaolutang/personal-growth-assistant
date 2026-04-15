import { useMemo, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";
import {
  CheckCircle,
  Circle,
  Clock,
  Lightbulb,
  PlusCircle,
  FileText,
  Zap,
  ArrowRight,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import type { TaskStatus } from "@/types/task";
import { nextStatusMap } from "@/config/constants";

export function Home() {
  const tasks = useTaskStore((state) => state.tasks);
  const updateTaskStatus = useTaskStore((state) => state.updateTaskStatus);
  const navigate = useNavigate();

  // 当前正在切换状态的任务 ID（防止双击）
  const [togglingTaskId, setTogglingTaskId] = useState<string | null>(null);

  // 今日任务
  const todayTasks = useMemo(() => {
    const today = new Date().toISOString().split("T")[0];
    return tasks.filter((task) => {
      if (task.planned_date) {
        return task.planned_date.startsWith(today);
      }
      if (task.created_at) {
        return task.created_at.startsWith(today);
      }
      return false;
    });
  }, [tasks]);

  // 未处理的灵感（inbox 中非 complete 状态）
  const unprocessedInbox = useMemo(
    () => tasks.filter((t) => t.category === "inbox" && t.status !== "complete"),
    [tasks]
  );

  // 最近灵感（取最新 3 条）
  const recentInbox = useMemo(
    () =>
      [...tasks]
        .filter((t) => t.category === "inbox")
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 3),
    [tasks]
  );

  // 今日统计
  const todayStats = useMemo(() => {
    const stats = { total: todayTasks.length, completed: 0, doing: 0, waitStart: 0 };
    for (const task of todayTasks) {
      if (task.status === "complete") stats.completed++;
      else if (task.status === "doing") stats.doing++;
      else if (task.status === "waitStart") stats.waitStart++;
    }
    return stats;
  }, [todayTasks]);

  const todayCompletionRate =
    todayStats.total > 0 ? Math.round((todayStats.completed / todayStats.total) * 100) : 0;

  // 是否完全无数据
  const isEmpty = tasks.length === 0;

  // 任务状态切换
  const handleToggleStatus = useCallback(
    async (taskId: string, currentStatus: TaskStatus) => {
      if (togglingTaskId) return; // 防止并发
      const nextStatus = nextStatusMap[currentStatus];
      setTogglingTaskId(taskId);
      try {
        await updateTaskStatus(taskId, nextStatus);
      } finally {
        setTogglingTaskId(null);
      }
    },
    [togglingTaskId, updateTaskStatus]
  );

  return (
    <>
      <Header title="今天" />
      <main className="flex-1 space-y-5 p-4 md:p-6 pb-32 overflow-y-auto">
        {isEmpty ? (
          /* ====== 空状态 ====== */
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Zap className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-lg font-semibold mb-2">开始你的一天</h2>
            <p className="text-sm text-muted-foreground max-w-xs mb-6">
              还没有任何记录。试试在下方输入框记录你的第一个任务或灵感吧！
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => navigate("/explore?type=inbox")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <Lightbulb className="h-4 w-4" />
                记灵感
              </button>
              <button
                onClick={() => navigate("/tasks")}
                className="inline-flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
              >
                <PlusCircle className="h-4 w-4" />
                建任务
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* ====== 今日进度 ====== */}
            <Card>
              <CardContent className="pt-4 pb-4">
                {todayStats.total > 0 ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">今日进度</span>
                      <span className="text-sm text-muted-foreground">
                        {todayStats.completed}/{todayStats.total} 已完成
                      </span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-500 ease-out"
                        style={{ width: `${todayCompletionRate}%` }}
                      />
                    </div>
                    <div className="flex gap-4 text-xs text-muted-foreground pt-0.5">
                      <span className="flex items-center gap-1">
                        <CheckCircle className="h-3 w-3 text-green-500" />
                        完成 {todayStats.completed}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3 text-yellow-500" />
                        进行中 {todayStats.doing}
                      </span>
                      <span className="flex items-center gap-1">
                        <Circle className="h-3 w-3 text-gray-400" />
                        待开始 {todayStats.waitStart}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    今天还没有任务，试试在下方输入「明天下午3点开会」
                  </p>
                )}
              </CardContent>
            </Card>

            {/* ====== 今日任务 ====== */}
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
                        onToggle={handleToggleStatus}
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

            {/* ====== 最近灵感 ====== */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Lightbulb className="h-4 w-4 text-yellow-500" />
                  最近灵感
                  {unprocessedInbox.length > 0 && (
                    <span className="inline-flex items-center justify-center h-5 min-w-[20px] rounded-full bg-primary px-1.5 text-[10px] font-medium text-primary-foreground">
                      {unprocessedInbox.length}
                    </span>
                  )}
                </CardTitle>
                {recentInbox.length > 0 && (
                  <Link
                    to="/explore?type=inbox"
                    className="flex items-center text-xs text-muted-foreground hover:text-primary transition-colors"
                  >
                    查看全部
                    <ArrowRight className="ml-0.5 h-3 w-3" />
                  </Link>
                )}
              </CardHeader>
              <CardContent>
                {recentInbox.length > 0 ? (
                  <div className="space-y-1">
                    {recentInbox.map((item) => (
                      <Link
                        key={item.id}
                        to={`/entries/${item.id}`}
                        className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-accent/50 transition-colors"
                      >
                        <Lightbulb className="h-3.5 w-3.5 text-yellow-500 shrink-0" />
                        <span className="text-sm truncate flex-1">{item.title}</span>
                        {item.status !== "complete" && (
                          <span className="text-[10px] text-muted-foreground shrink-0">
                            {new Date(item.created_at).toLocaleDateString("zh-CN", {
                              month: "short",
                              day: "numeric",
                            })}
                          </span>
                        )}
                      </Link>
                    ))}
                  </div>
                ) : (
                  <p className="py-4 text-center text-sm text-muted-foreground">
                    暂无灵感记录
                  </p>
                )}
              </CardContent>
            </Card>

            {/* ====== 快捷操作 ====== */}
            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">快捷操作</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <QuickActionButton
                  icon={<Lightbulb className="h-5 w-5" />}
                  label="记灵感"
                  onClick={() => navigate("/explore?type=inbox")}
                />
                <QuickActionButton
                  icon={<PlusCircle className="h-5 w-5" />}
                  label="建任务"
                  onClick={() => navigate("/tasks")}
                />
                <QuickActionButton
                  icon={<FileText className="h-5 w-5" />}
                  label="写笔记"
                  onClick={() => navigate("/explore?type=note")}
                />
              </div>
            </div>
          </>
        )}
      </main>
    </>
  );
}

/* ====== 今日任务项 ====== */
interface TodayTaskItemProps {
  task: {
    id: string;
    title: string;
    status: TaskStatus;
  };
  isToggling: boolean;
  onToggle: (taskId: string, status: TaskStatus) => void;
}

function TodayTaskItem({ task, isToggling, onToggle }: TodayTaskItemProps) {
  const isComplete = task.status === "complete";

  return (
    <div className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-accent/30 transition-colors">
      <button
        onClick={() => onToggle(task.id, task.status)}
        disabled={isToggling}
        className={`shrink-0 transition-colors ${
          isToggling
            ? "opacity-50 cursor-not-allowed"
            : "cursor-pointer hover:scale-110"
        }`}
        aria-label={isComplete ? "标为未完成" : "标为完成"}
      >
        {isComplete ? (
          <CheckCircle className="h-5 w-5 text-green-500" />
        ) : task.status === "doing" ? (
          <Clock className="h-5 w-5 text-yellow-500" />
        ) : (
          <Circle className="h-5 w-5 text-muted-foreground" />
        )}
      </button>
      <span
        className={`text-sm flex-1 truncate ${
          isComplete ? "line-through text-muted-foreground" : ""
        }`}
      >
        {task.title}
      </span>
      {isToggling && (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      )}
    </div>
  );
}

/* ====== 快捷操作按钮 ====== */
interface QuickActionButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}

function QuickActionButton({ icon, label, onClick }: QuickActionButtonProps) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center justify-center gap-1.5 rounded-xl border bg-card p-4 text-sm font-medium hover:bg-accent hover:border-primary/30 transition-colors active:scale-95"
    >
      <span className="text-primary">{icon}</span>
      <span>{label}</span>
    </button>
  );
}
