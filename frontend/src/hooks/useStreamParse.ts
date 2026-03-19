import { useState, useCallback, useRef } from "react";
import { API_BASE } from "@/config/api";
import type { Intent } from "@/lib/intentDetection";

// 解析后的任务结构
export interface ParsedTask {
  id?: string;
  title?: string;
  content?: string;
  category: "task" | "inbox" | "note" | "project";
  status: "waitStart" | "doing" | "complete";
  tags?: string[];
  planned_date?: string;
}

export interface ParseResult {
  tasks: ParsedTask[];
}

// 意图检测结果
export interface IntentResult {
  intent: Intent;
  confidence: number;
  query: string;
  entities: Record<string, string>;
}

// parse() 返回结果
export interface ParseResponse {
  intent: IntentResult;
  result?: ParseResult;
}

// 标签映射常量
export const CATEGORY_LABELS: Record<string, string> = {
  task: "任务",
  inbox: "灵感",
  note: "笔记",
  project: "项目",
};

export const STATUS_LABELS: Record<string, string> = {
  waitStart: "待开始",
  doing: "进行中",
  complete: "已完成",
};

// 格式化解析结果
function formatParsedResult(result: ParseResult): string {
  if (result.tasks.length === 0) return "未识别到有效内容";

  const lines = result.tasks.map((task, index) => {
    const categoryLabel = CATEGORY_LABELS[task.category] || task.category;
    const statusLabel = STATUS_LABELS[task.status] || task.status;
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
 * 流式解析 Hook（使用统一的 /chat 接口）
 *
 * 后端统一处理意图检测，返回 Promise<ParseResponse>
 */
export function useStreamParse(options: UseStreamParseOptions = {}) {
  const [rawJson, setRawJson] = useState("");
  const [result, setResult] = useState<ParseResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // 使用 ref 存储稳定的回调，避免 useCallback 依赖频繁变化
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const parse = useCallback(
    async (text: string, sessionId: string = "default"): Promise<ParseResponse> => {
      if (!text.trim()) throw new Error("文本为空");

      optionsRef.current.onMessage?.("user", text);
      setRawJson("");
      setResult(null);
      setError(null);
      setIsLoading(true);

      return new Promise((resolve, reject) => {
            (async () => {
              try {
                const res = await fetch(`${API_BASE}/chat`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ text, session_id: sessionId }),
                });

                if (!res.ok) throw new Error(`HTTP error: ${res.status}`);

                const reader = res.body?.getReader();
                if (!reader) throw new Error("No response body");

                const decoder = new TextDecoder();
                let fullJson = "";
                let currentEvent = "";
                let intentResult: IntentResult | null = null;

                // SSE buffer 处理跨 chunk 的数据
                let buffer = "";

                while (true) {
                  const { done, value } = await reader.read();
                  if (done) break;

                  buffer += decoder.decode(value, { stream: true });
                  const lines = buffer.split("\n");
                  // 保留最后一个不完整的行
                  buffer = lines.pop() || "";

                  for (const line of lines) {
                    if (line.startsWith("event: ")) {
                      currentEvent = line.slice(7).trim();
                    } else if (line.startsWith("data: ")) {
                      const data = line.slice(6).trim();

                      if (currentEvent === "intent") {
                        try {
                          intentResult = JSON.parse(data) as IntentResult;
                        } catch {
                          console.error("Intent parse error:", data);
                        }
                      } else if (currentEvent === "content") {
                        try {
                          const json = JSON.parse(data);
                          if (json.content) {
                            fullJson += json.content;
                            setRawJson(fullJson);
                          }
                        } catch {
                          // 忽略解析错误
                        }
                      } else if (currentEvent === "done") {
                        // 非 create 意图完成
                        if (intentResult && intentResult.intent !== "create") {
                          setIsLoading(false);
                          resolve({ intent: intentResult });
                          return;
                        }
                      } else if (currentEvent === "error") {
                        let errorMsg = "未知错误";
                        try {
                          const errorData = JSON.parse(data);
                          errorMsg = errorData.message || errorMsg;
                        } catch {
                          errorMsg = data;
                        }
                        const err = new Error(errorMsg);
                        setError(err);
                        setIsLoading(false);
                        optionsRef.current.onError?.(err);
                        reject(err);
                        return;
                      } else if (data === "[DONE]") {
                        // create 意图完成
                        let parsedResult: ParseResult | undefined;
                        if (fullJson) {
                          try {
                            parsedResult = JSON.parse(fullJson);
                            setResult(parsedResult);
                            optionsRef.current.onComplete?.(parsedResult);
                            optionsRef.current.onMessage?.("assistant", formatParsedResult(parsedResult));
                          } catch (e) {
                            console.error("JSON parse error:", e);
                            const err = new Error("JSON 解析失败");
                            setError(err);
                            optionsRef.current.onError?.(err);
                          }
                        }
                        setIsLoading(false);
                        if (intentResult) {
                          resolve({ intent: intentResult, result: parsedResult });
                        } else {
                          reject(new Error("未收到意图检测结果"));
                        }
                        return;
                      }
                    }
                  }
                }

                setIsLoading(false);
                if (intentResult) {
                  resolve({ intent: intentResult });
                } else {
                  reject(new Error("未收到意图检测结果"));
                }
              } catch (err) {
                const error = err instanceof Error ? err : new Error(String(err));
                setError(error);
                setIsLoading(false);
                optionsRef.current.onError?.(error);
                reject(error);
              }
            })();
          });
        },
        [] // 空依赖，使用 ref 存储回调
      );

  const reset = useCallback(() => {
    setRawJson("");
    setResult(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    rawJson,
    result,
    isLoading,
    error,
    parse,
    reset,
  };
}
