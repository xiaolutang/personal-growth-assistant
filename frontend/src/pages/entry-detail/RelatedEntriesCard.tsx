import { useNavigate } from "react-router-dom";
import {
  Link2,
  Plus,
  FileText,
  Loader2,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LinkEntryDialog } from "@/components/LinkEntryDialog";
import { categoryConfig } from "@/config/constants";
import type { RelatedEntry, EntryLinkItem } from "@/services/api";

interface RelatedEntriesCardProps {
  entryId: string;
  entryLinks: EntryLinkItem[];
  relatedEntries: RelatedEntry[];
  relatedLoading: boolean;
  relatedError: boolean;
  showLinkDialog: boolean;
  deletingLinkId: string | null;
  onShowLinkDialog: (show: boolean) => void;
  onDeleteLink: (linkId: string) => Promise<void>;
  onReloadLinks: () => void;
}

export function RelatedEntriesCard({
  entryId,
  entryLinks,
  relatedEntries,
  relatedLoading,
  relatedError,
  showLinkDialog,
  deletingLinkId,
  onShowLinkDialog,
  onDeleteLink,
  onReloadLinks,
}: RelatedEntriesCardProps) {
  const navigate = useNavigate();

  return (
    <Card className="mt-6">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Link2 className="h-4 w-4" />
            关联条目
          </CardTitle>
          <Button variant="outline" size="sm" onClick={() => onShowLinkDialog(true)}>
            <Plus className="h-3.5 w-3.5 mr-1" />
            添加关联
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {entryLinks.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-medium text-muted-foreground mb-2">手动关联</p>
            <div className="space-y-2">
              {entryLinks.map((link) => (
                <div
                  key={link.id}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-colors group"
                >
                  <div
                    className="flex items-center gap-2 flex-1 min-w-0 cursor-pointer"
                    onClick={() => navigate(`/entries/${link.target_id}`)}
                  >
                    <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="text-sm truncate">{link.target_entry.title}</span>
                    <Badge variant="outline" className="text-xs shrink-0">
                      {(categoryConfig as Record<string, { label: string }>)[link.target_entry.category]?.label || link.target_entry.category}
                    </Badge>
                    <Badge variant="secondary" className="text-xs shrink-0">
                      {link.relation_type === "related" ? "关联" :
                       link.relation_type === "depends_on" ? "依赖" :
                       link.relation_type === "derived_from" ? "来源" : "引用"}
                    </Badge>
                  </div>
                  <button
                    onClick={() => onDeleteLink(link.id)}
                    disabled={deletingLinkId === link.id}
                    className="text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-2"
                    title="删除关联"
                  >
                    {deletingLinkId === link.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {!relatedLoading && !relatedError && relatedEntries.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">自动推荐</p>
            <div className="space-y-2">
              {relatedEntries.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/entries/${item.id}`)}
                >
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{item.title}</span>
                    <Badge variant="outline" className="text-xs">
                      {(categoryConfig as Record<string, { label: string }>)[item.category]?.label || item.category}
                    </Badge>
                  </div>
                  <span className="text-xs text-muted-foreground">{item.relevance_reason}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {entryLinks.length === 0 && relatedEntries.length === 0 && !relatedLoading && (
          <p className="text-sm text-muted-foreground py-2">
            暂无关联条目，点击「添加关联」或添加更多标签自动发现关联
          </p>
        )}
      </CardContent>

      {showLinkDialog && (
        <LinkEntryDialog
          entryId={entryId}
          onClose={() => onShowLinkDialog(false)}
          onCreated={onReloadLinks}
        />
      )}
    </Card>
  );
}
