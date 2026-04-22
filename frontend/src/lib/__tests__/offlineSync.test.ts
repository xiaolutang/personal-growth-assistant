import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock dependencies before importing
vi.mock("@/lib/offlineQueue", () => ({
  getAll: vi.fn(),
  count: vi.fn(),
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

import { sync, initSync, subscribeSyncProgress, isSyncing } from "../offlineSync";
import * as queue from "@/lib/offlineQueue";
import { createEntry, updateEntry, deleteEntry } from "@/services/api";
import { useTaskStore } from "@/stores/taskStore";

const mockQueue = vi.mocked(queue);
const mockCreateEntry = vi.mocked(createEntry);
const mockUpdateEntry = vi.mocked(updateEntry);
const mockDeleteEntry = vi.mocked(deleteEntry);
const mockTaskStore = vi.mocked(useTaskStore);

// Extract stable references to the mock functions
const removeOfflineEntry = () => mockTaskStore.getState().removeOfflineEntry;
const fetchEntries = () => mockTaskStore.getState().fetchEntries;

function makeItem(overrides: Partial<{ id: string; client_entry_id: string; method: string; url: string; body: object; retry_count: number; status: "pending" | "synced" | "failed" }> = {}) {
  return {
    id: overrides.id ?? "q-1",
    user_id: "user-1",
    client_entry_id: overrides.client_entry_id ?? "local-1",
    method: overrides.method ?? "POST",
    url: overrides.url ?? "/entries",
    body: overrides.body ?? { type: "inbox", title: "test", content: "test", status: "complete" },
    timestamp: Date.now(),
    status: overrides.status ?? "pending",
    retry_count: overrides.retry_count ?? 0,
  };
}

describe("offlineSync", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("syncs 3 pending POST items — all succeed", async () => {
    const items = [makeItem({ id: "q-1", client_entry_id: "local-1" }), makeItem({ id: "q-2", client_entry_id: "local-2" }), makeItem({ id: "q-3", client_entry_id: "local-3" })];
    mockQueue.getAll.mockResolvedValue(items);
    mockCreateEntry.mockResolvedValue({} as any);
    mockQueue.remove.mockResolvedValue();

    const events: any[] = [];
    const unsub = subscribeSyncProgress((e) => events.push(e));

    await sync();

    expect(mockCreateEntry).toHaveBeenCalledTimes(3);
    expect(mockQueue.remove).toHaveBeenCalledTimes(3);
    expect(removeOfflineEntry()).toHaveBeenCalledTimes(3);
    expect(fetchEntries()).toHaveBeenCalledTimes(1);

    // Events: 3 progress + 1 completed
    expect(events.filter((e) => e.type === "progress")).toHaveLength(3);
    expect(events[events.length - 1].type).toBe("completed");

    unsub();
  });

  it("2nd item 5xx — continues with 1st and 3rd", async () => {
    const items = [makeItem({ id: "q-1" }), makeItem({ id: "q-2" }), makeItem({ id: "q-3" })];
    mockQueue.getAll.mockResolvedValue(items);

    const err: any = new Error("Server Error");
    err.status = 500;
    mockCreateEntry
      .mockResolvedValueOnce({} as any)
      .mockRejectedValueOnce(err)
      .mockResolvedValueOnce({} as any);

    await sync();

    expect(mockCreateEntry).toHaveBeenCalledTimes(3);
    expect(mockQueue.remove).toHaveBeenCalledTimes(2); // only 1st and 3rd removed
    expect(mockQueue.update).toHaveBeenCalledWith("q-2", { retry_count: 1 });
  });

  it("retry_count > 3 marks as failed and toasts", async () => {
    const { toast } = await import("sonner");
    const items = [makeItem({ id: "q-1", retry_count: 3 })];
    mockQueue.getAll.mockResolvedValue(items);

    const err: any = new Error("Server Error");
    err.status = 500;
    mockCreateEntry.mockRejectedValue(err);

    await sync();

    expect(mockQueue.update).toHaveBeenCalledWith("q-1", { status: "failed", retry_count: 4 });
    expect(toast.error).toHaveBeenCalledWith("同步失败", { description: "离线操作重试次数已用尽，请检查网络后重试" });
    // Terminal failure triggers fetchEntries to rollback optimistic state
    expect(fetchEntries()).toHaveBeenCalled();
  });

  it("empty queue — no API calls", async () => {
    mockQueue.getAll.mockResolvedValue([]);

    await sync();

    expect(mockCreateEntry).not.toHaveBeenCalled();
    expect(mockUpdateEntry).not.toHaveBeenCalled();
    expect(mockDeleteEntry).not.toHaveBeenCalled();
  });

  it("prevents reentry (boolean lock)", async () => {
    const items = [makeItem({ id: "q-1" })];
    mockQueue.getAll.mockResolvedValue(items);

    // Make createEntry slow
    let resolveCreate: () => void;
    mockCreateEntry.mockReturnValue(new Promise<any>((r) => { resolveCreate = () => r({} as any); }));

    // Start first sync (doesn't await)
    const p1 = sync();
    expect(isSyncing()).toBe(true);

    // Try second sync (should be no-op)
    await sync();
    expect(mockCreateEntry).toHaveBeenCalledTimes(1);

    // Resolve first sync
    resolveCreate!();
    await p1;
    expect(isSyncing()).toBe(false);
  });

  it("401 marks failed, stops, and emits auth_failed event", async () => {
    const items = [makeItem({ id: "q-1" }), makeItem({ id: "q-2" })];
    mockQueue.getAll.mockResolvedValue(items);

    const err: any = new Error("Unauthorized");
    err.status = 401;
    mockCreateEntry.mockRejectedValue(err);

    const events: any[] = [];
    const unsub = subscribeSyncProgress((e) => events.push(e));

    await sync();

    // Only first item attempted, second skipped
    expect(mockCreateEntry).toHaveBeenCalledTimes(1);
    expect(mockQueue.update).toHaveBeenCalledWith("q-1", { status: "failed" });
    expect(mockQueue.remove).not.toHaveBeenCalled();
    // Last event should be auth_failed
    expect(events[events.length - 1].type).toBe("auth_failed");

    unsub();
  });

  it("replays PUT mutation successfully", async () => {
    const items = [
      makeItem({ id: "q-1", method: "PUT", url: "/entries/entry-123", body: { title: "updated title" }, client_entry_id: "entry-123" }),
    ];
    mockQueue.getAll.mockResolvedValue(items);
    mockUpdateEntry.mockResolvedValue({} as any);
    mockQueue.remove.mockResolvedValue();

    await sync();

    expect(mockUpdateEntry).toHaveBeenCalledWith("entry-123", { title: "updated title" });
    expect(mockQueue.remove).toHaveBeenCalledWith("q-1");
    // PUT should NOT call removeOfflineEntry (only POST does)
    expect(removeOfflineEntry()).not.toHaveBeenCalled();
    // PUT-only sync does not trigger fetchEntries (preserves page-level filters)
    expect(fetchEntries()).not.toHaveBeenCalled();
  });

  it("replays DELETE mutation successfully", async () => {
    const items = [
      makeItem({ id: "q-1", method: "DELETE", url: "/entries/entry-456", body: {}, client_entry_id: "entry-456" }),
    ];
    mockQueue.getAll.mockResolvedValue(items);
    mockDeleteEntry.mockResolvedValue({} as any);
    mockQueue.remove.mockResolvedValue();

    await sync();

    expect(mockDeleteEntry).toHaveBeenCalledWith("entry-456");
    expect(mockQueue.remove).toHaveBeenCalledWith("q-1");
    // DELETE should NOT call removeOfflineEntry
    expect(removeOfflineEntry()).not.toHaveBeenCalled();
    // DELETE-only sync does not trigger fetchEntries
    expect(fetchEntries()).not.toHaveBeenCalled();
  });

  it("replays mixed POST, PUT, DELETE mutations", async () => {
    const items = [
      makeItem({ id: "q-1", method: "POST", url: "/entries", body: { type: "inbox", title: "new" } }),
      makeItem({ id: "q-2", method: "PUT", url: "/entries/e1", body: { title: "update" }, client_entry_id: "e1" }),
      makeItem({ id: "q-3", method: "DELETE", url: "/entries/e2", body: {}, client_entry_id: "e2" }),
    ];
    mockQueue.getAll.mockResolvedValue(items);
    mockCreateEntry.mockResolvedValue({} as any);
    mockUpdateEntry.mockResolvedValue({} as any);
    mockDeleteEntry.mockResolvedValue({} as any);
    mockQueue.remove.mockResolvedValue();

    await sync();

    expect(mockCreateEntry).toHaveBeenCalledTimes(1);
    expect(mockUpdateEntry).toHaveBeenCalledWith("e1", { title: "update" });
    expect(mockDeleteEntry).toHaveBeenCalledWith("e2");
    expect(mockQueue.remove).toHaveBeenCalledTimes(3);
    // Only POST calls removeOfflineEntry
    expect(removeOfflineEntry()).toHaveBeenCalledTimes(1);
  });

  it("replays POST with category from merged update", async () => {
    // Simulates: offline create (type=inbox) → offline update (category=task) → sync
    const items = [
      makeItem({
        id: "q-1",
        method: "POST",
        url: "/entries",
        body: { type: "inbox", title: "my idea", content: "desc", category: "task" },
      }),
    ];
    mockQueue.getAll.mockResolvedValue(items);
    mockCreateEntry.mockResolvedValue({} as any);
    mockQueue.remove.mockResolvedValue();

    await sync();

    // Should use category (task) over type (inbox)
    expect(mockCreateEntry).toHaveBeenCalledWith({
      type: "task",
      title: "my idea",
      content: "desc",
      status: undefined,
    });
  });

  it("4xx replay marks failed and toasts", async () => {
    const { toast } = await import("sonner");
    const items = [makeItem({ id: "q-1", method: "PUT", url: "/entries/e1", body: { title: "x" } })];
    mockQueue.getAll.mockResolvedValue(items);

    const err: any = new Error("Bad Request");
    err.status = 400;
    mockUpdateEntry.mockRejectedValue(err);

    await sync();

    expect(mockQueue.update).toHaveBeenCalledWith("q-1", { status: "failed" });
    expect(toast.error).toHaveBeenCalledWith("同步失败", { description: "部分离线操作未能同步，请检查后重试" });
    // Terminal failure triggers fetchEntries to rollback optimistic state
    expect(fetchEntries()).toHaveBeenCalled();
  });

  it("skips unknown method/url without deleting", async () => {
    const items = [
      makeItem({ id: "q-1", method: "PATCH", url: "/entries/123", body: {} }),
      makeItem({ id: "q-2", method: "POST", url: "/entries", body: { type: "inbox", title: "valid" } }),
    ];
    mockQueue.getAll.mockResolvedValue(items);
    mockCreateEntry.mockResolvedValue({} as any);
    mockQueue.remove.mockResolvedValue();

    await sync();

    // Only POST /entries is processed
    expect(mockCreateEntry).toHaveBeenCalledTimes(1);
    expect(mockQueue.remove).toHaveBeenCalledTimes(1);
    expect(mockQueue.remove).toHaveBeenCalledWith("q-2");
  });

  it("initSync triggers sync when online + queue has items", async () => {
    Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
    mockQueue.count.mockResolvedValue(2);
    mockQueue.getAll.mockResolvedValue([]);

    await initSync();

    expect(mockQueue.count).toHaveBeenCalled();
  });

  it("initSync does not trigger when offline", async () => {
    Object.defineProperty(navigator, "onLine", { value: false, configurable: true });

    await initSync();

    expect(mockQueue.count).not.toHaveBeenCalled();
  });

  it("API succeeds but queue.remove fails — marks synced, next sync cleans up without re-executing API", async () => {
    // First sync: API succeeds, queue.remove fails
    const items = [makeItem({ id: "q-1" })];
    mockQueue.getAll.mockResolvedValueOnce(items);
    mockCreateEntry.mockResolvedValueOnce({} as any);
    // queue.update for synced status succeeds
    mockQueue.update.mockResolvedValueOnce(true as any);
    // queue.remove fails
    mockQueue.remove.mockRejectedValueOnce(new Error("IDB error"));

    await sync();

    // Should have marked as synced
    expect(mockQueue.update).toHaveBeenCalledWith("q-1", { status: "synced" });
    // remove was attempted
    expect(mockQueue.remove).toHaveBeenCalledWith("q-1");
    // API was called once
    expect(mockCreateEntry).toHaveBeenCalledTimes(1);

    vi.clearAllMocks();

    // Second sync: item is synced, should be cleaned up without API call
    const syncedItem = makeItem({ id: "q-1", status: "synced" as any });
    mockQueue.getAll.mockResolvedValueOnce([syncedItem]);
    mockQueue.remove.mockResolvedValueOnce();

    await sync();

    // Should have removed the synced item
    expect(mockQueue.remove).toHaveBeenCalledWith("q-1");
    // API should NOT be called again
    expect(mockCreateEntry).not.toHaveBeenCalled();
  });
});
