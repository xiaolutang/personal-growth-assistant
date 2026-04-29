import { useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useTaskStore } from "@/stores/taskStore";
import type { Task, TaskStatus, Priority } from "@/types/task";
import { toast } from "sonner";
import {
  TASK_QUERY_PARAMS, STATUS_OPTIONS, SORT_OPTIONS, type SortOption,
  TASK_SUB_TABS, type SubTabKey, ACTIONABLE_CATEGORIES,
  VALID_VIEW_KEYS, type ViewKey,
} from "./constants";

// === URL 参数合法性校验 ===
const VALID_PRIORITIES: Priority[] = ["high", "medium", "low"];
const VALID_SORT_OPTIONS: SortOption[] = SORT_OPTIONS.map(o => o.value);
const VALID_SUB_TAB_KEYS: SubTabKey[] = TASK_SUB_TABS.map(t => t.key);

function validateUrlParam<T>(value: string | null, validValues: readonly T[]): T | null {
  if (!value) return null;
  return validValues.includes(value as T) ? (value as T) : null;
}

/** 获取本地日期字符串 YYYY-MM-DD */
function toLocalDateString(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

// 获取日期范围
function getDateRange(option: string) {
  const now = new Date();
  const today = toLocalDateString(now);

  switch (option) {
    case "today":
      return { start: today, end: today };
    case "week": {
      const weekStart = new Date(now);
      weekStart.setDate(now.getDate() - now.getDay());
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);
      return {
        start: toLocalDateString(weekStart),
        end: toLocalDateString(weekEnd),
      };
    }
    case "month": {
      const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
      const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      return {
        start: toLocalDateString(monthStart),
        end: toLocalDateString(monthEnd),
      };
    }
    default:
      return { start: "", end: "" };
  }
}

interface UseTaskFiltersReturn {
  // Filter state
  showFilters: boolean;
  setShowFilters: (v: boolean) => void;
  selectedStatus: TaskStatus | null;
  setSelectedStatus: (s: TaskStatus | null) => void;
  selectedPriority: Priority | null;
  setSelectedPriority: (p: Priority | null) => void;
  quickDate: string;
  setQuickDate: (v: string) => void;
  startDate: string;
  setStartDate: (v: string) => void;
  endDate: string;
  setEndDate: (v: string) => void;
  sortBy: SortOption;
  setSortBy: (s: SortOption) => void;
  clearFilters: () => void;
  hasActiveFilters: boolean;

  // Sub-tab state — F03
  activeSubTab: SubTabKey;
  setActiveSubTab: (key: SubTabKey) => void;

  // View state — F08
  activeView: ViewKey;
  setActiveView: (view: ViewKey) => void;

  // Filtered data
  filteredTasks: Task[];

  // Batch operations
  selectMode: boolean;
  selectedIds: Set<string>;
  batchLoading: boolean;
  enterSelectMode: () => void;
  exitSelectMode: () => void;
  toggleSelect: (id: string) => void;
  selectAll: () => void;
  handleBatchDelete: () => Promise<void>;

  // Store access
  serviceUnavailable: boolean;
  fetchEntries: (params: { category_group: string; limit: number }) => Promise<void>;
}

export function useTaskFilters(): UseTaskFiltersReturn {
  const allTasks = useTaskStore((state) => state.tasks);
  const fetchEntries = useTaskStore((state) => state.fetchEntries);
  const serviceUnavailable = useTaskStore((state) => state.serviceUnavailable);
  const deleteTask = useTaskStore((state) => state.deleteTask);
  const [searchParams, setSearchParams] = useSearchParams();

  // 从 URL 初始化筛选状态（带合法性校验，防止 URL 篡改产生幽灵筛选）
  const initStatus = validateUrlParam<TaskStatus>(searchParams.get("status"), STATUS_OPTIONS);
  const initPriority = validateUrlParam<Priority>(searchParams.get("priority"), VALID_PRIORITIES);
  const initSort = validateUrlParam<SortOption>(searchParams.get("sort_by"), VALID_SORT_OPTIONS) ?? "";
  const initSubTab = validateUrlParam<SubTabKey>(searchParams.get("tab"), VALID_SUB_TAB_KEYS) ?? "all";
  const initView = validateUrlParam<ViewKey>(searchParams.get("view"), VALID_VIEW_KEYS) ?? "list";

  // 筛选状态
  const [showFilters, setShowFilters] = useState(false);
  const [selectedStatus, setSelectedStatusRaw] = useState<TaskStatus | null>(initStatus);
  const [selectedPriority, setSelectedPriorityRaw] = useState<Priority | null>(initPriority);
  const [sortBy, setSortByRaw] = useState<SortOption>(initSort);
  const [quickDate, setQuickDate] = useState<string>("all");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  // F03: 子 Tab 状态
  const [activeSubTab, setActiveSubTabRaw] = useState<SubTabKey>(initSubTab);

  // F08: 视图状态
  const [activeView, setActiveViewRaw] = useState<ViewKey>(initView);

  // URL 同步的 setter
  const setSelectedStatus = useCallback((s: TaskStatus | null) => {
    setSelectedStatusRaw(s);
    setSearchParams((prev) => {
      if (s) prev.set("status", s);
      else prev.delete("status");
      return prev;
    }, { replace: true });
  }, [setSearchParams]);

  const setSelectedPriority = useCallback((p: Priority | null) => {
    setSelectedPriorityRaw(p);
    setSearchParams((prev) => {
      if (p) prev.set("priority", p);
      else prev.delete("priority");
      return prev;
    }, { replace: true });
  }, [setSearchParams]);

  const setSortBy = useCallback((s: SortOption) => {
    setSortByRaw(s);
    setSearchParams((prev) => {
      if (s) prev.set("sort_by", s);
      else prev.delete("sort_by");
      return prev;
    }, { replace: true });
  }, [setSearchParams]);

  // F03: sub-tab URL 同步
  const setActiveSubTab = useCallback((key: SubTabKey) => {
    setActiveSubTabRaw(key);
    setSearchParams((prev) => {
      if (key && key !== "all") prev.set("tab", key);
      else prev.delete("tab");
      return prev;
    }, { replace: true });
  }, [setSearchParams]);

  // F08: view URL 同步
  const setActiveView = useCallback((view: ViewKey) => {
    setActiveViewRaw(view);
    setSearchParams((prev) => {
      if (view && view !== "list") prev.set("view", view);
      else prev.delete("view");
      return prev;
    }, { replace: true });
  }, [setSearchParams]);

  // 多选状态
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchLoading, setBatchLoading] = useState(false);

  // 首次挂载时加载数据
  useEffect(() => {
    const state = useTaskStore.getState();
    if (state.tasks.length === 0 && !state.serviceUnavailable) {
      state.fetchEntries(TASK_QUERY_PARAMS);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- 挂载时一次性检查 store 快照，无需响应 reactive 变化
  }, []);

  // 当快捷时间选项改变时，更新日期范围
  useEffect(() => {
    if (quickDate !== "custom") {
      const range = getDateRange(quickDate);
      setStartDate(range.start);
      setEndDate(range.end);
    }
  }, [quickDate]);

  // 本地筛选数据 — F03: 增加 category 过滤
  const filteredTasks = useMemo(() => {
    // F03: 先过滤只保留 actionable 类别
    let result = allTasks.filter((task) =>
      ACTIONABLE_CATEGORIES.includes(task.category)
    );

    // F03: 子 Tab category 过滤
    if (activeSubTab !== "all") {
      const tabDef = TASK_SUB_TABS.find(t => t.key === activeSubTab);
      if (tabDef && "category" in tabDef && tabDef.category) {
        result = result.filter((task) => task.category === tabDef.category);
      }
    }

    if (selectedStatus) {
      result = result.filter((task) => task.status === selectedStatus);
    }

    if (selectedPriority) {
      result = result.filter((task) => task.priority === selectedPriority);
    }

    if (startDate) {
      result = result.filter((task) => {
        const taskDate = task.planned_date || task.created_at;
        if (!taskDate) return false;
        return toLocalDateString(new Date(taskDate)) >= startDate;
      });
    }
    if (endDate) {
      result = result.filter((task) => {
        const taskDate = task.planned_date || task.created_at;
        if (!taskDate) return false;
        return toLocalDateString(new Date(taskDate)) <= endDate;
      });
    }

    // 排序
    if (sortBy === "priority") {
      const priorityOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
      result = [...result].sort((a, b) => {
        const pa = a.priority ? priorityOrder[a.priority] : 99;
        const pb = b.priority ? priorityOrder[b.priority] : 99;
        return pa - pb;
      });
    } else if (sortBy === "created_at") {
      result = [...result].sort((a, b) => {
        const da = a.created_at || "";
        const db = b.created_at || "";
        return db.localeCompare(da);
      });
    }

    return result;
  }, [allTasks, activeSubTab, selectedStatus, selectedPriority, startDate, endDate, sortBy]);

  const clearFilters = () => {
    setSelectedStatus(null);
    setSelectedPriority(null);
    setSortBy("");
    setQuickDate("all");
    setStartDate("");
    setEndDate("");
    setActiveSubTab("all");
  };

  const hasActiveFilters = !!(selectedStatus || selectedPriority || sortBy || startDate || endDate);

  // 多选操作
  const enterSelectMode = useCallback(() => {
    setSelectMode(true);
    setSelectedIds(new Set());
  }, []);

  const exitSelectMode = useCallback(() => {
    setSelectMode(false);
    setSelectedIds(new Set());
  }, []);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(filteredTasks.map((t) => t.id)));
  }, [filteredTasks]);

  // ESC 键退出多选模式
  useEffect(() => {
    if (!selectMode) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") exitSelectMode();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [selectMode, exitSelectMode]);

  // 批量删除
  const handleBatchDelete = async () => {
    setBatchLoading(true);
    let failed = 0;
    for (const id of selectedIds) {
      try { await deleteTask(id); } catch { failed++; }
    }
    setBatchLoading(false);
    if (failed === 0) {
      toast.success(`已删除 ${selectedIds.size} 条任务`);
      exitSelectMode();
    } else {
      toast.error(`${failed} 条删除失败`);
    }
  };

  return {
    showFilters,
    setShowFilters,
    selectedStatus,
    setSelectedStatus,
    selectedPriority,
    setSelectedPriority,
    quickDate,
    setQuickDate,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    sortBy,
    setSortBy,
    clearFilters,
    hasActiveFilters,
    activeSubTab,
    setActiveSubTab,
    activeView,
    setActiveView,
    filteredTasks,
    selectMode,
    selectedIds,
    batchLoading,
    enterSelectMode,
    exitSelectMode,
    toggleSelect,
    selectAll,
    handleBatchDelete,
    serviceUnavailable,
    fetchEntries,
  };
}
