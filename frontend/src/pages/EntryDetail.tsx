import { useParams, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { exportSingleEntry } from "@/services/api";
import { PageChatPanel } from "@/components/PageChatPanel";
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

        {!editing.isEditing && entry && (
          <PageChatPanel
            title="编辑助手"
            welcomeMessage="需要帮忙整理内容吗？"
            suggestions={
              entry.category === "task" ? [
                { label: "拆解子任务", message: "帮我把这个任务拆解为可执行的子任务" },
                { label: "生成摘要", message: "帮我生成一段摘要" },
                { label: "整理内容", message: "帮我整理和优化这段内容" },
              ] : entry.category === "note" ? [
                { label: "整理笔记", message: "帮我把这段笔记整理一下" },
                { label: "提取要点", message: "帮我提取关键知识点" },
                { label: "关联知识", message: "帮我看看还有哪些相关知识" },
              ] : [
                { label: "整理内容", message: "帮我整理和优化这段内容" },
                { label: "生成摘要", message: "帮我生成一段摘要" },
                { label: "关联知识", message: "帮我看看还有哪些相关知识" },
              ]
            }
            pageContext={{ page: "entry_detail" }}
            pageData={{
              entry_title: entry.title,
              category: entry.category,
              tags: (entry.tags || []).join(", "),
              status: entry.status,
              priority: entry.priority ?? "",
              content_preview: (entry.content || "").slice(0, 500),
            }}
            className="mt-6"
            defaultCollapsed
          />
        )}
      </div>
    </div>
  );
}
