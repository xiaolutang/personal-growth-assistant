import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import { getEntryLinks, deleteEntryLink } from "@/services/api";
import type { EntryLinkItem } from "@/services/api";

export interface EntryLinksState {
  entryLinks: EntryLinkItem[];
  showLinkDialog: boolean;
  deletingLinkId: string | null;
  setShowLinkDialog: React.Dispatch<React.SetStateAction<boolean>>;
  loadEntryLinks: () => void;
  handleDeleteLink: (linkId: string) => Promise<void>;
}

export function useEntryLinks(): EntryLinksState {
  const { id } = useParams<{ id: string }>();
  const [entryLinks, setEntryLinks] = useState<EntryLinkItem[]>([]);
  const [, setEntryLinksLoading] = useState(false);
  const [showLinkDialog, setShowLinkDialog] = useState(false);
  const [deletingLinkId, setDeletingLinkId] = useState<string | null>(null);

  // 手动关联加载
  const loadEntryLinks = useCallback(() => {
    if (!id) return;
    setEntryLinksLoading(true);
    getEntryLinks(id)
      .then((data) => setEntryLinks(data.links))
      .catch(() => {}) // 不阻塞页面
      .finally(() => setEntryLinksLoading(false));
  }, [id]);

  useEffect(() => {
    loadEntryLinks();
  }, [loadEntryLinks]);

  // 删除手动关联
  const handleDeleteLink = useCallback(async (linkId: string) => {
    if (!id) return;
    setDeletingLinkId(linkId);
    try {
      await deleteEntryLink(id, linkId);
      setEntryLinks((prev) => prev.filter((l) => l.id !== linkId));
    } catch {
      // 失败不更新列表
    } finally {
      setDeletingLinkId(null);
    }
  }, [id]);

  return {
    entryLinks,
    showLinkDialog,
    deletingLinkId,
    setShowLinkDialog,
    loadEntryLinks,
    handleDeleteLink,
  };
}
