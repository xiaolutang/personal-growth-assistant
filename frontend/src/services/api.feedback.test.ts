import { describe, expect, it, vi, afterEach } from "vitest";

import { submitFeedback } from "./api";

describe("submitFeedback", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("成功时返回反馈结果", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      success: true,
      issue: {
        id: 1,
        title: "搜索功能响应慢",
        status: "open",
        created_at: "2026-04-12T10:00:00Z",
      },
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })));

    const result = await submitFeedback({
      title: "搜索功能响应慢",
      description: "任务列表卡顿",
      severity: "medium",
    });

    expect(result.success).toBe(true);
    expect(result.issue.id).toBe(1);
  });

  it("503 时抛出 ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: "反馈服务暂时不可用，请稍后重试",
    }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    })));

    await expect(submitFeedback({
      title: "后端不可用",
      severity: "high",
    })).rejects.toMatchObject({
      status: 503,
      message: "反馈服务暂时不可用，请稍后重试",
    });
  });

  it("422 时透传校验错误", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: "title 不能为空",
    }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    })));

    await expect(submitFeedback({
      title: "",
      severity: "low",
    })).rejects.toMatchObject({
      status: 422,
      message: "title 不能为空",
    });
  });
});
