import { useState, useCallback } from "react";
import { Plus, Loader2, Milestone as MilestoneIcon } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MilestoneItem } from "./MilestoneItem";
import {
  getMilestones,
  createMilestone,
  updateMilestone,
  deleteMilestone,
  type Milestone as MilestoneType,
} from "@/services/api";

interface MilestoneListProps {
  goalId: string;
  milestones: MilestoneType[];
  onMilestonesChange: (milestones: MilestoneType[]) => void;
}

export function MilestoneList({ goalId, milestones, onMilestonesChange }: MilestoneListProps) {
  const [newTitle, setNewTitle] = useState("");
  const [newDueDate, setNewDueDate] = useState("");
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const sortedMilestones = [...milestones].sort((a, b) => a.sort_order - b.sort_order);
  const completedCount = milestones.filter(m => m.status === "completed").length;

  const refreshList = useCallback(async () => {
    try {
      const res = await getMilestones(goalId);
      onMilestonesChange(res.milestones ?? []);
    } catch {
      toast.error("刷新里程碑列表失败");
    }
  }, [goalId, onMilestonesChange]);

  const handleCreate = async () => {
    const title = newTitle.trim();
    if (!title) return;
    setCreating(true);
    try {
      await createMilestone(goalId, {
        title,
        due_date: newDueDate || undefined,
      });
      setNewTitle("");
      setNewDueDate("");
      setShowForm(false);
      await refreshList();
      toast.success("里程碑已创建");
    } catch {
      toast.error("创建里程碑失败");
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (milestoneId: string) => {
    const ms = milestones.find(m => m.id === milestoneId);
    if (!ms) return;
    const newStatus = ms.status === "completed" ? "pending" : "completed";
    try {
      const updated = await updateMilestone(goalId, milestoneId, { status: newStatus });
      onMilestonesChange(milestones.map(m => m.id === milestoneId ? updated : m));
    } catch {
      toast.error("更新状态失败");
    }
  };

  const handleDelete = async (milestoneId: string) => {
    try {
      await deleteMilestone(goalId, milestoneId);
      onMilestonesChange(milestones.filter(m => m.id !== milestoneId));
      toast.success("里程碑已删除");
    } catch {
      toast.error("删除里程碑失败");
    }
  };

  const handleTitleChange = async (milestoneId: string, title: string) => {
    const updated = await updateMilestone(goalId, milestoneId, { title });
    onMilestonesChange(milestones.map(m => m.id === milestoneId ? updated : m));
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base flex items-center gap-2">
          <MilestoneIcon className="h-4 w-4" />
          里程碑
          {milestones.length > 0 && (
            <span className="text-sm font-normal text-muted-foreground">
              ({completedCount}/{milestones.length})
            </span>
          )}
        </CardTitle>
        <Button variant="outline" size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-1" />
          添加里程碑
        </Button>
      </CardHeader>
      <CardContent>
        {/* 创建表单 */}
        {showForm && (
          <div className="mb-4 p-3 rounded-lg border bg-accent/20 space-y-2">
            <input
              className="w-full rounded-md border px-3 py-2 text-sm"
              placeholder="里程碑标题"
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") handleCreate(); }}
              autoFocus
            />
            <div className="flex items-center gap-2">
              <input
                type="date"
                className="rounded-md border px-3 py-1.5 text-sm"
                value={newDueDate}
                onChange={e => setNewDueDate(e.target.value)}
              />
              <Button size="sm" onClick={handleCreate} disabled={creating || !newTitle.trim()}>
                {creating ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Plus className="h-3.5 w-3.5 mr-1" />}
                创建
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setShowForm(false); setNewTitle(""); setNewDueDate(""); }}>
                取消
              </Button>
            </div>
          </div>
        )}

        {/* 里程碑列表 */}
        {sortedMilestones.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">
            暂无里程碑，点击上方按钮添加
          </p>
        ) : (
          <div className="space-y-2">
            {sortedMilestones.map(ms => (
              <MilestoneItem
                key={ms.id}
                milestone={ms}
                onToggle={handleToggle}
                onDelete={handleDelete}
                onTitleChange={handleTitleChange}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
