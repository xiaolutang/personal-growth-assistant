import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Loader2,
  Calendar,
  Clock,
  Tag,
  Edit2,
  Save,
  X,
  Plus,
  Link2,
  Download,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { statusConfig, categoryConfig, priorityConfig } from "@/config/constants";
import type { Task, TaskStatus, Priority } from "@/types/task";
import { getDueDateInfo } from "@/lib/dueDate";

interface EntryHeaderProps {
  entry: Task;
  isEditing: boolean;
  isSaving: boolean;
  isExporting: boolean;
  editTitle: string;
  editStatus: TaskStatus;
  editPriority: Priority;
  editPlannedDate: string;
  editTags: string[];
  newTagInput: string;
  saveError: string | null;
  parentEntry: Task | null;
  onNavigateBack: () => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveAll: () => void;
  onExport: () => void;
  setEditTitle: (v: string) => void;
  setEditStatus: (v: TaskStatus) => void;
  setEditPriority: (v: Priority) => void;
  setEditPlannedDate: (v: string) => void;
  setNewTagInput: (v: string) => void;
  handleAddTag: () => void;
  handleRemoveTag: (tag: string) => void;
}

const renderStatusIcon = (status: TaskStatus) => {
  switch (status) {
    case "complete": return <span className="text-green-500 dark:text-green-400">✓</span>;
    case "doing": return <span className="text-yellow-500 dark:text-yellow-400">○</span>;
    case "paused": return <span className="text-orange-500 dark:text-orange-400">⏸</span>;
    case "cancelled": return <span className="text-red-500 dark:text-red-400">✕</span>;
    default: return <span>○</span>;
  }
};

export function EntryHeader({
  entry,
  isEditing,
  isSaving,
  isExporting,
  editTitle,
  editStatus,
  editPriority,
  editPlannedDate,
  editTags,
  newTagInput,
  saveError,
  parentEntry,
  onNavigateBack,
  onStartEdit,
  onCancelEdit,
  onSaveAll,
  onExport,
  setEditTitle,
  setEditStatus,
  setEditPriority,
  setEditPlannedDate,
  setNewTagInput,
  handleAddTag,
  handleRemoveTag,
}: EntryHeaderProps) {
  const navigate = useNavigate();
  const statusInfo = statusConfig[entry.status];
  const categoryInfo = categoryConfig[entry.category];
  const CategoryIcon = categoryInfo.icon;

  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="ghost" size="sm" onClick={onNavigateBack}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          返回
        </Button>
        {!isEditing && (
          <Button variant="outline" size="sm" disabled={isExporting} onClick={onExport}>
            {isExporting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            导出
          </Button>
        )}
        {!isEditing ? (
          <Button variant="outline" size="sm" onClick={onStartEdit}>
            <Edit2 className="h-4 w-4 mr-2" />
            编辑
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button size="sm" onClick={onSaveAll} disabled={isSaving}>
              {isSaving ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" />保存中...</>
              ) : (
                <><Save className="h-4 w-4 mr-2" />保存</>
              )}
            </Button>
            <Button variant="outline" size="sm" onClick={onCancelEdit} disabled={isSaving}>
              <X className="h-4 w-4 mr-2" />
              取消
            </Button>
          </div>
        )}
      </div>

      {saveError && (
        <div className="flex items-center gap-2 mb-4 p-2 rounded-lg bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 text-sm">
          <span className="text-red-500">⚠</span>
          {saveError}
        </div>
      )}

      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 mt-1">
          <CategoryIcon className="h-6 w-6 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
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
            <Badge variant="secondary">{categoryInfo.label}</Badge>

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

            {isEditing ? (
              <select
                value={editPriority}
                onChange={(e) => setEditPriority(e.target.value as "low" | "medium" | "high")}
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

            {isEditing ? (
              <div className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                <input
                  type="date"
                  value={editPlannedDate}
                  onChange={(e) => setEditPlannedDate(e.target.value)}
                  className="text-sm border rounded px-1.5 py-0.5 bg-background"
                />
                {editPlannedDate && (
                  <button
                    type="button"
                    onClick={() => setEditPlannedDate("")}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                    aria-label="清除日期"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            ) : (
              entry.planned_date && (() => {
                const due = getDueDateInfo(entry.planned_date);
                return (
                  <div className={`flex items-center gap-1 ${
                    due.status === "overdue" ? "text-red-500 dark:text-red-400" :
                    due.status === "today" ? "text-amber-500 dark:text-amber-400" :
                    ""
                  }`}>
                    {due.status === "overdue" ? (
                      <AlertTriangle className="h-4 w-4" />
                    ) : (
                      <Calendar className="h-4 w-4" />
                    )}
                    <span>
                      {due.label}
                    </span>
                  </div>
                );
              })()
            )}

            {entry.created_at && (
              <div className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                <span>创建于 {new Date(entry.created_at).toLocaleDateString()}</span>
              </div>
            )}

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
                  <button onClick={handleAddTag} className="text-muted-foreground hover:text-foreground">
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
                onClick={() => navigate(`/entries/${parentEntry.id}`)}
                className="text-sm text-primary hover:underline"
              >
                {parentEntry.title}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
