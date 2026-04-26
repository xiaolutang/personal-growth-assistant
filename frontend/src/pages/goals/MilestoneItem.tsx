import { useState, useRef, useEffect } from "react";
import { CheckSquare, Square, Trash2, Calendar, Pencil } from "lucide-react";
import { toast } from "sonner";
import type { Milestone } from "@/services/api";

interface MilestoneItemProps {
  milestone: Milestone;
  onToggle: (id: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onTitleChange: (id: string, title: string) => Promise<void>;
}

export function MilestoneItem({ milestone, onToggle, onDelete, onTitleChange }: MilestoneItemProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(milestone.title);
  const [deleting, setDeleting] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) inputRef.current.focus();
  }, [editing]);

  const handleToggle = async () => {
    setToggling(true);
    try {
      await onToggle(milestone.id);
    } finally {
      setToggling(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("确定要删除此里程碑吗？")) return;
    setDeleting(true);
    try {
      await onDelete(milestone.id);
    } finally {
      setDeleting(false);
    }
  };

  const handleSaveTitle = async () => {
    const trimmed = draft.trim();
    if (!trimmed) {
      setDraft(milestone.title);
      setEditing(false);
      return;
    }
    if (trimmed === milestone.title) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onTitleChange(milestone.id, trimmed);
      setEditing(false);
    } catch {
      toast.error("更新标题失败");
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSaveTitle();
    if (e.key === "Escape") { setDraft(milestone.title); setEditing(false); }
  };

  const isCompleted = milestone.status === "completed";
  const isDisabled = toggling || deleting || saving;

  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${isCompleted ? "bg-muted/40" : "hover:bg-accent/50"}`}>
      {/* 复选框 */}
      <button
        className="shrink-0 disabled:opacity-50"
        onClick={handleToggle}
        disabled={isDisabled}
        title={isCompleted ? "标记为未完成" : "标记为已完成"}
      >
        {isCompleted ? (
          <CheckSquare className="h-5 w-5 text-primary" />
        ) : (
          <Square className="h-5 w-5 text-muted-foreground" />
        )}
      </button>

      {/* 标题（可内联编辑） */}
      <div className="flex-1 min-w-0">
        {editing ? (
          <input
            ref={inputRef}
            className="w-full text-sm border-b border-primary bg-transparent outline-none px-0.5 py-0.5"
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onBlur={handleSaveTitle}
            onKeyDown={handleKeyDown}
            disabled={saving}
          />
        ) : (
          <span
            className={`text-sm cursor-pointer ${isCompleted ? "line-through text-muted-foreground" : ""}`}
            onDoubleClick={() => setEditing(true)}
            title="双击编辑标题"
          >
            {milestone.title}
          </span>
        )}
      </div>

      {/* 截止日期 */}
      {milestone.due_date && (
        <span className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
          <Calendar className="h-3.5 w-3.5" />
          {milestone.due_date}
        </span>
      )}

      {/* 编辑按钮 */}
      {!editing && (
        <button
          className="shrink-0 text-muted-foreground hover:text-foreground p-1"
          onClick={() => { setDraft(milestone.title); setEditing(true); }}
          title="编辑标题"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
      )}

      {/* 删除按钮 */}
      <button
        className="shrink-0 text-muted-foreground hover:text-destructive p-1 disabled:opacity-50"
        onClick={handleDelete}
        disabled={isDisabled}
        title="删除里程碑"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
