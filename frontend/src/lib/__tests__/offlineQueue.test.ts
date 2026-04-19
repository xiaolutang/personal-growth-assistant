/**
 * offlineQueue.ts 单元测试
 *
 * 通过 mock indexedDB.open 来模拟 IndexedDB 行为。
 * 使用 fake-indexeddb 风格的内存实现。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ─── mock userStore ─────────────────────────────────────

let mockUserId: string | null = "user-1";

vi.mock("@/stores/userStore", () => ({
  useUserStore: {
    getState: () => ({
      user: mockUserId ? { id: mockUserId } : null,
    }),
  },
}));

// ─── In-memory IndexedDB mock ───────────────────────────

/**
 * 创建一个内存中的 IndexedDB mock。
 * indexedDB.open() 返回的 request 对象会在同步设置 onsuccess 之后
 * 由 Promise.resolve() 触发，确保回调注册在触发之前。
 */
function createMockIndexedDB() {
  const records = new Map<string, Record<string, unknown>>();

  function open() {
    const request = {
      result: {
        objectStoreNames: { contains: () => true },
        transaction(_storeName: string, _mode: string) {
          const store = {
            add(record: Record<string, unknown>) {
              const id = record.id as string;
              records.set(id, { ...record });
              return makeRequest(undefined);
            },
            put(record: Record<string, unknown>) {
              const id = record.id as string;
              records.set(id, { ...record });
              return makeRequest(undefined);
            },
            get(id: string) {
              return makeRequest(records.get(id) ?? null);
            },
            getAll() {
              return makeRequest([...records.values()]);
            },
            delete(id: string) {
              records.delete(id);
              return makeRequest(undefined);
            },
          };
          const tx = {
            objectStore: () => store,
            oncomplete: null as (() => void) | null,
          };
          // 在所有同步操作完成后触发 oncomplete
          Promise.resolve().then(() => tx.oncomplete?.());
          return tx;
        },
        close() {},
      } as unknown as IDBDatabase,
      onupgradeneeded: null as (() => void) | null,
      onsuccess: null as (() => void) | null,
      onerror: null as (() => void) | null,
    };

    // 使用 Promise.resolve() 确保在同步注册 onsuccess 后触发
    Promise.resolve().then(() => request.onsuccess?.());

    return request;
  }

  return { open, records };
}

function makeRequest(result: unknown) {
  const request = {
    result,
    error: null,
    onsuccess: null as (() => void) | null,
    onerror: null as (() => void) | null,
  };
  Promise.resolve().then(() => request.onsuccess?.());
  return request;
}

// ─── 测试 ───────────────────────────────────────────────

describe("offlineQueue", () => {
  let mockIDB: ReturnType<typeof createMockIndexedDB>;
  let originalIndexedDB: typeof indexedDB;

  beforeEach(() => {
    mockIDB = createMockIndexedDB();
    mockUserId = "user-1";
    originalIndexedDB = globalThis.indexedDB;

    Object.defineProperty(globalThis, "indexedDB", {
      value: { open: mockIDB.open },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(globalThis, "indexedDB", {
      value: originalIndexedDB,
      writable: true,
      configurable: true,
    });
    vi.restoreAllMocks();
  });

  it("add → getAll 返回包含该条目的数组（含正确 user_id 和 client_entry_id）", async () => {
    const { add, getAll } = await import("../offlineQueue");

    const id = await add({
      client_entry_id: "local-123",
      method: "POST",
      url: "/entries",
      body: { text: "hello" },
    });

    expect(id).toBeTruthy();

    const items = await getAll();
    expect(items).toHaveLength(1);
    expect(items[0].user_id).toBe("user-1");
    expect(items[0].client_entry_id).toBe("local-123");
    expect(items[0].status).toBe("pending");
    expect(items[0].retry_count).toBe(0);
  });

  it("多次 add → getAll 返回多条，count() 返回正确数字", async () => {
    const { add, getAll, count } = await import("../offlineQueue");

    await add({ client_entry_id: "local-1", method: "POST", url: "/entries", body: {} });
    await add({ client_entry_id: "local-2", method: "PUT", url: "/entries/1", body: {} });
    await add({ client_entry_id: "local-3", method: "DELETE", url: "/entries/2", body: {} });

    const items = await getAll();
    expect(items).toHaveLength(3);

    const c = await count();
    expect(c).toBe(3);
  });

  it("update(id, {retry_count: 1}) → getAll() 返回更新后的条目", async () => {
    const { add, getAll, update } = await import("../offlineQueue");

    const id = await add({
      client_entry_id: "local-u1",
      method: "POST",
      url: "/entries",
      body: {},
    });

    await update(id, { retry_count: 1, status: "failed" });

    const items = await getAll();
    expect(items).toHaveLength(1);
    expect(items[0].retry_count).toBe(1);
    expect(items[0].status).toBe("failed");
  });

  it("remove(id) → 再次 getAll 不包含该条目", async () => {
    const { add, getAll, remove } = await import("../offlineQueue");

    const id1 = await add({ client_entry_id: "local-r1", method: "POST", url: "/entries", body: {} });
    const id2 = await add({ client_entry_id: "local-r2", method: "POST", url: "/entries", body: {} });

    await remove(id1);

    const items = await getAll();
    expect(items).toHaveLength(1);
    expect(items[0]?.id).toBe(id2);
  });

  it("mock IndexedDB.open 抛错 → add 返回 ''，getAll 返回 []，count 返回 0", async () => {
    // 让 indexedDB.open 抛出异常
    Object.defineProperty(globalThis, "indexedDB", {
      value: {
        open: () => {
          throw new Error("IndexedDB not available");
        },
      },
      writable: true,
      configurable: true,
    });

    const { add, getAll, count } = await import("../offlineQueue");

    const id = await add({ client_entry_id: "local-x", method: "POST", url: "/entries", body: {} });
    expect(id).toBe("");

    const items = await getAll();
    expect(items).toEqual([]);

    const c = await count();
    expect(c).toBe(0);
  });

  it("不同 user_id 的 add → getAll 只返回当前用户的条目", async () => {
    const { add, getAll } = await import("../offlineQueue");

    // user-A 添加
    mockUserId = "user-A";
    await add({ client_entry_id: "local-a1", method: "POST", url: "/entries", body: {} });
    await add({ client_entry_id: "local-a2", method: "POST", url: "/entries", body: {} });

    // 切换到 user-B
    mockUserId = "user-B";
    await add({ client_entry_id: "local-b1", method: "POST", url: "/entries", body: {} });

    // user-B 只看到自己的
    const itemsB = await getAll();
    expect(itemsB).toHaveLength(1);
    expect(itemsB[0].client_entry_id).toBe("local-b1");

    // 切回 user-A 看到自己的
    mockUserId = "user-A";
    const itemsA = await getAll();
    expect(itemsA).toHaveLength(2);
  });

  it("clear() → getAll 返回空数组", async () => {
    const { add, getAll, clear } = await import("../offlineQueue");

    await add({ client_entry_id: "local-c1", method: "POST", url: "/entries", body: {} });
    await add({ client_entry_id: "local-c2", method: "POST", url: "/entries", body: {} });

    expect(await getAll()).toHaveLength(2);

    await clear();

    const items = await getAll();
    expect(items).toEqual([]);
  });

  it("未登录时 add 返回空字符串", async () => {
    mockUserId = null;
    const { add } = await import("../offlineQueue");

    const id = await add({ client_entry_id: "local-nologin", method: "POST", url: "/entries", body: {} });
    expect(id).toBe("");
  });

  it("未登录时 getAll 返回空数组", async () => {
    mockUserId = null;
    const { getAll } = await import("../offlineQueue");

    const items = await getAll();
    expect(items).toEqual([]);
  });

  it("未登录时 count 返回 0", async () => {
    mockUserId = null;
    const { count } = await import("../offlineQueue");

    const c = await count();
    expect(c).toBe(0);
  });

  it("count 只计算 pending 状态的条目", async () => {
    const { add, getAll, update, count } = await import("../offlineQueue");

    const id1 = await add({ client_entry_id: "local-p1", method: "POST", url: "/entries", body: {} });
    await add({ client_entry_id: "local-p2", method: "POST", url: "/entries", body: {} });

    // 将 id1 标记为 synced
    await update(id1, { status: "synced" });

    const c = await count();
    expect(c).toBe(1);

    // getAll 仍然返回全部
    const items = await getAll();
    expect(items).toHaveLength(2);
  });
});
