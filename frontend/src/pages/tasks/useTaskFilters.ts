import { useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useTaskStore } from "@/stores/taskStore";
import type { Task, TaskStatus, Category, Priority } from "@/types/task";
import { toast } from "sonner";
import { TASK_QUERY_PARAMS, STATUS_OPTIONS, SORT_OPTIONS, type SortOption } from "./constants";

// === URL 参数合法性校验 ===
const VALID_PRIORITIES: Priority[] = ["high", "medium", "low"];
const VALID_SORT_OPTIONS: SortOption[] = SORT_OPTIONS.map(o => o.value);

function validateUrlParam<T>(value: string | null, validValues: readonly T[]): T | null {
  if (!value) return null;
  return validValues.includes(value as T) ? (value as T) : null;
}

// 获取日期范围
function getDateRange(option: string) {
  const now = new Date();
  const today = now.toISOString().split("T")[0];

  switch (option) {
    case "today":
      return { start: today, end: today };
    case "week": {
      const weekStart = new Date(now);
      weekStart.setDate(now.getDate() - now.getDay());
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);
      return {
        start: weekStart.toISOString().split("T")[0],
        end: weekEnd.toISOString().split("T")[0],
      };
    }
    case "month": {
      const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
      const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      return {
        start: monthStart.toISOString().split("T")[0],
        end: monthEnd.toISOString().split("T")[0],
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
  handleBatchCategory: (category: Category) => Promise<void>;

  // Store access
  serviceUnavailable: boolean;
  fetchEntries: (params: { type: string; limit: number }) => Promise<void>;
}

export function useTaskFilters(): UseTaskFiltersReturn {
  const allTasks = useTaskStore((state) => state.tasks);
  const fetchEntries = useTaskStore((state) => state.fetchEntries);
  const serviceUnavailable = useTaskStore((state) => state.serviceUnavailable);
  const deleteTask = useTaskStore((state) => state.deleteTask);
  const storeUpdateEntry = useTaskStore((state) => state.updateEntry);
  const [searchParams, setSearchParams] = useSearchParams();

  // 从 URL 初始化筛选状态（带合法性校验，防止 URL 篡改产生幽灵筛选）
  const initStatus = validateUrlParam<TaskStatus>(searchParams.get("status"), STATUS_OPTIONS);
  const initPriority = validateUrlParam<Priority>(searchParams.get("priority"), VALID_PRIORITIES);
  const initSort = validateUrlParam<SortOption>(searchParams.get("sort_by"), VALID_SORT_OPTIONS) ?? "";

  // 筛选状态
  const [showFilters, setShowFilters] = useState(false);
  const [selectedStatus, setSelectedStatusRaw] = useState<TaskStatus | null>(initStatus);
  const [selectedPriority, setSelectedPriorityRaw] = useState<Priority | null>(initPriority);
  const [sortBy, setSortByRaw] = useState<SortOption>(initSort);
  const [quickDate, setQuickDate] = useState<string>("all");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

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
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 当快捷时间选项改变时，更新日期范围
  useEffect(() => {
    if (quickDate !== "custom") {
      const range = getDateRange(quickDate);
      setStartDate(range.start);
      setEndDate(range.end);
    }
  }, [quickDate]);

  // 本地筛选数据
  const filteredTasks = useMemo(() => {
    let result = allTasks;

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
        return taskDate.split("T")[0] >= startDate;
      });
    }
    if (endDate) {
      result = result.filter((task) => {
        const taskDate = task.planned_date || task.created_at;
        if (!taskDate) return false;
        return taskDate.split("T")[0] <= endDate;
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
  }, [allTasks, selectedStatus, selectedPriority, startDate, endDate, sortBy]);

  const clearFilters = () => {
    setSelectedStatus(null);
    setSelectedPriority(null);
    setSortBy("");
    setQuickDate("all");
    setStartDate("");
    setEndDate("");
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

  // 批量转分类
  const handleBatchCategory = async (category: Category) => {
    setBatchLoading(true);
    let failed = 0;
    for (const id of selectedIds) {
      try { await storeUpdateEntry(id, { category }); } catch { failed++; }
    }
    setBatchLoading(false);
    const label = category === "task" ? "任务" : category === "note" ? "笔记" : "灵感";
    if (failed === 0) {
      toast.success(`已转为${label} ${selectedIds.size} 条`);
      exitSelectMode();
    } else {
      toast.error(`${failed} 条转换失败`);
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
    filteredTasks,
    selectMode,
    selectedIds,
    batchLoading,
    enterSelectMode,
    exitSelectMode,
    toggleSelect,
    selectAll,
    handleBatchDelete,
    handleBatchCategory,
    serviceUnavailable,
    fetchEntries,
  };
}
