import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowLeft,
  Loader2,
  Calendar,
  Clock,
  Tag,
  CheckCircle,
  Circle,
  Pause,
  XCircle,
  BarChart3,
  Link2,
  Edit2,
  Save,
  X,
  FileText,
  Eye,
  Code,
  Plus,
  AlertCircle,
  Sparkles,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Trash2,
  Scale,
  RotateCcw,
  HelpCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { getEntry, getEntries, getProjectProgress, getRelatedEntries, generateEntrySummary, getKnowledgeContext, getEntryLinks, deleteEntryLink } from "@/services/api";
import type { RelatedEntry, EntrySummaryResponse, KnowledgeContextResponse, EntryLinkItem } from "@/services/api";
import { useTaskStore } from "@/stores/taskStore";
import type { Task, TaskStatus, Priority } from "@/types/task";
import type { ProjectProgressResponse } from "@/services/api";
import { PageChatPanel } from "@/components/PageChatPanel";
import { statusConfig, categoryConfig, priorityConfig } from "@/config/constants";
import { TaskList } from "@/components/TaskList";
import { KnowledgeGraphThumbnail } from "@/components/KnowledgeGraphThumbnail";
import { LinkEntryDialog } from "@/components/LinkEntryDialog";

type ContentTab = "preview" | "edit";

/** 共享的 Markdown 链接渲染器：/entry/ 走 SPA 导航，其他走原生跳转 */
function getMarkdownComponents(navigate: (path: string) => void) {
  return {
    a: ({ href, children }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { children?: React.ReactNode }) => {
      if (href?.startsWith("/entry/")) {
        return (
          <span
            className="text-primary hover:underline cursor-pointer"
            onClick={() => navigate(href)}
          >
            {children}
          </span>
        );
      }
      return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
    },
  };
}

/** 将 Markdown 按 ## 分割成结构化 sections 并以卡片形式渲染 */
function StructuredContent({ content, category, navigate }: { content: string; category: string; navigate: (path: string) => void }) {
  const sections = content.split(/\n(?=## )/).filter(Boolean);
  if (sections.length === 0) {
    return <div className="prose prose-sm dark:prose-invert max-w-none">{content || "暂无内容"}</div>;
  }

  const sectionLabels: Record<string, Record<string, string>> = {
    decision: {
      "决策背景": "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800",
      "可选方案": "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800",
      "最终选择": "bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800",
      "选择理由": "bg-purple-50 dark:bg-purple-950/30 border-purple-200 dark:border-purple-800",
    },
    reflection: {
      "回顾目标": "bg-teal-50 dark:bg-teal-950/30 border-teal-200 dark:border-teal-800",
      "实际结果": "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800",
      "经验教训": "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800",
      "下一步行动": "bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800",
    },
    question: {
      "问题描述": "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800",
      "相关背景": "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800",
      "思考方向": "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800",
    },
  };
  const colorMap = sectionLabels[category] || {};

  return (
    <div className="space-y-3">
      {sections.map((section, i) => {
        const match = section.match(/^## (.+)/);
        const title = match ? match[1].trim() : "";
        const body = match ? section.slice(match[0].length).trim() : section.trim();
        const colorClass = colorMap[title] || "bg-muted/50 border-border";

        return (
          <div key={i} className={`rounded-lg border p-4 ${colorClass}`}>
            {title && (
              <h3 className="text-sm font-semibold mb-2">{title}</h3>
            )}
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={getMarkdownComponents(navigate)}
              >
                {body || "（待补充）"}
              </ReactMarkdown>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function EntryDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [entry, setEntry] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [childTasks, setChildTasks] = useState<Task[]>([]);
  const [projectProgress, setProjectProgress] = useState<ProjectProgressResponse | null>(null);
  const [parentEntry, setParentEntry] = useState<Task | null>(null);
  const [referencedNotes, setReferencedNotes] = useState<Map<string, Task>>(new Map());
  const [relatedEntries, setRelatedEntries] = useState<RelatedEntry[]>([]);
  const [relatedLoading, setRelatedLoading] = useState(false);
  const [relatedError, setRelatedError] = useState(false);

  // 知识上下文状态
  const [knowledgeContext, setKnowledgeContext] = useState<KnowledgeContextResponse | null>(null);
  const [knowledgeContextLoading, setKnowledgeContextLoading] = useState(false);
  const [knowledgeContextError, setKnowledgeContextError] = useState(false);
  const [knowledgeContextExpanded, setKnowledgeContextExpanded] = useState(true);

  // 手动关联状态
  const [entryLinks, setEntryLinks] = useState<EntryLinkItem[]>([]);
  const [, setEntryLinksLoading] = useState(false);
  const [showLinkDialog, setShowLinkDialog] = useState(false);
  const [deletingLinkId, setDeletingLinkId] = useState<string | null>(null);

  // AI 摘要状态
  const [aiSummaryExpanded, setAiSummaryExpanded] = useState(false);
  const [aiSummaryData, setAiSummaryData] = useState<EntrySummaryResponse | null>(null);
  const [aiSummaryLoading, setAiSummaryLoading] = useState(false);
  const [aiSummaryError, setAiSummaryError] = useState<string | null>(null);
  const aiSummaryFetched = useRef(false);

  // 编辑模式状态
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [editTitle, setEditTitle] = useState("");
  const [editTags, setEditTags] = useState<string[]>([]);
  const [editStatus, setEditStatus] = useState<TaskStatus>("waitStart");
  const [editPriority, setEditPriority] = useState<Priority>("medium");
  const [editPlannedDate, setEditPlannedDate] = useState("");
  const [newTagInput, setNewTagInput] = useState("");
  const [contentTab, setContentTab] = useState<ContentTab>("preview");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const { updateEntry } = useTaskStore();

  // 自动保存 debounce
  const autoSaveTimer = useRef<ReturnType<typeof setTimeout>>(null);
  const lastSavedContent = useRef("");

  // 解析内容中的 [[note-id]] 引用
  const parsedContent = useMemo(() => {
    if (!entry?.content) return entry?.content || "";
    return entry.content.replace(/\[\[([^\]]+)\]\]/g, (_match, noteId) => {
      const refNote = referencedNotes.get(noteId);
      if (refNote) {
        return `[${refNote.title}](/entry/${noteId})`;
      }
      return `[${noteId}](/entry/${noteId})`;
    });
  }, [entry?.content, referencedNotes]);

  // 提取内容中的所有引用 ID
  const referenceIds = useMemo(() => {
    if (!entry?.content) return [];
    const matches = entry.content.match(/\[\[([^\]]+)\]\]/g) || [];
    return matches.map((m) => m.slice(2, -2));
  }, [entry?.content]);

  useEffect(() => {
    if (!id) return;

    const fetchEntry = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getEntry(id);
        setEntry(data);
        setEditContent(data.content || "");
        setEditTitle(data.title || "");
        setEditTags(data.tags || []);
        setEditStatus(data.status || "waitStart");
        setEditPriority(data.priority || "medium");
        setEditPlannedDate(data.planned_date ? data.planned_date.split("T")[0] : "");
        lastSavedContent.current = data.content || "";

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
      } catch (err) {
        setError(err instanceof Error ? err.message : "获取条目失败");
      } finally {
        setIsLoading(false);
      }
    };

    fetchEntry();
  }, [id]);

  // 关联条目独立加载
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setRelatedLoading(true);
    setRelatedError(false);
    getRelatedEntries(id)
      .then((related) => {
        if (!cancelled) setRelatedEntries(related);
      })
      .catch(() => {
        if (!cancelled) setRelatedError(true);
      })
      .finally(() => {
        if (!cancelled) setRelatedLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

  // 手动关联加载
  const loadEntryLinks = useCallback(() => {
    if (!id) return;
    setEntryLinksLoading(true);
    getEntryLinks(id)
      .then((data) => setEntryLinks(data.links))
      .catch(() => {}) // 不阻塞页面
      .finally(() => setEntryLinksLoading(false));
  }, [id]);

  useEffect(() => {
    loadEntryLinks();
  }, [loadEntryLinks]);

  // 删除手动关联
  const handleDeleteLink = useCallback(async (linkId: string) => {
    if (!id) return;
    setDeletingLinkId(linkId);
    try {
      await deleteEntryLink(id, linkId);
      setEntryLinks((prev) => prev.filter((l) => l.id !== linkId));
    } catch {
      // 失败不更新列表
    } finally {
      setDeletingLinkId(null);
    }
  }, [id]);

  // 知识上下文独立加载
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setKnowledgeContextLoading(true);
    setKnowledgeContextError(false);
    getKnowledgeContext(id)
      .then((data) => {
        if (!cancelled) setKnowledgeContext(data);
      })
      .catch(() => {
        if (!cancelled) setKnowledgeContextError(true);
      })
      .finally(() => {
        if (!cancelled) setKnowledgeContextLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

  // AI 摘要加载：首次展开时自动请求，id 变化时重置
  useEffect(() => {
    setAiSummaryData(null);
    setAiSummaryError(null);
    setAiSummaryLoading(false);
    setAiSummaryExpanded(false);
    aiSummaryFetched.current = false;
  }, [id]);

  const handleToggleAiSummary = useCallback(() => {
    if (!aiSummaryExpanded) {
      // 展开
      setAiSummaryExpanded(true);
      if (!aiSummaryFetched.current && !aiSummaryLoading) {
        setAiSummaryLoading(true);
        setAiSummaryError(null);
        aiSummaryFetched.current = true;
        generateEntrySummary(id!)
          .then((data) => {
            setAiSummaryData(data);
          })
          .catch((err) => {
            setAiSummaryError(err instanceof Error ? err.message : "生成摘要失败");
            aiSummaryFetched.current = false; // 允许重试
          })
          .finally(() => {
            setAiSummaryLoading(false);
          });
      }
    } else {
      // 收起
      setAiSummaryExpanded(false);
    }
  }, [aiSummaryExpanded, aiSummaryLoading, id]);

  const handleRetryAiSummary = useCallback(() => {
    setAiSummaryError(null);
    setAiSummaryLoading(true);
    aiSummaryFetched.current = true;
    generateEntrySummary(id!)
      .then((data) => {
        setAiSummaryData(data);
      })
      .catch((err) => {
        setAiSummaryError(err instanceof Error ? err.message : "生成摘要失败");
        aiSummaryFetched.current = false;
      })
      .finally(() => {
        setAiSummaryLoading(false);
      });
  }, [id]);

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
  }, [editContent, isEditing, id, entry, updateEntry]);

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
  const handleNavigateBack = useCallback(() => {
    if (hasUnsavedChanges) {
      const ok = window.confirm("有未保存的变更，确定要离开吗？");
      if (!ok) return;
    }
    navigate(-1);
  }, [hasUnsavedChanges, navigate]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !entry) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-muted-foreground">{error || "条目不存在"}</p>
        <Button variant="outline" onClick={() => navigate(-1)}>
          返回
        </Button>
      </div>
    );
  }

  const statusInfo = statusConfig[entry.status];
  const categoryInfo = categoryConfig[entry.category];
  const CategoryIcon = categoryInfo.icon;

  const renderStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case "complete": return <CheckCircle className="h-4 w-4 text-green-500 dark:text-green-400" />;
      case "doing": return <Circle className="h-4 w-4 text-yellow-500 dark:text-yellow-400" />;
      case "paused": return <Pause className="h-4 w-4 text-orange-500 dark:text-orange-400" />;
      case "cancelled": return <XCircle className="h-4 w-4 text-red-500 dark:text-red-400" />;
      default: return <Circle className="h-4 w-4" />;
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto p-4 md:p-6">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Button variant="ghost" size="sm" onClick={handleNavigateBack}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回
            </Button>
            {!isEditing ? (
              <Button variant="outline" size="sm" onClick={handleStartEdit}>
                <Edit2 className="h-4 w-4 mr-2" />
                编辑
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button size="sm" onClick={handleSaveAll} disabled={isSaving}>
                  {isSaving ? (
                    <><Loader2 className="h-4 w-4 mr-2 animate-spin" />保存中...</>
                  ) : (
                    <><Save className="h-4 w-4 mr-2" />保存</>
                  )}
                </Button>
                <Button variant="outline" size="sm" onClick={handleCancelEdit} disabled={isSaving}>
                  <X className="h-4 w-4 mr-2" />
                  取消
                </Button>
              </div>
            )}
          </div>

          {/* 保存错误提示 */}
          {saveError && (
            <div className="flex items-center gap-2 mb-4 p-2 rounded-lg bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 text-sm">
              <AlertCircle className="h-4 w-4" />
              {saveError}
            </div>
          )}

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 mt-1">
              <CategoryIcon className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              {/* 标题 — inline editable */}
              {isEditing ? (
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="text-2xl font-bold mb-2 w-full border-b-2 border-primary bg-transparent focus:outline-none"
                  placeholder="输入标题..."
                />
              ) : (
                <h1 className="text-2xl font-bold mb-2">{entry.title}</h1>
              )}

              <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                {/* Category */}
                <Badge variant="secondary">{categoryInfo.label}</Badge>

                {/* Status */}
                {isEditing ? (
                  <select
                    value={editStatus}
                    onChange={(e) => setEditStatus(e.target.value as TaskStatus)}
                    className="text-sm border rounded px-1.5 py-0.5 bg-background"
                  >
                    {Object.entries(statusConfig).map(([key, cfg]) => (
                      <option key={key} value={key}>{cfg.label}</option>
                    ))}
                  </select>
                ) : (
                  <div className="flex items-center gap-1">
                    {renderStatusIcon(entry.status)}
                    <span>{statusInfo.label}</span>
                  </div>
                )}

                {/* Priority */}
                {isEditing ? (
                  <select
                    value={editPriority}
                    onChange={(e) => setEditPriority(e.target.value as Priority)}
                    className="text-sm border rounded px-1.5 py-0.5 bg-background"
                  >
                    {Object.entries(priorityConfig).map(([key, cfg]) => (
                      <option key={key} value={key}>优先级: {cfg.label}</option>
                    ))}
                  </select>
                ) : (
                  entry.priority && entry.priority !== "medium" && (
                    <Badge variant={priorityConfig[entry.priority].variant}>
                      优先级: {priorityConfig[entry.priority].label}
                    </Badge>
                  )
                )}

                {/* Planned Date */}
                {isEditing ? (
                  <div className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    <input
                      type="date"
                      value={editPlannedDate}
                      onChange={(e) => setEditPlannedDate(e.target.value)}
                      className="text-sm border rounded px-1.5 py-0.5 bg-background"
                    />
                  </div>
                ) : (
                  entry.planned_date && (
                    <div className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      <span>计划 {new Date(entry.planned_date).toLocaleDateString()}</span>
                    </div>
                  )
                )}

                {/* Created date */}
                {entry.created_at && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    <span>创建于 {new Date(entry.created_at).toLocaleDateString()}</span>
                  </div>
                )}

                {/* Updated date */}
                {entry.updated_at && entry.updated_at !== entry.created_at && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    <span>更新于 {new Date(entry.updated_at).toLocaleDateString()}</span>
                  </div>
                )}
              </div>

              {/* Tags */}
              <div className="flex items-center gap-2 mt-3">
                <Tag className="h-4 w-4 text-muted-foreground shrink-0" />
                <div className="flex flex-wrap gap-1">
                  {(isEditing ? editTags : entry.tags || []).map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs group">
                      {tag}
                      {isEditing && (
                        <button
                          onClick={() => handleRemoveTag(tag)}
                          className="ml-1 text-muted-foreground hover:text-foreground"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      )}
                    </Badge>
                  ))}
                  {isEditing && (
                    <div className="flex items-center gap-1">
                      <input
                        type="text"
                        value={newTagInput}
                        onChange={(e) => setNewTagInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            handleAddTag();
                          }
                        }}
                        placeholder="添加标签"
                        className="text-xs border rounded px-1.5 py-0.5 w-20 bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                      <button
                        onClick={handleAddTag}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        <Plus className="h-3 w-3" />
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Parent Entry */}
              {parentEntry && (
                <div className="flex items-center gap-2 mt-3">
                  <Link2 className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">所属{categoryConfig[parentEntry.category]?.label || "条目"}:</span>
                  <button
                    onClick={() => navigate(`/entry/${parentEntry.id}`)}
                    className="text-sm text-primary hover:underline"
                  >
                    {parentEntry.title}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Decision/Reflection/Question Info Card */}
        {entry.category === "decision" && (
          <Card className="mb-6 border-amber-200 dark:border-amber-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2 text-amber-700 dark:text-amber-300">
                <Scale className="h-4 w-4" />
                决策记录
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              记录重要决策的背景、方案对比和选择理由，帮助未来回顾决策脉络。
            </CardContent>
          </Card>
        )}
        {entry.category === "reflection" && (
          <Card className="mb-6 border-teal-200 dark:border-teal-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2 text-teal-700 dark:text-teal-300">
                <RotateCcw className="h-4 w-4" />
                复盘笔记
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              结构化回顾目标、结果和经验教训，持续改进。
            </CardContent>
          </Card>
        )}
        {entry.category === "question" && (
          <Card className="mb-6 border-rose-200 dark:border-rose-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2 text-rose-700 dark:text-rose-300">
                <HelpCircle className="h-4 w-4" />
                待解疑问
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              记录待解决的问题和思考方向，积累待探索的知识点。
              {entry.status === "complete" && (
                <span className="ml-2 text-green-600 dark:text-green-400">已解决</span>
              )}
            </CardContent>
          </Card>
        )}

        {/* Project Progress Section */}
        {entry.category === "project" && projectProgress && (
          <Card className="mb-6">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                项目进度
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>完成进度</span>
                    <span>{projectProgress.progress_percentage}%</span>
                  </div>
                  <Progress value={projectProgress.progress_percentage} />
                </div>
                <div className="flex gap-4 text-sm text-muted-foreground">
                  <span>总任务: {projectProgress.total_tasks}</span>
                  <span>已完成: {projectProgress.completed_tasks}</span>
                </div>
                {Object.keys(projectProgress.status_distribution).length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(projectProgress.status_distribution).map(([status, count]) => (
                      <Badge key={status} variant="outline" className="text-xs">
                        {statusConfig[status as keyof typeof statusConfig]?.label || status}: {count}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Child Tasks Section */}
        {entry.category === "project" && childTasks.length > 0 && (
          <Card className="mb-6">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">子任务 ({childTasks.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <TaskList tasks={childTasks} emptyMessage="暂无子任务" />
            </CardContent>
          </Card>
        )}

        {/* Content — 预览/编辑 Tab 切换 */}
        {isEditing && (
          <div className="flex items-center gap-2 mb-3">
            <button
              onClick={() => setContentTab("preview")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                contentTab === "preview"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              <Eye className="h-4 w-4" />
              预览
            </button>
            <button
              onClick={() => setContentTab("edit")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                contentTab === "edit"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              <Code className="h-4 w-4" />
              编辑
            </button>
          </div>
        )}

        {isEditing && contentTab === "edit" ? (
          <div className="space-y-3">
            <Textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              placeholder="输入 Markdown 格式的内容..."
              className="min-h-[300px] md:min-h-[400px] font-mono text-sm w-full"
              disabled={isSaving}
            />
            <p className="text-xs text-muted-foreground">内容修改后 1 秒自动保存</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* 结构化类型渲染: decision/reflection/question */}
            {["decision", "reflection", "question"].includes(entry.category) &&
            !isEditing ? (
              <StructuredContent
                content={parsedContent}
                category={entry.category}
                navigate={navigate}
              />
            ) : (
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={getMarkdownComponents(navigate)}
                >
                  {(isEditing ? editContent : parsedContent) || "暂无内容"}
                </ReactMarkdown>
              </div>
            )}

            {/* 引用笔记列表 */}
            {referenceIds.length > 0 && (
              <Card className="mt-4">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    引用的笔记 ({referenceIds.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {referenceIds.map((noteId) => {
                      const note = referencedNotes.get(noteId);
                      return (
                        <div
                          key={noteId}
                          className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                          onClick={() => navigate(`/entry/${noteId}`)}
                        >
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm">{note?.title || noteId}</span>
                            {note && (
                              <Badge variant="outline" className="text-xs">
                                {categoryConfig[note.category]?.label || note.category}
                              </Badge>
                            )}
                          </div>
                          {note && (
                            <span className="text-xs text-muted-foreground">
                              {new Date(note.created_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* AI 摘要折叠卡片 — 仅非空内容且非编辑模式时显示 */}
        {!isEditing && entry.content && entry.content.trim().length > 0 && (
          <Card className="mt-6">
            <CardHeader
              className="pb-2 cursor-pointer select-none"
              onClick={handleToggleAiSummary}
            >
              <CardTitle className="text-base flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  AI 摘要
                </span>
                {aiSummaryExpanded ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </CardTitle>
            </CardHeader>
            {aiSummaryExpanded && (
              <CardContent>
                {aiSummaryLoading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    正在生成摘要...
                  </div>
                )}
                {aiSummaryError && !aiSummaryLoading && (
                  <div className="flex items-center justify-between py-2">
                    <div className="flex items-center gap-2 text-sm text-destructive">
                      <AlertCircle className="h-4 w-4" />
                      {aiSummaryError}
                    </div>
                    <Button variant="outline" size="sm" onClick={handleRetryAiSummary}>
                      <RefreshCw className="h-3 w-3 mr-1" />
                      重试
                    </Button>
                  </div>
                )}
                {aiSummaryData && !aiSummaryLoading && (
                  <div className="space-y-3">
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {aiSummaryData.summary}
                      </ReactMarkdown>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      {aiSummaryData.cached && (
                        <Badge variant="secondary" className="text-xs">已缓存</Badge>
                      )}
                      {aiSummaryData.generated_at && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(aiSummaryData.generated_at).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        )}

        {/* 知识上下文缩略图 — 可折叠卡片 */}
        {!isEditing && !knowledgeContextError && (
          <Card className="mt-6">
            <CardHeader
              className="pb-2 cursor-pointer select-none"
              onClick={() => setKnowledgeContextExpanded(!knowledgeContextExpanded)}
            >
              <CardTitle className="text-base flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  知识上下文
                </span>
                {knowledgeContextExpanded ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </CardTitle>
            </CardHeader>
            {knowledgeContextExpanded && (
              <CardContent>
                <KnowledgeGraphThumbnail
                  nodes={knowledgeContext?.nodes ?? []}
                  edges={knowledgeContext?.edges ?? []}
                  centerConcepts={knowledgeContext?.center_concepts ?? []}
                  loading={knowledgeContextLoading}
                />
                {knowledgeContext && knowledgeContext.nodes.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-2 text-center">
                    点击概念节点查看详情
                  </p>
                )}
              </CardContent>
            )}
          </Card>
        )}

        {/* 关联条目 — 手动关联 + 自动推荐 */}
        {!isEditing && (
          <Card className="mt-6">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Link2 className="h-4 w-4" />
                  关联条目
                </CardTitle>
                <Button variant="outline" size="sm" onClick={() => setShowLinkDialog(true)}>
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  添加关联
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {/* 手动关联 */}
              {entryLinks.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-medium text-muted-foreground mb-2">手动关联</p>
                  <div className="space-y-2">
                    {entryLinks.map((link) => (
                      <div
                        key={link.id}
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors group"
                      >
                        <div
                          className="flex items-center gap-2 flex-1 min-w-0 cursor-pointer"
                          onClick={() => navigate(`/entry/${link.target_id}`)}
                        >
                          <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="text-sm truncate">{link.target_entry.title}</span>
                          <Badge variant="outline" className="text-xs shrink-0">
                            {(categoryConfig as Record<string, { label: string }>)[link.target_entry.category]?.label || link.target_entry.category}
                          </Badge>
                          <Badge variant="secondary" className="text-xs shrink-0">
                            {link.relation_type === "related" ? "关联" :
                             link.relation_type === "depends_on" ? "依赖" :
                             link.relation_type === "derived_from" ? "来源" : "引用"}
                          </Badge>
                        </div>
                        <button
                          onClick={() => handleDeleteLink(link.id)}
                          disabled={deletingLinkId === link.id}
                          className="text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-2"
                          title="删除关联"
                        >
                          {deletingLinkId === link.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 自动推荐 */}
              {!relatedLoading && !relatedError && relatedEntries.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-2">自动推荐</p>
                  <div className="space-y-2">
                    {relatedEntries.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                        onClick={() => navigate(`/entries/${item.id}`)}
                      >
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">{item.title}</span>
                          <Badge variant="outline" className="text-xs">
                            {(categoryConfig as Record<string, { label: string }>)[item.category]?.label || item.category}
                          </Badge>
                        </div>
                        <span className="text-xs text-muted-foreground">{item.relevance_reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 空态 */}
              {entryLinks.length === 0 && relatedEntries.length === 0 && !relatedLoading && (
                <p className="text-sm text-muted-foreground py-2">
                  暂无关联条目，点击「添加关联」或添加更多标签自动发现关联
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* 添加关联弹窗 */}
        {showLinkDialog && id && (
          <LinkEntryDialog
            entryId={id}
            onClose={() => setShowLinkDialog(false)}
            onCreated={loadEntryLinks}
          />
        )}

        {/* 编辑助手 AI */}
        {!isEditing && entry && (
          <PageChatPanel
            title="编辑助手"
            welcomeMessage="需要帮忙整理内容吗？"
            suggestions={entry.category === "task" ? [
              { label: "拆解子任务", message: "帮我把这个任务拆解为可执行的子任务" },
              { label: "生成摘要", message: "帮我生成一段摘要" },
              { label: "整理内容", message: "帮我整理和优化这段内容" },
            ] : entry.category === "note" ? [
              { label: "整理笔记", message: "帮我把这段笔记整理一下" },
              { label: "提取要点", message: "帮我提取关键知识点" },
              { label: "关联知识", message: "帮我看看还有哪些相关知识" },
            ] : [
              { label: "整理内容", message: "帮我整理和优化这段内容" },
              { label: "生成摘要", message: "帮我生成一段摘要" },
              { label: "关联知识", message: "帮我看看还有哪些相关知识" },
            ]}
            pageContext={{ page: "entry_detail" }}
            pageData={{
              entry_title: entry.title,
              category: entry.category,
              tags: (entry.tags || []).join(", "),
              status: entry.status,
              priority: entry.priority ?? "",
              content_preview: (entry.content || "").slice(0, 500),
            }}
            className="mt-6"
            defaultCollapsed
          />
        )}
      </div>
    </div>
  );
}
