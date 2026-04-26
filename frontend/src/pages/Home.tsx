import { Header } from "@/components/layout/Header";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import {
  Lightbulb,
  PlusCircle,
  FileText,
  Zap,
  Scale,
  RotateCcw,
  HelpCircle,
} from "lucide-react";
import { PageChatPanel } from "@/components/PageChatPanel";

// Hooks
import { useHomeData } from "./home/useHomeData";

// Sub-components
import { MorningDigestCard } from "./home/MorningDigestCard";
import { TodayProgressCard } from "./home/TodayProgressCard";
import { TodayTasksCard } from "./home/TodayTasksCard";
import { GoalsCard } from "./home/GoalsCard";
import { RecentInboxCard } from "./home/RecentInboxCard";
import { QuickActionButton } from "./home/QuickActionButton";

export function Home() {
  const {
    serviceUnavailable,
    isEmpty,
    navigate,
    fetchEntries,
    onboardingCompleted,
    handleOnboardingFirstResponse,
    todayTasks,
    unprocessedInbox,
    recentInbox,
    todayStats,
    todayCompletionRate,
    togglingTaskId,
    handleToggleStatus,
    convertingId,
    handleConvert,
    digest,
    digestLoading,
    digestError,
    digestCollapsed,
    handleDismissDigest,
    activeGoals,
    goalsLoading,
  } = useHomeData();

  return (
    <>
      <Header title="今天" />
      <main className="flex-1 space-y-5 p-4 md:p-6 pb-32 overflow-y-auto">
        {serviceUnavailable ? (
          <ServiceUnavailable onRetry={() => fetchEntries()} />
        ) : isEmpty ? (
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
              <MorningDigestCard
                digest={digest}
                digestLoading={digestLoading}
                digestError={digestError}
                onDismiss={handleDismissDigest}
                onNavigateToEntry={(entryId) => navigate(`/entry/${entryId}`)}
              />
            )}

            {/* ====== 今日进度 ====== */}
            <TodayProgressCard
              total={todayStats.total}
              completed={todayStats.completed}
              doing={todayStats.doing}
              waitStart={todayStats.waitStart}
              completionRate={todayCompletionRate}
            />

            {/* ====== 今日任务 ====== */}
            <TodayTasksCard
              todayTasks={todayTasks}
              togglingTaskId={togglingTaskId}
              onToggle={handleToggleStatus}
            />

            {/* ====== 我的目标 ====== */}
            <GoalsCard goals={activeGoals} loading={goalsLoading} />

            {/* ====== 最近灵感 ====== */}
            <RecentInboxCard
              unprocessedCount={unprocessedInbox.length}
              recentInbox={recentInbox}
              convertingId={convertingId}
              onConvert={handleConvert}
            />

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
          </>
        )}

        {/* ====== AI 对话面板 ====== */}
        <PageChatPanel
              key={onboardingCompleted ? "normal" : "onboarding"}
              title="晨报助手"
              welcomeMessage={onboardingCompleted ? "有什么想聊的？我可以帮你规划今天" : undefined}
              greetingMessage={onboardingCompleted ? undefined : "你好！我是日知，你的个人成长助手。你可以试试和我聊天来记录灵感、管理任务或写笔记。"}
              suggestions={
                onboardingCompleted
                  ? [
                      { label: "今日复盘", message: "帮我复盘一下今天的任务完成情况" },
                      { label: "查看进度", message: "本周的学习进度怎么样？" },
                      { label: "推荐优先级", message: "帮我看看今天哪些任务最该优先做" },
                    ]
                  : [
                      { label: "记灵感", message: "想到一个有趣的想法" },
                      { label: "做任务", message: "今天要完成阅读" },
                      { label: "记笔记", message: "读了《深度工作》的体会" },
                    ]
              }
              pageContext={onboardingCompleted ? { page: "home" } : { page: "home", is_new_user: true }}
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
              defaultCollapsed={onboardingCompleted}
              onFirstResponse={onboardingCompleted ? undefined : handleOnboardingFirstResponse}
            />
      </main>
    </>
  );
}
