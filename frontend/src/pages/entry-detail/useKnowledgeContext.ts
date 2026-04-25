import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { getKnowledgeContext } from "@/services/api";
import type { KnowledgeContextResponse } from "@/services/api";

export interface KnowledgeContextState {
  knowledgeContext: KnowledgeContextResponse | null;
  knowledgeContextLoading: boolean;
  knowledgeContextError: boolean;
  knowledgeContextExpanded: boolean;
  setKnowledgeContextExpanded: React.Dispatch<React.SetStateAction<boolean>>;
}

export function useKnowledgeContext(): KnowledgeContextState {
  const { id } = useParams<{ id: string }>();
  const [knowledgeContext, setKnowledgeContext] = useState<KnowledgeContextResponse | null>(null);
  const [knowledgeContextLoading, setKnowledgeContextLoading] = useState(false);
  const [knowledgeContextError, setKnowledgeContextError] = useState(false);
  const [knowledgeContextExpanded, setKnowledgeContextExpanded] = useState(true);

  // 知识上下文独立加载
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setKnowledgeContextLoading(true);
    setKnowledgeContextError(false);
    getKnowledgeContext(id)
      .then((data) => {
        if (!cancelled) setKnowledgeContext(data);
      })
      .catch(() => {
        if (!cancelled) setKnowledgeContextError(true);
      })
      .finally(() => {
        if (!cancelled) setKnowledgeContextLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

  return {
    knowledgeContext,
    knowledgeContextLoading,
    knowledgeContextError,
    knowledgeContextExpanded,
    setKnowledgeContextExpanded,
  };
}
