import { useState, useCallback, useRef } from "react";
import { API_BASE } from "@/config/api";
import { authFetch } from "@/lib/authFetch";
import type { Intent } from "@/lib/intentDetection";
import type { PageContext } from "@/stores/chatStore";

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

// 确认项（多选场景）
export interface ConfirmItem {
  id: string;
  title: string;
}

// 确认事件数据
export interface ConfirmData {
  action: "update" | "delete";
  items: ConfirmItem[];
  entities?: Record<string, string>;
}

// 搜索结果项
export interface ResultItem {
  id: string;
  title: string;
  status?: string;
  category?: string;
}

// 操作结果
export interface OperationResult {
  created?: { ids: string[]; count: number };
  updated?: { id: string; title?: string; changes: Record<string, unknown> };
  deleted?: { id: string };
  confirm?: ConfirmData;
  results?: { items: ResultItem[]; count: number };
  message?: string;
}

// parse() 返回结果
export interface ParseResponse {
  intent: IntentResult;
  result?: ParseResult;
  operation?: OperationResult;
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
  // 新增：意图检测回调
  onIntentDetected?: (intent: IntentResult) => void;
  // 新增：操作结果回调
  onCreated?: (ids: string[], count: number) => void;
  onUpdated?: (id: string, title: string, changes: Record<string, unknown>) => void;
  onDeleted?: (id: string) => void;
  onConfirm?: (data: ConfirmData) => void;
  onResults?: (items: ResultItem[]) => void;
  // 预留：工具/Skill 调用回调
  onToolStart?: (name: string, params: Record<string, unknown>) => void;
  onToolEnd?: (name: string, result: Record<string, unknown>) => void;
}

// 确认请求参数
export interface ConfirmRequest {
  action: "update" | "delete";
  item_id: string;
}

/**
 * 流式解析 Hook（使用统一的 /chat 接口）
 *
 * 后端一站式处理意图检测和操作执行
 */
export function useStreamParse(options: UseStreamParseOptions = {}) {
  const [rawJson, setRawJson] = useState("");
  const [result, setResult] = useState<ParseResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [operation, setOperation] = useState<OperationResult | null>(null);

  // 使用 ref 存储稳定的回调，避免 useCallback 依赖频繁变化
  const optionsRef = useRef(options);
  optionsRef.current = options;

  // 用于取消进行中的 SSE 请求
  const abortControllerRef = useRef<AbortController | null>(null);

  // 组件卸载时取消进行中的请求
  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
  }, []);

  const parse = useCallback(
    async (text: string, sessionId: string = "default", confirm?: ConfirmRequest, pageContext?: PageContext | null): Promise<ParseResponse> => {
      if (!text.trim()) throw new Error("文本为空");

      // 取消之前的请求
      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;

      optionsRef.current.onMessage?.("user", text);
      setRawJson("");
      setResult(null);
      setError(null);
      setOperation(null);
      setIsLoading(true);

      return new Promise((resolve, reject) => {
        (async () => {
          try {
            const res = await authFetch(`${API_BASE}/chat`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                text,
                session_id: sessionId,
                confirm,
                page_context: pageContext || null,
              }),
              signal: controller.signal,
            });

            if (!res.ok) throw new Error(`HTTP error: ${res.status}`);

            const reader = res.body?.getReader();
            if (!reader) throw new Error("No response body");

            const decoder = new TextDecoder();
            let fullJson = "";
            let currentEvent = "";
            let intentResult: IntentResult | null = null;
            let operationResult: OperationResult | null = null;

            // SSE buffer 处理跨 chunk 的数据
            let buffer = "";

            while (true) {
              if (controller.signal.aborted) {
                reader.cancel();
                return;
              }
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
                      // 触发意图检测回调
                      optionsRef.current.onIntentDetected?.(intentResult);
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
                  } else if (currentEvent === "created") {
                    try {
                      const created = JSON.parse(data);
                      operationResult = { created };
                      setOperation(operationResult);
                      optionsRef.current.onCreated?.(created.ids, created.count);
                    } catch {
                      console.error("Created parse error:", data);
                    }
                  } else if (currentEvent === "updated") {
                    try {
                      const updated = JSON.parse(data);
                      operationResult = { updated };
                      setOperation(operationResult);
                      optionsRef.current.onUpdated?.(updated.id, updated.title, updated.changes);
                      optionsRef.current.onMessage?.("assistant", `已更新「${updated.title || updated.id}」`);
                    } catch {
                      console.error("Updated parse error:", data);
                    }
                  } else if (currentEvent === "deleted") {
                    try {
                      const deleted = JSON.parse(data);
                      operationResult = { deleted };
                      setOperation(operationResult);
                      optionsRef.current.onDeleted?.(deleted.id);
                      optionsRef.current.onMessage?.("assistant", "已删除");
                    } catch {
                      console.error("Deleted parse error:", data);
                    }
                  } else if (currentEvent === "confirm") {
                    try {
                      const confirmData: ConfirmData = JSON.parse(data);
                      operationResult = { confirm: confirmData };
                      setOperation(operationResult);
                      optionsRef.current.onConfirm?.(confirmData);
                    } catch {
                      console.error("Confirm parse error:", data);
                    }
                  } else if (currentEvent === "results") {
                    try {
                      const results = JSON.parse(data);
                      operationResult = { results };
                      setOperation(operationResult);
                      optionsRef.current.onResults?.(results.items);
                    } catch {
                      console.error("Results parse error:", data);
                    }
                  } else if (currentEvent === "done") {
                    try {
                      const doneData = JSON.parse(data);
                      if (doneData.message) {
                        optionsRef.current.onMessage?.("assistant", doneData.message);
                      }
                    } catch {
                      // 忽略解析错误
                    }
                    setIsLoading(false);
                    resolve({
                      intent: intentResult!,
                      result: result || undefined,
                      operation: operationResult || undefined,
                    });
                    return;
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
                    // create 意图完成（旧格式兼容）
                    let parsedResult: ParseResult | undefined = undefined;
                    if (fullJson) {
                      try {
                        const parsed = JSON.parse(fullJson) as ParseResult;
                        parsedResult = parsed;
                        setResult(parsed);
                        optionsRef.current.onComplete?.(parsed);
                        optionsRef.current.onMessage?.("assistant", formatParsedResult(parsed));
                      } catch (e) {
                        console.error("JSON parse error:", e);
                        const err = new Error("JSON 解析失败");
                        setError(err);
                        optionsRef.current.onError?.(err);
                      }
                    }
                    setIsLoading(false);
                    resolve({
                      intent: intentResult!,
                      result: parsedResult,
                      operation: operationResult || undefined,
                    });
                    return;
                  }
                }
              }
            }

            setIsLoading(false);
            if (intentResult) {
              resolve({ intent: intentResult, operation: operationResult || undefined });
            } else {
              reject(new Error("未收到意图检测结果"));
            }
          } catch (err) {
            // 请求被取消时不更新状态
            if (err instanceof DOMException && err.name === "AbortError") {
              return;
            }
            if (controller.signal.aborted) {
              return;
            }
            const error = err instanceof Error ? err : new Error(String(err));
            setError(error);
            setIsLoading(false);
            optionsRef.current.onError?.(error);
            reject(error);
          }
        })();
      });
    },
    [result]
  );

  const reset = useCallback(() => {
    setRawJson("");
    setResult(null);
    setError(null);
    setOperation(null);
    setIsLoading(false);
  }, []);

  return {
    rawJson,
    result,
    operation,
    isLoading,
    error,
    parse,
    reset,
    abort,
  };
}
