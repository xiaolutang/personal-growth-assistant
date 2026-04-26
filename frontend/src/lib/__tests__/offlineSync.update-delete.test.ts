/**
 * F142: 离线更新/删除拦截测试
 *
 * 覆盖 test_tasks:
 * 1. 离线 update 拦截入队
 * 2. 离线 delete 拦截入队
 * 3. 5xx 重试最多 3 次
 * 4. 超时重试
 * 5. 快速切换在线/离线
 * 6. 同条目多操作冲突(update→delete)
 * 7. 同条目多次 update 合并
 * 8. 上线后自动回放
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock dependencies before importing
vi.mock("@/lib/offlineQueue", () => ({
  getAll: vi.fn(),
  remove: vi.fn(),
  update: vi.fn(),
}));

vi.mock("@/services/api", () => ({
  createEntry: vi.fn(),
  updateEntry: vi.fn(),
  deleteEntry: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn() },
}));

vi.mock("@/stores/taskStore", () => {
  const removeOfflineEntry = vi.fn();
  const fetchEntries = vi.fn().mockResolvedValue(undefined);
  return {
    useTaskStore: {
      getState: vi.fn(() => ({
        removeOfflineEntry,
        fetchEntries,
      })),
    },
  };
});

import { sync, optimizePendingQueue } from "../offlineSync";
import * as queue from "@/lib/offlineQueue";
import { updateEntry, deleteEntry } from "@/services/api";

const mockQueue = vi.mocked(queue);
const mockUpdateEntry = vi.mocked(updateEntry);
const mockDeleteEntry = vi.mocked(deleteEntry);

function makeItem(overrides: Partial<{
  id: string;
  client_entry_id: string;
  method: string;
  url: string;
  body: object;
  retry_count: number;
  status: "pending" | "synced" | "failed";
}> = {}) {
  return {
    id: overrides.id ?? "q-1",
    user_id: "user-1",
    client_entry_id: overrides.client_entry_id ?? "entry-1",
    method: overrides.method ?? "PUT",
    url: overrides.url ?? "/entries/entry-1",
    body: overrides.body ?? {},
    timestamp: Date.now(),
    status: overrides.status ?? "pending",
    retry_count: overrides.retry_count ?? 0,
  };
}

describe("F142: 离线更新/删除拦截", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ─── 1. 离线 update 拦截入队 ────────────────────────────

  describe("离线 update 拦截入队", () => {
    it("离线时 PUT 操作入队并在回放时调用 updateEntry API", async () => {
      const items = [
        makeItem({
          id: "q-u1",
          method: "PUT",
          url: "/entries/entry-100",
          body: { title: "updated title", status: "doing" },
          client_entry_id: "entry-100",
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);
      mockUpdateEntry.mockResolvedValue({} as any);
      mockQueue.remove.mockResolvedValue();

      await sync();

      expect(mockUpdateEntry).toHaveBeenCalledWith("entry-100", {
        title: "updated title",
        status: "doing",
      });
      expect(mockQueue.remove).toHaveBeenCalledWith("q-u1");
    });
  });

  // ─── 2. 离线 delete 拦截入队 ────────────────────────────

  describe("离线 delete 拦截入队", () => {
    it("离线时 DELETE 操作入队并在回放时调用 deleteEntry API", async () => {
      const items = [
        makeItem({
          id: "q-d1",
          method: "DELETE",
          url: "/entries/entry-200",
          body: {},
          client_entry_id: "entry-200",
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);
      mockDeleteEntry.mockResolvedValue({} as any);
      mockQueue.remove.mockResolvedValue();

      await sync();

      expect(mockDeleteEntry).toHaveBeenCalledWith("entry-200");
      expect(mockQueue.remove).toHaveBeenCalledWith("q-d1");
    });
  });

  // ─── 3. 5xx 重试最多 3 次 ──────────────────────────────

  describe("5xx 重试最多 3 次", () => {
    it("5xx 错误递增 retry_count，达到 3 次后标记 failed", async () => {
      const { toast } = await import("sonner");
      const items = [
        makeItem({
          id: "q-r1",
          method: "PUT",
          url: "/entries/entry-300",
          body: { title: "x" },
          retry_count: 3, // 已经 3 次了
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);

      const err: any = new Error("Server Error");
      err.status = 500;
      mockUpdateEntry.mockRejectedValue(err);

      await sync();

      // retry_count > 3 → failed
      expect(mockQueue.update).toHaveBeenCalledWith("q-r1", {
        status: "failed",
        retry_count: 4,
      });
      expect(toast.error).toHaveBeenCalledWith("同步失败", {
        description: "离线操作重试次数已用尽，请检查网络后重试",
      });
    });

    it("5xx 重试次数未达上限时递增 retry_count 不标记 failed", async () => {
      const items = [
        makeItem({
          id: "q-r2",
          method: "PUT",
          url: "/entries/entry-301",
          body: { title: "x" },
          retry_count: 1,
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);

      const err: any = new Error("Server Error");
      err.status = 500;
      mockUpdateEntry.mockRejectedValue(err);

      await sync();

      // retry_count 1 → 2，不标记 failed
      expect(mockQueue.update).toHaveBeenCalledWith("q-r2", { retry_count: 2 });
      expect(mockQueue.update).not.toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ status: "failed" })
      );
    });
  });

  // ─── 4. 超时重试 ────────────────────────────────────────

  describe("超时重试", () => {
    it("网络超时（无 status）递增 retry_count", async () => {
      const items = [
        makeItem({
          id: "q-t1",
          method: "PUT",
          url: "/entries/entry-400",
          body: { title: "timeout test" },
          retry_count: 0,
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);

      // 模拟超时：无 status 的网络错误
      const err: any = new Error("Timeout");
      // 不设置 status 属性
      mockUpdateEntry.mockRejectedValue(err);

      await sync();

      // 超时被当作网络错误处理，递增 retry_count
      expect(mockQueue.update).toHaveBeenCalledWith("q-t1", { retry_count: 1 });
    });

    it("多次超时后最终达到上限标记 failed", async () => {
      const { toast } = await import("sonner");
      const items = [
        makeItem({
          id: "q-t2",
          method: "DELETE",
          url: "/entries/entry-401",
          body: {},
          retry_count: 3,
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);

      const err: any = new Error("Network request timed out");
      mockDeleteEntry.mockRejectedValue(err);

      await sync();

      expect(mockQueue.update).toHaveBeenCalledWith("q-t2", {
        status: "failed",
        retry_count: 4,
      });
      expect(toast.error).toHaveBeenCalled();
    });
  });

  // ─── 5. 快速切换在线/离线 ───────────────────────────────

  describe("快速切换在线/离线", () => {
    it("同步中 online 事件触发不会导致重入", async () => {
      const items = [
        makeItem({
          id: "q-1",
          method: "PUT",
          url: "/entries/e1",
          body: { title: "test" },
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);

      // 让 updateEntry 慢速执行
      let resolveUpdate: () => void;
      mockUpdateEntry.mockReturnValue(
        new Promise<any>((r) => {
          resolveUpdate = () => r({} as any);
        })
      );

      // 开始同步
      const p1 = sync();

      // 同步进行中再次调用 sync() — 应被忽略
      await sync();

      // 只调用一次 updateEntry
      expect(mockUpdateEntry).toHaveBeenCalledTimes(1);

      // 完成第一次同步
      resolveUpdate!();
      mockQueue.remove.mockResolvedValue();
      await p1;
    });
  });

  // ─── 6. 同条目多操作冲突(update→delete) ──────────────────

  describe("同条目多操作冲突(update→delete)", () => {
    it("同一 entry 的 PUT + DELETE 合并后只执行 DELETE", async () => {
      const items = [
        makeItem({
          id: "q-put",
          method: "PUT",
          url: "/entries/entry-conflict",
          body: { title: "should be discarded" },
          client_entry_id: "entry-conflict",
        }),
        makeItem({
          id: "q-del",
          method: "DELETE",
          url: "/entries/entry-conflict",
          body: {},
          client_entry_id: "entry-conflict",
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);
      mockDeleteEntry.mockResolvedValue({} as any);
      mockQueue.remove.mockResolvedValue();

      await sync();

      // PUT 被丢弃，只有 DELETE 被执行
      expect(mockUpdateEntry).not.toHaveBeenCalled();
      expect(mockDeleteEntry).toHaveBeenCalledWith("entry-conflict");

      // PUT 的队列项从 IDB 删除
      expect(mockQueue.remove).toHaveBeenCalledWith("q-put");
      // DELETE 的队列项也删除
      expect(mockQueue.remove).toHaveBeenCalledWith("q-del");
    });

    it("optimizePendingQueue 正确处理 update→delete 冲突", () => {
      const items = [
        makeItem({
          id: "q-put-1",
          method: "PUT",
          url: "/entries/e1",
          body: { title: "update1" },
          client_entry_id: "e1",
        }),
        makeItem({
          id: "q-put-2",
          method: "PUT",
          url: "/entries/e1",
          body: { title: "update2" },
          client_entry_id: "e1",
        }),
        makeItem({
          id: "q-del",
          method: "DELETE",
          url: "/entries/e1",
          body: {},
          client_entry_id: "e1",
        }),
      ];

      const { optimized, discarded } = optimizePendingQueue(items);

      // 所有 PUT 被丢弃
      expect(discarded).toContain("q-put-1");
      expect(discarded).toContain("q-put-2");
      // 只保留 DELETE
      expect(optimized).toHaveLength(1);
      expect(optimized[0].method).toBe("DELETE");
      expect(optimized[0].id).toBe("q-del");
    });
  });

  // ─── 7. 同条目多次 update 合并 ──────────────────────────

  describe("同条目多次 update 合并", () => {
    it("同一 entry 的多次 PUT 累积合并 body（partial patch 语义）", async () => {
      const items = [
        makeItem({
          id: "q-put-1",
          method: "PUT",
          url: "/entries/entry-merge",
          body: { title: "first update" },
          client_entry_id: "entry-merge",
        }),
        makeItem({
          id: "q-put-2",
          method: "PUT",
          url: "/entries/entry-merge",
          body: { status: "doing" },
          client_entry_id: "entry-merge",
        }),
        makeItem({
          id: "q-put-3",
          method: "PUT",
          url: "/entries/entry-merge",
          body: { title: "final title" },
          client_entry_id: "entry-merge",
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);
      mockUpdateEntry.mockResolvedValue({} as any);
      mockQueue.remove.mockResolvedValue();

      await sync();

      // 只调用一次 updateEntry，body 是所有 PUT 的累积合并
      expect(mockUpdateEntry).toHaveBeenCalledTimes(1);
      expect(mockUpdateEntry).toHaveBeenCalledWith("entry-merge", {
        title: "final title", // 被第三次覆盖
        status: "doing", // 第二次的字段保留
      });

      // 前两次 PUT 被丢弃并从 IDB 删除
      expect(mockQueue.remove).toHaveBeenCalledWith("q-put-1");
      expect(mockQueue.remove).toHaveBeenCalledWith("q-put-2");
      expect(mockQueue.remove).toHaveBeenCalledWith("q-put-3");
    });

    it("partial patch 合并：不同字段的更新全部保留", async () => {
      const items = [
        makeItem({
          id: "q-1",
          method: "PUT",
          url: "/entries/e1",
          body: { title: "new title" },
          client_entry_id: "e1",
        }),
        makeItem({
          id: "q-2",
          method: "PUT",
          url: "/entries/e1",
          body: { status: "complete" },
          client_entry_id: "e1",
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);
      mockUpdateEntry.mockResolvedValue({} as any);
      mockQueue.remove.mockResolvedValue();

      await sync();

      // 合并后的 body 应包含两个字段
      expect(mockUpdateEntry).toHaveBeenCalledWith("e1", {
        title: "new title",
        status: "complete",
      });
    });

    it("optimizePendingQueue 累积合并多次 PUT 的 body（partial patch）", () => {
      const items = [
        makeItem({
          id: "q-1",
          method: "PUT",
          url: "/entries/e1",
          body: { title: "first" },
          client_entry_id: "e1",
        }),
        makeItem({
          id: "q-2",
          method: "PUT",
          url: "/entries/e1",
          body: { status: "doing" },
          client_entry_id: "e1",
        }),
      ];

      const { optimized, discarded } = optimizePendingQueue(items);

      expect(discarded).toEqual(["q-1"]);
      expect(optimized).toHaveLength(1);
      expect(optimized[0].id).toBe("q-2");
      // 累积合并：两个字段都保留
      expect(optimized[0].body).toEqual({ title: "first", status: "doing" });
    });

    it("不同 entry 的 PUT 不合并", async () => {
      const items = [
        makeItem({
          id: "q-1",
          method: "PUT",
          url: "/entries/entry-a",
          body: { title: "update A" },
          client_entry_id: "entry-a",
        }),
        makeItem({
          id: "q-2",
          method: "PUT",
          url: "/entries/entry-b",
          body: { title: "update B" },
          client_entry_id: "entry-b",
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);
      mockUpdateEntry.mockResolvedValue({} as any);
      mockQueue.remove.mockResolvedValue();

      await sync();

      expect(mockUpdateEntry).toHaveBeenCalledTimes(2);
      expect(mockUpdateEntry).toHaveBeenCalledWith("entry-a", { title: "update A" });
      expect(mockUpdateEntry).toHaveBeenCalledWith("entry-b", { title: "update B" });
    });
  });

  // ─── 8. 上线后自动回放 ──────────────────────────────────

  describe("上线后自动回放", () => {
    it("混合 PUT 和 DELETE 队列全部回放成功", async () => {
      const items = [
        makeItem({
          id: "q-u1",
          method: "PUT",
          url: "/entries/entry-a",
          body: { title: "update A" },
          client_entry_id: "entry-a",
        }),
        makeItem({
          id: "q-d1",
          method: "DELETE",
          url: "/entries/entry-b",
          body: {},
          client_entry_id: "entry-b",
        }),
        makeItem({
          id: "q-u2",
          method: "PUT",
          url: "/entries/entry-c",
          body: { status: "complete" },
          client_entry_id: "entry-c",
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);
      mockUpdateEntry.mockResolvedValue({} as any);
      mockDeleteEntry.mockResolvedValue({} as any);
      mockQueue.remove.mockResolvedValue();

      await sync();

      expect(mockUpdateEntry).toHaveBeenCalledWith("entry-a", { title: "update A" });
      expect(mockDeleteEntry).toHaveBeenCalledWith("entry-b");
      expect(mockUpdateEntry).toHaveBeenCalledWith("entry-c", { status: "complete" });
      expect(mockQueue.remove).toHaveBeenCalledTimes(3);
    });

    it("部分回放失败不影响其他操作", async () => {
      const items = [
        makeItem({
          id: "q-ok1",
          method: "PUT",
          url: "/entries/entry-ok",
          body: { title: "ok" },
          client_entry_id: "entry-ok",
        }),
        makeItem({
          id: "q-fail",
          method: "DELETE",
          url: "/entries/entry-fail",
          body: {},
          client_entry_id: "entry-fail",
        }),
        makeItem({
          id: "q-ok2",
          method: "PUT",
          url: "/entries/entry-ok2",
          body: { title: "ok2" },
          client_entry_id: "entry-ok2",
        }),
      ];
      mockQueue.getAll.mockResolvedValue(items);

      mockUpdateEntry.mockResolvedValue({} as any);
      const err: any = new Error("Server Error");
      err.status = 500;
      mockDeleteEntry.mockRejectedValue(err);
      mockQueue.remove.mockResolvedValue();

      await sync();

      // 成功的 PUT 都执行了
      expect(mockUpdateEntry).toHaveBeenCalledTimes(2);
      // DELETE 失败，递增 retry_count
      expect(mockQueue.update).toHaveBeenCalledWith("q-fail", { retry_count: 1 });
      // 成功的都被移除
      expect(mockQueue.remove).toHaveBeenCalledWith("q-ok1");
      expect(mockQueue.remove).toHaveBeenCalledWith("q-ok2");
    });
  });

  // ─── optimizePendingQueue 纯函数单元测试 ──────────────────

  describe("optimizePendingQueue", () => {
    it("空数组返回空优化列表", () => {
      const { optimized, discarded } = optimizePendingQueue([]);
      expect(optimized).toEqual([]);
      expect(discarded).toEqual([]);
    });

    it("POST 条目不参与合并", () => {
      const items = [
        makeItem({
          id: "q-post",
          method: "POST",
          url: "/entries",
          body: { title: "new" },
          client_entry_id: "local-1",
        }),
        makeItem({
          id: "q-put",
          method: "PUT",
          url: "/entries/e1",
          body: { title: "update" },
          client_entry_id: "e1",
        }),
      ];

      const { optimized, discarded } = optimizePendingQueue(items);
      expect(optimized).toHaveLength(2);
      expect(discarded).toEqual([]);
    });

    it("单条 PUT 不合并", () => {
      const items = [
        makeItem({
          id: "q-1",
          method: "PUT",
          url: "/entries/e1",
          body: { title: "only" },
          client_entry_id: "e1",
        }),
      ];

      const { optimized, discarded } = optimizePendingQueue(items);
      expect(optimized).toHaveLength(1);
      expect(discarded).toEqual([]);
    });

    it("单条 DELETE 不受影响", () => {
      const items = [
        makeItem({
          id: "q-1",
          method: "DELETE",
          url: "/entries/e1",
          body: {},
          client_entry_id: "e1",
        }),
      ];

      const { optimized, discarded } = optimizePendingQueue(items);
      expect(optimized).toHaveLength(1);
      expect(optimized[0].method).toBe("DELETE");
      expect(discarded).toEqual([]);
    });

    it("多条 DELETE 保留最后一条", () => {
      const items = [
        makeItem({
          id: "q-d1",
          method: "DELETE",
          url: "/entries/e1",
          body: {},
          client_entry_id: "e1",
        }),
        makeItem({
          id: "q-d2",
          method: "DELETE",
          url: "/entries/e1",
          body: {},
          client_entry_id: "e1",
        }),
      ];

      const { optimized, discarded } = optimizePendingQueue(items);
      expect(discarded).toEqual(["q-d1"]);
      expect(optimized).toHaveLength(1);
      expect(optimized[0].id).toBe("q-d2");
    });
  });
});
