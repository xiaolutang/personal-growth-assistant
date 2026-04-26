import { useState, useEffect } from "react";
import {
  getDailyReport,
  getWeeklyReport,
  getMonthlyReport,
  getProgressSummary,
  type DailyReport,
  type WeeklyReport,
  type MonthlyReport,
  type TaskStats,
  type NoteStats,
  type ProgressSummaryResponse,
} from "@/services/api";
import { useServiceUnavailable } from "@/hooks/useServiceUnavailable";
import type { ReportType } from "@/types/review";

interface UseReportDataReturn {
  reportType: ReportType;
  setReportType: (type: ReportType) => void;
  isLoading: boolean;
  error: string | null;
  retryKey: number;
  setRetryKey: React.Dispatch<React.SetStateAction<number>>;
  dailyReport: DailyReport | null;
  weeklyReport: WeeklyReport | null;
  monthlyReport: MonthlyReport | null;
  taskStats: TaskStats | null;
  noteStats: NoteStats | null;
  aiSummary: string | null;
  goalSummary: ProgressSummaryResponse | null;
  serviceUnavailable: boolean;
  isEmpty: boolean;
}

export function useReportData(): UseReportDataReturn {
  const [reportType, setReportType] = useState<ReportType>("daily");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [dailyReport, setDailyReport] = useState<DailyReport | null>(null);
  const [weeklyReport, setWeeklyReport] = useState<WeeklyReport | null>(null);
  const [monthlyReport, setMonthlyReport] = useState<MonthlyReport | null>(null);
  const { serviceUnavailable, runWith503 } = useServiceUnavailable();

  // 目标进展概览
  const [goalSummary, setGoalSummary] = useState<ProgressSummaryResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchReport = async () => {
      setIsLoading(true);
      setError(null);
      // Clear stale report data before refetching to prevent mixed state
      if (!cancelled) {
        setDailyReport(null);
        setWeeklyReport(null);
        setMonthlyReport(null);
      }
      try {
        await runWith503(async () => {
          if (reportType === "daily") {
            const data = await getDailyReport();
            if (!cancelled) setDailyReport(data);
          } else if (reportType === "weekly") {
            const data = await getWeeklyReport();
            if (!cancelled) setWeeklyReport(data);
          } else if (reportType === "monthly") {
            const data = await getMonthlyReport();
            if (!cancelled) setMonthlyReport(data);
          }
        });
      } catch {
        if (!cancelled) setError("加载失败，请重试");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    if (reportType !== "trend") {
      fetchReport();
    } else {
      setIsLoading(false);
    }

    return () => { cancelled = true; };
  }, [reportType, retryKey, runWith503]);

  // 目标进展概览
  useEffect(() => {
    let cancelled = false;
    // Clear stale goal data before refetching
    setGoalSummary(null);
    getProgressSummary(reportType === "monthly" ? "monthly" : "weekly")
      .then((data) => { if (!cancelled) setGoalSummary(data); })
      .catch(() => { if (!cancelled) setGoalSummary(null); });
    return () => { cancelled = true; };
  }, [reportType]);

  // 派生值
  const taskStats: TaskStats | null = (() => {
    if (reportType === "daily") return dailyReport?.task_stats || null;
    if (reportType === "weekly") return weeklyReport?.task_stats || null;
    return monthlyReport?.task_stats || null;
  })();

  const noteStats: NoteStats | null = (() => {
    if (reportType === "daily") return dailyReport?.note_stats || null;
    if (reportType === "weekly") return weeklyReport?.note_stats || null;
    return monthlyReport?.note_stats || null;
  })();

  const aiSummary: string | null = (() => {
    if (reportType === "daily") return dailyReport?.ai_summary ?? null;
    if (reportType === "weekly") return weeklyReport?.ai_summary ?? null;
    if (reportType === "monthly") return monthlyReport?.ai_summary ?? null;
    return null;
  })();

  // Empty state: both taskStats and noteStats are zero / absent
  const isEmpty = !isLoading && !error && !!(
    (!taskStats || taskStats.total === 0) &&
    (!noteStats || noteStats.total === 0)
  );

  return {
    reportType,
    setReportType,
    isLoading,
    error,
    retryKey,
    setRetryKey,
    dailyReport,
    weeklyReport,
    monthlyReport,
    taskStats,
    noteStats,
    aiSummary,
    goalSummary,
    serviceUnavailable,
    isEmpty,
  };
}
