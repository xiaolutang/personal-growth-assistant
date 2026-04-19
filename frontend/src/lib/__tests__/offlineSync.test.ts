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
import { createEntry } from "@/services/api";
import { useTaskStore } from "@/stores/taskStore";

const mockQueue = vi.mocked(queue);
const mockCreateEntry = vi.mocked(createEntry);
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
    // Reset syncing state between tests by reimporting... but we can't.
    // The sync function uses a module-level `syncing` boolean.
    // We rely on each test completing sync before the next one.
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("syncs 3 pending items — all succeed", async () => {
    const items = [makeItem({ id: "q-1", client_entry_id: "local-1" }), makeItem({ id: "q-2", client_entry_id: "local-2" }), makeItem({ id: "q-3", client_entry_id: "local-3" })];
    mockQueue.getAll.mockResolvedValue(items);
    mockCreateEntry.mockResolvedValue({} as any);
    mockQueue.remove.mockResolvedValue();

    const progressEvents: (any | null)[] = [];
    const unsub = subscribeSyncProgress((p) => progressEvents.push(p));

    await sync();

    expect(mockCreateEntry).toHaveBeenCalledTimes(3);
    expect(mockQueue.remove).toHaveBeenCalledTimes(3);
    expect(removeOfflineEntry()).toHaveBeenCalledTimes(3);
    expect(fetchEntries()).toHaveBeenCalledTimes(1);

    // Progress events: 3 items + final null
    expect(progressEvents.filter((p) => p !== null)).toHaveLength(3);
    expect(progressEvents[progressEvents.length - 1]).toBeNull();

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

  it("retry_count > 3 marks as failed", async () => {
    const items = [makeItem({ id: "q-1", retry_count: 3 })];
    mockQueue.getAll.mockResolvedValue(items);

    const err: any = new Error("Server Error");
    err.status = 500;
    mockCreateEntry.mockRejectedValue(err);

    await sync();

    expect(mockQueue.update).toHaveBeenCalledWith("q-1", { status: "failed", retry_count: 4 });
  });

  it("empty queue — no API calls", async () => {
    mockQueue.getAll.mockResolvedValue([]);

    await sync();

    expect(mockCreateEntry).not.toHaveBeenCalled();
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

  it("401 marks failed and stops", async () => {
    const items = [makeItem({ id: "q-1" }), makeItem({ id: "q-2" })];
    mockQueue.getAll.mockResolvedValue(items);

    const err: any = new Error("Unauthorized");
    err.status = 401;
    mockCreateEntry.mockRejectedValue(err);

    await sync();

    // Only first item attempted, second skipped
    expect(mockCreateEntry).toHaveBeenCalledTimes(1);
    expect(mockQueue.update).toHaveBeenCalledWith("q-1", { status: "failed" });
    expect(mockQueue.remove).not.toHaveBeenCalled();
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
});
