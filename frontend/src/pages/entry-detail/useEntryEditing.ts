import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import { useTaskStore } from "@/stores/taskStore";
import type { Task, TaskStatus, Priority } from "@/types/task";

export interface EditingState {
  isEditing: boolean;
  isSaving: boolean;
  isExporting: boolean;
  editContent: string;
  editTitle: string;
  editTags: string[];
  editStatus: TaskStatus;
  editPriority: Priority;
  editPlannedDate: string;
  newTagInput: string;
  contentTab: "preview" | "edit";
  saveError: string | null;
  hasUnsavedChanges: boolean;
  setIsEditing: (v: boolean) => void;
  setIsExporting: (v: boolean) => void;
  setEditContent: React.Dispatch<React.SetStateAction<string>>;
  setEditTitle: React.Dispatch<React.SetStateAction<string>>;
  setEditTags: React.Dispatch<React.SetStateAction<string[]>>;
  setEditStatus: React.Dispatch<React.SetStateAction<TaskStatus>>;
  setEditPriority: React.Dispatch<React.SetStateAction<Priority>>;
  setEditPlannedDate: React.Dispatch<React.SetStateAction<string>>;
  setNewTagInput: React.Dispatch<React.SetStateAction<string>>;
  setContentTab: React.Dispatch<React.SetStateAction<"preview" | "edit">>;
  handleStartEdit: () => void;
  handleCancelEdit: () => void;
  handleSaveAll: () => Promise<void>;
  handleAddTag: () => void;
  handleRemoveTag: (tag: string) => void;
  handleNavigateBack: (navigate: (delta: number) => void) => void;
  autoSaveTimer: React.MutableRefObject<ReturnType<typeof setTimeout> | null>;
  lastSavedContent: React.MutableRefObject<string>;
}

export function useEntryEditing(
  entry: Task | null,
  setEntry: React.Dispatch<React.SetStateAction<Task | null>>,
): EditingState {
  const { id } = useParams<{ id: string }>();
  const { updateEntry } = useTaskStore();

  const [isEditing, setIsEditing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [editTitle, setEditTitle] = useState("");
  const [editTags, setEditTags] = useState<string[]>([]);
  const [editStatus, setEditStatus] = useState<TaskStatus>("waitStart");
  const [editPriority, setEditPriority] = useState<Priority>("medium");
  const [editPlannedDate, setEditPlannedDate] = useState("");
  const [newTagInput, setNewTagInput] = useState("");
  const [contentTab, setContentTab] = useState<"preview" | "edit">("preview");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // 自动保存 debounce
  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedContent = useRef("");

  // entry 加载/切换时同步 lastSavedContent（仅 entry.id 变化时触发）
  useEffect(() => {
    if (entry) {
      lastSavedContent.current = entry.content || "";
    }
  }, [entry?.id]);

  // 检测未保存变更
  useEffect(() => {
    if (!entry || !isEditing) {
      setHasUnsavedChanges(false);
      return;
    }
    const contentChanged = editContent !== (entry.content || "");
    const titleChanged = editTitle !== (entry.title || "");
    const tagsChanged = JSON.stringify(editTags) !== JSON.stringify(entry.tags || []);
    const statusChanged = editStatus !== entry.status;
    const priorityChanged = editPriority !== (entry.priority || "medium");
    const dateChanged = editPlannedDate !== (entry.planned_date ? entry.planned_date.split("T")[0] : "");
    setHasUnsavedChanges(contentChanged || titleChanged || tagsChanged || statusChanged || priorityChanged || dateChanged);
  }, [isEditing, editContent, editTitle, editTags, editStatus, editPriority, editPlannedDate, entry]);

  // 离开页面提示
  useEffect(() => {
    if (!hasUnsavedChanges) return;
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasUnsavedChanges]);

  // 自动保存：内容变化后 debounce 1s
  useEffect(() => {
    if (!isEditing || !id || !entry) return;
    if (editContent === lastSavedContent.current) return;

    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    autoSaveTimer.current = setTimeout(async () => {
      try {
        await updateEntry(id, { content: editContent });
        lastSavedContent.current = editContent;
        setEntry((prev) => prev ? { ...prev, content: editContent } : prev);
        setSaveError(null);
      } catch {
        setSaveError("自动保存失败，请手动保存");
      }
    }, 1000);
    return () => {
      if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    };
  }, [editContent, isEditing, id, entry, updateEntry, setEntry]);

  // 开始编辑
  const handleStartEdit = () => {
    if (!entry) return;
    setEditContent(entry.content || "");
    setEditTitle(entry.title || "");
    setEditTags([...(entry.tags || [])]);
    setEditStatus(entry.status || "waitStart");
    setEditPriority(entry.priority || "medium");
    setEditPlannedDate(entry.planned_date ? entry.planned_date.split("T")[0] : "");
    setContentTab("preview");
    setSaveError(null);
    setIsEditing(true);
  };

  // 取消编辑
  const handleCancelEdit = () => {
    if (!entry) return;
    setEditContent(entry.content || "");
    setEditTitle(entry.title || "");
    setEditTags([...(entry.tags || [])]);
    setEditStatus(entry.status || "waitStart");
    setEditPriority(entry.priority || "medium");
    setEditPlannedDate(entry.planned_date ? entry.planned_date.split("T")[0] : "");
    setIsEditing(false);
    setSaveError(null);
  };

  // 保存所有编辑
  const handleSaveAll = async () => {
    if (!id) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      const update: Record<string, unknown> = {};
      if (editTitle !== (entry?.title || "")) update.title = editTitle;
      if (editContent !== (entry?.content || "")) update.content = editContent;
      if (JSON.stringify(editTags) !== JSON.stringify(entry?.tags || [])) update.tags = editTags;
      if (editStatus !== entry?.status) update.status = editStatus;
      if (editPriority !== (entry?.priority || "medium")) update.priority = editPriority;
      if (editPlannedDate !== (entry?.planned_date ? entry.planned_date.split("T")[0] : "")) update.planned_date = editPlannedDate || null;

      if (Object.keys(update).length > 0) {
        await updateEntry(id, update);
        setEntry((prev) => prev ? {
          ...prev,
          title: editTitle,
          content: editContent,
          tags: editTags,
          status: editStatus,
          priority: editPriority,
          planned_date: editPlannedDate || prev.planned_date,
        } : prev);
        lastSavedContent.current = editContent;
      }
      setIsEditing(false);
    } catch (err) {
      setSaveError("保存失败，请重试");
      console.error("保存失败:", err);
    } finally {
      setIsSaving(false);
    }
  };

  // 添加标签
  const handleAddTag = useCallback(() => {
    const tag = newTagInput.trim();
    if (!tag || editTags.includes(tag)) return;
    setEditTags((prev) => [...prev, tag]);
    setNewTagInput("");
  }, [newTagInput, editTags]);

  // 删除标签
  const handleRemoveTag = useCallback((tag: string) => {
    setEditTags((prev) => prev.filter((t) => t !== tag));
  }, []);

  // 导航拦截
  const handleNavigateBack = useCallback((navigate: (delta: number) => void) => {
    if (hasUnsavedChanges) {
      const ok = window.confirm("有未保存的变更，确定要离开吗？");
      if (!ok) return;
    }
    navigate(-1);
  }, [hasUnsavedChanges]);

  return {
    isEditing,
    isSaving,
    isExporting,
    editContent,
    editTitle,
    editTags,
    editStatus,
    editPriority,
    editPlannedDate,
    newTagInput,
    contentTab,
    saveError,
    hasUnsavedChanges,
    setIsEditing,
    setIsExporting,
    setEditContent,
    setEditTitle,
    setEditTags,
    setEditStatus,
    setEditPriority,
    setEditPlannedDate,
    setNewTagInput,
    setContentTab,
    handleStartEdit,
    handleCancelEdit,
    handleSaveAll,
    handleAddTag,
    handleRemoveTag,
    handleNavigateBack,
    autoSaveTimer,
    lastSavedContent,
  };
}
