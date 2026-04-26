import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import { generateEntrySummary } from "@/services/api";
import type { EntrySummaryResponse } from "@/services/api";

export interface AiSummaryState {
  aiSummaryExpanded: boolean;
  aiSummaryData: EntrySummaryResponse | null;
  aiSummaryLoading: boolean;
  aiSummaryError: string | null;
  handleToggleAiSummary: () => void;
  handleRetryAiSummary: () => void;
}

export function useAiSummary(): AiSummaryState {
  const { id } = useParams<{ id: string }>();
  const [aiSummaryExpanded, setAiSummaryExpanded] = useState(false);
  const [aiSummaryData, setAiSummaryData] = useState<EntrySummaryResponse | null>(null);
  const [aiSummaryLoading, setAiSummaryLoading] = useState(false);
  const [aiSummaryError, setAiSummaryError] = useState<string | null>(null);
  const aiSummaryFetched = useRef(false);

  // id 变化时重置
  useEffect(() => {
    setAiSummaryData(null);
    setAiSummaryError(null);
    setAiSummaryLoading(false);
    setAiSummaryExpanded(false);
    aiSummaryFetched.current = false;
  }, [id]);

  const handleToggleAiSummary = useCallback(() => {
    if (!aiSummaryExpanded) {
      // 展开
      setAiSummaryExpanded(true);
      if (!aiSummaryFetched.current && !aiSummaryLoading) {
        setAiSummaryLoading(true);
        setAiSummaryError(null);
        aiSummaryFetched.current = true;
        generateEntrySummary(id!)
          .then((data) => {
            setAiSummaryData(data);
          })
          .catch((err) => {
            setAiSummaryError(err instanceof Error ? err.message : "生成摘要失败");
            aiSummaryFetched.current = false; // 允许重试
          })
          .finally(() => {
            setAiSummaryLoading(false);
          });
      }
    } else {
      // 收起
      setAiSummaryExpanded(false);
    }
  }, [aiSummaryExpanded, aiSummaryLoading, id]);

  const handleRetryAiSummary = useCallback(() => {
    setAiSummaryError(null);
    setAiSummaryLoading(true);
    aiSummaryFetched.current = true;
    generateEntrySummary(id!)
      .then((data) => {
        setAiSummaryData(data);
      })
      .catch((err) => {
        setAiSummaryError(err instanceof Error ? err.message : "生成摘要失败");
        aiSummaryFetched.current = false;
      })
      .finally(() => {
        setAiSummaryLoading(false);
      });
  }, [id]);

  return {
    aiSummaryExpanded,
    aiSummaryData,
    aiSummaryLoading,
    aiSummaryError,
    handleToggleAiSummary,
    handleRetryAiSummary,
  };
}
