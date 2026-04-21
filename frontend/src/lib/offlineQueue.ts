/**
 * IndexedDB 离线队列模块 — 纯数据层
 *
 * 为离线写操作提供持久化队列。所有方法均为异步，
 * IndexedDB 不可用时优雅降级（不 throw）。
 */

import { useUserStore } from "@/stores/userStore";

// ─── 类型 ───────────────────────────────────────────────

export interface OfflineQueueItem {
  id: string;
  user_id: string;
  client_entry_id: string;
  method: string;
  url: string;
  body: object;
  timestamp: number;
  status: "pending" | "synced" | "failed";
  retry_count: number;
}

export type AddQueueItem = Omit<
  OfflineQueueItem,
  "id" | "user_id" | "timestamp" | "status" | "retry_count"
>;

// ─── 常量 ───────────────────────────────────────────────

const DB_NAME = "growth-offline";
const STORE_NAME = "mutations";
const DB_VERSION = 1;

// ─── IndexedDB 连接 ─────────────────────────────────────

/** 打开/复用数据库连接，自动创建 object store */
function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** 获取当前 user_id，未登录返回 null */
function getUserId(): string | null {
  return useUserStore.getState().user?.id ?? null;
}

/** 生成唯一 ID */
function generateId(): string {
  return `q-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

// ─── 导出 API ───────────────────────────────────────────

/**
 * 向队列中添加一条离线写操作。
 * 返回生成的 id；未登录或 IndexedDB 不可用时返回空字符串。
 */
export async function add(item: AddQueueItem): Promise<string> {
  try {
    const user_id = getUserId();
    if (!user_id) return "";

    const db = await openDB();
    const id = generateId();
    const record: OfflineQueueItem = {
      id,
      user_id,
      ...item,
      timestamp: Date.now(),
      status: "pending",
      retry_count: 0,
    };

    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const req = store.add(record);

      req.onsuccess = () => resolve(id);
      req.onerror = () => resolve("");
      tx.oncomplete = () => db.close();
    });
  } catch {
    return "";
  }
}

/**
 * 获取当前用户的所有队列项，按 timestamp 升序排列。
 * IndexedDB 不可用时返回空数组。
 */
export async function getAll(): Promise<OfflineQueueItem[]> {
  try {
    const user_id = getUserId();
    if (!user_id) return [];

    const db = await openDB();

    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAll();

      req.onsuccess = () => {
        const items = (req.result as OfflineQueueItem[])
          .filter((r) => r.user_id === user_id)
          .sort((a, b) => a.timestamp - b.timestamp);
        resolve(items);
      };
      req.onerror = () => resolve([]);
      tx.oncomplete = () => db.close();
    });
  } catch {
    return [];
  }
}

/**
 * 更新指定队列项的字段（如 retry_count、status）。
 * IndexedDB 不可用时静默忽略。
 */
export async function update(
  id: string,
  changes: Partial<Pick<OfflineQueueItem, "retry_count" | "status" | "body">>
): Promise<void> {
  try {
    const db = await openDB();

    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(id);

      req.onsuccess = () => {
        const record = req.result as OfflineQueueItem | undefined;
        if (record) {
          Object.assign(record, changes);
          store.put(record);
        }
        resolve();
      };
      req.onerror = () => resolve();
      tx.oncomplete = () => db.close();
    });
  } catch {
    // 静默
  }
}

/**
 * 删除指定队列项。
 * IndexedDB 不可用时静默忽略。
 */
export async function remove(id: string): Promise<void> {
  try {
    const db = await openDB();

    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const req = store.delete(id);

      req.onsuccess = () => resolve();
      req.onerror = () => resolve();
      tx.oncomplete = () => db.close();
    });
  } catch {
    // 静默
  }
}

/**
 * 返回当前用户 pending 状态的队列项数量。
 * IndexedDB 不可用时返回 0。
 */
export async function count(): Promise<number> {
  try {
    const user_id = getUserId();
    if (!user_id) return 0;

    const db = await openDB();

    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAll();

      req.onsuccess = () => {
        const n = (req.result as OfflineQueueItem[]).filter(
          (r) => r.user_id === user_id && r.status === "pending"
        ).length;
        resolve(n);
      };
      req.onerror = () => resolve(0);
      tx.oncomplete = () => db.close();
    });
  } catch {
    return 0;
  }
}

/**
 * 清空当前用户的所有队列项（登出时调用）。
 * IndexedDB 不可用时静默忽略。
 */
export async function clear(): Promise<void> {
  try {
    const user_id = getUserId();
    if (!user_id) return;

    await clearForUser(user_id);
  } catch {
    // 静默
  }
}

/**
 * 清空指定用户的所有队列项（logout 时使用，避免竞态）。
 * IndexedDB 不可用时静默忽略。
 */
export async function clearForUser(userId: string): Promise<void> {
  try {
    const db = await openDB();

    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAll();

      req.onsuccess = () => {
        const records = req.result as OfflineQueueItem[];
        for (const r of records) {
          if (r.user_id === userId) {
            store.delete(r.id);
          }
        }
        resolve();
      };
      req.onerror = () => resolve();
      tx.oncomplete = () => db.close();
    });
  } catch {
    // 静默
  }
}
