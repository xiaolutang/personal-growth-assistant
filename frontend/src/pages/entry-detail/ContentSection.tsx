import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Eye, Code, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { categoryConfig } from "@/config/constants";
import type { Task } from "@/types/task";
import { StructuredContent } from "./StructuredContent";
import { getMarkdownComponents } from "./MarkdownComponents";

interface ContentSectionProps {
  entry: Task;
  isEditing: boolean;
  contentTab: "preview" | "edit";
  editContent: string;
  parsedContent: string;
  referenceIds: string[];
  referencedNotes: Map<string, Task>;
  isSaving: boolean;
  setEditContent: React.Dispatch<React.SetStateAction<string>>;
  setContentTab: React.Dispatch<React.SetStateAction<"preview" | "edit">>;
}

export function ContentSection({
  entry,
  isEditing,
  contentTab,
  editContent,
  parsedContent,
  referenceIds,
  referencedNotes,
  isSaving,
  setEditContent,
  setContentTab,
}: ContentSectionProps) {
  const navigate = useNavigate();

  return (
    <>
      {isEditing && (
        <div className="flex items-center gap-2 mb-3">
          <button
            onClick={() => setContentTab("preview")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              contentTab === "preview"
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            <Eye className="h-4 w-4" />
            预览
          </button>
          <button
            onClick={() => setContentTab("edit")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              contentTab === "edit"
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            <Code className="h-4 w-4" />
            编辑
          </button>
        </div>
      )}

      {isEditing && contentTab === "edit" ? (
        <div className="space-y-3">
          <Textarea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            placeholder="输入 Markdown 格式的内容..."
            className="min-h-[300px] md:min-h-[400px] font-mono text-sm w-full"
            disabled={isSaving}
          />
          <p className="text-xs text-muted-foreground">内容修改后 1 秒自动保存</p>
        </div>
      ) : (
        <div className="space-y-4">
          {["decision", "reflection", "question"].includes(entry.category) && !isEditing ? (
            <StructuredContent
              content={parsedContent}
              category={entry.category}
              navigate={navigate}
            />
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={getMarkdownComponents(navigate)}
              >
                {(isEditing ? editContent : parsedContent) || "暂无内容"}
              </ReactMarkdown>
            </div>
          )}

          {referenceIds.length > 0 && (
            <Card className="mt-4">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  引用的笔记 ({referenceIds.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {referenceIds.map((noteId) => {
                    const note = referencedNotes.get(noteId);
                    return (
                      <div
                        key={noteId}
                        className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                        onClick={() => navigate(`/entry/${noteId}`)}
                      >
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">{note?.title || noteId}</span>
                          {note && (
                            <Badge variant="outline" className="text-xs">
                              {categoryConfig[note.category]?.label || note.category}
                            </Badge>
                          )}
                        </div>
                        {note && (
                          <span className="text-xs text-muted-foreground">
                            {new Date(note.created_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </>
  );
}
