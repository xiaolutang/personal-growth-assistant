import { create } from "zustand";
import type {
  Task,
  TaskStatus,
  Category,
  EntryCreate,
  EntryUpdate,
  SearchResult,
  KnowledgeGraphResponse,
} from "@/types/task";
import {
  getEntries,
  createEntry as apiCreateEntry,
  updateEntry,
  deleteEntry as apiDeleteEntry,
  searchEntries as apiSearchEntries,
  getKnowledgeGraph as apiGetKnowledgeGraph,
} from "@/services/api";
import { ApiError } from "@/lib/errors";

interface TaskStore {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;
  serviceUnavailable: boolean;
  searchResults: SearchResult[];
  knowledgeGraph: KnowledgeGraphResponse | null;
  /** 离线创建的条目列表（同步完成后移除） */
  _offlineEntries: Task[];

  // Actions
  fetchEntries: (params?: {
    type?: string;
    status?: string;
    parent_id?: string;
    tags?: string[];
    start_date?: string;
    end_date?: string;
    limit?: number;
  }) => Promise<void>;
  createEntry: (data: EntryCreate) => Promise<Task>;
  updateEntry: (id: string, data: EntryUpdate) => Promise<void>;
  addTasks: (tasks: { type: string; title: string; content?: string; category: Category; status: TaskStatus; tags?: string[] }[]) => Promise<void>;
  updateTaskStatus: (id: string, status: TaskStatus) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
  searchEntries: (query: string, limit?: number) => Promise<SearchResult[]>;
  getKnowledgeGraph: (concept: string, depth?: number) => Promise<KnowledgeGraphResponse | null>;
  clearSearchResults: () => void;
  clearKnowledgeGraph: () => void;
  getTasksByCategory: (category: Category) => Task[];
  getTasksByStatus: (status: TaskStatus) => Task[];
  getTodayTasks: () => Task[];
  /** 添加或更新离线条目 */
  upsertOfflineEntry: (entry: Task) => void;
  /** 移除指定离线条目（同步完成后） */
  removeOfflineEntry: (clientEntryId: string) => void;
  /** 清空所有离线条目（登出时） */
  clearOfflineEntries: () => void;
}

export const useTaskStore = create<TaskStore>()((set, get) => ({
  tasks: [],
  isLoading: false,
  error: null,
  serviceUnavailable: false,
  searchResults: [],
  knowledgeGraph: null,
  _offlineEntries: [],

  fetchEntries: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await getEntries(params);
      set(state => ({
        tasks: [...response.entries, ...state._offlineEntries],
        isLoading: false,
        serviceUnavailable: false,
      }));
    } catch (error) {
      const is503 = error instanceof ApiError && error.isServiceUnavailable;
      set({
        error: error instanceof Error ? error.message : "获取条目失败",
        serviceUnavailable: is503,
        isLoading: false,
      });
    }
  },

  createEntry: async (data: EntryCreate) => {
    set({ isLoading: true, error: null });
    try {
      const entry = await apiCreateEntry(data);
      // 创建成功后重新获取列表
      await get().fetchEntries();
      return entry;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "创建条目失败",
        isLoading: false,
      });
      throw error;
    }
  },

  updateEntry: async (id: string, data: EntryUpdate) => {
    set({ isLoading: true, error: null });
    try {
      await updateEntry(id, data);
      // 更新成功后重新获取列表
      await get().fetchEntries();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "更新条目失败",
        isLoading: false,
      });
      throw error;
    }
  },

  // 批量添加任务（从 AI 解析结果创建）
  addTasks: async (tasks) => {
    set({ isLoading: true, error: null });
    try {
      // 并行创建条目
      await Promise.all(
        tasks.map((task) =>
          apiCreateEntry({
            type: task.type || task.category,
            title: task.title,
            content: task.content,
            tags: task.tags,
          })
        )
      );
      // 创建完成后重新获取列表
      await get().fetchEntries();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "创建条目失败",
        isLoading: false,
      });
    }
  },

  updateTaskStatus: async (id: string, status: TaskStatus) => {
    set({ isLoading: true, error: null });
    try {
      await updateEntry(id, { status });
      // 更新成功后重新获取列表
      await get().fetchEntries();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "更新状态失败",
        isLoading: false,
      });
    }
  },

  deleteTask: async (id: string) => {
    // 乐观更新：先从本地移除
    const previousTasks = get().tasks;
    console.log('[乐观更新] 删除前任务数:', previousTasks.length, '删除ID:', id);
    set({ tasks: previousTasks.filter((t) => t.id !== id), error: null });
    console.log('[乐观更新] 删除后任务数:', get().tasks.length);

    try {
      console.log('[API调用] 开始删除:', id);
      const result = await apiDeleteEntry(id);
      console.log('[API调用] 删除结果:', result);
      // 删除成功后重新获取列表以确保后端数据一致
      await get().fetchEntries();
    } catch (error) {
      // 失败时回滚
      console.log('[API调用] 删除失败:', error);
      set({
        tasks: previousTasks,
        error: error instanceof Error ? error.message : "删除失败",
      });
    }
  },

  searchEntries: async (query: string, limit: number = 5) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiSearchEntries(query, limit);
      set({
        searchResults: response.results,
        isLoading: false,
      });
      return response.results;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "搜索失败",
        isLoading: false,
      });
      return [];
    }
  },

  getKnowledgeGraph: async (concept: string, depth: number = 2) => {
    set({ isLoading: true, error: null });
    try {
      const response = await apiGetKnowledgeGraph(concept, depth);
      set({
        knowledgeGraph: response,
        isLoading: false,
      });
      return response;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "获取知识图谱失败",
        isLoading: false,
      });
      return null;
    }
  },

  clearSearchResults: () => {
    set({ searchResults: [] });
  },

  clearKnowledgeGraph: () => {
    set({ knowledgeGraph: null });
  },

  upsertOfflineEntry: (entry: Task) => {
    set(state => {
      const offlineEntry = { ...entry, _offlinePending: true };
      const exists = state._offlineEntries.find(e => e.id === entry.id);
      if (exists) {
        return {
          _offlineEntries: state._offlineEntries.map(e => e.id === entry.id ? offlineEntry : e),
          tasks: state.tasks.map(t => t.id === entry.id ? offlineEntry : t),
        };
      }
      return {
        _offlineEntries: [...state._offlineEntries, offlineEntry],
        tasks: [offlineEntry, ...state.tasks],
      };
    });
  },

  removeOfflineEntry: (clientEntryId: string) => {
    set(state => ({
      _offlineEntries: state._offlineEntries.filter(e => e.id !== clientEntryId),
      tasks: state.tasks.filter(t => t.id !== clientEntryId),
    }));
  },

  clearOfflineEntries: () => {
    set(state => ({
      _offlineEntries: [],
      tasks: state.tasks.filter(t => !t._offlinePending),
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
}));
