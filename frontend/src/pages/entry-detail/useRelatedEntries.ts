import { useState, useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";
import { getRelatedEntries } from "@/services/api";
import type { RelatedEntry } from "@/services/api";
import type { Task } from "@/types/task";

export interface RelatedEntriesState {
  relatedEntries: RelatedEntry[];
  relatedLoading: boolean;
  relatedError: boolean;
  parsedContent: string;
  referenceIds: string[];
  referencedNotes: Map<string, Task>;
}

export function useRelatedEntries(
  entry: Task | null,
  referencedNotes: Map<string, Task>,
): RelatedEntriesState {
  const { id } = useParams<{ id: string }>();
  const [relatedEntries, setRelatedEntries] = useState<RelatedEntry[]>([]);
  const [relatedLoading, setRelatedLoading] = useState(false);
  const [relatedError, setRelatedError] = useState(false);

  // 解析内容中的 [[note-id]] 引用
  const parsedContent = useMemo(() => {
    if (!entry?.content) return entry?.content || "";
    return entry.content.replace(/\[\[([^\]]+)\]\]/g, (_match, noteId) => {
      const refNote = referencedNotes.get(noteId);
      if (refNote) {
        return `[${refNote.title}](/entry/${noteId})`;
      }
      return `[${noteId}](/entry/${noteId})`;
    });
  }, [entry?.content, referencedNotes]);

  // 提取内容中的所有引用 ID
  const referenceIds = useMemo(() => {
    if (!entry?.content) return [];
    const matches = entry.content.match(/\[\[([^\]]+)\]\]/g) || [];
    return matches.map((m) => m.slice(2, -2));
  }, [entry?.content]);

  // 关联条目独立加载
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setRelatedLoading(true);
    setRelatedError(false);
    getRelatedEntries(id)
      .then((related) => {
        if (!cancelled) setRelatedEntries(related);
      })
      .catch(() => {
        if (!cancelled) setRelatedError(true);
      })
      .finally(() => {
        if (!cancelled) setRelatedLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

  return {
    relatedEntries,
    relatedLoading,
    relatedError,
    parsedContent,
    referenceIds,
    referencedNotes,
  };
}
