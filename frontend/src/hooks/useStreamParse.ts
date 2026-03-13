import { useState, useCallback } from "react";

const API_BASE = "/api";

interface Task {
  id: string;
  name: string;
  description?: string;
  category: "task" | "inbox" | "note" | "project";
  status: "waitStart" | "doing" | "complete";
  planned_date?: string;
}

interface ParseResult {
  tasks: Task[];
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
                  // 存储 AI 响应
                  options.onMessage?.("assistant", fullJson);
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
