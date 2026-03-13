import { useState, useRef, useEffect } from "react";
import {
  Send,
  Loader2,
  Plus,
  MessageSquare,
  Trash2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useStreamParse } from "@/hooks/useStreamParse";
import { useTaskStore } from "@/stores/taskStore";
import { useChatStore } from "@/stores/chatStore";

export function FloatingChat() {
  const [input, setInput] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    sessions,
    currentSessionId,
    createSession,
    deleteSession,
    switchSession,
    addMessage,
    getCurrentSession,
    updateSessionTitle,
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

  return (
    <div className="fixed bottom-0 left-64 right-0 bg-background border-t z-50">
      {/* 会话列表（展开时显示） */}
      {isExpanded && (
        <div className="border-b bg-muted/30 max-h-60 overflow-y-auto">
          <div className="flex items-center justify-between p-2 border-b">
            <span className="text-sm font-medium">会话历史</span>
            <Button variant="ghost" size="sm" onClick={handleNewSession}>
              <Plus className="h-4 w-4 mr-1" />
              新对话
            </Button>
          </div>
          <div className="p-2 space-y-1">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`flex items-center justify-between p-2 rounded cursor-pointer hover:bg-muted ${
                  session.id === currentSessionId ? "bg-muted" : ""
                }`}
                onClick={() => handleSwitchSession(session.id)}
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <MessageSquare className="h-4 w-4 shrink-0" />
                  <span className="truncate text-sm">{session.title}</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 shrink-0"
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
              <p className="text-sm text-muted-foreground text-center py-4">
                暂无对话，开始新对话吧
              </p>
            )}
          </div>
        </div>
      )}

      {/* 历史消息区域 */}
      {currentSession && currentSession.messages.length > 0 && (
        <div className="max-h-40 overflow-y-auto p-3 border-b bg-muted/20">
          {currentSession.messages.map((msg) => (
            <div
              key={msg.id}
              className={`mb-2 ${
                msg.role === "user" ? "text-right" : "text-left"
              }`}
            >
              <span
                className={`inline-block px-3 py-1.5 rounded-lg text-sm max-w-[80%] ${
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
      <div className="p-3">
        <div className="flex items-center gap-2">
          {/* 展开/收起按钮 */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? "收起会话列表" : "展开会话列表"}
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronUp className="h-4 w-4" />
            )}
          </Button>

          {/* 输入框 */}
          <form onSubmit={handleSubmit} className="flex-1 flex gap-2">
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
        </div>

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
