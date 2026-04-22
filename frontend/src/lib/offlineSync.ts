/**
 * 离线同步模块
 *
 * 监听 online 事件，自动重放 offlineQueue 中的 pending mutation。
 * 导出 initSync() 供 App 启动时调用。
 */

import * as queue from "@/lib/offlineQueue";
import { createEntry, updateEntry, deleteEntry } from "@/services/api";
import type { TaskStatus, EntryUpdate } from "@/types/task";
import { toast } from "sonner";

// ─── 同步进度订阅 ────────────────────────────────────

export interface SyncProgress {
  current: number;
  total: number;
}

export type SyncEventType = "progress" | "completed" | "auth_failed";

export interface SyncEvent {
  type: SyncEventType;
  progress?: SyncProgress;
}

type SyncEventListener = (event: SyncEvent) => void;
const listeners = new Set<SyncEventListener>();

/** 订阅同步进度变化 */
export function subscribeSyncProgress(cb: SyncEventListener): () => void {
  listeners.add(cb);
  return () => { listeners.delete(cb); };
}

function notifyProgress(event: SyncEvent) {
  listeners.forEach((cb) => cb(event));
}

// ─── 同步核心 ────────────────────────────────────────

let syncing = false;

/** 当前是否正在同步 */
export function isSyncing(): boolean {
  return syncing;
}

/**
 * 重放队列中的 pending 项。
 * 防重入：同步进行中再次调用会被忽略。
 */
export async function sync(): Promise<void> {
  if (syncing) return;
  syncing = true;

  try {
    const items = await queue.getAll();
    const pending = items.filter((i) => i.status === "pending");

    // 清理上次 sync 已标记 synced 但 remove 失败的残留项
    const syncedItems = items.filter((i) => i.status === "synced");
    for (const si of syncedItems) {
      try { await queue.remove(si.id); } catch { /* 忽略 */ }
    }

    if (pending.length === 0) {
      return;
    }

    let synced = 0;
    let authFailed = false;
    let hasPostSync = false;
    let hasTerminalFailure = false;

    for (const item of pending) {
      notifyProgress({ type: "progress", progress: { current: synced + 1, total: pending.length } });

      try {
        if (item.method === "POST" && item.url === "/entries") {
          const body = item.body as Record<string, unknown>;
          await createEntry({
            type: (body.category as string) || (body.type as string) || "inbox",
            title: (body.title as string) || "",
            content: body.content as string | undefined,
            status: body.status as TaskStatus | undefined,
          });
          hasPostSync = true;
        } else if (item.method === "PUT" && item.url.startsWith("/entries/")) {
          const entryId = item.url.replace("/entries/", "");
          await updateEntry(entryId, item.body as EntryUpdate);
        } else if (item.method === "DELETE" && item.url.startsWith("/entries/")) {
          const entryId = item.url.replace("/entries/", "");
          await deleteEntry(entryId);
        } else {
          // 不支持的 mutation，跳过
          continue;
        }
      } catch (err: unknown) {
        const status =
          (err as { status?: number })?.status ??
          (err as { response?: { status?: number } })?.response?.status;

        if (status === 401) {
          // 认证错误：标记 failed，停止同步
          try { await queue.update(item.id, { status: "failed" }); } catch { /* 队列不可用时忽略 */ }
          authFailed = true;
          break;
        } else if (!status || status >= 500) {
          // 网络错误 / 5xx：递增重试计数
          const newRetry = item.retry_count + 1;
          if (newRetry > 3) {
            try { await queue.update(item.id, { status: "failed", retry_count: newRetry }); } catch { /* 队列不可用时忽略 */ }
            hasTerminalFailure = true;
            toast.error("同步失败", { description: "离线操作重试次数已用尽，请检查网络后重试" });
          } else {
            try { await queue.update(item.id, { retry_count: newRetry }); } catch { /* 队列不可用时忽略 */ }
          }
        } else {
          // 其他错误（4xx 等）：标记 failed
          try { await queue.update(item.id, { status: "failed" }); } catch { /* 队列不可用时忽略 */ }
          hasTerminalFailure = true;
          toast.error("同步失败", { description: "部分离线操作未能同步，请检查后重试" });
        }
        continue;
      }

      // API 调用成功：先标记 synced 防止 remove 失败后重复执行远程调用
      try {
        await queue.update(item.id, { status: "synced" });
      } catch {
        // 标记失败时继续尝试移除
      }

      // 从队列移除（IDB 失败不影响已成功的远程调用，下次同步会清理 synced 项）
      try {
        await queue.remove(item.id);
      } catch {
        // 队列移除失败不影响已成功的远程操作，synced 状态确保不会被重复执行
      }
      // POST 对应离线创建的 local-* 条目，需要移除离线占位
      if (item.method === "POST") {
        const { useTaskStore } = await import("@/stores/taskStore");
        useTaskStore.getState().removeOfflineEntry(item.client_entry_id);
      }
      synced++;
    }

    // POST 同步后需要刷新获取服务端真实 ID；终态失败也需要刷新回滚乐观状态
    if (hasPostSync || hasTerminalFailure) {
      const { useTaskStore } = await import("@/stores/taskStore");
      await useTaskStore.getState().fetchEntries();
    }

    // 发送完成事件
    if (authFailed) {
      notifyProgress({ type: "auth_failed" });
    } else {
      notifyProgress({ type: "completed" });
    }
  } finally {
    syncing = false;
  }
}

/**
 * 初始化同步：在线 + 队列有 pending 项时立即触发。
 * 在 App.tsx useEffect 中调用，覆盖「app 重启时已在线但有 pending 队列」场景。
 */
export async function initSync(): Promise<void> {
  if (!navigator.onLine) return;
  const n = await queue.count();
  if (n > 0) {
    sync();
  }
}

// ─── 自动监听 online 事件 ────────────────────────────

if (typeof window !== "undefined") {
  window.addEventListener("online", () => {
    sync();
  });
}
