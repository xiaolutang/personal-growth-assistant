import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Task, TaskStatus, Category } from "@/types/task";
import { parseText } from "@/services/api";

interface TaskStore {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;

  // Actions
  addTasks: (tasks: Omit<Task, "id" | "created_at">[]) => void;
  parseAndAddTasks: (text: string) => Promise<void>;
  updateTaskStatus: (id: number, status: TaskStatus) => void;
  deleteTask: (id: number) => void;
  getTasksByCategory: (category: Category) => Task[];
  getTasksByStatus: (status: TaskStatus) => Task[];
  getTodayTasks: () => Task[];
}

export const useTaskStore = create<TaskStore>()(
  persist(
    (set, get) => ({
      tasks: [],
      isLoading: false,
      error: null,

      addTasks: (newTasks: Omit<Task, "id" | "created_at">[]) => {
        const tasksWithId = newTasks.map((task, index) => ({
          ...task,
          id: Date.now() + index,
          created_at: new Date().toISOString(),
        }));
        set((state) => ({
          tasks: [...state.tasks, ...tasksWithId],
        }));
      },

      parseAndAddTasks: async (text: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await parseText(text);
          const newTasks = response.tasks.map((task, index) => ({
            ...task,
            id: Date.now() + index,
            created_at: new Date().toISOString(),
          }));
          set((state) => ({
            tasks: [...state.tasks, ...newTasks],
            isLoading: false,
          }));
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "解析失败",
            isLoading: false,
          });
        }
      },

      updateTaskStatus: (id: number, status: TaskStatus) => {
        set((state) => ({
          tasks: state.tasks.map((task) =>
            task.id === id
              ? {
                  ...task,
                  status,
                  updated_at: new Date().toISOString(),
                  ...(status === "complete"
                    ? { completed_at: new Date().toISOString() }
                    : {}),
                }
              : task
          ),
        }));
      },

      deleteTask: (id: number) => {
        set((state) => ({
          tasks: state.tasks.filter((task) => task.id !== id),
        }));
      },

      getTasksByCategory: (category: Category) => {
        return get().tasks.filter((task) => task.category === category);
      },

      getTasksByStatus: (status: TaskStatus) => {
        return get().tasks.filter((task) => task.status === status);
      },

      getTodayTasks: () => {
        const today = new Date().toISOString().split("T")[0];
        return get().tasks.filter((task) => {
          if (task.planned_date) {
            return task.planned_date.startsWith(today);
          }
          if (task.created_at) {
            return task.created_at.startsWith(today);
          }
          return false;
        });
      },
    }),
    {
      name: "task-storage",
    }
  )
);
