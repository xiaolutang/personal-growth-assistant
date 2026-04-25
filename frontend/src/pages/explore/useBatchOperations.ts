import { useState, useCallback, useEffect } from "react";
import { useTaskStore } from "@/stores/taskStore";
import { toast } from "sonner";
import type { Task, Category } from "@/types/task";

interface UseBatchOperationsProps {
  filteredTasks: Task[];
  setEntries: React.Dispatch<React.SetStateAction<Task[]>>;
  setSearchResults: React.Dispatch<React.SetStateAction<Task[] | null>>;
}

export function useBatchOperations({
  filteredTasks,
  setEntries,
  setSearchResults,
}: UseBatchOperationsProps) {
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchLoading, setBatchLoading] = useState(false);
  const deleteTask = useTaskStore((state) => state.deleteTask);
  const storeUpdateEntry = useTaskStore((state) => state.updateEntry);

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
  const handleBatchDelete = useCallback(async () => {
    if (!confirm(`确定要删除选中的 ${selectedIds.size} 条内容吗？`)) return;
    setBatchLoading(true);
    let failed = 0;
    const deletedIds: string[] = [];
    for (const id of selectedIds) {
      await deleteTask(id);
      if (useTaskStore.getState().error) {
        failed++;
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
      toast.success(`已删除 ${deletedIds.length} 条内容`);
      exitSelectMode();
    } else {
      toast.error(`${failed} 条删除失败`);
    }
  }, [selectedIds, deleteTask, setEntries, setSearchResults, exitSelectMode]);

  // 批量转分类
  const handleBatchCategory = useCallback(async (category: Category) => {
    setBatchLoading(true);
    let failed = 0;
    const updatedIds: string[] = [];
    for (const id of selectedIds) {
      await storeUpdateEntry(id, { category });
      if (useTaskStore.getState().error) {
        failed++;
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
      toast.success(`已转为${label} ${updatedIds.length} 条`);
      exitSelectMode();
    } else {
      toast.error(`${failed} 条转换失败`);
    }
  }, [selectedIds, storeUpdateEntry, setEntries, setSearchResults, exitSelectMode]);

  return {
    selectMode,
    selectedIds,
    batchLoading,
    enterSelectMode,
    exitSelectMode,
    toggleSelect,
    selectAll,
    handleBatchDelete,
    handleBatchCategory,
  };
}
