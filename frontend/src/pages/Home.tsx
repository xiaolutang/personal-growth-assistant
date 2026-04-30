import { useState, useCallback } from "react";
import { Header } from "@/components/layout/Header";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";
import { CreateDialog } from "@/components/CreateDialog";
import {
  Lightbulb,
  PlusCircle,
  Zap,
} from "lucide-react";

// Hooks
import { useHomeData } from "./home/useHomeData";

// Sub-components
import { MorningDigestCard } from "./home/MorningDigestCard";
import { TodayProgressCard } from "./home/TodayProgressCard";
import { TodayTasksCard } from "./home/TodayTasksCard";
import { GoalsCard } from "./home/GoalsCard";
import { RecentInboxCard } from "./home/RecentInboxCard";
import { QuickCaptureBar } from "./home/QuickCaptureBar";

export function Home() {
  const {
    serviceUnavailable,
    isEmpty,
    navigate,
    fetchEntries,
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

  // QuickCaptureBar 聚焦触发器
  const [focusTrigger, setFocusTrigger] = useState(0);
  // CreateDialog 状态（空状态建任务用）
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  const handleFocusInput = useCallback(() => {
    setFocusTrigger((prev) => prev + 1);
  }, []);

  return (
    <>
      <Header title="今天" />
      <main className="flex-1 space-y-5 p-4 md:p-6 pb-32 overflow-y-auto">
        {serviceUnavailable ? (
          <ServiceUnavailable onRetry={() => fetchEntries()} />
        ) : isEmpty ? (
          /* ====== 空状态 ====== */
          <div className="space-y-5">
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
                  onClick={handleFocusInput}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                  <Lightbulb className="h-4 w-4" />
                  记灵感
                </button>
                <button
                  onClick={() => setCreateDialogOpen(true)}
                  className="inline-flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
                >
                  <PlusCircle className="h-4 w-4" />
                  建任务
                </button>
              </div>
            </div>
            <QuickCaptureBar focusTrigger={focusTrigger} />
            <CreateDialog
              open={createDialogOpen}
              onOpenChange={setCreateDialogOpen}
              defaultType="task"
            />
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
                onNavigateToEntry={(entryId) => navigate(`/entries/${entryId}`)}
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

            {/* ====== 快速捕捉 ====== */}
            <QuickCaptureBar />
          </>
        )}

      </main>
    </>
  );
}
