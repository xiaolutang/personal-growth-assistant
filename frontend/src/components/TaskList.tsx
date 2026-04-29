import type { Task } from "@/types/task";
import { TaskCard } from "./TaskCard";
import { DecisionCard } from "@/pages/tasks/DecisionCard";
import { ProjectCard } from "@/pages/tasks/ProjectCard";
import { Inbox } from "lucide-react";

interface TaskListProps {
  tasks: Task[];
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
  emptyAction?: { label: string; onClick: () => void };
  highlightKeyword?: string;
  selectable?: boolean;
  selectedIds?: Set<string>;
  onSelect?: (id: string) => void;
  disableActions?: boolean;
  /** F05: 当前激活的子 Tab，用于决定 ProjectCard 的布局模式 */
  activeSubTab?: string;
  /** F06: 自定义卡片点击回调（搜索模式下用于 task/decision/project 跳转到任务页） */
  onCardClick?: (task: Task) => void;
  /** F07: 转化成功后的回调（用于从列表移除卡片） */
  onConvertSuccess?: (task: Task) => void;
}

export function TaskList({ tasks, emptyMessage = "暂无任务", emptyIcon, emptyAction, highlightKeyword, selectable = false, selectedIds, onSelect, disableActions = false, activeSubTab = "all", onCardClick, onConvertSuccess }: TaskListProps) {
  if (tasks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
        {emptyIcon || <Inbox className="h-10 w-10 opacity-30" />}
        <p>{emptyMessage}</p>
        {emptyAction && (
          <button
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:bg-primary/90 transition-colors"
            onClick={emptyAction.onClick}
          >
            {emptyAction.label}
          </button>
        )}
      </div>
    );
  }

  // F05: 在 project 子 Tab 下使用网格布局
  const isProjectTab = activeSubTab === "project";
  const projectTasks = isProjectTab ? tasks : [];

  return (
    <>
      {/* F05: project 子 Tab 下以 2 列网格布局展示 */}
      {isProjectTab ? (
        <div className="grid grid-cols-2 gap-3">
          {projectTasks.map((task) => (
            <ProjectCard
              key={task.id}
              project={task}
              layout="grid"
              selectable={selectable}
              selected={selectedIds?.has(task.id)}
              onSelect={onSelect}
            />
          ))}
        </div>
      ) : (
        /* F05: 全部子 Tab 下 project 与其他条目混合展示，project 用 compact 布局 */
        <div className="space-y-2">
          {tasks.map((task) => {
            // F04: decision 类型使用专属 DecisionCard
            if (task.category === "decision") {
              return (
                <DecisionCard
                  key={task.id}
                  decision={task}
                  selectable={selectable}
                  selected={selectedIds?.has(task.id)}
                  onSelect={onSelect}
                  onClickOverride={onCardClick}
                />
              );
            }
            // F05: project 类型使用专属 ProjectCard（紧凑布局）
            if (task.category === "project") {
              return (
                <ProjectCard
                  key={task.id}
                  project={task}
                  layout="compact"
                  selectable={selectable}
                  selected={selectedIds?.has(task.id)}
                  onSelect={onSelect}
                  onClickOverride={onCardClick}
                />
              );
            }
            return (
              <TaskCard key={task.id} task={task} highlightKeyword={highlightKeyword} selectable={selectable} selected={selectedIds?.has(task.id)} onSelect={onSelect} disableActions={disableActions} onClickOverride={onCardClick} onConvertSuccess={onConvertSuccess} />
            );
          })}
        </div>
      )}
    </>
  );
}
