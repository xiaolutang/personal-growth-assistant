import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/config/api", () => ({
  API_BASE: "http://localhost:3000/api",
  API_CONFIG: { base: "http://localhost:3000/api", backendUrl: "http://localhost" },
}));

import { searchEntries } from "./api";

describe("searchEntries", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("空搜索词保留为空字符串，不发送 null", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      results: [],
      query: "",
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchSpy);

    await searchEntries("", 20, "note", {
      startTime: "2026-04-28T00:00:00.000",
      endTime: "2026-04-28T23:59:59.999",
    });

    const request = fetchSpy.mock.calls[0][0] as Request;
    const body = JSON.parse(await request.text());

    expect(body.query).toBe("");
    expect(body.query).not.toBeNull();
    expect(body.filter_type).toBe("note");
  });

  it("原样透传本地时间过滤值", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      results: [],
      query: "",
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchSpy);

    await searchEntries("", 20, undefined, {
      startTime: "2026-04-28T00:00:00.000",
      endTime: "2026-04-30T23:59:59.999",
      tags: ["ai"],
    });

    const request = fetchSpy.mock.calls[0][0] as Request;
    const body = JSON.parse(await request.text());

    expect(body.start_time).toBe("2026-04-28T00:00:00.000");
    expect(body.end_time).toBe("2026-04-30T23:59:59.999");
    expect(body.tags).toEqual(["ai"]);
  });
});
