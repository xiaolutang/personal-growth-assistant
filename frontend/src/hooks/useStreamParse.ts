import { useState, useCallback } from "react";
import { API_BASE } from "@/config/api";

// 解析后的任务结构（与后端 ParsedTaskInput 对应）
interface ParsedTask {
  id?: string;
  title?: string;
  content?: string;
  category: "task" | "inbox" | "note" | "project";
  status: "waitStart" | "doing" | "complete";
  tags?: string[];
  planned_date?: string;
}

interface ParseResult {
  tasks: ParsedTask[];
}

// 类型和状态的中文映射
const categoryLabels: Record<string, string> = {
  task: "任务",
  inbox: "灵感",
  note: "笔记",
  project: "项目",
};

const statusLabels: Record<string, string> = {
  waitStart: "待开始",
  doing: "进行中",
  complete: "已完成",
};

// 格式化解析结果为可读文本
function formatParsedResult(result: ParseResult): string {
  if (result.tasks.length === 0) {
    return "未识别到有效内容";
  }

  const lines = result.tasks.map((task, index) => {
    const categoryLabel = categoryLabels[task.category] || task.category;
    const statusLabel = statusLabels[task.status] || task.status;
    const tags = task.tags?.length ? ` [${task.tags.join(", ")}]` : "";
    const date = task.planned_date
      ? ` 📅 ${new Date(task.planned_date).toLocaleString("zh-CN")}`
      : "";

    return `${index + 1}. [${categoryLabel}] ${task.title}${tags}${date}\n   状态: ${statusLabel}`;
  });

  return `✅ 已识别 ${result.tasks.length} 个条目：\n\n${lines.join("\n\n")}`;
}

interface UseStreamParseOptions {
  onComplete?: (result: ParseResult) => void;
  onError?: (error: Error) => void;
  onMessage?: (role: "user" | "assistant", content: string) => void;
}

/**
 * 流式解析 Hook
 *
 * 使用方式：
 * const { rawJson, result, isLoading, parse, error } = useStreamParse();
 *
 * await parse("明天下午3点开会");
 */
export function useStreamParse(options: UseStreamParseOptions = {}) {
  const [rawJson, setRawJson] = useState(""); // 流式累积的 JSON 字符串
  const [result, setResult] = useState<ParseResult | null>(null); // 解析后的结果
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const parse = useCallback(
    async (text: string, sessionId: string = "default") => {
      if (!text.trim()) return;

      // 存储用户消息
      options.onMessage?.("user", text);

      setRawJson("");
      setResult(null);
      setError(null);
      setIsLoading(true);

      try {
        const res = await fetch(`${API_BASE}/parse`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, session_id: sessionId }),
        });

        if (!res.ok) {
          throw new Error(`HTTP error: ${res.status}`);
        }

        const reader = res.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let fullJson = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6).trim();

              if (data === "[DONE]") {
                // 流结束，解析完整 JSON
                try {
                  const parsed: ParseResult = JSON.parse(fullJson);
                  setResult(parsed);
                  options.onComplete?.(parsed);
                  // 生成可读的 AI 响应
                  const readableResponse = formatParsedResult(parsed);
                  options.onMessage?.("assistant", readableResponse);
                } catch (e) {
                  console.error("JSON parse error:", e);
                  setError(new Error("JSON 解析失败"));
                }
                setIsLoading(false);
                return;
              }

              try {
                const json = JSON.parse(data);
                if (json.content) {
                  fullJson += json.content;
                  setRawJson(fullJson); // 实时显示累积的 JSON
                }
              } catch {
                // 忽略解析错误（可能是不完整的 JSON）
              }
            }
          }
        }

        setIsLoading(false);
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        setIsLoading(false);
        options.onError?.(error);
      }
    },
    [options]
  );

  const reset = useCallback(() => {
    setRawJson("");
    setResult(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    rawJson, // 流式累积的 JSON 字符串（用于显示过程）
    result, // 解析后的结构化结果
    isLoading,
    error,
    parse,
    reset,
  };
}
