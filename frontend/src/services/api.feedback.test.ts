import { describe, expect, it, vi, afterEach } from "vitest";

// openapi-fetch 内部用 new Request(url) 构造请求，需要绝对 URL
vi.mock("@/config/api", () => ({
  API_BASE: "http://localhost:3000/api",
  API_CONFIG: { base: "http://localhost:3000/api", backendUrl: "http://localhost" },
}));

import { submitFeedback, getFeedbackList, getFeedbackDetail } from "./api";

describe("submitFeedback", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("成功时返回反馈结果", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      success: true,
      feedback: {
        id: 1,
        title: "搜索功能响应慢",
        severity: "medium",
        status: "pending",
        log_service_issue_id: null,
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
      feedback_type: "general",
    });

    expect(result.success).toBe(true);
    expect(result.feedback.id).toBe(1);
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
      feedback_type: "general",
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
      feedback_type: "general",
    })).rejects.toMatchObject({
      status: 422,
      message: "title 不能为空",
    });
  });
});

describe("getFeedbackList", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("成功时返回反馈列表", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      items: [
        { id: 1, title: "Bug A", severity: "high", status: "pending", log_service_issue_id: null, created_at: "2026-04-12T10:00:00Z" },
        { id: 2, title: "Bug B", severity: "low", status: "reported", log_service_issue_id: 42, created_at: "2026-04-11T08:00:00Z" },
      ],
      total: 2,
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })));

    const result = await getFeedbackList();
    expect(result.items).toHaveLength(2);
    expect(result.total).toBe(2);
    expect(result.items[0].title).toBe("Bug A");
  });

  it("503 时抛出 ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: "存储服务未初始化",
    }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    })));

    await expect(getFeedbackList()).rejects.toMatchObject({
      status: 503,
    });
  });
});

describe("getFeedbackDetail", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("成功时返回单条反馈", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      id: 1, title: "Bug A", user_id: "u1", severity: "high", status: "pending", log_service_issue_id: null, created_at: "2026-04-12T10:00:00Z",
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })));

    const result = await getFeedbackDetail(1);
    expect(result.id).toBe(1);
    expect(result.title).toBe("Bug A");
  });

  it("404 时抛出 ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: "反馈不存在",
    }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    })));

    await expect(getFeedbackDetail(999)).rejects.toMatchObject({
      status: 404,
    });
  });
});
