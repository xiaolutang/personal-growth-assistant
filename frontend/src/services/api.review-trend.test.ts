import { describe, expect, it, vi, afterEach } from "vitest";

import { getReviewTrend } from "./api";

describe("getReviewTrend", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const mockTrendData = {
    periods: [
      { date: "2026-04-14", total: 5, completed: 3, completion_rate: 60.0, notes_count: 2 },
      { date: "2026-04-13", total: 4, completed: 2, completion_rate: 50.0, notes_count: 1 },
    ],
  };

  it("正确传递 daily period 和 days 参数", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify(mockTrendData), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchSpy);

    const result = await getReviewTrend("daily", 7);

    expect(result.periods).toHaveLength(2);
    expect(result.periods[0].completion_rate).toBe(60.0);
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toContain("period=daily");
    expect(calledUrl).toContain("days=7");
  });

  it("正确传递 weekly period 和 weeks 参数", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify(mockTrendData), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchSpy);

    const result = await getReviewTrend("weekly", 8);

    expect(result.periods).toHaveLength(2);
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toContain("period=weekly");
    expect(calledUrl).toContain("weeks=8");
  });

  it("默认 daily 传 days=7，weekly 传 weeks=8", async () => {
    const fetchSpy = vi.fn().mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify(mockTrendData), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }))
    );
    vi.stubGlobal("fetch", fetchSpy);

    await getReviewTrend("daily");
    expect((fetchSpy.mock.calls[0][0] as string)).toContain("days=7");

    await getReviewTrend("weekly");
    expect((fetchSpy.mock.calls[1][0] as string)).toContain("weeks=8");
  });

  it("空数组返回时正常返回空 periods", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ periods: [] }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })));

    const result = await getReviewTrend("daily", 7);
    expect(result.periods).toHaveLength(0);
  });

  it("API 错误时透传 ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: "趋势数据查询失败",
    }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    })));

    await expect(getReviewTrend("daily", 7)).rejects.toMatchObject({
      status: 500,
      message: "趋势数据查询失败",
    });
  });

  it("503 错误透传", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: "服务暂时不可用",
    }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    })));

    await expect(getReviewTrend("weekly", 8)).rejects.toMatchObject({
      status: 503,
    });
  });
});
