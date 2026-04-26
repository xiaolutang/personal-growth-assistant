/**
 * 截止日期判断共享 helper
 * 用于 TaskCard、EntryHeader 等组件统一判断过期/今天/未来
 */

export interface DueDateInfo {
  status: "overdue" | "today" | "future" | "none";
  label: string;
  /** 原始日期字符串 (YYYY-MM-DD) */
  dateStr: string | null;
}

/**
 * 根据计划日期返回截止日期信息
 * @param plannedDate ISO 日期字符串，如 "2024-06-15" 或 "2024-06-15T00:00:00"
 * @returns DueDateInfo
 */
export function getDueDateInfo(plannedDate: string | null | undefined): DueDateInfo {
  if (!plannedDate) {
    return { status: "none", label: "", dateStr: null };
  }

  const plannedDateStr = plannedDate.split("T")[0];
  const todayStr = new Date().toISOString().split("T")[0];

  if (plannedDateStr < todayStr) {
    const date = new Date(plannedDateStr + "T00:00:00");
    return {
      status: "overdue",
      label: `已过期 ${date.toLocaleDateString("zh-CN")}`,
      dateStr: plannedDateStr,
    };
  }

  if (plannedDateStr === todayStr) {
    return {
      status: "today",
      label: "今天到期",
      dateStr: plannedDateStr,
    };
  }

  const date = new Date(plannedDateStr + "T00:00:00");
  return {
    status: "future",
    label: date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" }),
    dateStr: plannedDateStr,
  };
}
