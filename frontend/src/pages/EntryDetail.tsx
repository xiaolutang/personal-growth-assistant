import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowLeft,
  Loader2,
  Calendar,
  Clock,
  Tag,
  CheckCircle,
  Circle,
  Pause,
  XCircle,
  BarChart3,
  Link2,
  Edit2,
  Save,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { getEntry, getEntries, getProjectProgress } from "@/services/api";
import { useTaskStore } from "@/stores/taskStore";
import type { Task } from "@/types/task";
import type { ProjectProgressResponse } from "@/services/api";
import { statusConfig, categoryConfig, priorityConfig } from "@/config/constants";
import { TaskList } from "@/components/TaskList";

export function EntryDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [entry, setEntry] = useState<Task | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [childTasks, setChildTasks] = useState<Task[]>([]);
  const [projectProgress, setProjectProgress] = useState<ProjectProgressResponse | null>(null);
  const [parentEntry, setParentEntry] = useState<Task | null>(null);

  // 编辑模式状态
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const { updateEntry } = useTaskStore();

  useEffect(() => {
    if (!id) return;

    const fetchEntry = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getEntry(id);
        setEntry(data);
        setEditContent(data.content || "");

        // 如果是项目类型，获取子任务和进度
        if (data.category === "project") {
          const [tasksRes, progressRes] = await Promise.all([
            getEntries({ parent_id: id, limit: 100 }),
            getProjectProgress(id).catch(() => null),
          ]);
          setChildTasks(tasksRes.entries);
          setProjectProgress(progressRes);
        }

        // 如果有父条目，获取父条目信息
        if (data.parent_id) {
          try {
            const parentData = await getEntry(data.parent_id);
            setParentEntry(parentData);
          } catch {
            // 父条目可能已被删除，忽略错误
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "获取条目失败");
      } finally {
        setIsLoading(false);
      }
    };

    fetchEntry();
  }, [id]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !entry) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-muted-foreground">{error || "条目不存在"}</p>
        <Button variant="outline" onClick={() => navigate(-1)}>
          返回
        </Button>
      </div>
    );
  }

  const statusInfo = statusConfig[entry.status];
  const categoryInfo = categoryConfig[entry.category];
  const priorityInfo = entry.priority ? priorityConfig[entry.priority] : null;
  const CategoryIcon = categoryInfo.icon;

  // 渲染状态图标
  const renderStatusIcon = () => {
    switch (entry.status) {
      case "complete":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "doing":
        return <Circle className="h-4 w-4 text-yellow-500" />;
      case "paused":
        return <Pause className="h-4 w-4 text-orange-500" />;
      case "cancelled":
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Circle className="h-4 w-4" />;
    }
  };

  // 开始编辑
  const handleStartEdit = () => {
    setEditContent(entry.content || "");
    setIsEditing(true);
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setEditContent(entry.content || "");
    setIsEditing(false);
  };

  // 保存编辑
  const handleSaveEdit = async () => {
    if (!id) return;
    setIsSaving(true);
    try {
      await updateEntry(id, { content: editContent });
      setEntry((prev) => prev ? { ...prev, content: editContent } : prev);
      setIsEditing(false);
    } catch (err) {
      console.error("保存失败:", err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <div className="mb-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(-1)}
            className="mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>

          {/* 编辑按钮 */}
          {!isEditing && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleStartEdit}
              className="mb-4 ml-2"
            >
              <Edit2 className="h-4 w-4 mr-2" />
              编辑
            </Button>
          )}

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 mt-1">
              <CategoryIcon className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl font-bold mb-2">{entry.title}</h1>
              <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                {/* Category */}
                <Badge variant="secondary">{categoryInfo.label}</Badge>

                {/* Status */}
                <div className="flex items-center gap-1">
                  {renderStatusIcon()}
                  <span>{statusInfo.label}</span>
                </div>

                {/* Priority */}
                {priorityInfo && entry.priority !== "medium" && (
                  <Badge variant={priorityInfo.variant}>优先级: {priorityInfo.label}</Badge>
                )}

                {/* Created date */}
                {entry.created_at && (
                  <div className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    <span>
                      创建于 {new Date(entry.created_at).toLocaleDateString()}
                    </span>
                  </div>
                )}

                {/* Updated date */}
                {entry.updated_at && entry.updated_at !== entry.created_at && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    <span>
                      更新于 {new Date(entry.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
              </div>

              {/* Tags */}
              {entry.tags && entry.tags.length > 0 && (
                <div className="flex items-center gap-2 mt-3">
                  <Tag className="h-4 w-4 text-muted-foreground" />
                  <div className="flex flex-wrap gap-1">
                    {entry.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Parent Entry (关联展示) */}
              {parentEntry && (
                <div className="flex items-center gap-2 mt-3">
                  <Link2 className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">所属{categoryConfig[parentEntry.category]?.label || "条目"}:</span>
                  <button
                    onClick={() => navigate(`/entry/${parentEntry.id}`)}
                    className="text-sm text-primary hover:underline"
                  >
                    {parentEntry.title}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Project Progress Section (only for projects) */}
        {entry.category === "project" && projectProgress && (
          <Card className="mb-6">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                项目进度
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>完成进度</span>
                    <span>{projectProgress.progress_percentage}%</span>
                  </div>
                  <Progress value={projectProgress.progress_percentage} />
                </div>
                <div className="flex gap-4 text-sm text-muted-foreground">
                  <span>总任务: {projectProgress.total_tasks}</span>
                  <span>已完成: {projectProgress.completed_tasks}</span>
                </div>
                {Object.keys(projectProgress.status_distribution).length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(projectProgress.status_distribution).map(([status, count]) => (
                      <Badge key={status} variant="outline" className="text-xs">
                        {statusConfig[status as keyof typeof statusConfig]?.label || status}: {count}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Child Tasks Section (only for projects) */}
        {entry.category === "project" && childTasks.length > 0 && (
          <Card className="mb-6">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">子任务 ({childTasks.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <TaskList
                tasks={childTasks}
                emptyMessage="暂无子任务"
              />
            </CardContent>
          </Card>
        )}

        {/* Content */}
        {isEditing ? (
          <div className="space-y-4">
            <Textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              placeholder="输入 Markdown 格式的内容..."
              className="min-h-[400px] font-mono text-sm"
              disabled={isSaving}
            />
            <div className="flex gap-2">
              <Button onClick={handleSaveEdit} disabled={isSaving}>
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    保存中...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    保存
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                onClick={handleCancelEdit}
                disabled={isSaving}
              >
                <X className="h-4 w-4 mr-2" />
                取消
              </Button>
            </div>
          </div>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {entry.content || "暂无内容"}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
