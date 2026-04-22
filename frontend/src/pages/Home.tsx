import { useMemo, useState, useCallback, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";
import { toast } from "sonner";
import {
  CheckCircle,
  Circle,
  Clock,
  Lightbulb,
  PlusCircle,
  FileText,
  Zap,
  ArrowRight,
  Sparkles,
  AlertTriangle,
  Inbox,
  BookOpen,
  Flame,
  Target,
  Eye,
  Scale,
  RotateCcw,
  HelpCircle,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import type { TaskStatus } from "@/types/task";
import { nextStatusMap } from "@/config/constants";
import {
  getGoals,
  type Goal,
} from "@/services/api";
import { useMorningDigest } from "@/hooks/useMorningDigest";
import { PageChatPanel } from "@/components/PageChatPanel";

export function Home() {
  const tasks = useTaskStore((state) => state.tasks);
  const updateTaskStatus = useTaskStore((state) => state.updateTaskStatus);
  const navigate = useNavigate();

  // 当前正在切换状态的任务 ID（防止双击）
  const [togglingTaskId, setTogglingTaskId] = useState<string | null>(null);

  // 当前正在转化的灵感 ID（防止双击）
  const [convertingId, setConvertingId] = useState<string | null>(null);

  const storeUpdateEntry = useTaskStore((state) => state.updateEntry);

  // 灵感转化处理
  const handleConvert = useCallback(async (e: React.MouseEvent, id: string, title: string, targetCategory: "task" | "note") => {
    e.preventDefault();
    e.stopPropagation();
    if (convertingId) return;
    setConvertingId(id);
    try {
      await storeUpdateEntry(id, { category: targetCategory });
      const label = targetCategory === "task" ? "任务" : "笔记";
      toast.success(`已转为${label}：${title}`);
    } catch {
      toast.error("转化失败，请重试");
    } finally {
      setConvertingId(null);
    }
  }, [convertingId, storeUpdateEntry]);

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

  // AI 晨报状态（共享 Hook）
  const { data: digest, loading: digestLoading, error: digestError } = useMorningDigest();
  const [digestCollapsed, setDigestCollapsed] = useState(() => {
    const dismissedDate = localStorage.getItem("morning_digest_dismissed");
    return dismissedDate === new Date().toISOString().split("T")[0];
  });

  // 活跃目标（最近 3 个）
  const [activeGoals, setActiveGoals] = useState<Goal[]>([]);
  const [goalsLoading, setGoalsLoading] = useState(true);

  useEffect(() => {
    getGoals("active")
      .then((res) => setActiveGoals((res.goals ?? []).slice(0, 3)))
      .catch(() => setActiveGoals([]))
      .finally(() => setGoalsLoading(false));
  }, []);

  const handleDismissDigest = () => {
    setDigestCollapsed(true);
    localStorage.setItem(
      "morning_digest_dismissed",
      new Date().toISOString().split("T")[0]
    );
  };

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
            {/* ====== AI 晨报卡片 ====== */}
            {!digestCollapsed && (
              <Card className="border-l-4 border-l-indigo-500 dark:border-l-indigo-400 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30">
                <CardContent className="pt-4 pb-4">
                  {digestLoading ? (
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <div className="h-8 w-8 rounded-full bg-primary/20 animate-pulse" />
                        <div className="h-4 bg-primary/10 rounded animate-pulse flex-1" />
                      </div>
                      <div className="h-4 bg-primary/10 rounded animate-pulse w-full" />
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        {Array.from({ length: 4 }).map((_, i) => (
                          <div key={i} className="h-10 bg-primary/10 rounded animate-pulse" />
                        ))}
                      </div>
                    </div>
                  ) : digestError ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Sparkles className="h-4 w-4 text-indigo-400" />
                      <span>晨报加载失败，请稍后刷新</span>
                    </div>
                  ) : digest && (
                    <div className="space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <Sparkles className="h-5 w-5 text-indigo-500" />
                          <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">
                            日知晨报
                          </span>
                        </div>
                        <button
                          onClick={handleDismissDigest}
                          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                        >
                          收起
                        </button>
                      </div>
                      <p className="text-sm text-foreground/80 leading-relaxed">
                        {digest.ai_suggestion}
                      </p>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        <DigestStat
                          icon={<Clock className="h-3.5 w-3.5" />}
                          label="待办"
                          count={digest.todos.length}
                          color="text-blue-500 dark:text-blue-400"
                        />
                        <DigestStat
                          icon={<AlertTriangle className="h-3.5 w-3.5" />}
                          label="逾期"
                          count={digest.overdue.length}
                          color="text-red-500 dark:text-red-400"
                        />
                        <DigestStat
                          icon={<Inbox className="h-3.5 w-3.5" />}
                          label="待跟进"
                          count={digest.stale_inbox.length}
                          color="text-yellow-500 dark:text-yellow-400"
                        />
                        <DigestStat
                          icon={<BookOpen className="h-3.5 w-3.5" />}
                          label="新概念"
                          count={digest.weekly_summary.new_concepts.length}
                          color="text-green-500 dark:text-green-400"
                        />
                      </div>

                      {/* 学习连续天数 */}
                      {(digest.learning_streak ?? 0) > 0 && (
                        <div className="flex items-center gap-2 pt-1">
                          <Flame className={`${
                            (digest.learning_streak ?? 0) >= 7
                              ? "h-5 w-5 text-orange-500"
                              : "h-4 w-4 text-orange-400"
                          }`} />
                          <span className={`text-sm font-medium ${
                            (digest.learning_streak ?? 0) >= 7
                              ? "text-orange-600 dark:text-orange-400"
                              : "text-muted-foreground"
                          }`}>
                            连续学习 {(digest.learning_streak ?? 0)} 天
                          </span>
                          {(digest.learning_streak ?? 0) >= 7 && (
                            <span className="text-xs text-orange-500">太棒了！</span>
                          )}
                        </div>
                      )}

                      {/* 今日聚焦 */}
                      {digest.daily_focus && (
                        <div
                          className="flex items-start gap-2 p-2 rounded-lg bg-background/60 cursor-pointer hover:bg-background/80 transition-colors"
                          onClick={() => {
                            if (digest.daily_focus?.target_entry_id) {
                              navigate(`/entry/${digest.daily_focus.target_entry_id}`);
                            }
                          }}
                        >
                          <Target className="h-4 w-4 text-indigo-500 mt-0.5 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{digest.daily_focus.title}</p>
                            <p className="text-xs text-muted-foreground line-clamp-2">{digest.daily_focus.description}</p>
                          </div>
                          {digest.daily_focus.target_entry_id && (
                            <ArrowRight className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-1" />
                          )}
                        </div>
                      )}

                      {/* 模式洞察 */}
                      {digest.pattern_insights && digest.pattern_insights.length > 0 && (
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-1.5">
                            <Eye className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="text-xs font-medium text-muted-foreground">洞察</span>
                          </div>
                          {digest.pattern_insights.map((insight, i) => (
                            <p key={i} className="text-xs text-muted-foreground pl-5">• {insight}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

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
                        <CheckCircle className="h-3 w-3 text-green-500 dark:text-green-400" />
                        完成 {todayStats.completed}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3 text-yellow-500 dark:text-yellow-400" />
                        进行中 {todayStats.doing}
                      </span>
                      <span className="flex items-center gap-1">
                        <Circle className="h-3 w-3 text-gray-400 dark:text-gray-500" />
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

            {/* ====== 我的目标 ====== */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Target className="h-4 w-4 text-primary" />
                  我的目标
                </CardTitle>
                <Link
                  to="/goals"
                  className="flex items-center text-xs text-muted-foreground hover:text-primary transition-colors"
                >
                  查看全部
                  <ArrowRight className="ml-0.5 h-3 w-3" />
                </Link>
              </CardHeader>
              <CardContent>
                {goalsLoading ? (
                  <div className="text-center py-4 text-sm text-muted-foreground">加载中...</div>
                ) : activeGoals.length > 0 ? (
                  <div className="space-y-2">
                    {activeGoals.map((goal) => (
                      <Link
                        key={goal.id}
                        to={`/goals/${goal.id}`}
                        className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-accent/50 transition-colors"
                      >
                        <Target className="h-4 w-4 text-primary shrink-0" />
                        <span className="text-sm truncate flex-1">{goal.title}</span>
                        <div className="w-16 shrink-0">
                          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all"
                              style={{ width: `${goal.progress_percentage}%` }}
                            />
                          </div>
                        </div>
                        <span className="text-xs text-muted-foreground shrink-0 w-8 text-right">
                          {Math.round(goal.progress_percentage)}%
                        </span>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <p className="py-4 text-center text-sm text-muted-foreground">
                    设定一个目标开始追踪
                  </p>
                )}
              </CardContent>
            </Card>

            {/* ====== 最近灵感 ====== */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Lightbulb className="h-4 w-4 text-yellow-500 dark:text-yellow-400" />
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
                      <div
                        key={item.id}
                        className="flex items-center gap-1 rounded-lg px-2 py-1.5 hover:bg-accent/50 transition-colors group"
                      >
                        {item._offlinePending ? (
                          <span className="flex items-center gap-2 flex-1 min-w-0 cursor-default">
                            <Lightbulb className="h-3.5 w-3.5 text-yellow-500 dark:text-yellow-400 shrink-0" />
                            <span className="text-sm truncate">{item.title}</span>
                            <span className="inline-flex items-center rounded-full bg-orange-100 px-1.5 py-0.5 text-[10px] text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 shrink-0">
                              待同步
                            </span>
                          </span>
                        ) : (
                          <>
                            <Link
                              to={`/entries/${item.id}`}
                              className="flex items-center gap-2 flex-1 min-w-0"
                            >
                              <Lightbulb className="h-3.5 w-3.5 text-yellow-500 dark:text-yellow-400 shrink-0" />
                              <span className="text-sm truncate">{item.title}</span>
                              {item.status !== "complete" && (
                                <span className="text-[10px] text-muted-foreground shrink-0">
                                  {new Date(item.created_at).toLocaleDateString("zh-CN", {
                                    month: "short",
                                    day: "numeric",
                                  })}
                                </span>
                              )}
                            </Link>
                            <div className="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={(e) => handleConvert(e, item.id, item.title, "task")}
                                disabled={convertingId === item.id}
                                className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50 disabled:opacity-50 transition-colors"
                              >
                                {convertingId === item.id ? "..." : "转任务"}
                              </button>
                              <button
                                onClick={(e) => handleConvert(e, item.id, item.title, "note")}
                                disabled={convertingId === item.id}
                                className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50 disabled:opacity-50 transition-colors"
                              >
                                {convertingId === item.id ? "..." : "转笔记"}
                              </button>
                            </div>
                          </>
                        )}
                      </div>
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
                <QuickActionButton
                  icon={<Scale className="h-5 w-5" />}
                  label="记决策"
                  onClick={() => navigate("/explore?type=decision")}
                />
                <QuickActionButton
                  icon={<RotateCcw className="h-5 w-5" />}
                  label="写复盘"
                  onClick={() => navigate("/explore?type=reflection")}
                />
                <QuickActionButton
                  icon={<HelpCircle className="h-5 w-5" />}
                  label="记疑问"
                  onClick={() => navigate("/explore?type=question")}
                />
              </div>
            </div>

            {/* ====== 晨报助手 AI ====== */}
            <PageChatPanel
              title="晨报助手"
              welcomeMessage="有什么想聊的？我可以帮你规划今天"
              suggestions={[
                { label: "今日复盘", message: "帮我复盘一下今天的任务完成情况" },
                { label: "查看进度", message: "本周的学习进度怎么样？" },
                { label: "推荐优先级", message: "帮我看看今天哪些任务最该优先做" },
              ]}
              pageContext={{ page: "home" }}
              pageData={{
                todo_count: todayTasks.length,
                completed_today: todayStats.completed,
                total_tasks: todayStats.total,
                inbox_count: unprocessedInbox.length,
                doing_count: todayStats.doing,
                wait_start_count: todayStats.waitStart,
                completion_rate: todayCompletionRate,
                overdue_count: digest?.overdue?.length ?? 0,
                stale_inbox_count: digest?.stale_inbox?.length ?? 0,
                learning_streak: digest?.learning_streak ?? 0,
                active_goals_count: activeGoals.length,
              }}
              defaultCollapsed
            />
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
          <CheckCircle className="h-5 w-5 text-green-500 dark:text-green-400" />
        ) : task.status === "doing" ? (
          <Clock className="h-5 w-5 text-yellow-500 dark:text-yellow-400" />
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

/* ====== 晨报统计小卡 ====== */
function DigestStat({
  icon,
  label,
  count,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg bg-background/50 p-2">
      <span className={color}>{icon}</span>
      <span className="text-lg font-bold">{count}</span>
      <span className="text-[10px] text-muted-foreground">{label}</span>
    </div>
  );
}
