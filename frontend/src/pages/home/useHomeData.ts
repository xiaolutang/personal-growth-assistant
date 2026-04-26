import { useMemo, useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTaskStore } from "@/stores/taskStore";
import { useUserStore } from "@/stores/userStore";
import { toast } from "sonner";
import { trackEvent } from "@/lib/analytics";
import type { TaskStatus } from "@/types/task";
import { nextStatusMap } from "@/config/constants";
import {
  getGoals,
  type Goal,
} from "@/services/api";
import { useMorningDigest } from "@/hooks/useMorningDigest";

export function useHomeData() {
  const tasks = useTaskStore((state) => state.tasks);
  const updateTaskStatus = useTaskStore((state) => state.updateTaskStatus);
  const fetchEntries = useTaskStore((state) => state.fetchEntries);
  const serviceUnavailable = useTaskStore((state) => state.serviceUnavailable);
  const navigate = useNavigate();
  const user = useUserStore((state) => state.user);
  const updateMe = useUserStore((state) => state.updateMe);

  // onboarding 状态
  const isNewUser = user ? !user.onboarding_completed : false;
  const [onboardingCompleted, setOnboardingCompleted] = useState(!isNewUser);
  const onboardingUpdateCalled = useRef(false);

  useEffect(() => {
    if (!isNewUser) {
      setOnboardingCompleted(true);
    }
  }, [isNewUser]);

  const handleOnboardingFirstResponse = useCallback(async () => {
    if (onboardingUpdateCalled.current) return;
    onboardingUpdateCalled.current = true;
    try {
      await updateMe({ onboarding_completed: true });
      setOnboardingCompleted(true);
      trackEvent("onboarding_completed");
    } catch (err) {
      console.error("Failed to mark onboarding completed:", err);
      onboardingUpdateCalled.current = false;
    }
  }, [updateMe]);

  // 状态切换
  const [togglingTaskId, setTogglingTaskId] = useState<string | null>(null);

  // 灵感转化
  const [convertingId, setConvertingId] = useState<string | null>(null);
  const storeUpdateEntry = useTaskStore((state) => state.updateEntry);

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

  // 单次遍历产出今日任务、灵感、统计
  const { todayTasks, unprocessedInbox, recentInbox, todayStats } = useMemo(() => {
    const today = new Date().toISOString().split("T")[0];
    const _todayTasks: typeof tasks = [];
    const _unprocessedInbox: typeof tasks = [];
    const allInbox: typeof tasks = [];
    const stats = { total: 0, completed: 0, doing: 0, waitStart: 0 };

    for (const task of tasks) {
      const isToday = task.planned_date?.startsWith(today) || task.created_at?.startsWith(today);
      if (isToday) {
        _todayTasks.push(task);
        stats.total++;
        if (task.status === "complete") stats.completed++;
        else if (task.status === "doing") stats.doing++;
        else if (task.status === "waitStart") stats.waitStart++;
      }
      if (task.category === "inbox") {
        allInbox.push(task);
        if (task.status !== "complete") _unprocessedInbox.push(task);
      }
    }

    const _recentInbox = allInbox
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 3);

    return {
      todayTasks: _todayTasks,
      unprocessedInbox: _unprocessedInbox,
      recentInbox: _recentInbox,
      todayStats: stats,
    };
  }, [tasks]);

  const todayCompletionRate =
    todayStats.total > 0 ? Math.round((todayStats.completed / todayStats.total) * 100) : 0;

  const isEmpty = tasks.length === 0;

  // AI 晨报状态
  const { data: digest, loading: digestLoading, error: digestError } = useMorningDigest();
  const [digestCollapsed, setDigestCollapsed] = useState(() => {
    const dismissedDate = localStorage.getItem("morning_digest_dismissed");
    return dismissedDate === new Date().toISOString().split("T")[0];
  });

  // 活跃目标
  const [activeGoals, setActiveGoals] = useState<Goal[]>([]);
  const [goalsLoading, setGoalsLoading] = useState(true);

  useEffect(() => {
    getGoals("active")
      .then((res) => setActiveGoals((res.goals ?? []).slice(0, 3)))
      .catch(() => setActiveGoals([]))
      .finally(() => setGoalsLoading(false));
  }, []);

  const handleDismissDigest = useCallback(() => {
    setDigestCollapsed(true);
    localStorage.setItem(
      "morning_digest_dismissed",
      new Date().toISOString().split("T")[0]
    );
  }, []);

  // 任务状态切换
  const handleToggleStatus = useCallback(
    async (taskId: string, currentStatus: TaskStatus) => {
      if (togglingTaskId) return;
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

  return {
    // 状态
    tasks,
    serviceUnavailable,
    isEmpty,
    navigate,
    fetchEntries,
    // onboarding
    onboardingCompleted,
    handleOnboardingFirstResponse,
    // 今日数据
    todayTasks,
    unprocessedInbox,
    recentInbox,
    todayStats,
    todayCompletionRate,
    // 任务切换
    togglingTaskId,
    handleToggleStatus,
    // 灵感转化
    convertingId,
    handleConvert,
    // 晨报
    digest,
    digestLoading,
    digestError,
    digestCollapsed,
    handleDismissDigest,
    // 目标
    activeGoals,
    goalsLoading,
  };
}
