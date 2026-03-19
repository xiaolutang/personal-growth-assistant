import { useState } from "react";
import { Send, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useStreamParse } from "@/hooks/useStreamParse";
import { useTaskStore } from "@/stores/taskStore";

export function ChatBox() {
  const [input, setInput] = useState("");
  const { rawJson, result, isLoading, error, parse, reset } = useStreamParse({
    onComplete: (data) => {
      // 解析完成后，将任务添加到 store
      if (data.tasks.length > 0) {
        addTasks(
          data.tasks.map((task) => ({
            type: task.category,
            title: task.title || "",
            content: task.content || "",
            category: task.category,
            status: task.status,
            tags: task.tags || [],
          }))
        );
      }
    },
  });
  const addTasks = useTaskStore((state) => state.addTasks);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    await parse(input.trim());
  };

  const handleReset = () => {
    reset();
    setInput("");
  };

  return (
    <div className="space-y-4">
      {/* 输入框 */}
      <form onSubmit={handleSubmit} className="space-y-2">
        <div className="flex gap-2">
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
        </div>
        {error && <p className="text-sm text-destructive">{error.message}</p>}
      </form>

      {/* 流式响应区域 */}
      {(rawJson || isLoading) && (
        <div className="rounded-lg border bg-muted/50 p-4">
          <div className="flex items-start gap-2">
            <Sparkles className="h-4 w-4 mt-1 text-muted-foreground" />
            <div className="flex-1 min-h-[60px]">
              {/* 显示流式 JSON（调试用） */}
              {isLoading && (
                <p className="text-xs text-muted-foreground mb-2">
                  正在解析...
                </p>
              )}
              <pre className="text-sm whitespace-pre-wrap leading-relaxed overflow-auto max-h-40">
                {rawJson}
                {/* 打字光标 */}
                {isLoading && (
                  <span className="inline-block w-2 h-4 ml-0.5 bg-primary animate-pulse" />
                )}
              </pre>

              {/* 解析结果 */}
              {result && result.tasks.length > 0 && (
                <div className="mt-3 pt-3 border-t">
                  <p className="text-sm font-medium mb-2">
                    识别到 {result.tasks.length} 个任务：
                  </p>
                  <ul className="text-sm space-y-1">
                    {result.tasks.map((task, index) => (
                      <li key={index} className="flex items-center gap-2">
                        <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">
                          {task.category}
                        </span>
                        <span>{task.title}</span>
                        {task.planned_date && (
                          <span className="text-xs text-muted-foreground">
                            {task.planned_date}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* 操作按钮 */}
          {!isLoading && rawJson && (
            <div className="flex justify-end mt-3 pt-3 border-t">
              <Button variant="outline" size="sm" onClick={handleReset}>
                清空
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
