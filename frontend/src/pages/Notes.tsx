import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TaskList } from "@/components/TaskList";
import { Header } from "@/components/layout/Header";
import { useTaskStore } from "@/stores/taskStore";
import { Plus, X, FileText, Loader2 } from "lucide-react";

export function Notes() {
  const { getTasksByCategory, createEntry } = useTaskStore();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newNoteTitle, setNewNoteTitle] = useState("");
  const [newNoteContent, setNewNoteContent] = useState("");
  const [newNoteTags, setNewNoteTags] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const notes = getTasksByCategory("note");

  const handleCreateNote = async () => {
    if (!newNoteTitle.trim()) return;

    setIsCreating(true);
    try {
      await createEntry({
        type: "note",
        title: newNoteTitle.trim(),
        content: newNoteContent.trim(),
        tags: newNoteTags.trim() ? newNoteTags.split(",").map((t) => t.trim()).filter(Boolean) : [],
      });
      // 重置表单
      setNewNoteTitle("");
      setNewNoteContent("");
      setNewNoteTags("");
      setShowCreateForm(false);
    } finally {
      setIsCreating(false);
    }
  };

  const handleCancel = () => {
    setNewNoteTitle("");
    setNewNoteContent("");
    setNewNoteTags("");
    setShowCreateForm(false);
  };

  return (
    <>
      <Header title="学习笔记" />
      <main className="flex-1 p-6 pb-32 overflow-y-auto">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">笔记列表 ({notes.length})</CardTitle>
            {!showCreateForm && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowCreateForm(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                新建笔记
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 创建笔记表单 */}
            {showCreateForm && (
              <Card className="border-dashed">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      新建笔记
                    </CardTitle>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCancel}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm font-medium mb-1 block">标题 *</label>
                    <Input
                      value={newNoteTitle}
                      onChange={(e) => setNewNoteTitle(e.target.value)}
                      placeholder="输入笔记标题..."
                      disabled={isCreating}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-1 block">内容（支持 Markdown）</label>
                    <textarea
                      value={newNoteContent}
                      onChange={(e) => setNewNoteContent(e.target.value)}
                      placeholder="输入笔记内容，支持 Markdown 格式..."
                      className="w-full min-h-[120px] p-3 text-sm border rounded-md resize-y focus:outline-none focus:ring-2 focus:ring-primary"
                      disabled={isCreating}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium mb-1 block">标签（逗号分隔）</label>
                    <Input
                      value={newNoteTags}
                      onChange={(e) => setNewNoteTags(e.target.value)}
                      placeholder="例如：技术, 学习, 笔记"
                      disabled={isCreating}
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="outline"
                      onClick={handleCancel}
                      disabled={isCreating}
                    >
                      取消
                    </Button>
                    <Button
                      onClick={handleCreateNote}
                      disabled={!newNoteTitle.trim() || isCreating}
                    >
                      {isCreating ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                          创建中
                        </>
                      ) : (
                        <>
                          <Plus className="h-4 w-4 mr-2" />
                          创建
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 笔记列表 */}
            <TaskList
              tasks={notes}
              emptyMessage={showCreateForm ? "创建你的第一篇笔记吧" : "还没有笔记，点击上方「新建笔记」开始"}
            />
          </CardContent>
        </Card>
      </main>
    </>
  );
}
