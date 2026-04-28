import { useState, useRef, useEffect } from "react";
import { MessageSquare, Plus, Trash2, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAgentStore } from "@/stores/agentStore";
import { cn } from "@/lib/utils";

interface SessionListProps {
  compact?: boolean;
  showTitle?: boolean;
  maxHeight?: string;
}

// 格式化相对时间
function formatRelativeTime(timestamp: number): string {
  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}小时前`;
  if (minutes < 10080) return `${Math.floor(minutes / 1440)}天前`;
  return new Date(timestamp).toLocaleDateString();
}

export function SessionList({
  compact = false,
  showTitle = true,
  maxHeight = "320px",
}: SessionListProps) {
  // 使用选择器避免过度订阅
  const sessions = useAgentStore((state) => state.sessions);
  const currentSessionId = useAgentStore((state) => state.currentSessionId);
  const createSession = useAgentStore((state) => state.createSession);
  const deleteSession = useAgentStore((state) => state.deleteSession);
  const switchSession = useAgentStore((state) => state.switchSession);
  const updateSessionTitle = useAgentStore((state) => state.updateSessionTitle);

  // 编辑状态
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // 自动聚焦编辑输入框
  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  // 开始编辑
  const handleStartEdit = (id: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(id);
    setEditingTitle(currentTitle);
  };

  // 确认编辑
  const handleConfirmEdit = (id: string) => {
    const trimmedTitle = editingTitle.trim();
    if (trimmedTitle) {
      updateSessionTitle(id, trimmedTitle);
    }
    setEditingId(null);
    setEditingTitle("");
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setEditingId(null);
    setEditingTitle("");
  };

  // 键盘事件处理
  const handleKeyDown = (e: React.KeyboardEvent, id: string) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleConfirmEdit(id);
    } else if (e.key === "Escape") {
      e.preventDefault();
      handleCancelEdit();
    }
  };

  const handleDeleteSession = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const session = sessions.find((s) => s.id === id);
    if (window.confirm(`确定删除对话「${session?.title || "新对话"}」吗？`)) {
      deleteSession(id);
    }
  };

  return (
    <div className="flex flex-col" style={{ maxHeight }}>
      {/* 标题区域 */}
      {showTitle && (
        <div className="flex items-center justify-between px-3 py-2 border-b">
          <span className="text-sm font-medium">会话列表</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={createSession}
            className="h-7 gap-1"
          >
            <Plus className="h-3.5 w-3.5" />
            新对话
          </Button>
        </div>
      )}

      {/* 新建按钮 (紧凑模式) - 使用虚线边框区分 */}
      {compact && (
        <button
          onClick={createSession}
          className="flex items-center gap-2 mx-3 my-2 px-3 py-2 text-sm text-muted-foreground border-2 border-dashed border-muted-foreground/30 rounded-lg hover:border-primary hover:text-primary hover:bg-primary/5 transition-colors"
        >
          <Plus className="h-4 w-4" />
          <span>新建对话</span>
        </button>
      )}

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            暂无对话记录
          </p>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => !editingId && switchSession(session.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 cursor-pointer transition-colors group",
                "hover:bg-accent",
                session.id === currentSessionId &&
                  "bg-primary/10 text-primary font-medium"
              )}
            >
              <MessageSquare className="h-4 w-4 shrink-0" />
              <div className="flex-1 min-w-0">
                {editingId === session.id ? (
                  <Input
                    ref={inputRef}
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onBlur={() => handleConfirmEdit(session.id)}
                    onKeyDown={(e) => handleKeyDown(e, session.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="h-6 text-sm px-1"
                    maxLength={30}
                  />
                ) : (
                  <>
                    <div className="truncate text-sm">{session.title}</div>
                    {!compact && (
                      <div className="text-xs text-muted-foreground">
                        {formatRelativeTime(session.updatedAt)}
                      </div>
                    )}
                  </>
                )}
              </div>
              {/* 操作按钮组 */}
              {editingId !== session.id && (
                <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 hover:text-primary"
                    onClick={(e) => handleStartEdit(session.id, session.title, e)}
                    title="编辑标题"
                  >
                    <Pencil className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 hover:text-destructive"
                    onClick={(e) => handleDeleteSession(session.id, e)}
                    title="删除对话"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
