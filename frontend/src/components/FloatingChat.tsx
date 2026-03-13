import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  Loader2,
  Plus,
  MessageSquare,
  Trash2,
  ChevronDown,
  GripHorizontal,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useStreamParse } from "@/hooks/useStreamParse";
import { useTaskStore } from "@/stores/taskStore";
import { useChatStore } from "@/stores/chatStore";

// 最小和最大面板高度
const MIN_HEIGHT = 200;
const MAX_HEIGHT = 600;

export function FloatingChat() {
  const [input, setInput] = useState("");
  const [showSessionList, setShowSessionList] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const {
    sessions,
    currentSessionId,
    createSession,
    deleteSession,
    switchSession,
    addMessage,
    getCurrentSession,
    updateSessionTitle,
    panelHeight,
    setPanelHeight,
  } = useChatStore();

  const currentSession = getCurrentSession();
  const { addTasks } = useTaskStore();

  const { rawJson, result, isLoading, error, parse, reset } = useStreamParse({
    onComplete: (data) => {
      if (data.tasks.length > 0) {
        addTasks(
          data.tasks.map((task) => ({
            name: task.name,
            description: task.description,
            category: task.category,
            status: task.status,
            planned_date: task.planned_date,
          }))
        );
        // 更新会话标题（使用第一个任务名称）
        if (currentSession && currentSession.title === "新对话") {
          updateSessionTitle(
            currentSession.id,
            data.tasks[0].name.slice(0, 20)
          );
        }
      }
    },
    onMessage: (role, content) => {
      if (currentSessionId) {
        addMessage(currentSessionId, { role, content });
      }
    },
  });

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentSession?.messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    // 如果没有当前会话，创建一个
    let sessionId = currentSessionId;
    if (!sessionId) {
      sessionId = createSession();
    }

    await parse(input.trim(), sessionId || undefined);
    setInput("");
  };

  const handleNewSession = () => {
    createSession();
    reset();
  };

  const handleSwitchSession = (id: string) => {
    switchSession(id);
    reset();
  };

  // 拖拽调整高度
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      // 从底部计算高度
      const newHeight = window.innerHeight - e.clientY;
      setPanelHeight(Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, newHeight)));
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging]);

  return (
    <div
      className={`fixed bottom-0 left-64 right-0 bg-background border-t z-50 flex flex-col ${
        isDragging ? "select-none" : ""
      }`}
      style={{ height: panelHeight }}
    >
      {/* 拖拽条 */}
      <div
        className="flex items-center justify-center h-6 cursor-ns-resize hover:bg-muted/50 border-b shrink-0"
        onMouseDown={handleMouseDown}
      >
        <GripHorizontal className="h-4 w-4 text-muted-foreground" />
      </div>

      {/* 会话列表区域 - 可折叠 */}
      <div className="border-b bg-muted/30 shrink-0">
        {/* 当前会话行（始终显示） */}
        <div
          className="flex items-center justify-between p-2 cursor-pointer hover:bg-muted/50"
          onClick={() => setShowSessionList(!showSessionList)}
        >
          <div className="flex items-center gap-2">
            {showSessionList ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <MessageSquare className="h-4 w-4" />
            <span className="text-sm font-medium truncate">
              {currentSession?.title || "新对话"}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleNewSession();
            }}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {/* 展开的会话列表 */}
        {showSessionList && (
          <div className="max-h-32 overflow-y-auto border-t">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`flex items-center justify-between px-4 py-1.5 cursor-pointer hover:bg-muted ${
                  session.id === currentSessionId ? "bg-muted" : ""
                }`}
                onClick={() => {
                  handleSwitchSession(session.id);
                  setShowSessionList(false);
                }}
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <MessageSquare className="h-3 w-3 shrink-0 text-muted-foreground" />
                  <span className="truncate text-sm">{session.title}</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5 shrink-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteSession(session.id);
                  }}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
            {sessions.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-2">
                暂无对话
              </p>
            )}
          </div>
        )}
      </div>

      {/* 历史消息区域 - 可滚动 */}
      {currentSession && currentSession.messages.length > 0 && (
        <div
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto p-3 border-b bg-muted/20 min-h-0"
        >
          {currentSession.messages.map((msg) => (
            <div
              key={msg.id}
              className={`mb-2 ${
                msg.role === "user" ? "text-right" : "text-left"
              }`}
            >
              <span
                className={`inline-block px-3 py-1.5 rounded-lg text-sm max-w-[80%] whitespace-pre-wrap break-words ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                {msg.content}
              </span>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* 输入区域 */}
      <div className="p-3 shrink-0">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入任务... (如: 明天下午3点开会)"
            className="flex-1"
            disabled={isLoading}
          />
          <Button type="submit" disabled={!input.trim() || isLoading}>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>

        {/* 错误提示 */}
        {error && (
          <p className="text-sm text-destructive mt-2">{error.message}</p>
        )}

        {/* 当前解析结果预览 */}
        {result && result.tasks.length > 0 && (
          <div className="mt-2 text-sm text-muted-foreground">
            已识别 {result.tasks.length} 个任务
          </div>
        )}
      </div>
    </div>
  );
}
