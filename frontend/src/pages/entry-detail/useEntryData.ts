import { useState, useCallback, useEffect } from "react";
import { useParams } from "react-router-dom";
import { getEntry, getEntries, getProjectProgress } from "@/services/api";
import { useServiceUnavailable } from "@/hooks/useServiceUnavailable";
import type { Task } from "@/types/task";
import type { ProjectProgressResponse } from "@/services/api";

export interface EntryDataState {
  entry: Task | null;
  isLoading: boolean;
  error: string | null;
  childTasks: Task[];
  projectProgress: ProjectProgressResponse | null;
  parentEntry: Task | null;
  referencedNotes: Map<string, Task>;
  serviceUnavailable: boolean;
  retryService: (fn: () => Promise<void>) => void;
  reloadEntry: () => Promise<void>;
  setEntry: React.Dispatch<React.SetStateAction<Task | null>>;
}

export function useEntryData(): EntryDataState {
  const { id } = useParams<{ id: string }>();
  const [entry, setEntry] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [childTasks, setChildTasks] = useState<Task[]>([]);
  const [projectProgress, setProjectProgress] = useState<ProjectProgressResponse | null>(null);
  const [parentEntry, setParentEntry] = useState<Task | null>(null);
  const [referencedNotes, setReferencedNotes] = useState<Map<string, Task>>(new Map());

  const { serviceUnavailable, runWith503, retry: retryService } = useServiceUnavailable();

  const reloadEntry = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      await runWith503(async () => {
        const data = await getEntry(id);
        setEntry(data);
        // 清除上次加载的关联数据（防止路由切换残留）
        setChildTasks([]);
        setProjectProgress(null);
        setParentEntry(null);
        setReferencedNotes(new Map());

        if (data.category === "project") {
          const [tasksRes, progressRes] = await Promise.all([
            getEntries({ parent_id: id, limit: 100 }),
            getProjectProgress(id).catch(() => null),
          ]);
          setChildTasks(tasksRes.entries);
          setProjectProgress(progressRes);
        }

        if (data.parent_id) {
          try {
            const parentData = await getEntry(data.parent_id);
            setParentEntry(parentData);
          } catch {
            // parent may be deleted
          }
        }

        const noteIds = data.content?.match(/\[\[([^\]]+)\]\]/g)?.map((m) => m.slice(2, -2)) || [];
        if (noteIds.length > 0) {
          const notesMap = new Map<string, Task>();
          await Promise.all(
            noteIds.map(async (noteId) => {
              try {
                const noteData = await getEntry(noteId);
                notesMap.set(noteId, noteData);
              } catch {
                // referenced note may not exist
              }
            })
          );
          setReferencedNotes(notesMap);
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "获取条目失败");
    } finally {
      setIsLoading(false);
    }
  }, [id, runWith503]);

  useEffect(() => { reloadEntry(); }, [reloadEntry]);

  return {
    entry,
    setEntry,
    isLoading,
    error,
    childTasks,
    projectProgress,
    parentEntry,
    referencedNotes,
    serviceUnavailable,
    retryService,
    reloadEntry,
  };
}
