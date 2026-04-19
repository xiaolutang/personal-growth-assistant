/**
 * 离线同步模块
 *
 * 监听 online 事件，自动重放 offlineQueue 中的 pending mutation。
 * 导出 initSync() 供 App 启动时调用。
 */

import * as queue from "@/lib/offlineQueue";
import { createEntry } from "@/services/api";
import type { TaskStatus } from "@/types/task";

// ─── 同步进度订阅 ────────────────────────────────────

export interface SyncProgress {
  current: number;
  total: number;
}

type SyncProgressListener = (progress: SyncProgress | null) => void;
const listeners = new Set<SyncProgressListener>();

/** 订阅同步进度变化 */
export function subscribeSyncProgress(cb: SyncProgressListener): () => void {
  listeners.add(cb);
  return () => { listeners.delete(cb); };
}

function notifyProgress(progress: SyncProgress | null) {
  listeners.forEach((cb) => cb(progress));
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

    if (pending.length === 0) {
      return;
    }

    let synced = 0;

    for (const item of pending) {
      notifyProgress({ current: synced + 1, total: pending.length });

      try {
        // 目前仅支持 POST /entries
        if (item.method === "POST" && item.url === "/entries") {
          const body = item.body as Record<string, unknown>;
          await createEntry({
            type: (body.type as string) || "inbox",
            title: (body.title as string) || "",
            content: body.content as string | undefined,
            status: body.status as TaskStatus | undefined,
          });
        }

        // 同步成功：从队列移除 + 移除离线条目
        await queue.remove(item.id);
        const { useTaskStore } = await import("@/stores/taskStore");
        useTaskStore.getState().removeOfflineEntry(item.client_entry_id);
        synced++;
      } catch (err: unknown) {
        const status =
          (err as { status?: number })?.status ??
          (err as { response?: { status?: number } })?.response?.status;

        if (status === 401) {
          // 认证错误：标记 failed，停止同步
          await queue.update(item.id, { status: "failed" });
          // 通知 UI 显示重新登录提示
          notifyProgress({ current: -1, total: -1 });
          break;
        } else if (!status || status >= 500) {
          // 网络错误 / 5xx：递增重试计数
          const newRetry = item.retry_count + 1;
          if (newRetry > 3) {
            await queue.update(item.id, { status: "failed", retry_count: newRetry });
          } else {
            await queue.update(item.id, { retry_count: newRetry });
          }
        } else {
          // 其他错误（4xx 等）：标记 failed
          await queue.update(item.id, { status: "failed" });
        }
      }
    }

    // 同步完成后刷新服务端数据
    if (synced > 0) {
      const { useTaskStore } = await import("@/stores/taskStore");
      await useTaskStore.getState().fetchEntries();
    }
  } finally {
    syncing = false;
    notifyProgress(null);
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
