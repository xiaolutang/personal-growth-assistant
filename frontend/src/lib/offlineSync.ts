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

// ─── 队列优化 ────────────────────────────────────────

import type { OfflineQueueItem } from "@/lib/offlineQueue";

/**
 * 优化 pending 队列：合并同条目多次 update，处理 update→delete 冲突。
 *
 * 规则：
 * 1. 同一条目（client_entry_id 相同）的多次 PUT，合并为最后一次的 body。
 * 2. 同一条目有 PUT + DELETE 时，丢弃所有 PUT（delete 已包含最终意图），只保留 DELETE。
 * 3. POST 条目不参与合并。
 * 4. 返回优化后的列表，同时返回被丢弃的队列项 ID（需从 IDB 中删除）。
 *
 * 优化后的列表保持原始时间顺序（只替换/丢弃，不重排）。
 */
export function optimizePendingQueue(
  items: OfflineQueueItem[]
): { optimized: OfflineQueueItem[]; discarded: string[] } {
  const discarded: string[] = [];

  // 按条目分组（排除 POST）
  const byEntry = new Map<string, OfflineQueueItem[]>();
  for (const item of items) {
    if (item.method === "POST") continue;
    const entryId = item.url.replace("/entries/", "");
    if (!entryId) continue;
    const group = byEntry.get(entryId) ?? [];
    group.push(item);
    byEntry.set(entryId, group);
  }

  // 对每个条目组进行优化
  const mergeMap = new Map<string, OfflineQueueItem>(); // entryId → merged item
  for (const [entryId, group] of byEntry) {
    const hasDelete = group.some((i) => i.method === "DELETE");
    const puts = group.filter((i) => i.method === "PUT");
    const deletes = group.filter((i) => i.method === "DELETE");

    if (hasDelete) {
      // 有 DELETE：丢弃所有 PUT，只保留最后一个 DELETE
      for (const put of puts) {
        discarded.push(put.id);
      }
      // 保留最后一个 DELETE（如果有多个 DELETE 也只保留最后一个）
      for (let i = 0; i < deletes.length - 1; i++) {
        discarded.push(deletes[i].id);
      }
      mergeMap.set(entryId, deletes[deletes.length - 1]);
    } else if (puts.length > 1) {
      // 多次 PUT：累积合并 body（partial patch 语义，保留所有字段）
      for (let i = 0; i < puts.length - 1; i++) {
        discarded.push(puts[i].id);
      }
      // 从第一个到最后一个依次合并 body，后面的字段覆盖前面的
      const mergedBody = puts.reduce(
        (acc, put) => ({ ...acc, ...put.body }),
        {} as Record<string, unknown>
      );
      const lastPut = puts[puts.length - 1];
      mergeMap.set(entryId, { ...lastPut, body: mergedBody });
    }
  }

  // 构建优化后的列表
  const optimized: OfflineQueueItem[] = [];
  const discardedSet = new Set(discarded);
  for (const item of items) {
    if (discardedSet.has(item.id)) continue;
    if (item.method === "POST") {
      // POST 条目不参与优化，直接保留
      optimized.push(item);
      continue;
    }
    const entryId = item.url.replace("/entries/", "");
    if (mergeMap.has(entryId)) {
      // 有合并/冲突优化：在第一次遇到该 entryId 时输出优化后的条目
      const mergedItem = mergeMap.get(entryId)!;
      if (mergedItem.id === item.id) {
        optimized.push(mergedItem);
        mergeMap.delete(entryId);
      }
      // 否则是被替代的条目（在 discarded 中），跳过
    } else {
      // 不在 mergeMap 中，说明是单条操作，直接保留
      optimized.push(item);
    }
  }

  return { optimized, discarded };
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
    let pending = items.filter((i) => i.status === "pending");

    // 清理上次 sync 已标记 synced 但 remove 失败的残留项
    const syncedItems = items.filter((i) => i.status === "synced");
    for (const si of syncedItems) {
      try { await queue.remove(si.id); } catch { /* 忽略 */ }
    }

    if (pending.length === 0) {
      return;
    }

    // 队列优化：合并同条目多次 PUT，处理 PUT→DELETE 冲突
    const { optimized, discarded } = optimizePendingQueue(pending);
    // 从 IDB 中删除被丢弃的队列项
    for (const id of discarded) {
      try { await queue.remove(id); } catch { /* 忽略 */ }
    }
    pending = optimized;

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
 * 初始化同步：在线时触发 sync()，覆盖以下场景：
 * - app 重启时有 pending 队列（正常离线重放）
 * - app 重启时有 synced 残留（上次 API 成功但 remove 失败）
 * sync() 内部会先清理 synced 残留，再处理 pending 项。
 */
export async function initSync(): Promise<void> {
  if (!navigator.onLine) return;
  sync();
}

// ─── 自动监听 online 事件 ────────────────────────────

if (typeof window !== "undefined") {
  window.addEventListener("online", () => {
    sync();
  });
}
