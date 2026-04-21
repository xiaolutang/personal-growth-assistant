import { describe, expect, it, vi, afterEach } from "vitest";

// openapi-fetch 内部用 new Request(url) 构造请求，需要绝对 URL
vi.mock("@/config/api", () => ({
  API_BASE: "http://localhost:3000/api",
  API_CONFIG: { base: "http://localhost:3000/api", backendUrl: "http://localhost" },
}));

import { linkGoalEntry, unlinkGoalEntry } from "./api";

const mockGoal = {
  id: "goal-1",
  title: "学习 Rust",
  description: null,
  metric_type: "count" as const,
  target_value: 10,
  current_value: 1,
  progress_percentage: 10.0,
  status: "active" as const,
  start_date: null,
  end_date: null,
  auto_tags: null,
  checklist_items: null,
  linked_entries_count: 1,
  created_at: "2026-04-20T10:00:00Z",
  updated_at: "2026-04-20T10:00:00Z",
};

const mockLinkResponse = {
  id: "link-1",
  goal_id: "goal-1",
  entry_id: "task-abc",
  created_at: "2026-04-20T10:00:00Z",
  entry: {
    id: "task-abc",
    title: "完成第一章",
    status: "doing",
    category: "task",
    created_at: "2026-04-19T08:00:00Z",
  },
  goal: mockGoal,
};

describe("linkGoalEntry", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("成功时返回 goal-entry 关联响应（含 entry 和 goal）", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(mockLinkResponse), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    })));

    const result = await linkGoalEntry("goal-1", "task-abc");

    expect(result.id).toBe("link-1");
    expect(result.goal_id).toBe("goal-1");
    expect(result.entry_id).toBe("task-abc");
    expect(result.entry.title).toBe("完成第一章");
    expect(result.goal.title).toBe("学习 Rust");
    expect(result.goal.linked_entries_count).toBe(1);
  });

  it("API 错误时透传 ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: "条目已关联",
    }), {
      status: 409,
      headers: { "Content-Type": "application/json" },
    })));

    await expect(linkGoalEntry("goal-1", "task-abc")).rejects.toMatchObject({
      status: 409,
      message: "条目已关联",
    });
  });

  it("503 时透传服务不可用", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: "服务暂时不可用",
    }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    })));

    await expect(linkGoalEntry("goal-1", "task-abc")).rejects.toMatchObject({
      status: 503,
    });
  });
});

describe("unlinkGoalEntry", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("成功时无返回值", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, {
      status: 204,
    })));

    const result = await unlinkGoalEntry("goal-1", "task-abc");
    expect(result).toBeUndefined();
  });

  it("404 时抛出 ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: "关联不存在",
    }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    })));

    await expect(unlinkGoalEntry("goal-1", "task-abc")).rejects.toMatchObject({
      status: 404,
    });
  });
});
