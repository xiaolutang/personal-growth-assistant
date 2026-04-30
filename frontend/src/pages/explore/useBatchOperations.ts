import { useState, useCallback, useEffect, useRef } from "react";
import { useTaskStore } from "@/stores/taskStore";
import { toast } from "sonner";
import { subscribeSyncProgress } from "@/lib/offlineSync";
import type { SyncEvent } from "@/lib/offlineSync";
import { convertEntry } from "@/services/api";
import type { Task, Category } from "@/types/task";

interface UseBatchOperationsProps {
  filteredTasks: Task[];
  setEntries: React.Dispatch<React.SetStateAction<Task[]>>;
  setSearchResults: React.Dispatch<React.SetStateAction<Task[] | null>>;
  /** 同步完成后回调（用于刷新列表） */
  onSyncCompleted?: () => void;
}

export function useBatchOperations({
  filteredTasks,
  setEntries,
  setSearchResults,
  onSyncCompleted,
}: UseBatchOperationsProps) {
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchLoading, setBatchLoading] = useState(false);
  const [failedItems, setFailedItems] = useState<{ id: string; title: string }[]>([]);
  const [offlineMode, setOfflineMode] = useState(false);
  const deleteTask = useTaskStore((state) => state.deleteTask);
  const storeUpdateEntry = useTaskStore((state) => state.updateEntry);

  // 用于在批量操作期间追踪是否为离线批量操作，以决定同步完成后是否自动退出多选
  const pendingOfflineCountRef = useRef(0);

  const enterSelectMode = useCallback(() => {
    setSelectMode(true);
    setSelectedIds(new Set());
    setFailedItems([]);
    setOfflineMode(false);
  }, []);

  const exitSelectMode = useCallback(() => {
    setSelectMode(false);
    setSelectedIds(new Set());
    setFailedItems([]);
    setOfflineMode(false);
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

  // 订阅同步完成事件：联网回放成功后刷新列表
  // 只要有 pending 离线操作就监听，不依赖 selectMode
  useEffect(() => {
    const unsub = subscribeSyncProgress((event: SyncEvent) => {
      if (event.type === "completed" && pendingOfflineCountRef.current > 0) {
        pendingOfflineCountRef.current = 0;
        setOfflineMode(false);
        onSyncCompleted?.();
        toast.success("离线操作已同步完成");
        if (selectMode) {
          exitSelectMode();
        }
      }
    });
    return unsub;
  }, [onSyncCompleted, exitSelectMode, selectMode]);

  // 获取条目标题的辅助函数
  const getTaskTitle = useCallback(
    (id: string): string => {
      const task = filteredTasks.find((t) => t.id === id);
      return task?.title ?? id;
    },
    [filteredTasks]
  );

  // 批量删除
  const handleBatchDelete = useCallback(async () => {
    if (!confirm(`确定要删除选中的 ${selectedIds.size} 条内容吗？`)) return;
    setBatchLoading(true);
    setFailedItems([]);

    const isOffline = !navigator.onLine;
    if (isOffline) {
      setOfflineMode(true);
    }

    let failed = 0;
    const deletedIds: string[] = [];
    const failures: { id: string; title: string }[] = [];

    for (const id of selectedIds) {
      await deleteTask(id);
      if (useTaskStore.getState().error) {
        failed++;
        failures.push({ id, title: getTaskTitle(id) });
        useTaskStore.setState({ error: null });
      } else {
        deletedIds.push(id);
      }
    }
    setBatchLoading(false);
    if (deletedIds.length > 0) {
      setEntries((prev) => prev.filter((e) => !deletedIds.includes(e.id)));
      setSearchResults((prev) => prev ? prev.filter((e) => !deletedIds.includes(e.id)) : null);
    }
    if (failed === 0) {
      if (isOffline) {
        pendingOfflineCountRef.current = deletedIds.length;
        toast.success(`离线：已标记删除 ${deletedIds.length} 条，联网后自动同步`);
      } else {
        toast.success(`已删除 ${deletedIds.length} 条内容`);
      }
      exitSelectMode();
    } else {
      setFailedItems(failures);
      if (isOffline) {
        pendingOfflineCountRef.current = deletedIds.length;
        toast.error(`${failed} 条删除失败`, {
          description: failures.map((f) => f.title).join("、"),
        });
      } else {
        toast.error(`${failed} 条删除失败`, {
          description: failures.map((f) => f.title).join("、"),
        });
      }
    }
  }, [selectedIds, deleteTask, setEntries, setSearchResults, exitSelectMode, getTaskTitle]);

  // 批量转分类
  const handleBatchCategory = useCallback(async (category: Category) => {
    setBatchLoading(true);
    setFailedItems([]);

    const isOffline = !navigator.onLine;
    if (isOffline) {
      setOfflineMode(true);
    }

    let failed = 0;
    const updatedIds: string[] = [];
    const failures: { id: string; title: string }[] = [];

    for (const id of selectedIds) {
      await storeUpdateEntry(id, { category });
      if (useTaskStore.getState().error) {
        failed++;
        failures.push({ id, title: getTaskTitle(id) });
        useTaskStore.setState({ error: null });
      } else {
        updatedIds.push(id);
      }
    }
    setBatchLoading(false);
    if (updatedIds.length > 0) {
      setEntries((prev) => prev.map((e) => updatedIds.includes(e.id) ? { ...e, category } : e));
      setSearchResults((prev) => prev ? prev.map((e) => updatedIds.includes(e.id) ? { ...e, category } : e) : null);
    }
    const label = category === "task" ? "任务" : category === "note" ? "笔记" : "灵感";
    if (failed === 0) {
      if (isOffline) {
        pendingOfflineCountRef.current = updatedIds.length;
        toast.success(`离线：已标记转为${label} ${updatedIds.length} 条，联网后自动同步`);
      } else {
        toast.success(`已转为${label} ${updatedIds.length} 条`);
      }
      exitSelectMode();
    } else {
      setFailedItems(failures);
      if (isOffline) {
        pendingOfflineCountRef.current = updatedIds.length;
        toast.error(`${failed} 条转换失败`, {
          description: failures.map((f) => f.title).join("、"),
        });
      } else {
        toast.error(`${failed} 条转换失败`, {
          description: failures.map((f) => f.title).join("、"),
        });
      }
    }
  }, [selectedIds, storeUpdateEntry, setEntries, setSearchResults, exitSelectMode, getTaskTitle]);

  // 清除失败提示
  const clearFailedItems = useCallback(() => {
    setFailedItems([]);
  }, []);

  // F07: 批量转化（使用 POST /entries/{id}/convert API）
  const handleBatchConvert = useCallback(async (targetCategory: "task" | "decision") => {
    setBatchLoading(true);
    setFailedItems([]);

    let failed = 0;
    const convertedIds: string[] = [];
    const failures: { id: string; title: string }[] = [];

    for (const id of selectedIds) {
      const task = filteredTasks.find((t) => t.id === id);
      if (!task || task.category !== "inbox") {
        // 非 inbox 条目跳过（计为失败）
        failed++;
        failures.push({ id, title: task?.title ?? id });
        continue;
      }
      try {
        await convertEntry(id, { target_category: targetCategory });
        convertedIds.push(id);
      } catch {
        failed++;
        failures.push({ id, title: task.title });
      }
    }
    setBatchLoading(false);

    // 移除成功转化的条目
    if (convertedIds.length > 0) {
      setEntries((prev) => prev.filter((e) => !convertedIds.includes(e.id)));
      setSearchResults((prev) => prev ? prev.filter((e) => !convertedIds.includes(e.id)) : null);
    }

    const label = targetCategory === "task" ? "任务" : "决策";
    if (failed === 0) {
      toast.success(`已转为${label} ${convertedIds.length} 条`);
      exitSelectMode();
    } else {
      setFailedItems(failures);
      toast.error(`${failed} 条转化失败`, {
        description: failures.map((f) => f.title).join("、"),
      });
      if (convertedIds.length > 0) {
        toast.success(`已成功转化 ${convertedIds.length} 条`);
      }
    }
  }, [selectedIds, filteredTasks, setEntries, setSearchResults, exitSelectMode]);

  // F07: 判断选中条目是否全部为 inbox 类型
  const allSelectedInbox = filteredTasks.length > 0 && Array.from(selectedIds).every((id) => {
    const task = filteredTasks.find((t) => t.id === id);
    return task?.category === "inbox";
  });

  return {
    selectMode,
    selectedIds,
    batchLoading,
    failedItems,
    offlineMode,
    enterSelectMode,
    exitSelectMode,
    toggleSelect,
    selectAll,
    handleBatchDelete,
    handleBatchCategory,
    handleBatchConvert,
    allSelectedInbox,
    clearFailedItems,
  };
}
