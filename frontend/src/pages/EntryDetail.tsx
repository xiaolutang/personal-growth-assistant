import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect, useCallback, useRef } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { exportSingleEntry, getBacklinks } from "@/services/api";
import type { BacklinkItem } from "@/services/api";
import { ServiceUnavailable } from "@/components/ServiceUnavailable";

// Hooks
import { useEntryData } from "./entry-detail/useEntryData";
import { useEntryEditing } from "./entry-detail/useEntryEditing";
import { useRelatedEntries } from "./entry-detail/useRelatedEntries";
import { useKnowledgeContext } from "./entry-detail/useKnowledgeContext";
import { useEntryLinks } from "./entry-detail/useEntryLinks";
import { useAiSummary } from "./entry-detail/useAiSummary";

// Sub-components
import { EntryHeader } from "./entry-detail/EntryHeader";
import { CategoryInfoCard } from "./entry-detail/CategoryInfoCard";
import { ProjectSection } from "./entry-detail/ProjectSection";
import { ContentSection } from "./entry-detail/ContentSection";
import { AiSummaryCard } from "./entry-detail/AiSummaryCard";
import { KnowledgeContextCard } from "./entry-detail/KnowledgeContextCard";
import { RelatedEntriesCard } from "./entry-detail/RelatedEntriesCard";
import { TypeActionBar } from "./entry-detail/TypeActionBar";
import { TypeHistoryTimeline } from "./entry-detail/TypeHistoryTimeline";

export function EntryDetail() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  // 数据加载（持有唯一的 entry 状态）
  const data = useEntryData();

  // 编辑状态（消费 data.entry 和 data.setEntry）
  const editing = useEntryEditing(data.entry, data.setEntry);

  // 关联条目
  const related = useRelatedEntries(data.entry, data.referencedNotes);

  // 知识上下文
  const knowledge = useKnowledgeContext();

  // 手动关联
  const links = useEntryLinks();

  // AI 摘要
  const aiSummary = useAiSummary();

  // 反向引用
  const [backlinks, setBacklinks] = useState<BacklinkItem[]>([]);
  const backlinksVersionRef = useRef(0);

  const loadBacklinks = useCallback(() => {
    if (!id) return;
    const version = ++backlinksVersionRef.current;
    getBacklinks(id)
      .then((res) => {
        if (backlinksVersionRef.current === version) {
          setBacklinks(res.backlinks);
        }
      })
      .catch(() => {
        if (backlinksVersionRef.current === version) {
          setBacklinks([]); // 静默降级
        }
      });
  }, [id]);

  useEffect(() => {
    setBacklinks([]);
    loadBacklinks();
  }, [loadBacklinks]);

  const { entry } = data;

  // Loading state
  if (data.isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // 503 service unavailable
  if (data.serviceUnavailable) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <ServiceUnavailable onRetry={() => data.retryService(data.reloadEntry)} />
      </div>
    );
  }

  // Error / not found
  if (data.error || !entry) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-muted-foreground">{data.error || "条目不存在"}</p>
        <Button variant="outline" onClick={() => navigate(-1)}>返回</Button>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto p-4 md:p-6">
        <EntryHeader
          entry={entry}
          isEditing={editing.isEditing}
          isSaving={editing.isSaving}
          isExporting={editing.isExporting}
          editTitle={editing.editTitle}
          editStatus={editing.editStatus}
          editPriority={editing.editPriority}
          editPlannedDate={editing.editPlannedDate}
          editTags={editing.editTags}
          newTagInput={editing.newTagInput}
          saveError={editing.saveError}
          parentEntry={data.parentEntry}
          onNavigateBack={() => editing.handleNavigateBack(navigate)}
          onStartEdit={editing.handleStartEdit}
          onCancelEdit={editing.handleCancelEdit}
          onSaveAll={editing.handleSaveAll}
          onExport={async () => {
            editing.setIsExporting(true);
            try {
              const blob = await exportSingleEntry(id!);
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `${entry?.title ?? "entry"}.md`;
              a.click();
              URL.revokeObjectURL(url);
            } catch { /* silent */ } finally {
              editing.setIsExporting(false);
            }
          }}
          setEditTitle={(v) => editing.setEditTitle(v)}
          setEditStatus={(v) => editing.setEditStatus(v)}
          setEditPriority={(v) => editing.setEditPriority(v)}
          setEditPlannedDate={(v) => editing.setEditPlannedDate(v)}
          setNewTagInput={(v) => editing.setNewTagInput(v)}
          handleAddTag={editing.handleAddTag}
          handleRemoveTag={editing.handleRemoveTag}
        />

        <CategoryInfoCard category={entry.category} status={entry.status} />

        {/* F11: 类型感知操作栏（task/inbox/question/reflection） */}
        {!editing.isEditing && (
          <TypeActionBar
            entry={entry}
            parentEntry={data.parentEntry}
            onReload={data.reloadEntry}
          />
        )}

        {/* F11: 类型转换历史时间线 */}
        {entry.type_history && entry.type_history.length > 0 && (
          <TypeHistoryTimeline typeHistory={entry.type_history} />
        )}

        <ProjectSection
          category={entry.category}
          projectProgress={data.projectProgress}
          childTasks={data.childTasks}
        />

        <ContentSection
          entry={entry}
          isEditing={editing.isEditing}
          contentTab={editing.contentTab}
          editContent={editing.editContent}
          parsedContent={related.parsedContent}
          referenceIds={related.referenceIds}
          referencedNotes={data.referencedNotes}
          isSaving={editing.isSaving}
          setEditContent={editing.setEditContent}
          setContentTab={editing.setContentTab}
        />

        {!editing.isEditing && (
          <AiSummaryCard
            content={entry.content || ""}
            expanded={aiSummary.aiSummaryExpanded}
            loading={aiSummary.aiSummaryLoading}
            error={aiSummary.aiSummaryError}
            data={aiSummary.aiSummaryData}
            onToggle={aiSummary.handleToggleAiSummary}
            onRetry={aiSummary.handleRetryAiSummary}
          />
        )}

        {!editing.isEditing && (
          <KnowledgeContextCard
            knowledgeContext={knowledge.knowledgeContext}
            loading={knowledge.knowledgeContextLoading}
            error={knowledge.knowledgeContextError}
            expanded={knowledge.knowledgeContextExpanded}
            setExpanded={knowledge.setKnowledgeContextExpanded}
          />
        )}

        {!editing.isEditing && id && (
          <RelatedEntriesCard
            entryId={id}
            entryLinks={links.entryLinks}
            relatedEntries={related.relatedEntries}
            relatedLoading={related.relatedLoading}
            relatedError={related.relatedError}
            showLinkDialog={links.showLinkDialog}
            deletingLinkId={links.deletingLinkId}
            onShowLinkDialog={links.setShowLinkDialog}
            onDeleteLink={links.handleDeleteLink}
            onReloadLinks={links.loadEntryLinks}
          />
        )}

        {!editing.isEditing && backlinks.length > 0 && (
          <Card className="mt-4">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5" />
                  <path d="M9 18h6" />
                  <path d="M10 22h4" />
                </svg>
                反向引用 ({backlinks.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {backlinks.map((bl) => (
                  <div
                    key={bl.id}
                    className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/entries/${bl.id}`)}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{bl.title}</span>
                      <Badge variant="outline" className="text-xs">
                        {bl.category}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

      </div>
    </div>
  );
}
