import { useState, useRef, useEffect, useCallback } from "react";
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
import { getEntries } from "@/services/api";

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

/** 从光标位置向前检测 [[ 触发词，返回搜索词和起始位置 */
function detectLinkTrigger(value: string, cursorPos: number): { searchQuery: string; startPos: number } | null {
  // 从光标向前找 [[
  const textBefore = value.slice(0, cursorPos);
  const openIdx = textBefore.lastIndexOf("[[");
  if (openIdx === -1) return null;

  // 确保 [[ 后面到光标之间没有换行或 ]]
  const between = textBefore.slice(openIdx + 2);
  if (between.includes("\n") || between.includes("]]")) return null;

  return { searchQuery: between, startPos: openIdx };
}

interface NoteCandidate {
  id: string;
  title: string;
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

  // --- 补全状态 ---
  const [showCompletion, setShowCompletion] = useState(false);
  const [completionItems, setCompletionItems] = useState<NoteCandidate[]>([]);
  const [completionLoading, setCompletionLoading] = useState(false);
  const [completionError, setCompletionError] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [triggerInfo, setTriggerInfo] = useState<{ searchQuery: string; startPos: number } | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 笔记列表缓存（首次触发后缓存）
  const notesCacheRef = useRef<NoteCandidate[] | null>(null);

  // 追踪当前是否有活跃的 [[ trigger（用于 await 后的陈旧检查）
  const activeTriggerRef = useRef(false);

  // 过滤匹配
  const filteredItems = triggerInfo
    ? completionItems.filter((item) => {
        const q = triggerInfo.searchQuery.toLowerCase();
        return item.title.toLowerCase().includes(q) || item.id.toLowerCase().includes(q);
      }).sort((a, b) => {
        const q = triggerInfo.searchQuery.toLowerCase();
        const aTitle = a.title.toLowerCase();
        const bTitle = b.title.toLowerCase();
        const aStarts = aTitle.startsWith(q) ? 0 : aTitle.includes(q) ? 1 : 2;
        const bStarts = bTitle.startsWith(q) ? 0 : bTitle.includes(q) ? 1 : 2;
        return aStarts - bStarts;
      })
    : completionItems;

  // 加载笔记列表
  const loadNotes = useCallback(async () => {
    if (notesCacheRef.current) return notesCacheRef.current;
    setCompletionLoading(true);
    setCompletionError(false);
    try {
      const res = await getEntries({ type: "note", limit: 200 });
      const notes: NoteCandidate[] = res.entries.map((e) => ({ id: e.id, title: e.title }));
      notesCacheRef.current = notes;
      return notes;
    } catch {
      setCompletionError(true);
      return null;
    } finally {
      setCompletionLoading(false);
    }
  }, []);

  // textarea onChange 处理
  const handleContentChange = useCallback(
    async (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const value = e.target.value;
      const cursorPos = e.target.selectionStart ?? value.length;
      setEditContent(value);

      const trigger = detectLinkTrigger(value, cursorPos);
      if (trigger) {
        setTriggerInfo(trigger);
        setSelectedIdx(0);
        activeTriggerRef.current = true;

        if (!notesCacheRef.current && !completionLoading && !completionError) {
          const notes = await loadNotes();
          if (!notes) {
            // API 失败，静默降级
            setShowCompletion(false);
            activeTriggerRef.current = false;
            return;
          }
          setCompletionItems(notes);
          // await 后重新检查：用户可能在等待期间删除了 [[，此时 ref 已被置为 false
          if (!activeTriggerRef.current) {
            return;
          }
        }
        setShowCompletion(true);
      } else {
        setShowCompletion(false);
        setTriggerInfo(null);
        activeTriggerRef.current = false;
      }
    },
    [setEditContent, loadNotes, completionLoading, completionError],
  );

  // 选中补全项
  const handleSelectItem = useCallback(
    (item: NoteCandidate) => {
      if (!triggerInfo) return;
      const before = editContent.slice(0, triggerInfo.startPos);
      const after = editContent.slice(textareaRef.current?.selectionStart ?? editContent.length);
      const insertion = `[[${item.id}|${item.title}]]`;
      setEditContent(before + insertion + after);
      setShowCompletion(false);
      setTriggerInfo(null);
      // 恢复光标
      requestAnimationFrame(() => {
        if (textareaRef.current) {
          const newPos = before.length + insertion.length;
          textareaRef.current.selectionStart = newPos;
          textareaRef.current.selectionEnd = newPos;
          textareaRef.current.focus();
        }
      });
    },
    [triggerInfo, editContent, setEditContent],
  );

  // 键盘导航
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (!showCompletion || filteredItems.length === 0) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIdx((prev) => (prev + 1) % filteredItems.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIdx((prev) => (prev - 1 + filteredItems.length) % filteredItems.length);
      } else if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSelectItem(filteredItems[selectedIdx]);
      } else if (e.key === "Escape") {
        e.preventDefault();
        setShowCompletion(false);
        setTriggerInfo(null);
      }
    },
    [showCompletion, filteredItems, selectedIdx, handleSelectItem],
  );

  // 点击外部关闭补全
  useEffect(() => {
    if (!showCompletion) return;
    const handleClickOutside = () => {
      setShowCompletion(false);
      setTriggerInfo(null);
    };
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [showCompletion]);

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
        <div className="space-y-3 relative">
          <Textarea
            ref={textareaRef}
            value={editContent}
            onChange={handleContentChange}
            onKeyDown={handleKeyDown}
            placeholder="输入 Markdown 格式的内容... 输入 [[ 引用其他笔记"
            className="min-h-[300px] md:min-h-[400px] font-mono text-sm w-full"
            disabled={isSaving}
          />

          {/* 补全弹窗 */}
          {showCompletion && !completionError && (
            <div
              className="absolute z-50 left-0 right-0 max-h-[240px] overflow-y-auto rounded-lg border bg-popover shadow-lg"
              onClick={(e) => e.stopPropagation()}
            >
              {completionLoading ? (
                <div className="px-3 py-2 text-sm text-muted-foreground">加载中...</div>
              ) : filteredItems.length === 0 ? (
                <div className="px-3 py-2 text-sm text-muted-foreground">无匹配笔记</div>
              ) : (
                filteredItems.map((item, idx) => (
                  <div
                    key={item.id}
                    className={`px-3 py-2 text-sm cursor-pointer transition-colors ${
                      idx === selectedIdx
                        ? "bg-primary/10 text-primary"
                        : "hover:bg-muted"
                    }`}
                    onClick={() => handleSelectItem(item)}
                    onMouseEnter={() => setSelectedIdx(idx)}
                  >
                    <span className="font-medium">{item.title}</span>
                    <span className="ml-2 text-xs text-muted-foreground">{item.id}</span>
                  </div>
                ))
              )}
            </div>
          )}

          <p className="text-xs text-muted-foreground">内容修改后 1 秒自动保存 · 输入 [[ 引用其他笔记</p>
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
